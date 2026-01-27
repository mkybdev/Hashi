# Hashi 開発ガイド

Hashiプロジェクトの開発環境セットアップから、ローカル開発、デプロイまでの最小限の手順を説明します。

## 📋 目次

- [プロジェクト構成](#プロジェクト構成)
- [前提条件](#前提条件)
- [開発開始](#開発開始)
- [デプロイ](#デプロイ)
- [トラブルシューティング](#トラブルシューティング)

## 📁 プロジェクト構成

モノレポ構成で、フロントエンド（React + Vite）とバックエンド（FastAPI）を含みます。

```
Hashi/
├── packages/
│   ├── frontend/          # React + Vite + TypeScript
│   └── backend/           # FastAPI + Python 3.9
├── docker-compose.yml     # Docker開発環境
└── firebase.json          # Firebase Hosting設定
```

## ✅ 前提条件

- **Node.js**: v18以上
- **npm**: v9以上
- **Docker**: 最新版
- **Firebase CLI**: デプロイ時に必要
- **Google Cloud CLI**: バックエンドデプロイ時に必要

```bash
# インストール確認
node --version
npm --version
docker --version
```

## 🚀 開発開始

### 1. 依存関係のインストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd Hashi

# フロントエンドの依存関係をインストール
npm install
```

### 2. 開発サーバーの起動

#### フロントエンド

```bash
npm run dev:frontend
```

`http://localhost:5173` で起動します。

#### バックエンド（Docker使用 - 推奨）

```bash
# 初回またはDockerfileを変更した場合
docker-compose up --build backend

# 2回目以降
docker-compose up backend
```

`http://localhost:8000` で起動します。

#### API ドキュメント

バックエンド起動後、以下のURLでAPIドキュメントにアクセスできます:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🚢 デプロイ

### バックエンドのデプロイ（Google Cloud Run）

```bash
cd packages/backend

# プロジェクトIDを設定
export PROJECT_ID=<your-gcp-project-id>

# Dockerイメージをビルドしてデプロイ
gcloud builds submit --tag gcr.io/${PROJECT_ID}/hashi-backend
gcloud run deploy hashi-backend \
  --image gcr.io/${PROJECT_ID}/hashi-backend \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

### フロントエンドのデプロイ（Firebase Hosting）

```bash
# フロントエンドをビルド
npm run build:frontend

# Firebaseにデプロイ
firebase deploy --only hosting
```

## 🔧 トラブルシューティング

### Docker ビルドエラー

Dockerイメージのビルドに失敗する場合:

```bash
# Dockerキャッシュをクリア
docker-compose down
docker system prune -a

# 再ビルド
docker-compose up --build backend
```

### ポートが既に使用されている

```bash
# 使用中のポートを確認
lsof -i :8000  # バックエンド
lsof -i :5173  # フロントエンド

# プロセスを停止
kill -9 <PID>
```

### フロントエンドの依存関係エラー

```bash
# node_modulesを削除して再インストール
rm -rf node_modules package-lock.json
npm install
```

## 📝 補足情報

### ローカルPython環境での開発（非推奨）

Dockerを使わずにローカルPython環境で開発する場合は、Python 3.9-3.11が必要です。Python 3.13以降は`tdmelodic`との互換性問題があります。

```bash
cd packages/backend

# Python 3.9で仮想環境を作成
python3.9 -m venv venv
source venv/bin/activate

# 依存関係をインストール
pip install "setuptools<60" wheel
pip install -r requirements.txt
python -m unidic download

# バックエンドを起動
uvicorn main:app --reload
```

### Git サブモジュール

このプロジェクトはGitサブモジュールを使用しています:

```bash
git submodule update --init --recursive
```

## 📚 参考リンク

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Firebase Hosting Documentation](https://firebase.google.com/docs/hosting)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
