#!/usr/bin/env python3
"""SessionStart: 作業状態（ブランチ・未コミット・当日プラン・ハーネス更新有無）を注入する。

claude-harness 管理ファイル。
"""
from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path

from _common import PROJECT, emit, lock, read_input


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=PROJECT, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    read_input()  # source（startup/resume/compact…）に関わらず同じ情報を注入する
    lines = []
    branch = git("branch", "--show-current")
    if branch:
        dirty = len(git("status", "--porcelain").splitlines())
        lines.append(f"- branch: {branch} / 未コミット: {dirty} 件")

    plans = sorted((PROJECT / "docs" / "plans").glob(date.today().strftime("%Y%m%d") + "_*"))
    for d in plans:
        lines.append(f"- 当日プラン: {d.relative_to(PROJECT)}/")
        todo = d / "ai_todo.md"
        if todo.exists():
            open_items = [l.strip() for l in todo.read_text().splitlines() if l.strip().startswith("- [ ]")]
            lines += [f"  {i}" for i in open_items[:5]]

    lk = lock()
    if lk.get("source"):
        version_file = Path(os.path.expanduser(lk["source"])) / "VERSION"
        if version_file.exists():
            latest = version_file.read_text().strip()
            if latest != lk.get("version"):
                lines.append(f"- ハーネス更新あり: v{lk.get('version')} → v{latest}。"
                             "ユーザーに「ハーネスを最新にして」で更新できると一言伝えること")

    if lines:
        emit("SessionStart", additionalContext="[harness] セッション状態\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
