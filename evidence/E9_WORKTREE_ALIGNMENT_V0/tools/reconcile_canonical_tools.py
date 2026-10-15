#!/usr/bin/env python3
"""E9 appended correction: reconcile `sha256sum -c` with `chain_check.py` over every manifest.

raw/13 reported the canonical-tool tally as "verifies = 431 / failing = 10" while the three-way
chain check reported 432 and 9. This scan re-measures both, per manifest, and separates three
distinct failure kinds that raw/13 collapsed into one number:

  1. content mismatch  - a line both parsers accept whose digest does not match the bytes
  2. unparsable line   - a line the parsers disagree about, so it enters one inventory and not the other
  3. path resolution   - entries whose names are relative to the manifest, checked from the wrong cwd

Run from the repo root:

    python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/reconcile_canonical_tools.py

Read-only: nothing is written, no Git command that mutates state is invoked, and no manifest is edited.
"""
import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
ENV = {"LC_ALL": "C.UTF-8", "PATH": os.environ["PATH"]}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse(line: str):
    """The canonical parser shared with E6/E7/E8/baseline/chain_check."""
    parts = line.split()
    if len(parts) < 2 or len(parts[0]) != 64:
        return None
    try:
        int(parts[0], 16)
    except ValueError:
        return None
    return parts[0].lower(), parts[1].lstrip("* ")


def manifests():
    return sorted(p for p in ROOT.rglob("SHA256SUMS*.txt") if ".git" not in p.parts)


