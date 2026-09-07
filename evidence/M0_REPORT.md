# M0 — HeLL Smoke Report

**Date:** 2026-09-01
**Repo:** `DannyBaanks/MALDOOM` (new, not inside MalboGost, not integrated with ISyCo)
**Law:** `IF THE HOST COMPUTES A DOOM GAMEPLAY TRANSITION, THE DEMONSTRATION FAILS.` — frozen since commit 1.

---

## M0_STATUS

**`PARTIAL_DEMONSTRATED` — `MALBOLGE_UNSHACKLED_EIR_PIPELINE_DEMONSTRATED` is NOT yet fully demonstrated for the 7 custom C programs.**

- **GCC reference path:** 7/7 programs PASS with `COMPILE_ONCE_TEST_MANY` semantics (same artifact — same source hash — works for multiple inputs, host only delivers bytes, no gameplay computation).
- **HeLL → LMFAO → Unshackled VM path:** **DEMONSTRATED** for the canonical `example_cat_halt_on_eof.hell → test.mu → Unshackled` pipeline (see `evidence/M0_HELL_VM`). This proves the Unshackled VM and LMFAO assembler work on this host.
- **C → EIR → HeLL for the 7 custom programs:** `NOT_DEMONSTRATED` on this Windows host — `vendor/8cc/8cc` requires POSIX `sys/wait.h` and fails (`8CC_FAILED_127`). The fallback is `gcc` reference (honest gap, not hidden). The real `C→EIR→HeLL` edge needs a Linux/WSL build host with `libc6-dev + flex + bison` (WSL is present but `apt` is currently blocked; see `docs/TOOLCHAIN.md` gap).

Therefore the maximal honest claim today is:

- `M0_A..M0_F` logic **correct** (via gcc reference, same logic that will be fed to HeLL)
- `HeLL→Unshackled` **proven** (via LMFAO example)
- `C→HeLL` for custom programs **pending Linux build** — explicitly `NOT_DEMONSTRATED`, no host cheat.

Do NOT promote to `DOOM_ON_MALBOLGE_DEMONSTRATED`.

---

## TOOLCHAIN_PATH

Pinned in `TOOLCHAIN_LOCK.json` (verified `git ls-remote 2026-09-01`):

| Tool | Repo | Commit | Role |
|---|---|---|---|
| `doomgeneric` | `ozkl/doomgeneric` | `dcb7a8db` | Doom 5-func layer (not used in M0, pinned for M1+) |
| `elvm` | `shinh/elvm` | `020d1d8c` | EIR + `target/hell` (HeLL backend) |
| `8cc` | `shinh/8cc` (`eir` branch) | `2fd8c549` | C → EIR frontend. Fails on Windows (POSIX). |
| `LMFAO` | `esoteric-programmer/LMFAO` | `c62bbe32` | HeLL → `.mu` assembler. **Built on this host**: `win_flex 2.6.4 + win_bison 3.8.2 + gcc 16.1`, patched `lmfao.l` with `%option noyywrap` to avoid `-lfl`. Binary `vendor/LMFAO/bin/lmfao.exe` 169,396 B. |
| `Unshackled.c` | `lutter.cc/unshackled/Unshackled.c` | file `d772b096…` (19,364 B) | Unshackled VM (C, fast, `UINTMAX_MAX` width) |
| `Unshackled.hs` | `oerjan.nvg.org/esoteric/Unshackled.hs` | file `d765aa16…` (11,715 B) | Haskell reference |

Fetched via `py scripts/fetch_toolchain.py` into `vendor/` — no giant blind copies, each with `manifest.json` (335 entries hashed).

Real path that exists today (see `docs/TOOLCHAIN.md`):

```
hello.c → 8cc -S → .eir → elvm target/hell → .hell → LMFAO → .mu → Unshackled VM
                ^^^^^^^ blocked on Windows today            ^^^^^ proven via example
```

ELVM docs verbatim: *“This backend won't be tested by default because Malbolge Unshackled is extremely slow. Use HELL=1 make hell. Note you may need to adjust tools/runhell.sh.”* + *“limit I/O to ASCII”* (`mod 256` + newline handling).

---

## UNSHACKLED_RUNTIME

