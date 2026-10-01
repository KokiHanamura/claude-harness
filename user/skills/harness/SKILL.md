---
name: harness
description: claude-harness（全リポジトリ共通の Claude Code ハーネス）の運用。「ハーネスを最新にして」「ハーネスを更新して」で登録済み全リポジトリを最新ベースに同期、「このリポジトリにハーネスを入れて」で導入、「これをハーネスに反映して」で改善をベースに取り込んで全体に展開する。
argument-hint: "[update | adopt | improve <内容> | status]"
---

ベースリポジトリ: `{{HARNESS_HOME}}`（以下 `$H`）。CLI は `python3 $H/harness.py`。
ベースの仕組みの詳細は `$H/README.md`。

依頼に応じて以下のどれかを実行する。

## update —「ハーネスを最新にして」
1. ベースを最新化: `git -C $H pull --ff-only`（リモートが無ければ飛ばす。ベースに未コミット変更があればユーザーに確認）
2. 計画を確認: `python3 $H/harness.py sync --all --dry-run`
3. 各対象リポジトリで、管理パス（`.claude/`, `docs/plans/_template/`, `.github/PULL_REQUEST_TEMPLATE.md`, `.gitignore`）に未コミット変更が無いか `git status` で確認。あればそのリポジトリは保留してユーザーに伝える
4. 実行: `python3 $H/harness.py sync --all`
5. **CONFLICT** が出たファイルは、`git diff` とベース版（`$H/base/<path>`）を比べて判断する:
   - リポジトリ固有の改変 → 中身を `CLAUDE.md` / `.claude/rules/<topic>.md` / `.claude/settings.repo.json` に移してから `sync <repo> --force`
   - 全体に有用な改変 → improve の手順でベースに取り込んでから再同期
   - 判断がつかなければユーザーに聞く
6. 各リポジトリで管理ファイルだけをコミット（他の作業中ファイルを巻き込まない）:
   `git -C <repo> add .claude .gitignore docs/plans/_template .github/PULL_REQUEST_TEMPLATE.md && git -C <repo> commit -m "chore(harness): sync to v<VERSION>"`
   - コミットする前に `git -C <repo> diff --cached --stat` で対象を確認する
   - push はしない（ユーザーの指示があれば行う）
7. 結果を表で報告: リポジトリ / 旧→新バージョン / 変更ファイル数 / conflict / コミット

## adopt —「このリポジトリにハーネスを入れて」
1. `python3 $H/harness.py init <repo の絶対パス>`（registry.json に自動登録される）
2. リポジトリを調べて `.claude/harness.config.json` を埋める:
   - `commands`: 実際のテスト・lint・型チェックのコマンド（venv があれば `.venv/bin/python -m pytest` など）
   - `scopes`: backend / frontend / tests のパス。単一構成なら backend にアプリ全体、frontend は空
   - `postEdit`: 導入済みのフォーマッタがあれば（無いなら空のまま。勝手にツールを追加しない）
   - `verifyOnStop`: テストが速い（〜30 秒）なら true を提案
3. `.claude/settings.repo.json` に退避された設定を見て、ベースと重複・旧式のものを整理する
4. CLAUDE.md を見直し、`.claude/rules/harness.md` と重複するワークフロー記述は削り、プロジェクト固有の事実だけ残す（100 行以内目安）。
   旧スクリプト（`scripts/create_daily_plan.py` 等）がベースの機能と重複していれば、削除を提案する
5. `$H` の registry.json の変更をベースでコミット: `git -C $H add registry.json && git -C $H commit -m "chore: register <repo名>"`
6. update の手順 6 と同様にリポジトリ側をコミット

## improve —「これをハーネスに反映して」
全リポジトリ共通にすべき改善（新しいフック、エージェントの改良、ルール追加など）をベースに入れて展開する。
1. 本当に全体共通か確認する。特定リポジトリだけの事情ならそのリポジトリの CLAUDE.md / rules に書く
2. `$H/base/`（配布ファイル）、`$H/settings/base.json`（共通設定）、`$H/seed/`（初回のみのテンプレ）のいずれかを編集
   - 廃止したファイルは `manifest.json` の `removed` に追加
3. `$H/VERSION` を semver で上げ（互換を壊す=major / 機能追加=minor / 修正=patch）、`$H/CHANGELOG.md` に追記
4. `cd $H && .venv/bin/python -m pytest -q` が通ることを確認
5. ベースをコミット（`feat(harness): ...` 等）。push はユーザー確認後
6. update の手順で全リポジトリへ展開

## status
`python3 $H/harness.py status --all` の結果を要約する。
