#!/usr/bin/env python3
"""E7 proof of irrecoverability for the entries classified NOT_RECOVERABLE.

Three independent searches are run for each failing seal, so "not recoverable" is a measured
statement about this machine, not an assumption:

  1. worktree  — every file outside .git/, vendor/ and E7/before/ is hashed and compared to the seal;
  2. object DB — every blob in the repository (including dangling ones) is hashed and compared;
  3. dir       — the full `sha256sum -c` verdict for every entry of that directory's manifest, which
     shows exactly how many sibling entries still verify.

Read-only.  Run from the repo root:
  python3 evidence/E7_SEAL_DISPOSITION_V0/tools/not_recoverable_proof.py
"""
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from disposition import ROOT, byte_index, seal_of, sha  # noqa: E402

TABLE = pathlib.Path(__file__).resolve().parent.parent / "raw" / "01_disposition_table.tsv"


def all_blob_hashes() -> dict[str, list[str]]:
    """sha256(content) -> [blob oid, ...] for every blob object in the repo, reachable or dangling."""
    listing = subprocess.run(["git", "cat-file", "--batch-all-objects", "--batch-check"],
                             cwd=ROOT, capture_output=True, text=True).stdout
    by_sha: dict[str, list[str]] = {}
    for line in listing.splitlines():
        oid, kind, _size = line.split()
        if kind != "blob":
            continue
        data = subprocess.run(["git", "cat-file", "blob", oid], cwd=ROOT, capture_output=True).stdout
        by_sha.setdefault(sha(data), []).append(oid)
    return by_sha


def main() -> int:
    rows = [l.split("\t") for l in TABLE.read_text().splitlines()]
    hdr, data = rows[0], rows[1:]
    blobs = all_blob_hashes()
    n_blobs = sum(len(v) for v in blobs.values())

    print(f"# E7 irrecoverability proof — {n_blobs} blob objects scanned in the object database")
    print("# and every worktree file outside .git/, vendor/, E7/before/ scanned for each seal.")
    print()
    for r in data:
        rec = dict(zip(hdr, r))
        if not rec["verdict"].startswith("NOT_RECOVERABLE"):
            continue
        rel, seal = rec["path"], rec["seal_sha256"]
        entry = ROOT / rel
        man = entry.parent / "SHA256SUMS.txt"
        print(f"{rel}")
        print(f"  seal                     = {seal}")
        print(f"  disk now                 = {sha(entry.read_bytes())}")
        print(f"  tracked in HEAD?         = {rec['head_sha256'] != 'UNTRACKED'}")
        print(f"  worktree files == seal   = {len(byte_index(seal, entry))}")
        print(f"  repo blobs == seal       = {len(blobs.get(seal, []))}")
        print(f"  CR-placement search      = {rec['placement'] or 'n/a'}")
        verdicts = subprocess.run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=man.parent,
                                  capture_output=True, text=True,
                                  env={**os.environ, "LC_ALL": "C.UTF-8"}).stdout.splitlines()
        ok = [v.split(":")[0] for v in verdicts if v.endswith(": OK")]
        bad = [v.split(":")[0] for v in verdicts if v.endswith(": FAILED")]
        print(f"  manifest {man.relative_to(ROOT)}: {len(ok)} entries verify, failing = {bad}")
        if rel.endswith("SHA256SUMS.txt"):
            self_lines = [l for l in man.read_bytes().decode("utf8", "replace").splitlines()
                          if "SHA256SUMS.txt" in l]
            print(f"  self-referential seal line(s) = {self_lines}")
            print("  -> the sealed bytes of a manifest that hashes itself cannot be produced by any")
            print("     edit that leaves the hash true: the file would have to contain SHA-256 of a")
            print("     file that already contains that SHA-256. Not a repair; a rewrite of a sealed manifest.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
