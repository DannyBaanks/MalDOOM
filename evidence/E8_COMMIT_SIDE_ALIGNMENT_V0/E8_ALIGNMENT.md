# E8 — Commit-side alignment: the 119 evidence blobs Git stored without their carriage returns

Experiment `evidence/E8_COMMIT_SIDE_ALIGNMENT_V0/`, run 2026-10-15 on `master` at `b3d372b`, committed
as `61437d3`. It executes the one option E7 measured and deliberately left to the maintainer —
`E7_DISPOSITION.md` §5: *"Fixing the remaining 119 (127 minus the 8 repaired here) means re-staging 119
committed evidence files and publishing the result… the decision is Danny's"* — a decision Danny gave
the same day.

## 1. Question and scope

One question, for each sealed entry: **does what Git has committed equal the bytes the seal
describes?** Not "does the worktree equal the seal" — that is what `sha256sum -c` answers, and it had
been answering "yes" for 337 entries while the published history differed from them.

In scope: the stored side only. Out of scope, and untouched: every file on disk, every
`SHA256SUMS.txt`, every seal value, every untracked path, and every gameplay, VM, toolchain or
milestone claim.

## 2. Method

| tool | role | question it answers |
|---|---|---|
| `tools/measure.py` | read-only | classify every sealed entry as `ALIGNED` / `CR-STRIPPED` / `NOT-IN-HEAD` / `WORKTREE-NOT-SEAL` by comparing seal, worktree bytes, HEAD blob, index blob and the blob `git add` *would* create |
| `tools/restage.py` | **the only writer** | stage the worktree bytes for the candidates, under five gates, refusing anything else; then prove `SHA-256(git show :path) == seal` |
| `tools/diff_proof.py` | read-only | prove the staged content differs from HEAD by CRs and nothing else, and re-run the worktree tally |
| `E7/tools/chain_check.py` | read-only | the three-way chain repo-wide, against the index before the commit and against HEAD after it |
| `E7/tools/stored_cr_analysis.py` | read-only | E7's own acceptance test for this repair |

## 3. What was found, before touching anything

`raw/01` over 346 sealed entries in 39 manifests:

| relation | entries |
|---|---|
| `ALIGNED` — worktree == seal == HEAD | 216 |
| `CR-STRIPPED` — worktree == seal, HEAD == seal with every CR dropped | **119** |
| `NOT-IN-HEAD` — worktree == seal, never committed | 2 (`EPOCH_TRANSPARENCY_V{0,1}/program.op`) |
| `WORKTREE-NOT-SEAL` — E7's 9 irrecoverable entries | 9 |

Zero entries fell outside those four relations: no fourth mechanism is needed. The 119 match E7's
127 minus the 8 E7 restored, and the 216 match the `HEAD == seal` count E7 recorded after its own
commit. They span 25 evidence directories (`raw/02` groups them), including `M1`, `M2a` and `M3a`
artifacts whose claims rest on byte-identical output.

## 4. Why `git add` cannot fix this, measured

The first attempt used `git add -- <path>` per candidate: **restaged=0 refused=119**, every one
`REFUSED-staged-not-seal-and-unstaged` (`raw/02a_*`). The index entry for these paths carries the
worktree's own size and mtime while holding the LF blob, so Git concludes the file is clean and
stages nothing. This is the same stat-cache blindness that made `git checkout HEAD -- <path>` a
silent no-op in E6, seen from the other side: there it hid a drifted worktree, here it hides a
drifted commit.

What works is index-only: `git hash-object -w` the existing worktree bytes, then
`git update-index --cacheinfo <mode>,<blob>,<path>`. No byte and no mtime on disk is touched; a
single `git reset -q -- <path>` would undo any staged entry again. The tool keeps the mode from
`git ls-files -s` so nothing but the blob changes.

## 5. The guard

A path was staged only if all five held at the moment of staging, and each is recorded per path:

1. the path is in `raw/01`'s candidate set **and** a fresh re-measurement still classifies it
   `CR-STRIPPED` — the state had not moved between measurement and action;
2. `SHA-256(worktree bytes) == the seal` — the bytes to be stored are the sealed ones;
3. `HEAD blob == worktree with every CR dropped` and `HEAD blob != seal` — the only defect is the CRs;
4. `SHA-1("blob N\0" + worktree bytes) == git hash-object(path)` — the clean filters are identity,
   so storing cannot alter a byte (`* -text`, and `core.autocrlf` unset, `raw/09`);
