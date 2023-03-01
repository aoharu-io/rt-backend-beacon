# rt-beacon
RTのバックエンドのBotサーバーとAPIサーバーが通信をするために使うipcsサーバーです。

## Set up
1. バージョンが3.11.xのPythonを用意。
2. サブモジュールを初期化。（例：`git submodule update --init`）
3. サブモジュールのrextlibが依存しているライブラリのインストール。（そのライブラリは、`core/rextlib/requirements.txt`にまとめられています。）
  例：`pip3 install -U -r core/rextlib/requirements.txt`
4. リポジトリrt-backend-botとrt-backend-apiで使っている`secret.key`を、このリポジトリのルートディレクトリに配置。

## Usage
### Normal
```shell
$ python3 main.py 127.0.0.1 8765
```
### Docker
Coming soon...