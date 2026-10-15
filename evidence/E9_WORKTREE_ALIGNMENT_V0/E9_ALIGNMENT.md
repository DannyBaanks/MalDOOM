# E9 — Worktree alignment, pre-track content scan, and sealing the Sep-8 threads

Date: 2026-10-15. Repo: `/home/danny/Development/ISyCo Git/MALDOOM`, branch `master`,
parent commit `4416109` (the README refresh). Tooling: `tools/`, raw captures: `raw/`.

## 0. The request and the two decisions that shaped it

Danny's instruction was **"TRACKEA TODO Y DEJA ACTUALIZADO YA BIEN TODO"** — track the whole untracked
pile and leave the repository internally consistent. Two sub-decisions were put to him and are the
scope of this experiment, taken literally:

1. **Normalise the disk to LF** for the tracked files whose worktree differs from `HEAD` — i.e. remove
   CR from the *worktree*, so `worktree == HEAD`, with **zero commits and zero newly published bytes**
   (the E6 precedent), rather than re-staging 60 committed blobs.
2. **A dated status pass for `docs/CLAIMS.md` that promotes no label.**

Everything below is measured, and where the measurement contradicted what I had asserted earlier in the
same task, the contradiction is recorded rather than smoothed over (§3).

## 1. Baseline (`raw/01_baseline.txt`, `tools/baseline.py`)

Repo-wide, before any write: **489 tracked files, 45 manifests, 82 untracked files.**

| seal verification (worktree side) | entries |
|---|---|
| `evidence/**` (42 manifests) | 355 of 364 verify |
| `vendor/**` (3 manifests) | 10 of 10 verify |

**60 tracked files had `worktree != HEAD` while `git status` was clean** — the index stat-cache
blindness E6 and E7 described. Splitting them by relation:

| relation | count | meaning |
|---|---|---|
| `CRLF-PAIRS-EXACT` | **49** | worktree == HEAD with every `\n` turned into `\r\n`; a rule reconstructs it |
| `CR-STRIPPED` | **11** | CRs were not all inside CRLF pairs (mixed endings); only a snapshot reconstructs it |
| `OTHER` | 0 | — |

By seal status: **53 unsealed** (no manifest lists them) and **7 listed-not-verifying** — and those 7
are exactly `evidence/M0_{A_CONST,B_ARITH,C_BRANCH,D_LOOP,E_MEMORY,F_INPUT,KILLER}/SHA256SUMS.txt`, the
self-sealing manifests E7 ruled must stay byte-for-byte as they are.

`vendor/` matters here for one reason only: E6/E7/E8 scanned `evidence/` and never counted the three
`vendor/` manifests, so E9 is the first round with a repo-wide denominator.

## 2. Why the guard had to run before any write

E7 recovered seven `evidence/M0_*_UNSHACKLED_V0/source.c` from a **witness**: their sealed bytes sat
verbatim in `engine/M0_*.c`. Seven of those engine files are in this divergent set *and* in the
`CR-STRIPPED` group. If an engine file were the only local copy of those bytes, stripping its CRs would
destroy the witness. So normalisation was gated on a measurement, not on a recollection.

## 3. The guard result — and the correction it forced (`raw/02_witness_check.txt`)

`tools/witness_check.py` indexes every seal in the repo, then for each divergent path asks: do the
*worktree* bytes satisfy some seal, do the *HEAD* bytes satisfy one, and how many other files on disk
would still satisfy it after the fold.

    # manifests: 45 | distinct seals: 325 | divergent: 60
    KEEP: 0 | NORMALIZE: 60
    NORMALIZE 51 | NORMALIZE-REDUNDANT-WITNESS 8 | fold_equals_HEAD: yes for all 60

Verdict: **`KEEP: 0`.** The 8 witness files are redundant — `engine/M0_*.c` carry the same digest as
`evidence/M0_*/source.c` **and** `evidence/M0_*_UNSHACKLED_V0/source.c`, so `others=2`: E7's restore had
already put the sealed bytes back where the seal points, and the engine copy is a duplicate, not the
last copy.

Two things I had said earlier in this task were wrong and are corrected here:

* that all 60 divergences were "CR-only, reconstructible by rule" — the `or`-based test was too loose;
  the honest split is **49 by rule, 11 only from a snapshot** (`raw/01`).
* that stripping CR from `engine/M0_*.c` would destroy E7's witness — **disproved by measurement**: the
  witness is redundant (`raw/02`). The guard is what caught it; the plan was not.

The guard is still hard-coded in the writer (`FREEZE` set + `KEEP-*` verdicts) so the invariant is
enforced on every run instead of remembered.

## 4. The repair (`raw/03`, `raw/04`, `raw/07`, `tools/normalize_lf.py`)

