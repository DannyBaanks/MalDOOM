#!/usr/bin/env python3
"""E7 guarded repair: restore the recoverable sealed bytes, refuse everything else.

Refusal by default. A file is written only if ALL of these hold at the moment of the write:

  1. its current bytes equal the `disk_sha256` recorded in the disposition table (nothing else
     touched the file in between);
  2. a candidate for the sealed bytes is available, either as a byte-exact witness file in the
     worktree or as the single CR placement of the committed rendering that hashes to the seal;
  3. SHA-256(candidate) == the seal recorded in that directory's SHA256SUMS.txt.

The candidate is written to <name>.repairtmp and moved into place with os.replace(), and the
pre-repair bytes are copied to E7/before/ first so the action is reversible byte for byte.
Entries classified NOT_RECOVERABLE are never written. Prints a record row per attempt.
"""
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from disposition import ROOT, placement_search, sha  # noqa: E402

HDR = "path\tseal_sha256\tbefore_sha256\tafter_sha256\tsource\tbytes_before\tbytes_after\tresult"


def main(table: pathlib.Path) -> int:
    rows = [l.split("\t") for l in table.read_text().splitlines()]
    hdr = rows[0]
    data = [r for r in rows[1:] if len(r) == len(hdr)]
    print(HDR)
    written = refused = 0
    for r in data:
        rec = dict(zip(hdr, r))
        rel, seal, disk_sha, verdict = rec["path"], rec["seal_sha256"], rec["disk_sha256"], rec["verdict"]
        target = ROOT / rel
        if not verdict.startswith("RECOVERABLE"):
            print(f"{rel}\t{seal}\t{disk_sha}\t-\t-\t{target.stat().st_size}\t-\tREFUSED-not-recoverable")
            refused += 1
            continue
        if sha(target.read_bytes()) != disk_sha:
            print(f"{rel}\t{seal}\t{disk_sha}\t-\t-\t-\t-\tREFUSED-disk-changed-since-measurement")
            refused += 1
            continue
        if verdict.endswith("witness"):
            wit = rec["witness"].split(";")[0]
            cand = (ROOT / wit).read_bytes()
            source = f"witness:{wit}"
        else:
            base = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True).stdout
            code, cand = placement_search(base, seal)
            source = f"placement:{code}"
            if cand is None:
                print(f"{rel}\t{seal}\t{disk_sha}\t-\t{source}\t{target.stat().st_size}\t-\tREFUSED-no-unique-placement")
                refused += 1
                continue
        if sha(cand) != seal:
            print(f"{rel}\t{seal}\t{disk_sha}\t-\t{source}\t{target.stat().st_size}\t-\tREFUSED-candidate-not-seal")
            refused += 1
            continue
        backup = HERE.parent / "before" / rel.replace("/", "__")
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(target, backup)
        tmp = target.with_name(target.name + ".repairtmp")
        tmp.write_bytes(cand)
        os.replace(tmp, target)
        after = sha(target.read_bytes())
        ok = after == seal
        print(f"{rel}\t{seal}\t{disk_sha}\t{after}\t{source}\t{backup.stat().st_size}\t{len(cand)}\t"
              f"{'REPAIRED' if ok else 'FAILED-VERIFY'}")
        written += ok
    print(f"# summary: repaired={written} refused={refused}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1
                  else HERE.parent / "raw" / "01_disposition_table.tsv"))
