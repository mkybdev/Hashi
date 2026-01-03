# 実装計画書: 日本語アクセント 8bit ゲーム

## 1. プロジェクト概要
日本語の単語の発音アクセントを利用したゲームを作成します。
ユーザーはターゲット単語と同じアクセントを持つ単語を入力し、正解を目指します。
デザインは 8bit 調で統一し、モダンな Web 技術（Vite, Bun, Firebase, GCP）を使用します。

## 2. アーキテクチャ構成
- **リポジトリ**: Monorepo (Bun Workspaces)
- **インフラ**: Google Cloud Platform (Free Tier ベース)
    - **Frontend**: Firebase Hosting
    - **Backend**: Cloud Run (Python, Dockerized)
- **コアライブラリ**:
    - Frontend: React, Vite, TheOrcDev/8bitcn-ui (Desgin), TailwindCSS
    - Backend: FastAPI, sudachipy, tdmelodic

## 3. 実装ステップ

### Phase 1: プロジェクト初期化と環境構築
- [ ] **Monorepo セットアップ**:
    - ルート `package.json` の作成 (Bun Workspaces 設定)。
    - `.gitignore` の整備 (Python, Node, macOS 用)。
- [ ] **パッケージディレクトリ作成**:
    - `packages/frontend`: Vite (React + TypeScript) で初期化。
    - `packages/backend`: Python プロジェクトとして初期化 (`pyproject.toml` または `requirements.txt`).

### Phase 2: バックエンド実装 (Python/FastAPI)
- [ ] **環境構築**:
    - Python 3.10+ 環境の用意。
    - 必要ライブラリのインストール (`fastapi`, `uvicorn`, `tdmelodic`, `sudachipy`, `sudachipy-dictionaries-small`).
- [ ] **アクセント解析ロジック実装**:
    - `tdmelodic` を利用して、入力されたテキスト（漢字・仮名）からアクセント核の位置と読み仮名を取得する関数を作成。
    - ※ `tdmelodic` のモデル読み込みは起動時に行い、コールドスタート対策を意識する。
- [ ] **API エンドポイント作成**:
    - `POST /analyze`: `{ text: string }` を受け取り、`{ reading: string, accent_pattern: number[] }` を返す。
- [ ] **動作確認**:
    - ローカルでの API 確認。

### Phase 3: フロントエンド実装 (Vite + React)
- [ ] **基本セットアップ**:
    - TailwindCSS の導入。
    - `TheOrcDev/8bitcn-ui` の導入（コンポーネントのコピーまたはインストール）。
    - 8bit フォント（`PixelMplus` や `DotGothic16` など）の選定と導入。
- [ ] **ゲームロジック実装**:
    - **ターゲット単語の選定**: 予め用意した単語リストからランダムに、または日替わりで選択するロジック。
    - **入力フォーム**: ユーザーが単語を入力する UI。
    - **判定処理**: 入力単語をバックエンドに送信し、返ってきたアクセントパターンとターゲットを比較。
- [ ] **UI デザイン**:
    - 8bit 調のコンテナ、ボタン、入力フォームのスタイル適用。
    - 結果表示（正解・不正解）のアニメーションや演出。

### Phase 4: インフラとデプロイ
- [ ] **Backend Docker化**:
    - `packages/backend/Dockerfile` の作成。
    - 軽量な Python イメージを使用。
- [ ] **GCP / Firebase 設定**:
    - GCP プロジェクトの作成（または既存使用）。
    - Firebase プロジェクトの初期化。
    - `firebase.json` の設定:
        - Hosting の設定。
        - `/api/**` へのリクエストを Cloud Run サービスへ Rewrite する設定。
- [ ] **デプロイ**:
    - Backend: `gcloud run deploy`
    - Frontend: `firebase deploy --only hosting`

## 4. リスクと対策
- **tdmelodic のメモリ・速度**:
    - `tdmelodic` は深層学習モデルを使用するため、Cloud Run のメモリ制限やコールドスタート時間に注意が必要。
    - **対策**: 必要であれば軽量な辞書ベースのアプローチ（`py-accent`など）への切り替えや、推論結果のキャッシュを検討。まずは `tdmelodic` で進める。
- **8bitcn-ui の整合性**:
    - 開発途中のライブラリである可能性がある。
    - **対策**: 必要に応じて `shadcn/ui` の標準コンポーネントを独自にスタイルカスタマイズする方針に切り替える。
