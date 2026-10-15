# Toolchain — Real Path That Exists Today

> Document before compiling. No claim that `C → Malbolge` works until each edge is demonstrated.

## Pinned Versions

See `TOOLCHAIN_LOCK.json` for exact commits — HEAD today (2026-09-01):

- `shinh/elvm` `020d1d8c` — contains `target/hell` (HeLL backend)
- `shinh/8cc` `2fd8c549` (branch `eir`) — `8cc` that emits EIR
- `ozkl/doomgeneric` `dcb7a8db` — 5-function Doom port
- `esoteric-programmer/LMFAO` `c62bbe32` — HeLL assembler
- `lutter.cc/Unshackled.c` + `Unshackled.hs` — Unshackled VMs

## Canonical Pipeline

```
hello.c  →  8cc -S -o hello.eir hello.c          # C → EIR (Harvard, 6 regs, 24-bit)
hello.eir → elvm target/hell → hello.hell        # EIR → HeLL
hello.hell → LMFAO → hello.mu                    # HeLL → Malbolge Unshackled
hello.mu → Unshackled.c → output                 # run
```

Or via ELVM make shortcut (once toolchain built):

```bash
HELL=1 make hell           # ELVM warns: extremely slow, adjust tools/runhell.sh
# produces out/*.eir.hell and out/*.eir.mu
```

## What ELVM Docs Actually Say

- HeLL is *"assembly language for Malbolge and Malbolge Unshackled. Use LMFAO to build."*
- *"This backend won't be tested by default because Malbolge Unshackled is extremely slow. Use HELL=1 make hell. Note you may need to adjust tools/runhell.sh."*
- *"This backend does not support all 8-bit characters on I/O, because I/O uses Unicode codepoints instead of single bytes. [...] You should limit I/O to ASCII."*
- `"The backend reverts/converts newlines [...] but cannot compensate [...] Limit to ASCII."*

## 8cc / EIR Facts

- EIR = `mov, add, sub, load, store, setcc, jcc, putc, getc, exit` + pseudo `.text/.data/.long/.string`
- 6 regs: A,B,C,D,SP,BP. No bit ops, no float. `sizeof(char)==sizeof(int)==sizeof(void* )==1`. Most backends 24-bit words.
- `mul/div/mod` via `__builtin_*`.

## Doomgeneric Facts

- 5 required funcs: `DG_Init, DG_DrawFrame, DG_SleepMs, DG_GetTicksMs, DG_GetKey` (+ optional `DG_SetWindowTitle`)
- Main loop: `doomgeneric_Create(argc,argv); while(1) doomgeneric_Tick();`
- `DG_ScreenBuffer` is the framebuffer (320×200, 8-bit paletted → expanded to 32-bit in ports).
- License GPL-2.0.

## Known Gaps — Not Invented

- `C → HeLL` has not been demonstrated on this host until `M0` runs. If it fails, document where: `C→EIR` / `EIR→HeLL` / `LMFAO assemble` / `Unshackled run` / I/O.
- LMFAO build requires Haskell or C toolchain depending on version — verify on this host.
- Unshackled rotation width is variable (≥10, grows when `j` widens `D`). Programs must probe it — the ELVM-generated prologue handles this, but we must measure artifact size and runtime.
- Classic Malbolge 59049 memory is NOT used for Doom full — that's TARGET_B `NOT_DEMONSTRATED`.

## Local Classic Synthesis

MALDOOM vendors the minimum Classic search substrate at
`vendor/classic_synthesis/`; it does not need an Autobolge or MALPAD clone at
runtime. Source commits, licenses, SHA256 values and credit are frozen in
`vendor/classic_synthesis/PROVENANCE.md` and `SHA256SUMS.txt`.

```powershell
cd vendor/classic_synthesis
zig build-exe branch_search.zig -O Debug "-femit-bin=branch_search.exe"
.\branch_search.exe 2 20 A A B B
# EXPECT: ub input1_steps=3 input2_steps=3; BRANCH total=64 hits=1
```

This searcher is tooling only. It never participates in Doom gameplay or in
the runtime host. The included MALPAD truth-machine is a verified non-echo
branch/halt seed; its source license was absent at the recorded source commit,
so its provenance must accompany every redistribution.

## Verification on This Host (to fill after fetch)

```bash
# after fetch
ls vendor/elvm/target/hell/
ls vendor/8cc/           # eir branch
./vendor/Unshackled vendor/build/M0_A_CONST.mu < /dev/null
```

Record exact output, SHA-256, wall time in `evidence/`.

## Windows EIR Frontend Workaround

The vendored `8cc` EIR frontend builds on Windows with MinGW after two local
source adjustments in `vendor/elvm/8cc/main.c`:

1. Include the POSIX headers only when `__eir__` is not defined. The EIR path
   does not use `fork`, `exec`, or `waitpid`.
2. Call `set_output_file(stdout)` in the `__eir__` path. Without this,
   `outputfp` remains NULL.

Build with `gcc`, not the Makefile's Unix-only default `cc`. In `__eir__`
mode, feed C on stdin; the frontend emits EIR on stdout. Redirect compiler
output with a binary-safe command shell, because PowerShell redirection can
produce UTF-16, which LMFAO rejects.

The complete path was verified on 2026-09-10 in
`evidence/PIPELINE_E2E_V0/SUMMARY.md`:

```
C -> 8cc (__eir__) -> EIR -> elc -hell -> HeLL -> LMFAO -> .mu -> Unshackled
```

Observed outputs were `A`, `OK`, and `40+2=42`.

## Linux Build Host (verified 2026-10-10)

The Windows host that produced `evidence/M0-M3a` is gone. The toolchain was
rebuilt on Linux (Ubuntu 24.04, gcc 13.3) and the offline suite is green
(4/4). Exact commands, all from the repo root:

```bash
# 1. Unshackled VM (the tests' expected binary name is vendor/Unshackled)
gcc -O3 -o vendor/Unshackled vendor/Unshackled.c

