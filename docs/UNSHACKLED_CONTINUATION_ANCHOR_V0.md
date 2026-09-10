# UNSHACKLED_CONTINUATION_ANCHOR_V0

## Claim

One uninterrupted Malbolge Unshackled VM execution emits `A -> B -> C` and
terminates with exit 0 on empty stdin. The demonstrated scope is the
ELVM-generated `ABC.mu` artifact: one `Unshackled.exe` process, no input,
no host state injection, observed output exactly `ABC`.

This is a TARGET_A (Malbolge Unshackled) micro-experiment, not a MALDOOM
M0-M7 milestone and not an integration into any Doom runtime. It must not be
cited as evidence for Full Doom, TARGET_B, or a host-computation claim.
It is the Unshackled counterpart of `PURE_CONTINUATION_ANCHOR_V0`, kept as a
separate experiment with separate artifacts: no Classic hash is reused here.

Receipt level is deliberately **black-box**: process exit code, captured
stdout/stderr, wall time, SHA-256. There is no step tracer for Unshackled on
this host, so phase boundaries, memory hashes, and perturbation controls are
`NOT_DEMONSTRATED` (see § NOT_DEMONSTRATED).

## Toolchain

| Component | Identity | SHA-256 |
|---|---|---|
| `vendor/Unshackled.c` | Lutter Unshackled VM source | `D772B096E925A0F32AC283E59E666BCCCC4B5FEBC2287FD1E0D2BBBB9372C3A7` |
| `vendor/Unshackled.exe` | built from the above | `818EBD42729686D507FC60C0DABD1B5F5A840D4E9AF3D0B3B2682310AA487A46` |
| `vendor/LMFAO/bin/lmfao.exe` | LMFAO v0.1.5 assembler | `350FB581F014D6913BD3C3A0BA86A6342E01A47DD9A2C1C3583225A348F33240` |
| `vendor/elvm/out/elc.exe` | ELVM EIR→HeLL, built on this host (see command) | `A64B20487B12D42246C12A2D20790451DC990027D58E9B6558C4F03E3C5E0A39` |

`elc.exe` build (executed 2026-09-10, exit 0):

```powershell
cd "C:\Development\ISyCo Git\MALDOOM\vendor\elvm"
gcc -std=gnu99 -O2 -w -I. -o out\elc.exe ir\ir.c ir\table.c target\*.c
# EXIT=0
```

Compiler: `gcc.exe (MinGW-W64 x86_64-ucrt-posix-seh, built by Brecht Sanders, r4) 16.1.0`.
The `UINT_MAX` redefinition warning from `ir/ir.h` is pre-existing upstream
behavior and does not affect the `hell` backend output.

## Sources

Hand-written ELVM IR (EIR). Verbatim contents:

```text
--- A.eir ---
putc 65
exit
--- AA.eir ---
putc 65
putc 65
exit
--- AB.eir ---
putc 65
putc 66
exit
--- ABC.eir ---
putc 65
putc 66
putc 67
exit
```

## Generation

EIR → HeLL was executed with raw-byte capture (see trap T1):

```powershell
py -c "import subprocess, pathlib
tmp = pathlib.Path(r'<work>\unshackled_pca')
elc = r'C:\Development\ISyCo Git\MALDOOM\vendor\elvm\out\elc.exe'
r = subprocess.run([elc, '-hell', str(tmp / 'ABC.eir'))], capture_output=True)
open(tmp / 'ABC.hell', 'wb').write(r.stdout)"
# returncode=0, stdout_len=28384, stderr_len=0
```

HeLL → `.mu` assembly:

```powershell
& "C:\Development\ISyCo Git\MALDOOM\vendor\LMFAO\bin\lmfao.exe" <work>\ABC.hell -o <work>\ABC.mu
# Malbolge Unshackled code written to <work>\ABC.mu ; LMFAO_EXIT=0
```

## Artifacts

