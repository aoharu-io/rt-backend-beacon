"RT - Utils"

__all__ = ("frozenlist_default_of_dumps",)

from typing import Any

from frozenlist import FrozenList

from .rextlib.common.json import dumps


def frozenlist_default_of_dumps(obj: Any) -> tuple:
    """frozenlistの`FrozenList`をその`orjson.dumps`で使えるようにするための関数です。
    その`dumps`の引数`default`に渡して使います。"""
    if isinstance(obj, FrozenList):
        return tuple(obj)
    raise TypeError