Pre-image snapshot first (`raw/03`, 60 rows: size, CR count, worktree sha, HEAD sha, verdict), then for
each candidate the guard `sha256(fold(worktree)) == sha256(HEAD)`; write to `<name>.e9tmp` +
`os.replace()`; refusal by default.

    # dry_run=False divergent=60 normalized=53 refused=7
    REFUSED evidence/M0_{A_CONST,B_ARITH,C_BRANCH,D_LOOP,E_MEMORY,F_INPUT,KILLER}/SHA256SUMS.txt  KEEP-FROZEN-BY-E7

`raw/07` proves the blast radius in one line: of the 374 sealed entry paths in the repo, the **53
rewritten paths intersect the sealed set in 0**; the 7 refused paths are all in the sealed set. So no
sealed byte on disk changed, by construction and not by hope.

## 5. What Git then showed, and the one command that works

After the fold, `git status --porcelain -uno` listed **53 entries ` M`** while `git diff HEAD` was
**0 bytes** — stale stat cache again, the E6 signature. Two routes look equivalent and are not:

* `git add -- <the 53>` **fails**: 5 of them are under `vendor/`, which `.gitignore` ignores, and
  `git add` refuses ignored paths even when already tracked (`exit 123`).
* `git update-index -- <the 53>` is the correct tool for tracked files: it consults no ignore rule.
  After it, `git status --porcelain -uno` = **0 lines** and `git diff --cached` = **0 bytes**, i.e. the
  index was refreshed and **nothing was staged**.

So this repair costs zero commits and publishes zero new bytes; 53 of the 60 divergences are gone and
the remaining 7 are E7's frozen set by decision.

`raw/06` re-runs the E7/E8 three-way check over the same denominator: **374 entries in 45 manifests,
365 `disk == seal`, 363 three-way, 4 absent from HEAD, 11 mismatches — identical to the pre-repair
numbers.** The normalisation is chain-neutral, which is the acceptance test it was designed to pass.

## 6. `.gitignore` — a committed defect, so it does need a commit

Measured: `worktree == HEAD` for `.gitignore`, **286 bytes, 8 CR and 14 NUL in both**. It was never in
the divergent set; the corruption is in published history. The last line is a UTF-16LE encoding of
`__pycache__/` (`_\0_\0p\0y\0...`), a duplicate of the active ASCII rule on line 3, written by a Windows
tool. Replaced with a clean LF/UTF-8 file of 232 bytes that keeps every rule and drops only the duplicate
rule and the stray `doom_headless.exe` line.

Behaviour proved unchanged: `git status --porcelain -uall` before vs after differs by exactly one line
(` M .gitignore`), and `git ls-files -i -c --exclude-standard` returns the **same 20** tracked-but-ignored
paths. `vendor/*` is left in place on purpose — the README's reproducibility section depends on vendor
binaries *not* being in the clone; those 20 files are tracked from before the rule and stay tracked.

## 7. Tracking the 79 untracked files (`raw/08`, `raw/09`)

79 foreign untracked files, **13,681,119 bytes (13.68 MB)**, of which `evidence/M2_S0_INIT_UNSHACKLED_V0/
artifact.mu` is 13,116,592 B — inside existing precedent (tracked `artifact.mu` files up to ~18 MB are
already public). `tools/content_scan.py` ran **before** `git add`, because this repo's remote is public
and the operation is irreversible:

| class | hits |
|---|---|
| credential markers | **0** |
| hostname markers | **0** |
| NUL bytes / binary | **0 / 0** |
| absolute paths | **2** — both `C:\Development\ISyCo Git\…` inside `fix_imports.py` |
| private-sibling names | 137 — `Walbolge`, `Autobolge`, `Malbolge-Translator`, `Malbolge-Engine`, `ISyCo Git` |

