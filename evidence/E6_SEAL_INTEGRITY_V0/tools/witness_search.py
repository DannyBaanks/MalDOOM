#!/usr/bin/env python3
"""Refine every seal-audit row that the line-ending rules could not explain.

`seal_audit.py` relates bytes with global CR/LF rules, so a file whose sealed
form carries CRs at only *some* of its line breaks looks like a content
difference. This tool answers that for each row where either side is CONTENT:

  same_text_modulo_cr   collapse(worktree) == collapse(HEAD): the two renderings
                        are the same bytes, only CR placement differs
  cr_placement          exhaustive search over CR placements of the collapsed
                        text, run only when there are <= 12 breaks; reports the
                        placement that hashes to the sealed value, or SKIPPED
  witness               path of any file in the repository whose exact bytes (or
                        collapsed bytes) hash to the sealed value: proof that the
                        sealed bytes still exist, even when this copy drifted

Read-only. Run from the repository root:
    python3 evidence/E6_SEAL_INTEGRITY_V0/tools/witness_search.py
Output is a TSV on stdout.
"""
import hashlib
import itertools
import pathlib
import subprocess

MAX_BREAKS = 12
SKIP_DIRS = {".git", "vendor", "__pycache__", "build", "node_modules"}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def collapse(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def manifest_hash(rel: str):
    p = pathlib.Path(rel)
    for depth in range(len(p.parts) - 1, 0, -1):
        man = pathlib.Path(*p.parts[:depth]) / "SHA256SUMS.txt"
        if not man.is_file():
            continue
        for line in man.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.strip().split()
            if len(parts) == 2 and len(parts[0]) == 64:
                if (man.parent / parts[1].lstrip("*")).as_posix() == rel:
                    return parts[0].lower()
    return None


def git_show(rel: str):
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def build_witness_index():
    """hash -> paths, for every regular file outside the skipped directories."""
    index: dict[str, list[str]] = {}
    for p in pathlib.Path(".").rglob("*"):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            b = p.read_bytes()
        except OSError:
            continue
        index.setdefault(sha(b), []).append(p.as_posix())
        index.setdefault(sha(collapse(b)), []).append("LF-rendering-of:" + p.as_posix())
    return index


audit = pathlib.Path("evidence/E6_SEAL_INTEGRITY_V0/raw_audit.tsv")
rows = [l.split("\t") for l in audit.read_text(encoding="utf-8").splitlines()
        if "\t" in l and not l.startswith(("path\t", "seal_files"))]
targets = [r for r in rows if "CONTENT" in (r[1], r[2])]

witness = build_witness_index()

print("path\tsame_text_modulo_cr\tcr_placement\tseal_witness")
for rel, wcls, hcls, wh, seen in targets:
    p = pathlib.Path(rel)
    disk = p.read_bytes() if p.is_file() else None
    blob = git_show(rel)
    expected = manifest_hash(rel)

    if disk is None or blob is None:
        same = "n/a"
        text = disk if disk is not None else blob
    else:
        same = "YES" if collapse(disk) == collapse(blob) else "NO"
        text = disk

    placement = "n/a"
    if expected and text is not None:
        c = collapse(text)
        breaks = [i for i, x in enumerate(c) if x == 10]
        if len(breaks) <= MAX_BREAKS:
            hits = []
            for k in range(len(breaks) + 1):
                for combo in itertools.combinations(range(len(breaks)), k):
                    v = bytearray(c)
                    off = 0
                    for idx in combo:
                        v.insert(breaks[idx] + off, 13)
                        off += 1
                    if sha(bytes(v)) == expected:
                        hits.append(combo)
            placement = ("NONE" if not hits
                         else f"{len(hits)} placement(s), e.g. CR before breaks {list(hits[0])}")
        else:
            placement = f"SKIPPED ({len(breaks)} breaks > {MAX_BREAKS})"

    w = witness.get(expected or "", [])
    print(f"{rel}\t{same}\t{placement}\t{'; '.join(sorted(set(w))[:4]) if w else 'NONE'}")
