#!/usr/bin/env py
"""
EPOCH TRANSPARENCY TEST v2 — State-split (not opcode-split).

Walbolge trace_program(max_steps=100) captures canonical state after exactly 100
executed steps. malbolge-generator executes suffix from that snapshot on fresh VM.
Compares against monolithic 200-step run.

Gate: FULL_STATE_EPOCH_TRANSPARENCY_CROSS_INTERPRETER = PASS/FAIL
"""

from __future__ import annotations

import hashlib
import json
import sys
sys.path.insert(0, r"C:\Development\ISyCo Git\Walbolge")
sys.path.insert(0, r"C:\Development\ISyCo Git\Malbolge-Translator")
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

# ─── Imports ────────────────────────────────────────────────────────────────

try:
    from malbolge import MalbolgeInterpreter, MalbolgeMachine, ProgramGenerator
    _MALBOLGE_AVAILABLE = True
except Exception as e:
    _MALBOLGE_AVAILABLE = False
    _IMPORT_ERROR_GEN = str(e)

try:
    from walbolge.trace import trace_program, TraceEvent, TraceResult
    _WALBOLGE_AVAILABLE = True
except Exception as e:
    _WALBOLGE_AVAILABLE = False
    _IMPORT_ERROR_WAL = str(e)


# ─── State Serialization ────────────────────────────────────────────────────

@dataclass
class FullMachineState:
    """Complete Malbolge machine state for cross-interpreter resume."""
    a: int
    c: int
    d: int
    halted: bool
    tape: List[int]  # full memory[0:59049] (or current length)
    steps: int
    halt_reason: str
    output: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FullMachineState':
        return cls(**data)

    def state_hash(self) -> str:
        """SHA256 of complete state for evidence."""
        data = json.dumps({
            'a': self.a, 'c': self.c, 'd': self.d,
            'halted': self.halted, 'steps': self.steps,
            'halt_reason': self.halt_reason,
            'tape_len': len(self.tape),
            'tape': self.tape
        }, separators=(',', ':')).encode()
        return hashlib.sha256(data).hexdigest()

    def equals(self, other: 'FullMachineState') -> bool:
        """Exact field-by-field comparison."""
        if (self.a != other.a or self.c != other.c or self.d != other.d or
            self.halted != other.halted or self.steps != other.steps or
            self.halt_reason != other.halt_reason):
            return False
        if len(self.tape) != len(other.tape):
            return False
        return self.tape == other.tape

    def tape_prefix_matches(self, other: 'FullMachineState') -> tuple[bool, Optional[int]]:
        """Check if tape content matches up to min length. Returns (matches, first_divergent_index)."""
        min_len = min(len(self.tape), len(other.tape))
        for i in range(min_len):
            if self.tape[i] != other.tape[i]:
                return False, i
        return True, None


def serialize_state_for_malbolge_generator(state: FullMachineState) -> MalbolgeMachine:
    """Convert our FullMachineState to malbolge-generator MalbolgeMachine."""
    machine = MalbolgeMachine()
    machine.a = state.a
    machine.c = state.c
    machine.d = state.d
    machine.halted = state.halted
    machine.tape = state.tape.copy()
    return machine


def deserialize_from_malbolge_generator(machine: MalbolgeMachine, steps: int, halt_reason: str, output: str) -> FullMachineState:
    """Convert malbolge-generator MalbolgeMachine to our FullMachineState."""
    return FullMachineState(
        a=machine.a,
        c=machine.c,
        d=machine.d,
        halted=machine.halted,
        tape=list(machine.tape),
        steps=steps,
        halt_reason=halt_reason,
        output=output
    )


# ─── Walbolge State Capture ────────────────────────────────────────────────

