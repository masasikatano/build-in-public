# GitHub Daily Commit Report - Specification

**Status**: Ready for Implementation  
**Last Updated**: 2026-06-07  
**Decision Method**: Grill Me Session (Matt Pocock Method)

---

## 1. Overview

`https://github.com/mtgcards/mtg` の更新履歴（commit履歴）をXのポストに変換する、**日次**レポート生成機能。

既存の週次GA4レポート機能（`build-in-public generate`）とは**完全に独立した別コマンド**として実装する。日次の開発活動をBuild in Publicとして発信するためのツール。

**核心理念**: 週次の数字報告（GA4）と日次の開発ログ（GitHub）を分離し、それぞれの頻度に合わせた最適なワークフローを提供する。

---

## 2. Goals

- **毎日**（または任意の日）、対象リポジトリのmainブランチのcommit履歴を自動取得する
- 取得したcommit一覧をLLMで**3パターンのXポスト案**（Straight / Self-deprecating / Future-oriented）に要約する
- 要約の下に**コミット詳細一覧**を記録用として含める
- 人間が最終編集・承認してから手動投稿するワークフローを支える
- 将来の月次サマリーやFew-shot例の自動収集に備え、生データをアーカイブする

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-GH01 | GitHub REST APIから指定日（JST 00:00〜23:59）のcommit履歴を取得する | Must |
| FR-GH02 | 対象は**main（default branch）のみ**。他ブランチは対象外 | Must |
| FR-GH03 | コミットフィルタリングは**行わない**（マージコミット・botコミットも全件含める） | Must |
| FR-GH04 | 1日のコミット数が多い場合も**全件取得**する | Must |
| FR-GH05 | 取得したcommit一覧をLLMプロンプトに含め、3パターンのポスト案を生成する | Must |
| FR-GH06 | Markdown出力に「Post Drafts（3パターン）」＋「Commit Log（詳細）」の両方を含める | Must |
| FR-GH07 | 生成結果を `posts/daily/YYYY-MM-DD.md` に出力する | Must |
| FR-GH08 | 生データを `data/archive/github-YYYY-MM-DD.json` に保存する | Must |
| FR-GH09 | CLIから日付指定（`--date`）と強制上書き（`--force`）ができる | Must |
| FR-GH10 | デフォルトの対象日付は**今日（JST基準）** | Must |
| FR-GH11 | `.env` の `GITHUB_TOKEN` があれば認証付きで、なければunauthenticatedでフォールバック | Should |

### 3.2 Non-Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| NFR-GH01 | 既存の週次レポート機能への影響を最小限に抑える | Must |
| NFR-GH02 | プロンプトは既存の `system_prompt.md` + `generate_post.md` を流用し、条件分岐で対応 | Must |
| NFR-GH03 | GitHub APIクライアントは `requests` を使い、シンプルに実装する | Must |
| NFR-GH04 | エラー時は明確なメッセージを表示し、`exit(1)` で終了する | Must |

---

## 4. Data Source & Authentication

### 4.1 GitHub REST API

- **Endpoint**: `GET https://api.github.com/repos/{owner}/{repo}/commits`
- **Query Parameters**:
  - `sha`: `main`（ブランチ指定）
  - `since`: 対象日のJST 00:00をUTCに変換した値（例：`2026-06-06T15:00:00Z`）
  - `until`: 対象日のJST 23:59をUTCに変換した値（例：`2026-06-07T14:59:59Z`）
  - `per_page`: `100`（1ページあたりの最大件数）
- **取得フィールド（MVP）**:
  - `sha`（短縮版7文字）
  - `commit.message`
  - `commit.author.name`
  - `commit.author.date`
  - `html_url`
- **Pagination**: `Link`ヘッダーの`rel="next"`を辿り、全件取得する

### 4.2 Authentication

- **Unauthenticated**: 60 requests/hour
- **Authenticated**（`GITHUB_TOKEN`）: 5,000 requests/hour
- 実装:
  - `.env` に `GITHUB_TOKEN` を**任意**で設定
  - 存在する場合は `Authorization: token {GITHUB_TOKEN}` ヘッダーを付与
  - 存在しない場合はヘッダーなしでフォールバック

---

