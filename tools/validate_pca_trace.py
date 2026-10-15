"""Validate and replay a Zig Classic Malbolge positional receipt.

The JSONL is the observed receipt. This tool reconstructs output from its
``out`` events, checks register continuity, then compares both against a fresh
run of the pinned PCA executable.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


MEM_SIZE = 59049


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("program", type=Path)
    parser.add_argument("pca", type=Path)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.trace.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit("FAIL: empty trace")

    expected_step = 1
    output = bytearray()
    previous = None
    for row in rows:
        required = {
            "schema", "step", "a_before", "c_before", "d_before", "opcode",
            "read_addr", "read_value", "write_addr", "write_before",
            "write_after", "enc_addr", "enc_before", "enc_after",
            "jump_target", "a_after", "c_after", "d_after",
        }
        missing = required.difference(row)
        if missing:
            raise SystemExit(f"FAIL: missing fields at step {row.get('step')}: {sorted(missing)}")
        if row["schema"] != "malbolge-step-v1" or row["step"] != expected_step:
            raise SystemExit(f"FAIL: bad sequence/schema at step {row.get('step')}")
        if previous is not None and (row["c_before"], row["d_before"]) != (
            previous["c_after"], previous["d_after"]
        ):
            raise SystemExit(f"FAIL: register continuity at step {row['step']}")
        for field in ("c_before", "d_before", "c_after", "d_after"):
            if not 0 <= row[field] < MEM_SIZE:
                raise SystemExit(f"FAIL: {field} out of range at step {row['step']}")
        if row["opcode"] == "out":
            output.append(row["a_before"] % 256)
        previous = row
        expected_step += 1

    if previous["opcode"] != "halt":
        raise SystemExit("FAIL: receipt does not end in HALT")

    proc = subprocess.run(
        [str(args.pca), str(args.program), "200000", ""],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    raw = proc.stdout + "\n" + proc.stderr
    observed_output = re.search(r"output_len=(\d+) output=(.*)", raw)
    observed_final = re.search(r"final a=(\d+) c=(\d+) d=(\d+)", raw)
    observed_status = re.search(r"status=(\w+) steps=(\d+)", raw)
    if proc.returncode != 0 or not observed_output or not observed_final or not observed_status:
        raise SystemExit(f"FAIL: fresh PCA run unavailable (exit={proc.returncode})")

    receipt_output = bytes(output).decode("latin-1")
    fresh_output = observed_output.group(2).rstrip("\r")
    fresh_final = tuple(int(observed_final.group(i)) for i in range(1, 4))
    receipt_final = (previous["a_after"], previous["c_after"], previous["d_after"])
    fresh_steps = int(observed_status.group(2))

    if proc.returncode != 0 or observed_status.group(1) != "halted":
        raise SystemExit("FAIL: fresh PCA run did not halt")
    if receipt_output != fresh_output:
        raise SystemExit(f"FAIL: output mismatch receipt={receipt_output!r} fresh={fresh_output!r}")
    if receipt_final != fresh_final:
        raise SystemExit(f"FAIL: final-state mismatch receipt={receipt_final} fresh={fresh_final}")
    if len(rows) != fresh_steps:
        raise SystemExit(f"FAIL: step-count mismatch receipt={len(rows)} fresh={fresh_steps}")

    print(f"R2_REPLAY=PASS lines={len(rows)} output={receipt_output} final={receipt_final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
