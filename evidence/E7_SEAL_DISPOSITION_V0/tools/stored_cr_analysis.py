#!/usr/bin/env python3
"""E7 collateral analysis: for every sealed entry whose WORKTREE matches the seal but whose stored
blob (HEAD) does not, test the single hypothesis "the stored blob is the worktree with every
carriage return removed".

Run from the repo root:  python3 evidence/E7_SEAL_DISPOSITION_V0/tools/stored_cr_analysis.py
Read-only.
"""
import os
import subprocess
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from disposition import ROOT, sha  # noqa: E402

ENV = {**os.environ, "LC_ALL": "C.UTF-8"}


def fold(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def main() -> int:
    stripped = other = absent = 0
    print("# E7 collateral analysis — worktree == seal, HEAD != seal")
    print("# hypothesis: HEAD bytes == worktree bytes with every CR removed (index-time normalisation)")
    print()
    print("path\tseal\tHEAD\trelation")
    for man in sorted((ROOT / "evidence").rglob("SHA256SUMS.txt")):
        for line in man.read_bytes().decode("utf8", "replace").splitlines():
            parts = line.split()
            if len(parts) < 2 or len(parts[0]) != 64:
                continue
            seal, name = parts[0].lower(), parts[1].lstrip("* ")
            target = man.parent / name
            if not target.is_file():
                target = ROOT / name
            if not target.is_file():
                continue
            work = target.read_bytes()
            if sha(work) != seal:
                continue
            rel = target.relative_to(ROOT).as_posix()
            r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, env=ENV)
            if r.returncode != 0:
                absent += 1
                print(f"{rel}\t{seal[:12]}\tABSENT\tnot in HEAD")
                continue
            if sha(r.stdout) == seal:
                continue
            if r.stdout == fold(work):
                stripped += 1
                print(f"{rel}\t{seal[:12]}\t{sha(r.stdout)[:12]}\tCR-STRIPPED (HEAD {len(r.stdout)}B vs worktree {len(work)}B)")
            else:
                other += 1
                print(f"{rel}\t{seal[:12]}\t{sha(r.stdout)[:12]}\tOTHER (HEAD {len(r.stdout)}B vs worktree {len(work)}B)")
    print()
    print(f"# hypothesis holds for {stripped} entries; {other} entries differ in another way; "
          f"{absent} sealed entries are not in HEAD at all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
