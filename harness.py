#!/usr/bin/env python3
"""claude-harness: ベースハーネスを各リポジトリへ配布・同期する CLI。

    python3 harness.py init <repo>            # リポジトリにハーネスを導入（registry にも登録）
    python3 harness.py sync <repo>... | --all # 最新のベースに同期
    python3 harness.py status [<repo>... | --all]
    python3 harness.py install-user           # ~/.claude/skills/harness を配置
    python3 harness.py list

ファイルの扱い:
    base/      → 管理ファイル。常にベースの内容で上書き（ローカル改変があれば conflict として停止）
    seed/      → 初回のみコピー。以後はリポジトリ側の持ち物
    settings/base.json + <repo>/.claude/settings.repo.json → <repo>/.claude/settings.json を生成
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path

HOME = Path(__file__).resolve().parent
BASE_DIR = HOME / "base"
SEED_DIR = HOME / "seed"
BASE_SETTINGS = HOME / "settings" / "base.json"
MANIFEST = HOME / "manifest.json"
REGISTRY = HOME / "registry.json"

LOCK_REL = ".claude/harness.lock.json"
SETTINGS_REL = ".claude/settings.json"
OVERLAY_REL = ".claude/settings.repo.json"


# ---------------------------------------------------------------- utils

def version() -> str:
    return (HOME / "VERSION").read_text().strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def dump_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def manifest() -> dict:
    return load_json(MANIFEST, {})


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts:
            yield p.relative_to(root).as_posix()


# ---------------------------------------------------------------- settings merge

def normalize_rule(value):
    """`Bash(git status:*)` と `Bash(git status *)` を同一視する。"""
    if isinstance(value, str) and value.endswith(":*)"):
        return value[:-3] + " *)"
    return value


def merge(base, overlay):
    """overlay を base に重ねる。dict は再帰、list は和集合（重複除去）、スカラーは overlay 優先。"""
    if isinstance(base, dict) and isinstance(overlay, dict):
        out = dict(base)
        for k, v in overlay.items():
            out[k] = merge(base[k], v) if k in base else v
        return out
    if isinstance(base, list) and isinstance(overlay, list):
        out = list(base)
        seen = {json.dumps(normalize_rule(x), sort_keys=True) for x in base}
        for item in overlay:
            key = json.dumps(normalize_rule(item), sort_keys=True)
            if key not in seen:
                out.append(item)
                seen.add(key)
        return out
    return overlay


def subtract(current, base):
    """current のうち base に無い部分だけを返す（= リポジトリ固有の設定）。無ければ None。"""
    if isinstance(current, dict) and isinstance(base, dict):
        out = {}
        for k, v in current.items():
            if k not in base:
                out[k] = v
                continue
            d = subtract(v, base[k])
            if d is not None:
                out[k] = d
        return out or None
    if isinstance(current, list) and isinstance(base, list):
        seen = {json.dumps(normalize_rule(x), sort_keys=True) for x in base}
        out = [x for x in current if json.dumps(normalize_rule(x), sort_keys=True) not in seen]
        return out or None
    return None if current == base else current


def strip_legacy(settings: dict) -> dict:
    """manifest.legacyHookCommands に一致する旧フックを取り除く（ベース側の新フックと重複するため）。"""
    legacy = set(manifest().get("legacyHookCommands", []))
    hooks = settings.get("hooks")
    if not legacy or not isinstance(hooks, dict):
        return settings
    for event in list(hooks):
        groups = []
        for g in hooks[event]:
            hs = [h for h in g.get("hooks", []) if h.get("command") not in legacy]
            if hs:
                groups.append(dict(g, hooks=hs))
        if groups:
            hooks[event] = groups
        else:
            del hooks[event]
    if not hooks:
        settings.pop("hooks", None)
    return settings


def render_settings(repo: Path) -> str:
    overlay = load_json(repo / OVERLAY_REL, {}) or {}
    return dump_json(merge(load_json(BASE_SETTINGS), overlay))


# ---------------------------------------------------------------- registry

def registry() -> list:
    return load_json(REGISTRY, {"repos": []})["repos"]


def register(repo: Path) -> None:
    repos = registry()
    home = str(Path.home())
    p = str(repo)
    display = "~" + p[len(home):] if p.startswith(home) else p
    if display not in repos and p not in repos:
        repos.append(display)
        REGISTRY.write_text(dump_json({"repos": repos}))
        print(f"  registered {display}")


def resolve_targets(args) -> list:
    if getattr(args, "all", False):
        return [Path(os.path.expanduser(r)).resolve() for r in registry()]
    return [Path(os.path.expanduser(r)).resolve() for r in (args.repos or ["."])]


# ---------------------------------------------------------------- sync core

class Result:
    def __init__(self, repo: Path):
        self.repo = repo
        self.changed, self.added, self.removed, self.conflicts, self.seeded = [], [], [], [], []

    def report(self, dry: bool) -> None:
        tag = "[dry-run] " if dry else ""
        print(f"\n{tag}{self.repo}")
        for label, items in (("added", self.added), ("updated", self.changed), ("removed", self.removed),
                             ("seeded", self.seeded), ("CONFLICT", self.conflicts)):
            for i in items:
                print(f"  {label:9} {i}")
        if not any((self.changed, self.added, self.removed, self.conflicts, self.seeded)):
            print("  up to date")


def sync_repo(repo: Path, dry: bool = False, force: bool = False) -> Result:
    if not (repo / ".git").exists():
        raise SystemExit(f"not a git repository: {repo}")
    res = Result(repo)
    lock = load_json(repo / LOCK_REL, {}) or {}
    old_files: dict = lock.get("files", {})
    new_files: dict = {}

    def write(rel: str, data: bytes) -> None:
        if dry:
            return
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        if rel.endswith(".py") or rel.endswith(".sh"):
            dst.chmod(0o755)

    # 1. managed files
    for rel in iter_files(BASE_DIR):
        src = BASE_DIR / rel
        dst = repo / rel
        new_hash = sha(src)
        new_files[rel] = new_hash
        if not dst.exists():
            res.added.append(rel)
            write(rel, src.read_bytes())
            continue
        cur = sha(dst)
        if cur == new_hash:
            continue
        locally_modified = cur != old_files.get(rel)
        if locally_modified and not force:
            res.conflicts.append(rel)
            new_files[rel] = old_files.get(rel, cur)  # 未解決のまま lock は進めない
            continue
        res.changed.append(rel)
        write(rel, src.read_bytes())

    # 2. files dropped from base (+ manifest.removed)
    to_remove = [r for r in old_files if r not in new_files] + manifest().get("removed", [])
    for rel in dict.fromkeys(to_remove):
        dst = repo / rel
        if not dst.exists():
            continue
        if rel in old_files and sha(dst) != old_files[rel] and not force:
            res.conflicts.append(f"{rel} (removed upstream, modified locally)")
            continue
        res.removed.append(rel)
        if not dry:
            dst.unlink()

    # 3. seed files (copy once)
    for rel in iter_files(SEED_DIR):
        if not (repo / rel).exists():
            res.seeded.append(rel)
            write(rel, (SEED_DIR / rel).read_bytes())

    # 4. settings.json = base + overlay. 直接編集されていたら差分を overlay に退避する
    settings_path = repo / SETTINGS_REL
    overlay_path = repo / OVERLAY_REL
    if settings_path.exists() and sha(settings_path) != lock.get("settings"):
        current = strip_legacy(load_json(settings_path, {}) or {})
        extra = subtract(current, load_json(BASE_SETTINGS))
        if extra:
            merged = merge(load_json(overlay_path, {}) or {}, extra)
            if not dry:
                overlay_path.write_text(dump_json(merged))
            res.changed.append(f"{OVERLAY_REL} (captured local settings)")
    rendered = render_settings(repo) if not dry else None
    if dry:
        res.changed.append(SETTINGS_REL + " (regenerate if changed)")
    elif not settings_path.exists() or settings_path.read_text() != rendered:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(rendered)
        res.changed.append(SETTINGS_REL)

    # 5. .gitignore
    gi = repo / ".gitignore"
    existing = gi.read_text().splitlines() if gi.exists() else []
    missing = [l for l in manifest().get("gitignore", []) if l not in existing]
    if missing:
        res.changed.append(".gitignore (+%d lines)" % len(missing))
        if not dry:
            body = "\n".join(existing).rstrip("\n")
            gi.write_text((body + "\n\n" if body else "") + "# claude-harness\n" + "\n".join(missing) + "\n")

    # 6. lock
    if not dry:
        (repo / LOCK_REL).write_text(dump_json({
            "version": version(),
            "source": str(HOME).replace(str(Path.home()), "~", 1),
            "synced_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "settings": sha(settings_path),
            "files": new_files,
        }))
    res.report(dry)
    return res


# ---------------------------------------------------------------- commands

def cmd_init(args) -> int:
    rc = 0
    for repo in resolve_targets(args):
        print(f"init {repo}")
        res = sync_repo(repo, dry=args.dry_run, force=args.force)
        if not args.dry_run:
            register(repo)
        rc |= bool(res.conflicts)
    return rc


def cmd_sync(args) -> int:
    rc = 0
    print(f"claude-harness v{version()}")
    for repo in resolve_targets(args):
        if not repo.exists():
            print(f"\n{repo}\n  MISSING (registry.json から削除してください)")
            rc = 1
            continue
        res = sync_repo(repo, dry=args.dry_run, force=args.force)
        rc |= bool(res.conflicts)
    if rc:
        print("\nconflict あり: ローカル改変を settings.repo.json / CLAUDE.md へ移すか、ベースへ取り込んでから再実行（--force で上書き）")
    return rc


def cmd_status(args) -> int:
    print(f"claude-harness v{version()}  ({HOME})")
    for repo in resolve_targets(args):
        lock = load_json(repo / LOCK_REL)
        if lock is None:
            print(f"  {repo}: not installed")
            continue
        drift = [r for r, h in lock.get("files", {}).items()
                 if not (repo / r).exists() or sha(repo / r) != h]
        state = "up to date" if lock["version"] == version() else f"outdated ({lock['version']} -> {version()})"
        print(f"  {repo}: v{lock['version']} {state}" + (f", drift: {', '.join(drift)}" if drift else ""))
    return 0


def cmd_install_user(args) -> int:
    dst = Path.home() / ".claude" / "skills" / "harness"
    dst.mkdir(parents=True, exist_ok=True)
    for rel in iter_files(HOME / "user" / "skills" / "harness"):
        text = (HOME / "user/skills/harness" / rel).read_text().replace("{{HARNESS_HOME}}", str(HOME))
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        (dst / rel).write_text(text)
    print(f"installed user skill -> {dst}")
    return 0


def cmd_list(args) -> int:
    for r in registry():
        print(r)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("init", cmd_init), ("sync", cmd_sync), ("status", cmd_status)):
        s = sub.add_parser(name)
        s.add_argument("repos", nargs="*")
        s.add_argument("--all", action="store_true", help="registry.json の全リポジトリ")
        if name != "status":
            s.add_argument("--dry-run", action="store_true")
            s.add_argument("--force", action="store_true", help="ローカル改変を上書き")
        s.set_defaults(fn=fn)
    sub.add_parser("install-user").set_defaults(fn=cmd_install_user)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
