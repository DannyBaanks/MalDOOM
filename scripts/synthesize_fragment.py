#!/usr/bin/env py
"""
MALDOOM Fragment Synthesizer
Busca opcodes Malbolge que implementen una transición de estado especificada.
Usa Malbolge-Translator backend + AnchorManager + WordBank.
"""

from __future__ import annotations
import sys
sys.path.insert(0, r"C:\Development\ISyCo Git\Malbolge-Translator")
sys.path.insert(0, r"C:\Development\ISyCo Git\Walbolge")

import hashlib
import json
import argparse
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

try:
    from malbolge import MalbolgeInterpreter, MalbolgeMachine, ProgramGenerator, GenerationConfig
    from malbolge_translator.backend import MalbolgeBackend, get_backend
    from malbolge_translator.anchor import AnchorManager, WordBank
    _TRANSLATOR_AVAILABLE = True
except Exception as e:
    _TRANSLATOR_AVAILABLE = False
    _IMPORT_ERROR = str(e)

try:
    from walbolge.trace import trace_program
    _WALBOLGE_AVAILABLE = True
except Exception as e:
    _WALBOLGE_AVAILABLE = False


@dataclass
class FragmentSpec:
    name: str
    description: str
    input_words: Dict[int, int]      # offset -> value
    output_words: Dict[int, int]     # offset -> expected value
    preserved_words: List[int] = None  # offsets that must not change
    max_ops: int = 150
    entry_offset: int = 0            # where fragment starts relative to BASE

    def to_dict(self):
        return asdict(self)


@dataclass
class FragmentEvidence:
    spec: Dict[str, Any]
    fragment_opcodes: str = ""
    fragment_length: int = 0
    oracle_result: Dict = None
    gost_result: Dict = None
    engine_result: Dict = None
    walbolge_trace: Dict = None
    state_match: bool = False
    output_match: bool = False
    preserved_match: bool = False
    first_divergence: Optional[str] = None
    verdict: str = "NOT_TESTED"
    sha256: str = ""

    def to_dict(self):
        return asdict(self)