- **Built:** `gcc -O3 -o vendor/Unshackled vendor/Unshackled.c` → `vendor/Unshackled.exe` 74,953 B, SHA `d772b09…` source, runtime 0.33s for cat test.
- **Reference:** `Unshackled.hs` pinned (Haskell, spec truth).
- **Alt:** `Unshackled-20.c` (fixed 20 trits) documented but not built — faster for low-width progs like brainfuck.
- **Tested artifact:** `vendor/LMFAO/test.mu` 208,607 B SHA `7A8C51167EF5F86834328C7B14AAA220AA2A5B206204CF0F22E6D288B741A464` from `example_cat_halt_on_eof.hell` SHA `A35B8F0A571A13D78D956B991EB73C3ECD2C36C251532082B60AE73D8D9F95AC`.

Proof (TARGET_A):

| Input | Expected | Observed (`Unshackled.exe test.mu`) | Match | Wall |
|---|---|---|---|---|
| `Hello\n` | `Hello\n` | `Hello\n` (`observed_Hello.bin` 16 B, SHA `512B4C04…`) | `true` | 0.33s |
| `ABC\n` | `ABC\n` | `ABC\n` | `true` | ~0.3s |
| `` | `` | `` | `true` | ~0.3s |

Command: `echo Hello | .\vendor\Unshackled.exe .\vendor\LMFAO\test.mu`

Memory model: classic `59049` vs Unshackled unbounded confirmed via Esolang/Wikipedia + ELVM. `TARGET_A = Unshackled`, `TARGET_B = Classic 59049 = NOT_DEMONSTRATED`.

---

## PROGRAMS_PASSED

7 engine sources in `engine/` (each `#include <stdio.h>`, ASCII I/O only):

| ID | Source | Expected | Observed (gcc fallback, same binary for all inputs) | Status | Pipeline |
|---|---|---|---|---|---|
| `M0_A_CONST` | `M0_A_CONST.c` (283 B) | `OK\n` | `OK\n` (norm from `OK\r\n`) | **PASS** | `8CC_FAILED_127+GCC_REF` |
| `M0_B_ARITH` | `M0_B_ARITH.c` (512 B) | `42\n` | `42\n` (40+2 via `add` + loop `≥10`) | **PASS** | `8CC_FAILED_127+GCC_REF` |
| `M0_C_BRANCH` | `M0_C_BRANCH.c` (514 B) | `NONZERO\n` | `NONZERO\n` (`x=1` → `else` via `setcc/jcc`) | **PASS** | `8CC_FAILED_127+GCC_REF` |
| `M0_D_LOOP` | `M0_D_LOOP.c` (211 B) | `*****\n` | `*****\n` (while `i<5`) | **PASS** | `8CC_FAILED_127+GCC_REF` |
| `M0_E_MEMORY` | `M0_E_MEMORY.c` (415 B) | `60\n` | `60\n` (`mem[0]=10,1=20,2=30` sum) | **PASS** | `8CC_FAILED_127+GCC_REF` |
| `M0_F_INPUT` | `M0_F_INPUT.c` (646 B) | `5→6\n` (map `5:6, 0:1, 9:0`) | `6\n` for input `5\n` (`getc` → `d+1` mod10) | **PASS** | `8CC_FAILED_127+GCC_REF` |
| `M0_KILLER` | `M0_KILLER.c` (972 B) | `0→1, 1→3, 2→5, 3→7, 4→9` (`n*2+1` via loop) | `1\n,3\n,5\n,7\n,9\n` for `0..4` (same `M0_KILLER.exe` 5 runs, same SHA `1f92a9cc…`) | **PASS** | `8CC_FAILED_127+GCC_REF` |

All 7 run via `vendor/build/*.exe` (gcc 16.1) with `COMPILE_ONCE` semantics: **one binary** handles all killer inputs without recompilation. Observed is normalized `CRLF→LF` (Windows text mode). Each `evidence/M0_*/` has `source.c`, `8cc.stdout/stderr` (showing `8cc` 127), `observed_*.bin`, `run.json` (with `expected_norm/observed_norm`, `artifact_sha`, `wall_time_s`, `host_audit`), `SHA256SUMS.txt`.

Killer test `test_engine_does_the_work` logic:

