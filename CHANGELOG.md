# Changelog

## 1.0.0 - 2026-10-01

- 初版
- 7 サブエージェント（researcher / story / spec / backend / frontend / test-verifier / reviewer）と `/feature` パイプライン
- フック: guard_bash, guard_files（機密・管理ファイル・エージェント scope）, post_edit, stop_gate, session_start, daily_plan
- `harness.py`: init / sync / status / install-user、settings の base + repo マージ、conflict 検出、lock ファイル
- ユーザースキル `harness`（「ハーネスを最新にして」）
- Introduction の旧 `ensure_daily_plan.py` / `skills/daily-setup.md` を置き換え
