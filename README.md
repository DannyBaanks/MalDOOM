# MALDOOM

> Un proyecto de investigacion que intenta construir estado interactivo
> progresivamente mas rico dentro de Malbolge Clasico (3^10 / 59049 celdas de memoria).

El proyecto trata a Malbolge mismo como sustrato computacional. El codigo host
puede correr experimentos, alimentar input, colectar traces y renderizar evidencia, pero
no debe implementar la semantica del juego que se reclama.

**Evidencia antes de narrativa.**

---

## Primera Ley

$$\boxed{\text{SI EL HOST COMPUTA UNA TRANSICION DE GAMEPLAY DE DOOM, LA DEMOSTRACION FALLA.}}$$

El host **solo** puede hacer I/O: presentar un framebuffer, transportar input de teclado,
mantener timing, y mover bytes de WAD (sin parsing semantico de WAD). NO puede computar
gameplay, posicion, AI, colisiones, RNG, o producir `S_t → S_{t+1}`.
`grep doomgeneric_Tick host/` debe retornar 0 hits, o el host se robo la
computacion.

---

## Por que existe esto

Doom ha corrido en calculadoras, pruebas de embarazo y papas. ¿Puede hacerse correr
*sobre* semantica de Malbolge — con el host reducido a un framebuffer tonto — y
no simplemente *imprimir* "Doom" desde Malbolge?

Malbolge Clasico es de **almacenamiento acotado** (59049 celdas) y famosamente hostil: el
codigo se auto-encripta mientras corre, `crazy` es una operacion tritwise, y los punteros
`c`/`d` avanzan cada paso. Construir incluso una unidad minima con estado adentro es el
problema dificil. Esa es la verdadera pregunta de investigacion.

---

## Restricciones de Malbolge Clasico

- Memoria: exactamente `3^10 = 59049` celdas. Celdas sin usar se llenan con
  `mem[i] = crazy(mem[i-1], mem[i-2])`.
- Auto-encriptacion: cada celda de codigo ejecutada se reescribe via la tabla de encriptacion.
- `crazy(a,b)`: deterministica, tritwise (ternaria) operacion.
- Punteros: `c` (codigo) y `d` (datos) avanzan en 1 cada paso, wrapping mod 59049.
- I/O: `mod 256`. No es Turing-completo (almacenamiento acotado).

`MALBOLGE_MEMORY_AS_CA_MODEL` es un *modelo experimental* usado en el experimento
de quine para estudiar la dinamica de memoria observada; **no** es un reclamo de que
"Malbolge es un automata celular".

---

## Escalon de hitos

Paramos en el primer `NOT_DEMONSTRATED`; sin saltos.

```
M0  El backend de Malbolge ejecuta aritmetica/flujo de control EIR arbitrario
M1  Header de WAD parseado dentro de semantica de Malbolge
M2  El estado de juego Doom S_0 se inicializa adentro
M3  un tick deterministico de Doom  H(S_{t+1}) == H(S_t)_C
M4  input del jugador cambia el estado del juego
M5  un framebuffer correcto (hash de pixel vs C)
M6  ticks repetidos sin reset/recompilacion
M7  E1M1 tecnicamente jugable
```

Dos targets, nunca conflados:

| Target | Variante | Memoria | Estado |
|---|---|---|---|
| TARGET_A | Malbolge Unshackled | ilimitado, Turing-completo | candidato para Doom completo |
| TARGET_B | Malbolge Clasico | 59049 fijo, acotado | `FULL_DOOM = NOT_DEMONSTRATED` |

---

## Experimento quine-outward

`experiments/QUINE_OUTWARD_V0/` estudia el quine real de Lutter Malbolge
(vendored en `vendor/quines/`, interprete en `vendor/malbolge/`) para extraer una
primitiva de estado componible:

1. **Mecanismo** — el quine es un *lector + cinta de fuente*: bloque de codigo ~29.2-29.5k
   lee sus propios bytes en `29516+k` secuencialmente; cada celda de cinta mapea a exactamente
   un byte de output (causal, verificado por perturbacion).
2. **Modelo de anillo discreto** — un anillo finito wrappeado bajo la regla de fill real `crazy`;
   busca *configuraciones* (no programas) para firmas estables y distinguibles.