Evidence dir: `evidence/UNSHACKLED_CONTINUATION_ANCHOR_V0/`
(`run.json` + `SHA256SUMS.txt`, 13 files, `SHA256SUMS_VALID=True`).

| Program | `.eir` SHA-256 | `.hell` (bytes / SHA-256) | `.mu` (bytes / SHA-256) | Output |
|---|---|---|---|---|
| A | `c3924496…ad30` | 27606 / `74dddbf6…c3955cde8` | 1122005 / `760c0fec…0016c23` | `A` |
| AA | `e74b6c28…cc52c` | 27995 / `a4195c34…259b48c7` | 1140241 / `4b96af20…6a8f600` | `AA` |
| AB | `f0c23bb1…85a09` | 27995 / `daba00f6…10aa5a9ed406` | 1140241 / `6447233b…beb6cb2b` | `AB` |
| ABC | `1c80e709…361034` | 28384 / `7563664a…f2a5cfb0a` | 1161109 / `16c5cea6…cbcd6c792` | `ABC` |

(Full hashes in `SHA256SUMS.txt`. Prefixes above are unambiguous within the file.)

## Runs

One process per program, empty stdin, observed via `run.json` generation
(2026-09-10):

```powershell
"" | & vendor\Unshackled.exe evidence\UNSHACKLED_CONTINUATION_ANCHOR_V0\<NAME>.mu
```

| Program | Observed stdout | stderr | Exit | Wall (s) | Verdict |
|---|---|---|---|---|---|
| A | `A` | empty | 0 | 1.60 | PASS |
| AA | `AA` | empty | 0 | 1.93 | PASS |
| AB | `AB` | empty | 0 | 1.72 | PASS |
| ABC | `ABC` | empty | 0 | 2.03 | PASS |

Stability: `ABC.mu` was additionally run 3× with >1 s gaps (distinct
`srand(time(NULL))` seeds inside the VM) before freezing: 3/3 `ABC`,
exit 0, walls 1.94 / 2.16 / 2.69 s. The ELVM HeLL prologue absorbs the
randomized initial rotation width (10–15) and growth policy.

"HALT" here means the black-box receipt: exit code 0 with empty stderr.
No internal halt-opcode trace is claimed.

## Negative probe: Classic transfer fails

The Classic `ABC.mal` from `PURE_CONTINUATION_ANCHOR_V0` (which yields
`ABC`, halted, 235 steps on the Classic Zig engine) does **not** transfer:

```powershell
"" | & vendor\Unshackled.exe evidence\PURE_CONTINUATION_ANCHOR_V0\programs\ABC.mal
# observed stdout: AB ; stderr: invalid unicode codepoint ; exit: 1
```

Stable 8/8 across rapid and >1 s-spaced runs. Sibling results under the
same probe: `AA` → `AA` exit 0 (5/5), `AB` → `AB` exit 0 (5/5),
`AAB` → `AAB` exit 0, `A` → empty + codepoint error, `ABA` → empty +
codepoint error. Transfer is program-dependent, not universal.

Root causes (read in `vendor/Unshackled.c`):

1. **OUT semantics differ.** Classic OUT emits `a % 256` unconditionally.
   Unshackled OUT (`case 5`, `print_utf8`) requires `a` to be a valid
   Unicode scalar (`head == T0`, value `< 0x110000`); otherwise the VM
   prints `invalid unicode codepoint` and exits 1. A Classic program that
   leaves a non-codepoint value in `a` at an OUT step dies on Unshackled.
2. **Rotation width is randomized per boot** (`rotwidth = 10 + rand() % 6`,
   plus growth slack/step/probability under `srand(time(NULL))`).
   Classic `.mal` programs carry no width-probing prologue, so even
   surviving programs are at the mercy of the draw; ELVM-generated HeLL
   carries one, which is why the `.mu` family above is seed-stable.

This probe is recorded in `run.json` as `CLASSIC_ABC.mal_under_Unshackled`
with `match: true` against expectation `NOT_TRANSFERABLE`.

