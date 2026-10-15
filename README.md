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
M0  El backend de Malbolge ejecuta aritmetica/flujo de control EIR arbitrario  [DEMOSTRADO en TARGET_A, 2026-09]
M1  Header de WAD parseado dentro de semantica de Malbolge                      [DEMOSTRADO en TARGET_A, 2026-09]
M2  El estado de juego Doom S_0 se inicializa adentro                           [solo PILOTO M2a; S_0 completo NOT_DEMONSTRATED]
M3  un tick deterministico de Doom  H(S_{t+1}) == H(S_t)_C                      [solo PILOTO M3a; tick completo NOT_DEMONSTRATED]
M4  input del jugador cambia el estado del juego                                [NOT_DEMONSTRATED]
M5  un framebuffer correcto (hash de pixel vs C)                                [NOT_DEMONSTRATED]
M6  ticks repetidos sin reset/recompilacion                                     [NOT_DEMONSTRATED]
M7  E1M1 tecnicamente jugable                                                   [NOT_DEMONSTRATED]
```

Dos targets, nunca conflados:

| Target | Variante | Memoria | Estado |
|---|---|---|---|
| TARGET_A | Malbolge Unshackled | ilimitado, Turing-completo | candidato para Doom completo |
| TARGET_B | Malbolge Clasico | 59049 fijo, acotado | `FULL_DOOM = NOT_DEMONSTRATED` |

---

## Cadena de integridad de la evidencia (E1-E8)

Renglon aparte del escalon M0-M7: estas corridas no ejecutan DOOM ni cambian ninguna etiqueta de
reclamo. Lo que establecen es que la evidencia **commiteada** es la evidencia **sellada**.

E1 migracion del toolchain a Linux · E2 reproducibilidad del toolchain · E3 rendimiento de la VM ·
E4 config de VM fijada (pinned) · E5 convencion del loader de LMFAO (imagenes `.mu` en motores de
ancho fijo) · E6 integridad de sellos · E7 disposicion de los sellos que fallaban · E8 alineacion del
lado commiteado.

Medido 2026-10-15 sobre arbol de trabajo, indice y `HEAD`:

| relacion | cifra |
|---|---|
| manifiestos `evidence/**/SHA256SUMS.txt` | 40 |
| entradas selladas | 362 |
| verifican en el worktree | 353 |
| tres vias `worktree == sello == HEAD` | **351** |
| fallos | 9 |

Los 9 no son trabajo abierto y no estan ocultados: 7 son `evidence/M0_*/SHA256SUMS.txt`, que se sellan
a si mismos (no existen bytes que satisfagan esa linea), y 2 son
`evidence/EPOCH_TRANSPARENCY_V{0,1}/evidence.json`, cuyos bytes sellados no estan en ninguna parte —
ni worktree, ni base de objetos, ni HEAD. Prueba y descartes: `evidence/E7_SEAL_DISPOSITION_V0/` y
`evidence/E8_COMMIT_SIDE_ALIGNMENT_V0/E8_ALIGNMENT.md`.

Convencion desde E5: manifiestos en LF y **sin auto-entrada**. `.gitattributes` fija `* -text`, asi que
Git no convierte finales de linea; lo commiteado son los bytes exactos.

### Advertencia operacional (medida, no folclore)

- `git status`, `git diff HEAD` y **`git add` pueden ser no-ops silenciosos**: la entrada del indice
  lleva el tamano y el mtime del worktree mientras guarda otro blob. Paso en E6 y en E8; el intento con
  `git add` dio `restaged=0 / refused=119` y la unica ruta que funciono fue por indice
  (`git hash-object -w` + `git update-index --cacheinfo`), sin tocar un byte del worktree.
- `sha256sum -c` **por si solo no es un chequeo de integridad**: compara worktree contra sello y pasa
  aunque lo commiteado difiera. El chequeo obligatorio aqui es el de tres vias.
- `scripts/build_m0.py` **no** sirve como verificador: `build_m0.py:65` escribe dentro de
  `evidence/<M0_*>/` y re-drifta archivos sellados en el lugar.

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

## Demostrado — TARGET_A Unshackled (2026-09, ruta EIR a mano)

`8cc` nunca compilo en este host, asi que el borde `C → EIR` se sorteo con
EIR escrito a mano en vez de trampearse con computo del host:
`EIR → HeLL` via `elvm/out/elc.exe` compilado local, `HeLL → .mu` via
LMFAO v0.1.5, ejecucion en `vendor/Unshackled.exe`. Los fuentes C quedan como
referencia y asi se declara en cada `run.json`.

- **M0 7/7 en la VM real** (`evidence/M0_*_UNSHACKLED_V0/`): output fijo,
  `40+2` con digitos calculados, branch, loop ×5, suma con store/load,
  incremento con wrap `9→0`, y el killer `n*2+1` con el **mismo `.mu` para
  5 inputs**.
- **M1**: header de `doom1.wad` parseado dentro de la VM → `IWAD / 1264 / 4175796`,
  byte-identico a la referencia C (`evidence/M1_WAD_HEADER_UNSHACKLED_V0/`).
  Binario crudo no cruza el stdin de Unshackled (UTF-8-gated), asi que el host
  hex-enmarca los 12 bytes del header (ciego al contenido); todo el
  decode/parse corre en-VM.
- **M2a (piloto)**: direccionamiento de lumps sobre 4 registros reales del
  directorio — `ENDOOM → MATCH 2/19468/4000`, `PLAYPAL → MATCH 0/12/10752`,
  nombre desconocido → `NOMATCH`, mismo `.mu`
  (`evidence/M2A_LUMP_FIND_UNSHACKLED_V0/`). S_0 completo NOT_DEMONSTRATED
  (throughput de getc acota el bulk; medido ~2 s/byte).
- **M3a (piloto)**: el `P_Random` real de Doom (tabla parseada del `m_random.c`
  vendored; la referencia linka ese archivo) corre 3 ticks × 8 draws en-VM con
  estado acarreado entre ticks, byte-identico a C
  (`evidence/M3A_P_RANDOM_UNSHACKLED_V0/`). Hash de `doomgeneric_Tick`
  completo NOT_DEMONSTRATED (EIR es 24-bit; la fisica fixed-point de Doom no
  cabe en el tipo).
- **Separacion TARGET**: `ABC.mal` clasico bajo Unshackled da `AB` +
  `invalid unicode codepoint`, exit 1 — artefactos `.mal` no transfieren;
  documentado en `docs/UNSHACKLED_CONTINUATION_ANCHOR_V0.md`.

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
# re-ejecutado en Linux 2026-10-15: status=HALTED steps=48, output='Hello, world.', exit 0
python3 vendor/malbolge/malbolge.py

# experimentos quine-outward (desde experiments/QUINE_OUTWARD_V0/src/)
python3 microcell.py        # microcelda mas pequena distinguible
python3 seam.py             # costura minima para coexistencia
python3 macrocell.py        # elevacion
python3 regen.py            # regeneracion / cuenca
python3 input_state.py      # input -> estado persistente
python3 vm_parity.py        # paridad modelo vs VM real (region pasiva)
```

