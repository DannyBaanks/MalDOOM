# PUBLIC_BUILD_REPORT

Date: 2026-09-02
Repo: `DannyBaanks/MALDOOM` — `master` (after sanitization)

## Status

A clean clone of this repo is self-contained for the Classic Malbolge /
QUINE_OUTWARD_V0 work: the interpreter and quine are vendored in-repo, all
scripts resolve paths relative to the repo root, and no external/private tree
is required.

## Verification table

| PROPERTY | STATUS | EVIDENCE |
|---|---|---|
| CLASSIC_VM_SELF_CONTAINED | DEMONSTRATED | `vendor/malbolge/malbolge.py` runs Wikipedia Hello World → HALTED |
| NO_PRIVATE_IMPORTS | DEMONSTRATED | `git grep` for ISyCo/`workspace/assembly` in `src/` and `README` → empty |
| NO_PRIVATE_PATHS | DEMONSTRATED | no absolute host-specific paths in tracked source (only in historical evidence + this audit doc) |
| NO_4D_RESEARCH_DEPENDENCY | DEMONSTRATED | `git grep` for `xeno4d`/`4D/holograph`/`cell4d` in tracked non-evidence → empty |
| NO_TOROIDAL_PRIVATE_DEPENDENCY | DEMONSTRATED | "toroidal" removed from experiment; wraparound described from model semantics |
| QUINE_PROVENANCE | DEMONSTRATED | `vendor/quines/quine_lutter.malbolge` + `vendor/malbolge/PROVENANCE.md` (SHA `DCA8476F...`) |
| PASSIVE_FILL_PARITY | DEMONSTRATED | `vm_parity.py` → 12/13 passive fill cells match `crazy(mem[i-1],mem[i-2])`; 1 fill-boundary exception |
| MICROCELL_RESULT | DEMONSTRATED (model) | `microcell.py` → smallest N=3, window-1 signature 0 vs 1 |
| SEAM_RESULT | DEMONSTRATED (model) | `seam.py` → minimal seam = 1 cell preserves both signatures |
| MACROCELL_RESULT | PARTIAL (model) | `macrocell.py` → lifting works at G=2; fails at G=1/3/4 |
| ROBUST_REGENERATION | NOT_DEMONSTRATED | `regen.py` → 3/8 single-cell, 0/8 double-cell |
| INPUT_PERSISTENT_STATE | PARTIAL | `input_state.py` → distinguishable at 1000 steps, not at 100 |
| CLASSIC_VM_VALIDATION | DEMONSTRATED | model parity + vendored interpreter validated vs Hello World |
| MALDOOM_STATE_PRIMITIVE | PARTIAL | real quine reader/tape mechanism on real VM; robust composable unit pending |

## Test run

- `test_host_no_gameplay` (First Law: host must not compute gameplay) → **PASS**.
- `test_m0_artifacts_exist`, `test_killer_same_artifact`, `test_killer` →
  **NOT_DEMONSTRATED_IN_PUBLIC_BUILD**: these belong to the TARGET_A
  (Unshackled/HeLL) pipeline and require prebuilt `vendor/build/*.exe` /
  `vendor/Unshackled.exe` binaries that are git-ignored and not reproducible on
  this host. They are independent of the Classic/QUINE_OUTWARD_V0 work and of
  this sanitization.

## Reproduce (self-contained)

```bash
py vendor/malbolge/malbolge.py            # Hello World -> HALTED
cd experiments/QUINE_OUTWARD_V0/src
py microcell.py && py seam.py && py macrocell.py
py regen.py && py input_state.py && py vm_parity.py
```

All scripts exit 0 and their output matches the committed evidence JSON
(verified: duplicate/seam/input_state identical to stored results).

## Not in public build

- The M0/Unshackled runtime binaries (git-ignored; pipeline TARGET_A).
- The removed `vendor/classic/extract.py` one-off (referenced a private sibling).