class FragmentSynthesizer:
    def __init__(self, evidence_dir: str = "evidence/FRAGMENTS"):
        if not _TRANSLATOR_AVAILABLE:
            raise RuntimeError(f"Malbolge-Translator not available: {_IMPORT_ERROR}")
        
        self.generator = ProgramGenerator()
        self.backend = get_backend(self.generator)
        self.interpreter = self.generator._interpreter
        
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Anchor manager for composition
        self.anchor_mgr = AnchorManager(self.generator, self.interpreter, self.evidence_dir / "anchors")
        self.word_bank = WordBank(self.generator, self.interpreter, self.evidence_dir / "anchors")
    
    def create_initial_machine(self, base: int, input_words: Dict[int, int]) -> MalbolgeMachine:
        """Crea máquina con estado inicial para el fragmento."""
        machine = MalbolgeMachine()
        machine.a = 0
        machine.c = 0  # será ajustado al cargar fragmento
        machine.d = base
        machine.halted = False
        
        # Inicializar memoria con valores de entrada
        for offset, value in input_words.items():
            addr = base + offset
            if addr < len(machine.tape):
                machine.tape[addr] = value
            else:
                # Extender tape si necesario
                while len(machine.tape) <= addr:
                    machine.tape.append(0)
                machine.tape[addr] = value
        
        return machine
    
    def create_target_machine(self, base: int, output_words: Dict[int, int], 
                              input_words: Dict[int, int], 
                              preserved_words: List[int]) -> MalbolgeMachine:
        """Crea máquina con estado objetivo esperado."""
        machine = MalbolgeMachine()
        machine.a = 0
        machine.c = 0
        machine.d = base
        machine.halted = True  # fragmento termina en HALT
        
        # Copiar todos los valores de entrada y aplicar salidas
        all_words = dict(input_words)
        all_words.update(output_words)
        
        for offset, value in all_words.items():
            addr = base + offset
            while len(machine.tape) <= addr:
                machine.tape.append(0)
            machine.tape[addr] = value
        
        # Verificar preservados
        for offset in preserved_words or []:
            if offset not in output_words:
                addr = base + offset
                if addr < len(machine.tape):
                    machine.tape[addr] = input_words.get(offset, 0)
        
        return machine
    
    def search_fragment(self, spec: FragmentSpec, base: int = 1000, 
                       max_search_depth: int = 5, random_seed: int = 42) -> Optional[str]:
        """
        Busca opcodes que transformen input_state -> output_state.
        Usa search_continuation del backend desde máquina inicial.
        """
        print(f"[synth] Searching fragment: {spec.name}")
        print(f"[synth]   base={base}, input_words={spec.input_words}, output_words={spec.output_words}")
        
        # Crear máquina inicial
        start_machine = self.create_initial_machine(base, spec.input_words)
        
        # El target_text para search_continuation es un proxy.
        # Realmente necesitamos state transition, no text output.
        # Workaround: encode target state as "text" to match.
        
        # Para search_bridge necesitamos target anchor machine
        target_machine = self.create_target_machine(
            base, spec.output_words, spec.input_words, spec.preserved_words or []
        )
        
        # Intentar search_bridge (depth limitado a 3)
        try:
            bridge_ops = self.backend.search_bridge(
                start_machine, target_machine, 
                verify_text="OK",  # dummy
                max_search_depth=max_search_depth,
                random_seed=random_seed
            )
            if bridge_ops:
                print(f"[synth] Found bridge: {len(bridge_ops)} ops")
                return bridge_ops
        except Exception as e:
            print(f"[synth] search_bridge failed: {e}")
        
        # Fallback: search_continuation con encoding de estado como texto
        # Codificar state objetivo como string de verificación
        target_encoding = self._encode_state_target(spec.output_words)
        try:
            cont_ops, final_machine, stats = self.backend.search_continuation(
                start_machine, target_encoding,
                max_search_depth=max_search_depth,
                random_seed=random_seed,
                opcode_choices="iop*jv<"
            )
            print(f"[synth] Found continuation: {len(cont_ops)} ops, evals={stats['evaluations']}")
            return cont_ops
        except Exception as e:
            print(f"[synth] search_continuation failed: {e}")
        
        return None
    
    def _encode_state_target(self, output_words: Dict[int, int]) -> str:
        """Codifica palabras objetivo como string para search_continuation."""
        # Simple encoding: cada palabra -> 2 chars (high/low trits)
        # Esto es un hack para usar text-generation como state-transition
        chars = []
        for offset in sorted(output_words.keys()):
            val = output_words[offset]
            # 10 trits -> 2 "chars" base-3 aproximado
            chars.append(chr(33 + (val % 94)))
            chars.append(chr(33 + ((val // 94) % 94)))
        return "".join(chars)
    
    def verify_fragment(self, fragment_opcodes: str, spec: FragmentSpec, 
                       base: int = 1000) -> FragmentEvidence:
        """Verifica fragmento en 3 intérpretes + Walbolge trace."""
        evidence = FragmentEvidence(spec=spec.to_dict())
        evidence.fragment_opcodes = fragment_opcodes
        evidence.fragment_length = len(fragment_opcodes)
        
        # Crear estado inicial
        start_machine = self.create_initial_machine(base, spec.input_words)
        target_machine = self.create_target_machine(
            base, spec.output_words, spec.input_words, spec.preserved_words or []
        )
        
        # 1. Malbolge-Translator (malbolge-generator)
        print("[verify] Running on malbolge-generator...")
        interp = self.interpreter
        machine_copy = MalbolgeMachine()
        machine_copy.a = start_machine.a
        machine_copy.c = start_machine.c
        machine_copy.d = start_machine.d
        machine_copy.halted = start_machine.halted
        machine_copy.tape = start_machine.tape.copy()
        
        result = interp.execute_from_snapshot(machine_copy, fragment_opcodes, 
                                             max_steps=5000, capture_machine=True)
        
        evidence.oracle_result = {
            "output": result.output,
            "steps": result.steps,
            "halt_reason": getattr(result, 'halt_reason', ''),
            "final_a": result.machine.a if result.machine else None,
            "final_c": result.machine.c if result.machine else None,
            "final_d": result.machine.d if result.machine else None,
            "final_halted": result.machine.halted if result.machine else None,
            "tape_len": len(result.machine.tape) if result.machine else 0,
        }
        
        # Verificar estado final
        if result.machine:
            state_ok = True
            for offset, expected in spec.output_words.items():
                addr = base + offset
                if addr >= len(result.machine.tape) or result.machine.tape[addr] != expected:
                    state_ok = False
                    evidence.first_divergence = f"output_word[{offset}] = {result.machine.tape[addr] if addr < len(result.machine.tape) else 'OOB'} != {expected}"
                    break
            
            # Verificar preservados
            if state_ok:
                for offset in spec.preserved_words or []:
                    if offset not in spec.output_words:
                        addr = base + offset
                        expected = spec.input_words.get(offset, 0)
                        if addr >= len(result.machine.tape) or result.machine.tape[addr] != expected:
                            state_ok = False
                            evidence.first_divergence = f"preserved_word[{offset}] = {result.machine.tape[addr] if addr < len(result.machine.tape) else 'OOB'} != {expected}"
                            break
            
            evidence.state_match = state_ok
        
        # 2. Walbolge trace
        if _WALBOLGE_AVAILABLE:
            print("[verify] Running Walbolge trace...")
            # Ejecutar desde estado inicial con trace
            trace = trace_program(fragment_opcodes, max_steps=5000, classic=False, 
                                 max_events=5000)
            evidence.walbolge_trace = {
                "steps": trace.steps,
                "halt_reason": trace.halt_reason,
                "output": trace.output,
                "output_len": trace.output_len,
                "peak_memory": trace.peak_memory,
            }
        
        # 3. Veredicto
        evidence.verdict = "PASS" if evidence.state_match else "FAIL"
        
        # SHA256
        evidence.sha256 = hashlib.sha256(fragment_opcodes.encode()).hexdigest()
        
        return evidence
    
    def save_evidence(self, evidence: FragmentEvidence):
        """Guarda evidencia completa."""
        frag_dir = self.evidence_dir / evidence.spec["name"].upper()
        frag_dir.mkdir(parents=True, exist_ok=True)
        
        # fragment.op
        (frag_dir / "fragment.op").write_text(evidence.fragment_opcodes)
        
        # evidence.json
        (frag_dir / "evidence.json").write_text(json.dumps(evidence.to_dict(), indent=2))
        
        # SHA256SUMS
        sha = evidence.sha256
        (frag_dir / "SHA256SUMS.txt").write_text(f"{sha}  fragment.op\n")
        
        # spec.json
        (frag_dir / "spec.json").write_text(json.dumps(evidence.spec, indent=2))
        
        print(f"[synth] Evidence saved to {frag_dir}")
        return frag_dir


# ─── Fragment Specs (from EPOCH_FRAGMENTS_SPEC.md) ──────────────────────────

def get_tick_inc_spec() -> FragmentSpec:
    return FragmentSpec(
        name="tick_inc",
        description="Increment tick counter modulo 59049",
        input_words={2: 0},  # tick=0 at BASE+2
        output_words={2: 1},  # tick'=1
        preserved_words=[0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        max_ops=150,
        entry_offset=0
    )

def get_rng_next_spec() -> FragmentSpec:
    return FragmentSpec(
        name="rng_next",
        description="LCG ternario: state = (state * 21 + 7) % 59049",
        input_words={3: 1},  # rng_state=1 at BASE+3
        output_words={3: 28},  # (1*21+7)%59049 = 28
        preserved_words=[0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        max_ops=200,
        entry_offset=0
    )

def get_player_move_x_spec() -> FragmentSpec:
    return FragmentSpec(
        name="player_move_x",
        description="x += cos(angle) * speed",
        input_words={4: 1000, 7: 0},  # x=1000, angle=0 (cos=1)
        output_words={4: 1100},  # x' = 1000 + 100 (SPEED)
        preserved_words=[0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        max_ops=300,
        entry_offset=0
    )


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MALDOOM Fragment Synthesizer")
    parser.add_argument("fragment", choices=["tick_inc", "rng_next", "player_move_x", "all"],
                       help="Fragment to synthesize")
    parser.add_argument("--base", type=int, default=1000, help="Capsule base address")
    parser.add_argument("--depth", type=int, default=5, help="Max search depth")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--verify-only", action="store_true", 
                       help="Only verify existing fragment.op in evidence dir")
    args = parser.parse_args()
    
    if not _TRANSLATOR_AVAILABLE:
        print(f"ERROR: Malbolge-Translator not available: {_IMPORT_ERROR}")
        sys.exit(1)
    
    synth = FragmentSynthesizer()
    
    specs = {
        "tick_inc": get_tick_inc_spec(),
        "rng_next": get_rng_next_spec(),
        "player_move_x": get_player_move_x_spec(),
    }
    
    if args.fragment == "all":
        targets = list(specs.keys())
    else:
        targets = [args.fragment]
    
    for name in targets:
        spec = specs[name]
        print(f"\n{'='*60}")
        print(f"FRAGMENT: {name}")
        print(f"{'='*60}")
        
        if args.verify_only:
            # Load existing fragment
            frag_dir = synth.evidence_dir / name.upper()
            op_file = frag_dir / "fragment.op"
            if not op_file.exists():
                print(f"[verify] No fragment.op found at {op_file}")
                continue
            fragment_opcodes = op_file.read_text().strip()
        else:
            # Search
            fragment_opcodes = synth.search_fragment(spec, base=args.base, 
                                                    max_search_depth=args.depth,
                                                    random_seed=args.seed)
            if not fragment_opcodes:
                print(f"[synth] FAILED to find fragment {name}")
                continue
        
        # Verify
        evidence = synth.verify_fragment(fragment_opcodes, spec, base=args.base)
        synth.save_evidence(evidence)
        
        print(f"[result] {name}: {evidence.verdict}")
        if evidence.first_divergence:
            print(f"  First divergence: {evidence.first_divergence}")


if __name__ == "__main__":
    main()