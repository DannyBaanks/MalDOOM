# Claims Registry

| Claim | Gate | Status |
|---|---|---|
| `MALBOLGE_UNSHACKLED_EIR_PIPELINE_DEMONSTRATED` | M0_A–F + KILLER all PASS, host audit PASS | NOT_DEMONSTRATED (until M0_REPORT) |
| `RUNTIME_STATEFUL_EXECUTION_DEMONSTRATED` | M0_KILLER same `.mu` gives correct output for 3+ unseen `n` without recompilation | NOT_DEMONSTRATED |
| `WAD_HEADER_PARSE_IN_MALBOLGE_DEMONSTRATED` | M1 bytes→fields inside VM hash vs C parser | NOT_DEMONSTRATED |
| `DOOM_STATE_INIT_DEMONSTRATED` | M2 S_0 hash vs C | NOT_DEMONSTRATED |
| `DOOM_TICK_IN_MALBOLGE_DEMONSTRATED` | M3 H(S_{t+1}) equality vs C reference | NOT_DEMONSTRATED |
| `FRAMEBUFFER_EQUIVALENCE_DEMONSTRATED` | M5 pixel hash | NOT_DEMONSTRATED |
| `MULTITICK_EXECUTION_DEMONSTRATED` | M6 N ticks stable | NOT_DEMONSTRATED |
| `PLAYABLE_DEMONSTRATED` | M7 E1M1 technically playable | NOT_DEMONSTRATED |
| `FULL_DOOM_ON_CLASSIC_MALBOLGE` | — | NOT_DEMONSTRATED (TARGET_B) |
| `WORLD_FIRST / FIRST_DOOM_ON_MALBOLGE` | exhaustive prior-art search | FORBIDDEN until published search |

Initial search (2026-09-01): `NO PRIOR MALBOLGE DOOM PORT FOUND IN INITIAL SEARCH` — via web search ELVM/Malbolge/Unshackled/Doom combos. Not a world-first claim.

Promotion rule: a claim moves from `NOT_DEMONSTRATED` → `DEMONSTRATED` only with `evidence/` dir containing source, artifact, HeLL, command, stdout/stderr, exit code, wall time, SHA-256, expected vs observed, host audit.

Forbidden: `REALTIME`, `PLAYABLE` before M7, `TURING_COMPLETE_CLASSIC_MALBOLGE`.

---

## Dated status pass — 2026-10-15 (appended; no row above was changed and no label was promoted)

Written against the artifacts on disk, not against earlier prose. The table keeps every row at
`NOT_DEMONSTRATED`, and that is a measured fact about *this file*, not about the evidence: three of its
rows are labelled `DEMONSTRATED` in the appendix of `evidence/M0_REPORT.md` (lines 248-256, the 2026-09
hand-written-EIR section). The registry and that report disagree. Both statements stay on disk and the
disagreement is recorded here instead of being resolved by editing either one — promoting a label here
needs a new `evidence/` run plus an explicit decision (`AGENTS.md` §9).

