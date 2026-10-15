"""Validate dynamic phase-boundary anchors for a measured Classic run."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def run(pca: Path, *args: str) -> str:
    proc = subprocess.run([str(pca), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise SystemExit(f"PCA failed: {proc.stderr}")
    return proc.stdout + "\n" + proc.stderr


def halt_cell(position: int) -> int:
    return 33 + ((81 - position - 33) % 94)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("program_dir", type=Path)
    parser.add_argument("pca", type=Path)
    parser.add_argument("names", nargs="+", default=["ABC"])
    args = parser.parse_args()
    cases = []

    for name in args.names:
        program = args.program_dir / f"{name}.mal"
        raw = run(args.pca, str(program), "200000", "")
        output = re.search(r"output_len=\d+ output=([^\r\n]*)", raw)
        if not output:
            raise SystemExit(f"FAIL: no output for {name}")
        trace_raw = run(args.pca, "trace-jsonl", str(program), "200000", "")
        rows = [json.loads(line) for line in trace_raw.splitlines() if line.strip().startswith("{")]
        phases = [row for row in rows if row["opcode"] == "out"]
        anchors = []
        for left, right in zip(phases, phases[1:]):
            path = [row for row in rows if left["step"] < row["step"] <= right["step"]]
            if not path or path[0]["c_before"] != left["c_after"]:
                raise SystemExit(f"FAIL: broken phase edge for {name} phase {left['step']}")
            jumps = [row for row in path if row["jump_target"] is not None]
            addr = left["c_after"]
            value = halt_cell(addr)
            perturb_raw = run(args.pca, "perturb", str(program), str(phases.index(left)), str(addr), str(value), "200000", "")
            verdict = re.search(r"PERTURBATION_DIVERGENCE=(PASS|FAIL)", perturb_raw)
            if not verdict or verdict.group(1) != "PASS":
                raise SystemExit(f"FAIL: anchor perturbation for {name} addr={addr}")
            anchors.append({
                "from_step": left["step"],
                "to_step": right["step"],
                "from_byte": left["a_before"] % 256,
                "to_byte": right["a_before"] % 256,
                "mandatory_next_c": addr,
                "halt_source_value": value,
                "jumps_before_next_phase": len(jumps),
                "isolation": "PASS" if not jumps else "NOT_DEMONSTRATED",
            })
        if any(anchor["isolation"] != "PASS" for anchor in anchors):
            raise SystemExit(f"FAIL: chase crosses phase boundary for {name}")
        cases.append({"program": name, "output": output.group(1), "phases": len(phases), "anchors": anchors, "status": "PASS"})

    print(json.dumps({"schema": "malbolge-anchor-isolation-v1", "status": "PASS", "general_generation": "NOT_DEMONSTRATED", "cases": cases}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
