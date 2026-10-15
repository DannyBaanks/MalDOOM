#!/usr/bin/env python3
"""E9 baseline (read-only): every seal in the repo, every tracked divergence, every untracked file.

Unlike E6/E7/E8 this scan walks **all** manifests on disk, because `vendor/` carries three manifests
that the earlier rounds never counted. Run from the repo root:

    python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/baseline.py

Read-only: no file is written and no Git command that mutates state is invoked.
"""
import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
ENV = {**os.environ, "LC_ALL": "C.UTF-8"}
CR = b"\r"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, env=ENV)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fold(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def manifests():
    """Every SHA256SUMS-style manifest on disk, tracked or not."""
    return [p for p in sorted(ROOT.rglob("SHA256SUMS*.txt")) if ".git" not in p.parts]


def entries(man: pathlib.Path):
    """Canonical parser shared with E7/E8: 64-hex first field, name may carry a `* ` binary flag."""
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
        yield parts[0].lower(), name, target


def seal_map():
    """path -> [(seal, manifest)] over every manifest on disk."""
    out = {}
    for man in manifests():
        for seal, _name, target in entries(man):
            if target.is_file():
                out.setdefault(target.resolve().relative_to(ROOT).as_posix(), []).append(
                    (seal, man.relative_to(ROOT).as_posix()))
    return out


def tally(group: str):
    total = ok = 0
    for man in manifests():
        rel = man.relative_to(ROOT).as_posix()
        if group == "evidence" and not rel.startswith("evidence/"):
            continue
        if group == "vendor" and not rel.startswith("vendor/"):
            continue
        for _seal, _name, target in entries(man):
            total += 1
            if target.is_file() and sha(target.read_bytes()) == _seal:
                ok += 1
    return ok, total


def main() -> int:
    man_paths = manifests()
    tracked = sorted(f.decode() for f in git("ls-files", "-z").stdout.split(b"\0") if f)
    untracked = sorted(f.decode()[3:] for f in git("status", "--porcelain", "-uall", "-z").stdout.split(b"\0")
                       if f.startswith(b"?? "))
    seals = seal_map()

    print("# E9 baseline — seals, divergences, untracked")
    print(f"# repo: {ROOT}")
    print(f"# tracked files: {len(tracked)} | manifests on disk: {len(man_paths)} | untracked files: {len(untracked)}")
    print()

    print("## seal verification by manifest group (worktree side)")
    for group in ("evidence", "vendor"):
        ok, total = tally(group)
        print(f"{group}/** : {ok} of {total} entries verify against the worktree")
    print()

    print("## tracked files where worktree != HEAD")
    print("path\tsize_worktree\tsize_HEAD\trelation\tseal_status")
    div = []
    for rel in tracked:
        p = ROOT / rel
        if not p.is_file():
            continue
        r = git("show", f"HEAD:{rel}")
        if r.returncode != 0:
            continue
        w = p.read_bytes()
        if w == r.stdout:
            continue
        div.append(rel)
        if w == r.stdout.replace(b"\n", b"\r\n"):
            relation = "CRLF-PAIRS-EXACT"          # fold() and re-CRLF() are both exact
        elif r.stdout == fold(w):
            relation = "CR-STRIPPED"               # CRs were not all in CRLF pairs
        else:
            relation = "OTHER"
        listed = seals.get(rel, [])
        if not listed:
            seal_status = "unsealed"
        elif any(sha(w) == s for s, _ in listed):
            seal_status = "VERIFIES-BY-SEAL"
        else:
            seal_status = "listed-not-verifying:" + ",".join(m for _, m in listed)
        print(f"{rel}\t{len(w)}\t{len(r.stdout)}\t{relation}\t{seal_status}")
    print(f"# divergent total: {len(div)}")
    print()

    print("## untracked files (candidate to track)")
    print("path\tsize\tCR\tsha256")
    for rel in untracked:
        b = (ROOT / rel).read_bytes()
        ncr = b.count(CR)
        print(f"{rel}\t{len(b)}\t{ncr}\t{sha(b)}")
    print(f"# untracked total: {len(untracked)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
