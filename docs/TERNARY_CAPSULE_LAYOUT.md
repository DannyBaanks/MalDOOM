# MALDOOM Ternary Capsule Layout

**Formato:** 10 trits/palabra = valor 0..59048 (1 trit = 0,1,2; 3^10 = 59049)
**Serialización:** little-endian (word 0 = menos significativo) o big-endian según convención

---

## CAPSULE HEADER (words 0-3)

| Word | Nombre | Rango | Descripción |
|---|---|---|---|
| 0 | `MAGIC` | fijo `0xDEAD` (57005 dec) | Identificador de cápsula válida |
| 1 | `VERSION` | 0..59048 | Versión del formato (empieza en 1) |
| 2 | `TICK` | 0..59048 | Tick global de la partida |
| 3 | `RNG_STATE` | 0..59048 | Estado del RNG trinario (ver abajo) |

---

## PLAYER STATE (words 4-18)

| Word | Nombre | Bits/trits | Descripción |
|---|---|---|---|
| 4 | `PLAYER_X` | 10 trits | Posición X (fixed-point 16.16 → trits) |
| 5 | `PLAYER_Y` | 10 trits | Posición Y |
| 6 | `PLAYER_Z` | 10 trits | Posición Z (altura) |
| 7 | `PLAYER_ANGLE` | 10 trits | Ángulo (0..65535 → trits) |
| 8 | `HEALTH` | 10 trits | 0..100 (o 0..200 con powerups) |
| 9 | `ARMOR` | 10 trits | 0..200 |
| 10 | `AMMO_SHELLS` | 10 trits | 0..400 |
| 11 | `AMMO_CELLS` | 10 trits | 0..600 |
| 12 | `AMMO_ROCKETS` | 10 trits | 0..50 |
| 13 | `WEAPONS_BITMASK` | 10 trits | Bit 0=fist, 1=pistol, 2=shotgun, 3=chaingun, 4=rocket, 5=plasma, 6=bfg, 7=chainsaw, 8=super shotgun |
| 14 | `KEYS_BITMASK` | 10 trits | Bit 0=red key, 1=yellow key, 2=blue key, 3=red skull, 4=yellow skull, 5=blue skull |
| 15 | `SELECTED_WEAPON` | 10 trits | 0..7 |
| 16 | `PENDING_WEAPON` | 10 trits | 0..7 (para cambio de arma) |
| 17 | `PLAYER_FLAGS` | 10 trits | Bitfield: godmode, noclip, notarget, etc. |
| 18 | `ATTACK_STATE` | 10 trits | Frames desde último ataque, estado de animación |

---

## WORLD STATE (words 19+)

### DOORS (variable, max 64 doors)
| Word | Nombre | Descripción |
|---|---|---|
| 19 | `NUM_DOORS` | Número de puertas activas (0..64) |
| 20..83 | `DOOR_STATES` | 64 palabras: cada una = `position<<6 | wait<<4 | speed<<2 | flags` (packed) |

### SWITCHES (variable, max 64)
| Word | Nombre | Descripción |
|---|---|---|
| 84 | `NUM_SWITCHES` | |
| 85..148 | `SWITCH_STATES` | 64 palabras: estado + timer |

### PICKUPS (variable, max 128)
| Word | Nombre | Descripción |
|---|---|---|
| 149 | `NUM_PICKUPS` | |
| 150..277 | `PICKUP_STATES` | 128 palabras: `type<<8 | position<<4 | flags` |

### ENEMIES (variable, max 64)
| Word | Nombre | Descripción |
|---|---|---|
| 278 | `NUM_ENEMIES` | |
| 279..342 | `ENEMY_STATES` | 64 palabras: `type<<26 | x<<16 | y<<10 | z<<4 | health<<2 | state | flags` (packed 10 trits) |

### PROJECTILES (variable, max 32)
| Word | Nombre | Descripción |
|---|---|---|
| 343 | `NUM_PROJECTILES` | |
| 344..375 | `PROJECTILE_STATES` | 32 palabras |

---

## ENGINE STATE (final words)

| Word | Nombre | Descripción |
|---|---|---|
| N-3 | `SCRIPTS_RUNNING` | Bitmask de scripts activos |
| N-2 | `RNG_COUNTER` | Contador adicional para RNG |
| N-1 | `CHECKSUM` | Checksum trit-wise de toda la cápsula |

---

## RNG TRINARIO (Word 3 + Word N-2)

Implementación: **LCG ternario** sobre 10 trits
```
state = (state * 21 + 7) % 59049  # multiplicador y incremento primos relativos a 3^10
```
- Word 3 = `state` principal
- Word N-2 = `counter` (incrementa cada llamada, evita ciclos cortos)

Para extraer bits: `state % 3` da trit, `state / 3` siguiente, etc.

---

## CHECKSUM (Word N-1)

```
checksum = 0
for each word in capsule[:-1]:
    checksum = crazy(checksum, word)  # operación crazy ternaria
checksum = checksum % 59049
```

---

## SERIALIZACIÓN COMPLETA

```python
# Total estimado: ~400 palabras = 4000 trits = ~500 bytes
# Cabe cómodamente en 59049 celdas de Malbolge Classic

CAPSULE_WORDS = [
    MAGIC, VERSION, TICK, RNG_STATE,
    PLAYER_X, PLAYER_Y, PLAYER_Z, PLAYER_ANGLE,
    HEALTH, ARMOR, AMMO_SHELLS, AMMO_CELLS, AMMO_ROCKETS,
    WEAPONS_BITMASK, KEYS_BITMASK, SELECTED_WEAPON, PENDING_WEAPON,
    PLAYER_FLAGS, ATTACK_STATE,
    NUM_DOORS, *[DOOR_STATES],
    NUM_SWITCHES, *[SWITCH_STATES],
    NUM_PICKUPS, *[PICKUP_STATES],
    NUM_ENEMIES, *[ENEMY_STATES],
    NUM_PROJECTILES, *[PROJECTILE_STATES],
    SCRIPTS_RUNNING, RNG_COUNTER, CHECKSUM
]
```

---

## MAPEO A MALBOLGE VM STATE

| Game State | VM State |
|---|---|
| `a` | Acumulador general / scratch |
| `c` | Instruction pointer (code pointer) |
| `d` | Data pointer (apunta a capsule base) |
| `tape[0:CAPSULE_SIZE]` | Cápsula completa serializada |
| `tape[CAPSULE_SIZE:]` | Memoria de trabajo / stack / scratch |

**Invariante:** Al reanudar epoch N+1, `d` debe apuntar al inicio de la cápsula en memoria, `c` al entry point del epoch handler.

---

## EVIDENCE REQUIREMENTS

Cada epoch transition debe producir:
- `capsule_before.json` (estado completo pre-epoch)
- `capsule_after.json` (estado completo post-epoch)
- `epoch_transition.op` (opcodes del transition handler)
- `SHA256SUMS.txt` de ambos + programa
- `EPOCH_N_TRANSITION_PASS = true/false` con primer divergencia si falla