## Verification

```powershell
cd C:\Development\ISyCo Git\MALDOOM
py -c "import json,pathlib,hashlib
ev = pathlib.Path('evidence/UNSHACKLED_CONTINUATION_ANCHOR_V0')
rec = json.loads((ev/'run.json').read_text())
print([(r.get('program'), r['match']) for r in rec['runs']])
ok = True
for line in (ev/'SHA256SUMS.txt').read_text().splitlines():
    h, name = line.split('  ')
    if hashlib.sha256((ev/name).read_bytes()).hexdigest() != h:
        ok = False; print('MISMATCH', name)
print('SHA256SUMS_VALID=', ok)"
# [(A, True), (AA, True), (AB, True), (ABC, True), (CLASSIC_ABC.mal_under_Unshackled, True)]
# SHA256SUMS_VALID= True
```

Re-running any `.mu` under `vendor/Unshackled.exe` with empty stdin must
reproduce its exact output with exit 0 (allow ~1–4 s wall variance).

## Traps

- **T1 — PowerShell `>` writes UTF-16.** Redirecting `elc.exe` stdout with
  `>` produced a 56770-byte `.hell` starting with `FF FE` (BOM); LMFAO
  rejected it with `syntax error ... at line 1 column 1`. The fix is
  raw-byte capture (Python `subprocess` + `'wb'` write, or `cmd /c`
  redirection). The valid `ABC.hell` is 28384 bytes starting with `.DATA`.
  Cost: one failed assembly + hex-dump diagnosis.
- **T2 — `srand(time(NULL))` hides nondeterminism from rapid re-runs.**
  Five back-to-back runs share the same seed and prove nothing about
  width stability. Re-runs that matter must be spaced >1 s apart.
- **T3 — `Out-String` appends a newline.** An early `ABC` capture showed
  `ABC\n`; the VM emits exactly `ABC` (3 bytes). Byte-level comparison in
  `run.json` uses the raw captured stdout, not the PowerShell rendering.
- **T4 — Classic `.mal` ≠ Unshackled `.mu`.** Same charset, different
  machine. Never run one through the other's VM and call a mismatch a
  regression; the mismatch is the expected TARGET separation (see probe).

## NOT_DEMONSTRATED

- Residual-state causality: no Unshackled step tracer exists on this host,
  so `perturb`-style controls, per-phase memory hashes, and any claim of
  the form "state S_k is causally necessary" are `NOT_DEMONSTRATED`.
- Dynamic flow map / anchor isolation: no `trace-jsonl` equivalent for
  Unshackled; `R5`/`R8`-style graph claims are `NOT_DEMONSTRATED`.
- Independent-engine agreement: the Haskell reference
  (`vendor/Unshackled.hs`) was not executed (GHC not probed); agreement
  between Classic engines and Unshackled is explicitly *not* expected.
- Anything beyond constant output: loops, input, memory use, and Doom
  mapping remain `NOT_DEMONSTRATED` on TARGET_A.

## Claims

| Claim | Status | Evidence |
|---|---|---|
| `ABC_single_vm_A_B_C_HALT` | PASS (black-box) | `run.json`: `ABC.mu` → `ABC`, exit 0, empty stderr, empty stdin |
| `family_A_AA_AB_ABC` | PASS (4/4 single-VM) | `run.json` runs 1–4 |
| `classic_transfer` | NOT_TRANSFERABLE | `run.json` probe 5: Classic `ABC.mal` → `AB` + codepoint error, exit 1 |
| `causal_perturb_controls` | NOT_DEMONSTRATED | no Unshackled tracer |
| `dynamic_flow_map` | NOT_DEMONSTRATED | no `trace-jsonl` for Unshackled |
| `haskell_reference_crosscheck` | NOT_DEMONSTRATED | GHC not probed |
| `FULL_DOOM_ON_UNSHACKLED` | NOT_DEMONSTRATED | out of scope for V0 |