Los seis scripts del quine imprimen su JSON por stdout y **no escriben archivos** (verificado en el
codigo, 2026-10-15), asi que relanzarlos no mueve la evidencia. Corren con `python3 <script>.py` desde
`src/` para que el `_common.py` vendored resuelva la raiz del repositorio. El host actual es
Ubuntu 24.04; los comandos `py` y PowerShell de las notas de 2026-09 son historicos.

---

## Evidencia

- `experiments/QUINE_OUTWARD_V0/` — docs + results JSON + scripts.
- `evidence/CLASSIC_ANCHOR_SMOKE_V1/` — Evidencia de checkpoint/busqueda clasica
  (P1-P5, negativos honrosos para cross-read state).
- `evidence/M0*/` — Evidencia del pipeline Unshackled/HeLL.
- `evidence/M0_*_UNSHACKLED_V0/` — M0 A..KILLER en la VM real (EIR a mano).
- `evidence/M1_WAD_HEADER_UNSHACKLED_V0/` — parse de header WAD en-VM.
- `evidence/M2A_LUMP_FIND_UNSHACKLED_V0/` — piloto de direccionamiento de lumps.
- `evidence/M3A_P_RANDOM_UNSHACKLED_V0/` — piloto de tick P_Random.
- `evidence/PURE_CONTINUATION_ANCHOR_V0/` — A→B→C→HALT clasico en una VM (TARGET_B).
- `evidence/UNSHACKLED_CONTINUATION_ANCHOR_V0/` — A/AA/AB/ABC HeLL nativo (TARGET_A).
- `evidence/DOOM_NATIVE_BASELINE/` — runs de referencia nativos de Doom.
- `evidence/E1_*` … `evidence/E8_*` — la cadena de integridad (herramientas, `raw/` y reporte de cada
  paso; ver la seccion E1-E8 arriba).

