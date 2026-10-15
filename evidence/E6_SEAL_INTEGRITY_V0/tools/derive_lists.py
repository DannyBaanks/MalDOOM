#!/usr/bin/env python3
"""Derive the repair lists for the seal audit from raw_audit.tsv.

Reads the audit TSV (repo-relative paths) and writes, next to it:

  restore_manifest.txt  entries whose worktree is a CRLF rendering of the sealed
                        bytes (worktree_vs_seal = crlf_to_lf) and whose commit
                        already holds the sealed bytes exactly
                        (committed_vs_seal = exact). One path per line, no
                        comments, stable order. Removing the CR from these
                        worktree files makes the seal verify again; the LF bytes
                        are already committed, so this is a content-preserving
                        restore, not a re-seal.

  drift_snapshot.tsv     the same entries with the three hashes and the exact
                        byte rule that relates them, so the repair can be
                        re-checked without re-running the audit.

Entries whose seal is CRLF and whose commit is the LF rendering
(committed_vs_seal = lf_to_crlf) are NOT listed: restoring them from HEAD would
break their seal. They are documented instead, and so are the CONTENT entries,
which no line-ending rule explains.

Run from the repository root:
    python3 evidence/E6_SEAL_INTEGRITY_V0/tools/derive_lists.py
"""
import hashlib
import pathlib
import subprocess

base = pathlib.Path("evidence/E6_SEAL_INTEGRITY_V0")
audit = base / "raw_audit.tsv"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def seal_index() -> dict[str, str]:
    """repo-relative path -> expected hash, for every entry of every manifest."""
    table: dict[str, str] = {}
    for manifest in sorted(pathlib.Path("evidence").glob("*/SHA256SUMS.txt")):
        for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.strip().split()
            if len(parts) == 2 and len(parts[0]) == 64:
                key = (manifest.parent / parts[1].lstrip("*")).as_posix()
                table[key] = parts[0].lower()
    return table


def head_sha(rel: str) -> str:
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], capture_output=True)
    return sha(r.stdout) if r.returncode == 0 else "?"


rows = [l.split("\t") for l in audit.read_text(encoding="utf-8").splitlines()
        if "\t" in l and not l.startswith("path\t") and not l.startswith("seal_files")]
seals = seal_index()

# worktree is a CRLF rendering, and the commit already holds the sealed LF bytes
picks = sorted(r[0] for r in rows if len(r) >= 3 and r[1] == "crlf_to_lf" and r[2] == "exact")
if not picks:
    raise SystemExit("no DRIFT_LF/head==seal rows found in raw_audit.tsv")

(base / "restore_manifest.txt").write_text(
    "".join(p + "\n" for p in picks), encoding="utf-8")

out = ["path\tworktree_bytes\tworktree_sha256\tseal_sha256\thead_sha256\tbyte_rule"]
for rel in picks:
    b = pathlib.Path(rel).read_bytes()
    out.append("\t".join([
        rel, str(len(b)), sha(b), seals.get(rel, "?"), head_sha(rel),
        "CRLF(worktree) -> LF(=seal=HEAD): drop every CR, nothing else changes",
    ]))
(base / "drift_snapshot.tsv").write_text(
    "".join(l + "\n" for l in out), encoding="utf-8")

print(f"restore_manifest.txt {len(picks)} paths")
print(f"drift_snapshot.tsv {len(picks)} rows")
