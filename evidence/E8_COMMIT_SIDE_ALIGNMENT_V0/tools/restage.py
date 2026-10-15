#!/usr/bin/env python3
"""E8 guarded commit-side alignment: re-store the worktree bytes Git already has, for the entries
whose committed blob is the seal with every CR dropped.

Nothing on disk is modified. This tool only changes what Git *stores*: it stages the existing
worktree bytes for the candidate paths, so that the new commit's blob equals the seal.

`git add -- <path>` cannot do this. For these paths the index entry carries the worktree's size and
mtime while holding the LF blob, so Git believes the file is clean and `git add` is a silent no-op —
measured, raw/02 of the first attempt: restaged=0 refused=119, every one `REFUSED-staged-not-seal`.
The tool therefore writes the object with `git hash-object -w` and sets the index entry with
`git update-index --cacheinfo`, which are index-only operations: no worktree byte and no mtime is
touched, and `git reset -q -- <path>` would undo a staged entry again.

Refusal by default. A path is staged only if ALL of these hold at the moment of staging:

  1. the path is in the candidate set measured in raw/01 (relation CR-STRIPPED) and the fresh
     re-measurement of that same path still says CR-STRIPPED — the state has not moved;
  2. SHA-256(worktree bytes) == the seal;
  3. HEAD blob == worktree with every CR dropped, and != the seal (so the only defect is the CRs);
  4. SHA-1("blob N\\0" + worktree bytes) == the id `git hash-object` gives for the path, which proves
     the clean filters are identity: staging cannot alter a byte;
  5. the path is not a SHA256SUMS.txt (a manifest is never restaged).

After staging, SHA-256(git show :<path>) must equal the seal; if it does not, the path is unstaged
again and recorded as REFUSED. Prints one record row per path. Does not commit.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from measure import ROOT, blob_sha1, entries, fold, git, sha  # noqa: E402

RAW = HERE.parent / "raw"
HDR = "path\tseal_sha256\thead_sha256\tstaged_sha256\thead_bytes\tstaged_bytes\tresult"


def measured_candidates() -> set[str]:
    """The candidate paths as recorded in raw/01_alignment_before.txt (read-only evidence)."""
    rows = RAW / "01_alignment_before.txt"
    out = set()
    for line in rows.read_text().splitlines():
        f = line.split("\t")
        if len(f) == 9 and f[8] == "CR-STRIPPED":
            out.add(f[0])
    return out


def seals_by_path() -> dict[str, str]:
    """rel -> seal, one pass over every manifest (first manifest to name a path wins, as in measure)."""
    out: dict[str, str] = {}
    for _man, seal, _name, target in entries():
        if target is not None:
            out.setdefault(target.relative_to(ROOT).as_posix(), seal)
    return out


SEALS = seals_by_path()


def state_of(rel: str) -> tuple | None:
    """Fresh (seal, worktree bytes, HEAD blob) for a path, or None if it is no longer a candidate."""
    seal = SEALS.get(rel)
    if seal is None:
        return None
    target = ROOT / rel
    if not target.is_file():
        return None
    work = target.read_bytes()
    if sha(work) != seal:
        return None
    head = git("show", f"HEAD:{rel}")
    if head.returncode != 0 or sha(head.stdout) == seal:
        return None
    would = git("hash-object", "--", rel).stdout.decode().strip()
    if would != blob_sha1(work):
        return None
    return (seal, work, head.stdout)


def main() -> int:
    candidates = measured_candidates()
    print(f"# E8 guarded restage — {len(candidates)} candidate paths from raw/01")
    print(f"# HEAD before: {git('rev-parse', 'HEAD').stdout.decode().strip()}")
    print(f"# staged paths before: {len(git('diff', '--cached', '--name-only').stdout.decode().splitlines())}")
    print()
    print(HDR)
    restaged = refused = 0
    for rel in sorted(candidates):
        if rel.endswith("SHA256SUMS.txt"):
            print(f"{rel}\t-\t-\t-\t-\t-\tREFUSED-is-a-manifest")
            refused += 1
            continue
        fresh = state_of(rel)
        if fresh is None:
            print(f"{rel}\t-\t-\t-\t-\t-\tREFUSED-state-changed-or-not-candidate")
            refused += 1
            continue
        seal, work, head_bytes = fresh
        if head_bytes != fold(work):
            print(f"{rel}\t{seal}\t{sha(head_bytes)}\t-\t{len(head_bytes)}\t-\tREFUSED-head-differs-by-more-than-cr")
            refused += 1
            continue
        listed = git("ls-files", "-s", "--", rel).stdout.decode().split()
        if len(listed) < 2:
            print(f"{rel}\t{seal}\t{sha(head_bytes)}\t-\t{len(head_bytes)}\t-\tREFUSED-not-tracked")
            refused += 1
            continue
        mode = listed[0]
        # `git add` is a silent no-op here: the index entry carries this file's size and mtime while
        # holding the LF blob, so Git believes the worktree is clean. The deterministic route writes
        # the object and sets the index entry directly; the worktree bytes and mtimes are not touched.
        blob = git("hash-object", "-w", "--", rel).stdout.decode().strip()
        upd = git("update-index", "--cacheinfo", f"{mode},{blob},{rel}")
        if upd.returncode != 0:
            print(f"{rel}\t{seal}\t{sha(head_bytes)}\t-\t{len(head_bytes)}\t-\tREFUSED-update-index-failed:"
                  + upd.stderr.decode().strip().replace("\t", " "))
            refused += 1
            continue
        staged = git("show", f":{rel}")
        s_sha = sha(staged.stdout)
        if s_sha != seal:
            git("reset", "-q", "--", rel)
            print(f"{rel}\t{seal}\t{sha(head_bytes)}\t{s_sha}\t{len(head_bytes)}\t{len(staged.stdout)}"
                  f"\tREFUSED-staged-not-seal-and-unstaged")
            refused += 1
            continue
        if staged.stdout != work:
            git("reset", "-q", "--", rel)
            print(f"{rel}\t{seal}\t{sha(head_bytes)}\t{s_sha}\t{len(head_bytes)}\t{len(staged.stdout)}"
                  f"\tREFUSED-staged-bytes-not-worktree-and-unstaged")
            refused += 1
            continue
        print(f"{rel}\t{seal}\t{sha(head_bytes)}\t{s_sha}\t{len(head_bytes)}\t{len(staged.stdout)}\tRESTAGED")
        restaged += 1
    print(f"# summary: restaged={restaged} refused={refused}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
