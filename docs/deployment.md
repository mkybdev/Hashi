# デプロイガイド

バックエンドはGoogle Cloud Run、フロントエンドはFirebase Hostingへデプロイします。基本手順は[開発ガイド](../DEVELOPMENT.md#デプロイ)を参照してください。

## バックエンド（Google Cloud Run）

Google Cloud CLIで認証した後、バックエンドのディレクトリで実行します。

```bash
cd packages/backend
gcloud run deploy hashi-backend \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2
```

Dockerfileを使用してビルドされます。Python 3.11とuvを使用し、`pyproject.toml`と`uv.lock`から`uv sync --locked --no-dev`で依存関係をインストールします。推論モデルや辞書を読み込むため、メモリは2Giを指定しています。事前に`git submodule update --init --recursive`でサブモジュールを取得してください。

## フロントエンド（Firebase Hosting）

リポジトリのルートで実行します。

```bash
bun install --frozen-lockfile
bun run build:frontend
firebase deploy --only hosting
```

`firebase.json`に従って`packages/frontend/dist`を配信し、`/api/**`をCloud Runへ転送します。

## Vercelで配信する場合

Vercelにリポジトリを接続し、以下を設定します。

- **Root Directory**: リポジトリのルート
- **Framework Preset**: Vite
- **Install Command**: `bun install --frozen-lockfile`
- **Build Command**: `bun run build:frontend`
- **Output Directory**: `packages/frontend/dist`
- **環境変数**: `VITE_API_URL`にCloud RunのURLと`/api`を指定（例: `https://hashi-backend-xyz123-an.a.run.app/api`）

ルートの`packageManager`と`bun.lock`で指定したbunと依存関係を使用してください。

## 動作確認

配信先でゲームを開き、ブラウザーのネットワークタブで`/api/target-word`へのリクエストを確認します。404が発生する場合は、`VITE_API_URL`末尾の`/api`またはFirebaseのリライト設定を確認してください。
