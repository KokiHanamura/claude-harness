#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit|NotebookEdit): 書き込み先のガード。claude-harness 管理ファイル。

1. 機密ファイル（.env, 鍵）への書き込みを拒否
2. ハーネス管理ファイルの直接編集を拒否（ベースリポジトリで直して同期する）
3. harness.config.json の protectedPaths を拒否
4. ビルダー系サブエージェントは自分の scope 外を編集できない
"""
from __future__ import annotations

from _common import config, deny, lock, matches, read_input, rel

SECRETS = [".env", ".env.*", "*.pem", "*.key", "id_rsa*", "id_ed25519*", "credentials.json", "secrets/*"]
SECRET_OK = [".env.example", ".env.sample", ".env.template"]

# エージェント名 → harness.config.json の scopes キー
AGENT_SCOPES = {"backend-builder": "backend", "frontend-builder": "frontend", "test-verifier": "tests"}
ALWAYS_WRITABLE = ["docs/plans/*"]


def main() -> None:
    data = read_input()
    tool_input = data.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not raw:
        return
    path = rel(raw)
    cfg = config()

    if matches(path, SECRETS) and not matches(path, SECRET_OK):
        deny(f"[harness] 機密ファイル {path} は編集しない。値の変更はユーザーに依頼すること。")

    managed = set(lock().get("files", {})) | {".claude/settings.json", ".claude/harness.lock.json"}
    if path in managed and not cfg.get("allowManagedEdits"):
        deny(
            f"[harness] {path} は claude-harness の管理ファイル（同期で上書きされる）。"
            " 全リポジトリ共通の変更ならベースリポジトリで直して「ハーネスを最新にして」。"
            " このリポジトリ固有なら .claude/settings.repo.json / CLAUDE.md / .claude/rules/ に書く。"
        )

    if cfg.get("protectedPaths") and matches(path, cfg["protectedPaths"]):
        deny(f"[harness] {path} は protectedPaths に含まれる。変更が必要ならユーザーに確認すること。")

    scope_key = AGENT_SCOPES.get(data.get("agent_type") or "")
    if scope_key:
        allowed = (cfg.get("scopes") or {}).get(scope_key) or []
        if allowed and not matches(path, allowed + ALWAYS_WRITABLE):
            deny(
                f"[harness] {data['agent_type']} の編集範囲は {allowed}。{path} は範囲外。"
                " 必要な変更はサマリに「範囲外の要望」として書いて親に返すこと。"
            )


if __name__ == "__main__":
    main()
