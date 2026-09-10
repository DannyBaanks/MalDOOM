"""Build a dynamic access/control-flow map from a PCA JSONL receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.trace.read_text(encoding="utf-8").splitlines() if line.strip()]
    executed = {row["c_before"] for row in rows}
    reads = {row["read_addr"] for row in rows if row["read_addr"] is not None}
    writes = {row["write_addr"] for row in rows if row["write_addr"] is not None}
    encrypted = {row["enc_addr"] for row in rows if row["enc_addr"] is not None}
    jumps = [
        {"step": row["step"], "from": row["c_before"], "to": row["jump_target"]}
        for row in rows
        if row["jump_target"] is not None
    ]
    edges = sorted({(row["c_before"], row["c_after"]) for row in rows})
    phases = [row for row in rows if row["opcode"] == "out"]

    phase_edges = []
    for left, right in zip(phases, phases[1:]):
        between = [row["c_before"] for row in rows if left["step"] <= row["step"] <= right["step"]]
        phase_edges.append({
            "from_phase_step": left["step"],
            "to_phase_step": right["step"],
            "from_byte": left["a_before"] % 256,
            "to_byte": right["a_before"] % 256,
            "observed_path_nodes": between,
            "next_instruction_after_from": left["c_after"],
        })

    def classify(addr: int) -> list[str]:
        result = []
        if addr in executed:
            result.append("executed_instruction")
        if addr in reads:
            result.append("data_read")
        if addr in writes:
            result.append("data_written")
        if addr in encrypted:
            result.append("encryption_written")
        if any(jump["to"] == addr for jump in jumps):
            result.append("jump_target")
        return result or ["unvisited_in_receipt"]

    relevant = sorted(executed | reads | writes | encrypted | {201, 203, 279, 290})
    result = {
        "schema": "malbolge-dynamic-flow-v1",
        "trace_lines": len(rows),
        "executed_instruction_addresses": sorted(executed),
        "data_read_addresses": sorted(reads),
        "data_write_addresses": sorted(writes),
        "encryption_addresses": sorted(encrypted),
        "jumps": jumps,
        "edges": [{"from": left, "to": right} for left, right in edges],
        "phase_boundaries": [
            {"step": row["step"], "byte": row["a_before"] % 256, "c_before": row["c_before"], "c_after": row["c_after"]}
            for row in phases
        ],
        "phase_transition_paths": phase_edges,
        "selected_address_classification": {str(addr): classify(addr) for addr in relevant},
        "scope": "observed dynamic execution only; no universal articulation claim",
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"R5_FLOW=PASS steps={len(rows)} phases={len(phases)} jumps={len(jumps)} addresses={len(relevant)}")
    print(f"R5_203={classify(203)} R5_290={classify(290)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
