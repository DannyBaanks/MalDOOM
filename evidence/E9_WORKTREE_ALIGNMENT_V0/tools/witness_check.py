#!/usr/bin/env python3
"""E9 witness check (read-only): would CR-stripping a divergent file destroy the only copy of sealed bytes?

`baseline.py` found 60 tracked files with `worktree != HEAD`. Normalising them means writing
`fold(worktree)` to disk, which changes `sha256(worktree)`. That is harmless **unless** the current
worktree bytes are themselves the witness for some seal — E7 recovered seven
`evidence/M0_*_UNSHACKLED_V0/source.c` from `engine/M0_*.c` exactly that way, and those engine files
appear in the divergent set.

So this scan indexes every seal in the repo, then for every divergent path reports which seals the
*worktree* bytes satisfy, which seals the *HEAD* bytes satisfy, and how many files on disk would still
satisfy the seal after the fold. A decision needs a witness to be unique; `raw/02` is that measurement.

    python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/witness_check.py

Read-only: no write, no mutating Git command.
"""
import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
ENV = {**os.environ, "LC_ALL": "C.UTF-8"}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, env=ENV)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fold(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def manifests():
    return [p for p in sorted(ROOT.rglob("SHA256SUMS*.txt")) if ".git" not in p.parts]


def entries(man: pathlib.Path):
    for line in man.read_bytes().decode("utf8", "replace").splitlines():
        parts = line.split()
        if len(parts) < 2 or len(parts[0]) != 64:
            continue
        try:
            int(parts[0], 16)
        except ValueError:
            continue
        name = parts[1].lstrip("* ")
        target = man.parent / name
        if not target.is_file():
            target = ROOT / name
        yield parts[0].lower(), name, target


def main() -> int:
    # seal -> set of paths it claims, and the reverse index over every file on disk
    seal_claims: dict[str, list[str]] = {}
    for man in manifests():
        for seal, _n, target in entries(man):
            rel = target.relative_to(ROOT).as_posix()
            seal_claims.setdefault(seal, []).append(rel)

    disk_hashes: dict[str, list[str]] = {}
    for p in ROOT.rglob("*"):
        if ".git" in p.parts or not p.is_file():
            continue
        disk_hashes.setdefault(sha(p.read_bytes()), []).append(p.relative_to(ROOT).as_posix())

    tracked = sorted(f.decode() for f in git("ls-files", "-z").stdout.split(b"\0") if f)
    divergent: dict[str, bytes] = {}
    for rel in tracked:
        p = ROOT / rel
        if not p.is_file():
            continue
        r = git("show", f"HEAD:{rel}")
        if r.returncode != 0 or r.stdout == p.read_bytes():
            continue
        divergent[rel] = r.stdout

    print("# E9 witness check — is any divergent file the unique carrier of sealed bytes?")
    print(f"# manifests: {len(manifests())} | distinct seals: {len(seal_claims)} | divergent: {len(divergent)}")
    print()
    print("path\trelation\tfold_equals_HEAD\tworktree_bytes_satisfy\tHEAD_bytes_satisfy\tverdict")
    n_keep = n_norm = 0
    for rel, h in divergent.items():
        w = (ROOT / rel).read_bytes()
        sw = sha(w)
        sh_ = sha(h)
        relation = ("CRLF-PAIRS-EXACT" if w == h.replace(b"\n", b"\r\n")
                    else "CR-STRIPPED" if h == fold(w) else "OTHER")
        # `sw` is the digest of this file's worktree bytes; `seal_claims[sw]` lists the paths whose
        # manifest line demands exactly those bytes. `disk_hashes[sw]` lists every file on disk that
        # currently carries them, so `others == 0` means this file is the last local copy.
        claimed_by = sorted(set(seal_claims.get(sw, [])))
        head_seals = sorted(set(seal_claims.get(sh_, [])))
        others = len([f for f in disk_hashes.get(sw, []) if f != rel])
        witnesses = [p for p in claimed_by if p != rel]
        self_verifies = rel in claimed_by
        foldable = fold(w) == h

        if not foldable:
            verdict = "KEEP-NOT-FOLDABLE"
        elif self_verifies:
            verdict = "KEEP-SELF-SEAL-VERIFIES"
        elif witnesses and others == 0:
            verdict = "KEEP-UNIQUE-WITNESS"
        elif witnesses:
            verdict = "NORMALIZE-REDUNDANT-WITNESS"
        else:
            verdict = "NORMALIZE"
        claims = [f"{p}:others={others}" for p in witnesses]
        if self_verifies:
            claims.append(f"{rel}:self-others={others}")
        if verdict.startswith("KEEP"):
            n_keep += 1
        else:
            n_norm += 1
        print(f"{rel}\t{relation}\t{'yes' if foldable else 'NO'}"
              f"\t{'witness:'+';'.join(claims) if claims else 'no-seal'}"
              f"\t{'head:'+';'.join(head_seals) if head_seals else 'no-seal'}"
              f"\t{verdict}")
    print(f"# KEEP: {n_keep} | NORMALIZE: {n_norm}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
