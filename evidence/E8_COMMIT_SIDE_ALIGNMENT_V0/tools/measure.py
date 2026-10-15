#!/usr/bin/env python3
"""E8 read-only measurement: which sealed entries are correct on disk but wrong in the commit?

For every entry listed in an evidence SHA256SUMS.txt, compare three things: the seal, the worktree
bytes, and what Git stores. Prints one TSV row per entry plus a summary. Writes nothing.

A row is a CANDIDATE (relation CR-STRIPPED) only if ALL of these hold:

  * SHA-256(worktree bytes) == the seal                     -> the sealed bytes are on disk
  * HEAD blob == worktree with every CR dropped             -> the committed rendering lost exactly
    the carriage returns and nothing else
  * the blob `git add` would store == the worktree bytes    -> the * -text attribute really means it,
    so restaging cannot alter a byte
  * HEAD blob != seal                                       -> there is something to fix

Anything else is reported under its own relation and is never a candidate.
"""
import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
ENV = {**os.environ, "LC_ALL": "C.UTF-8"}
HDR = ("path\tseal_sha256\tworktree_sha256\tworktree_bytes\thead_bytes\t"
       "would_store_blob\tindex_blob\thead_blob\trelation")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fold(b: bytes) -> bytes:
    """Drop every carriage return: CRLF -> LF, lone CR -> LF."""
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, env=ENV)


def entries():
    """(manifest, seal, path) for every sealed entry in the repo, hex in either case.

    Yields path None when the manifest names a file that is not on disk.
    """
    for man in sorted((ROOT / "evidence").rglob("SHA256SUMS.txt")):
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
            yield man, parts[0].lower(), name, (target if target.is_file() else None)


def blob_sha1(b: bytes) -> str:
    """The SHA-1 Git names a blob by: SHA-1("blob <len>\\0" + bytes)."""
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(b))
    h.update(b)
    return h.hexdigest()


def main() -> int:
    print(f"# E8 alignment measurement — repo: {ROOT}")
    print(f"# HEAD {git('rev-parse', 'HEAD').stdout.decode().strip()}")
    print(f"# .gitattributes: {' / '.join(git('show', 'HEAD:.gitattributes').stdout.decode().splitlines())}")
    print(f"# core.autocrlf={git('config','--get','core.autocrlf').stdout.decode().strip() or '(unset)'}")
    print()
    print(HDR)
    tally = {}
    candidates = []
    for man, seal, name, target in entries():
        if target is None:
            tally["NO-FILE"] = tally.get("NO-FILE", 0) + 1
            print(f"{man.parent.name}/{name}\t{seal}\tABSENT\t-\t-\t-\t-\t-\tNO-FILE")
            continue
        rel = target.relative_to(ROOT).as_posix()
        work = target.read_bytes()
        w_sha = sha(work)
        head = git("show", f"HEAD:{rel}")
        in_head = head.returncode == 0
        h_sha1 = sha(head.stdout) if in_head else None
        idx = git("ls-files", "-s", "--", rel).stdout.decode().split()
        would = git("hash-object", "--", rel).stdout.decode().strip()
        # `git add` stores the clean-filtered bytes; with * -text that must be the worktree bytes.
        # Proved without writing any object: the blob id Git would name must equal SHA-1(worktree).
        verbatim = would == blob_sha1(work)
        if w_sha != seal:
            relation = "WORKTREE-NOT-SEAL"
        elif not in_head:
            relation = "NOT-IN-HEAD"
        elif sha(head.stdout) == seal and verbatim:
            relation = "ALIGNED"
        elif head.stdout == fold(work) and verbatim:
            relation = "CR-STRIPPED"
            candidates.append(rel)
        else:
            relation = "OTHER-DIVERGENCE"
        tally[relation] = tally.get(relation, 0) + 1
        print(f"{rel}\t{seal}\t{w_sha}\t{len(work)}\t{len(head.stdout)}\t"
              f"{would}\t{idx[1] if len(idx) > 1 else 'ABSENT'}\t"
              f"{h_sha1 or 'ABSENT'}\t{relation}")
    print()
    for relation in sorted(tally):
        print(f"# {relation:<20} {tally[relation]}")
    print(f"# total sealed entries inspected  {sum(tally.values())}")
    print(f"# CANDIDATES (relation CR-STRIPPED) {len(candidates)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
