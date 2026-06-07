# Build in Public Assistant - Specification

**Status**: Ready for Implementation  
**Last Updated**: 2026-06-06  
**Decision Method**: Grill Me Session (Matt Pocock Method)  

---

## 1. Overview

自分のX（Twitter）アカウントをBuild in Publicに変えるための、週次レポート・ポスト生成支援CLIツール。

制作中のサイトの分析データ（Google Analytics 4）を自動取得し、indie hackerのBuild in PublicのプロであるPieter Levels（@levelsio）の文体を参考に、Xへのポスト案をLLMで生成する。

**核心理念**: 「自分用MVP」を最優先。過剰な抽象化やSaaS化を避け、まず自分が週1回サクッと使えるツールを作る。

---

## 2. Goals

- **週1回**、サイトの分析データを自動取得し、Build in Public用のXポスト案を**3パターン**生成する
- **Levelsio風の文体**（率直、カジュアル、数字入り、少し自虐）を参考に、自然な日本語ポストを作成する
- **人間が最終編集・承認**してから手動投稿するワークフローを支える
- **透明性のある開発履歴**をGit管理下に残す（GitHub Actions自動実行）

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | GA4から週次データ（PV, Sessions, UU, 滞在時間, Top Pages）を取得する | Must |

| FR-03 | 前週との比較（%変化）をツール側で計算し、プロンプトに含める | Must |
| FR-04 | Few-shot例（`examples/post_examples.md`）を読み込み、LLMプロンプトに注入する | Must |
| FR-05 | OpenRouter経由でLLMを呼び出し、3パターンのポスト案を生成する | Must |
| FR-06 | 生成結果を `posts/YYYY-MM-DD.md` にMarkdown形式で出力する | Must |
| FR-07 | CLIから週指定（`--week`）や日付指定（`--date`）、上書き（`--force`）ができる | Must |
| FR-08 | GitHub Actionsで週1回自動実行し、生成ファイルを自動コミットする | Should |

### 3.2 Non-Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| NFR-01 | Pythonで実装し、`pyproject.toml` で依存管理する | Must |
| NFR-02 | プロンプトは `prompts/` ディレクトリに外部ファイル化する | Must |
| NFR-03 | 設定は `config.yaml` に集約し、認証情報は `.env` で管理する | Must |
| NFR-04 | エラー時は明確なメッセージを表示し、`exit(1)` で終了する | Must |
| NFR-05 | 自分以外が使う場合も、configをコピーして変更するだけで動くようにする | Should |

---

## 4. Data Sources & Authentication

### 4.1 Google Analytics 4 (GA4)

- **API**: Google Analytics Data API v1
- **指標**:
  - `screenPageViews`（総PV）
  - `sessions`（セッション数）
  - `totalUsers`（ユニークユーザー数）
  - `averageEngagementTimePerSession`（平均滞在時間）
  - `topPages`（ページビューTOP5）
- **認証**: Google Cloud サービスアカウント（JSONキー）
- **必要なスコープ**: `https://www.googleapis.com/auth/analytics.readonly`

### 4.2 Authentication Setup

1. Google Cloud Consoleでプロジェクト作成
2. Analytics API を有効化
3. サービスアカウントを作成し、JSONキーをダウンロード
4. GA4プロパティにサービスアカウントを追加（閲覧権限）
5. JSONキーを `credentials/service-account.json` に配置
6. `.env` に `GOOGLE_CREDENTIALS_PATH=credentials/service-account.json` を記載

---

## 5. LLM Integration & Prompt Design

### 5.1 LLM Provider

- **Primary**: OpenRouter（`https://openrouter.ai/`）
  - 統一的なAPIで複数モデル（Claude, GPT, Grok等）にアクセス可能
  - 週1回実行なのでコストは無視できるレベル
- **Default Model**: `anthropic/claude-3.5-sonnet`
- **Config**: `.env` に `LLM_PROVIDER=openrouter` と `LLM_MODEL=anthropic/claude-3.5-sonnet` を設定

### 5.2 Prompt Files

```
prompts/
├── system_prompt.md      # LLMの役割・文体指示
└── generate_post.md      # ポスト生成用テンプレート（Jinja2）
```

**system_prompt.md** の概要:
- 役割: "あなたはindie hackerのBuild in Publicのプロです"
- 文体: Levelsio風（率直、カジュアル、数字入り、少し自虐、絵文字少なめ）
- 言語: 日本語（config.yamlの `language` に従う）
- 制約: 140〜280文字、Xポストとして自然な形

**generate_post.md** の概要:
- Jinja2テンプレート
- `{{analytics_summary}}` に整形済みの分析データを注入
- `{{few_shot_examples}}` に `examples/post_examples.md` から抽出した例を注入
- 出力指示: 3パターン（Straight / Self-deprecating / Future-oriented）

