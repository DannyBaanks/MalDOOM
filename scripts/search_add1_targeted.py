#!/usr/bin/env py
"""
MALDOOM ADD1 Search — Targeted insertion into truth_machine.mal
Strategy: Test insertion of ADD1 fragments at various positions in seed.
"""

from __future__ import annotations
import sys
sys.path.insert(0, r"C:\Development\ISyCo Git\MALDOOM")
sys.path.insert(0, r"C:\Development\ISyCo Git\Autobolge\zig")
sys.path.insert(0, r"C:\Development\ISyCo Git\Walbolge")

from scripts.search_bolge_batch import BolgeBatchSearcher, create_bolg1_input, parse_bolg2_output
from walbolge.trace import trace_program
import hashlib
import json
import os
import subprocess
import tempfile
from typing import List, Dict, Optional
from dataclasses import dataclass


XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"

def load_seed(path: str) -> str:
    with open(path, 'r') as f:
        return f.read().strip()


@dataclass
class Add1Constraints:
    tape_addr: int = 1002
    expected_value: int = 1
    require_halt: bool = True


class BolgeBatchRunner:
    def __init__(self, bolge_exe: str = r"C:\Development\ISyCo Git\Autobolge\zig\bolge.exe"):
        self.bolge_exe = bolge_exe
        self._verify()

    def _verify(self):
        result = self.run_batch(["v"], b"", 100)
        assert len(result) == 1 and result[0]["terminated"]
        print("[init] bolge.exe batch runner ready")

    def run_batch(self, programs: List[str], input_bytes: bytes, max_steps: int) -> List[Dict]:
        in_data = create_bolg1_input(programs, input_bytes, max_steps)
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f_in:
            f_in.write(in_data)
            in_path = f_in.name
        out_path = in_path.replace(".bin", "_out.bin")
        try:
            cmd = [self.bolge_exe, in_path, out_path]
            proc = subprocess.run(cmd, capture_output=True, timeout=120)
            if proc.returncode != 0:
                raise RuntimeError(f"bolge.exe failed: {proc.stderr.decode()}")
            with open(out_path, "rb") as f:
                out_data = f.read()
            return parse_bolg2_output(out_data)
        finally:
            for p in [in_path, out_path]:
                if os.path.exists(p):
                    os.unlink(p)


def verify_add1(program: str, max_steps: int = 10000) -> Optional[Dict]:
    final_tape = []
    def on_step(ev, tape):
        final_tape.clear()
        final_tape.extend(tape)
    trace = trace_program(program, max_steps=max_steps, classic=True, on_step=on_step)
    if not trace.halted or trace.halt_reason != "halt_opcode":
        return None
    if len(final_tape) <= 1002 or final_tape[1002] != 1:
        return None
    if trace.events:
        last = trace.events[-1]
        final_a = last.a_after
        final_c = last.c
        final_d = last.d
    else:
        final_a = final_c = final_d = 0
    return {
        "steps": trace.steps,
        "halted": trace.halted,
        "halt_reason": trace.halt_reason,
        "a": final_a,
        "c": final_c,
        "d": final_d,
        "tape": final_tape,
        "output": trace.output
    }


def save_evidence(program: str, final_state: Dict, note: str = ""):
    sha = hashlib.sha256(program.encode()).hexdigest()
    os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal", "w") as f:
        f.write(program)
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.json", "w") as f:
        json.dump({
            "program": program,
            "sha256": hashlib.sha256(program.encode()).hexdigest(),
            "length": len(program),
            "note": note,
            "final_state": final_state,
            "verified_in": ["bolge_exe_batch", "walbolge_trace"]
        }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
    print(f"[EVIDENCE] Saved ADD1_{sha[:8]}.mal")


def main():
    print("=" * 70)
    print("MALDOOM ADD1 TARGETED INSERTION — bolge.exe + Walbolge")
    print("=" * 70)

    seed = load_seed(r"C:\Development\ISyCo Git\MALPAD\evidence\m2_state\truth_machine.mal")
    print(f"[seed] truth_machine.mal: {len(seed)} chars")

    # Verify seed does NOT have ADD1
    result = verify_add1(seed)
    if result:
        print(f"  Seed HAS ADD1? tape[1002]={result['tape'][1002] if len(result['tape']) > 1002 else 'N/A'}")
    else:
        print("  Seed does not have ADD1 (expected)")

    bolge_runner = BolgeBatchRunner()
    print("[init] bolge.exe batch runner ready")

    # Try various ADD1 fragments inserted at positions
    fragments = [
        "p" * 10 + "*" * 10 + "p" * 10,
        "p*p*p*p*p*p*p*p*p*p",
        "p*j*p*j*p*j*p*j*p*j",
        "p*p*p*j*j*j*p*p*p*j",
        "p" * 10 + "v",
        "p*" * 10 + "v",
        "p" * 10 + "*" * 10 + "j" * 5 + "p" * 5 + "*" * 5 + "j" * 5,
    ]

    print("\n[search] Trying ADD1 fragment insertions...")
    for pos in range(10, 240, 10):
        for i, fragment in enumerate(fragments):
            candidate = seed[:pos] + fragment + seed[pos:]
            try:
                results = bolge_runner.run_batch([candidate], b"", 5000)
                if results[0]["terminated"]:
                    result = verify_add1(candidate, 10000)
                    if result:
                        print(f"\n[VERIFIED] ADD1 at pos {pos}, frag {i}!")
                        print(f"  tape[1002] = {result['tape'][1002]}")
                        save_evidence(candidate, result, f"pos={pos},frag={i}")
                        return
            except Exception as e:
                pass

    print("\n[search] No ADD1 found with simple fragments. Need real Lou Scheffer ADD1.")
    print("Next: obtain the actual ~95-op Lou Scheffer ADD1 from Malbolge literature.")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, r"C:\Development\ISyCo Git\MALDOOM")
    sys.path.insert(0, r"C:\Development\ISyCo Git\Autobolge\zig")
    sys.path.insert(0, r"C:\Development\ISyCo Git\Walbolge")
    main()