#!/usr/bin/env python3
"""Stop: 完了宣言の前の品質ゲート + 完了通知。claude-harness 管理ファイル。

- verifyOnStop=true かつ commands.test があり、コードに未コミット変更があればテストを実行。
  失敗したら停止をブロックして Claude に直させる（stop_hook_active 時は再ブロックしない）。
- notifySound=true なら macOS の効果音を鳴らす。
"""
from __future__ import annotations

import json
import shutil
import subprocess

from _common import PROJECT, config, read_input


def git_changes() -> list:
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT, capture_output=True,
                             text=True, timeout=10).stdout
    except Exception:
        return []
    return [l[3:] for l in out.splitlines() if l[3:] and not l[3:].startswith("docs/plans/")]


def notify(cfg: dict) -> None:
    if cfg.get("notifySound") and shutil.which("afplay"):
        subprocess.Popen(["afplay", "/System/Library/Sounds/Hero.aiff"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def main() -> None:
    data = read_input()
    cfg = config()
    test_cmd = (cfg.get("commands") or {}).get("test")
    changes = git_changes()

    if cfg.get("verifyOnStop") and test_cmd and changes and not data.get("stop_hook_active"):
        try:
            p = subprocess.run(test_cmd, shell=True, cwd=PROJECT, capture_output=True, text=True, timeout=600)
            failed, output = p.returncode != 0, p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            failed, output = True, "(timeout)"
        if failed:
            tail = "\n".join(output.strip().splitlines()[-60:])
            print(json.dumps({"decision": "block",
                              "reason": f"[harness] `{test_cmd}` が失敗しています。直してから完了してください。\n{tail}"},
                             ensure_ascii=False))
            return

    notify(cfg)
    if changes:
        print(json.dumps({"systemMessage": f"[harness] 未コミットの変更 {len(changes)} 件"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