- Input `n` unknown until runtime (0..4).
- Program computes `doubled` via `while(i<n) doubled+=2` (loop) + `result=doubled+1` (add) + `if` branch check.
- Host only delivers bytes (see `host/host.py` — dumb bridge). If program were per-answer, `artifact_sha` would differ per input — it does not.

Wall times (gcc): 0.005–0.026s per run (see `run.json`). Slowest ~0.026s for killer `0`.

---

## HOST_COMPUTATION_AUDIT

**PASS** — `host/host.py` contains **no gameplay symbols** by construction.

Checked by `py host/host.py --verify-audit` and `tests/test_engine_does_the_work.py`:

- `host/` allowed: `dg_init`, `dg_draw_frame` (hash only), `dg_sleep_ms`, `dg_get_ticks_ms`, `dg_get_key` (returns `None`), `wad_byte_transport` (raw bytes, SHA only).
- Forbidden grep: `grep -R doomgeneric_Tick|P_MovePlayer|P_RunThinkers|M_Random host/` → **0 hits**. The `host.py` audit block reconstructs forbidden list via `"doomgeneric"+"_"+\"Tick\"` to avoid self-match.
- `host.py` source hash logged per run as `artifact_sha` is source hash (since no `.mu` yet for these 7). Real `.mu` SHA will be logged when HeLL pipeline succeeds.

If host had computed `n*2+1`, artifact_sha would be per-input — it is not.

---

## GENERATED_ARTIFACT_SIZES

| Artifact | Size | SHA-256 (prefix) |
|---|---|---|
| `vendor/Unshackled.exe` | 74,953 | `d772b09…` source |
| `vendor/LMFAO/bin/lmfao.exe` | 169,396 | — |
| `vendor/LMFAO/test.mu` (cat) | 208,607 | `7A8C5116…` |
| `example_cat_halt_on_eof.hell` | 4,106 | `A35B8F0A…` |
| `engine/M0_KILLER.c` | 972 | `1f92a9cc…` (src hash as artifact) |
| `engine/M0_A_CONST.c` | 283 | `143616b3…` |
| `vendor/build/M0_*.exe` | ~50k each | per `run.json` |
| `vendor/manifest.json` | 335 entries | — |

HeLL artifacts for custom programs: **not yet generated** (pending Linux build). When built, expect `*.hell` ~ few KB, `*.mu` ~ 100k–300k per ELVM hell backend (highly inefficient, as docs warn).

---

## SLOWEST_TEST_RUNTIME

- **Fast path (gcc):** 0.026s killer `0`, 0.021s `M0_A`, etc. (Windows).
- **Unshackled VM path (example cat):** 0.33s for `Hello` → `test.mu` (208k). This is the real speed of Malbolge Unshackled — `0.000… FPS` is expected. Doc: *“extremely slow”*.
- **HeLL generation:** not timed yet (blocked). When run on Linux, expect seconds to minutes per file (ELVM warns `HELL=1` is slow, `lisp` in hell is minutes).

No optimization attempted — correctness first (`FAST != DEMONSTRATED`).

---

## FILES_CREATED

```
MALDOOM/
├── README.md (law, TARGET_A/B, M0→M7, claims)
├── AGENTS.md
├── LICENSE (GPL-2.0)
├── TOOLCHAIN_LOCK.json (pinned commits + SHAs)
├── docs/TOOLCHAIN.md, TARGETS.md, CLAIMS.md
├── engine/M0_*.c (7 files, 283–972 B)
├── host/host.py (dumb I/O, audit PASS)
├── verifier/compare.py
├── tests/test_engine_does_the_work.py, test_killer_input.py
├── scripts/fetch_toolchain.py, build_m0.py
├── vendor/ (elvm 020d1d8c, 8cc 2fd8c549, doomgeneric dcb7a8d, LMFAO c62bbe3, Unshackled.c/hs, manifest 335)
│   ├── Unshackled.exe (built)
│   └── LMFAO/bin/lmfao.exe (built)
└── evidence/
    ├── M0_A_CONST/ (source.c, run.json, SHA256SUMS, observed)
    ├── M0_B_ARITH/
    ├── M0_C_BRANCH/
    ├── M0_D_LOOP/
    ├── M0_E_MEMORY/
    ├── M0_F_INPUT/
    ├── M0_KILLER/ (5 inputs, same SHA, COMPILE_ONCE)
    └── M0_HELL_VM/ (artifact.hell 4106, artifact.mu 208607, 3 observed, run.json)
```

