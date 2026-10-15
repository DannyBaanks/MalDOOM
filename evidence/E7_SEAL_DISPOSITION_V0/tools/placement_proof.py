#!/usr/bin/env python3
"""E7 placement proof for evidence/UNSHACKLED_CONTINUATION_ANCHOR_V0/ABC.eir.

The committed blob lost one content byte (a trailing CR) to Git's line-ending conversion, so no
witness exists. The sealed bytes are recovered by re-inserting CR before a subset of the line
breaks of the committed rendering; the search is exhaustive over 2**n subsets and is accepted only
when exactly one subset reproduces the seal. Read-only.

Run from the repo root:  python3 evidence/E7_SEAL_DISPOSITION_V0/tools/placement_proof.py
"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from disposition import ROOT, placement_search, seal_of, sha  # noqa: E402

REL = "evidence/UNSHACKLED_CONTINUATION_ANCHOR_V0/ABC.eir"
HERE = pathlib.Path(__file__).resolve().parent.parent


def dump(tag: str, data: bytes) -> None:
    cr = data.count(b"\r")
    lf = data.count(b"\n")
    print(f"  {tag}: {len(data)} bytes, CR={cr}, LF={lf}")
    print(f"  {tag}: sha256={sha(data)}")
    print(f"  {tag}: raw bytes = {data!r}")


def main() -> int:
    entry = ROOT / REL
    man = entry.parent / "SHA256SUMS.txt"
    seal = seal_of(entry)
    base = subprocess.run(["git", "show", f"HEAD:{REL}"], cwd=ROOT, capture_output=True).stdout
    before = next(HERE.glob("before/*ABC.eir"), None)

    print(f"# E7 placement proof — {REL}")
    print(f"# seal line in {man.relative_to(ROOT)}: "
          f"{[l for l in man.read_bytes().decode('utf8','replace').splitlines() if entry.name in l][0]}")
    print()
    print("MEASURED STATES")
    if before:
        dump("before (worktree at measurement, full CRLF)", before.read_bytes())
    dump("HEAD blob (Git-committed rendering, conversion already applied)", base)
    print(f"  seal (target)              = {seal}")
    print()

    print("EXHAUSTIVE CR-PLACEMENT SEARCH over the line breaks of the HEAD blob")
    code, cand = placement_search(base, seal)
    folds = base.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    breaks = [i for i, c in enumerate(folds) if c == 10]
    print(f"  line breaks available      = {len(breaks)} -> 2**{len(breaks)} = {2 ** len(breaks)} subsets, "
          f"positions {breaks}")
    print(f"  search result              = {code}")
    if cand is None:
        print("  NO unique placement -> NOT RECOVERABLE by placement")
        return 1
    positions = [i for i, c in enumerate(cand) if c == 13]
    print(f"  unique winning subset      = CR inserted before byte offsets {positions} of the folded blob")
    dump("candidate", cand)
    print(f"  candidate == seal?         = {sha(cand) == seal}")
    print()

    print("POST-REPAIR STATE")
    dump("worktree", entry.read_bytes())
    print(f"  worktree == seal?          = {sha(entry.read_bytes()) == seal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
