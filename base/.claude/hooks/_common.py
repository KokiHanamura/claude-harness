"""フック共通ユーティリティ（標準ライブラリのみ・Python 3.9 互換）。claude-harness 管理ファイル。"""
from __future__ import annotations

import fnmatch
import json
import os
import sys
from pathlib import Path

PROJECT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])

DEFAULT_CONFIG = {
    "commands": {"test": "", "lint": "", "typecheck": ""},
    "postEdit": [],
    "verifyOnStop": False,
    "scopes": {"backend": [], "frontend": [], "tests": []},
    "protectedPaths": [],
    "allowManagedEdits": False,
    "notifySound": True,
}


def read_input() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    path = PROJECT / ".claude" / "harness.config.json"
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text()))
        except ValueError:
            pass
    return cfg


def lock() -> dict:
    path = PROJECT / ".claude" / "harness.lock.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def rel(path: str) -> str:
    p = Path(path)
    if not p.is_absolute():
        return p.as_posix()
    try:
        return p.resolve().relative_to(PROJECT.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def matches(path: str, patterns) -> bool:
    """fnmatch ベース（`*` は `/` も跨ぐので `src/**` も `src/*` も同じ意味になる）。"""
    name = path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in patterns)


def emit(event: str, **fields) -> None:
    print(json.dumps({"hookSpecificOutput": dict(hookEventName=event, **fields)}, ensure_ascii=False))


def deny(reason: str) -> None:
    emit("PreToolUse", permissionDecision="deny", permissionDecisionReason=reason)
    sys.exit(0)


def ask(reason: str) -> None:
    emit("PreToolUse", permissionDecision="ask", permissionDecisionReason=reason)
    sys.exit(0)