La evidencia cruda es historica y nunca se reescribe para encajar en una narrativa.

Dos avisos de lectura: `evidence/M0_REPORT.md` es el informe por hito de M0 (de ahi salen las
etiquetas del escalon), y `docs/CLAIMS.md` es el registro de reclamos y **no se ha promovido** desde
2026-09-03 — sigue en `NOT_DEMONSTRATED` para M0/M1 aunque existan `evidence/M0_REPORT.md` y
`evidence/M0_*_UNSHACKLED_V0/`. La discrepancia esta abierta; este README no la resuelve ni sube
ningun label.

---

## Publicacion

Repo publico `https://github.com/DannyBaanks/MalDOOM`, rama `master`, sin CI configurada
(`check-runs` = 0, consultado por API, no asumido). La auditoria de publicacion y la matriz de
integridad por commit estan en `docs/GIT_PUBLICATION_REPORT.md`. Un clone anterior a 2026-10-15 trae
los renderings LF de los archivos que E8 alineo: necesita `git pull`. No se reescribio historia, asi
que las versiones previas siguen siendo objetos validos del historial.

---

## Limitaciones

- Los resultados de microcelda/macrocelda/costura quine-outward son de **nivel modelo**; se
  validan contra la VM real solo en la region de fill pasivo, no aun como
  programa clasico corriendo.
- No se ha producido ningun estado de juego Doom completo (S_0) dentro de
  Malbolge; solo el primitivo de direccionamiento (M2a) y el kernel RNG (M3a).
- Malbolge Clasico es de almacenamiento acotado; `FULL_DOOM` en Clasico no se reclama.
- EIR a mano corre en valores de 24-bit: lo que necesite mas de `2^24`
  (fisica fixed-point de 32-bit de Doom, `infotableofs` de WADs de 28 MB)
  esta fuera de esta ruta por construccion, no por esfuerzo.
- Throughput medido acota lo intentable: ~2 s por byte de stdin (`getc`),
  ~0.3 s por paso EIR. Streaming bulk de WAD y compute de tick completo
  exceden cualquier presupuesto a este ritmo.
- Replay requiere el drop de vendor (`vendor/Unshackled.exe`, LMFAO, fuentes
  `elvm`): `vendor/*` esta git-ignored, asi que un clone limpio trae los
  artefactos `.mu` y sus hashes pero no los binarios del toolchain. Recetas de
  build y SHAs en cada `run.json`.
- Estado medido 2026-10-15: **60 archivos trackeados tienen `worktree != HEAD` con `git status`
  limpio** (README.md era el 61; este commit lo alinea). Los 60 son CR-only (el blob commiteado es el worktree sin los retornos de carro) y ninguno
  es una entrada cuyo worktree verifique su sello, asi que la cadena E1-E8 de arriba sigue en pie. No
  estan reparados a proposito: repararlos es decision pendiente, no un olvido. Entre ellos esta
  `.gitignore`, que ademas lleva 14 bytes NUL (una regla `__pycache__/` duplicada en UTF-16); la
  version ASCII de esa regla esta activa, asi que el defecto es de higiene y no de comportamiento.

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
