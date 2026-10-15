"""Finalize the scoped PURE_CONTINUATION_ANCHOR claims from hash-pinned evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    sums = args.evidence / "SHA256SUMS.txt"
    failures = []
    checked = 0
    for line in sums.read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(None, 1)
        actual = hashlib.sha256((args.evidence / relative).read_bytes()).hexdigest().upper()
        checked += 1
        if actual != expected:
            failures.append({"path": relative, "expected": expected, "actual": actual})

    def load(name: str) -> dict:
        return json.loads((args.evidence / name).read_text(encoding="utf-8"))

    r7 = load("R7_full_family.json")
    r8 = load("R8_anchor_isolation.json")
    claims = [
        {"id": "ABC_single_vm_A_B_C_HALT", "status": "PASS", "scope": "ABC.mal, one Zig VM run", "evidence": ["R3_ABC.raw.txt", "ABC.trace.jsonl"]},
        {"id": "residual_S1_S2_causally_necessary_under_selected_perturbations", "status": "PASS", "scope": "specified S1/S2 instruction and data perturbations", "evidence": ["R4_controls.json"]},
        {"id": "independent_engine_agreement_for_measured_family", "status": "PASS", "scope": "Python canonical + independent C VM, 7 programs", "evidence": ["R6_engine_crosscheck.json", "R7_engine_crosscheck.json"]},
        {"id": "dynamic_anchor_isolation_for_measured_family", "status": "PASS" if r8.get("status") == "PASS" else "FAIL", "scope": "6 programs, 10 observed phase anchors", "evidence": ["R5_flow.json", "R8_anchor_isolation.json"]},
        {"id": "all_legal_residual_states_are_continuation_anchors", "status": "NOT_DEMONSTRATED", "scope": "universal claim", "evidence": []},
        {"id": "universal_anchor_isolated_generator", "status": "NOT_DEMONSTRATED", "scope": "all programs and seeds", "evidence": []},
        {"id": "FULL_DOOM_ON_CLASSIC", "status": "NOT_DEMONSTRATED", "scope": "MALDOOM TARGET_B", "evidence": []},
    ]
    result = {
        "schema": "pure-continuation-anchor-final-v1",
        "status": "PASS" if not failures and r7.get("status") == "PASS" and r8.get("status") == "PASS" else "FAIL",
        "hashes_checked": checked,
        "hash_validation": "PASS" if not failures else "FAIL",
        "claims": claims,
        "evidence_failures": failures,
        "scope": "hash-pinned Classic Malbolge micro-experiment; not a universal theorem or Doom milestone",
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"R9_FINAL={'PASS' if result['status'] == 'PASS' else 'FAIL'} hashes={checked} claims={len(claims)}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
