#!/usr/bin/env python3
"""PreToolUse(Bash): 破壊的・不可逆なコマンドを止める。claude-harness 管理ファイル。

permissions.deny は単純な前方一致なので、`cd x && rm -rf ~` のような形や
フラグの順序違いをここで正規表現で補う。
"""
from __future__ import annotations

import re

from _common import ask, deny, read_input

DENY = [
    (r"\brm\s+-[a-zA-Z]*(r[a-zA-Z]*f|f[a-zA-Z]*r)[a-zA-Z]*\s+(-\S+\s+)*(/|~|\$HOME|\*|\.{1,2})/?(\s|$|;|&|\|)",
     "ルート・ホーム・カレント全体への rm -rf"),
    (r"\bgit\s+push\b.*\s(--force(?!-with-lease)|-f)\b", "git push --force（--force-with-lease を使う）"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard（未コミットの変更が消える。git stash を使う）"),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f", "git clean -f（未追跡ファイルが消える）"),
    (r"\bgit\s+commit\b.*--no-verify\b", "--no-verify による pre-commit フックの回避"),
    (r"(^|[;&|]\s*)sudo\b", "sudo"),
    (r"\bchmod\s+-R\s+777\b", "chmod -R 777"),
    (r"\bmkfs(\.\w+)?\b|\bdd\s+if=", "ディスク操作"),
    (r"\b(curl|wget)\b[^|]*\|\s*(ba|z)?sh\b", "リモートスクリプトのパイプ実行"),
]

ASK = [
    (r"\bgit\s+push\b.*\b(main|master)\b", "main/master への直接 push"),
    (r"\bgit\s+(checkout|restore)\s+(--\s+)?\.(\s|$)", "作業ツリーの変更を一括破棄"),
    (r"\b(DROP\s+(TABLE|DATABASE)|TRUNCATE\s+TABLE)\b", "破壊的な SQL"),
    (r"\bgit\s+branch\s+-D\b", "未マージブランチの強制削除"),
]


def main() -> None:
    cmd = (read_input().get("tool_input") or {}).get("command", "")
    for pattern, label in DENY:
        if re.search(pattern, cmd, re.IGNORECASE if "DROP" in pattern else 0):
            deny(f"[harness] ブロック: {label}。必要ならユーザーに手動実行を依頼すること。")
    for pattern, label in ASK:
        if re.search(pattern, cmd, re.IGNORECASE):
            ask(f"[harness] 確認: {label}")


if __name__ == "__main__":
    main()
