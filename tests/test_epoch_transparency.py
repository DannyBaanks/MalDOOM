#!/usr/bin/env py
"""
EPOCH TRANSPARENCY TEST — Prueba reina para MALDOOM epochs.

Verifica que dividir una ejecución Malbolge en dos epochs (procesos separados)
produce idéntico estado final que la ejecución monolítica.

S0 --epoch1(prefix opcodes)--> A1 --epoch2(suffix opcodes)--> A2
    \_____________________________________________/
                    monolítico (full opcodes)

Exige: A2_mono == A2_chunked (estado completo: a, c, d, tape, steps, output, halted)
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional

try:
    from malbolge import MalbolgeInterpreter, MalbolgeMachine, ProgramGenerator
    _MALBOLGE_AVAILABLE = True
except Exception as e:
    _MALBOLGE_AVAILABLE = False
    _IMPORT_ERROR = str(e)

# ─── Machine State Serialization ────────────────────────────────────────────

def machine_state_hash(machine: MalbolgeMachine) -> str:
    """SHA256 del estado completo de la máquina (tape + registros)."""
    tape_list = list(machine.tape) if hasattr(machine.tape, '__iter__') else []
    state_data = json.dumps({
        'a': machine.a,
        'c': machine.c,
        'd': machine.d,
        'halted': getattr(machine, 'halted', False),
        'tape_len': len(tape_list),
        'tape': tape_list
    }, separators=(',', ':')).encode()
    return hashlib.sha256(state_data).hexdigest()


def machine_state_eq(m1: MalbolgeMachine, m2: MalbolgeMachine) -> bool:
    """Compara estado completo de dos máquinas."""
    if m1.a != m2.a or m1.c != m2.c or m1.d != m2.d:
        return False
    if getattr(m1, 'halted', False) != getattr(m2, 'halted', False):
        return False
    if len(m1.tape) != len(m2.tape):
        return False
    return list(m1.tape) == list(m2.tape)


# ─── Evidence Structure ─────────────────────────────────────────────────────

@dataclass
class EpochTransparencyEvidence:
    program_opcodes: str = ""
    program_length: int = 0
    split_at: int = 0
    
    # Monolithic run final state
    mono_output: str = ""
    mono_output_hash: str = ""
    mono_steps: int = 0
    mono_halt_reason: str = ""
    mono_final_a: int = 0
    mono_final_c: int = 0
    mono_final_d: int = 0
    mono_final_halted: bool = False
    mono_final_tape_len: int = 0
    mono_final_tape_hash: str = ""
    
    # Epoch 1 (prefix) state
    epoch1_output: str = ""
    epoch1_steps: int = 0
    epoch1_halt_reason: str = ""
    epoch1_a: int = 0
    epoch1_c: int = 0
    epoch1_d: int = 0
    epoch1_halted: bool = False
    epoch1_tape_len: int = 0
    epoch1_tape_hash: str = ""
    
    # Epoch 2 (suffix on fresh VM) final state
    epoch2_output: str = ""
    epoch2_steps: int = 0
    epoch2_halt_reason: str = ""
    epoch2_final_a: int = 0
    epoch2_final_c: int = 0
    epoch2_final_d: int = 0
    epoch2_final_halted: bool = False
    epoch2_final_tape_len: int = 0
    epoch2_final_tape_hash: str = ""
    
    # Concatenated chunked output
    chunked_output: str = ""
    chunked_output_hash: str = ""
    
    # Verification
    output_match: bool = False
    steps_match: bool = False
    state_match: bool = False
    epoch_transparency_pass: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Core Test Logic ────────────────────────────────────────────────────────

def split_opcodes(opcodes: str, split_at: Optional[int] = None) -> tuple[str, str]:
    """Split opcode stream at midpoint (or given position)."""
    if not opcodes:
        return "", ""
    split = split_at if split_at is not None else len(opcodes) // 2
    if split <= 0 or split >= len(opcodes):
        raise ValueError("split_at must be strictly inside the opcode stream")
    return opcodes[:split], opcodes[split:]


def run_epoch_transparency_test(
    opcodes: str,
    split_at: Optional[int] = None,
    max_steps: int = 5_000_000
) -> EpochTransparencyEvidence:
    """Ejecuta la prueba reina de transparencia de epochs (opcode-split)."""
    
    evidence = EpochTransparencyEvidence(
        program_opcodes=opcodes,
        program_length=len(opcodes)
    )
    
    if not _MALBOLGE_AVAILABLE:
        evidence.error = f"malbolge-generator not available: {_IMPORT_ERROR}"
        return evidence
    
    prefix, suffix = split_opcodes(opcodes, split_at)
    evidence.split_at = len(prefix)
    
    print(f"[test] Program: {len(opcodes)} opcodes, split at {evidence.split_at}")
    print(f"[test] Prefix: {len(prefix)} ops, Suffix: {len(suffix)} ops")
    
    # ─── Monolithic run ───
    print("[test] Running monolithic...")
    full = MalbolgeInterpreter().execute(opcodes, max_steps=max_steps, capture_machine=True)
    
    evidence.mono_output = full.output
    evidence.mono_output_hash = hashlib.sha256(full.output.encode()).hexdigest()
    evidence.mono_steps = full.steps
    evidence.mono_halt_reason = getattr(full, "halt_reason", "")
    
    if full.machine:
        evidence.mono_final_a = full.machine.a
        evidence.mono_final_c = full.machine.c
        evidence.mono_final_d = full.machine.d
        evidence.mono_final_halted = full.machine.halted
        evidence.mono_final_tape_len = len(full.machine.tape)
        evidence.mono_final_tape_hash = machine_state_hash(full.machine)
    
    print(f"[test] Monolithic: steps={evidence.mono_steps}, output_len={len(evidence.mono_output)}, halt={evidence.mono_halt_reason}")
    print(f"[test]   Final state: a={evidence.mono_final_a}, c={evidence.mono_final_c}, d={evidence.mono_final_d}, tape_len={evidence.mono_final_tape_len}")
    
    # ─── Epoch 1: Prefix run → snapshot ───
    print("[test] Running epoch 1 (prefix)...")
    pref = MalbolgeInterpreter().execute(prefix, max_steps=max_steps, capture_machine=True)
    snapshot = pref.machine
    
    if snapshot is None:
        evidence.error = "Epoch 1 failed to capture machine snapshot"
        return evidence
    
    evidence.epoch1_output = pref.output
    evidence.epoch1_steps = pref.steps
    evidence.epoch1_halt_reason = getattr(pref, "halt_reason", "")
    evidence.epoch1_a = snapshot.a
    evidence.epoch1_c = snapshot.c
    evidence.epoch1_d = snapshot.d
    evidence.epoch1_halted = snapshot.halted
    evidence.epoch1_tape_len = len(snapshot.tape)
    evidence.epoch1_tape_hash = machine_state_hash(snapshot)
    
    print(f"[test] Epoch 1: steps={evidence.epoch1_steps}, output_len={len(evidence.epoch1_output)}, halt={evidence.epoch1_halt_reason}")
    print(f"[test]   Snapshot state: a={evidence.epoch1_a}, c={evidence.epoch1_c}, d={evidence.epoch1_d}, tape_len={evidence.epoch1_tape_len}")
    
    # ─── Epoch 2: Fresh VM resume suffix from snapshot ───
    print("[test] Running epoch 2 (suffix on fresh VM)...")
    fresh = MalbolgeInterpreter()
    suff = fresh.execute_from_snapshot(snapshot, suffix, max_steps=max_steps, capture_machine=True)
    
    evidence.epoch2_output = suff.output
    evidence.epoch2_steps = suff.steps
    evidence.epoch2_halt_reason = getattr(suff, "halt_reason", "")
    
    if suff.machine:
        evidence.epoch2_final_a = suff.machine.a
        evidence.epoch2_final_c = suff.machine.c
        evidence.epoch2_final_d = suff.machine.d
        evidence.epoch2_final_halted = suff.machine.halted
        evidence.epoch2_final_tape_len = len(suff.machine.tape)
        evidence.epoch2_final_tape_hash = machine_state_hash(suff.machine)
    
    # Concatenated output
    evidence.chunked_output = evidence.epoch1_output + evidence.epoch2_output
    evidence.chunked_output_hash = hashlib.sha256(evidence.chunked_output.encode()).hexdigest()
    
    print(f"[test] Epoch 2: steps={evidence.epoch2_steps}, output_len={len(evidence.epoch2_output)}, halt={evidence.epoch2_halt_reason}")
    if suff.machine:
        print(f"[test]   Final state: a={evidence.epoch2_final_a}, c={evidence.epoch2_final_c}, d={evidence.epoch2_final_d}, tape_len={evidence.epoch2_final_tape_len}")
    
    # ─── Verification ───
    evidence.output_match = (evidence.mono_output == evidence.chunked_output)
    evidence.steps_match = (evidence.mono_steps == evidence.epoch1_steps + evidence.epoch2_steps)
    
    if full.machine and suff.machine:
        evidence.state_match = machine_state_eq(full.machine, suff.machine)
    
    evidence.epoch_transparency_pass = evidence.output_match and evidence.steps_match and evidence.state_match
    
    print(f"\n[test] RESULTS:")
    print(f"  Output match:     {evidence.output_match}")
    print(f"    mono:  {evidence.mono_output_hash[:16]}... ({len(evidence.mono_output)} chars)")
    print(f"    chunk: {evidence.chunked_output_hash[:16]}... ({len(evidence.chunked_output)} chars)")
    print(f"  Steps match:      {evidence.steps_match} (mono={evidence.mono_steps}, epoch1+2={evidence.epoch1_steps + evidence.epoch2_steps})")
    print(f"  State match:      {evidence.state_match}")
    if full.machine and suff.machine:
        print(f"    a: {evidence.mono_final_a} vs {evidence.epoch2_final_a}")
        print(f"    c: {evidence.mono_final_c} vs {evidence.epoch2_final_c}")
        print(f"    d: {evidence.mono_final_d} vs {evidence.epoch2_final_d}")
        print(f"    tape_len: {evidence.mono_final_tape_len} vs {evidence.epoch2_final_tape_len}")
        print(f"    tape_hash: {evidence.mono_final_tape_hash[:16]}... vs {evidence.epoch2_final_tape_hash[:16]}...")
    print(f"  EPOCH_TRANSPARENCY: {'PASS' if evidence.epoch_transparency_pass else 'FAIL'}")
    
    return evidence


# ─── Program Discovery ──────────────────────────────────────────────────────

def find_suitable_program(min_ops: int = 100, max_ops: int = 1000) -> Optional[str]:
    """Busca un programa generado con longitud de opcodes adecuada."""
    if not _MALBOLGE_AVAILABLE:
        return None
    
    generator = ProgramGenerator()
    
    # Try various string lengths to get programs in the right opcode range
    for length in [5, 8, 10, 12, 15, 18, 20, 25, 30, 35, 40]:
        for attempt in range(3):
            try:
                text = "X" * length
                result = generator.generate_for_string(text)
                if min_ops <= len(result.opcodes) <= max_ops:
                    print(f"[search] Found: '{text}' -> {len(result.opcodes)} ops, {result.opcodes[:50]}...")
                    return result.opcodes
            except Exception:
                continue
    return None


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("MALDOOM EPOCH TRANSPARENCY TEST (opcode-split)")
    print("=" * 60)
    
    if not _MALBOLGE_AVAILABLE:
        print(f"ERROR: malbolge-generator not available: {_IMPORT_ERROR}")
        sys.exit(1)
    
    # Find a suitable program
    print("[test] Searching for suitable program (100-1000 ops)...")
    opcodes = find_suitable_program()
    
    if opcodes is None:
        print("[test] No suitable program found, using default generated")
        generator = ProgramGenerator()
        result = generator.generate_for_string("Hello World! " * 8)
        opcodes = result.opcodes
        print(f"[test] Using generated program: {len(opcodes)} opcodes")
    
    # Run the test
    evidence = run_epoch_transparency_test(opcodes, max_steps=5_000_000)
    
    # Save evidence
    import os
    os.makedirs("evidence/EPOCH_TRANSPARENCY_V0", exist_ok=True)
    
    evidence_path = "evidence/EPOCH_TRANSPARENCY_V0/evidence.json"
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence.to_dict(), f, indent=2, ensure_ascii=False)
    
    # Also save program
    with open("evidence/EPOCH_TRANSPARENCY_V0/program.op", "w") as f:
        f.write(opcodes)
    
    # SHA256 of artifacts
    program_sha = hashlib.sha256(opcodes.encode()).hexdigest()
    evidence_json = json.dumps(evidence.to_dict(), ensure_ascii=False)
    evidence_sha = hashlib.sha256(evidence_json.encode()).hexdigest()
    
    with open("evidence/EPOCH_TRANSPARENCY_V0/SHA256SUMS.txt", "w") as f:
        f.write(f"{program_sha}  program.op\n")
        f.write(f"{evidence_sha}  evidence.json\n")
    
    print(f"\n[test] Evidence saved to evidence/EPOCH_TRANSPARENCY_V0/")
    print(f"[test] Program SHA256: {program_sha}")
    print(f"[test] Evidence SHA256: {evidence_sha}")
    
    sys.exit(0 if evidence.epoch_transparency_pass else 1)


if __name__ == "__main__":
    main()