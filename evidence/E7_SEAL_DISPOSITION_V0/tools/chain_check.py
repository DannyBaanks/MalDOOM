#!/usr/bin/env python3
"""E7 three-way chain check: for every entry of every evidence manifest, compare

    seal (SHA256SUMS.txt)  ==  worktree bytes  ==  stored bytes (HEAD blob, or the staged index)

Prints one aggregate block plus one line per mismatch. Read-only.

Run from the repo root:  python3 evidence/E7_SEAL_DISPOSITION_V0/tools/chain_check.py [HEAD|INDEX]
INDEX is what HEAD will become once the staged content is committed, so the same proof runs before
and after the commit.
"""
import subprocess
import sys
import pathlib
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from disposition import ROOT, sha  # noqa: E402

ENV = {**os.environ, "LC_ALL": "C.UTF-8"}
SOURCE = (sys.argv[1] if len(sys.argv) > 1 else "HEAD").upper()


def entries():
    for man in sorted((ROOT / "evidence").rglob("SHA256SUMS.txt")):
        for line in man.read_bytes().decode("utf8", "replace").splitlines():
            parts = line.split()
            if len(parts) < 2 or len(parts[0]) != 64:
                continue
            yield man, parts[0].lower(), parts[1].lstrip("* ")


def stored(rel: str) -> bytes | None:
    ref = "HEAD" if SOURCE == "HEAD" else ""
    r = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=ROOT, capture_output=True, env=ENV)
    return r.stdout if r.returncode == 0 else None


def main() -> int:
    total = disk_ok = head_ok = all_three = untracked = 0
    bad = []
    for man, seal, name in entries():
        total += 1
        target = man.parent / name
        if not target.is_file():
            target = ROOT / name
        if not target.is_file():
            bad.append(f"NO-FILE {man.relative_to(ROOT)} :: {name}")
            continue
        rel = target.relative_to(ROOT).as_posix()
        d = sha(target.read_bytes())
        blob = stored(rel)
        h = sha(blob) if blob is not None else None
        de, he = d == seal, h == seal
        disk_ok += de
        head_ok += bool(he)
        untracked += blob is None
        all_three += de and he
        if not (de and he):
            bad.append(f"{rel}  seal={seal[:12]}  disk={d[:12]}({'=' if de else 'x'})  "
                       f"{SOURCE}={(h[:12] if h else 'ABSENT')}({'=' if he else 'x'})")
    print(f"# E7 three-way chain check over all evidence manifests (repo-wide), stored side = {SOURCE}")
    print(f"# sealed entries total            = {total}")
    print(f"# worktree bytes == seal          = {disk_ok}")
    print(f"# {SOURCE} bytes   == seal          = {head_ok}")
    print(f"# disk == seal == {SOURCE} (3-way OK) = {all_three}")
    print(f"# entries absent from {SOURCE}        = {untracked}")
    print(f"# mismatches                      = {len(bad)}")
    print()
    for b in bad:
        print(b)
    return 0 if all_three == total else 1


if __name__ == "__main__":
    sys.exit(main())
