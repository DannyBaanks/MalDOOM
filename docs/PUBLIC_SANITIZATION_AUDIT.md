# PUBLIC_SANITIZATION_AUDIT

Date: 2026-09-02
Repo: `DannyBaanks/MALDOOM` (public) — `master`
Goal: classify every dependency on private ISyCo/4D/toroidal research so the
public repo stands on Classic Malbolge (3^10 / 59049) alone.
Classification legend: `KEEP` | `REWRITE_NEUTRAL` | `REMOVE` | `PRIVATE_DEPENDENCY` | `UNCERTAIN`.

## Summary

The public repo is mostly self-contained. The **only hard runtime dependency on
private machinery** is in the QUINE_OUTWARD_V0 experiment scripts, which import
the ISyCo workspace assembly interpreter
(`workspace/assembly/malbolge/malbolge_interpreter.py`) by absolute, host-specific path.
Everything else is doc/reference language that must be reframed or kept as
historical evidence.

---

## 1. QUINE_OUTWARD_V0 experiment — `experiments/QUINE_OUTWARD_V0/`

The experiment (mechanism extraction, microcell, seam, macrocell, regen,
input-state, VM parity) contains real, reproducible Classic Malbolge findings.
But its scripts and a few docs leak private research.

### Scripts `src/*.py` — PRIVATE_DEPENDENCY (hard)

13 scripts import the ISyCo workspace assembly interpreter
(`workspace/assembly/malbolge/malbolge_interpreter.py`) by absolute host path,
and read the quine (`workspace/assembly/malbolge/quine_lutter.malbolge`) the
same way.

Files: `ca_model.py, duplicate.py, input_state.py, macrocell.py, mechanism.py,
microcell.py, odometer.py, perturb.py, regen.py, regions.py, seam.py,
src_pointer.py, vm_parity.py`.

Action: `REWRITE_NEUTRAL` — vendor a minimal Classic Malbolge interpreter
*inside* the repo (the semantics are public: Iizawa 2005 / malbolge.c), and a
copy of the quine source with provenance, so a clean clone reproduces without
ISyCo.

### `AUDIT.md` — PRIVATE_DEPENDENCY (narrative)

- Line "Root: `<absolute path to the private workspace's assembly/malbolge dir>`"
- Section "Files found — ISyCo (reusable machinery)"
- References `4D/holographic/malbolge_fast/` and
  `4D/holographic/COMPARATIVA_HOST_VS_MALBOLGE.md`

Action: `REWRITE_NEUTRAL` — the audited files become vendored-in-repo; rewrite
the audit to reference repo-local paths only. Keep the quine provenance
(public: Lutter quine).

### `CA_MODEL.md` / `SUMMARY.md` — REWRITE_NEUTRAL

- `CA_MODEL.md` calls the model "toroidal, mod N" (line 12) and "geometry of
  the toroidal" (line 35).
- `SUMMARY.md` gives "Repo:" as an absolute local path instead of the repo name.

Action: `REWRITE_NEUTRAL` — describe wraparound from the experiment's own
semantics ("memory indices modeled with explicit wraparound"), not as inherited
torus theory. Repo path → `DannyBaanks/MALDOOM`.

### `src/ca_model.py` — REWRITE_NEUTRAL

- `(radius-2, toroidal)` comment.
- Absolute import path.

Action: `REWRITE_NEUTRAL` — "radius-2 with wraparound" + repo-local import.

---

## 2. `AGENTS.md` — KEEP / REWRITE_NEUTRAL

Line 17: "Do NOT integrate with ISyCo, `workspace/assembly`, or `MalboGost`
yet. This repo is standalone." — This is a **negative/guard** statement, not a
dependency. KEEP the intent. Minor: it is the only mention of ISyCo in the
contract; harmless as-is, but can be rewritten to "this repo is standalone" to
be fully clean.

---

## 3. `evidence/` — mostly KEEP (historical), some REWRITE_NEUTRAL

