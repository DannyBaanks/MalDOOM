#!/usr/bin/env py
"""
MALDOOM ADD1 Search — Hybrid: bolge.exe batch + Walbolge trace verification
1. bolge.exe batch (BOLG1/BOLG2): fast execution with final state
2. Walbolge trace (on_step): full tape verification tape[1002] == 1
3. Evidence: SHA256 + final state + trace excerpt
"""

from __future__ import annotations
import sys
sys.path.insert(0, r"C:\Development\ISyCo Git\MALDOOM")
sys.path.insert(0, r"C:\Development\ISyCo Git\Autobolge\zig")
sys.path.insert(0, r"C:\Development\ISyCo Git\Walbolge")

from scripts.search_bolge_batch import BolgeBatchSearcher, create_bolg1_input, parse_bolg2_output
from walbolge.trace import trace_program
import itertools
import time
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Dict, Optional


# ─── Constraints ────────────────────────────────────────────────────────────

@dataclass
class Add1Constraints:
    tape_addr: int = 1002      # BASE+2 where tick/counter lives
    expected_value: int = 1    # increment from 0 to 1
    require_halt: bool = True


# ─── Bolge.exe Batch Runner ────────────────────────────────────────────────

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


# ─── Walbolge Verification ────────────────────────────────────────────────

def verify_add1_with_walbolge(program: str, constraints: 'Add1Constraints', max_steps: int = 10000) -> Optional[Dict]:
    final_tape = []
    
    def on_step(ev, tape):
        final_tape.clear()
        final_tape.extend(tape)
    
    trace = trace_program(program, max_steps=max_steps, classic=True, on_step=on_step)
    
    if not trace.halted or trace.halt_reason != "halt_opcode":
        return None
    
    if trace.events:
        last = trace.events[-1]
        final_a = last.a_after
        final_c = last.c
        final_d = last.d
    else:
        final_a = final_c = final_d = 0
    
    if len(final_tape) <= 1002:
        return None
    if final_tape[1002] != 1:
        return None
    
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


# ─── Exhaustive Search ────────────────────────────────────────────────────

def exhaustive_search_add1(bolge_runner: 'BolgeBatchRunner', max_len: int = 12, 
                          batch_size: int = 2000, max_total: int = 50000) -> Optional[str]:
    ops = ['i', '<', '/', 'p', '*', 'j', 'o', 'v']
    
    print(f"[search] Exhaustive search up to length {max_len}, max {max_total} programs")
    
    for length in range(8, max_len + 1):
        print(f"\n[search] Length {length}: 8^{length} = {8**length} combinations")
        
        batch = []
        evaluations = 0
        start = time.time()
        
        for combo in itertools.product(['i', '<', '/', 'p', '*', 'j', 'o', 'v'], repeat=length):
            program = ''.join(combo)
            batch.append(program)
            
            if len(batch) >= 2000:
                results = bolge_runner.run_batch(batch, b"", 10000)
                for prog, res in zip(batch, results):
                    if res["terminated"]:
                        wal_result = verify_add1_with_walbolge(prog, None, 10000)
                        if wal_result:
                            return prog
                evaluations += len(batch)
                batch = []
                
                if evaluations % 10000 == 0:
                    elapsed = time.time() - start
                    rate = evaluations / elapsed if elapsed > 0 else 0
                    print(f"  {evaluations} evals ({rate:.0f} prog/s)")
                
                if evaluations >= 50000:
                    break
        
        if batch:
            results = bolge_runner.run_batch(batch, b"", 10000)
            for prog, res in zip(batch, results):
                if res["terminated"]:
                    wal_result = verify_add1_with_walbolge(prog, None, 10000)
                    if wal_result:
                        return prog
            evaluations += len(batch)
        
        elapsed = time.time() - start
        print(f"  Length {length}: {evaluations} evals in {elapsed:.1f}s, no ADD1 found")
    
    return None


def load_seed_program(path: str) -> str:
    with open(path, 'r') as f:
        return f.read().strip()


def save_evidence(program: str, final_state: Dict):
    sha = hashlib.sha256(program.encode()).hexdigest()
    os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
    
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{hashlib.sha256(program.encode()).hexdigest()[:8]}.mal", "w") as f:
        f.write(program)
    
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{hashlib.sha256(program.encode()).hexdigest()[:8]}.json", "w") as f:
        json.dump({
            "program": program,
            "sha256": hashlib.sha256(program.encode()).hexdigest(),
            "length": len(program),
            "final_state": final_state,
            "verified_in": ["bolge_exe_batch", "walbolge_trace"]
        }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
    
    print(f"[EVIDENCE] Saved to evidence/FRAGMENTS_VERIFIED/ADD1_...")


def main():
    print("=" * 70)
    print("MALDOOM ADD1 SEARCH — bolge.exe batch + Walbolge trace")
    print("=" * 70)
    
    # Load seed
    seed = load_seed_program(r"C:\Development\ISyCo Git\MALPAD\evidence\m2_state\truth_machine.mal")
    print(f"[seed] truth_machine.mal: {len(seed)} chars")
    
    # Initialize runners
    bolge_runner = BolgeBatchRunner()
    print("[init] bolge.exe batch runner ready")
    
    # Exhaustive search
    print("\n" + "=" * 70)
    print("PHASE 1: Exhaustive search (short programs)")
    print("=" * 70)
    
    found = exhaustive_search_add1(bolge_runner, max_len=10, max_total=30000)
    
    if found:
        print(f"\n[FOUND] ADD1 at length {len(found)}: {found}")
        final = verify_add1_with_walbolge(found, None, 10000)
        if final:
            print(f"  VERIFIED: tape[1002] = {final['tape'][1002]}")
            save_evidence(found, final)
        return
    
    print("\n[search] No ADD1 found in exhaustive search up to length 10")


if __name__ == "__main__":
    import time
    import itertools
    
    print("=" * 70)
    print("MALDOOM ADD1 SEARCH — bolge.exe batch + Walbolge trace")
    print("=" * 70)
    
    seed = load_seed_program(r"C:\Development\ISyCo Git\MALPAD\evidence\m2_state\truth_machine.mal")
    print(f"[seed] truth_machine.mal: {len(seed)} chars")
    
    bolge_runner = BolgeBatchRunner()
    
    found = exhaustive_search_add1(bolge_runner, max_len=10, max_total=30000)
    
    if found:
        print(f"\n[FOUND] ADD1 at length {len(found)}: {found}")
        final = verify_add1_with_walbolge(found, None, 10000)
        if final:
            print(f"  VERIFIED: tape[1002] = {final['tape'][1002]}")
            save_evidence(found, final)
    else:
        print("\n[search] No ADD1 found in exhaustive search up to length 10")