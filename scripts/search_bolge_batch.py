#!/usr/bin/env py
"""
MALDOOM Zig VM Batch Searcher
Usa bolge.exe (Zig VM) en modo batch para búsqueda masiva con constraints de estado.
Formato: BOLG1 input -> bolge.exe -> BOLG2 output (con final_a, final_c, final_d, steps, terminated)
"""

from __future__ import annotations
import struct
import subprocess
import hashlib
import itertools
import time
import tempfile
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from pathlib import Path


# ─── Binary Format Helpers ──────────────────────────────────────────────────

MAGIC_IN = b"BOLG1"
MAGIC_OUT = b"BOLG2"

def pack_u32(v: int) -> bytes:
    return struct.pack("<I", v)

def pack_u64(v: int) -> bytes:
    return struct.pack("<Q", v)

def unpack_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]

def unpack_u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def encode_program(program: str) -> List[int]:
    """Convierte programa .mal (chars 33-126) a celdas u32 (valores 0..59048)."""
    cells = []
    for ch in program:
        val = ord(ch)
        if 33 <= val <= 126:
            cells.append(val - 33)  # Normalize to 0..93? No, bolge usa valores directos
        else:
            cells.append(val)
    return cells


def create_bolg1_input(programs: List[str], input_bytes: bytes, max_steps: int) -> bytes:
    """Crea archivo BOLG1 binario para batch de programas."""
    out = bytearray()
    out.extend(b"BOLG1")
    out.extend(struct.pack("<Q", len(programs)))  # count
    
    for prog in programs:
        # Convert program to cells (u32 values)
        prog_cells = [ord(ch) for ch in prog]
        prog_len = len(prog_cells)
        
        # record: u32 prog_len + prog_len*u32 + u32 input_len + input_len*u8 + u32 max_steps
        record = bytearray()
        record.extend(struct.pack("<I", prog_len))
        for cell in prog_cells:
            record.extend(struct.pack("<I", cell))
        record.extend(struct.pack("<I", len(input_bytes)))
        record.extend(input_bytes)
        record.extend(struct.pack("<I", max_steps))
        
        out.extend(record)
    
    return bytes(out)


def parse_bolg2_output(data: bytes) -> List[Dict]:
    """Parsea archivo BOLG2 output."""
    if len(data) < 13 or not data.startswith(b"BOLG2"):
        raise ValueError("Invalid BOLG2 magic")
    
    pos = 5
    count = struct.unpack_from("<Q", data, pos)[0]
    pos += 8
    
    results = []
    for _ in range(len(data)):  # iterate count times
        if pos >= len(data):
            break
        
        # result: u32 output_len + output_len*u8 + u64 steps + u8 terminated + u8 reason + u32 final_c + u32 final_a + u32 final_d
        if pos + 4 > len(data):
            break
        output_len = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        
        if pos + output_len > len(data):
            break
        output = data[pos:pos+output_len]
        pos += output_len
        
        if pos + 8 > len(data):
            break
        steps = struct.unpack_from("<Q", data, pos)[0]
        pos += 8
        
        if pos + 2 > len(data):
            break
        terminated = data[pos]
        pos += 1
        reason = data[pos]
        pos += 1
        
        if pos + 12 > len(data):
            break
        final_c = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        final_a = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        final_d = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        
        results.append({
            "output": output,
            "steps": steps,
            "terminated": bool(terminated),
            "reason": reason,
            "final_c": final_c,
            "final_a": final_a,
            "final_d": final_d
        })
    
    return results


# ─── State Constraints ──────────────────────────────────────────────────────

@dataclass
class StateConstraints:
    final_a: Optional[int] = None
    final_c: Optional[int] = None
    final_d: Optional[int] = None
    terminated: Optional[bool] = None
    max_steps: int = 10000
    tape_checks: Dict[int, int] = None  # addr -> expected (NOT available from bolge.exe output!)
    
    def check(self, result: Dict) -> Tuple[bool, Optional[str]]:
        if self.final_a is not None and result["final_a"] != self.final_a:
            return False, f"final_a: {result['final_a']} != {self.final_a}"
        if self.final_c is not None and result["final_c"] != self.final_c:
            return False, f"final_c: {result['final_c']} != {self.final_c}"
        if self.final_d is not None and result["final_d"] != self.final_d:
            return False, f"final_d: {result['final_d']} != {self.final_d}"
        if self.terminated is not None and result["terminated"] != self.terminated:
            return False, f"terminated: {result['terminated']} != {self.terminated}"
        return True, None


# ─── Searcher ────────────────────────────────────────────────────────────────

