#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit): 編集直後にフォーマッタ/リンタを走らせ、失敗を Claude に返す。

harness.config.json:
  "postEdit": [{"glob": "*.py", "command": "ruff format {file} && ruff check --fix {file}"}]
claude-harness 管理ファイル。
"""
from __future__ import annotations

import shlex
import subprocess

from _common import PROJECT, config, emit, matches, read_input, rel


def main() -> None:
    tool_input = read_input().get("tool_input") or {}
    raw = tool_input.get("file_path") or ""
    if not raw:
        return
    path = rel(raw)
    problems = []
    for rule in config().get("postEdit") or []:
        if not matches(path, [rule.get("glob", "")]):
            continue
        cmd = rule["command"].replace("{file}", shlex.quote(path))
        try:
            p = subprocess.run(cmd, shell=True, cwd=PROJECT, capture_output=True, text=True,
                               timeout=rule.get("timeout", 60))
        except subprocess.TimeoutExpired:
            problems.append(f"$ {cmd}\n(timeout)")
            continue
        if p.returncode != 0:
            tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-40:])
            problems.append(f"$ {cmd}\n{tail}")
    if problems:
        emit("PostToolUse", additionalContext="[harness] 編集後チェックが失敗。直してから先に進むこと:\n\n"
             + "\n\n".join(problems))


if __name__ == "__main__":
    main()
