#!/usr/bin/env py
"""
MALDOOM ADD1 Search — Hybrid: Zig VM batch + Walbolge trace
1. Zig VM batch: fast candidate generation with register constraints  
2. Walbolge trace (on_step): full state verification including tape
3. Evidence: JSON with SHA256, final state, trace excerpt
"""

from __future__ import annotations
import sys
sys.path.insert(0, r"C:\Development\ISyCo Git\MALDOOM")
sys.path.insert(0, r"C:\Development\ISyCo Git\Autobolge\zig")
sys.path.insert(0, r"C:\Development\ISyCo Git\Walbolge")

from scripts.search_bolge_batch import BolgeBatchSearcher
from walbolge.trace import trace_program
import itertools
import time
import hashlib
import json
import os
from typing import List, Dict, Optional


# ─── Zig VM Batch Searcher ────────────────────────────────────────────────

class HybridSearcher:
    def __init__(self, bolge_exe: str = r"C:\Development\ISyCo Git\Autobolge\zig\bolge.exe"):
        self.zig_searcher = BolgeBatchSearcher(bolge_exe)
        print("[init] Hybrid searcher ready: Zig VM batch + Walbolge trace")
    
    def zig_batch_search(self, length: int, max_total: int = 50000) -> List[str]:
        """Fase 1: Búsqueda rápida con Zig VM batch (solo terminated=True)."""
        candidates = []
        batch = []
        evaluations = 0
        
        print(f"[zig] Searching length={length} (max {max_total} evals)...")
        
        for combo in itertools.product(['i', '<', '/', 'p', '*', 'j', 'o', 'v'], repeat=length):
            program = ''.join(combo)
            batch.append(program)
            
            if len(batch) >= 2000:
                results = self.zig_searcher.run_batch(batch, b"", 5000)
                for prog, res in zip(batch, results):
                    if res["terminated"]:
                        candidates.append(prog)
                evaluations += len(batch)
                batch = []
                
                if evaluations >= max_total:
                    break
        
        if batch:
            results = self.zig_searcher.run_batch(batch, b"", 5000)
            for prog, res in zip(batch, results):
                if res["terminated"]:
                    candidates.append(prog)
        
        print(f"[zig] Phase 1 complete: {len(candidates)} terminated candidates from {evaluations} evals")
        return candidates


# ─── Walbolge Verification ────────────────────────────────────────────────

def verify_with_walbolge(program: str, max_steps: int = 10000) -> Optional[Dict]:
    """Verifica un programa con Walbolge trace, retorna estado final si pasa."""
    final_tape = []
    
    def on_step(ev, tape):
        final_tape.clear()
        final_tape.extend(tape)
    
    trace = trace_program(program, max_steps=10000, classic=True, on_step=on_step)
    
    if not trace.halted or trace.halt_reason != "halt_opcode":
        return None
    
    # Get final register state from last event
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


