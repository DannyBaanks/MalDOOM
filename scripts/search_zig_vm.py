#!/usr/bin/env py
"""
MALDOOM State-Constrained Searcher (Python + Zig VM)
Busca programas Malbolge que satisfagan constraints de estado final (a, c, d, tape).
Usa bolge.exe (Zig VM) como backend de ejecución.
"""

from __future__ import annotations
import subprocess
import json
import argparse
import hashlib
import itertools
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path


@dataclass
class StateConstraints:
    """Constraints on final machine state."""
    final_a: Optional[int] = None
    final_c: Optional[int] = None
    final_d: Optional[int] = None
    final_terminated: Optional[bool] = None
    tape_equals: Optional[Dict[int, int]] = None  # addr -> expected value
    tape_not_equals: Optional[Dict[int, int]] = None
    max_steps: int = 10000


@dataclass
class SearchSpec:
    name: str
    length: int
    input_bytes: bytes = b""
    constraints: StateConstraints = None
    prefix: str = ""  # fixed prefix bytes
    alphabet: List[int] = None  # valid opcodes
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = StateConstraints()
        if self.alphabet is None:
            self.alphabet = [4, 5, 23, 39, 40, 62, 68, 81]  # OPS_VALID


@dataclass
class SearchResult:
    spec: Dict
    found: bool = False
    program: str = ""
    program_sha256: str = ""
    final_state: Dict = None
    evaluations: int = 0
    duration_ms: float = 0.0


class ZigVMSearcher:
    def __init__(self, bolge_exe: str = r"C:\Development\ISyCo Git\Autobolge\zig\bolge.exe"):
        self.bolge_exe = bolge_exe
        # Verify VM works
        result = subprocess.run([bolge_exe, "--help"], capture_output=True, text=True)
        if result.returncode != 0 and "usage" not in result.stderr.lower():
            # bolge.exe might not have --help, try running a simple program
            test = subprocess.run([bolge_exe, "v"], capture_output=True, text=True, timeout=5)
            if test.returncode != 0:
                raise RuntimeError(f"bolge.exe not working: {test.stderr}")
    
    def _run_program(self, program: str, input_bytes: bytes, max_steps: int) -> Dict:
        """Ejecuta programa y retorna estado final."""
        # bolge.exe espera programa en stdin o archivo?
        # Revisar uso: bolge.exe <program.mal> [max_steps]
        # O bolge.exe --stdin < max_steps
        
        # Crear archivo temporal con el programa
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mal', delete=False) as f:
            f.write(program)
            temp_path = f.name
        
        try:
            # bolge.exe <file.mal> [max_steps]
            cmd = [self.bolge_exe, temp_path, str(max_steps)]
            if input_bytes:
                result = subprocess.run(cmd, input=input_bytes, capture_output=True, timeout=30)
            else:
                result = subprocess.run(cmd, capture_output=True, timeout=30)
        finally:
            import os
            os.unlink(temp_path)
        
        # Parse output
        # bolge.exe output format?
        # Según gost.c: imprime output a stdout, estado a stderr?
        # Necesito ver el formato exacto
        
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "program": program
        }
    
    def _check_constraints(self, result: Dict, constraints: StateConstraints) -> Tuple[bool, Optional[str]]:
        """Verifica si el resultado satisface constraints."""
        # Parse bolge.exe output para extraer estado final
        # El formato depende de la implementación
        # Por ahora, retorna True si returncode == 0 y terminated
        return result["returncode"] == 0, None
    
    def search_exhaustive(self, spec: SearchSpec) -> SearchResult:
        """Búsqueda exhaustiva para programas cortos (length <= 10)."""
        result = SearchResult(spec=asdict(spec))
        
        alphabet = spec.alphabet
        prefix = spec.prefix
        length = spec.length
        input_bytes = spec.input_bytes
        constraints = spec.constraints
        
        # Generar todos los programas
        chars = []
        for pos in range(length):
            pos_chars = []
            for op in alphabet:
                # validCharAt(pos, op) en Zig
                v = 33 + ((op - 33 - (prefix.length + pos)) % 94)
                pos_chars.append(chr(v))
            chars.append(pos_chars)
        
        total = len(alphabet) ** length
        print(f"[search] {spec.name}: searching {total} programs (length={length}, alphabet={len(alphabet)})")
        
        evaluations = 0
        start_time = time.time()
        
        for combo in itertools.product(*chars):
            program = prefix + ''.join(combo)
            evaluations += 1
            
            run_result = self._run_program(program, input_bytes, spec.constraints.max_steps)
            ok, divergence = self._check_constraints(run_result, constraints)
            
            if ok:
                result.found = True
                result.program = program
                result.program_sha256 = hashlib.sha256(program.encode()).hexdigest()
                result.evaluations = evaluations
                result.duration_ms = (time.time() - start_time) * 1000
                print(f"[search] FOUND: {program}")
                return result
            
            if evaluations % 10000 == 0:
                elapsed = time.time() - start_time
                rate = evaluations / elapsed if elapsed > 0 else 0
                print(f"[search] {evaluations}/{total} ({rate:.0f} prog/s)")
        
        result.duration_ms = (time.time() - start_time) * 1000
        result.evaluations = evaluations
        return result