3. **Microcelda** — anillo mas pequeno (N=3) cuya firma de ventana distingue dos
   estados estables.
4. **Composicion** — dos microceldas se destruyen mutuamente a menos que esten separadas por una
   costura; una costura de 1 celda preserva ambas. Elevar a macrocelda funciona en un
   gap inter-unitario especifico.
5. **Regeneracion** — fill pasivo no repara (3/8 single-cell, 0/8
   double-cell). La regeneracion real debe venir de reescrituras de codigo dirigidas.
6. **Input → estado** — un bit de input 0/1 produce firmas distinguibles en
   horizonte largo (1000 pasos) pero no corto (100 pasos).
7. **Paridad VM** — el modelo de anillo discreto concuerda con la VM real en la region
   de fill pasivo (12/13, una excepcion de frontera de fill).

Veredictos honestos completos en `experiments/QUINE_OUTWARD_V0/SUMMARY.md`.

---

## Demostrado

- Mecanismo real de lector/cinta de quine (en la VM real, verificado por perturbacion).
- Paridad de regla de fill pasivo entre el modelo de anillo y la VM real (12/13).
- Microcelda mas pequena distinguible en el modelo (N=3).
- Una costura de 1 celda que deja coexistir a dos microceldas en el modelo.
- Elevacion a macrocelda en un gap inter-unitario en el modelo.

## No demostrado

- Regeneracion robusta despues de dano (fill pasivo).
- Input → estado persistente en horizonte corto.
- `FULL_DOOM_ON_CLASSIC_MALBOLGE`.
- Cualquier equivalencia de "Malbolge es un automata celular".

---

## Reproducir

Desde un clone limpio (autosuficiente; sin dependencia externa/privada):

```bash
# self-test del interprete vendored (Wikipedia Hello World -> HALTED)
py vendor/malbolge/malbolge.py

# experimentos quine-outward (desde experiments/QUINE_OUTWARD_V0/src/)
py microcell.py        # microcelda mas pequena distinguible
py seam.py             # costura minima para coexistencia
py macrocell.py        # elevacion
py regen.py            # regeneracion / cuenca
py input_state.py      # input -> estado persistente
py vm_parity.py        # paridad modelo vs VM real (region pasiva)
```

Cada script escribe su JSON de evidencia al lado (o imprime). Las herramientas corren con
`py <script>.py` desde el directorio `src/` para que el `_common.py` vendored resuelva
la raiz del repositorio.

---

## Evidencia

- `experiments/QUINE_OUTWARD_V0/` — docs + results JSON + scripts.
- `evidence/CLASSIC_ANCHOR_SMOKE_V1/` — Evidencia de checkpoint/busqueda clasica
  (P1-P5, negativos honrosos para cross-read state).
- `evidence/M0*/` — Evidencia del pipeline Unshackled/HeLL.
- `evidence/DOOM_NATIVE_BASELINE/` — runs de referencia nativos de Doom.

La evidencia cruda es historica y nunca se reescribe para encajar en una narrativa.

---

## Limitaciones

- Los resultados de microcelda/macrocelda/costura quine-outward son de **nivel modelo**; se
  validan contra la VM real solo en la region de fill pasivo, no aun como
  programa clasico corriendo.
- No se ha producido ningun estado de juego Doom dentro de Malbolge.
- Malbolge Clasico es de almacenamiento acotado; `FULL_DOOM` en Clasico no se reclama.

---

## Referencias

- `ozkl/doomgeneric` — capa de porting de 5 funciones (`DG_Init, DG_DrawFrame,
  DG_SleepMs, DG_GetTicksMs, DG_GetKey`).
- `shinh/elvm` + `shinh/8cc` (eir) — pipeline `C → EIR → HeLL`.
- HeLL / LMFAO — ensamblador y assembler de Malbolge/Unshackled.
- Malbolge Unshackled — `oerjan.nvg.org/esoteric/Unshackled.hs`,
  `lutter.cc/unshackled/`.
- Malbolge Clasico — Iizawa (2005) / `malbolge.c` de referencia (lenguaje publico).

---

*Si el host computa una transicion de gameplay de Doom, la demostracion falla. No
es un slogan — es una puerta.*