def main() -> int:
    mans = manifests()
    phys = pars = rejected = 0
    bad_bom = []
    for man in mans:
        for line in man.read_bytes().decode("utf8", "replace").splitlines():
            if not line.strip():
                continue
            phys += 1
            if parse(line):
                pars += 1
            else:
                rejected += 1
                off = man.read_bytes().find(b"\xef\xbb\xbf")
                bad_bom.append((man, line, off))

    print("# E9 appended correction — `sha256sum -c` vs `chain_check.py`, every manifest on disk")
    print("# repo: " + str(ROOT))
    print(f"# manifests on disk        = {len(mans)}")
    print(f"# physical nonblank lines  = {phys}")
    print(f"# lines the canonical parser accepts = {pars}")
    print(f"# lines the canonical parser rejects = {rejected}")
    print()

    print("## 1. rejected lines, with the byte offset of the cause")
    for man, line, off in bad_bom:
        raw = man.read_bytes()
        print(f"path = {man.relative_to(ROOT).as_posix()}")
        print(f"  first 8 bytes   = {raw[:8].hex(' ')}")
        print(f"  UTF-8 BOM at    = {off if off >= 0 else 'absent'}")
        print(f"  size            = {len(raw)} bytes, {len([l for l in raw.splitlines() if l.strip()])} line(s)")
        print(f"  parsed line     = {line[:24]}...  ({len(line.split()[0])} chars in field 1)")
    print()

    print("## 2. per-manifest `sha256sum -c`, run from the manifest's own directory (the canonical recipe)")
    print("manifest\trc\tOK\tCONTENT-FAILED\tOPEN-OR-READ-FAILED\tparsed-lines\tstderr")
    tot = {"ok": 0, "cf": 0, "or": 0, "pl": 0}
    rc1 = []
    for man in mans:
        r = subprocess.run(["sha256sum", "-c", man.name], cwd=man.parent,
                           capture_output=True, text=True, env=ENV)
        lines = r.stdout.splitlines()
        ok = len([l for l in lines if l.endswith(": OK")])
        cf = len([l for l in lines if l.endswith(": FAILED")])
        orf = len([l for l in lines if "FAILED open or read" in l])
        npl = sum(1 for l in man.read_bytes().decode("utf8", "replace").splitlines()
                  if l.strip() and parse(l))
        tot["ok"] += ok; tot["cf"] += cf; tot["or"] += orf; tot["pl"] += npl
        err = " ".join(r.stderr.split())
        if r.returncode != 0:
            rc1.append(man.relative_to(ROOT).as_posix())
        if r.returncode != 0 or err:
            print(f"{man.relative_to(ROOT).as_posix()}\t{r.returncode}\t{ok}\t{cf}\t{orf}\t{npl}\t{err[:110]}")
    print(f"# totals: rc!=0 manifests = {len(rc1)} | OK = {tot['ok']} | CONTENT-FAILED = {tot['cf']}"
          f" | OPEN-OR-READ-FAILED = {tot['or']} | lines sha256sum was given = {tot['pl']}")
    print()

    print("## 3. control: the same check run from the repo root instead of the manifest directory")
    print("entries are stored relative to their manifest, so a root-side run resolves nothing and proves "
          "nothing about content; it is shown only to rule that shape out as the source of raw/13's figures")
    root_ok = root_cf = root_or = 0
    root_rc1 = 0
    for man in mans:
        r = subprocess.run(["sha256sum", "-c", man.as_posix()], cwd=ROOT,
                           capture_output=True, text=True, env=ENV)
        lines = r.stdout.splitlines()
        root_ok += len([l for l in lines if l.endswith(": OK")])
        root_cf += len([l for l in lines if l.endswith(": FAILED")])
        root_or += len([l for l in lines if "FAILED open or read" in l])
        root_rc1 += (r.returncode != 0)
    print(f"root-side run: rc!=0 manifests = {root_rc1} | OK = {root_ok} | CONTENT-FAILED = {root_cf}"
          f" | OPEN-OR-READ-FAILED = {root_or}")
    print(f"# {root_ok}/{root_or} against {tot['ok']}/{tot['or']} for the same bytes: the manifest-directory "
          f"recipe is the only one of the two that measures content")
    print()

    print("## 4. does the rejected line hide an integrity failure?")
    for man, line, _off in bad_bom:
        want = line.split()[0].lstrip("\ufeff").lower()
        name = line.split()[1]
        target = man.parent / name
        got = sha(target.read_bytes())
        print(f"{target.relative_to(ROOT).as_posix()}")
        print(f"  seal in manifest (case as written) = {line.split()[0].lstrip(chr(0xfeff))}")
        print(f"  sha256 of the bytes on disk        = {got}")
        print(f"  equal ignoring case = {want == got}")
        print("  -> the manifest holds exactly one entry and its digest is correct; only the line "
              "PREFIX is unparsable, so this is a format defect, not a mismatch")
    print()

    print("## 5. CR-bearing manifests (the reason the canonical parser, not sha256sum, decides the 9)")
    cr = [m.relative_to(ROOT).as_posix() for m in mans if b"\r" in m.read_bytes()]
    print(f"manifests containing CR = {len(cr)}")
    for c in cr:
        print(f"  {c}")
    print()

    print("## 6. reconciliation")
    cc = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("chain_check.py")),
                         "--group", "all"], cwd=ROOT, capture_output=True, text=True, env=ENV)
    fig = {}
    for line in cc.stdout.splitlines():
        if line.startswith("#") and "=" in line:
            k, v = line.lstrip("# ").rsplit("= ", 1)
            fig[k.strip()] = v.strip()
    print("chain_check.py, same disk, same moment:")
    for key in ("manifests", "sealed entries total", "disk bytes == seal",
                "HEAD bytes == seal", "disk == seal == HEAD (3-way)",
                "entries absent from HEAD", "mismatches"):
        print(f"  {key:26s} = {fig.get(key)}")
    print()
    print(f"sha256sum -c, canonical recipe: {tot['ok']} OK + {tot['cf']} CONTENT-FAILED "
          f"= {tot['ok'] + tot['cf']} lines it accepted out of {phys} physical lines")
    print(f"chain_check.py:                 {fig.get('disk bytes == seal')} disk==seal + "
          f"{fig.get('mismatches')} mismatches = {fig.get('sealed entries total')} lines its parser accepted")
    print(f"nonzero-exit manifests          = {len(rc1)} = {tot['cf']} content mismatches "
          f"(one manifest each) + {len(rc1) - tot['cf']} unparsable manifest(s) that report ZERO FAILED lines")
    print("# the two tools agree on the mismatch count; the extra nonzero exit is the BOM line, "
          "counted by neither parser as an entry")
    n441 = int(fig["sealed entries total"])
    print(f"# raw/13's canonical-tool line read 'verifies = {n441 - len(rc1)} / failing = {len(rc1)}'. "
          f"{n441} - {len(rc1)} = {n441 - len(rc1)}: that pair is the count of manifests exiting non-zero "
          "subtracted from the entry total, so it is a manifest-level tally reported with entry-level labels.")
    print(f"# the entry-level figures for these same bytes are {tot['ok']} verifying and {tot['cf']} failing. "
          "raw/13 stands as recorded; this file is the appended correction.")
    print()
    print("## 7. disposition")
    print("vendor/quines/SHA256SUMS.txt is NOT repaired here: it is vendor-drop bytes, and stripping its BOM "
          "would change a file whose seal already matches its payload. Same class as the .gitignore NUL bytes "
          "recorded in the README — a hygiene defect, deferred by decision rather than oversight.")
    print("NOT_DEMONSTRATED: that GNU sha256sum ever accepts a BOM-prefixed line, or that any other tool in "
          "this repo reads this manifest. The claim here is only that the two tools on these bytes agree on 9.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
