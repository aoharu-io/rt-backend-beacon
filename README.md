RTのバックエンドのBotサーバーとAPIサーバーが通信をするために使うipcsサーバーです。

## 環境構築
1. サブモジュールの用意。
2. バージョンが3.11.xのPythonを用意。
3. 開発ツールryeで依存関係の用意。（`rye sync`）
4. リポジトリ`rt-{bot,api}`で使っている`secret.key`を、このリポジトリのルートディレクトリに配置。

## Usage
```shell
$ rye run python3 .
```