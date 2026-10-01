# claude-harness

全リポジトリ共通の Claude Code ハーネス（ベース）。ここを直して「ハーネスを最新にして」と言うと、登録済みの全リポジトリが同じ構成に揃う。

## 何が入るか

| 種類 | ファイル | 役割 |
|------|----------|------|
| サブエージェント ×7 | `.claude/agents/` | codebase-researcher → story-writer → spec-writer → backend-builder → frontend-builder → test-verifier → code-reviewer |
| スキル | `.claude/skills/feature` | 上の 7 エージェントを順に回すパイプライン（人間承認 2 回） |
| | `.claude/skills/daily-setup` | 日次フォルダ作成 |
| フック | `guard_bash.py` (PreToolUse/Bash) | force push・`reset --hard`・`rm -rf ~`・`--no-verify` などを拒否、main への push などは確認 |
| | `guard_files.py` (PreToolUse/Edit 系) | `.env`/鍵の編集拒否、管理ファイルの直接編集拒否、**ビルダー系エージェントの編集範囲を scope に制限** |
| | `post_edit.py` (PostToolUse) | 編集直後にフォーマッタ/リンタを実行し、失敗を Claude に返す |
| | `stop_gate.py` (Stop) | 完了前にテストを実行し、失敗なら止めさせない（opt-in）＋完了音 |
| | `session_start.py` (SessionStart) | ブランチ・未コミット・当日 TODO・ハーネス更新有無を注入 |
| | `daily_plan.py --ensure` (PreToolUse/EnterPlanMode) | 当日フォルダを自動作成 |
| ルール | `.claude/rules/harness.md` | 共通ワークフロー（CLAUDE.md を肥大化させないため rules に分離） |
| 設定 | `settings/base.json` | 権限（allow/ask/deny）とフック登録 |
| その他 | `docs/plans/_template/`, `.github/PULL_REQUEST_TEMPLATE.md` | |

## 設計方針（2026 年時点のベストプラクティスから）

- **強制はフック、指示はルール**: 「テストして」と書くより Stop フックで落とす。CLAUDE.md はコンテキストであって強制ではない
- **CLAUDE.md は短く**: 共通事項は `.claude/rules/harness.md` に出し、リポジトリの CLAUDE.md は固有の事実だけ（〜100 行）
- **役割ごとにコンテキストを分ける**: 1 セッションに PM・設計・実装・テスト・レビューを兼任させない。各エージェントは必要なツールだけを持ち、書き込み範囲はフックで強制
- **人間のチェックポイントは上流に**: ストーリーと仕様の段階で承認する（10 ファイル変更した後ではなく）
- **速いフィードバック**: 編集直後（PostToolUse）→ 完了時（Stop）→ CI の順に、速い層でできるだけ検出する
- **同じミスは 2 回目で仕組みにする**: ルール・テスト・フックのどれで防ぐかを決め、全体共通ならこのリポジトリへ

## 配布の仕組み

```
claude-harness/                       各リポジトリ
  base/**            ── 上書き同期 ──▶  同じパス（管理ファイル）
  seed/**            ── 無ければ作成 ─▶  CLAUDE.md, .claude/harness.config.json（以後リポジトリの持ち物）
  settings/base.json ┐
                     ├─ マージ ──────▶  .claude/settings.json（生成物。直接編集しない）
  .claude/settings.repo.json ┘ (リポジトリ固有の設定)
                                       .claude/harness.lock.json（バージョンと各ファイルのハッシュ）
```

- 管理ファイルがリポジトリ側で改変されていたら、上書きせず **conflict** として止まる（`--force` で上書き）
- `settings.json` が直接編集されていたら、ベースとの差分を自動で `settings.repo.json` に退避してから再生成
- ベースから消したファイルは、未改変なら各リポジトリからも削除（`manifest.json` の `removed` で旧ファイルも掃除）
- 各リポジトリにファイルの実体がコミットされるので、クラウドセッションやチームメンバーの環境でもそのまま動く
  （plugin 方式はリポジトリごとの settings/rules を配れず、ローカル設定に依存するため採用していない）

## 使い方

Claude Code にはこう言うだけでよい（ユーザースキル `~/.claude/skills/harness` が処理する）:

| 言うこと | 動作 |
|----------|------|
| 「ハーネスを最新にして」 | ベースを pull → 全リポジトリへ同期 → conflict 解決 → 管理ファイルだけコミット |
| 「このリポジトリにハーネスを入れて」 | 導入 + registry 登録 + `harness.config.json` をリポジトリに合わせて記入 |
| 「これをハーネスに反映して」 | ベースを修正 → VERSION/CHANGELOG 更新 → テスト → 全体へ展開 |

CLI を直接使う場合:

```bash
python3 harness.py init ~/new-repo        # 導入（registry.json に登録）
python3 harness.py sync --all --dry-run   # 何が変わるか確認
python3 harness.py sync --all             # 全リポジトリを同期
python3 harness.py status --all           # バージョンとドリフト
python3 harness.py install-user           # ~/.claude/skills/harness を（再）配置
```

## リポジトリごとの設定: `.claude/harness.config.json`

```jsonc
{
  "commands": { "test": ".venv/bin/python -m pytest -q", "lint": "", "typecheck": "" },
  "postEdit": [{ "glob": "*.py", "command": "ruff format {file} && ruff check --fix {file}" }],
  "verifyOnStop": true,                    // 完了前にテスト必須
  "scopes": {                              // ビルダー系エージェントの書き込み範囲
    "backend": ["app/*"], "frontend": ["web/*"], "tests": ["tests/*"]
  },
  "protectedPaths": ["data/*.db"],         // 誰も編集させないパス
  "allowManagedEdits": false,              // ハーネス自体を試験的に直すときだけ true
  "notifySound": true
}
```

## 開発

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest -q
```

フックは標準ライブラリのみ・Python 3.9 互換で書く（各リポジトリに追加依存を持ち込まないため）。

## 参考

- Claude Code Docs: [Hooks](https://code.claude.com/docs/en/hooks) / [Subagents](https://code.claude.com/docs/en/sub-agents) / [Skills](https://code.claude.com/docs/en/skills) / [Memory・rules](https://code.claude.com/docs/en/memory) / [Permissions](https://code.claude.com/docs/en/permissions) / [Plugins](https://code.claude.com/docs/en/plugins)
- [Harness Engineering Best Practices 2026](https://nyosegawa.com/en/posts/harness-engineering-best-practices-2026/)
- 「7-agent software factory」記事（Researcher / Story / Spec / Backend / Frontend / Test Verifier / Reviewer）