The decisive test is whether any of this is a *new* class of disclosure. `raw/09` counts the same marker
classes already present in committed `HEAD`: `Walbolge` 2 files, `Autobolge` 8, `Malbolge-Translator` 3,
`Malbolge-Engine` 2, `ISyCo Git` 14, `C:\Development` 5. They are all already published, so tracking adds
no new disclosure class. The 2 absolute paths are a Windows `C:\` layout with no username in it.

Content being tracked (byte-for-byte, `* -text` means no conversion):

| group | files | what it is |
|---|---|---|
| `evidence/FRAGMENTS_LIB` | 18 | Classic fragment library; `FRAGMENTS_REAL/*.json` say `"verified": false` |
| `evidence/FRAGMENTS_REAL` | 10 | real-VM fragment attempts |
| `evidence/FRAGMENTS_STUBS` | 4 | `.op` stubs + specs |
| `evidence/FRAGMENTS_VERIFIED` | 2 | `ADD1_L10` |
| `evidence/M2_S0_INIT_UNSHACKLED_V0` | 10 | scoped THINGS census for M2 — **no `run.json`** |
| `evidence/STATE_TRANSITIONS` | 1 | `TICK_INC/result.json`, `found: false` |
| `evidence/EPOCH_TRANSPARENCY_V{0,1}` | 6 | each: `program.op` (verifies) + `evidence.json` (irrecoverable, E7) + its manifest, unchanged |
| `scripts/` | 16 | `search_add1_*` (5), `search_{bolge_batch,state_transition,zig_vm}.py`, `fragment_{codegen,library,real}.py`, `synthesize_fragment.py`, `ternary_capsule.py`, `test_walbolge{,2,3}.py` |
| `tools/` | 8 | PCA validators and `finalize_pca_claims.py` |
| `docs/` | 2 | `EPOCH_FRAGMENTS_SPEC.md`, `TERNARY_CAPSULE_LAYOUT.md` |
| root | 2 | `test.mal`, `fix_imports.py` |

This is blocker #2 of the ladder (Classic `ADD1` / indexed addressing), and its **negative** results.
`evidence/EPOCH_TRANSPARENCY_V{0,1}/program.op` were deliberately **not** CR-stripped: they verify their
seal as-is, and folding them would break them.

## 8. Sealing what had no seal (`raw/10`, `tools/make_manifests.py`)

Six new `SHA256SUMS.txt` (LF, sorted, **no self-entry**), 45 entries, `sha256sum -c` clean on all six.
The two `EPOCH_TRANSPARENCY_V*` manifests were **refused** — a manifest that already exists is never
rewritten (`AGENTS.md` §4). Committing these directories is what finally moves `program.op` into `HEAD`:
`raw/11` measures the pre-commit state (419 entries / 410 disk / 363 three-way / 49 absent / **56**
mismatches, the 45 new seals not yet in `HEAD`); the addendum capture holds the measured post-commit
state.

Sealing is byte identity from this commit forward. It is **not** endorsement: the tracked JSONs still say
`verified: false`, `found: false`, `epoch_transparency_pass: false`, and that is precisely what is frozen.

## 9. `docs/CLAIMS.md` — dated, and promoting nothing

Appended a `## Dated status pass — 2026-10-15` section: for every registry row, the gate as written, the
evidence that exists on disk with its path, and the residual that keeps the label down. **No row was
edited; every row stays `NOT_DEMONSTRATED`.**

The section records an unresolved conflict instead of silently resolving it: three rows are marked
`DEMONSTRATED` in the appendix of `evidence/M0_REPORT.md` (lines 248-256, 2026-09 hand-written EIR)
while the registry says `NOT_DEMONSTRATED`. Both remain on disk. `WORLD_FIRST` stays **FORBIDDEN** (the
2026-09-01 note is an *initial* search, not an exhaustive published one), and `REALTIME`, `PLAYABLE`
before M7 and `TURING_COMPLETE_CLASSIC_MALBOLGE` stay forbidden.

## 10. NOT_DEMONSTRATED / unchanged by this experiment

* **No ladder claim moved.** M0–M3 statuses, M4–M7 and `FULL_DOOM_ON_CLASSIC` are untouched here; the
  cost wall in `evidence/E3_VM_PERFORMANCE_V0/run.json` (HeLL's ~10–15 M-step fixed overhead per program
  and ~1e10–1e12 steps per Doom tick) is unaffected by repository hygiene.
* The **7** self-sealing `evidence/M0_*/SHA256SUMS.txt` still fail their own line, on disk and in `HEAD`,
  and stay that way per E7.
* The **2** `EPOCH_TRANSPARENCY_V{0,1}/evidence.json` are irrecoverable: their sealed bytes exist in no
  worktree file and in no blob. Tracking the directory commits the *current* bytes, which do not match
  the old seal; the failure remains visible, it is not repaired.
* `fix_imports.py` is tracked for the record and is **not** runnable here: it rewrites the tracked
  `tests/test_epoch_transparency_v2.py` and hardcodes absent Windows sibling paths. Same class of hazard
  as `scripts/build_m0.py:65`, which writes into sealed `evidence/<M0_*>/` directories.
* Whether the Sep-8 fragment work is *correct* is out of scope for E9; only its bytes are now canonical.

## 11. Reproduce

```bash
cd "/home/danny/Development/ISyCo Git/MALDOOM"
python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/baseline.py           # raw/01 shape
python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/witness_check.py      # raw/02 guard
python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/normalize_lf.py --dry-run   # refuses, writes nothing
python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/content_scan.py       # raw/08 scan
python3 evidence/E9_WORKTREE_ALIGNMENT_V0/tools/chain_check.py --group all   # raw/06 / raw/11
```
