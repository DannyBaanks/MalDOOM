# PIPELINE_E2E_V0 — Full C→EIR→HeLL→.mu→Unshackled pipeline
# Date: 2026-09-10
# Host: Windows, gcc 16.1.0, MinGW

## What was done

1. **8cc compiled with __eir__ backend** on Windows for the first time
   - Patch: conditional POSIX headers in main.c (sys/types.h, sys/wait.h, unistd.h)
   - Patch: set_output_file(stdout) in __eir__ path (was missing → NULL fp → silent crash)
   - Location: vendor/elvm/8cc/8cc.exe

2. **Full pipeline verified: C → EIR → HeLL → .mu → Unshackled VM → output**

## Pipeline steps
`
C source  →  8cc.exe (__eir__)  →  .eir
  .eir    →  elc.exe -hell      →  .hell
  .hell   →  lmfao.exe          →  .mu
  .mu     →  Unshackled.exe     →  stdout
`

## Test results

| Program | C source | VM output | Expected |
|---------|----------|-----------|----------|
| putchar(65) | putchar(65) | A | A ✅ |
| M0_A_CONST | putchar(79); putchar(75); putchar(10) | OK | OK ✅ |
| M0_B_direct | putchar(52); putchar(48); ... | 40+2=42 | 40+2=42 ✅ |

## Key findings
- 8cc __eir__ path reads C from stdin, writes EIR to stdout
- elc.exe needs -hell flag and path without spaces in cmd.exe
- LMFAO expects ASCII HeLL (not UTF-16)
- Division (__builtin_div) not in EIR builtins — needs libc
- Unshackled.exe takes .mu file as sole argument

## Fixes applied to vendor/elvm/8cc/main.c
1. Conditional POSIX includes under #ifndef __eir__
2. set_output_file(stdout) in __eir__ path

## Significance
This demonstrates the COMPLETE toolchain from C source to Malbolge Unshackled execution.
The C → EIR step that was previously claimed as "never built on this host" now works.
