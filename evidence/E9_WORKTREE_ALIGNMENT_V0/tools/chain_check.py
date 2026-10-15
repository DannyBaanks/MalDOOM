#!/usr/bin/env python3
"""E9 three-way chain check — the same measurement E7/E8 published, so the rounds stay comparable.

For every sealed entry it compares three things and prints one line per mismatch:

    seal (from the manifest) | disk bytes | HEAD bytes

`--group evidence` restricts to `evidence/**` manifests, which is the denominator E7/E8 used (362
entries); `--group all` adds the three `vendor/**` manifests (10 more entries) that only E9 counts.

    python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/chain_check.py --group evidence
    python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/chain_check.py --group all

Read-only.
"""
import argparse
import hashlib
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
ENV = {**os.environ, "LC_ALL": "C.UTF-8"}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, env=ENV)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def entries(man: pathlib.Path):
    for line in man.read_bytes().decode("utf8", "replace").splitlines():
        parts = line.split()
        if len(parts) < 2 or len(parts[0]) != 64:
            continue
        try:
            int(parts[0], 16)
        except ValueError:
            continue
        name = parts[1].lstrip("* ")
        target = man.parent / name
        if not target.is_file():
            target = ROOT / name
        yield parts[0].lower(), target


def head_bytes(rel: str):
    r = git("show", f"HEAD:{rel}")
    return r.stdout if r.returncode == 0 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", choices=["evidence", "vendor", "all"], default="all")
    a = ap.parse_args()

    mans = [p for p in sorted(ROOT.rglob("SHA256SUMS*.txt")) if ".git" not in p.parts]
    if a.group != "all":
        mans = [m for m in mans if m.relative_to(ROOT).as_posix().startswith(a.group + "/")]

    total = disk_ok = head_ok = three = absent = 0
    bad = []
    for man in mans:
        for seal, target in entries(man):
            rel = target.relative_to(ROOT).as_posix()
            total += 1
            d = sha(target.read_bytes()) if target.is_file() else None
            hb = head_bytes(rel)
            h = sha(hb) if hb is not None else None
            if d == seal:
                disk_ok += 1
            if h == seal:
                head_ok += 1
            if d == seal == h:
                three += 1
            if h is None:
                absent += 1
            if not (d == seal == h):
                mark = lambda x, s: ("NONE" if x is None else x[:12]) + ("(=)" if x == s else "(x)")
                bad.append(f"{rel}  seal={seal[:12]}  disk={mark(d, seal)}  HEAD={mark(h, seal)}")

    print(f"# E9 three-way chain check over {a.group} manifests, stored side = HEAD")
    print(f"# manifests                     = {len(mans)}")
    print(f"# sealed entries total          = {total}")
    print(f"# disk bytes == seal            = {disk_ok}")
    print(f"# HEAD bytes == seal            = {head_ok}")
    print(f"# disk == seal == HEAD (3-way)  = {three}")
    print(f"# entries absent from HEAD      = {absent}")
    print(f"# mismatches                    = {len(bad)}")
    print()
    for line in bad:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