def capture_state_at_step(opcodes: str, target_steps: int, classic: bool = False) -> FullMachineState:
    """
    Use Walbolge trace_program with on_step callback to capture exact machine
    state after exactly target_steps executed instructions.
    """
    if not _WALBOLGE_AVAILABLE:
        raise RuntimeError(f"Walbolge not available: {_IMPORT_ERROR_WAL}")
    
    captured_state: Dict[str, Any] = {}
    final_tape: List[int] = []
    final_a = final_c = final_d = 0
    final_halted = False
    final_halt_reason = ""
    final_output = ""
    
    def on_step(event: TraceEvent, tape: List[int]):
        nonlocal final_a, final_c, final_d, final_halted, final_halt_reason, final_output, final_tape
        # event.step is 0-indexed, so step 99 = 100th instruction
        if event.step == target_steps - 1:
            # This is the LAST step we want - capture POST-instruction state
            final_a = event.a_after
            final_c = event.c + 1  # c was incremented after instruction
            final_d = (event.d + 1) if not classic else ((event.d + 1) if event.d < 59048 else 0)
            final_tape = tape.copy()
            # Note: halt_reason/output captured after loop
    
    result: TraceResult = trace_program(
        opcodes, 
        max_steps=target_steps, 
        classic=classic,
        on_step=on_step,
        max_events=target_steps  # capture all events up to target
    )
    
    final_halted = result.halted
    final_halt_reason = result.halt_reason
    final_output = result.output
    
    # If we halted before target_steps, the last event is at result.steps - 1
    if result.steps < target_steps:
        # Re-run with exact steps to get precise state
        # For now, use what we have
        pass
    
    return FullMachineState(
        a=final_a,
        c=final_c,
        d=final_d,
        halted=final_halted,
        tape=final_tape,
        steps=result.steps,
        halt_reason=final_halt_reason,
        output=final_output
    )


# ─── Malbolge-Generator Execution ──────────────────────────────────────────

def run_monolithic(opcodes: str, max_steps: int) -> FullMachineState:
    """Monolithic run on malbolge-generator."""
    if not _MALBOLGE_AVAILABLE:
        raise RuntimeError(f"malbolge-generator not available: {_IMPORT_ERROR_GEN}")
    
    interp = MalbolgeInterpreter()
    result = interp.execute(opcodes, max_steps=max_steps, capture_machine=True)
    
    return deserialize_from_malbolge_generator(
        result.machine, result.steps, 
        getattr(result, 'halt_reason', ''), 
        result.output
    )


def run_suffix_from_snapshot(snapshot: FullMachineState, suffix_opcodes: str, max_steps: int) -> FullMachineState:
    """Fresh VM: resume from snapshot, execute suffix opcodes."""
    if not _MALBOLGE_AVAILABLE:
        raise RuntimeError(f"malbolge-generator not available: {_IMPORT_ERROR_GEN}")
    
    machine = serialize_state_for_malbolge_generator(snapshot)
    interp = MalbolgeInterpreter()
    result = interp.execute_from_snapshot(machine, suffix_opcodes, max_steps=max_steps, capture_machine=True)
    
    return deserialize_from_malbolge_generator(
        result.machine, result.steps,
        getattr(result, 'halt_reason', ''),
        result.output
    )


# ─── Program Discovery ──────────────────────────────────────────────────────

def find_long_program(min_steps: int = 250, max_attempts: int = 20) -> Optional[str]:
    """Find a generated program that runs at least min_steps before halting."""
    if not _MALBOLGE_AVAILABLE:
        return None
    
    generator = ProgramGenerator()
    
    for length in [20, 30, 40, 50, 60, 80, 100, 120, 150]:
        for attempt in range(max_attempts):
            try:
                text = "X" * length
                result = generator.generate_for_string(text)
                interp = MalbolgeInterpreter()
                test = interp.execute(result.opcodes, max_steps=5000, capture_machine=True)
                if test.steps >= min_steps:
                    print(f"[search] Found: len={len(result.opcodes)} ops, steps={test.steps}, halt={getattr(test, 'halt_reason', '')} for '{text[:30]}...'")
                    return result.opcodes
            except Exception:
                continue
    return None


# ─── Evidence Structure ─────────────────────────────────────────────────────

