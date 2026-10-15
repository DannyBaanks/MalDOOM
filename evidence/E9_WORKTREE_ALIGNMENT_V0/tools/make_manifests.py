#!/usr/bin/env python3
"""E9: seal the evidence directories that were untracked until this round.

The Sep-8 fragment/ADD1/M2 threads wrote outputs with **no manifest at all**, so `sha256sum -c` had
nothing to check them against. This writes one `SHA256SUMS.txt` per named directory in the convention
E5-E8 established: LF lines, `<64hex><two spaces><relative path>`, sorted, **no self-entry**, and the
addendum file is left out of the main manifest.

It refuses, by construction, to touch a directory that already carries a manifest — which is why
`evidence/EPOCH_TRANSPARENCY_V{0,1}/` are excluded: they are already sealed, and their manifests are
part of what is being committed unchanged.

Sealing here means *recording byte identity from this commit forward*. It is not an endorsement of the
results inside: `FRAGMENTS_REAL/*.json` carry `"verified": false`,
`STATE_TRANSITIONS/TICK_INC/result.json` carries `found: false`, and one EPOCH run carries
`epoch_transparency_pass: false`. Those negatives are exactly what the seals now freeze.

    python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/make_manifests.py [--dry-run] <dir> [<dir> ...]
"""
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SKIP = {"SHA256SUMS.txt", "SHA256SUMS_addendum.txt"}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    dry = "--dry-run" in sys.argv
    dirs = [d.rstrip("/") for d in sys.argv[1:] if not d.startswith("--")]
    if not dirs:
        print("usage: make_manifests.py [--dry-run] <dir> ...", file=sys.stderr)
        return 2

    for rel in dirs:
        d = (ROOT / rel).resolve()
        man = d / "SHA256SUMS.txt"
        if man.exists():
            print(f"REFUSED {rel}: a manifest already exists — never rewrite a sealed manifest")
            continue
        files = sorted(p.relative_to(d).as_posix() for p in d.rglob("*")
                       if p.is_file() and p.name not in SKIP)
        if not files:
            print(f"REFUSED {rel}: no files to seal")
            continue
        body = "".join(f"{sha(d / f)}  {f}\n" for f in files)
        if not dry:
            man.write_bytes(body.encode("utf8"))
        print(f"WROTE {man.relative_to(ROOT).as_posix()}: {len(files)} entries"
              f"{' (dry-run, not written)' if dry else ''}")
        for f in files:
            print(f"   {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
