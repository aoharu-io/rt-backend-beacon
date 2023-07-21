RTのバックエンドのBotサーバーとAPIサーバーが通信をするために使うipcsサーバーです。

## 環境構築
1. サブモジュールの用意。
2. バージョンが3.11.xのPythonを用意。
3. 開発ツールryeで依存関係の用意。（`rye sync`）
4. `rt-backend`から始まる名前のリポジトリで使っている`secret.key`をこのリポジトリのルートディレクトリに配置。

## Usage
```shell
$ rye run python3 .
```