## 5. LLM Integration & Prompt Design

### 5.1 プロンプト方針

既存のプロンプトファイルを**流用**し、最小限の変更で対応する。

- **`prompts/system_prompt.md`**: 変更なし（Levelsio風トーン指示はそのまま流用）
- **`prompts/generate_post.md`**: 条件分岐を追加
  - `{{data_type}}` 変数で `"ga_weekly"` or `"github_daily"` を判定
  - `ga_weekly` の場合: 既存の `{{analytics_summary}}` を使用
  - `github_daily` の場合: `{{commit_summary}}` を使用

### 5.2 Commit Summary のフォーマット（プロンプト注入用）

```markdown
## Today's Commits (2026-06-07)

Total: 5 commits

1. `abc1234` by @user — 検索フィルタ追加
2. `def5678` by @user — 価格グラフUI修正
3. `ghi9012` by @user — バグ修正: ページネーション
4. `jkl3456` by @user — README更新
5. `mno7890` by @user — CI設定調整
```

### 5.3 Few-Shot Examples

既存の `examples/post_examples.md` を流用。将来的にGitHub専用の例を追加することも検討する（Future Considerations参照）。

---

## 6. Workflow & CLI Interface

### 6.1 Command Reference

```bash
# 今日のコミットでレポート生成（デフォルト）
build-in-public github

# 特定の日付を指定
build-in-public github --date 2026-06-06

# 既存ファイルを強制上書き
build-in-public github --date 2026-06-06 --force

# ヘルプ
build-in-public github --help
```

### 6.2 Execution Flow

```
1. 引数パース（日付決定。デフォルトは今日JST）
2. config.yaml と .env の読み込み
3. GitHub APIでコミット一覧取得（JST→UTC変換、ページネーション対応）
4. コミットデータをアーカイブ（data/archive/github-YYYY-MM-DD.json）
5. コミット一覧をMarkdown形式に整形（プロンプト用サマリー）
6. LLMプロンプト構築（Jinja2、data_type="github_daily"）
7. LLM呼び出し（OpenRouter）
8. レスポンスをパースして3パターン抽出
9. Markdownファイル生成（posts/daily/YYYY-MM-DD.md）
10. 完了メッセージ表示
```

---

## 7. Output Specification

### 7.1 File Path

```
posts/daily/YYYY-MM-DD.md
```

- `YYYY-MM-DD` は対象日（JST基準）
- 既存ファイルがある場合は `--force` が必要

### 7.2 Markdown Format

```markdown
# Daily Build in Public: 2026-06-07

## 📊 Today's Activity
- Commits: 5件
- 主な変更: カード検索フィルタ追加、価格グラフUI修正 など

## 📝 Post Drafts

### Pattern A: Straight
今日はカード検索のフィルタリング機能を強化した。価格グラフの細かいUIも直した。まだ地味だけど着実に改善中。
https://github.com/mtgcards/mtg

### Pattern B: Self-deprecating
今日もコードと格闘。検索フィルタ入れたら変なバグが出て1時間溶かしたわ（笑）。価格グラフも微調整したけど、まだダサい。
https://github.com/mtgcards/mtg

### Pattern C: Future-oriented
カード検索フィルタと価格グラフUIを改善した。来週はもっと使いやすい並び替え機能を追加したい。
https://github.com/mtgcards/mtg

## 📋 Commit Log (詳細)
- `abc1234` — 検索フィルタ追加 by @user
- `def5678` — 価格グラフUI修正 by @user
- `ghi9012` — バグ修正: ページネーション by @user
- `jkl3456` — README更新 by @user
- `mno7890` — CI設定調整 by @user

→ Full history: https://github.com/mtgcards/mtg/commits/main
```

### 7.3 Archive Format

```
data/archive/github-YYYY-MM-DD.json
```

```json
{
  "date": "2026-06-07",
  "repo": "mtgcards/mtg",
  "branch": "main",
  "total_commits": 5,
  "commits": [
    {
      "sha": "abc1234",
      "message": "検索フィルタ追加",
      "author": "user",
      "date": "2026-06-07T10:30:00+09:00",
      "url": "https://github.com/mtgcards/mtg/commit/abc1234"
    }
  ],
  "model_used": "anthropic/claude-3.5-sonnet"
}
```

