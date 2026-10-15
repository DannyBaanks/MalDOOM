#!/usr/bin/env py
"""
MALDOOM ADD1 Search — Guided mutation from truth_machine.mal
Uses bolge.exe batch + Walbolge trace verification.
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
import random
from typing import List, Dict, Optional
from dataclasses import dataclass


# ─── Constants & Helpers ──────────────────────────────────────────────────

XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"

def load_seed(path: str) -> str:
    with open(path, 'r') as f:
        return f.read().strip()


def mutate_program(program: str, mutation_rate: float = 0.1) -> str:
    chars = list(program)
    ops = ['i', '<', '/', 'p', '*', 'j', 'o', 'v']
    for i in range(len(chars)):
        if random.random() < mutation_rate:
            op = random.choice(['i', '<', '/', 'p', '*', 'j', 'o', 'v'])
            chars[i] = chr((XLAT1.index(op) - i) % 94 + 33)
    return ''.join(chars)


def crossover(p1: str, p2: str) -> str:
    if len(p1) != len(p2):
        return p1
    point = random.randint(1, len(p1) - 1)
    return p1[:point] + p2[point:]


# ─── Constraints & Verification ───────────────────────────────────────────

@dataclass
class Add1Constraints:
    tape_addr: int = 1002
    expected_value: int = 1
    require_halt: bool = True


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


def save_evidence(program: str, final_state: Dict):
    sha = hashlib.sha256(program.encode()).hexdigest()
    os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal", "w") as f:
        f.write(program)
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.json", "w") as f:
        json.dump({
            "program": program,
            "sha256": hashlib.sha256(program.encode()).hexdigest(),
            "length": len(program),
            "final_state": final_state,
            "verified_in": ["bolge_exe_batch", "walbolge_trace"]
        }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
    print(f"[EVIDENCE] Saved to evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal")


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


# ─── Mutation Strategies ──────────────────────────────────────────────────

def load_seed(path: str) -> str:
    with open(path, 'r') as f:
        return f.read().strip()


def mutate_program(program: str, mutation_rate: float = 0.1) -> str:
    chars = list(program)
    ops = ['i', '<', '/', 'p', '*', 'j', 'o', 'v']
    for i in range(len(chars)):
        if random.random() < mutation_rate:
            op = random.choice(['i', '<', '/', 'p', '*', 'j', 'o', 'v'])
            chars[i] = chr((XLAT1.index(op) - i) % 94 + 33)
    return ''.join(chars)


def crossover(p1: str, p2: str) -> str:
    if len(p1) != len(p2):
        return p1
    point = random.randint(1, len(p1) - 1)
    return p1[:point] + p2[point:]


# ─── Walbolge Verification ────────────────────────────────────────────────

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


def save_evidence(program: str, final_state: Dict):
    sha = hashlib.sha256(program.encode()).hexdigest()
    os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal", "w") as f:
        f.write(program)
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.json", "w") as f:
        json.dump({
            "program": program,
            "sha256": hashlib.sha256(program.encode()).hexdigest(),
            "length": len(program),
            "final_state": final_state,
            "verified_in": ["bolge_exe_batch", "walbolge_trace"]
        }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
    print(f"[EVIDENCE] Saved to evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal")


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


# ─── Mutation Strategies ──────────────────────────────────────────────────

def load_seed(path: str) -> str:
    with open(path, 'r') as f:
        return f.read().strip()


def mutate_program(program: str, mutation_rate: float = 0.1) -> str:
    chars = list(program)
    ops = ['i', '<', '/', 'p', '*', 'j', 'o', 'v']
    for i in range(len(chars)):
        if random.random() < mutation_rate:
            op = random.choice(['i', '<', '/', 'p', '*', 'j', 'o', 'v'])
            chars[i] = chr((XLAT1.index(op) - i) % 94 + 33)
    return ''.join(chars)


def crossover(p1: str, p2: str) -> str:
    if len(p1) != len(p2):
        return p1
    point = random.randint(1, len(p1) - 1)
    return p1[:point] + p2[point:]


# ─── Main Search Loop ────────────────────────────────────────────────────

def guided_search(bolge_runner):
    print("=" * 70)
    print("MALDOOM ADD1 GUIDED SEARCH — bolge.exe + Walbolge")
    print("=" * 70)
    
    seed = load_seed(r"C:\Development\ISyCo Git\MALPAD\evidence\m2_state\truth_machine.mal")
    print(f"[seed] truth_machine.mal: {len(seed)} chars")
    
    population = [load_seed(r"C:\Development\ISyCo Git\MALPAD\evidence\m2_state\truth_machine.mal")]
    pop_size = 20
    generations = 50
    
    for _ in range(pop_size - 1):
        population.append(mutate_program(population[0], 0.05))
    
    print(f"\n[init] Population: {pop_size} individuals")
    
    for gen in range(generations):
        print(f"\n{'='*60}")
        print(f"GENERATION {gen + 1}/{generations}")
        print(f"{'='*60}")
        
        print(f"[eval] Running batch on {len(population)} programs...")
        results = bolge_runner.run_batch(population, b"", 5000)
        
        fitness_scores = []
        candidates_for_walbolge = []
        
        for prog, res in zip(population, results):
            score = 0
            if res["terminated"]:
                score += 10
                candidates_for_walbolge.append(prog)
            fitness_scores.append((prog, score, res))
        
        print(f"[walbolge] Verifying {len(candidates_for_walbolge)} terminated candidates...")
        
        for prog in candidates_for_walbolge:
            result = verify_add1(prog, 10000)
            if result:
                print(f"\n[VERIFIED] ADD1 FOUND: {prog}")
                print(f"  tape[1002] = {result['tape'][1002]}")
                print(f"  steps={result['steps']}, a={result['a']}, c={result['c']}, d={result['d']}")
                save_evidence(prog, result)
                return prog
        
        fitness_scores.sort(key=lambda x: x[1], reverse=True)
        top = [x[0] for x in fitness_scores[:pop_size // 2]]
        
        new_pop = top[:]
        while len(new_pop) < pop_size:
            if random.random() < 0.7 and len(top) >= 2:
                p1, p2 = random.sample(top, 2)
                child = crossover(p1, p2)
            else:
                parent = random.choice(top)
                child = mutate_program(parent, 0.08)
            new_pop.append(child)
        
        population = new_pop
        print(f"[gen {gen+1}] Best score: {fitness_scores[0][1]}, top prog: {fitness_scores[0][0][:50]}...")
    
    print("\n[search] No ADD1 found after all generations")
    return None


# ─── Walbolge Verification ────────────────────────────────────────────────

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


def save_evidence(program: str, final_state: Dict):
    sha = hashlib.sha256(program.encode()).hexdigest()
    os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal", "w") as f:
        f.write(program)
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.json", "w") as f:
        json.dump({
            "program": program,
            "sha256": hashlib.sha256(program.encode()).hexdigest(),
            "length": len(program),
            "final_state": final_state,
            "verified_in": ["bolge_exe_batch", "walbolge_trace"]
        }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
    print(f"[EVIDENCE] Saved to evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal")


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


# ─── Mutation Strategies ──────────────────────────────────────────────────

def load_seed(path: str) -> str:
    with open(path, 'r') as f:
        return f.read().strip()


def mutate_program(program: str, mutation_rate: float = 0.1) -> str:
    chars = list(program)
    ops = ['i', '<', '/', 'p', '*', 'j', 'o', 'v']
    for i in range(len(chars)):
        if random.random() < mutation_rate:
            op = random.choice(['i', '<', '/', 'p', '*', 'j', 'o', 'v'])
            chars[i] = chr((XLAT1.index(op) - i) % 94 + 33)
    return ''.join(chars)


def crossover(p1: str, p2: str) -> str:
    if len(p1) != len(p2):
        return p1
    point = random.randint(1, len(p1) - 1)
    return p1[:point] + p2[point:]


# ─── Main Search Loop ────────────────────────────────────────────────────

def guided_search(bolge_runner):
    print("=" * 70)
    print("MALDOOM ADD1 GUIDED SEARCH — bolge.exe + Walbolge")
    print("=" * 70)
    
    seed = load_seed(r"C:\Development\ISyCo Git\MALPAD\evidence\m2_state\truth_machine.mal")
    print(f"[seed] truth_machine.mal: {len(seed)} chars")
    
    population = [load_seed(r"C:\Development\ISyCo Git\MALPAD\evidence\m2_state\truth_machine.mal")]
    pop_size = 20
    generations = 50
    
    for _ in range(pop_size - 1):
        population.append(mutate_program(population[0], 0.05))
    
    print(f"\n[init] Population: {pop_size} individuals")
    
    for gen in range(generations):
        print(f"\n{'='*60}")
        print(f"GENERATION {gen + 1}/{generations}")
        print(f"{'='*60}")
        
        print(f"[eval] Running batch on {len(population)} programs...")
        results = bolge_runner.run_batch(population, b"", 5000)
        
        fitness_scores = []
        candidates_for_walbolge = []
        
        for prog, res in zip(population, results):
            score = 0
            if res["terminated"]:
                score += 10
                candidates_for_walbolge.append(prog)
            fitness_scores.append((prog, score, res))
        
        print(f"[walbolge] Verifying {len(candidates_for_walbolge)} terminated candidates...")
        
        for prog in candidates_for_walbolge:
            result = verify_add1(prog, 10000)
            if result:
                print(f"\n[VERIFIED] ADD1 FOUND: {prog}")
                print(f"  tape[1002] = {result['tape'][1002]}")
                print(f"  steps={result['steps']}, a={result['a']}, c={result['c']}, d={result['d']}")
                save_evidence(prog, result)
                return prog
        
        fitness_scores.sort(key=lambda x: x[1], reverse=True)
        top = [x[0] for x in fitness_scores[:pop_size // 2]]
        
        new_pop = top[:]
        while len(new_pop) < pop_size:
            if random.random() < 0.7 and len(top) >= 2:
                p1, p2 = random.sample(top, 2)
                child = crossover(p1, p2)
            else:
                parent = random.choice(top)
                child = mutate_program(parent, 0.08)
            new_pop.append(child)
        
        population = new_pop
        print(f"[gen {gen+1}] Best score: {fitness_scores[0][1]}, top prog: {fitness_scores[0][0][:50]}...")
    
    print("\n[search] No ADD1 found after all generations")
    return None


# ─── Walbolge Verification ────────────────────────────────────────────────

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


def save_evidence(program: str, final_state: Dict):
    sha = hashlib.sha256(program.encode()).hexdigest()
    os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal", "w") as f:
        f.write(program)
    with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.json", "w") as f:
        json.dump({
            "program": program,
            "sha256": hashlib.sha256(program.encode()).hexdigest(),
            "length": len(program),
            "final_state": final_state,
            "verified_in": ["bolge_exe_batch", "walbolge_trace"]
        }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
    print(f"[EVIDENCE] Saved to evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal")


# ─── Main ────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("MALDOOM ADD1 GUIDED SEARCH — bolge.exe batch + Walbolge")
    print("=" * 70)
    
    bolge_runner = BolgeBatchRunner()
    print("[init] bolge.exe batch runner ready")
    
    found = guided_search(bolge_runner)
    
    if found:
        print(f"\n[SUCCESS] ADD1 found: {found}")
    else:
        print("\n[search] No ADD1 found after guided search")


# ─── Imports & Classes ───────────────────────────────────────────────────

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
import random
from typing import List, Dict, Optional
from dataclasses import dataclass


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


# ─── Mutation Strategies ──────────────────────────────────────────────────

XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"

def load_seed(path: str) -> str:
    with open(path, 'r') as f:
        return f.read().strip()


def mutate_program(program: str, mutation_rate: float = 0.1) -> str:
    chars = list(program)
    ops = ['i', '<', '/', 'p', '*', 'j', 'o', 'v']
    for i in range(len(chars)):
        if random.random() < mutation_rate:
            op = random.choice(['i', '<', '/', 'p', '*', 'j', 'o', 'v'])
            chars[i] = chr((XLAT1.index(op) - i) % 94 + 33)
    return ''.join(chars)


def crossover(p1: str, p2: str) -> str:
    if len(p1) != len(p2):
        return p1
    point = random.randint(1, len(p1) - 1)
    return p1[:point] + p2[point:]


def guided_search(bolge_runner):
    print("=" * 70)
    print("MALDOOM ADD1 GUIDED SEARCH — bolge.exe + Walbolge")
    print("=" * 70)
    
    seed = load_seed(r"C:\Development\ISyCo Git\MALPAD\evidence\m2_state\truth_machine.mal")
    print(f"[seed] truth_machine.mal: {len(seed)} chars")
    
    population = [load_seed(r"C:\Development\ISyCo Git\MALPAD\evidence\m2_state\truth_machine.mal")]
    pop_size = 20
    generations = 50
    
    for _ in range(pop_size - 1):
        population.append(mutate_program(population[0], 0.05))
    
    print(f"\n[init] Population: {pop_size} individuals")
    
    for gen in range(generations):
        print(f"\n{'='*60}")
        print(f"GENERATION {gen + 1}/{generations}")
        print(f"{'='*60}")
        
        print(f"[eval] Running batch on {len(population)} programs...")
        results = bolge_runner.run_batch(population, b"", 5000)
        
        fitness_scores = []
        candidates_for_walbolge = []
        
        for prog, res in zip(population, results):
            score = 0
            if res["terminated"]:
                score += 10
                candidates_for_walbolge.append(prog)
            fitness_scores.append((prog, score, res))
        
        print(f"[walbolge] Verifying {len(candidates_for_walbolge)} terminated candidates...")
        
        for prog in candidates_for_walbolge:
            result = verify_add1(prog, 10000)
            if result:
                print(f"\n[VERIFIED] ADD1 FOUND: {prog}")
                print(f"  tape[1002] = {result['tape'][1002]}")
                print(f"  steps={result['steps']}, a={result['a']}, c={result['c']}, d={result['d']}")
                save_evidence(prog, result)
                return prog
        
        fitness_scores.sort(key=lambda x: x[1], reverse=True)
        top = [x[0] for x in fitness_scores[:pop_size // 2]]
        
        new_pop = top[:]
        while len(new_pop) < pop_size:
            if random.random() < 0.7 and len(top) >= 2:
                p1, p2 = random.sample(top, 2)
                child = crossover(p1, p2)
            else:
                parent = random.choice(top)
                child = mutate_program(parent, 0.08)
            new_pop.append(child)
        
        population = new_pop
        print(f"[gen {gen+1}] Best score: {fitness_scores[0][1]}, top prog: {fitness_scores[0][0][:50]}...")
    
    print("\n[search] No ADD1 found after all generations")
    return None


# ─── Main ────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("MALDOOM ADD1 GUIDED SEARCH — bolge.exe batch + Walbolge")
    print("=" * 70)
    
    bolge_runner = BolgeBatchRunner()
    print("[init] bolge.exe batch runner ready")
    
    found = guided_search(bolge_runner)
    
    if found:
        print(f"\n[SUCCESS] ADD1 found: {found}")
    else:
        print("\n[search] No ADD1 found after guided search")


# ─── Imports ────────────────────────────────────────────────────────────

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
import random
from typing import List, Dict, Optional
from dataclasses import dataclass


if __name__ == "__main__":
    import time
    import random
    
    print("=" * 70)
    print("MALDOOM ADD1 GUIDED SEARCH — bolge.exe batch + Walbolge")
    print("=" * 70)
    
    main()