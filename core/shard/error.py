"RT Shard - Error"

__all__ = ("LibShardError", "UnavaliableError", "BadRequestError", "UNAVALIABLE")


class LibShardError(Exception):
    "シャードライブラリで起きたエラーの基底となるエラーです。"


class UnavaliableError(LibShardError):
    "まだシャードが準備できてない際に発生するエラーです。"
class BadRequestError(LibShardError):
    "無理なリクエストを要求された際に発生するエラーです。"


UNAVALIABLE = UnavaliableError("シャード管理がまだ準備できてません。")
"まだシャードが準備できていないことを示すエラーの定数です。"