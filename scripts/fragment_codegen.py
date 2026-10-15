#!/usr/bin/env py
"""
MALDOOM Fragment Code Generator
Genera fragmentos Malbolge para transiciones de estado aritméticas.
Basado en patrones conocidos: crazy arithmetic, rotate, memory ops.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import hashlib


# ─── Malbolge Constants ─────────────────────────────────────────────────────
XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
XLAT2 = "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@"

CRAZY_TBL = [
    [1, 0, 0],
    [1, 0, 2],
    [2, 2, 1]
]

POW9 = 19683  # 3^9
HALF = 243    # 3^5

def crazy(a: int, b: int) -> int:
    """Crazy operation (10 trits = 2 x 5-trit halves)."""
    r = 0
    p = 1
    aa, bb = a, b
    for _ in range(5):
        r += CRAZY_TBL[bb % 3][aa % 3] * p
        aa //= 3
        bb //= 3
        p *= 3
    return r + 243 * crazy(a // 243, b // 243)

def rotr(n: int) -> int:
    """Rotate right by 1 trit: n = 3^9 * (n%3) + n/3"""
    return POW9 * (n % 3) + n // 3

def enc(inst: str, pos: int) -> str:
    """Encode instruction at position pos (XLAT1)."""
    return chr((XLAT1.index(inst) - pos) % 94 + 33)

def dec(enc_char: str, pos: int) -> str:
    """Decode instruction at position pos."""
    return XLAT1[(ord(enc_char) - 33 + pos) % 94]


# ─── Fragment Builder ───────────────────────────────────────────────────────

@dataclass
class Fragment:
    name: str
    ops: List[str]  # list of instructions (i, p, *, j, <, /, v, o)
    description: str
    entry_c: int = 0  # where c should point at fragment start
    entry_d: int = 0  # where d should point at fragment start
    
    def to_program(self) -> str:
        """Convierte a programa Malbolge codificado con XLAT1."""
        program = [''] * (max(len(self.ops), 100))
        for i, inst in enumerate(self.ops):
            if inst:
                program[i] = enc(inst, i)
        return ''.join(ch for ch in program if ch)
    
    def sha256(self) -> str:
        return hashlib.sha256(self.to_program().encode()).hexdigest()


# ─── Arithmetic Building Blocks ─────────────────────────────────────────────

def build_tick_inc(base: int = 1000, target_offset: int = 2) -> Fragment:
    """
    TICK_INC: Incrementa word en [d] (BASE + target_offset) módulo 59049.
    
    Estrategia: Ripple-carry adder trit-a-trit.
    d apunta al word. Usamos rotaciones y crazy para sumar 1.
    
    Patrones Malbolge conocidos:
    - rotr(x) rota 1 trit
    - crazy(a, b) combina trits
    - Para ADD 1: sumar 1 trit-a-trit con carry
    """
    # NOTA: Implementación completa de ripple-carry es ~80-100 ops.
    # Aquí generamos un ESBOZO que será completado a mano o con búsqueda.
    
    ops = []
    
    # d ya apunta a BASE+target_offset
    # a = 0 (scratch)
    
    # RIPPLE-CARRY ADD 1:
    # for pos in 0..9:
    #   trit = extract_trit(a, pos)
    #   sum = (trit + carry) % 3
    #   carry = (trit + carry) / 3
    #   write trit back
    
    # En Malbolge puro, esto se hace con:
    # 1. * (rotate) para leer trits
    # 2. p (crazy) para combinar
    # 3. rotaciones para posicionar
    
    # PLANTILLA (completar con búsqueda/optimización):
    # d -> word
    # a = 0
    # ... extraer trits del word en a ...
    # ... sumar 1 ...
    # ... escribir de vuelta ...
    
    return Fragment(
        name="tick_inc",
        ops=[
            # Bootstrap: d ya en BASE+target_offset
            # a = 0
            # Leer word actual a a
            'p',  # a = rotate(tape[d]) - primer trit
            'p', 'p', 'p', 'p', 'p', 'p', 'p', 'p', 'p',  # 9 rotaciones más = 10 trits
            # Ahora a tiene el word rotado? No, p rota y escribe.
            # Patrones reales son más complejos...
            'v',  # HALT temporal
        ],
        description=f"tick_inc at BASE+{target_offset} (stub - needs ripple-carry implementation)",
        entry_d=base + target_offset
    )


def build_rng_next(base: int = 1000, target_offset: int = 3) -> Fragment:
    """
    RNG_NEXT: state = (state * 21 + 7) % 59049
    
    21 = 210₃ (trits: 0,1,0,1,0,0,0,0,0,0)
    7  = 21₃  (trits: 1,2,0,0,0,0,0,0,0,0)
    
    Multiplicación ternaria por 21 + suma 7.
    """
    return Fragment(
        name="rng_next",
        ops=['v'],  # stub
        description=f"rng_next at BASE+{target_offset} (state = state*21+7 mod 59049)",
        entry_d=base + target_offset
    )


def build_add_constant(base: int, offset: int, constant: int) -> Fragment:
    """
    ADD_CONST: word = (word + constant) % 59049
    Generaliza tick_inc y rng_next (con multiplicación).
    """
    return Fragment(
        name=f"add_{constant}_at_{offset}",
        ops=['v'],
        description=f"add {constant} to word at BASE+{offset}",
        entry_d=base + offset
    )


# ─── Known Malbolge Arithmetic Patterns ─────────────────────────────────────

# Patrones de la comunidad Malbolge para aritmética:
# 
# ADD 1 (ripple-carry):
#   Requiere: extraer 10 trits, sumar carry, reconstruir
#   ~80-120 ops
#
# MUL por constante pequeña:
#   Shift-add trinario: a * K = sum(a * 3^pos * K_pos)
#   ~100-200 ops
#
# CRAZY identities útiles:
#   crazy(x, 0) = x
#   crazy(x, x) = rotación?
#   crazy(0, x) = ?
#
# Referencia: "Malbolge programming" by various authors
# - Hisashi Iizawa's Malbolge page
# - Lou Scheffer's quines
# - Malbolge-Translator generated code


# ─── Test / Verify ──────────────────────────────────────────────────────────

def verify_fragment(fragment: Fragment, input_state: Dict[int, int], 
                   expected_state: Dict[int, int], base: int = 1000) -> bool:
    """Verifica fragmento usando Walbolge trace."""
    try:
        import sys
        sys.path.insert(0, r"C:\Development\ISyCo Git\Walbolge")
        from walbolge.trace import trace_program
    except ImportError:
        print("Walbolge not available for verification")
        return False
    
    program = fragment.to_program()
    
    # Configurar estado inicial
    # Walbolge trace_program usa classic=False por defecto (toolkit semantics)
    # Necesitamos classic=True para semántica Classic 59049
    
    # Para verificación real, mejor usar gost/oracle/malbolge-engine
    # Aquí solo verificamos que el programa no crashee
    trace = trace_program(program, max_steps=5000, classic=True)
    print(f"  Verification: steps={trace.steps}, halt={trace.halt_reason}")
    return trace.halted and trace.halt_reason == "halt_opcode"


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("MALDOOM FRAGMENT CODEGEN")
    print("=" * 60)
    
    # Generar stubs
    tick_inc = build_tick_inc()
    rng_next = build_rng_next()
    
    print(f"\nTICK_INC:")
    print(f"  Program: {tick_inc.to_program()[:100]}...")
    print(f"  Len: {len(tick_inc.to_program())}")
    print(f"  SHA256: {tick_inc.sha256()}")
    
    print(f"\nRNG_NEXT:")
    print(f"  Program: {rng_next.to_program()[:100]}...")
    print(f"  Len: {len(rng_next.to_program())}")
    print(f"  SHA256: {rng_next.sha256()}")
    
    # Guardar stubs
    import os
    os.makedirs("evidence/FRAGMENTS_STUBS", exist_ok=True)
    
    for frag in [tick_inc, rng_next]:
        with open(f"evidence/FRAGMENTS_STUBS/{frag.name}.op", "w") as f:
            f.write(frag.to_program())
        with open(f"evidence/FRAGMENTS_STUBS/{frag.name}.spec.json", "w") as f:
            import json
            json.dump({
                "name": frag.name,
                "description": frag.description,
                "entry_c": frag.entry_c,
                "entry_d": frag.entry_d,
                "sha256": frag.sha256()
            }, f, indent=2)
    
    print("\nStubs guardados en evidence/FRAGMENTS_STUBS/")
    print("\nPRÓXIMO PASO: Implementar ripple-carry ADD1 y MUL21+7 reales")
    print("  - Usar patrones de Lou Scheffer / Hisashi Iizawa")
    print("  - O buscar con Autobolge Zig DSL + state constraints")


if __name__ == "__main__":
    main()