### 5.3 Few-Shot Examples

```
examples/
└── post_examples.md
```

形式:
```markdown
### Type: progress
内容: 今週のPVは1,234で先週比+12%。まだ小さいけど、毎週ちょっとずつ育ってる感じ。気長に続ける。
---
### Type: failure
内容: 先週リリースした機能、全然使われてなくて泣いてる。需要調査サボった自分がバカだった。
---
### Type: plan
内容: 来週はOOOの改善に集中。まだ使ってくれてる人の離脱率下げるのが最優先。
```

抽出ロジック:
- 各Typeからランダムに1〜2個ずつ、合計3〜5個をプロンプトに含める
- 将来的にX API連携時は自動追加可能な構造にしておく

---

## 6. Workflow & CLI Interface

### 6.1 Command Reference

```bash
# 先週のレポートを生成（デフォルト）
python -m build_in_public generate

# 特定の週を指定
python -m build_in_public generate --week 2026-W23

# 特定の日付（その週の月〜日を対象）
python -m build_in_public generate --date 2026-06-01

# 既存ファイルを強制上書き
python -m build_in_public generate --week 2026-W23 --force
```

### 6.2 Execution Flow

```
1. 引数パース（週 or 日付の決定）
2. config.yaml と .env の読み込み
3. Google認証（サービスアカウントJSON）
4. GA4データ取得（指定期間）
5. 前週データ読み込み（data/archive/）
7. 前週比計算
8. データをMarkdown形式に整形
9. Few-shot例を読み込み
10. LLMプロンプト構築（Jinja2）
11. LLM呼び出し（OpenRouter）
12. レスポンスをパースして3パターン抽出
13. Markdownファイル生成（posts/YYYY-MM-DD.md）
14. 今週データを data/archive/ に保存
15. 完了メッセージ表示
```

---

## 7. Output Specification

### 7.1 File Path

```
posts/YYYY-MM-DD.md
```

- `YYYY-MM-DD` は対象週の月曜日の日付
- 既存ファイルがある場合は `--force` が必要

### 7.2 Markdown Format

```markdown
# Build in Public Report: 2026-06-01 ~ 2026-06-07

## 📊 This Week's Stats
- **PV**: 1,234 (+12% from last week)
- **Sessions**: 987
- **Unique Users**: 654
- **Avg. Engagement Time**: 2m 34s
- **Top Pages**:
  1. `/blog/ai-tool` — 345 views
  2. `/about` — 128 views
  3. `/` — 98 views
## 📝 Post Drafts

### Pattern A: Straight (levelsio風)
[生成されたポスト案]

### Pattern B: Self-deprecating
[生成されたポスト案]

### Pattern C: Future-oriented
[生成されたポスト案]

## 💡 Notes for Editor
- 「XXXクエリ」が急上昇中 → 言及推奨
- 今週はデータ少なめなので控えめに
```

---

## 8. Configuration

### 8.1 config.yaml

```yaml
site_name: "YourSite"
ga4_property_id: "123456789"
language: "ja"
default_tone: "levelsio"
posts_dir: "posts"
archive_dir: "data/archive"
examples_file: "examples/post_examples.md"
prompts_dir: "prompts"
```

### 8.2 .env (gitignored)

