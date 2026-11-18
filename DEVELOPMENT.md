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

現在のバックエンドはGCPプロジェクト`hashi-game`のCloud Runサービス`backend`（`asia-northeast1`）です。更新は`packages/backend`で`gcloud run deploy backend --source . --project hashi-game --region asia-northeast1`を実行します。

Dockerfileは`uv sync --locked --no-dev`で依存関係をインストールします。`uv.lock`もビルド対象に含めてください。

### フロントエンド（Firebase Hosting）

リポジトリのルートで実行します。

```bash
bun install --frozen-lockfile
bun run build:frontend
firebase deploy --only hosting --project hashi-accent-game
```

## トラブルシューティング

### Pythonバージョンや依存関係が合わない

`packages/backend`で`uv sync --locked`を実行してください。uvは`.python-version`を参照し、`.venv`を作成・同期します。旧環境の`venv`をactivateしている場合は、先に`deactivate`してください。

### フロントエンドの依存関係が合わない

リポジトリのルートで`bun install --frozen-lockfile`を実行してください。再インストールが必要な場合は`node_modules`を削除して同じコマンドを実行します。`bun.lock`は保持してください。

### Dockerの依存関係が更新されない

`docker compose up --build backend`でイメージを再ビルドしてください。

## ゲームAPI

- `POST /api/game/target`: `difficulty`（`easy` / `normal` / `hard`）、`homophones`、`recent`（直近の正解の語彙キー）を指定して出題します。
- `POST /api/game/guess`: 上記設定に`target_id`と`text`を加えて、バックエンドで正解を判定します。
- お題はKanjium全体の表記・読みのエントリから、小説コーパスの使用頻度上位10,000表記に該当し、難易度の拍数と別の正解候補の存在を満たすものを選びます。回答はKanjium → UniDic → tdmelodicの順に解析します。辞書の複数の許容型を拍ごとの高低列へ変換し、いずれかの列全体が一致すれば正解にします。単語内の高低が同じ平板・尾高は一致扱いです。
- かな回答は読みから候補を検索します。同音語を許可しても、お題と同じ読みをかなだけで回答することはできません。表記で語を特定してください。
- 出題は別の正解候補があるものに限定します。エンドレスでは直近30正解の使い回しを防ぎます。
- スタート・遊び方・設定・プレイ・リザルト・ランキング案内の画面があります。マラソン・タイムアタック・エンドレスに対応しています。共有ランキングの保存は後続工程です。現在のAPIは練習用で、ランキング用のセッション管理は行いません。

判定の回帰テストはバックエンドのディレクトリで実行します。

```bash
uv run python -m unittest discover -s tests -v
```

### ゲーム開始時に「Not Found」が表示される

ローカル開発では`packages/frontend/.env`の`VITE_API_URL`を空にしてください。Viteのプロキシを通して`http://127.0.0.1:8000/api`に接続します。古いCloud RunのURLが入っていると、新しいゲームAPIが存在せず404になります。

本番用URLは`.env.production.local`に設定し、開発用の`.env`と分けてください。設定変更が反映されない場合はフロントエンドの開発サーバーを再起動します。


## アクセント辞書と回答の解析

Kanjiumは`packages/backend/vendor/kanjium`のGitサブモジュールです。`git submodule update --init --recursive`で取得してください。アクセントと頻度データは`data/source_files/raw/accents.txt`と`novels_freq.txt`を直接参照します。親リポジトリでコミットを固定しており、実行時のダウンロードは不要です。出典・帰属・利用条件は`packages/backend/KANJIUM.md`と上流の`LICENSE.txt`を参照してください。Dockerビルド前にもサブモジュールを取得してください。

回答のアクセント位置は次の順で取得します。

1. Kanjium: 表記と読みを照合し、収録された複数アクセントを許容。
2. UniDic: Kanjiumにない語はMeCabの単語エントリのアクセント情報を参照。
3. tdmelodic: 両方でアクセントを確認できない語は推定。最初の下降に丸めず、途中の上昇・下降をすべて使って高低列を復元。単語の外側に当たる語末直後の下降は比較しません。

漢字の多読語は形態素解析の通常の読みを優先します。かな入力はKanjiumの読み索引を利用します。推定は語の実在性を保証しません。回答は推定も受け付け、画面で参照元と推定であることを表示します。文章、空入力、読みを取得できない入力はエラーにします。

手作業の身近な語リストや旧候補DBで制限せず、Kanjiumの各表記・読みを候補とし、難易度（2〜3拍 / 4〜5拍 / 6〜8拍）、直近の正解履歴、別の正解候補の存在を考慮します。


