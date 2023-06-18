__all__ = ("logger", "ipcs_logger")

from logging import getLogger, Logger

from ipcs import logger as ipcs_logger

from .rextlib.common.log import set_stream_handler
from .common.lib.log import set_file_handler


logger = getLogger("rt")
for l in (ipcs_logger, logger):
    set_stream_handler(l)
    set_file_handler(l, default="main.log")


def get_logger(name: str) -> Logger:
    "ロガーを取得します。"
    return getLogger(f"rt.{name}")