# ─── Specs para fragments MALDOOM ──────────────────────────────────────────

def get_add1_spec() -> SearchSpec:
    """ADD 1: [d] = ([d] + 1) % 59049"""
    return SearchSpec(
        name="add1",
        length=20,  # Empezar con 20, aumentar si no encuentra
        input_bytes=b"",
        constraints=StateConstraints(
            tape_equals={1002: 1},  # BASE+2 = 1 (assuming initial 0)
            final_terminated=True
        ),
        alphabet=[4, 5, 23, 39, 40, 62, 68, 81]  # i, <, /, p, *, j, o, v
    )


def get_mul21_add7_spec() -> SearchSpec:
    """MUL21_ADD7: [d] = ([d] * 21 + 7) % 59049"""
    return SearchSpec(
        name="mul21_add7",
        length=30,
        input_bytes=b"",
        constraints=StateConstraints(
            tape_equals={1003: 28},  # BASE+3 = 28 (from 1*21+7)
            final_terminated=True
        ),
        alphabet=[4, 5, 23, 39, 40, 62, 68, 81]
    )


def get_checksum_spec() -> SearchSpec:
    """CHECKSUM: crazy-fold over 378 words"""
    return SearchSpec(
        name="checksum",
        length=50,  # Muy largo, necesita búsqueda guiada
        input_bytes=b"",
        constraints=StateConstraints(
            tape_equals={1378: 12345},  # BASE+378 = checksum
            final_terminated=True
        ),
        alphabet=[4, 5, 23, 39, 40, 62, 68, 81]
    )


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MALDOOM State-Constrained Searcher")
    parser.add_argument("fragment", choices=["add1", "mul21_add7", "checksum", "all"])
    parser.add_argument("--length", type=int, help="Override program length")
    parser.add_argument("--bolge", default=r"C:\Development\ISyCo Git\Autobolge\zig\bolge.exe")
    args = parser.parse_args()
    
    import time
    sys.modules['__main__'].time = time  # hack for time in class
    
    searcher = ZigVMSearcher(args.bolge)
    
    specs = {
        "add1": get_add1_spec(),
        "mul21_add7": get_mul21_add7_spec(),
        "checksum": get_checksum_spec(),
    }
    
    if args.fragment == "all":
        targets = list(specs.keys())
    else:
        targets = [args.fragment]
    
    if args.length:
        for t in targets:
            specs[t].length = args.length
    
    for name in targets:
        spec = specs[name]
        print(f"\n{'='*60}")
        print(f"SEARCHING: {name} (length={spec.length})")
        print(f"{'='*60}")
        
        result = searcher.search_exhaustive(spec)
        
        if result.found:
            print(f"✅ FOUND: {result.program}")
            print(f"   SHA256: {result.program_sha256}")
            print(f"   Evals: {result.evaluations}, Time: {result.duration_ms:.1f}ms")
        else:
            print(f"❌ NOT FOUND in {result.evaluations} evaluations")


if __name__ == "__main__":
    main()