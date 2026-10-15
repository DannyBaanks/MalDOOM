"""Cross-check PCA ladder programs in Python canonical and independent C VMs."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("program_dir", type=Path)
    parser.add_argument("c_engine", type=Path)
    parser.add_argument("names", nargs="*", default=["A", "AA", "AB", "ABC"])
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "malbolge_canonical", Path(r"C:\Development\ISyCo\workspace\assembly\malbolge\malbolge_interpreter.py")
    )
    if spec is None or spec.loader is None:
        raise SystemExit("FAIL: canonical Python interpreter unavailable")
    pyvm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pyvm)

    rows = []
    for name in args.names:
        program = args.program_dir / f"{name}.mal"
        source = program.read_text(encoding="ascii")
        py_output, py_steps, py_status = pyvm.run(source, max_steps=200000)
        c = subprocess.run([str(args.c_engine), str(program), "200000"], input=b"", capture_output=True, check=False)
        c_text = c.stdout.decode("latin-1")
        c_err = c.stderr.decode("latin-1")
        match = re.search(rb"steps: (\d+) \| status: (\w+)", c.stderr)
        c_steps = int(match.group(1)) if match else None
        c_status = match.group(2).decode("ascii") if match else None
        row = {
            "program": name,
            "python": {"output": py_output, "steps": py_steps, "status": py_status},
            "c": {"output": c_text.rstrip("\r\n"), "steps": c_steps, "status": c_status},
        }
        rows.append(row)
        if not (
            c.returncode == 0
            and py_output == c_text.rstrip("\r\n")
            and py_steps == c_steps
            and py_status == "HALTED"
            and c_status == "HALTED"
        ):
            raise SystemExit(f"FAIL: {json.dumps(row, sort_keys=True)}")

    print(json.dumps({"schema": "malbolge-engine-crosscheck-v1", "cases": rows}, sort_keys=True))
    print(f"ENGINE_CROSSCHECK=PASS cases={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
