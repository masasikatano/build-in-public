# Build in Public Assistant

自分のX（Twitter）アカウントをBuild in Publicに変えるための、週次レポート・ポスト生成支援CLIツール。

制作中のサイトの分析データ（Google Analytics 4 / Search Console）を自動取得し、indie hackerのBuild in PublicのプロであるPieter Levels（@levelsio）の文体を参考に、Xへのポスト案をLLMで生成します。

---

## ローカル環境での実行方法

### 1. 前提条件

- Python 3.11+
- [OpenRouter](https://openrouter.ai/) の API キー
- Google Cloud プロジェクト（GA4 / Search Console API 有効化済み）

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
ga4_property_id: "123456789"                      # GA4 プロパティID
search_console_site_url: "sc-domain:example.com"  # または "https://example.com/"
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
2. 以下の2つのAPIを検索して、それぞれ **「有効にする」** をクリック:
  - **Google Analytics Data API**
  - **Google Search Console API**

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

1. [Google Analytics](https://analytics.google.com/) にアクセス
2. 対象のプロパティを開く
3. 左下の歯車アイコン → **「プロパティ」** → **「プロパティのアクセス権限の管理」**
4. **「アクセス権限を付与する」** をクリック
5. サービスアカウントのメールアドレス（例: `build-in-public@your-project.iam.gserviceaccount.com`）を入力
6. ロールを **「閲覧者」** に設定し、**「追加」**

#### 4.6 Search Console に権限を付与

1. [Google Search Console](https://search.google.com/search-console) にアクセス
2. 対象のプロパティを選択
3. 左メニューの歯車アイコン → **「ユーザーと権限」**
4. **「ユーザーを追加」** をクリック
5. サービスアカウントのメールアドレスを入力
6. 権限を **「閲覧者」** に設定し、**「追加」**

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

### 6. 出力結果

実行後、以下が生成されます:

- `posts/YYYY-MM-DD.md` — レポート（Xポスト案3パターン含む）
- `data/archive/YYYY-MM-DD.json` — 生データのアーカイブ

### トラブルシューティング


| エラー                                        | 対処法                                        |
| ------------------------------------------ | ------------------------------------------ |
| `Config Error: config.yaml not found`      | リポジトリのルートに `config.yaml` があるか確認            |
| `Config Error: Credentials file not found` | `credentials/service-account.json` を配置     |
| `GA4 API Error: 認証情報を確認してください`             | サービスアカウントにGA4の閲覧権限があるか確認                   |
| `Search Console API Error`                 | サイトURLの形式を確認 (`sc-domain:` または `https://`) |
| `LLM Error`                                | `.env` の `OPENROUTER_API_KEY` が正しいか確認      |


---

## 自動化（GitHub Actions）

`.github/workflows/weekly-buildinpublic.yml` に毎週月曜日に自動実行するワークフローが含まれています。

リポジトリの **Settings > Secrets and variables > Actions** に以下を登録してください:

- `GOOGLE_CREDENTIALS_JSON` — サービスアカウントJSON（Base64推奨）
- `OPENROUTER_API_KEY`
- `DISCORD_WEBHOOK_URL`（オプション）

## ライセンス

MIT