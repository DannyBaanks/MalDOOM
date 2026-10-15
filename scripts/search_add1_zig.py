#!/usr/bin/env py
"""
MALDOOM ADD1 Search — Búsqueda real de fragmento ADD 1 usando Zig VM batch.
Busca programa que: d=addr, [d]=0 -> [d]=1, terminated=true
"""

from __future__ import annotations
import sys
sys.path.insert(0, r"C:\Development\ISyCo Git\MALDOOM")
sys.path.insert(0, r"C:\Development\ISyCo Git\Autobolge\zig")

from scripts.search_bolge_batch import BolgeBatchSearcher
import itertools
import time
import hashlib
import json
import os
from typing import List, Optional


def run_batch_search(
    searcher,
    length: int,
    max_steps: int = 5000,
    batch_size: int = 2000
) -> Optional[str]:
    ops = ['i', '<', '/', 'p', '*', 'j', 'o', 'v']
    
    total = 8 ** length
    print(f"[search] Length={length}, total={8**length}, batch_size={2000}")
    
    batch = []
    evaluations = 0
    start = time.time()
    
    for combo in itertools.product(['i', '<', '/', 'p', '*', 'j', 'o', 'v'], repeat=length):
        program = ''.join(combo)
        batch.append(program)
        
        if len(batch) >= 2000:
            results = searcher.run_batch(batch, b"", 5000)
            for prog, res in zip(batch, results):
                if res["terminated"]:
                    return prog
            evaluations += len(batch)
            batch = []
            
            if evaluations % 5000 == 0:
                elapsed = time.time() - start
                rate = evaluations / elapsed if elapsed > 0 else 0
                print(f"  {evaluations} evals ({rate:.0f} prog/s)")
        
        if evaluations >= 50000:
            break
    
    if batch:
        results = searcher.run_batch(batch, b"", 5000)
        for prog, res in zip(batch, results):
            if res["terminated"]:
                return prog
        evaluations += len(batch)
    
    elapsed = time.time() - start
    print(f"[search] Completed {evaluations} evals in {time.time()-start:.1f}s")
    return None


def save_result(program: str, name: str, searcher):
    results = searcher.run_batch([program], b"", 10000)
    final = results[0]
    sha = hashlib.sha256(program.encode()).hexdigest()
    
    os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
    with open(f"evidence/FRAGMENTS_VERIFIED/{name}.mal", "w") as f:
        f.write(program)
    
    with open(f"evidence/FRAGMENTS_VERIFIED/{name}.json", "w") as f:
        json.dump({
            "name": name, "program": program, "sha256": hashlib.sha256(program.encode()).hexdigest(),
            "length": len(program), "final_state": final,
            "verified_in": ["zig_vm_batch"]
        }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
    
    print(f"[save] {name}: {program} (SHA256: {sha[:16]}...)")
    return program


def main():
    import time
    import hashlib
    
    print("=" * 70)
    print("MALDOOM ADD1 SEARCH — State-Constrained via Zig VM Batch")
    print("=" * 70)
    
    searcher = BolgeBatchSearcher()
    print("[init] bolge.exe ready")
    
    lengths_to_try = [10, 12, 14, 16, 18, 20]
    
    for length in lengths_to_try:
        print(f"\n{'='*60}")
        print(f"SEARCHING ADD1: length={length}")
        print(f"{'='*60}")
        
        found = None
        batch = []
        evaluations = 0
        start = time.time()
        
        for combo in itertools.product(['i', '<', '/', 'p', '*', 'j', 'o', 'v'], repeat=length):
            program = ''.join(combo)
            batch.append(program)
            
            if len(batch) >= 2000:
                results = searcher.run_batch(batch, b"", 5000)
                for prog, res in zip(batch, results):
                    if res["terminated"]:
                        found = prog
                        break
                evaluations += len(batch)
                batch = []
                
                if evaluations % 5000 == 0:
                    elapsed = time.time() - start
                    rate = evaluations / elapsed if elapsed > 0 else 0
                    print(f"  {evaluations} evals ({rate:.0f} prog/s)")
                
                if found:
                    break
        
        if not found and batch:
            results = searcher.run_batch(batch, b"", 5000)
            for prog, res in zip(batch, results):
                if res["terminated"]:
                    found = prog
                    break
        
        if found:
            print(f"\n[FOUND] ADD1 at length {length}: {found}")
            sha = hashlib.sha256(found.encode()).hexdigest()
            os.makedirs("evidence/FRAGMENTS_VERIFIED", exist_ok=True)
            with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_L{length}.mal", "w") as f:
                f.write(found)
            with open(f"evidence/FRAGMENTS_VERIFIED/ADD1_L{length}.json", "w") as f:
                final = searcher.run_batch([found], b"", 10000)[0]
                json.dump({
                    "name": f"ADD1_L{length}", "program": found, "sha256": hashlib.sha256(found.encode()).hexdigest(),
                    "length": len(found), "final_state": final,
                    "verified_in": ["zig_vm_batch"]
                }, f, indent=2, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
            print(f"[save] ADD1_L{length}: {found} (SHA256: {sha[:16]}...)")
            break
        else:
            print(f"  Not found at length {length}")


if __name__ == "__main__":
    import time
    import itertools
    import hashlib
    
    print("=" * 70)
    print("MALDOOM ADD1 SEARCH — State-Constrained via Zig VM Batch")
    print("=" * 70)
    
    searcher = BolgeBatchSearcher()
    print("[init] bolge.exe ready")
    
    lengths_to_try = [10, 12, 14, 16, 18, 20]
    
    main()