@dataclass
class EpochTransparencyEvidence:
    program_opcodes: str = ""
    program_length: int = 0
    epoch_boundary_step: int = 0
    max_steps: int = 0
    
    # Monolithic run (200 steps)
    mono: Optional[Dict[str, Any]] = None
    
    # Epoch 1 (first 100 steps via Walbolge)
    epoch1: Optional[Dict[str, Any]] = None
    
    # Epoch 2 (suffix on fresh VM via malbolge-generator)
    epoch2: Optional[Dict[str, Any]] = None
    
    # Chunked combined
    chunked_output: str = ""
    chunked_output_hash: str = ""
    
    # Verification
    output_match: bool = False
    state_match: bool = False
    steps_match: bool = False
    tape_prefix_match: bool = False
    epoch_transparency_pass: bool = False
    first_divergent_field: Optional[str] = None
    first_divergent_memory_index: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─── Core Test ──────────────────────────────────────────────────────────────

def run_epoch_transparency_test(
    opcodes: str,
    epoch_boundary: int = 100,
    total_steps: int = 200,
    max_steps: int = 5000
) -> EpochTransparencyEvidence:
    
    evidence = EpochTransparencyEvidence(
        program_opcodes=opcodes,
        program_length=len(opcodes),
        epoch_boundary_step=epoch_boundary,
        max_steps=max_steps
    )
    
    if not _WALBOLGE_AVAILABLE or not _MALBOLGE_AVAILABLE:
        evidence.error = f"Dependencies missing: walbolge={_WALBOLGE_AVAILABLE}, malbolge={_MALBOLGE_AVAILABLE}"
        return evidence
    
    print(f"[test] Program: {len(opcodes)} opcodes")
    print(f"[test] Epoch boundary: step {epoch_boundary}, total target: {total_steps}")
    
    # ─── 1. Monolithic run (200 steps) ───
    print("[test] Running monolithic (200 steps)...")
    mono_state = run_monolithic(opcodes, max_steps)
    evidence.mono = mono_state.to_dict()
    print(f"[test] Monolithic: steps={mono_state.steps}, output='{mono_state.output}', halt={mono_state.halt_reason}")
    print(f"[test]   Final: a={mono_state.a}, c={mono_state.c}, d={mono_state.d}, tape_len={len(mono_state.tape)}, hash={mono_state.state_hash()[:16]}...")
    
    # ─── 2. Epoch 1: Walbolge trace to exact step boundary ───
    print(f"[test] Running epoch 1 via Walbolge (capture at step {epoch_boundary})...")
    epoch1_state = capture_state_at_step(opcodes, epoch_boundary, classic=False)
    evidence.epoch1 = epoch1_state.to_dict()
    print(f"[test] Epoch 1: steps={epoch1_state.steps}, output='{epoch1_state.output}', halt={epoch1_state.halt_reason}")
    print(f"[test]   Snapshot: a={epoch1_state.a}, c={epoch1_state.c}, d={epoch1_state.d}, tape_len={len(epoch1_state.tape)}, hash={epoch1_state.state_hash()[:16]}...")
    
    # Verify epoch1 actually ran enough steps
    if epoch1_state.steps < epoch_boundary:
        evidence.error = f"Epoch 1 halted early at step {epoch1_state.steps} (target {epoch_boundary})"
        print(f"[test] WARNING: {evidence.error}")
        return evidence
    
    # ─── 3. Epoch 2: malbolge-generator fresh VM from snapshot ───
    # Need suffix opcodes - but we don't have a clean split!
    # The epoch boundary is in EXECUTION STEPS, not opcode position.
    # We need to run the FULL program on fresh VM but starting from the snapshot.
    # execute_from_snapshot expects suffix_opcodes - but we want to continue the SAME program.
    
    # Actually, execute_from_snapshot runs the suffix opcodes from the snapshot state.
    # The "suffix" should be the remaining opcodes from the original program.
    # But we don't know which opcode position corresponds to step 100!
    
    # For now, pass the FULL opcodes - execute_from_snapshot will start from snapshot
    # and execute the opcodes. But the opcode position matters for decoding!
    # The snapshot has c=XXX, so it will start executing at that position.
    # But execute_from_snapshot expects suffix_opcodes starting from position 0...
    
    # Let me check: execute_from_snapshot(snapshot, suffix_opcodes, start_index=prefix_len)
    # The start_index tells it the absolute position for decoding.
    
    # We don't know prefix_len (opcode position at step 100).
    # This is a fundamental issue: step count ≠ opcode position due to jumps.
    
    # WORKAROUND: Run monolithic with trace to find opcode position at step 100
    print("[test] Finding opcode position at step boundary via trace...")
    trace_full = trace_program(opcodes, max_steps=total_steps, classic=False, max_events=total_steps)
    
    if trace_full.steps < epoch_boundary:
        evidence.error = f"Program halts at step {trace_full.steps} < epoch boundary {epoch_boundary}"
        return evidence
    
    # Find the opcode position (c) at step epoch_boundary
    # Events have step=0..N-1, c=c_exec (position of instruction)
    target_event = None
    for ev in trace_full.events:
        if ev.step == epoch_boundary - 1:
            target_event = ev
            break
    
    if target_event is None:
        evidence.error = f"Could not find event at step {epoch_boundary - 1}"
        return evidence
    
    # The NEXT instruction will be at c = target_event.c + 1 (after increment)
    # But wait - the event.c is c_exec (position BEFORE increment)
    # After instruction, c += 1, so next instruction is at c_exec + 1
    prefix_opcode_len = target_event.c + 1
    
    print(f"[test] Opcode position at step {epoch_boundary}: c={target_event.c}, prefix_len={prefix_opcode_len}")
    
    suffix_opcodes = opcodes[prefix_opcode_len:]
    print(f"[test] Suffix opcodes: {len(suffix_opcodes)} (from position {prefix_opcode_len})")
    
    print("[test] Running epoch 2 via malbolge-generator (fresh VM from snapshot)...")
    epoch2_state = run_suffix_from_snapshot(epoch1_state, suffix_opcodes, max_steps)
    evidence.epoch2 = epoch2_state.to_dict()
    print(f"[test] Epoch 2: steps={epoch2_state.steps}, output='{epoch2_state.output}', halt={epoch2_state.halt_reason}")
    print(f"[test]   Final: a={epoch2_state.a}, c={epoch2_state.c}, d={epoch2_state.d}, tape_len={len(epoch2_state.tape)}, hash={epoch2_state.state_hash()[:16]}...")
    
    # ─── 4. Verification ───
    evidence.chunked_output = epoch1_state.output + epoch2_state.output
    evidence.chunked_output_hash = hashlib.sha256(evidence.chunked_output.encode()).hexdigest()
    
    evidence.output_match = (mono_state.output == evidence.chunked_output)
    evidence.steps_match = (mono_state.steps == epoch1_state.steps + epoch2_state.steps)
    evidence.state_match = mono_state.equals(epoch2_state)
    
    # Tape prefix comparison (even if lengths differ)
    tape_prefix_match, first_div_idx = mono_state.tape_prefix_matches(epoch2_state)
    evidence.tape_prefix_match = tape_prefix_match
    evidence.first_divergent_memory_index = first_div_idx
    
    # Find first divergence if any
    if not evidence.state_match:
        # Check registers
        if mono_state.a != epoch2_state.a:
            evidence.first_divergent_field = "a"
        elif mono_state.c != epoch2_state.c:
            evidence.first_divergent_field = "c"
        elif mono_state.d != epoch2_state.d:
            evidence.first_divergent_field = "d"
        elif mono_state.halted != epoch2_state.halted:
            evidence.first_divergent_field = "halted"
        elif mono_state.halt_reason != epoch2_state.halt_reason:
            evidence.first_divergent_field = "halt_reason"
        elif len(mono_state.tape) != len(epoch2_state.tape):
            evidence.first_divergent_field = "tape_len"
            if first_div_idx is not None:
                evidence.first_divergent_field += f" (but tape[{first_div_idx}] diverges first)"
        else:
            # Find first divergent memory cell
            for i, (m1, m2) in enumerate(zip(mono_state.tape, epoch2_state.tape)):
                if m1 != m2:
                    evidence.first_divergent_memory_index = i
                    evidence.first_divergent_field = f"tape[{i}]"
                    break
    
    evidence.epoch_transparency_pass = evidence.output_match and evidence.steps_match and evidence.state_match
    
    print(f"\n[test] RESULTS:")
    print(f"  Output match:     {evidence.output_match}")
    print(f"    mono:  {hashlib.sha256(mono_state.output.encode()).hexdigest()[:16]}... ({len(mono_state.output)} chars)")
    print(f"    chunk: {evidence.chunked_output_hash[:16]}... ({len(evidence.chunked_output)} chars)")
    print(f"  Steps match:      {evidence.steps_match} (mono={mono_state.steps}, epoch1+2={epoch1_state.steps + epoch2_state.steps})")
    print(f"  State match:      {evidence.state_match}")
    print(f"  Tape prefix match: {evidence.tape_prefix_match} (up to min_len={min(len(mono_state.tape), len(epoch2_state.tape))})")
    
    if not evidence.state_match:
        print(f"  FIRST DIVERGENCE: {evidence.first_divergent_field}")
        if evidence.first_divergent_memory_index is not None:
            idx = evidence.first_divergent_memory_index
            print(f"    tape[{idx}]: mono={mono_state.tape[idx]}, chunked={epoch2_state.tape[idx]}")
        print(f"    Registers:")
        print(f"      a: {mono_state.a} vs {epoch2_state.a}")
        print(f"      c: {mono_state.c} vs {epoch2_state.c}")
        print(f"      d: {mono_state.d} vs {epoch2_state.d}")
        print(f"      tape_len: {len(mono_state.tape)} vs {len(epoch2_state.tape)}")
    
    print(f"  FULL_STATE_EPOCH_TRANSPARENCY_CROSS_INTERPRETER: {'PASS' if evidence.epoch_transparency_pass else 'FAIL'}")
    
    return evidence


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("MALDOOM EPOCH TRANSPARENCY TEST v2 — STATE-SPLIT")
    print("Walbolge trace (100 steps) -> malbolge-generator fresh VM resume")
    print("=" * 70)
    
    if not _WALBOLGE_AVAILABLE:
        print(f"ERROR: Walbolge not available: {_IMPORT_ERROR_WAL}")
        sys.exit(1)
    if not _MALBOLGE_AVAILABLE:
        print(f"ERROR: malbolge-generator not available: {_IMPORT_ERROR_GEN}")
        sys.exit(1)
    
    # Find a program that survives at least 250 steps
    print("[test] Searching for long-running program (>=250 steps)...")
    opcodes = find_long_program(min_steps=250)
    
    if opcodes is None:
        print("[test] No long-running program found, trying default...")
        generator = ProgramGenerator()
        result = generator.generate_for_string("Hello World! " * 20)
        opcodes = result.opcodes
        print(f"[test] Using generated program: {len(opcodes)} opcodes")
    
    # Run the test
    evidence = run_epoch_transparency_test(
        opcodes,
        epoch_boundary=100,
        total_steps=200,
        max_steps=5000
    )
    
    # Save evidence
    import os
    os.makedirs("evidence/EPOCH_TRANSPARENCY_V1", exist_ok=True)
    
    evidence_path = "evidence/EPOCH_TRANSPARENCY_V1/evidence.json"
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence.to_dict(), f, indent=2, ensure_ascii=False)
    
    with open("evidence/EPOCH_TRANSPARENCY_V1/program.op", "w") as f:
        f.write(opcodes)
    
    program_sha = hashlib.sha256(opcodes.encode()).hexdigest()
    evidence_json = json.dumps(evidence.to_dict(), ensure_ascii=False)
    evidence_sha = hashlib.sha256(evidence_json.encode()).hexdigest()
    
    with open("evidence/EPOCH_TRANSPARENCY_V1/SHA256SUMS.txt", "w") as f:
        f.write(f"{program_sha}  program.op\n")
        f.write(f"{evidence_sha}  evidence.json\n")
    
    print(f"\n[test] Evidence saved to evidence/EPOCH_TRANSPARENCY_V1/")
    print(f"[test] Program SHA256: {program_sha}")
    print(f"[test] Evidence SHA256: {evidence_sha}")
    
    sys.exit(0 if evidence.epoch_transparency_pass else 1)


if __name__ == "__main__":
    main()