Kanjiumには、かな表記の読みを空欄で省略したレコードがあります（例: セピア、サーバー）。この場合は表記を読みとして補完します。有効なアクセント解析結果が得られない場合は、レコードの有無だけで処理を終了せず、次の取得元へ進みます。tdmelodic自体の推定例外はログに残し、APIでは422で入力し直せるエラーを返します。読み取得不能などの入力エラー（400）と、推定成功後のアクセント不一致は別の結果です。


### お題の使用頻度

Kanjium同梱の`novels_freq.txt`を使用し、出現回数上位10,000表記に絞って出題します。さらに出現回数の平方根を抽選の重みにして、よく出る語を優先しつつ語彙の幅を確保します。同じ表記に複数の読みがある場合は、その表記の重みを分配します。閾値は`game.py`の`MAX_TARGET_FREQUENCY_RANK`で調整できます。頻度未収録・低頻度の語を回答することは引き続き可能です。小説由来なので、会話での一般性や各読みの一般性とは一致しない場合があります。


## 高低のリズムによる正解判定

比較対象は同じ拍数の単語の内部にある高低列全体です。`pitch_patterns`は許容される列の一覧（1=低、2=高）、`accent_pattern`は表示用の列です。正解時は実際に一致した列を回答・お題双方の表示用列に設定します。辞書の`accents`は核位置の原情報として残し、判定には使いません。推定語は核位置に丸められないので`accents`を空にします。

例: 「橋（ハシ）」と「端（ハシ）」はどちらも`[1,2]`なので、同音異義語を許可すれば正解です。同音語の許可、同一語の禁止、直近の回答の使い回し制限は別のルールとして適用します。`[1,2,1,2,1]`と`[1,2,1,1,1]`は先頭の下降が一致しても不正解です。

tdmelodicが省略する冒頭の通常の上昇を復元し、それ以降のすべての上昇・下降を高低列に反映します。複数句や長い複合語の推定精度を保証するものではありません。通常の辞書単語は核位置から復元できる高低列を使用します。


## ゲームモードと計時

- マラソン: 30 / 60 / 120秒（既定60秒）で正解数を記録。残り時間0で結果画面へ移動します。
- タイムアタック: 5 / 10 / 20問（既定10問）を正解するまでの入力可能時間を記録。目標達成時は計時を停止して最後の回答詳細を表示し、「結果を見る」を押すと結果画面へ移動します。
- エンドレス: 終了条件なし。任意に結果を確認できます。

計時はフロントエンドの`GameEngine`で管理し、`performance.now()`で入力可能な時間を積算します。初回・次問の取得、回答判定の通信待ち、正解後に「次のお題へ」を押すまでの待機を含めません。不正解や回答通信失敗後は同じお題で計時を再開し、スキップは正解数に含めません。出題通信が失敗した場合は、お題を再取得するまで停止します。リクエストは15秒でタイムアウトします。バックグラウンド中の入力可能時間も経過扱いです。

送信時刻が期限より前の回答は、応答が遅れても判定します。期限ちょうど以降の送信は受け付けません。連打や終了後の古い応答による二重加算を防ぎます。途中終了では目標達成と区別した結果を表示します。計時モードの正解語はプレイ中の使い回しを禁止し、エンドレスは直近30語を対象にします。APIの履歴上限は1,000語です。

この計時は端末内のプレイ用です。共有ランキング向けの正式記録・サーバーでのセッション管理は次の工程で実装します。

ゲーム進行のテスト（通信と時計を差し替えて、実時間を待たずに境界条件を確認）:

```bash
cd packages/frontend
bun run test
```


## 本番の接続先とビルド

Firebase Hostingは`hashi-accent-game`、Cloud Runは`hashi-game`の別プロジェクトです。本番フロントエンドは`packages/frontend/.env.production`に設定したCloud Runの`/api`へ直接アクセスします。Hostingの設定はSPA用のリライトのみです。ローカル開発では従来どおりViteの`/api`プロキシを使います。

`bun run build:frontend`は子プロセスの`NODE_ENV=production`を明示して、bunとViteの両方に本番用環境ファイルを選択させます。これにより、開発用`.env`の空の`VITE_API_URL`で本番用URLが上書きされることを防ぎます。バックエンドのソースデプロイでは`.gcloudignore`を使用し、仮想環境を除外しつつKanjiumのデータ・Dockerfile・DBを含めます。
