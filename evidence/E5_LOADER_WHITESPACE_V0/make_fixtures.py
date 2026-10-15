#!/usr/bin/env python3
"""E5 fixtures - regenerate from the sealed artifact instead of storing 2.9 MB copies.

Writes into the directory given as argv[1] (default: sibling ./fixtures).
Refuses to write if the destination resolves inside the sealed evidence tree.
Verifies the source sha256 before touching anything.
"""
import hashlib
import pathlib
import sys

SRC_SHA = "3b9bdf37eb708ec751d10f0dea32edde4375e526ce56fd2dd440f5a22819ba10"
REPO = pathlib.Path(__file__).resolve().parents[2]
SRC = REPO / "evidence" / "M0_KILLER_UNSHACKLED_V0" / "artifact.mu"
TRUNC_SHA = "fd390dd413224854d506ab00f50b3349d6c8039bbf1170f40be3c606d33b125e"
TOL_SHA = "0c8c85fbb4cb31c5839ca809291e2c798f40d58cd8a239e3c8249d9805fe083d"
WS = (0x20, 0x09, 0x0D, 0x0A)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    raw = SRC.read_bytes()
    if sha(raw) != SRC_SHA:
        print(f"FAIL sealed source changed: {sha(raw)}", file=sys.stderr)
        return 1

    ws_pos = [i for i, c in enumerate(raw) if c in WS]
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures").resolve()
    if str(out).startswith(str(REPO / "evidence" / "M0_KILLER_UNSHACKLED_V0")):
        print("REFUSING to write inside the sealed M0_KILLER dir", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)

    # fixture 1: the image minus its trailing whitespace bytes
    tail = len(raw)
    while tail > 0 and raw[tail - 1] in WS:
        tail -= 1
    trunc = raw[:tail]
    # fixture 2: the clean code plus 5 whitespace bytes (tolerance probe)
    tol = trunc + b" \r\n\t\n"

    (out / "artifact_trunc.mu").write_bytes(trunc)
    (out / "artifact_tol.mu").write_bytes(tol)

    print(f"sealed artifact.mu  bytes={len(raw)} ws_bytes={len(ws_pos)} "
          f"positions={ws_pos} values={[hex(raw[p]) for p in ws_pos]}")
    print(f"artifact_trunc.mu   bytes={len(trunc)} sha256={sha(trunc)} "
          f"expected={'OK' if sha(trunc) == TRUNC_SHA else 'MISMATCH'}")
    print(f"artifact_tol.mu     bytes={len(tol)} sha256={sha(tol)} "
          f"expected={'OK' if sha(tol) == TOL_SHA else 'MISMATCH'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
