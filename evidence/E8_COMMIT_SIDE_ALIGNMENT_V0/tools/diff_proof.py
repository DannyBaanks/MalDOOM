#!/usr/bin/env python3
"""E8 read-only proof that the staged content differs from HEAD by carriage returns and nothing else.

For every path that E8 restaged, compare three things:

  staged (git show :<path>)   HEAD (git show HEAD:<path>)   seal (SHA256SUMS.txt)

and assert  SHA-256(staged) == seal  and  fold(staged) == HEAD, where fold() drops every CR. If both
hold, the commit E8 is about to make cannot introduce a byte that is not a carriage return: the
content is the content that was already published, restored to the bytes the seal describes.

Also re-runs the worktree tally (`sha256sum -c` per manifest, LC_ALL=C.UTF-8) to show that E8 leaves
the working tree exactly as it found it.
"""
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from measure import ROOT, entries, fold, git, sha  # noqa: E402

ENV = {**os.environ, "LC_ALL": "C.UTF-8"}
HDR = "path\tseal\tstaged\thead\tstaged_eq_seal\tfold_staged_eq_head\tresult"


def restaged_paths() -> list[str]:
    raw = HERE.parent / "raw" / "02_restage_record.tsv"
    return [f.split("\t")[0] for f in (l.rstrip("\n") for l in raw.read_text().splitlines())
            if len(f.split("\t")) == 7 and f.split("\t")[6] == "RESTAGED"]


def main() -> int:
    seals = {}
    for _man, seal, _name, target in entries():
        if target is not None:
            seals.setdefault(target.relative_to(ROOT).as_posix(), seal)
    ok = bad = 0
    print(HDR)
    for rel in restaged_paths():
        staged = git("show", f":{rel}").stdout
        head = git("show", f"HEAD:{rel}").stdout
        seal = seals.get(rel, "?")
        a, b = sha(staged) == seal, fold(staged) == head
        ok += a and b
        bad += not (a and b)
        print(f"{rel}\t{seal[:16]}\t{sha(staged)[:16]}\t{sha(head)[:16]}\t"
              f"{'YES' if a else 'no'}\t{'YES' if b else 'no'}\t"
              f"{'CR-ONLY' if a and b else 'REFUSE-COMMIT'}")
    print(f"# paths proved CR-only: {ok}   unproven: {bad}")
    print()
    print("# worktree tally after restaging (must be unchanged: E8 touches no file on disk)")
    total = ok_n = fail = 0
    for man in sorted((ROOT / "evidence").rglob("SHA256SUMS.txt")):
        r = subprocess.run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=man.parent,
                           capture_output=True, text=True, env=ENV)
        o = r.stdout.count(": OK")
        f = r.stdout.count(": FAILED")
        total += o + f
        ok_n += o
        fail += f
        if f:
            print(f"# {man.parent.relative_to(ROOT).as_posix()}: OK={o} FAILED={f}")
    print(f"# repo-wide sealed entries={total}  OK={ok_n}  FAILED={fail}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
