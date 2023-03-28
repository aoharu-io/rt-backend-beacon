"RT - Beacon (Ipcs Server)"

from typing import Any

from argparse import ArgumentParser

from ipcs import Server, logger

from websockets.datastructures import Headers

from core.rextlib.common.chiper import ChiperManager
from core.rextlib.common.log import set_stream_handler

from common.lib.log import set_output_handler
from common.lib.backend import IPCS_SERVER_ID, is_bot


parser = ArgumentParser(
    prog="RT Discord Botのためのビーコンの実装",
    description="バックエンドのAPI実装およびBotクライアント実装の通信に必要なサーバーがこれです。"
)

parser.add_argument("-H", "--host", default="127.0.0.1", help="提供対象のホスト名です。")
parser.add_argument("-p", "--port", type=int, default=8765, help="使うポートです。")

args = parser.parse_args()


set_stream_handler(logger)
set_output_handler(logger, default="log/ipcs.log")
logger.info("RT Discord Bot （ビーコンの実装） が起動中...")


with open("secret.key", "rb") as f:
    chiper = ChiperManager(f.read())


server = Server(IPCS_SERVER_ID)


data, Undefined = dict[str, Any](), type("Undefined", (), {})
@server.route("data")
def shared_data(_, attr: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(data, attr)(*args, **kwargs)


async def _process_request(headers: Headers) -> ...:
    if "Authorization" not in headers or \
            not is_bot(chiper, headers["Authorization"]):
        logger.info("無効なリクエストを拒否しました。")
        logger.debug("拒否されたリクエストのヘッダ：%s", headers)
        return (401, (), bytes())


logger.info("提供を開始しました。")
server.run(
    args.host, args.port,
    process_request=_process_request
)