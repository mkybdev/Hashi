# Hashi 開発ガイド

フロントエンドはbun、バックエンドはuvで依存関係と実行環境を管理します。

## プロジェクト構成

```text
Hashi/
├── bun.lock                  # フロントエンドの依存関係を固定
├── package.json              # bunワークスペースと共通コマンド
├── packages/
│   ├── frontend/             # React + Vite + TypeScript
│   └── backend/              # FastAPI + Python 3.11
│       ├── .python-version   # uvで使用するPythonバージョン
│       ├── pyproject.toml    # Python依存関係の定義
│       └── uv.lock           # バックエンドの依存関係を固定
├── docker-compose.yml        # Docker開発環境
└── firebase.json             # Firebase Hosting設定
```

## 前提条件

- **bun**: 1.3.9（ルートの`packageManager`で指定）
- **uv**: 0.9.16以上（Dockerイメージでは0.9.16に固定）
- **Python**: 3.11（未インストールの場合はuvが取得）
- **Docker / Docker Compose**: Dockerでバックエンドを動かす場合に必要
- **Firebase CLI / Google Cloud CLI**: デプロイ時に必要

`tdmelodic`が使用するChainerとの互換性のため、Pythonは3.10〜3.11、NumPyは2.0未満に制限しています。Chainerのビルドと実行時には`setuptools<60`を使用します。

## 初回セットアップ

以下はリポジトリのルートで実行します。

```bash
git submodule update --init --recursive

# フロントエンド
bun install --frozen-lockfile

# バックエンド（.venvはuvが作成）
cd packages/backend
uv sync --locked

# UniDicの辞書データを初回のみダウンロード
uv run python -m unidic download
cd ../..
```

仮想環境の手動作成やactivateは不要です。MeCabや推論ライブラリのローカル環境への導入が難しい場合は、後述のDockerを使用してください。

## 開発サーバー

別々のターミナルで、リポジトリのルートから実行します。

```bash
# フロントエンド: http://localhost:5173
bun run dev:frontend
```

```bash
# バックエンド: http://localhost:8000
bun run dev:backend
```

各ディレクトリから直接起動する場合は、フロントエンドで`bun run --bun dev`、バックエンドで`uv run uvicorn main:app --reload`を使用します。ルートのフロントエンド用スクリプトも`--bun`を指定し、ViteやTypeScriptをbunで実行します。

バックエンドを起動する前に`lsof -i :8000`などで既存サーバーを確認し、動作中ならそのインスタンスを使用してください。タスク用に起動したサーバーは終了時に停止してください。

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Dockerでバックエンドを起動

リポジトリのルートで実行します。イメージ内でもuvと`uv.lock`を使用し、UniDicの辞書をダウンロードします。

```bash
# 初回または依存関係・Dockerfileを変更した場合
docker compose up --build backend

# 2回目以降
docker compose up backend

# 終了
docker compose down
```

Docker Composeが単独コマンドとしてインストールされている環境では、`docker compose`を`docker-compose`に置き換えてください。仮想環境はコンテナ内の`/opt/venv`に置き、ソースコードのバインドマウントから独立させています。

## ビルドと検証

リポジトリのルートで実行します。

```bash
bun run build:frontend
bun run lint
```

ビルド成果物は`packages/frontend/dist`に出力されます。

## 依存関係の変更

```bash
# フロントエンド（リポジトリのルートから）
bun add --cwd packages/frontend <package>
bun add --cwd packages/frontend --dev <package>

# バックエンド
cd packages/backend
uv add <package>
uv add --dev <package>
```

変更した依存定義とロックファイルを一緒にコミットしてください。フロントエンドはルートの`bun.lock`、バックエンドは`packages/backend/uv.lock`を使用します。

## デプロイ

### バックエンド（Google Cloud Run）

```bash
cd packages/backend
export PROJECT_ID=<your-gcp-project-id>

gcloud builds submit --tag gcr.io/${PROJECT_ID}/hashi-backend
gcloud run deploy hashi-backend \
  --image gcr.io/${PROJECT_ID}/hashi-backend \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

Dockerfileは`uv sync --locked --no-dev`で依存関係をインストールします。`uv.lock`もビルド対象に含めてください。

### フロントエンド（Firebase Hosting）

リポジトリのルートで実行します。

```bash
bun install --frozen-lockfile
bun run build:frontend
firebase deploy --only hosting
```

## トラブルシューティング

### Pythonバージョンや依存関係が合わない

`packages/backend`で`uv sync --locked`を実行してください。uvは`.python-version`を参照し、`.venv`を作成・同期します。旧環境の`venv`をactivateしている場合は、先に`deactivate`してください。

### フロントエンドの依存関係が合わない

リポジトリのルートで`bun install --frozen-lockfile`を実行してください。再インストールが必要な場合は`node_modules`を削除して同じコマンドを実行します。`bun.lock`は保持してください。

### Dockerの依存関係が更新されない

`docker compose up --build backend`でイメージを再ビルドしてください。