```bash
# Google Auth
GOOGLE_CREDENTIALS_PATH=credentials/service-account.json

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
LLM_PROVIDER=openrouter
LLM_MODEL=anthropic/claude-3.5-sonnet

# Optional: Notification
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 8.3 .env.example (committed)

```bash
GOOGLE_CREDENTIALS_PATH=credentials/service-account.json
OPENROUTER_API_KEY=your-openrouter-api-key
LLM_PROVIDER=openrouter
LLM_MODEL=anthropic/claude-3.5-sonnet
# DISCORD_WEBHOOK_URL=
```

---

## 9. Project Structure

```
build-in-public-assistant/
├── .github/
│   └── workflows/
│       └── weekly-buildinpublic.yml    # GitHub Actions週次実行
├── src/
│   └── build_in_public/
│       ├── __init__.py
│       ├── __main__.py                  # python -m build_in_public エントリポイント
│       ├── cli.py                       # argparse, コマンド処理
│       ├── config.py                    # config.yaml / .env の読み込み
│       ├── analytics/
│       │   ├── __init__.py
│       │   └── ga4.py                   # GA4 Data API クライアント
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py                # OpenRouter API クライアント
│       │   └── prompt_builder.py        # Jinja2テンプレート処理
│       ├── writers/
│       │   ├── __init__.py
│       │   └── markdown_writer.py       # Markdownファイル生成
│       └── utils/
│           ├── __init__.py
│           ├── date_helpers.py          # 週・日付計算
│           └── archive_manager.py       # data/archive/ の読み書き
├── prompts/
│   ├── system_prompt.md
│   └── generate_post.md
├── examples/
│   └── post_examples.md
├── posts/                               # 生成されたレポート（Git管理）
├── data/
│   └── archive/                         # 週次データのJSON保存
├── credentials/                         # .gitignore
│   └── .gitkeep
├── config.yaml
├── .env.example
├── .env                                 # .gitignore
├── .gitignore
├── pyproject.toml
├── README.md
└── spec.md                              # This file
```

---

## 10. Error Handling

### 10.1 Error Categories

| Scenario | Behavior | Exit Code |
|---|---|---|
| Google認証失敗 | "GA4 API Error: 認証情報を確認してください" + スタックトレース | 1 |
| APIレート制限 | "API rate limit exceeded. しばらく待って再実行してください" | 1 |
| データが空/少ない | 警告表示 + プロンプトに「序盤スタートアップ感」を自動指示 | 0 |
| LLM APIエラー | "LLM Error: {message}" + リトライ1回 | 1 |
| 既存ファイルあり（--forceなし） | "File already exists: posts/YYYY-MM-DD.md. Use --force to overwrite." | 1 |
| config.yaml不正 | "Config Error: {field} is required" | 1 |
| .env読み込み失敗 | 警告（オプション項目のみの場合）またはエラー（必須項目） | 1 or 0 |

### 10.2 Logging

- 標準出力に進捗メッセージを表示（`Fetching GA4 data...` など）
- エラー時はスタックトレースを簡潔に表示（デバッグ用）
- 過剰なロギングは避け、シンプルに保つ

---

## 11. Deployment & Automation

### 11.1 GitHub Actions

`.github/workflows/weekly-buildinpublic.yml`:

```yaml
name: Weekly Build in Public Report

on:
  schedule:
    - cron: '0 9 * * 1'  # 毎週月曜日 09:00 UTC
  workflow_dispatch:      # 手動実行も可能

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: pip install -e .
        
      - name: Generate report
        env:
          GOOGLE_CREDENTIALS_PATH: ${{ secrets.GOOGLE_CREDENTIALS_PATH }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: python -m build_in_public generate --force
        
      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add posts/
          git add data/archive/
          git diff --cached --quiet || (git commit -m "chore: weekly build in public report $(date +%Y-%m-%d)" && git push)
        
      - name: Notify Discord (optional)
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: |
          curl -H "Content-Type: application/json" \
               -d '{"content":"📊 今週のBuild in Publicレポートが生成されました！"}' \
               $DISCORD_WEBHOOK_URL
```

### 11.2 Secrets Setup

GitHubリポジトリの Settings > Secrets and variables > Actions に以下を登録:

- `GOOGLE_CREDENTIALS_JSON`: サービスアカウントJSONの全文（Base64推奨）
- `OPENROUTER_API_KEY`
- `DISCORD_WEBHOOK_URL`（オプション）

---

## 12. Build in Public Guidelines

### 12.1 公開してよいデータ

- アクセス数（PV, Sessions, UU）
- 人気記事・ページのタイトルとURL
- 検索クエリ（個人を特定しないもの）
- 技術スタックとその変更
- 学びや失敗談
- 開発進捗（機能リリース、バグ修正など）

### 12.2 公開しないデータ

- 正確な収益額（「月1万円くらい」などぼかして可）
- 未公開機能の詳細仕様
- 競合に悪用されそうな内部ロジック
- 個人情報（メールアドレス、ユーザーID等）

### 12.3 ポストのトーン

- **率直**: 数字を隠さず出す
- **カジュアル**: 堅苦しくない、友達に話す感じ
- **少し自虐**: 失敗も隠さず笑いに変える
- **未来志向**: 次にやること、目標を語る
- **絵文字少なめ**: プロフェッショナルでありながら親しみやすく

---

## 13. Future Considerations

| Feature | Description | Priority |
|---|---|---|
| X API Integration | X APIでFew-shot例を自動収集・更新 | Low |
| Web UI | Streamlit or FastAPIでブラウザから実行・編集 | Low |
| Multi-site Support | 複数サイトのレポートを一括生成 | Low |
| Image Generation | 週次データのグラフ画像を自動生成してポストに添付 | Low |
| Auto-posting | 人間の承認なしでXに自動投稿（非推奨だが検討） | Very Low |
| SaaS化 | 他の人も使えるように設定画面を作る | Very Low |

---

## Appendix: Command Reference

```bash
# インストール
pip install -e .

# セットアップ後、初回実行
python -m build_in_public generate

# 過去の週を生成
python -m build_in_public generate --week 2026-W20

# 強制上書き
python -m build_in_public generate --force

# ヘルプ
python -m build_in_public --help
python -m build_in_public generate --help
```

---

**End of Specification**
