# プロジェクト概要: 日本語アクセントゲーム（8-bit）

お題の単語と同じピッチアクセントを持つ単語を当てるWebゲームです。

## 技術スタック

- **モノレポ**: フロントエンドはbunワークスペース、バックエンドは独立したuvプロジェクトとして管理。
- **フロントエンド**:
  - **フレームワーク**: Vite + React
  - **ホスティング**: Firebase Hosting
  - **UIライブラリ**: `TheOrcDev/8bitcn-ui`（Shadcn/uiベースの8-bitスタイル）
  - **ツールチェーン**: bun（依存管理・スクリプト実行）
- **バックエンド**:
  - **Python**: 3.11（対応範囲は3.10〜3.11）
  - **ツールチェーン**: uv（Python・仮想環境・依存関係・実行を管理）
  - **フレームワーク**: FastAPI
  - **推論**: `PKSHATechnology-Research/tdmelodic`（サブモジュール連携、辞書優先ロジック）
  - **形態素解析**: `sudachipy` + `UniDic`（特徴抽出用のカスタムmecabrc）
  - **インフラ**: Google Cloud Run
- **インフラ / DevOps**:
  - **プラットフォーム**: GCP
  - **ゲートウェイ**: Firebase Hosting（Cloud Runへのリライト）

## モノレポ構成

```text
.
├── packages/
│   ├── frontend/       # Vite + Reactアプリ
│   └── backend/        # FastAPI + tdmelodicアプリ
│       ├── pyproject.toml
│       └── uv.lock
├── firebase.json       # Hosting設定とリライト
├── package.json        # bunワークスペースとルートスクリプト
└── bun.lock
```

## ゲームの仕組み

1. ランダムまたは日替わりで、お題の単語を表示します。
2. プレイヤーが日本語の単語（ひらがな・漢字）を入力します。
3. フロントエンドからバックエンドへ入力を送信し、`tdmelodic`で読みとアクセントを取得して、お題と比較します。
4. 正解時には8-bitの効果音・演出、不正解時にはアクセントの高低差を表示します。

## 開発環境

- **依存関係**: ルートで`bun install --frozen-lockfile`、`packages/backend`で`uv sync --locked`。
- **フロントエンド**: ルートで`bun run dev:frontend`、または`packages/frontend`で`bun run --bun dev`。
- **バックエンド**: ルートで`bun run dev:backend`、または`packages/backend`で`uv run uvicorn main:app --reload`。
- **辞書の初回取得**: `packages/backend`で`uv run python -m unidic download`。
- 詳細は[開発ガイド](DEVELOPMENT.md)を参照してください。

## エージェントへの指示

- **言語**: 回答とドキュメントは常に日本語を使用してください。
- **ツールチェーン**: バックエンドにはuv、フロントエンドにはbunを使用してください。依存関係の変更時には対応するロックファイルも更新してください。
- **バックエンド開発サーバーの管理**:
  - 起動前に、すでに開発サーバーが動作しているか確認してください。動作中なら既存インスタンスを使用してください。
  - 新しく起動する場合はタスクの実行中だけ動作させ、完了後に停止してください。
