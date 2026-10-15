#!/usr/bin/env python3
"""E7 direct proof, per repaired path, that worktree bytes, the seal and the staged blob agree.

Run from the repo root, AFTER `git add` of the repaired files:
  python3 evidence/E7_SEAL_DISPOSITION_V0/tools/staged_blob_check.py
Read-only.
"""
import os
import subprocess
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from disposition import ROOT, seal_of, sha  # noqa: E402

TABLE = pathlib.Path(__file__).resolve().parent.parent / "raw" / "01_disposition_table.tsv"
ENV = {**os.environ, "LC_ALL": "C.UTF-8"}


def main() -> int:
    rows = [l.split("\t") for l in TABLE.read_text().splitlines()]
    hdr, data = rows[0], rows[1:]
    print("# E7 staged-blob check for the entries classified RECOVERABLE (seal == worktree == index)")
    print("path\tseal\tworktree\tstaged_blob\tall_three_equal")
    equal = 0
    for r in data:
        if len(r) != len(hdr):
            continue
        rec = dict(zip(hdr, r))
        if not rec["verdict"].startswith("RECOVERABLE"):
            continue
        rel = rec["path"]
        entry = ROOT / rel
        seal = seal_of(entry)
        disk = sha(entry.read_bytes())
        idx = subprocess.run(["git", "show", f":{rel}"], cwd=ROOT, capture_output=True, env=ENV)
        blob = sha(idx.stdout) if idx.returncode == 0 else "NOT-STAGED"
        ok = seal == disk == blob
        equal += ok
        print(f"{rel}\t{seal}\t{disk}\t{blob}\t{'YES' if ok else 'NO'}")
    print(f"# all-three-equal rows: {equal}")
    return 0 if equal == 8 else 1


if __name__ == "__main__":
    sys.exit(main())
