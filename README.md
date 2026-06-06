# Build in Public Assistant

自分のX（Twitter）アカウントをBuild in Publicに変えるための、週次レポート・ポスト生成支援CLIツール。

## 概要

制作中のサイトの分析データ（Google Analytics 4 / Search Console）を自動取得し、indie hackerのBuild in PublicのプロであるPieter Levels（@levelsio）の文体を参考に、Xへのポスト案をLLMで生成します。

## インストール

```bash
pip install -e .
```

## セットアップ

1. `config.yaml` を自分のサイトに合わせて編集
2. `.env` を `.env.example` を参考に作成
3. Google Cloud のサービスアカウントJSONを `credentials/service-account.json` に配置

## 使い方

```bash
# 先週のレポートを生成（デフォルト）
python -m build_in_public generate

# 特定の週を指定
python -m build_in_public generate --week 2026-W23

# 特定の日付（その週の月曜〜日曜を対象）
python -m build_in_public generate --date 2026-06-01

# 既存ファイルを強制上書き
python -m build_in_public generate --week 2026-W23 --force
```

## 自動化

GitHub Actions で毎週月曜日に自動実行するワークフローが `.github/workflows/weekly-buildinpublic.yml` に含まれています。

## ライセンス

MIT
