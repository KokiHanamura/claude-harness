<!-- claude-harness 管理ファイル。直接編集せずベースリポジトリで変更して同期する -->
# 共通ワークフロー（claude-harness）

## 作業の進め方
- 新機能・複数ファイルにまたがる変更は `/feature <説明>` で進める（調査→ストーリー→仕様の 2 段階承認の後に実装）
- 小さな修正は直接やってよいが、触る前に関連コードを読み、終わったら `.claude/harness.config.json` の `commands` を実行して確認する
- 「完了」と言う前に検証する。テストや動作確認をしていないなら、していないと明記する

## 日次フォルダ
- `docs/plans/YYYYMMDD_<説明>/` に `co_plan.md`（人間と協働の計画）と `ai_todo.md`（Claude 専用。人間は読むだけ）
- 作成: `python3 .claude/scripts/daily_plan.py "<作業内容>"`（プランモード開始時はフックが自動作成）
- `/feature` の成果物（research / story / spec / backend / frontend / verification / review）も同じフォルダに置く

## Git
- 新機能はブランチを切って PR。main へ直接 push しない
- コミットメッセージは変更の意図（why）を中心に書く
- `--no-verify`・force push・`reset --hard` は使わない（フックでブロックされる）

## ハーネス
- `.claude/` 配下の管理ファイル（`harness.lock.json` の `files`）と `.claude/settings.json` は直接編集しない
  - このリポジトリ固有の設定 → `.claude/settings.repo.json`（同期時に settings.json へマージ）
  - このリポジトリ固有の指示 → `CLAUDE.md` または `.claude/rules/<topic>.md`
  - 全リポジトリ共通にしたい改善 → ユーザーに「ハーネスに反映して」を提案
- 同じミスを 2 回したら、プロンプトで頑張らず、ルール・テスト・フックのどれで防ぐかを提案する
