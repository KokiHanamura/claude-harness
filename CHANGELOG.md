# Changelog

## 1.0.1 - 2026-10-01

- 変更が無い同期で `harness.lock.json` の `synced_at` だけが書き換わり、空のコミットが生まれる問題を修正
- `--dry-run` が settings.json を常に「更新」と表示していたのを、実際に差分がある場合だけ表示するよう修正

## 1.0.0 - 2026-10-01

- 初版
- 7 サブエージェント（researcher / story / spec / backend / frontend / test-verifier / reviewer）と `/feature` パイプライン
- フック: guard_bash, guard_files（機密・管理ファイル・エージェント scope）, post_edit, stop_gate, session_start, daily_plan
- `harness.py`: init / sync / status / install-user、settings の base + repo マージ、conflict 検出、lock ファイル
- ユーザースキル `harness`（「ハーネスを最新にして」）
- Introduction の旧 `ensure_daily_plan.py` / `skills/daily-setup.md` を置き換え