class BolgeBatchSearcher:
    def __init__(self, bolge_exe: str = r"C:\Development\ISyCo Git\Autobolge\zig\bolge.exe"):
        self.bolge_exe = bolge_exe
        self._verify_vm()
    
    def _verify_vm(self):
        # Test simple program
        test_prog = "v"  # HALT
        result = self.run_batch([test_prog], b"", 100)
        assert len(result) == 1
        assert result[0]["terminated"] == True
        assert result[0]["final_c"] == 1  # c advances to 1 after 'v'
    
    def run_batch(self, programs: List[str], input_bytes: bytes, max_steps: int) -> List[Dict]:
        """Ejecuta batch de programas y retorna resultados parseados."""
        # Create input file
        in_data = create_bolg1_input(programs, b"", max_steps)
        
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f_in:
            f_in.write(in_data)
            in_path = f_in.name
        
        out_path = in_path.replace(".bin", "_out.bin")
        
        try:
            # Run bolge.exe
            cmd = [self.bolge_exe, in_path, out_path]
            proc = subprocess.run(cmd, capture_output=True, timeout=60)
            if proc.returncode != 0:
                raise RuntimeError(f"bolge.exe failed: {proc.stderr.decode()}")
            
            # Read output
            with open(out_path, "rb") as f:
                out_data = f.read()
            
            return parse_bolg2_output(out_data)
        finally:
            for p in [in_path, out_path]:
                if os.path.exists(p):
                    os.unlink(p)


# ─── Search Strategies ──────────────────────────────────────────────────────

def search_exhaustive(
    searcher: 'BolgeBatchSearcher',
    length: int,
    alphabet: List[str],
    constraints,
    prefix: str = "",
    max_steps: int = 10000,
    batch_size: int = 1000
) -> Optional[str]:
    """Búsqueda exhaustiva por lotes."""
    
    ops = ['i', '<', '/', 'p', '*', 'j', 'o', 'v']  # 4,5,23,39,40,62,68,81
    op_chars = {op: chr(op) for op in [4, 5, 23, 39, 40, 62, 68, 81]}
    
    # Generate all combinations
    positions = length - len(prefix)
    if positions <= 0:
        return None
    
    total = len(ops) ** positions
    print(f"[search] Exhaustive: {total} combinations (length={length}, prefix={len(prefix)})")
    
    # Batch evaluation
    batch = []
    evaluations = 0
    start = time.time()
    
    for combo in itertools.product(ops, repeat=positions):
        program = prefix + ''.join(combo)
        batch.append(program)
        
        if len(batch) >= batch_size:
            results = searcher.run_batch(batch, b"", max_steps)
            for prog, res in zip(batch, results):
                if check_constraints(res, constraints):
                    return program
            evaluations += len(batch)
            batch = []
            
            if evaluations % 10000 == 0:
                elapsed = time.time() - start
                print(f"  {evaluations} evals, {evaluations/elapsed:.0f} prog/s")
    
    # Remaining batch
    if batch:
        results = searcher.run_batch(batch, b"", max_steps)
        for prog, res in zip(batch, results):
            if check_constraints(res, constraints):
                return program
        evaluations += len(batch)
    
    print(f"[search] Exhausted {evaluations} programs, not found")
    return None


# ─── Constraint Checker ─────────────────────────────────────────────────────

def check_constraints(result: Dict, constraints) -> bool:
    if constraints.final_a is not None and result["final_a"] != constraints.final_a:
        return False
    if constraints.final_c is not None and result["final_c"] != constraints.final_c:
        return False
    if constraints.final_d is not None and result["final_d"] != constraints.final_d:
        return False
    if constraints.terminated is not None and result["terminated"] != constraints.terminated:
        return False
    return True


# ─── Specs ──────────────────────────────────────────────────────────────────

@dataclass
class SearchSpec:
    name: str
    length: int
    prefix: str = ""
    constraints = None
    max_steps: int = 10000


def get_add1_spec() -> Dict:
    return {
        "name": "add1",
        "length": 20,
        "prefix": "",
        "constraints": type('C', (), {
            "final_a": None,
            "final_c": None,
            "final_d": None,
            "terminated": True
        })(),
        "max_steps": 10000
    }


def get_mul21_add7_spec() -> Dict:
    return {
        "name": "mul21_add7",
        "length": 30,
        "prefix": "",
        "constraints": type('C', (), {
            "final_a": None,
            "final_c": None,
            "final_d": None,
            "terminated": True
        })(),
        "max_steps": 20000
    }


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    import sys
    sys.path.insert(0, r"C:\Development\ISyCo Git\Autobolge\zig")
    
    print("=" * 60)
    print("MALDOOM Zig VM Batch Searcher")
    print("=" * 60)
    
    searcher = BolgeBatchSearcher()
    print("[init] bolge.exe verified")
    
    # Test run
    print("[test] Running test batch...")
    test_progs = ["v", "ov", "pv", "*v"]
    results = searcher.run_batch(test_progs, b"", 100)
    for prog, res in zip(test_progs, results):
        print(f"  {prog}: terminated={res['terminated']}, steps={res['steps']}, a={res['final_a']}, c={res['final_c']}, d={res['final_d']}")
    
    print("\nZig VM batch searcher ready!")
    print("Ready for state-constrained search of MALDOOM fragments.")


if __name__ == "__main__":
    main()