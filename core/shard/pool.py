from __future__ import annotations

__all__ = (
    "UsedShardIdsCache", "DeadCallbacks", "ShardStateContext",
    "TemporaryShardStateContext", "ShardState", "ShardPool"
)

from typing import TYPE_CHECKING, NamedTuple, TypeAlias, Any
from collections.abc import Callable

from collections import defaultdict

from asyncio import Lock, iscoroutinefunction

from uuid import uuid4
from time import time

import backoff
from frozenlist import FrozenList

from ipcs import Request, IpcsError

from ..rextlib.common.cacher import DictCache
from ..rextlib.common.json import dumps

from ..log import get_logger
from ..utils import frozenlist_default_of_dumps

from .error import BadRequestError

if TYPE_CHECKING:
    from .. import Core


LIFETIME = 30.


class UsedShardIdsCache(DictCache[str, FrozenList[int]]):
    """使われているかもしれないシャードのIDを格納するための辞書キャッシュの型。
    キーは署名で、値がシャードId達です。
    ここに入れられたシャードが寿命で死んだ時、`ShardState`の`not_used`にシャードのIDが移動します。"""

    def __init__(self, parent: ShardState, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.parent = parent

    async def _async_on_dead(self, k: str) -> None:
        # 死んだシャードを`not_used`に移動させる。
        async with self.parent as ctx:
            ctx.not_used.extend(ctx.used.pop(k))

    def on_dead(self, key: str, _) -> Any:
        self.parent.parent.server.loop.create_task(
            self._async_on_dead(key), name=
                "shard: pool: on dead shard"
        )

    def delete(self, key: str) -> None:
        # 死んだ際のコールバックを呼び出す。
        for callback in self.parent.dead_callbacks:
            callback(key, self[key])
        return super().delete(key)

DeadCallbacks: TypeAlias = set[Callable[[str, FrozenList[int]], Any]]
"シャードが死んだ際に呼ばれるコールバック関数の集合の型。"


class ShardStateContext(NamedTuple):
    "`ShardState`のシャード情報を一つにまとめるのに使うクラスです。"

    used: UsedShardIdsCache
    """使われたシャードが格納されるリストです。キーが署名で、値がシャード達です。
    もしハートビートがなくてシャードが死んだ場合、死んだシャードとなり`.not_used`に転送されます。"""
    not_used: list[int]
    "使われていないシャードのIDが格納されるリストです。"


class TemporaryShardStateContext(NamedTuple):
    """`ShardContainer`の一時的にしか使えないバージョンです。
    `ShardContainer`の`get_bypass`用。"""

    used: dict[str, FrozenList[int]]
    not_used: FrozenList[int]


class ShardState(Lock):
    """シャードの情報を安全に保管するための機能を実装したクラスです。
    このクラスは`asyncio.Lock`を継承しており、シャードの中身を操作する場合は、そのロックを獲得する必要があります。"""

    def __init__(
        self, parent: ShardPool, *args: Any,
        not_used: list[int] | None = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)

        self.parent = parent

        self.dead_callbacks = DeadCallbacks()
        "シャードが死んだ際に呼ばれる関数達です。"
        self.__body = ShardStateContext(
            self.parent.server.cacher.register(
                UsedShardIdsCache(self, LIFETIME)
            ), not_used or []
        )

    async def __aenter__(self) -> ShardStateContext:
        await super().__aenter__()
        return self.__body

    def get_bypass(self) -> TemporaryShardStateContext:
        """獲得をバイパスしてシャードID達を取得します。
        これで得たデータは、変更ができないまたは変更しても反映されません。
        また、常に最新の状態であると言う保証がありません。"""
        (ctx := TemporaryShardStateContext(
            {key: value for key, value in self.__body.used.items()},
            FrozenList(self.__body.not_used)
        )).not_used.freeze()
        return ctx

    def close(self) -> None:
        "お片付けをします。"
        self.parent.server.cacher.delete(self.__body.used)


class ShardPool:
    """シャードを管理するためのクラスです。
    ここに実装されている公開メソッドは、全てipcs経由でRTコネクション越しに実行が可能です。"""

    ROUTE_PREFIX = "shard.pool."

    @staticmethod
    def make_route(route_name: str) -> str:
        return f"{ShardPool.ROUTE_PREFIX}{route_name}"

    def __init__(self, server: Core, channel: str, shard_count: int) -> None:
        self.server, self.channel, self.shard_count = server, channel, shard_count
        self.logger = get_logger(f"{__name__}.{channel}")

        self._initialize_shards(shard_count)
        self.get_bypass = self.ids.get_bypass

        # インスタンスにある関数を全てipcsに登録する。
        for attr in dir(self):
            if attr in ("acquire", "get_bypass"):
                continue
            if callable(getattr(self, attr)) and not attr.startswith("_"):
                if iscoroutinefunction(getattr(self, attr)):
                    async def _route(_, *args, attr=attr, **kwargs):
                        return await getattr(self, attr)(*args, **kwargs)
                else:
                    _route = lambda _, *args, attr=attr, **kwargs: getattr \
                        (self, attr)(*args, **kwargs)
                self.server.set_route(_route, self.make_route(attr))

        @self.server.route(self.make_route("get"))
        async def get_bypass_for_ipcs(_) -> str:
            return dumps(self.get_bypass()._asdict(), default=frozenlist_default_of_dumps)

        @self.server.route(self.make_route("acquire"))
        async def acquire_wrapper_for_ipcs(
            _, *args: Any, **kwargs: Any
        ) -> tuple[str, tuple[int, ...]]:
            data = await self.acquire(*args, **kwargs)
            return data[0], tuple(data[1])

        # シャードが死んだ際のコールバックをipcs越しに設定できるようにする。
        self._route_dead_callbacks = defaultdict[str, set[str]](set)
        @self.server.route(self.make_route("add_dead_callback"))
        def add_dead_callback(request: Request, route_name: str) -> None:
            self._route_dead_callbacks[request.source.id_].add(route_name)
        @self.server.route(self.make_route("remove_dead_callback"))
        def remove_dead_callback(request: Request, route_name: str) -> None:
            self._route_dead_callbacks[request.source.id_].remove(route_name)

        # ipcs越しのコールバックを呼び出す。三回まで再試行する。
        @backoff.on_exception(backoff.expo, (IpcsError,), max_tries=3)
        async def call_dead_callback_of_route(
            id_: str, route_name: str,
            signature: str,
            shard_ids: FrozenList[int]
        ) -> None:
            await self.server.request(id_, route_name, signature, tuple(shard_ids))
        self._call_dead_callback_of_route = call_dead_callback_of_route

        @self.server.listen()
        def on_disconnect(id_: str) -> None:
            # もしクライアントが切断したのなら、そのクライアントのコールバックを消す。
            if id_ in self._route_dead_callbacks:
                del self._route_dead_callbacks[id_]

    def _on_dead(self, signature: str, shard_ids: FrozenList[int]) -> None:
        # シャードが死んだのなら、ipcs越しのコールバックを呼び出す。
        for id_, route_callback_names in self._route_dead_callbacks.items():
            for rcn in route_callback_names:
                self.server.loop.create_task(
                    self._call_dead_callback_of_route(
                        id_, rcn, signature, shard_ids
                    ), name="shard: pool: call dead callback of route"
                )

    def _initialize_shards(self, shard_count: int) -> None:
        if hasattr(self, "ids"):
            self.ids.close()
        self.ids = ShardState(self, not_used=list(range(shard_count)))
        self.ids.dead_callbacks.add(self._on_dead)

    def reset(self, shard_count: int) -> None:
        "シャードプールのシャード情報を初期化します。"
        self._initialize_shards(shard_count)

    @property
    def signature(self) -> str:
        "署名を作ります。"
        return f"{self.channel}_{uuid4()}_{time()}"

    async def acquire(self, count: int) -> tuple[str, FrozenList[int]]:
        """引数`count`分できるだけシャードの獲得を行います。
        返り値は、ハートビートなどに使う署名と獲得したシャード達の二つのタプルです。"""
        async with self.ids as ctx:
            if not ctx.not_used:
                raise BadRequestError("シャードがもうないです。")

            # できるだけ獲得を行う。
            print(ctx)
            ctx.used[signature := self.signature] = \
                FrozenList(ctx.not_used[:count])
            ctx.used[signature].freeze()
            del ctx.not_used[:count]

            return signature, ctx.used[signature]

    def assert_signature_exists(self, ctx: ShardStateContext, signature: str) -> None:
        "署名が存在するかのアセーションします。"
        if signature not in ctx.used:
            raise BadRequestError("その署名は存在しません。")

    async def release(self, signature: str) -> None:
        "シャードの解放を行います。"
        async with self.ids as ctx:
            self.assert_signature_exists(ctx, signature)
            # 解放するシャードを`not_used`に移動する。
            ctx.not_used.extend(ctx.used.pop(signature))

    async def process_heartbeat(self, signature: str) -> None:
        """ハートビートの処理をします。
        具体的には、指定された署名のデータの寿命を伸ばします。
        この関数は30秒毎に実行されなければ、署名のデータが死んだものとみなされ、他のクライアントがデータを横取り可能な状態となります。
        もし署名のデータが死んだのなら、二重起動するのでそのデータで稼働しているBotを停止すべきです。"""
        async with self.ids as ctx:
            self.assert_signature_exists(ctx, signature)
            if ctx.used.data[signature].is_dead():
                raise BadRequestError("その署名のデータは死にました。")
            ctx.used.data[signature].update_deadline(LIFETIME)