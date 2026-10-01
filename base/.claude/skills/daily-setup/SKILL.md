---
name: daily-setup
description: 当日の作業フォルダ docs/plans/YYYYMMDD_<作業内容>/ を作成する。「今日のフォルダ作成して」「今日は〇〇をやる」と言われたときに使う。
argument-hint: "<作業内容>"
---

1. 作業内容が分からなければユーザーに一言で聞く
2. `python3 .claude/scripts/daily_plan.py "<作業内容>"` を実行
3. 作成されたフォルダの `co_plan.md` の「今日の目標」をユーザーと埋め、`ai_todo.md` にタスクを書く
