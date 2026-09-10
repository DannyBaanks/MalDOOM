"""Run the non-neutral causal perturbation matrix for PURE_CONTINUATION_ANCHOR."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


CASES = (
    # S1: next instruction after A at c=201. Values decode as HALT, OUT, ROT.
    ("S1", 0, 201, (68, 86, 85), "BC"),
    # S2: next instruction after B at c=279. Values decode as HALT, OUT, MOVD.
    ("S2", 1, 279, (84, 102, 43), "C"),
    # S1 data cell: read by CRAZY before B is emitted and causally changes it.
    ("S1-data", 0, 174, (0, 1, 2), "BC"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("program", type=Path)
    parser.add_argument("pca", type=Path)
    args = parser.parse_args()

    receipts = []
    for label, phase, addr, values, expected in CASES:
        for value in values:
            proc = subprocess.run(
                [str(args.pca), "perturb", str(args.program), str(phase), str(addr), str(value), "200000", ""],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            raw = proc.stdout + "\n" + proc.stderr
            control = re.search(r"CONTROL\s+resume:.* output=(.*)", raw)
            perturb = re.search(r"PERTURB\s+addr=.* output=(.*)", raw)
            verdict = re.search(r"PERTURBATION_DIVERGENCE=(PASS|FAIL)", raw)
            if not control or not perturb or not verdict:
                raise SystemExit(f"FAIL: malformed PCA receipt for {label} value={value}")
            control_output = control.group(1).rstrip("\r")
            perturb_output = perturb.group(1).rstrip("\r")
            row = {
                "label": label,
                "phase": phase,
                "addr": addr,
                "new_value": value,
                "expected_control": expected,
                "control_output": control_output,
                "perturbed_output": perturb_output,
                "divergence": verdict.group(1),
            }
            receipts.append(row)
            if proc.returncode != 0 or control_output != expected or verdict.group(1) != "PASS" or perturb_output == expected:
                raise SystemExit(f"FAIL: {json.dumps(row, sort_keys=True)}")

    print(json.dumps({"schema": "malbolge-causal-controls-v1", "cases": receipts}, sort_keys=True))
    print(f"R4_CONTROLS=PASS cases={len(receipts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
