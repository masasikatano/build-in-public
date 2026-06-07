# Build in Public Assistant

自分のX（Twitter）アカウントをBuild in Publicに変えるための、週次レポート・ポスト生成支援CLIツール。

制作中のサイトの分析データ（Google Analytics 4）を自動取得し、indie hackerのBuild in PublicのプロであるPieter Levels（@levelsio）の文体を参考に、Xへのポスト案をLLMで生成します。

---

## プロジェクト構成

```
build-in-public/
├── src/build_in_public/       # メインソースコード
│   ├── __main__.py             # python -m build_in_public エントリポイント
│   ├── cli.py                  # コマンドライン引数処理
│   ├── config.py               # 設定ファイル読み込み
│   ├── analytics/
│   │   └── ga4.py              # GA4 Data API クライアント
│   ├── llm/
│   │   ├── client.py           # OpenRouter API クライアント
│   │   └── prompt_builder.py   # プロンプト構築
│   ├── utils/
│   │   ├── archive_manager.py  # データアーカイブ管理
│   │   └── date_helpers.py     # 日付・週計算
│   └── writers/
│       └── markdown_writer.py  # Markdownレポート生成
├── prompts/                    # LLMプロンプトテンプレート
├── examples/                   # Few-shot例文
├── posts/                      # 生成されたレポート（Git管理）
├── data/archive/               # 週次データのJSON保存
├── credentials/                # サービスアカウントJSON（.gitignore）
├── config.yaml                 # サイト設定
├── .env                        # 環境変数（.gitignore）
├── .env.example                # 環境変数テンプレート
└── pyproject.toml              # 依存関係管理
```

---

## ローカル環境での実行方法

### 1. 前提条件

- Python 3.11+
- [OpenRouter](https://openrouter.ai/) の API キー
- Google Cloud プロジェクト（GA4 API 有効化済み）

### 2. インストール

```bash
# リポジトリに移動
cd build-in-public

# 仮想環境を作成（推奨）
python3 -m venv .venv
source .venv/bin/activate

# 依存関係をインストール
pip install -e .
```

### 3. 設定ファイルの編集

#### `config.yaml`

自分のサイト情報に書き換えます。

```yaml
site_name: "MySite"
site_url: "https://example.com"  # サイトURL（ポストに含まれる）
ga4_property_id: "123456789"     # GA4 プロパティID
language: "ja"
default_tone: "levelsio"
posts_dir: "posts"
archive_dir: "data/archive"
examples_file: "examples/post_examples.md"
prompts_dir: "prompts"
```

#### `.env`

`.env.example` をコピーして編集します。

```bash
cp .env.example .env
```

```bash
# Google Auth
GOOGLE_CREDENTIALS_PATH=credentials/service-account.json

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
LLM_PROVIDER=openrouter
LLM_MODEL=anthropic/claude-3.5-sonnet

# Optional: Discord通知
# DISCORD_WEBHOOK_URL=
```

### 4. Google 認証情報の準備

#### 4.1 Google Cloud プロジェクトを作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 画面上部のプロジェクト選択メニューから **「新しいプロジェクト」** をクリック
3. プロジェクト名を入力し、**「作成」** をクリック

#### 4.2 API を有効化

1. ナビゲーションメニュー（≡）→ **「APIとサービス」** → **「ライブラリ」**
2. **Google Analytics Data API** を検索して **「有効にする」** をクリック

#### 4.3 サービスアカウントを作成

1. ナビゲーションメニュー → **「IAMと管理」** → **「サービスアカウント」**
2. **「サービスアカウントを作成」** をクリック
3. **ステップ1**: サービスアカウント名を入力（例: `build-in-public`）
   - サービスアカウントIDが自動生成されます
   - **「作成して続行」** をクリック
4. **ステップ2**: ロールの付与は不要なので **「完了」** をクリック

#### 4.4 JSON キーを作成・ダウンロード

1. 作成したサービスアカウントをクリック
2. **「キー」** タブを選択
3. **「鍵を追加」** → **「新しい鍵を作成」**
4. **JSON** を選択し、**「作成」** をクリック
5. 自動的に `.json` ファイルがダウンロードされます
6. ダウンロードしたJSONをプロジェクトに配置:

```bash
cp ~/Downloads/build-in-public-xxxxxxxx.json credentials/service-account.json
```

#### 4.5 GA4 に権限を付与

> [!IMPORTANT]
> 現在、GA4の管理画面（UI）から直接サービスアカウントのメールアドレス（`@*.iam.gserviceaccount.com`）を追加しようとすると、エラーが発生して追加できない不具合があります。そのため、以下の通り **Google Analytics Admin API Explorer** を使用して権限を付与します。

1. [Google Analytics Admin API Explorer (properties.accessBindings.create)](https://developers.google.com/analytics/devguides/config/admin/v1/rest/v1alpha/properties.accessBindings/create) にアクセス
2. 画面右側の **「Try this API」** 枠内にパラメータを入力:
   - `**parent`**: `properties/【あなたのGA4プロパティID】` (例: `properties/123456789`)
3. **Request body** のJSON入力欄（またはフィールド）を以下の通りに編集:
   ```json
   {
     "user": "【あなたのサービスアカウントのメールアドレス】",
     "roles": [
       "predefinedRoles/viewer"
     ]
   }
   ```
4. **「Google OAuth 2.0」** にチェックが入っていることを確認し、**「Execute」** ボタンをクリック
5. 対象のGA4プロパティの「管理者」権限を持つGoogleアカウントでサインインし、アクセスを許可
6. Responseコードが `200`（成功）となることを確認

### 5. 実行

```bash
# 先週のレポートを生成（デフォルト）
python3 -m build_in_public generate

# 特定の週を指定
python3 -m build_in_public generate --week 2026-W23

# 特定の日付（その週の月曜〜日曜を対象）
python3 -m build_in_public generate --date 2026-06-01

# 既存ファイルを強制上書き
python3 -m build_in_public generate --force
```

> `build-in-public generate` としても実行できます（`pyproject.toml` でエイリアス登録済み）。

### 6. 出力結果

実行後、以下が生成されます:

- `posts/YYYY-MM-DD.md` — レポート（Xポスト案3パターン含む）
- `data/archive/YYYY-MM-DD.json` — 生データのアーカイブ

### トラブルシューティング

| エラー | 対処法 |
|---|---|
| `Config Error: config.yaml not found` | リポジトリのルートに `config.yaml` があるか確認 |
| `Config Error: Credentials file not found` | `credentials/service-account.json` を配置 |
| `GA4 API Error: 認証情報を確認してください` | サービスアカウントにGA4の閲覧権限があるか確認 |
| `LLM Error` | `.env` の `OPENROUTER_API_KEY` が正しいか確認 |

---

## 自動化（GitHub Actions）

`.github/workflows/weekly-buildinpublic.yml` に毎週月曜日に自動実行するワークフローが含まれています。

リポジトリの **Settings > Secrets and variables > Actions** に以下を登録してください:

- `GOOGLE_CREDENTIALS_JSON` — サービスアカウントJSON（Base64推奨）
- `OPENROUTER_API_KEY`
- `DISCORD_WEBHOOK_URL`（オプション）

## ライセンス

MIT