### `DOOM_NATIVE_BASELINE/` — KEEP (historical raw evidence)
- `baseline_report.md`, `launch_command.txt` contain the local command line
  (originally recorded with the host-local absolute path to the repo checkout;
  sanitized to repo-relative `./doom_native_win.exe ...`). This is a real
  historical run command. KEEP as evidence (it was produced here).

### `M0_REPORT.md` — KEEP (historical evidence)
- Lines 180-185 are the WSL build command used at the time (with local paths).
  Historical evidence. KEEP. Add note if needed that paths were host-local.

### `CLASSIC_ANCHOR_SMOKE_V0/` — KEEP (historical), note supersession
- `gost.c:19` "verified against malbolge-oracle (Python)" — historical note.
- `INTERPRETER_LOCK.json` lists `malbolge-oracle (local)`. Historical lock.
  KEEP as historical; the vendored `vendor/classic/oracle.py` is the
  self-contained public control.

### `*_REPORT.md` (M0, etc.) — KEEP
- Do not rewrite raw evidence to fit the new narrative.

---

## 4. `vendor/classic/oracle.py` — KEEP (self-contained)
Implements Malbolge from the public Iizawa (2005) pseudocode / malbolge.c, MIT.
No private dependency. This is the legitimate public control interpreter.

## 5. `vendor/classic/extract.py` — REMOVE (private one-off)
Reads `test_oracle.py` from the private sibling repo `malbolge-oracle`. It was
a one-off to regenerate `hello.mal`. Not needed at runtime.
Action: `REMOVE` from public (or move to `tools/legacy/` with a neutral note;
it is a tiny extractor, safer to remove).

## 6. `vendor/classic/gost.c` — KEEP (public C), note only
gost.c is a vendored public Malbolge interpreter (C). Only a comment mentions
malbolge-oracle. KEEP the C; the comment is historical.

---

## 7. Paths / names summary

| Term | Where | Class |
|---|---|---|
| absolute host path into ISyCo `workspace/assembly/` | QUINE_OUTWARD_V0/src/*.py | PRIVATE_DEPENDENCY → fix |
| `4D/holographic/...` | QUINE_OUTWARD_V0/AUDIT.md | PRIVATE_DEPENDENCY (narrative) → rewrite |
| `toroidal / torus / topology` | QUINE_OUTWARD_V0/CA_MODEL.md, src/ca_model.py | REWRITE_NEUTRAL |
| `ISyCo` (as standalone repo name) | AGENTS.md:17, M0_REPORT.md:4 | KEEP (guard/historical) |
| `malbolge-oracle` | vendor/classic/extract.py, gost.c comment, INTERPRETER_LOCK | REMOVE (extract.py) / KEEP (historical note) |
| absolute local checkout path (local run cmds) | evidence/, M0_REPORT.md | KEEP (historical evidence) |

## 8. Not found (search term sweep)

`xeno4d`, `cell4d`, `bactelang`, `holograph` → **no content hits** in tracked
text (only false positives in SHA256SUMS hashes). No 4D machinery was ever
committed to this repo. Good.

## 9. GIT HISTORY — PRIVATE_HISTORY_FOUND = YES

The QUINE_OUTWARD_V0 experiment was committed (as `50316b0`, created during
this sanitization session, on `master` — the current HEAD branch) **before**
the sanitization audit ran. That commit contains private-path references:

- 13 scripts import the private workspace assembly interpreter
  (`workspace/assembly/malbolge/malbolge_interpreter.py`) by absolute path and
  read the quine from the same private tree.
- `AUDIT.md` references `4D/holographic/` (private research) and the ISyCo tree.
- `QUINE_MECHANISM.md` references `workspace/assembly/malbolge`.

Commit: `50316b0`
Accesible: YES — reachable from `master` (HEAD) and no branch/force-push has
been performed. Per instructions, **no history rewrite was done**. A future
`filter-repo`/branch replacement is a decision for the maintainer.

The sanitization below fixes the *current* tree; the old path remains
recoverable from `50316b0` until history is rewritten.

## Verdicts

PRIVATE_HISTORY_FOUND = YES
PUBLIC_SANITIZATION = NOT_DEMONSTRATED (work pending)
Hard private dependency: 13 scripts import ISyCo interpreter.