---

## 8. Configuration

### 8.1 config.yaml（追加項目）

```yaml
site_name: "昭和MTG"
site_url: "https://mtg.syowa.workers.dev"
site_description: "MTGカードの価格推移や歴代データをビジュアル化するサイト"
ga4_property_id: "526889116"
github_repo: "mtgcards/mtg"  # 追加
language: "ja"
default_tone: "levelsio"
posts_dir: "posts"
archive_dir: "data/archive"
examples_file: "examples/post_examples.md"
prompts_dir: "prompts"
```

### 8.2 .env（追加項目）

```bash
# Google Auth
GOOGLE_CREDENTIALS_PATH=credentials/service-account.json

# GitHub (Optional)
GITHUB_TOKEN=ghp_xxxxxxxx  # 任意。設定するとレート制限緩和

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
LLM_PROVIDER=openrouter
LLM_MODEL=anthropic/claude-3.5-sonnet

# Optional: Notification
# DISCORD_WEBHOOK_URL=
```

---

## 9. Project Structure（変更点）

```
build-in-public/
├── src/build_in_public/
│   ├── __main__.py
│   ├── cli.py                    # ← githubサブコマンド追加
│   ├── config.py                 # ← github_repo検証追加
│   ├── analytics/
│   │   └── ga4.py
│   ├── github/                   # ← 新規ディレクトリ
│   │   ├── __init__.py
│   │   ├── client.py             # GitHub APIクライアント
│   │   └── formatter.py          # コミット一覧整形
│   ├── llm/
│   │   ├── client.py
│   │   └── prompt_builder.py     # ← data_type分岐追加
│   ├── utils/
│   │   ├── archive_manager.py    # ← githubアーカイブ対応
│   │   └── date_helpers.py       # ← JST日付変換
│   └── writers/
│       └── markdown_writer.py    # ← dailyレポート対応
├── prompts/
│   ├── system_prompt.md
│   └── generate_post.md          # ← 条件分岐追加
├── posts/
│   └── daily/                    # ← 新規ディレクトリ
├── data/archive/
│   └── github-YYYY-MM-DD.json    # 生成例
├── examples/
│   └── post_examples.md
├── config.yaml
├── .env.example                  # ← GITHUB_TOKEN追加
└── spec_github.md                # This file
```

---

## 10. Error Handling

| Scenario | Behavior | Exit Code |
|---|---|---|
| `github_repo`未設定 | "Config Error: github_repo is required in config.yaml" | 1 |
| GitHub API 404 | "GitHub Error: Repository not found: mtgcards/mtg" | 1 |
| GitHub API 403（レート制限） | "GitHub API rate limit exceeded. GITHUB_TOKENを設定してください" | 1 |
| 指定日のコミットが0件 | 警告表示 + 「本日はコミットなし」のレポートを生成 | 0 |
| LLM APIエラー | "LLM Error: {message}" + リトライ1回 | 1 |
| 既存ファイルあり（--forceなし） | "File already exists: posts/daily/YYYY-MM-DD.md. Use --force to overwrite." | 1 |
| 日付フォーマット不正 | "Error: Invalid date format. Use YYYY-MM-DD." | 1 |

---

## 11. Future Considerations

| Feature | Description | Priority |
|---|---|---|
| GraphQL API移行 | changed files/additions/deletionsを効率的に取得 | Low |
| 複数リポジトリ対応 | `github_repos` リスト化 | Low |
| GitHub Actions自動実行 | 毎日決まった時間に実行 | Should |
| GitHub専用Few-shot例 | `examples/github_post_examples.md` を追加 | Low |
| コミットフィルタリング | bot除外、接頭辞フィルタなど | Low |
| ブランチ指定 | `config.yaml` でブランチを変更可能に | Low |

---

## Appendix: Command Reference

```bash
# インストール
pip install -e .

# 今日のレポートを生成
python -m build_in_public github

# 特定の日付を生成
python -m build_in_public github --date 2026-06-06

# 強制上書き
python -m build_in_public github --date 2026-06-06 --force

# ヘルプ
python -m build_in_public github --help
```

---

**End of Specification**
