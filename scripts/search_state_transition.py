#!/usr/bin/env py
"""
MALDOOM State Transition Searcher
Busca opcodes que transformen un estado inicial de maquina Malbolge en un estado objetivo.
Usa malbolge-generator internals (_extend_state) con cache para eficiencia.
"""

from __future__ import annotations
import hashlib
import json
import argparse
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Set, Any
from pathlib import Path
from random import Random
from time import perf_counter_ns

try:
    from malbolge import MalbolgeInterpreter, MalbolgeMachine, ProgramGenerator, GenerationConfig
    _GEN_AVAILABLE = True
except Exception as e:
    _GEN_AVAILABLE = False
    _IMPORT_ERROR = str(e)


@dataclass
class StateTransitionSpec:
    name: str
    description: str
    base: int
    input_state: Dict[int, int]
    target_state: Dict[int, int]
    preserved_offsets: List[int] = None
    max_ops: int = 150
    opcode_alphabet: str = "iop*jv<"

    def to_dict(self):
        return asdict(self)


@dataclass
class SearchResult:
    spec: Dict[str, Any]
    found: bool = False
    fragment_opcodes: str = ""
    fragment_length: int = 0
    evaluations: int = 0
    duration_ms: float = 0.0
    final_state: Dict[str, Any] = None
    divergence: Optional[str] = None
    sha256: str = ""

    def to_dict(self):
        return asdict(self)


class StateTransitionSearcher:
    def __init__(self, evidence_dir: str = "evidence/STATE_TRANSITIONS"):
        if not _GEN_AVAILABLE:
            raise RuntimeError(f"malbolge-generator not available: {_IMPORT_ERROR}")

        self.generator = ProgramGenerator()
        self.interpreter = self.generator._interpreter
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def _extend_state(self, prefix_state, suffix: str, cfg: GenerationConfig, stats):
        from malbolge.generator import _PrefixState as GenPrefixState
        gen_prefix = GenPrefixState(
            opcodes=prefix_state.opcodes,
            output=prefix_state.output,
            machine=prefix_state.machine
        )
        return self.generator._extend_state(gen_prefix, suffix, self.interpreter, cfg, stats)

    def _get_or_extend_state(self, prefix_state, suffix: str, cfg: GenerationConfig,
                            cache: dict, stats):
        key = prefix_state.opcodes + suffix
        cached = cache.get(key)
        if cached is not None:
            stats.cache_hits += 1
            return cached, True

        extended = self._extend_state(prefix_state, suffix, cfg, stats)
        if extended.machine is not None:
            cache[key] = extended
        return extended, False

    def create_machine(self, base: int, state: Dict[int, int]) -> MalbolgeMachine:
        machine = MalbolgeMachine()
        machine.a = 0
        machine.c = 0
        machine.d = base
        machine.halted = False

        for offset, value in state.items():
            addr = base + offset
            while len(machine.tape) <= addr:
                machine.tape.append(0)
            machine.tape[addr] = value

        return machine

    def states_match(self, machine: MalbolgeMachine, base: int,
                    target: Dict[int, int], preserved: List[int],
                    input_state: Dict[int, int]) -> Tuple[bool, Optional[str]]:
        for offset, expected in target.items():
            addr = base + offset
            if addr >= len(machine.tape):
                return False, f"target offset {offset} OOB (tape_len={len(machine.tape)})"
            actual = machine.tape[addr]
            if actual != expected:
                return False, f"target[{offset}] = {actual} != {expected}"

        for offset in preserved or []:
            if offset not in target:
                addr = base + offset
                expected = input_state.get(offset, 0)
                if addr >= len(machine.tape):
                    return False, f"preserved offset {offset} OOB"
                actual = machine.tape[addr]
                if actual != expected:
                    return False, f"preserved[{offset}] = {actual} != {expected}"

        return True, None

    def search(self, spec: StateTransitionSpec, max_depth: int = 6) -> SearchResult:
        result = SearchResult(spec=spec.to_dict())
        start_time = perf_counter_ns()

        print(f"[search] {spec.name}: base={spec.base}, input={spec.input_state}, target={spec.target_state}")

        start_machine = self.create_machine(spec.base, spec.input_state)

        from malbolge.generator import _PrefixState as GenPrefixState
        prefix = GenPrefixState(opcodes="", output="", machine=start_machine.copy())

        cfg = GenerationConfig(
            opcode_choices=spec.opcode_alphabet,
            max_search_depth=max_depth,
            random_seed=42
        )

        from malbolge.generator import _GenerationStats
        stats = _GenerationStats()
        cache: Dict[str, GenPrefixState] = {}
        dead: Set[str] = set()

        current_level = [prefix]
        max_total_ops = spec.max_ops

        for length in range(1, max_total_ops + 1):
            next_level = []
            for prefix_state in current_level:
                if len(prefix_state.opcodes) >= max_total_ops:
                    continue

                for op in spec.opcode_alphabet:
                    suffix = op
                    candidate_key = prefix_state.opcodes + suffix

                    if candidate_key in dead:
                        stats.pruned += 1
                        continue

                    try:
                        extended, from_cache = self._get_or_extend_state(
                            prefix_state, suffix, cfg, cache, stats
                        )
                    except Exception:
                        continue

                    if extended.machine is None:
                        continue

                    match, divergence = self.states_match(
                        extended.machine, spec.base,
                        spec.target_state, spec.preserved_offsets, spec.input_state
                    )

                    if match:
                        final_ops = extended.opcodes + "v"
                        result.found = True
                        result.fragment_opcodes = final_ops
                        result.fragment_length = len(final_ops)
                        result.evaluations = stats.evaluations
                        result.duration_ms = (perf_counter_ns() - start_time) / 1_000_000

                        test_machine = start_machine.copy()
                        interp = self.interpreter
                        exec_result = interp.execute_from_snapshot(test_machine, final_ops,
                                                                  max_steps=5000, capture_machine=True)
                        result.final_state = {
                            "a": exec_result.machine.a if exec_result.machine else None,
                            "c": exec_result.machine.c if exec_result.machine else None,
                            "d": exec_result.machine.d if exec_result.machine else None,
                            "halted": exec_result.machine.halted if exec_result.machine else None,
                            "tape_len": len(exec_result.machine.tape) if exec_result.machine else 0,
                            "steps": exec_result.steps,
                            "halt_reason": getattr(exec_result, 'halt_reason', ''),
                        }
                        result.sha256 = hashlib.sha256(final_ops.encode()).hexdigest()
                        print(f"[search] FOUND: {len(final_ops)} ops, evals={stats.evaluations}")
                        return result

                    next_level.append(extended)

                    if len(next_level) > 10000:
                        next_level = next_level[:10000]
                        break

            current_level = next_level
            if not current_level:
                break

            if length % 10 == 0:
                print(f"[search] depth={length}, frontier={len(current_level)}, evals={stats.evaluations}")

        result.duration_ms = (perf_counter_ns() - start_time) / 1_000_000
        result.evaluations = stats.evaluations
        print(f"[search] NOT FOUND after {result.duration_ms:.1f}ms, {stats.evaluations} evals")
        return result

    def save_result(self, result: SearchResult):
        frag_dir = self.evidence_dir / result.spec["name"].upper()
        frag_dir.mkdir(parents=True, exist_ok=True)

        if result.found:
            (frag_dir / "fragment.op").write_text(result.fragment_opcodes)

        (frag_dir / "result.json").write_text(json.dumps(result.to_dict(), indent=2))

        if result.found:
            sha = result.sha256
            (frag_dir / "SHA256SUMS.txt").write_text(f"{sha}  fragment.op\n")

        print(f"[search] Saved to {frag_dir}")


