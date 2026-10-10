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
