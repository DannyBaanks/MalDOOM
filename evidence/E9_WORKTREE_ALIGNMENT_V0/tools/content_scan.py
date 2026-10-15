#!/usr/bin/env python3
"""E9 pre-track content scan: what would this commit publish?

Tracking 79 previously untracked files puts their bytes on a **public** GitHub remote, so the scan runs
before `git add`, not after. It reports size, CR/NUL counts, binary-ness, and hits for credential
markers, absolute workstation paths, hostnames and sibling private-repo names. It never edits anything.

    python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/content_scan.py
"""
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
ENV = {**os.environ, "LC_ALL": "C.UTF-8"}

PATTERNS = {
    "credential": re.compile(rb"(?i)(api[_-]?key|secret[_-]?key|passw(?:or)?d|token|BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|xox[baprs]-)"),
    "abs-path": re.compile(rb"(/home/[a-z0-9_.-]+|/Users/[a-z0-9_.-]+|C:\\\\Users\\\\|C:\\\\Development)"),
    "hostname": re.compile(rb"(?i)(desktop-[a-z0-9-]+|laptop-[a-z0-9-]+)"),
    "private-sibling": re.compile(rb"(Walbolge|Autobolge|Malbolge-Translator|Malbolge-Engine|ISyCo Git)"),
}


def main() -> int:
    lst = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=ROOT,
                         capture_output=True, env=ENV).stdout.decode().splitlines()
    paths = sorted(l[3:] for l in lst if l.startswith("?? "))
    e9 = "evidence/E9_WORKTREE_ALIGNMENT_V0/"
    foreign = [p for p in paths if not p.startswith(e9)]
    mine = [p for p in paths if p.startswith(e9)]

    print("# E9 pre-track content scan")
    print(f"# untracked total: {len(paths)} | foreign (to track): {len(foreign)} | this experiment's own files: {len(mine)}")
    print()
    tot = 0
    hits = {k: [] for k in PATTERNS}
    hits["binary"] = []
    bin_ct = cr_ct = nul_ct = 0
    for p in foreign:
        b = (ROOT / p).read_bytes()
        tot += len(b)
        nul = b.count(b"\x00")
        cr = b.count(b"\r")
        nul_ct += nul
        cr_ct += cr
        binary = nul > 0 or b[:4] in (b"\x7fELF", b"MZ\x90\x00")
        bin_ct += binary
        for name, rx in PATTERNS.items():
            for m in rx.finditer(b):
                ln = b[:m.start()].count(b"\n") + 1
                hits[name].append(f"{p}:{ln}: {b[max(0, m.start() - 40):m.end() + 40]!r}")
        if binary:
            hits["binary"].append(f"{p}: size={len(b)} NUL={nul}")

    print(f"total bytes to publish: {tot} ({tot/1e6:.2f} MB) | files containing NUL: {bin_ct} | CR bytes: {cr_ct} | NUL bytes: {nul_ct}")
    print()
    for name, rows in hits.items():
        print(f"## {name}: {len(rows)} hit(s)")
        for r in rows[:60]:
            print("  " + r)
        if len(rows) > 60:
            print(f"  … {len(rows)-60} more")
        print()
    print("## largest 8 files")
    for p, s in sorted(((p, (ROOT / p).stat().st_size) for p in foreign), key=lambda x: -x[1])[:8]:
        print(f"  {s:>12,}  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
