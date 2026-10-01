---
name: feature
description: 新機能・非自明な変更を 7 エージェントのパイプライン（調査→ストーリー→仕様→バックエンド→フロント→受け入れテスト→レビュー）で進める。2 回の人間承認チェックポイント付き。数行で済む修正やタイポ修正には使わない。
argument-hint: "<作りたい機能の説明>"
---

# Feature パイプライン: $ARGUMENTS

あなたはオーケストレーター。自分ではコードを書かず、各工程を専用サブエージェントに委譲し、成果物をファイルに残し、人間の承認を取る。

## 0. 準備
- `python3 .claude/scripts/daily_plan.py "<機能名の短い要約>"` で作業フォルダ（以下 `$PLAN`）を作る
- `.claude/harness.config.json` の `scopes` と `commands` を読む。`scopes.frontend` が空なら手順 5 を飛ばす
- `$PLAN/ai_todo.md` に工程 1〜7 を TODO として書く

## 1. 調査 — `codebase-researcher`
機能説明を渡す。結果を `$PLAN/research.md` に保存。

## 2. ストーリー — `story-writer`
機能説明 + research.md を渡す。結果を `$PLAN/story.md` に保存。

### ✋ チェックポイント 1（必須）
story.md の要点（ストーリー・AC 一覧・スコープ外・未決事項）をユーザーに示し、承認を得るまで **先に進まない**。
未決事項があれば AskUserQuestion で聞き、回答を story.md に反映する。

## 3. 仕様 — `spec-writer`
承認済み story.md + research.md を渡す。結果を `$PLAN/spec.md` に保存。

### ✋ チェックポイント 2（必須）
spec.md の要点（データモデル・API 形状・変更ファイル一覧・新規インフラ・リスク）を示し、承認を得るまで **ファイルを 1 つも変更しない**。
曖昧な状態の置き場・新規依存・テナント/タイムゾーンの考慮漏れがあれば指摘してから聞く。

## 4. バックエンド — `backend-builder`
spec.md + research.md を渡す。返ってきたサマリを `$PLAN/backend.md` に保存。

## 5. フロントエンド — `frontend-builder`
spec.md + research.md + **backend.md（API 契約）** を渡す。サマリを `$PLAN/frontend.md` に保存。
「API へのフィードバック」が返ったら、backend-builder に差し戻すかユーザーに確認する。

## 6. 受け入れテスト — `test-verifier`
story.md + spec.md + ビルダーのサマリを渡す。結果を `$PLAN/verification.md` に保存。
失敗があれば原因の層のビルダーに再依頼（最大 2 往復。超えたらユーザーに相談）。

## 7. レビュー — `code-reviewer`
spec.md と story.md の場所を伝えて差分をレビューさせる。結果を `$PLAN/review.md` に保存。
Blocker/Major は該当ビルダーに修正させ、再レビュー（最大 2 往復）。

## 8. 仕上げ
- `commands` の test / lint / typecheck を自分でも実行して結果を確認
- ユーザーへの報告: 何を作ったか、AC ごとの検証結果、残課題、レビューで出た再発防止ルール案
- 再発防止ルール案は、このリポジトリ固有なら CLAUDE.md / `.claude/rules/` に、全リポジトリ共通ならユーザーに「ハーネスに反映して」を提案
- コミット・PR はユーザーの指示を待つ（ブランチ未作成なら `feat/<name>` を提案）

## 進め方の原則
- サブエージェントには必要なファイルのパスと要点だけを渡す（会話の全文を渡さない）
- 各工程の完了ごとに ai_todo.md を更新する
- 工程を飛ばしたくなったら、飛ばす理由をユーザーに伝えて了承を得る
