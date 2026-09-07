# PUBLIC_SANITIZATION_REPORT

Date: 2026-09-02
Repo: `DannyBaanks/MALDOOM` — `master`

## Summary

MALDOOM was reframed so the public repo stands on Classic Malbolge (3^10 /
59049) alone, with all hard dependencies on private ISyCo/4D research removed.
Results were not changed; the narrative/architectural dependency on private
research was removed. `PUBLIC_SANITIZATION = DEMONSTRATED` for the current
tree; `PRIVATE_HISTORY_FOUND = YES` (see below).

## What was REMOVED

- `vendor/classic/extract.py` — one-off that read a private sibling tree
  (`C:\...\malbolge-oracle\...`). Not used at runtime.
- Absolute-path imports of the private workspace assembly Malbolge interpreter
  (`workspace/assembly/malbolge/malbolge_interpreter.py`) from all 13
  QUINE_OUTWARD_V0 scripts.
- Narrative references to `4D/holographic/` and `ISyCo` in the experiment docs.

## What was REWRITTEN

- `experiments/QUINE_OUTWARD_V0/src/*.py` → now import the vendored,
  in-repo interpreter via `src/_common.py` (repo-root-relative resolution).
- `AUDIT.md` → references repo-local vendored paths instead of the ISyCo tree.
- `CA_MODEL.md` + `src/ca_model.py` → "toroidal" replaced by explicit
  "wraparound" described from the experiment's own index arithmetic.
- `QUINE_MECHANISM.md`, `SUMMARY.md` → repo-local paths / `DannyBaanks/MALDOOM`.
- `README.md` → rewritten around Classic Malbolge, the quine-outward experiment,
  demonstrated/not-demonstrated, reproduce, evidence, limitations.
- `AGENTS.md` → standalone guard reworded to not name the private tree.

## What SURVIVED (derivable from Classic Malbolge alone)

- The vendored self-contained interpreter `vendor/malbolge/malbolge.py`
  (public Malbolge semantics: Iizawa 2005 / malbolge.c).
- The Lutter quine specimen `vendor/quines/quine_lutter.malbolge` with
  provenance (SHA `DCA8476F...`).
- All experiment results (unchanged, reproducible):
  - QUINE_MECHANISM_EXTRACTED = DEMONSTRATED (real VM reader/tape)
  - DISTINGUISHABLE_CELLULAR_STATE = DEMONSTRATED (model, N=3)
  - TWO_PRIMITIVES_COEXIST / SEAM_PRESERVES_BEHAVIOR = DEMONSTRATED (model)
  - MACROCELL_LIFTING = DEMONSTRATED (model, G=2)
  - REGENERATION_AFTER_DAMAGE = NOT_DEMONSTRATED (3/8, 0/8)
  - INPUT_TO_PERSISTENT_STATE = PARTIAL
  - CLASSIC_VM_PARITY = DEMONSTRATED (passive region 12/13)
- Existing evidence dirs (`evidence/`) — historical, not rewritten.

## Why the survivors are derivable from Classic Malbolge

- The interpreter and quine are public Malbolge artifacts (vendored with
  provenance).
- The discrete-ring model and microcell/seam/macrocell are defined entirely by
  the real `crazy` fill rule and index arithmetic on a finite ring — no private
  topology needed.
- Every claim was validated against the vendored real VM (parity, Hello World).

## Tests

- `test_host_no_gameplay` (First Law) PASS.
- M0/Unshackled pipeline tests NOT_DEMONSTRATED_IN_PUBLIC_BUILD (git-ignored
  binaries; independent of this work).
- QUINE_OUTWARD_V0 scripts exit 0 and match committed evidence JSON.

## Known limitations

- `PRIVATE_HISTORY_FOUND = YES`: commit `50316b0` (created before this audit
  ran) contains the private-path scripts and `4D/holographic` references,
  reachable from `master`. Per instructions, **no history rewrite / force-push
  was performed**. A future `filter-repo`/branch replacement is the
  maintainer's decision.
- The microcell/macrocell/seam results remain **model-level**; only the passive
  fill region is validated against the real VM, not a running Classic program.
- `FULL_DOOM` on Classic Malbolge remains NOT_DEMONSTRATED.

## Claims after sanitization

- No claim that "Malbolge is a cellular automaton" — the model is an
  experimental lens (`MALBOLGE_MEMORY_AS_CA_MODEL`), not an equivalence.
- `MALDOOM_STATE_PRIMITIVE = PARTIAL` (real reader/tape mechanism; robust
  composable unit pending).