5. the path is not a `SHA256SUMS.txt` — a manifest is never restaged. Zero candidates were manifests.

After staging, `SHA-256(git show :path) == seal` and `git show :path == worktree bytes` were both
required; otherwise the entry was unstaged again. Outcome: **restaged=119 refused=0** (`raw/02`).

Three further checks before the commit: the staged set was **exactly** those 119 paths and nothing
else (`raw/03`, and `git status --porcelain` showed no deletion, rename or addition); the staged
content folded back to HEAD byte for byte, i.e. the commit introduces no content that is not a CR,
and the size delta is 77,731 bytes for 77,731 changed lines (`raw/04`, matching `git show --numstat`);
and a credential scan over the 119 *staged blobs* returned 0 hits, with no candidate path matching
`env|secret|token|cred|key|pem` (`raw/06`).

## 6. Verification after the commit

| measure | before | after |
|---|---|---|
| sealed entries repo-wide | 346 in 39 manifests | **346** at `raw/07`; E8's own 16 entries in a 40th manifest make the repo total 362 (`raw/10`) |
| worktree == seal | 337 | **337** — unchanged, E8 wrote no file |
| HEAD == seal | 216 | **335** (`raw/07`) |
| three-way `worktree == seal == HEAD` | 216 | **335** (`raw/07`) |
| mismatches | 130 | **11** = E7's 9 irrecoverable + the 2 never-committed `program.op` |
| `stored_cr_analysis.py` "hypothesis holds for N entries" | 119 | **0** (`raw/08`) — E7's stated acceptance test |

The remaining 11 are exactly the entries E7 proved irrecoverable or untracked; E8 did not create
them and cannot close them without editing a manifest or inventing evidence.

## 7. What this does *not* claim

- **No content changed.** The insertions and deletions are line terminators. That is proved against
  the previous blob (`raw/04`), not asserted. The 119 files were never re-executed, so "the sealed
  program still behaves as reported" rests on the original M*/E* runs, not on this one —
  `[NOT_DEMONSTRATED]` here.
- **The published history is not rewritten.** `b3d372b` and every earlier commit still contain the
  LF renderings; they are superseded, not erased. Anyone who cloned before this commit has blobs
  that do not match the seals, and reconciling means a normal `git pull`, not a force.
- **The mechanism is still an inference.** A Windows host whose `core.autocrlf` stripped CRs on
  `git add` and re-added them on checkout best explains the three byte states and covers 127 of 127
  cases; the host is gone (`AGENTS.md` §5: the Windows disk was lost 2026-09-23). `[NOT_DEMONSTRATED]`.
- **Nothing about DOOM changed.** No ladder rung, VM number, tick or hash claim is made, moved or
  retracted by E8. `M0` status stays as E3/E4/E6/E7 recorded it.

## 8. Reproduction

```bash
cd <MALDOOM repo root>
python3 evidence/E8_COMMIT_SIDE_ALIGNMENT_V0/tools/measure.py       # read-only classification
python3 evidence/E8_COMMIT_SIDE_ALIGNMENT_V0/tools/diff_proof.py    # read-only, CR-only proof + tally
python3 evidence/E7_SEAL_DISPOSITION_V0/tools/chain_check.py HEAD   # read-only, 3-way vs HEAD
python3 evidence/E7_SEAL_DISPOSITION_V0/tools/stored_cr_analysis.py # read-only, expect "holds for 0"
# the writer is tools/restage.py; it is a no-op now — every candidate is already aligned, so a
# re-run measures them out of the candidate set and stages nothing.
```

`git add` and `git checkout HEAD --` are both no-ops for these paths and must not be used as
"fixers" here; `scripts/build_m0.py` must still never be run as a verifier (`build_m0.py:65`
overwrites sealed files in place).

Claim status: `DEMONSTRATED` — 119 committed evidence blobs were the seal minus every CR, and are
now byte-equal to the seal in HEAD, proved per path before and after the commit; `DEMONSTRATED` —
the repair changed no file on disk and no seal value; `PARTIAL` — the repo-wide chain is
335/346 three-way aligned, not 346/346, the 11 remaining entries being E7's documented set.