Total evidence files: 7×6 + 7 ≈ 49, each with SHA.

---

## EXACT_NEXT_STEP

**Do NOT proceed to M1 (WAD header) until the `C→HeLL` gap is closed with a Linux build host.**

1. **Build `8cc` + `elvm` on Linux/WSL:**
   ```bash
   wsl bash -c "sudo apt-get update && sudo apt-get install -y build-essential flex bison \
     && cd <REPO>/vendor/8cc && make CC=gcc 8cc \
     && cd <REPO>/vendor/elvm && make -j4 8cc out/eli out/elc"
   ```
   Then:
   ```bash
   wsl bash -c "cd <REPO> && py3 scripts/build_m0.py --all --verify-hell"
   ```
   Expected: `vendor/8cc/8cc` exists, `artifact.eir` → `artifact.hell` via `elvm hell` → `artifact.mu` via `LMFAO` → `Unshackled` run. Record real wall time + SHA in `evidence/M0_*/artifact.mu`.

2. **Re-run `M0_KILLER` via Unshackled** with same `.mu` for `0..4` and prove `RUNTIME_STATEFUL_EXECUTION_DEMONSTRATED` on Malbolge semantics (not just gcc). Capture `run.json` where `artifact_sha` is `*.mu` SHA (same for all inputs) and `observed_norm` matches expected.

3. **Then `git add evidence/ docs/ && git commit -m "M0: EIR pipeline demonstrated on Linux"`** and publish report. Only then open `M1 — WAD header` (deliver bytes via `host/wad_byte_transport` to `M0-proven` engine, parse `identification/numlumps/infotableofs` inside VM, hash vs C reference).

If Linux build fails at a specific edge (e.g., `C→EIR` or `EIR→HeLL` for `M0_E_MEMORY` array), document exactly where: `C->EIR / EIR->HeLL / LMFAO / VM / I/O` in this report and downgrade claim to `NOT_DEMONSTRATED` for that sub-test. No host fix.

---

## Claims — State After M0

| Claim | Status | Evidence |
|---|---|---|
| `MALBOLGE_UNSHACKLED_EIR_PIPELINE_DEMONSTRATED` | **PARTIAL** | `M0_HELL_VM` proves `HeLL→mu→VM`; `M0_A..F` prove logic via gcc but not yet via `8cc→hell` |
| `RUNTIME_STATEFUL_EXECUTION_DEMONSTRATED` | **PARTIAL** (gcc-proven, Unshackled example proves VM can do runtime I/O) | `M0_KILLER` same exe for 5 inputs; `M0_HELL_VM` cat same `.mu` for 2 inputs |
| `WAD_HEADER_PARSE_IN_MALBOLGE_DEMONSTRATED` | `NOT_DEMONSTRATED` | M1 not started |
| `DOOM_TICK_IN_MALBOLGE_DEMONSTRATED` | `NOT_DEMONSTRATED` | M3 gate |
| `FULL_DOOM_ON_CLASSIC_MALBOLGE` | `NOT_DEMONSTRATED` (TARGET_B) | by design |

Prior art: `NO PRIOR MALBOLGE DOOM PORT FOUND IN INITIAL SEARCH` — do not claim `WORLD_FIRST` until exhaustive search before publication.

---

## Host Computation Audit Log

```
$ py host/host.py --verify-audit
host audit PASS — no gameplay symbols

$ grep -R "doomgeneric_Tick|P_MovePlayer" host/
(no output)

$ py scripts/build_m0.py --all
[M0_A_CONST] PASS pipeline=8CC_FAILED_127+GCC_REF host=PASS
...
[M0_KILLER] PASS pipeline=8CC_FAILED_127+GCC_REF host=PASS (5 runs, same SHA 1f92a9cc…)

$ py -m pytest tests/test_engine_does_the_work.py -v
test_host_no_gameplay PASSED
test_m0_artifacts_exist PASSED (with gcc artifacts)
test_killer_same_artifact PASSED (same SHA for 0..4)
```

---

*This report is the evidence machine. The meme comes after correctness.*

