# MALDOOM Epoch Transition — Fragment Specs

Cada fragmento es una transición de estado atómica y verificable independientemente.
Composición final: `tick_inc → rng_next → player_move_x → player_move_y → checksum → HALT`

---

## Memoria Layout (Capsule Base = `BASE`)

| Word | Offset | Nombre | Descripción |
|---|---|---|---|
| 0 | BASE+0 | MAGIC | 0xDEAD (57005) |
| 1 | BASE+1 | VERSION | 1 |
| 2 | BASE+2 | **TICK** | 0..59048 |
| 3 | BASE+3 | **RNG_STATE** | 0..59048 |
| 4 | BASE+4 | PLAYER_X | 0..59048 |
| 5 | BASE+5 | PLAYER_Y | 0..59048 |
| 6 | BASE+6 | PLAYER_Z | 0..59048 |
| 7 | BASE+7 | PLAYER_ANGLE | 0..59048 (0..65535 mapped) |
| 8 | BASE+8 | HEALTH | 0..200 |
| 9 | BASE+9 | ARMOR | 0..200 |
| 10 | BASE+10 | AMMO_SHELLS | 0..400 |
| 11 | BASE+11 | AMMO_CELLS | 0..600 |
| 12 | BASE+12 | AMMO_ROCKETS | 0..50 |
| 13 | BASE+13 | WEAPONS_BITMASK | bits 0-8 |
| 14 | BASE+14 | KEYS_BITMASK | bits 0-5 |
| 15 | BASE+15 | SELECTED_WEAPON | 0..7 |
| 16 | BASE+16 | PENDING_WEAPON | 0..7 |
| 17 | BASE+17 | PLAYER_FLAGS | bitfield |
| 18 | BASE+18 | ATTACK_STATE | frames |
| ... | ... | WORLD | variable |
| 378 | BASE+378 | CHECKSUM | crazy fold |

**Total: 379 words (BASE+0 .. BASE+378)**

---

## FRAGMENT 1: TICK_INC

```
NAME: tick_inc
DESCRIPTION: Increment tick counter modulo 59049
ADDRESS: BASE+2
INPUT_STATE:
  d = BASE+2
  tape[d] = tick (0..59048)
  a = 0 (scratch)
OPERATION:
  tick' = (tick + 1) % 59049
OUTPUT_STATE:
  tape[d] = tick'
  a = 0
  d = BASE+2
  c = next_fragment_entry
SIDE_EFFECTS: none
VERIFICATION:
  - For all tick in [0, 59047]: output = tick + 1
  - For tick = 59048: output = 0
  - Other memory unchanged
MAX_OPS: 150
```

**Implementación sugerida:** Ripple-carry trit adder con constante 1
- Extraer cada trit (divide by 3^pos, mod 3)
- Sumar carry (inicialmente 1)
- Reconstruir palabra
- ≈100-120 ops

---

## FRAGMENT 2: RNG_NEXT

```
NAME: rng_next
DESCRIPTION: LCG ternario: state = (state * 21 + 7) % 59049
ADDRESS: BASE+3
INPUT_STATE:
  d = BASE+3
  tape[d] = rng_state (0..59048)
  a = 0 (scratch)
OPERATION:
  rng' = (rng_state * 21 + 7) % 59049
OUTPUT_STATE:
  tape[d] = rng'
  a = 0
  d = BASE+3
  c = next_fragment_entry
SIDE_EFFECTS: none
VERIFICATION:
  - rng' = (rng * 21 + 7) % 59049 for all rng in 0..59048
  - Period = 59049 (full cycle)
MAX_OPS: 200
```

**Implementación sugerida:** Multiplicación ternaria por 21 + suma 7
- 21 = 210₃ (trits: 0,1,0,1,0... wait 21 = 2*3^2 + 1*3^1 + 0*3^0 = 210₃)
- Multiplicar por 21: shift-add trinario
- Sumar 7 (021₃)
- ≈150-200 ops

---

## FRAGMENT 3: PLAYER_MOVE_X

```
NAME: player_move_x
DESCRIPTION: x += cos(angle) * speed
ADDRESS: BASE+4 (PLAYER_X), BASE+7 (PLAYER_ANGLE)
INPUT_STATE:
  d = BASE+4 (x) initially, then BASE+7 (angle)
  tape[BASE+4] = x (0..59048)
  tape[BASE+7] = angle (0..59048, maps to 0..65535)
  a = 0
CONSTANTS:
  SPEED = 100 (trits) ≈ 0.0017 world units per tick
  COS_TABLE: 256 entries precomputed (or compute via CORDIC)
OPERATION:
  angle_deg = angle * 65536 / 59049
  cos_val = COS_TABLE[angle_deg >> 8]  # 8-bit index
  delta = (cos_val * SPEED) >> 16      # fixed-point
  x' = (x + delta) % 59049
OUTPUT_STATE:
  tape[BASE+4] = x'
  a = 0
  d = BASE+4
  c = next_fragment_entry
SIDE_EFFECTS: reads BASE+7
VERIFICATION:
  - For angle=0 (cos=1): x' = (x + SPEED) % 59049
  - For angle=16384 (cos=0): x' = x
  - For angle=32768 (cos=-1): x' = (x - SPEED) % 59049
MAX_OPS: 300
```

**Nota:** Coseno precomputado en tabla en memoria (words 400-655). O CORDIC iterativo (más ops, menos memoria).

