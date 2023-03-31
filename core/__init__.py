"RT - Core"

from __future__ import annotations

__all__ = ("Core", "logger")

from typing import TYPE_CHECKING, Any

from ipcs import Server
from ipcs.utils import SimpleAttrDict

from .rextlib.common.cacher import Cacher
from .rextlib.common.chiper import ChiperManager

from .common.lib.backend import is_bot

from .log import get_logger
from .shard import ShardPool

if TYPE_CHECKING:
    from websockets.datastructures import Headers


logger = get_logger("rt.core")


class Core(Server):
    "ビーコンの心臓部です。"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        with open("secret.key", "rb") as f:
            self.chiper = ChiperManager(f.read())

        self.cacher = Cacher()
        self.cacher.start()

        self.shards = SimpleAttrDict[ShardPool]()
        self.set_route(self._setup_shard_pool, "setup_shard_pool")

    async def _setup_shard_pool(self, _, channel: str, shard_count: int) -> None:
        self.shards[channel] = ShardPool(self, channel, shard_count)

    async def _process_request(self, _, headers: Headers) -> ...:
        # WebSocketへの接続リクエストを検証する。
        if "Authorization" not in headers or \
                not is_bot(self.chiper, headers["Authorization"]):
            logger.info("無効なリクエストを拒否しました。")
            logger.debug("拒否されたリクエストのヘッダ：%s", headers)
            return (401, (), bytes())

    def run(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("process_request", self._process_request)
        return super().run(*args, **kwargs)

    async def close(self, *args: Any, **kwargs: Any) -> None:
        logger.info("終了中...")
        return await super().close(*args, **kwargs)

    def sync_close(self) -> None:
        """ブロッキングする終了処理です。
        最後に呼ばれるべきです。"""
        logger.info("ブロッキングする終了処理をしています...")
        self.cacher.close()
        self.cacher.join()