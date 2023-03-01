"RT - Beacon (Ipcs Server)"

from typing import Any

from sys import argv

from ipcs import Server, logger

from websockets.datastructures import Headers

from core.rextlib.common.chiper import ChiperManager
from core.rextlib.common.log import set_stream_handler

from common.lib.log import set_output_handler
from common.lib.backend import IPCS_SERVER_ID, is_bot


set_stream_handler(logger)
set_output_handler(logger, default="log/ipcs.log")

with open("secret.key", "rb") as f:
    chiper = ChiperManager(f.read())


server = Server(IPCS_SERVER_ID)


data, Undefined = dict[str, Any](), type("Undefined", (), {})
@server.route("data")
def shared_data(_, attr: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(data, attr)(*args, **kwargs)


async def _process_request(_, headers: Headers) -> ...:
    if "Authorization" not in headers or \
            not is_bot(chiper, headers["Authorization"]):
        logger.info("Kicked invalid request.")
        return (401, (), bytes())


logger.info(f"Host: {argv[1]}, Port: {argv[2]}")
server.run(
    argv[1], int(argv[2]),
    process_request=_process_request
)