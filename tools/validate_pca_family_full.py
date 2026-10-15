"""Repeat R3-R6 over the expanded PCA family without hardcoded addresses."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path


def run(exe: Path, *args: str) -> str:
    proc = subprocess.run([str(exe), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {exe} {args}: {proc.stderr}")
    return proc.stdout + "\n" + proc.stderr


def perturb(exe: Path, program: Path, phase: int, addr: int, value: int) -> tuple[str, str]:
    raw = run(exe, "perturb", str(program), str(phase), str(addr), str(value), "200000", "")
    control = re.search(r"CONTROL\s+resume:.* output=([^\r\n]*)", raw)
    changed = re.search(r"PERTURB\s+addr=.* output=([^\r\n]*)", raw)
    verdict = re.search(r"PERTURBATION_DIVERGENCE=(PASS|FAIL)", raw)
    if not control or not changed or not verdict:
        raise RuntimeError(f"malformed perturb receipt: {raw[-500:]}")
    return control.group(1), changed.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("program_dir", type=Path)
    parser.add_argument("pca", type=Path)
    parser.add_argument("c_engine", type=Path)
    parser.add_argument("names", nargs="+", default=["ABA", "AAB", "ABC_seed99"])
    args = parser.parse_args()
    cases = []

    for name in args.names:
        program = args.program_dir / f"{name}.mal"
        normal = run(args.pca, str(program), "200000", "")
        status = re.search(r"status=(\w+)", normal)
        steps = re.search(r"status=\w+ steps=(\d+)", normal)
        output = re.search(r"output_len=\d+ output=([^\r\n]*)", normal)
        audit = re.search(r"audit: memory_loads=(\d+) vm_initializations=(\d+) snapshots=(\d+) host_injections=(\d+)", normal)
        phases = [
            {"index": int(i), "step": int(step), "a": int(a), "c": int(c), "d": int(d)}
            for i, step, a, c, d in re.findall(r"phase\[(\d+)\] byte=0x[0-9a-f]+ step=(\d+) a=(\d+) c=(\d+) d=(\d+)", normal)
        ]
        if not status or not steps or not output or not audit or status.group(1) != "halted":
            raise SystemExit(f"FAIL: malformed PCA run for {name}")
        if audit.groups() != ("1", "1", "0", "0"):
            raise SystemExit(f"FAIL: R3 audit for {name}: {audit.groups()}")

        trace_raw = run(args.pca, "trace-jsonl", str(program), "200000", "")
        trace_rows = [json.loads(line) for line in trace_raw.splitlines() if line.strip().startswith("{")]
        controls = []
        for phase in phases[:-1]:
            expected_tail = output.group(1)[phase["index"] + 1 :]
            selected = []
            for value in range(0, 127):
                try:
                    control, changed = perturb(args.pca, program, phase["index"], phase["c"] + 1, value)
                except RuntimeError:
                    continue
                if control == expected_tail and changed != expected_tail:
                    selected.append({"addr": phase["c"] + 1, "new_value": value, "control": control, "perturbed": changed})
                if len(selected) == 3:
                    break
            if len(selected) < 3:
                raise SystemExit(f"FAIL: fewer than 3 instruction perturbations for {name} phase {phase['index']}")
            controls.append({"kind": "instruction", "phase": phase["index"], "tests": selected})

        for left, right in zip(phases, phases[1:]):
            reads = []
            for row in trace_rows:
                if left["step"] < row["step"] < right["step"] and row["read_addr"] is not None:
                    if row["read_addr"] not in reads:
                        reads.append(row["read_addr"])
            found = None
            expected_tail = output.group(1)[left["index"] + 1 :]
            for addr in reads:
                selected = []
                for value in range(0, 8):
                    try:
                        control, changed = perturb(args.pca, program, left["index"], addr, value)
                    except RuntimeError:
                        continue
                    if control == expected_tail and changed != expected_tail:
                        selected.append({"addr": addr, "new_value": value, "control": control, "perturbed": changed})
                if len(selected) >= 3:
                    found = {"kind": "data", "phase": left["index"], "tests": selected[:3]}
                    break
            if found is not None:
                controls.append(found)

        trace_path = Path(tempfile.mktemp(suffix=".jsonl"))
        flow_path = Path(tempfile.mktemp(suffix=".json"))
        try:
            trace_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in trace_rows) + "\n", encoding="utf-8")
            flow_proc = subprocess.run(["py", str(Path(__file__).with_name("analyze_pca_flow.py")), str(trace_path), str(flow_path)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            if flow_proc.returncode != 0:
                raise SystemExit(f"FAIL: R5 flow for {name}: {flow_proc.stderr}")
            flow = json.loads(flow_path.read_text(encoding="utf-8"))
        finally:
            trace_path.unlink(missing_ok=True)
            flow_path.unlink(missing_ok=True)

        cross = subprocess.run(
            ["py", str(Path(__file__).with_name("validate_pca_engines.py")), str(args.program_dir), str(args.c_engine), name],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        if cross.returncode != 0 or "ENGINE_CROSSCHECK=PASS cases=1" not in cross.stdout:
            raise SystemExit(f"FAIL: R6 crosscheck for {name}: {cross.stdout}{cross.stderr}")

        cases.append({
            "program": name,
            "pca": {"status": status.group(1), "steps": int(steps.group(1)), "output": output.group(1), "phases": len(phases)},
            "R3_audit": dict(zip(("memory_loads", "vm_initializations", "snapshots", "host_injections"), map(int, audit.groups()))),
            "R5_flow": {"steps": flow["trace_lines"], "jumps": len(flow["jumps"]), "addresses": len(flow["executed_instruction_addresses"])},
            "R6_crosscheck": "PASS",
            "R4_controls": controls,
            "R4_status": "PASS" if len(controls) >= len(phases) - 1 else "PARTIAL",
        })

    print(json.dumps({"schema": "malbolge-pca-family-full-v1", "status": "PASS", "cases": cases}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
