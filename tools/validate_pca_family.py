"""Run the Zig PCA harness over the R7 generated family."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("program_dir", type=Path)
    parser.add_argument("pca", type=Path)
    parser.add_argument("names", nargs="+")
    args = parser.parse_args()
    rows = []
    for name in args.names:
        proc = subprocess.run([str(args.pca), str(args.program_dir / f"{name}.mal"), "200000", ""], capture_output=True, text=True, encoding="utf-8", errors="replace")
        raw = proc.stdout + "\n" + proc.stderr
        status = re.search(r"status=(\w+)", raw)
        steps = re.search(r"status=\w+ steps=(\d+)", raw)
        output = re.search(r"output_len=\d+ output=(.*)", raw)
        row = {"program": name, "status": status.group(1) if status else None, "steps": int(steps.group(1)) if steps else None, "output": output.group(1).rstrip("\r") if output else None}
        rows.append(row)
        if proc.returncode != 0 or row["status"] != "halted" or row["output"] != name.replace("_seed99", ""):
            raise SystemExit(f"FAIL: {json.dumps(row, sort_keys=True)}")
    print(json.dumps({"schema": "malbolge-pca-family-v1", "cases": rows}, sort_keys=True))
    print(f"R7_PCA_FAMILY=PASS cases={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
