#!/usr/bin/env python3
"""Audit every evidence seal in this repository: sealed bytes vs worktree vs HEAD.

For each SHA256SUMS.txt under evidence/ (its entries are paths relative to the
manifest's own directory) three byte sources are compared:

  seal      the hash recorded in SHA256SUMS.txt (bytes as they were when sealed)
  worktree  the bytes on disk right now
  HEAD      the committed blob

Each comparison names the line-ending rule that relates the two sides, because a
CR/LF rendering difference is the only kind this repository can hide from git:
the tree is byte-exact by attribute (`* -text`, no conversion configured), so
git decides "unchanged" from stat data, and a rendering swap that preserves byte
size or timestamps is invisible to `git status`.

Categories for worktree_vs_seal and committed_vs_seal:

  exact            bytes are identical
  crlf_to_lf       CRLF runs collapse to LF and match
  lf_to_crlf       LF runs expand to CRLF and match
  cr_to_lf         lone-CR breaks collapse to LF and match (no CRLF present)
  lf_to_cr         LF breaks become lone CR and match (no CRLF present)
  canonical_lf     any mix of CR/CRLF/LF collapses to LF and match
  canonical_crlf   any mix collapses then expands to CRLF and match
  CONTENT          no rendering rule explains it: a real content difference
  UNTRACKED        no blob in HEAD for this path
  MISSING          the sealed file is not on disk

worktree_vs_head uses the same rule names, against the blob's hash instead of
the seal's. `git_says` reports whether `git status` noticed, independently of
the above: a clean status is not evidence that a byte-level seal holds.

Run from the repository root:
    python3 evidence/E6_SEAL_INTEGRITY_V0/tools/seal_audit.py
Output is a TSV on stdout with repository-relative paths only.
"""
import hashlib
import pathlib
import subprocess

root = pathlib.Path(".")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def crlf_to_lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def lf_to_crlf(b: bytes) -> bytes:
    return b.replace(b"\n", b"\r\n")


def cr_to_lf(b: bytes) -> bytes:
    return None if b"\r\n" in b else b.replace(b"\r", b"\n")


def lf_to_cr(b: bytes) -> bytes:
    return None if b"\r\n" in b else b.replace(b"\n", b"\r")


def canonical_lf(b: bytes) -> bytes:
    return crlf_to_lf(b).replace(b"\r", b"\n")


def canonical_crlf(b: bytes) -> bytes:
    return lf_to_crlf(canonical_lf(b))


RULES = [
    ("exact", lambda b: b),
    ("crlf_to_lf", crlf_to_lf),
    ("lf_to_crlf", lf_to_crlf),
    ("cr_to_lf", cr_to_lf),
    ("lf_to_cr", lf_to_cr),
    ("canonical_lf", canonical_lf),
    ("canonical_crlf", canonical_crlf),
]


def relation(a: bytes, target: str):
    """First rule that turns bytes `a` into something hashing `target`."""
    for name, f in RULES:
        v = f(a)
        if v is not None and sha(v) == target:
            return name
    return "CONTENT"


def git_blob(rel: str):
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


dirty = set()
for line in subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                           text=True).stdout.splitlines():
    if len(line) > 3:
        dirty.add(line[3:].strip())

tally = {}
rows = []
seals = sorted((root / "evidence").glob("*/SHA256SUMS.txt"))
for seal in seals:
    base = seal.parent
    for raw in seal.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2 or len(parts[0]) != 64:
            continue
        expected, name = parts[0].lower(), parts[-1].lstrip("*")
        path = (base / name)
        rel = path.as_posix()
        disk = path.read_bytes() if path.is_file() else None
        if disk is None:
            wcls = "MISSING"
        else:
            wcls = relation(disk, expected)
        blob = git_blob(rel)
        if blob is None:
            hcls = "UNTRACKED"
        else:
            hcls = relation(blob, expected)
        wh = "MISSING" if disk is None else ("UNTRACKED" if blob is None
                                             else relation(disk, sha(blob)))
        seen = "git_dirty" if rel in dirty else "git_clean"
        rows.append(f"{rel}\t{wcls}\t{hcls}\t{wh}\t{seen}")
        key = (wcls, hcls, wh, seen)
        tally[key] = tally.get(key, 0) + 1

print("seal_files\t" + str(len(seals)))
print("path\tworktree_vs_seal\tcommitted_vs_seal\tworktree_vs_head\tgit_says")
for r in rows:
    print(r)
print("summary")
for k, v in sorted(tally.items(), key=lambda x: (-x[1], x[0])):
    print(f"  {k[0]:<14} {k[1]:<14} {k[2]:<14} {k[3]:<10} {v}")
