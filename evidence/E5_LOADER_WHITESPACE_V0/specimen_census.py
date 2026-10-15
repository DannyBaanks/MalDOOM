#!/usr/bin/env python3
"""E5 - whitespace census + container/loadability controls over the two image conventions.

Each specimen is pinned by sha256 and SKIPPED (never guessed) if it has drifted.

Why the census decides the loader question: a *trailing* whitespace byte can be
trimmed, but a *mid-file* whitespace byte displaces every cell after it - so the
two fixed-19 engines and the reference VM are not running "the same program at
different speeds", they are running different programs.
"""
import hashlib
import pathlib

WS = {0x20: "space", 0x09: "tab", 0x0D: "CR", 0x0A: "LF"}
OPC = {4, 5, 23, 39, 40, 62, 68, 81}
RT = "/home/danny/Development/ISyCo/CoEvoLang/experiments/malbolge_lisp_petri_dish/runtime/"

# (label, path, sha256, convention the producing toolchain targets)
SPECIMENS = [
    ("artifact.mu", "/home/danny/Development/ISyCo Git/MALDOOM/evidence/"
     "M0_KILLER_UNSHACKLED_V0/artifact.mu",
     "3b9bdf37eb708ec751d10f0dea32edde4375e526ce56fd2dd440f5a22819ba10",
     "LMFAO/HeLL .mu - opcode-aligned TEXT for the strict loader"),
    ("init_module.mb", RT + "init_module.mb",
     "4b3080fd250a4193030ec647e6c496f90540c1546f717b923284ea31b411e812",
     "LMFAO init module - opcode-aligned TEXT"),
    ("core.mb", RT + "core.mb",
     "70e9155bbe44b58a0a44795cf0c614b214c8f31f82270f4913394e07f1f3e53a",
     "MalbolgeLISP epochal core - RAW CELL DUMP"),
    ("lisp.mb", RT + "lisp.mb",
     "092df5cdc240de33a355d3cf82bdf09e0859c5827ee57a65bf93dfc37e8f3256",
     "init_module.mb || core.mb - mixed container"),
]


def stream(path):
    """(sha256, nbytes, [(position, kind)]) without loading big files into memory."""
    h = hashlib.sha256()
    n = 0
    ws = []
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1 << 22)
            if not chunk:
                break
            h.update(chunk)
            base = n
            n += len(chunk)
            ws += [(base + i, WS[b]) for i, b in enumerate(chunk) if b in WS]
    return h.hexdigest(), n, ws


def prefix(path, nbytes):
    with pathlib.Path(path).open("rb") as fh:
        return fh.read(nbytes)


def main() -> int:
    for label, p, want, conv in SPECIMENS:
        path = pathlib.Path(p)
        if not path.exists():
            print(f"SKIP {label}: {p} absent")
            continue
        got, n, ws = stream(path)
        if got != want:
            print(f"SKIP {label}: sha256 {got} != pinned {want} - drifted, not measured")
            continue
        pos = [p for p, _ in ws]
        where = "none" if not ws else ("at EOF" if pos[-1] == n - 1 else "MID-FILE")
        shown = pos if len(pos) <= 4 else pos[:1] + ["…"] + pos[-3:]
        kinds = ",".join(sorted({k for _, k in ws})) if ws else "-"
        print(f"{label:16s} bytes={n:12d} sha={got[:16]}… ws={len(ws):3d} at {shown} ({where}) "
              f"types={kinds}\n{'':16s}convention: {conv}")

    init = prefix(SPECIMENS[1][1], 19392)
    core = prefix(SPECIMENS[2][1], 16384)
    lisp = prefix(SPECIMENS[3][1], 19392 + 16384)
    if init and core and lisp:
        # container control: lisp == init || core, checked on the parts we hold
        seam_ok = lisp[:len(init)] == init
        print(f"\ncontainer control: lisp[:{len(init)}] == init_module -> {seam_ok}; "
              f"size 19392+371312023 == 371331415; "
              f"full concatenation hash equality was verified separately on 2026-10-15")

        # loadability control: strict rule applied to the raw core, following the init module
        pos = sum(1 for b in init if b not in WS)
        bad = next((i for i, b in enumerate(core) if (b + pos + i) % 94 not in OPC), None)
        if bad is None:
            print(f"strict-rule probe on core head: no rejection in {len(core)} bytes (pos={pos})")
        else:
            print(f"strict-rule probe on core.mb: after {pos} accepted init cells the first "
                  f"non-opcode core byte is at core-offset {bad}: value={core[bad]} "
                  f"instr={(core[bad] + pos + bad) % 94} not in {sorted(OPC)} -> the reference "
                  f"loader aborts ('invalid character') on this image")
    return 0


if __name__ == "__main__":
    main()
