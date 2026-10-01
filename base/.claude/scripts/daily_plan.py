#!/usr/bin/env python3
"""日次作業フォルダ docs/plans/YYYYMMDD_<説明>/ を作成する。claude-harness 管理ファイル。

  python3 .claude/scripts/daily_plan.py "<作業内容>"   # 説明付きで作成（既存なら場所を表示）
  python3 .claude/scripts/daily_plan.py --ensure       # 当日フォルダが無ければ「作業」で作成
  --hook を付けると PreToolUse 用の JSON を出力する
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
PLANS = ROOT / "docs" / "plans"


def create(description: str) -> Path:
    folder = PLANS / f"{date.today():%Y%m%d}_{description}"
    if folder.exists():
        return folder
    folder.mkdir(parents=True)
    for name in ("co_plan.md", "ai_todo.md"):
        src = PLANS / "_template" / name
        if src.exists():
            (folder / name).write_text(src.read_text().replace("{{DATE}}", f"{date.today():%Y-%m-%d}"))
    return folder


def main(argv: list) -> int:
    hook = "--hook" in argv
    args = [a for a in argv if not a.startswith("--")]
    if "--ensure" in argv:
        if hook:
            sys.stdin.read()
        existing = sorted(PLANS.glob(f"{date.today():%Y%m%d}_*"))
        folder = existing[0] if existing else create("作業")
        created = not existing
    elif args:
        folder, created = create(args[0]), True
    else:
        print(__doc__)
        return 1
    rel = folder.relative_to(ROOT)
    if hook:
        if created:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"[harness] 当日フォルダを作成: {rel}/ （計画は co_plan.md、AI の TODO は ai_todo.md）",
            }}, ensure_ascii=False))
    else:
        print(f"{rel}/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