# 2. ELVM tools: elc (EIR -> HeLL) and 8cc (C -> EIR)
cd vendor/elvm && mkdir -p out
gcc -std=gnu99 -O2 -w -I. -o out/elc ir/ir.c ir/table.c target/*.c
make out/8cc                 # builds elvm's copy of 8cc (no flex/bison needed)

# 3. C -> EIR -> HeLL, verified end to end:
./vendor/elvm/out/elc -hell /path/to/prog.eir > prog.hell
```

Two Linux-only recipes learned the hard way:

1. **`#include <stdio.h>` only resolves when the C file lives inside
   `vendor/elvm/`** (8cc searches angle includes relative to the source file's
   directory, not only `-I`). Copy/keep sources there, then:
   `cd vendor/elvm && ./out/8cc -S -I. -Ilibc -I8cc/include -o out.eir src.c`
   (`elvm/libc/*.h` is ELVM's own libc shim — required, `vendor/8cc/include`
   alone has no stdio.)
2. **elc takes the target as a flag:** `elc -hell file.eir > file.hell`
   (`elc hell file.eir` errors with "no target").

Still blocked on Linux: **LMFAO** (HeLL -> .mu) needs `flex`/`bison`
(`apt install flex bison`; the Windows build patched `lmfao.l` with
`%option noyywrap`). Until then, .mu artifacts are produced on Windows or by
the hand-written EIR path of commit 35bc289.

## Pinned Unshackled VM (verified 2026-10-14, evidence/E4_VM_CONFIG_PINNED_V0)

`vendor/Unshackled.c` draws its rotation-width policy from `srand(time(NULL))`
at startup (`rotwidth = 10 + rand()%6`, `growth_slack`, `growth_step`,
`growth_prob`, `det_growth`). Consequence, measured: **the same immutable `.mu`
executes between 10,347,259 and 22,996,958 steps depending on the draw** — a
2.22x spread over 153 runs. stdout never changed. So a bare step count is not a
fact about an artifact, and E3's two step numbers came from two different draws.

For any step-count, trace or timing claim, build the pinned clone instead of
the raw vendor source:

```bash
mkdir -p "$HOME/tmp_e4" && cd "$HOME/tmp_e4"
gcc -O2 -w -o unsh_pinned "$REPO/evidence/E4_VM_CONFIG_PINNED_V0/unsh_pinned.c"
printf '0\n' | UNSH_ROTWIDTH=10 UNSH_GROWTH_SLACK=3 UNSH_GROWTH_STEP=5 UNSH_DET_GROWTH=1 \
  ./unsh_pinned "$REPO/evidence/M0_KILLER_UNSHACKLED_V0/artifact.mu"
```

Raw telemetry, verbatim (`evidence/E4_VM_CONFIG_PINNED_V0/raw/10_pin_verbatim.txt`):

```
UNSH_PIN STEPS 10347959 WALL 1.518s SPS 6815549 cfg{seed=7 rotwidth0=10 slack=3 gstep=5 det=1 prob=1073741823} final{rotwidth=20 max_wordwidth=10}
1
```

Rules learned the hard way, both binding for evidence:

1. **Pin with `det_growth=1`.** It consumes no `rand()` inside the dispatch
   loop, so the run is seed-invariant (verified with seeds 1/7/4242).
   `det_growth=0` with `growth_slack>0` varies with seed *and* with
   `growth_prob`; `det_growth=0` with `slack=0` degenerates to the forced
   branch and is deterministic.
2. **Never report a single wall time.** Within-level run-to-run spread is
   2.1-4.4% over 5 reps; the first single-shot probe of this session claimed
   `-O1` was slow, and 5 reps refuted it. Reference throughput at the pin is
   **~6.5M steps/s (-O2)**, roughly 1.9x what `evidence/E3` recorded.

Full sweep and its raw logs: `evidence/E4_VM_CONFIG_PINNED_V0/commands.txt`;
re-run with `E4_QUICK=1 ./evidence/E4_VM_CONFIG_PINNED_V0/e4_capture.sh`, which
writes to its own scratch dir and cannot overwrite the sealed logs.
