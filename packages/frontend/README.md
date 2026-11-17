# Hashi フロントエンド

React + TypeScript + Viteを使用しています。依存管理とスクリプト実行にはbunを使用します。

リポジトリのルートで実行してください。

```bash
bun install --frozen-lockfile
bun run dev:frontend
bun run build:frontend
bun run lint
```

このディレクトリから直接実行する場合は`bun run --bun dev`、`bun run --bun build`、`bun run --bun lint`を使用します。依存関係はルートの`bun.lock`で管理します。

開発サーバーは`http://localhost:5173`で起動し、`/api`へのリクエストをバックエンドの`http://127.0.0.1:8000`へ転送します。

バックエンドのセットアップとデプロイ手順は[開発ガイド](../../DEVELOPMENT.md)を参照してください。
