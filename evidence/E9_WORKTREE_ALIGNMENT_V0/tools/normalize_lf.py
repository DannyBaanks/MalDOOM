#!/usr/bin/env python3
"""E9 normalisation: make `worktree == HEAD` for the divergent tracked files by dropping CR from disk.

Danny's decision for Request G was **"normalizar disco a LF"**: change no committed byte, publish no new
blob, and instead repair the *worktree* side, exactly the route E6 used for 32 files (`REPAIR_EXECUTED.md`).
For every candidate the guard is `sha256(fold(worktree)) == sha256(HEAD)`, so the rewrite is provably a
CR-removal and nothing else; any file that fails the guard is refused, never forced.

Two refusal classes are hard-coded, not configurable:

* `FREEZE` — the seven `evidence/M0_*/SHA256SUMS.txt` that seal themselves. E7 ruled they stay
  byte-for-byte as they are ("documented rather than silenced"), so their CRLF on disk is left alone even
  though folding them would be technically possible.
* `KEEP-*` verdicts from `witness_check.py` — a file whose current bytes are the only local copy of some
  seal must not be folded. The 2026-10-15 measurement says there are none (`raw/02`: KEEP=0), but the
  guard stays in the writer so the invariant is enforced, not remembered.

Writes go to `<name>.e9tmp` + `os.replace()`, and a snapshot of every pre-image is written first.

    python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/normalize_lf.py [--dry-run]

Evidence output (raw/03 snapshot, raw/04 record) is written under this experiment's `raw/` only.
"""
import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
RAW = ROOT / "evidence" / "E9_WORKTREE_ALIGNMENT_V0" / "raw"
ENV = {**os.environ, "LC_ALL": "C.UTF-8"}

FREEZE = {
    f"evidence/M0_{n}/SHA256SUMS.txt"
    for n in ("A_CONST", "B_ARITH", "C_BRANCH", "D_LOOP", "E_MEMORY", "F_INPUT", "KILLER")
}


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
        yield parts[0].lower(), target


def seal_claims():
    out = {}
    for man in manifests():
        for seal, target in entries(man):
            out.setdefault(seal, []).append(target.relative_to(ROOT).as_posix())
    return out


def disk_index():
    idx = {}
    for p in ROOT.rglob("*"):
        if ".git" in p.parts or not p.is_file():
            continue
        idx.setdefault(sha(p.read_bytes()), []).append(p.relative_to(ROOT).as_posix())
    return idx


def divergent():
    out = {}
    for rel in sorted(f.decode() for f in git("ls-files", "-z").stdout.split(b"\0") if f):
        p = ROOT / rel
        if not p.is_file():
            continue
        r = git("show", f"HEAD:{rel}")
        if r.returncode != 0 or r.stdout == p.read_bytes():
            continue
        out[rel] = r.stdout
    return out


def classify(rel, w, h, claims, disk):
    sw = sha(w)
    claimed_by = set(claims.get(sw, []))
    others = len([f for f in disk.get(sw, []) if f != rel])
    if fold(w) != h:
        return "KEEP-NOT-FOLDABLE"
    if rel in FREEZE:
        return "KEEP-FROZEN-BY-E7"
    if rel in claimed_by:
        return "KEEP-SELF-SEAL-VERIFIES"
    if [p for p in claimed_by if p != rel] and others == 0:
        return "KEEP-UNIQUE-WITNESS"
    return "NORMALIZE"


def main() -> int:
    dry = "--dry-run" in sys.argv
    div = divergent()
    claims = seal_claims()
    disk = disk_index()

    snap = RAW / "03_pre_normalisation_snapshot.tsv"
    with snap.open("w", encoding="utf8", newline="\n") as fh:
        fh.write("path\tsize_worktree\tCR_worktree\tsha256_worktree\tsize_HEAD\tsha256_HEAD\tverdict\n")
        for rel, h in div.items():
            w = (ROOT / rel).read_bytes()
            fh.write(f"{rel}\t{len(w)}\t{w.count(b"\r")}\t{sha(w)}\t{len(h)}\t{sha(h)}\t"
                     f"{classify(rel, w, h, claims, disk)}\n")

    rec = RAW / "04_normalisation_record.tsv"
    n_ok = n_ref = 0
    rows = []
    for rel, h in div.items():
        p = ROOT / rel
        w = p.read_bytes()
        verdict = classify(rel, w, h, claims, disk)
        if verdict != "NORMALIZE":
            n_ref += 1
            rows.append((rel, "REFUSED", verdict, len(w), len(w), ""))
            continue
        new = fold(w)
        if sha(new) != sha(h):
            n_ref += 1
            rows.append((rel, "REFUSED", "guard:folded-sha != HEAD-sha", len(w), len(w), ""))
            continue
        if not dry:
            tmp = p.with_name(p.name + ".e9tmp")
            tmp.write_bytes(new)
            os.replace(tmp, p)
        after = (ROOT / rel).read_bytes() if not dry else new
        n_ok += 1
        rows.append((rel, "NORMALIZED", "cr_removed" if after == new else "check-failed",
                     len(w), len(after), sha(after)))

    with rec.open("w", encoding="utf8", newline="\n") as fh:
        fh.write("path\taction\treason\tsize_before\tsize_after\tsha256_after\n")
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
        fh.write(f"# dry_run={dry} normalized={n_ok} refused={n_ref}\n")

    print(f"# dry_run={dry} divergent={len(div)} normalized={n_ok} refused={n_ref}")
    for r in rows:
        if r[1] == "REFUSED":
            print(f"REFUSED {r[0]}  {r[2]}")
    return 0



if __name__ == "__main__":
    sys.exit(main())
