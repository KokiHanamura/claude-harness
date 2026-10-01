# CLAUDE.md

# claude-harness

全リポジトリに配布する Claude Code ハーネスのベース。仕組みは @README.md

## Commands

| Command | Description |
|---------|-------------|
| `.venv/bin/python -m pytest -q` | テスト（初回: `python3 -m venv .venv && .venv/bin/pip install pytest`） |
| `python3 harness.py sync --all --dry-run` | 全リポジトリへの影響確認 |
| `python3 harness.py install-user` | `user/skills/harness` を変更したら実行 |

## Rules

- `base/` 配下は各リポジトリにそのまま配られる。リポジトリ固有の事情を入れない
- フック・スクリプトは標準ライブラリのみ、Python 3.9 互換（`X | Y` 型を実行時に評価しない）
- 変更したら `VERSION`（semver）と `CHANGELOG.md` を更新し、テストを通してからコミット
- ファイルを廃止したら `manifest.json` の `removed` に追加（各リポジトリから掃除される）
- フックの挙動を変えたら `tests/test_hooks.py` にケースを追加
- 展開は `sync --all --dry-run` で影響を見てから