def get_tick_inc_spec() -> StateTransitionSpec:
    return StateTransitionSpec(
        name="tick_inc",
        description="Increment tick counter modulo 59049",
        base=1000,
        input_state={2: 0},
        target_state={2: 1},
        preserved_offsets=[0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        max_ops=120,
        opcode_alphabet="iop*jv<"
    )


def get_rng_next_spec() -> StateTransitionSpec:
    return StateTransitionSpec(
        name="rng_next",
        description="LCG ternario: state = (state * 21 + 7) % 59049",
        base=1000,
        input_state={3: 1},
        target_state={3: 28},
        preserved_offsets=[0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        max_ops=200,
        opcode_alphabet="iop*jv<"
    )


def get_rng_next_spec_2() -> StateTransitionSpec:
    return StateTransitionSpec(
        name="rng_next_2",
        description="LCG ternario: state = (state * 21 + 7) % 59049",
        base=1000,
        input_state={3: 42},
        target_state={3: (42 * 21 + 7) % 59049},
        preserved_offsets=[0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        max_ops=200,
        opcode_alphabet="iop*jv<"
    )


def main():
    parser = argparse.ArgumentParser(description="MALDOOM State Transition Searcher")
    parser.add_argument("fragment", choices=["tick_inc", "rng_next", "rng_next_2", "all"],
                       help="Fragment to search")
    parser.add_argument("--depth", type=int, default=6, help="Max search depth")
    parser.add_argument("--base", type=int, default=1000, help="Base address")
    args = parser.parse_args()

    if not _GEN_AVAILABLE:
        print(f"ERROR: malbolge-generator not available: {_IMPORT_ERROR}")
        sys.exit(1)

    import sys
    sys.path.insert(0, r"C:\Development\ISyCo Git\Malbolge-Translator")
    sys.path.insert(0, r"C:\Development\ISyCo Git\Walbolge")

    searcher = StateTransitionSearcher()

    specs = {
        "tick_inc": get_tick_inc_spec(),
        "rng_next": get_rng_next_spec(),
        "rng_next_2": get_rng_next_spec_2(),
    }

    if args.fragment == "all":
        targets = list(specs.keys())
    else:
        targets = [args.fragment]

    for name in targets:
        spec = specs[name]
        print(f"\n{'='*60}")
        print(f"SEARCHING: {name}")
        print(f"{'='*60}")

        result = searcher.search(spec, max_depth=args.depth)
        searcher.save_result(result)

        if result.found:
            print(f"FOUND: {result.fragment_length} ops, {result.evaluations} evals, {result.duration_ms:.1f}ms")
            print(f"   SHA256: {result.sha256}")
        else:
            print(f"NOT FOUND: {result.evaluations} evals, {result.duration_ms:.1f}ms")


if __name__ == "__main__":
    main()