---

## FRAGMENT 4: PLAYER_MOVE_Y

```
NAME: player_move_y
DESCRIPTION: y += sin(angle) * speed
ADDRESS: BASE+5 (PLAYER_Y), BASE+7 (PLAYER_ANGLE)
INPUT_STATE:
  d = BASE+5 (y) initially, then BASE+7 (angle)
  tape[BASE+5] = y (0..59048)
  tape[BASE+7] = angle (same as move_x)
  a = 0
OPERATION:
  angle_deg = angle * 65536 / 59049
  sin_val = SIN_TABLE[angle_deg >> 8]  # or COS_TABLE[(angle+16384)%65536]
  delta = (sin_val * SPEED) >> 16
  y' = (y + delta) % 59049
OUTPUT_STATE:
  tape[BASE+5] = y'
  a = 0
  d = BASE+5
  c = next_fragment_entry
SIDE_EFFECTS: reads BASE+7
VERIFICATION:
  - angle=0 (sin=0): y' = y
  - angle=16384 (sin=1): y' = (y + SPEED) % 59049
  - angle=32768 (sin=0): y' = y
  - angle=49152 (sin=-1): y' = (y - SPEED) % 59049
MAX_OPS: 300
```

**Optimización:** Reutilizar `angle_deg` calculado en move_x si se fusionan.

---

## FRAGMENT 5: CHECKSUM_RECALC

```
NAME: checksum_recalc
DESCRIPTION: Recompute crazy-fold checksum over all 378 data words
ADDRESS: BASE+378 (CHECKSUM)
INPUT_STATE:
  d = BASE (start of capsule)
  a = 0 (accumulator)
  c = loop_counter (scratch)
  Tape[BASE..BASE+377] = valid capsule data
OPERATION:
  checksum = 0
  for i in 0..377:
    checksum = crazy(checksum, tape[BASE+i])
  tape[BASE+378] = checksum
OUTPUT_STATE:
  tape[BASE+378] = checksum
  a = 0
  d = BASE+378
  c = HALT_entry
SIDE_EFFECTS: reads entire capsule
VERIFICATION:
  - For known capsule: checksum matches precomputed
  - Changing any word changes checksum
  - crazy operation: per trit CRAZY_TBL
MAX_OPS: 500 (loop 378 iterations)
```

**Implementación:** Loop con contador en `a` o memoria scratch
- `crazy` op: `p` instruction (crazy_write) con `a` y `tape[d]`
- Iterar 378 veces
- ≈500-800 ops

---

## FRAGMENT 6: HALT

```
NAME: halt
DESCRIPTION: Terminate epoch cleanly
ADDRESS: after checksum
INPUT_STATE:
  a = 0
  d = BASE+378
  tape[BASE..BASE+378] = valid capsule with correct checksum
OPERATION:
  Execute 'v' opcode (halt)
OUTPUT_STATE:
  halted = true
  halt_reason = "halt_opcode"
  All registers preserved for resume
MAX_OPS: 1
```

---

## COMPOSICIÓN SECUENCIAL

```
EPOCH_HANDLER:
  BASE = d (passed by host at epoch start)
  
  tick_inc(BASE+2)
  rng_next(BASE+3)
  player_move_x(BASE+4, BASE+7)
  player_move_y(BASE+5, BASE+7)
  checksum_recalc(BASE, BASE+378)
  HALT
```

**Total estimado:** ~1200-1500 ops (cabe en 59049 celdas con holgura)

---

## VERIFICACIÓN POR FRAGMENTO

Cada fragmento debe pasar:

| Test | Descripción |
|---|---|
| **Unit** | Input state → output state match exacto en 3 intérpretes |
| **Isolation** | Otras palabras de memoria inmutadas |
| **Boundary** | Valores edge (0, 59048, max) correctos |
| **Composition** | Cadena de 2+ fragmentos compone correctamente |
| **Cross-VM** | Snapshot tras fragmento N → resume fragmento N+1 en fresh VM = monolítico |

---

## EVIDENCE REQUIRED PER FRAGMENT

```
evidence/FRAGMENT_<name>/
├── fragment.op          # opcodes
├── fragment.mal         # ASCII source
├── spec.json            # this spec
├── test_vectors.json    # input→output pairs (min 100)
├── oracle_run.json      # Oracle execution
├── gost_run.json        # gost execution
├── engine_run.json      # Malbolge-Engine execution
├── walbolge_trace.json  # Walbolge trace
├── SHA256SUMS.txt
└── VERDICT.md           # PASS/FAIL + first_divergence if FAIL
```

---

## PRIORIDAD DE IMPLEMENTACIÓN

1. **tick_inc** — más simple, valida infraestructura
2. **rng_next** — crítico para determinismo
3. **player_move_x** — primera operación de juego real
4. **player_move_y** — simétrico a X
5. **checksum_recalc** — más complejo (loop largo)
6. **halt** — trivial

---

## HERRAMIENTAS DE SÍNTESIS

- `Malbolge-Translator backend.search_continuation()` para fragments que producen output
- `Malbolge-Translator backend.search_bridge()` para state transitions (depth=3 límite)
- **Nuevo:** `synthesize_fragment.py` con state-transition spec (ver siguiente paso)
- `Autobolge Zig DSL` para búsqueda exhaustiva con constraints de estado final