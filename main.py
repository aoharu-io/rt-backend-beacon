"RT - Beacon (Ipcs Server)"

from typing import Any

from argparse import ArgumentParser

from core.common.lib.backend import IPCS_SERVER_ID

from core import Core
from core.log import logger


parser = ArgumentParser(
    prog="RT Discord Botのためのビーコンの実装",
    description="バックエンドのAPI実装およびBotクライアント実装の通信に必要なサーバーがこれです。"
)

parser.add_argument("-H", "--host", default="127.0.0.1", help="提供対象のホスト名です。")
parser.add_argument("-p", "--port", type=int, default=8765, help="使うポートです。")

args = parser.parse_args()


logger.info("RT Discord Bot （ビーコンの実装） が起動中...")


server = Core(IPCS_SERVER_ID)


data = dict[str, Any]()
@server.route("data")
def shared_data(_, attr: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(data, attr)(*args, **kwargs)



logger.info("提供を開始しました。")
server.run(args.host, args.port)
server.sync_close()