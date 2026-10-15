#!/usr/bin/env python3
"""E7 read-only disposition measurement for the seal entries that still fail `sha256sum -c`.

For every failing entry it answers one question: are the SEALED BYTES RECOVERABLE, and if so
from what proof?

  witness      some other file in the worktree whose bytes hash to the seal
  placement    the seal is reproduced by re-inserting CR before a subset of the line breaks of
               the committed (HEAD) rendering, and exactly one subset works
  none         neither, so the sealed bytes are gone and the entry is not repairable

Prints one TSV row per entry to stdout. Writes nothing.
"""
import hashlib
import itertools
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
HDR = "path\tseal_sha256\tdisk_sha256\thead_sha256\tdisk_eq_seal\thead_eq_seal\twitness\tplacement\tverdict"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def seal_of(entry: pathlib.Path) -> str | None:
    man = entry.parent / "SHA256SUMS.txt"
    for line in man.read_bytes().decode("utf8", "replace").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].lstrip("* ") == entry.name:
            return parts[0].lower()
    return None


def git_blob(rel: str) -> bytes | None:
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def byte_index(seal: str, skip: pathlib.Path) -> list[str]:
    hits = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p == skip:
            continue
        posix = p.relative_to(ROOT).as_posix()
        if posix.startswith(".git/") or posix.startswith("vendor/") or "E7_SEAL_DISPOSITION_V0/before/" in posix:
            continue
        try:
            if sha(p.read_bytes()) == seal:
                hits.append(posix)
        except OSError:
            pass
    return hits


def placement_search(base: bytes, seal: str, cap: int = 24) -> tuple[str, bytes | None]:
    """Insert CR before subsets of the line breaks of `base` and look for `seal`."""
    folds = base.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    breaks = [i for i, c in enumerate(folds) if c == 10]
    if not breaks or len(breaks) > cap:
        return f"SKIPPED ({len(breaks)} breaks > {cap})", None
    hits = []
    for r in range(len(breaks) + 1):
        for combo in itertools.combinations(breaks, r):
            s = set(combo)
            out = bytearray()
            for i, c in enumerate(folds):
                if i in s:
                    out.append(13)
                out.append(c)
            cand = bytes(out)
            if sha(cand) == seal:
                hits.append(cand)
    if len(hits) == 1:
        return f"1 unique placement of 2^{len(breaks)}", hits[0]
    return f"{len(hits)} placements", None


def main() -> int:
    entries = sys.argv[1:]
    print(HDR)
    if not entries:
        entries = [
            (d.parent.relative_to(ROOT) / l.split(":")[0]).as_posix()
            for d in sorted((ROOT / "evidence").glob("*/SHA256SUMS.txt"))
            for l in subprocess.run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=d.parent, capture_output=True, text=True).stdout.splitlines()
            if "no coincide" in l.lower() and "atención" not in l.lower()
        ]
    for rel in entries:
        entry = ROOT / rel
        seal = seal_of(entry)
        disk = sha(entry.read_bytes())
        blob = git_blob(rel)
        head = sha(blob) if blob is not None else "UNTRACKED"
        if disk == seal:
            verdict, wit, place = "OK-already", "", ""
        elif seal is None:
            verdict, wit, place = "NO-SEAL-LINE", "", ""
        else:
            wit = byte_index(seal, entry)
            if wit:
                verdict, place = "RECOVERABLE-witness", ""
            else:
                code, cand = placement_search(blob or entry.read_bytes(), seal)
                place = code
                verdict = "RECOVERABLE-placement" if cand is not None else "NOT_RECOVERABLE"
        print(f"{rel}\t{seal}\t{disk}\t{head}\t{'YES' if disk == seal else 'no'}\t"
              f"{'YES' if head == seal else 'no'}\t{';'.join(wit) if wit else 'NONE'}\t{place}\t{verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