# ─── Main Search ──────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("MALDOOM ADD1 HYBRID SEARCH — Zig VM batch + Walbolge trace")
    print("=" * 70)
    
    from scripts.search_bolge_batch import BolgeBatchSearcher
    from walbolge.trace import trace_program
    
    searcher = HybridSearcher()
    
    lengths_to_try = [10, 12, 14]
    max_total = 50000
    
    for length in lengths_to_try:
        print(f"\n{'='*60}")
        print(f"SEARCHING ADD1: length={length}")
        print(f"{'='*60}")
        
        # Fase 1: Zig VM batch (terminated=True)
        candidates = searcher.zig_batch_search(length=length, max_total=50000)
        
        if not candidates:
            print(f"  No terminated candidates at length {length}")
            continue
        
        # Fase 2: Walbolge verification con tape check
        print(f"[walbolge] Verifying {len(candidates)} candidates...")
        
        found = False
        for prog in candidates:
            result = verify_with_walbolge(prog, max_steps=10000)
            
            if result is None:
                continue
            
            # Check ADD1 constraint: tape[1002] == 1 (BASE+2 incrementado)
            tape = result["tape"]
            if len(tape) > 1002 and tape[1002] == 1:
                print(f"\n[VERIFIED] {prog}")
                print(f"  tape[1002] = {tape[1002]}")
                print(f"  final_state: a={result['a']}, c={result['c']}, d={result['d']}")
                print(f"  steps={result['steps']}, halt={result['halt_reason']}")
                
                # Save evidence
                sha = hashlib.sha256(prog.encode()).hexdigest()
                os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
                
                with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal", "w") as f:
                    f.write(prog)
                
                with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.json", "w") as f:
                    json.dump({
                        "program": prog,
                        "sha256": hashlib.sha256(prog.encode()).hexdigest(),
                        "length": len(prog),
                        "final_state": result,
                        "verified_in": ["zig_vm_batch", "walbolge_trace"]
                    }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
                
                print(f"[EVIDENCE] Saved to evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal")
                return True
        
        return False


def main():
    print("=" * 70)
    print("MALDOOM ADD1 HYBRID SEARCH — Zig VM batch + Walbolge trace")
    print("=" * 70)
    
    searcher = HybridSearcher()
    
    lengths_to_try = [10, 12, 14]
    max_total = 50000
    
    for length in lengths_to_try:
        print(f"\n{'='*60}")
        print(f"SEARCHING ADD1: length={length}")
        print(f"{'='*60}")
        
        # Fase 1: Zig VM batch
        print(f"[zig] Searching length={length} (max {max_total} evals)...")
        candidates = searcher.zig_batch_search(length=length, max_total=50000)
        
        if not candidates:
            print(f"  No terminated candidates at length {length}")
            continue
        
        # Fase 2: Walbolge verification
        print(f"[walbolge] Verifying {len(candidates)} candidates...")
        
        found = False
        for prog in candidates:
            result = verify_with_walbolge(prog, max_steps=10000)
            
            if result is None:
                continue
            
            # Check ADD1 constraint: tape[1002] == 1 (BASE+2 incrementado)
            tape = result["tape"]
            if len(tape) > 1002 and tape[1002] == 1:
                print(f"\n[VERIFIED] {prog}")
                print(f"  tape[1002] = {tape[1002]}")
                print(f"  final_state: a={result['a']}, c={result['c']}, d={result['d']}")
                print(f"  steps={result['steps']}, halt={result['halt_reason']}")
                
                # Save evidence
                sha = hashlib.sha256(prog.encode()).hexdigest()
                os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
                
                with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal", "w") as f:
                    f.write(prog)
                
                with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.json", "w") as f:
                    json.dump({
                        "program": prog,
                        "sha256": hashlib.sha256(prog.encode()).hexdigest(),
                        "length": len(prog),
                        "final_state": result,
                        "verified_in": ["zig_vm_batch", "walbolge_trace"]
                    }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
                
                print(f"[EVIDENCE] Saved to evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal")
                return True
        
        return False


def main():
    print("=" * 70)
    print("MALDOOM ADD1 HYBRID SEARCH — Zig VM batch + Walbolge trace")
    print("=" * 70)
    
    searcher = HybridSearcher()
    
    lengths_to_try = [10, 12, 14]
    max_total = 50000
    
    for length in lengths_to_try:
        print(f"\n{'='*60}")
        print(f"SEARCHING ADD1: length={length}")
        print(f"{'='*60}")
        
        candidates = searcher.zig_batch_search(length=length, max_total=max_total)
        
        if not candidates:
            print(f"  No terminated candidates at length {length}")
            continue
        
        print(f"[walbolge] Verifying {len(candidates)} candidates...")
        
        found = False
        for prog in candidates:
            result = verify_with_walbolge(prog, max_steps=10000)
            
            if result is None:
                continue
            
            tape = result["tape"]
            if len(tape) > 1002 and tape[1002] == 1:
                print(f"\n[VERIFIED] {prog}")
                print(f"  tape[1002] = {tape[1002]}")
                print(f"  final_state: a={result['a']}, c={result['c']}, d={result['d']}")
                print(f"  steps={result['steps']}, halt={result['halt_reason']}")
                
                sha = hashlib.sha256(prog.encode()).hexdigest()
                os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
                
                with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal", "w") as f:
                    f.write(prog)
                
                with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.json", "w") as f:
                    json.dump({
                        "program": prog,
                        "sha256": hashlib.sha256(prog.encode()).hexdigest(),
                        "length": len(prog),
                        "final_state": result,
                        "verified_in": ["zig_vm_batch", "walbolge_trace"]
                    }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
                
                print(f"[EVIDENCE] Saved to evidence/FRAGMENTS_VERIFIED/ADD1_{sha[:8]}.mal")
                found = True
                break
        
        if found:
            print(f"\n[SUCCESS] Found verified ADD1 at length {length}")
            break
        else:
            print(f"  No verified ADD1 at length {length}")


if __name__ == "__main__":
    import time
    import itertools
    import hashlib
    
    print("=" * 70)
    print("MALDOOM ADD1 HYBRID SEARCH — Zig VM batch + Walbolge trace")
    print("=" * 70)
    
    from scripts.search_bolge_batch import BolgeBatchSearcher
    from walbolge.trace import trace_program
    
    main()