| Claim | Gate as written | What exists on disk, 2026-10-15 | What still keeps it down |
|---|---|---|---|
| `MALBOLGE_UNSHACKLED_EIR_PIPELINE_DEMONSTRATED` | M0_A–F + KILLER PASS + host audit PASS | 7/7 hand-written EIR programs ran in the real Unshackled VM (`evidence/M0_*_UNSHACKLED_V0/`, 2026-09). The full `C→EIR` edge with real `8cc` ran on Windows for **3** programs (`evidence/PIPELINE_E2E_V0/SUMMARY.md`, 2026-09-10) and the toolchain was reproduced on Linux in `evidence/E1_TOOLCHAIN_LINUX_MIGRATION_V0/` + `evidence/E2_TOOLCHAIN_REPRODUCIBILITY_V0/` | `8cc` never produced EIR for the 7 M0 programs; the claim as named covers the pipeline, so the hand-EIR substitution falls inside its scope |
| `RUNTIME_STATEFUL_EXECUTION_DEMONSTRATED` | same `.mu`, 3+ unseen `n`, no recompile | `evidence/M0_KILLER_UNSHACKLED_V0/`: one `.mu` for 5 inputs, outputs `n*2+1` correct, state carried in-VM | nothing at artifact level; the label is held by the row above and by the registry/report split |
| `WAD_HEADER_PARSE_IN_MALBOLGE_DEMONSTRATED` | bytes→fields inside VM, hash vs C | `evidence/M1_WAD_HEADER_UNSHACKLED_V0/`: `IWAD / 1264 / 4175796`, byte-identical to the C reference | the host hex-frames the 12 header bytes (Unshackled stdin is UTF-8-gated) and is blind to content — transport, but a documented deviation from a literal "bytes→fields" reading |
| `DOOM_STATE_INIT_DEMONSTRATED` | M2 `S_0` hash vs C | pilot only: `evidence/M2A_LUMP_FIND_UNSHACKLED_V0/` (lump addressing over 4 real directory records, same `.mu`) and the census `evidence/M2_S0_INIT_UNSHACKLED_V0/`, which has no `run.json` and no `SHA256SUMS.txt` | no `S_0` hash has ever been produced; `getc` ≈ 2 s/byte bounds the bulk path |
| `DOOM_TICK_IN_MALBOLGE_DEMONSTRATED` | `H(S_{t+1}) == H(S_t)_C` | pilot only: `evidence/M3A_P_RANDOM_UNSHACKLED_V0/` (the real `P_Random`, 3 ticks × 8 draws, byte-identical to C, state carried across ticks) | EIR is 24-bit against Doom's 32-bit fixed point; `evidence/E3_VM_PERFORMANCE_V0/run.json` measures ~1e10–1e12 steps per tick, i.e. hours per tick, plus a ~10–15 M-step fixed HeLL overhead per program |
| `FRAMEBUFFER_EQUIVALENCE_DEMONSTRATED` | M5 pixel hash | nothing on the Malbolge side; the C baseline exists (`evidence/DOOM_NATIVE_BASELINE/`, frames 35/70/105/150) | no in-VM framebuffer has ever been produced |
| `MULTITICK_EXECUTION_DEMONSTRATED` | M6 N ticks stable | nothing | the full M3 tick is its prerequisite |
| `PLAYABLE_DEMONSTRATED` | M7 E1M1 technically playable | nothing | forbidden before M7 |
| `FULL_DOOM_ON_CLASSIC_MALBOLGE` | — | `evidence/PURE_CONTINUATION_ANCHOR_V0/` PASS (R1–R9) is a TARGET_B continuation anchor, not a Doom state; `CLASSIC_ANCHOR_PRIMITIVE` has no `program_v1.mal` | `NOT_DEMONSTRATED` **by design** — 3^10 = 59049 cells is bounded; also blocked on ADD1 and indexed addressing, both `NOT_DEMONSTRATED` |
| `WORLD_FIRST / FIRST_DOOM_ON_MALBOLGE` | exhaustive prior-art search | the 2026-09-01 line above is an *initial* search | stays **FORBIDDEN**: no published exhaustive search exists |

`REALTIME`, `PLAYABLE` before M7 and `TURING_COMPLETE_CLASSIC_MALBOLGE` remain forbidden.

Integrity context for every path cited above: the seal chain is measured in
`evidence/E6_SEAL_INTEGRITY_V0/`, `E7_SEAL_DISPOSITION_V0/`, `E8_COMMIT_SIDE_ALIGNMENT_V0/` and
`E9_WORKTREE_ALIGNMENT_V0/`. Repo-wide as of 2026-10-15, after E9: 52 manifests, 441 sealed entries,
432 verify against the worktree and **432 satisfy `worktree == seal == HEAD`** (0 entries absent from
`HEAD`). The 9 remaining mismatches are E7's documented irrecoverable set — 7 self-sealing
`evidence/M0_*/SHA256SUMS.txt` (no bytes can satisfy a line that hashes its own file) and the 2
`evidence/EPOCH_TRANSPARENCY_V{0,1}/evidence.json`, whose sealed bytes exist in no worktree file and in
no blob; those directories are now tracked, so the current bytes are published and the failure stays
visible rather than repaired.
