#!/usr/bin/env python3
"""E7 witness proof: for every entry classified RECOVERABLE-witness, list ALL files in the
worktree whose exact bytes hash to that entry's seal. Read-only; skips .git/, vendor/, E7/before/.

Run from the repo root:  python3 evidence/E7_SEAL_DISPOSITION_V0/tools/witness_proof.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from disposition import ROOT, byte_index, seal_of  # noqa: E402

TABLE = pathlib.Path(__file__).resolve().parent.parent / "raw" / "01_disposition_table.tsv"


def main() -> int:
    rows = [l.split("\t") for l in TABLE.read_text().splitlines()]
    hdr, data = rows[0], rows[1:]
    print("# E7 witness proof — every worktree file whose exact bytes hash to the seal of each")
    print("# entry classified RECOVERABLE-witness. The entry itself is excluded from the search.")
    print()
    for r in data:
        rec = dict(zip(hdr, r))
        if not rec["verdict"].endswith("witness"):
            continue
        entry = ROOT / rec["path"]
        seal = seal_of(entry)
        hits = byte_index(seal, entry)
        print(f"{rec['path']}")
        print(f"  seal                            = {seal}")
        print(f"  files hashing to the seal       = {len(hits)}")
        for h in sorted(hits):
            print(f"    - {h}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
