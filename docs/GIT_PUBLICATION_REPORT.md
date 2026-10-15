# GIT_PUBLICATION_REPORT.md

Closure of Git ownership for MALDOOM and malbolge-lisp-forensics.
Executed 2026-10-15 on host Ubuntu 24.04, git user Danny, gh account `DannyBaanks` (token scopes `repo`, HTTPS).
Every number below was measured in this session; nothing is carried over from a previous report.

## Repository 1 — MALDOOM

Branch:
`master` (local `0dd01df`), upstream `origin/master`.

Remote:
`origin https://github.com/DannyBaanks/MALDOOM.git` — **public**, `protected=false`, Danny is `admin`.
GitHub answers a rename redirect: the repository now lives at `DannyBaanks/MalDOOM`. The local remote URL was
**not** changed (out of authorization).

Commits:
**8 commits were published, not 3.** The named work was E5 + E6, but a branch push necessarily carries every
ancestor, and the local branch was ahead by 8:

| commit | subject |
|---|---|
| `0dd01df` | E6: seal-integrity audit of every evidence manifest, and repair of the 32 drifted files |
| `9ffd3a6` | E5: the loader, not the epochal semantics, breaks LMFAO images on fixed-19 engines |
| `1660819` | E4: pinned Unshackled VM config — E3 step counts reproduced |
| `36fc274` | E3: Unshackled VM performance on Linux |
| `e442a68` | E1b+E2: LMFAO rebuilt on Linux; sealed M0_KILLER artifact reproduced |
| `231998f` | E1: migrate toolchain to Linux |
| `534d6dd` | fix(gitattributes): disable EOL conversion, not force LF |
| `58a3473` | chore: normalize line endings to LF (mechanical) + .gitattributes |

The five pre-existing commits were reviewed here at range level (they were authored by earlier sessions of this
project, none by another person or agent): 0 secret patterns, 0 sensitive filenames, 0 binary blobs added, largest
added blob is a text file. `E5` = 23 files/+1,566 lines, all under `evidence/E5_LOADER_WHITESPACE_V0/`.
`E6` = 14 files/+1,795 lines, all under `evidence/E6_SEAL_INTEGRITY_V0/`. No new commits were created and no
commit was amended; the existing ones already represent the authorized work.

**The 32-file repair is correctly attributed:** it is not in `0dd01df`'s diff. The repair made the worktree equal
`HEAD`, so there was nothing to commit; `0dd01df` contains only the E6 directory (including `REPAIR_EXECUTED.md`,
which records it).

Checks:
- **A Reproducibility** — PASS. `src/bolge19/main.zig` on disk `sha256 47758a3f…` equals the `source_sha256` recorded
  in the sealed `raw/01_build.txt`; rebuild `zig build-exe -O ReleaseFast … -lc` (zig 0.16.0) yields binary
  `2cae851d…`, byte-identical to the sealed `binary_sha256`.
- **B Parity** — PASS 5/5 against MALDOOM's untouched sealed `artifact.mu` (`3b9bdf37…`):
  `310a/330a/350a/370a/390a` at steps `8623625 / 9171949 / 9725624 / 10254258 / 10820576`; `diff` against the sealed
  `raw/05_mu_canonical_matrix.txt` empty. Raw-loader control still emits `02ce`. Determinism 3/3 identical.
- **C Drift** — PASS 32/32. `disk == seal == HEAD` for all 32 rows of `drift_snapshot.tsv`; 160,982 bytes on disk.
- **D Pending** — PASS. Repo-wide `sha256sum -c` over all 33 manifests: **284 entries verify, 17 fail**, the same
  17 as before the push; latest mtime among them is 2026-09-09 21:58:23 (the Windows bulk event), proving none of
  them was touched here.
- **E Secrets** — PASS. Per-commit and per-range scans for `api_key|secret|passwd|password|PRIVATE KEY|ghp_|
  github_pat_|AKIA|xox[bp]-|Bearer …|ssh-rsa` → 0 hits; sensitive filenames → 0.
- **F Worktree** — PASS. `git status` = 29 `??`, 0 ` M`, 0 staged. No bridge lease is currently live
  (330 leases, 0 with `ts+ttl > now`; none mentions MALDOOM or forensics), so no concurrent agent owned these paths.

Push:
`git push origin master` — normal, no flags, fast-forward `13d2255..0dd01df`, rc 0. Nothing was forced, no tag, no
release, no other branch, remote unchanged.

Remote HEAD:
`refs/heads/master = 0dd01dfdaddd93de332be8a7c758f56d2811952f` confirmed three ways: `git ls-remote origin`,
refreshed `origin/master` tracking ref, and GitHub API `branches/master`. `git status -sb` reports
`## master...origin/master` with no ahead/behind. `pushed_at=2026-10-15T13:54:49Z`.
CI: **consulted, none exists** — `check-runs` for `0dd01df` = 0. Publication is not a test pass.

Remaining changes:
29 untracked paths preserved exactly as found (`evidence/{EPOCH_TRANSPARENCY_V0,V1,FRAGMENTS_LIB,FRAGMENTS_REAL,
FRAGMENTS_STUBS,FRAGMENTS_VERIFIED,M2_S0_INIT_UNSHACKLED_V0,STATE_TRANSITIONS}`, `scripts/search_add1_*.py`,
`scripts/fragment_*.py`, `fix_imports.py`, `docs/{EPOCH_FRAGMENTS_SPEC,TERNARY_CAPSULE_LAYOUT}.md` and the rest of
the Sep-8 pile). They are user data, not disposable, and were deliberately not added to any commit.

Risks:
- **Public disclosure, irreversible.** `origin/master` previously exposed no `/home/*` path and no hostname. The 8
  published commits add **28 lines containing `/home/danny` across 11 files** and the hostname **`DannyISyCo` in 3
  files** (`E4/raw/00_environment.txt`, `E4/run.json`, `E5/run.json`), plus kernel/gcc fingerprints. This is
  intentional per MALDOOM `AGENTS.md` §6 ("Record: timestamp · environment …"), and it cannot be removed without
  rewriting sealed evidence or force-pushing history — both forbidden here. Flagged, not silently accepted.
- The remote name is now `MalDOOM`; the old URL works via redirect but a future `git remote set-url` will be needed
  if the redirect is ever retired. Not done here.
- `master` is unprotected: anyone with admin can force-push it. No action taken.
- The 17 failing seals are now public as failing. They remain Danny's decision (§6 of this tasking: not repaired,
  not normalized, not deleted, not committed).

## Repository 2 — Forensics

Branch:
`main` (local `a0ce164`), upstream `origin/main`. Single branch in the repo.

Remote:
`origin https://github.com/DannyBaanks/MalbolgeLispForensics.git` — **public**, `protected=false`, Danny is `admin`.

Commits:
1 published: `a0ce164` "feat(bolge19): canonical Whitespace-skipping loader + evidence for the LMFAO .mu break" —
23 files, +669/−2: `src/bolge19/main.zig` (+47/−2), 4 doc appends (`ARCHITECTURE`, `CLAIMS`, `NOT_DEMONSTRATED`,
`REPRODUCTION`), `evidence/loader_convention_v1/{FINDINGS.md,capture.sh,raw/01..12,tools/{census,manifest_cause}.py}`
and `evidence/hashes/loader_convention_v1.sha256`. All 23 files are `text/*`; **no binary, no `*.mb` specimen**
(respects `AGENTS.md` rule 6: large specimens referenced by SHA-256, never redistributed). Append-only respected.

Checks:
- **A/B** — PASS, same rebuild and same 5/5 matrix as above (this is where the sealed `raw/05` lives).
- **E Secrets / private data** — PASS, and stricter than MALDOOM: `a0ce164` adds **0** lines with `/home/danny`,
  0 Windows paths, 0 credential patterns. `AGENTS.md` rule 5 (no absolute workstation paths, relative manifests)
  holds.
- **F Worktree** — PASS. `git status --porcelain` = 0 lines before and after: nothing of any other agent was
  present and nothing was left behind.
- `evidence/hashes/loader_convention_v1.sha256` verifies **18/18** from the repo root (repo-root-relative paths).

Push:
`git push origin main` — normal, no flags, fast-forward `41d3cf3..a0ce164`, rc 0.

Remote HEAD:
`refs/heads/main = a0ce1642f7c3ba46175d6623edfead5197d6a7c5` confirmed by `git ls-remote` (both `refs/heads/main`
and `HEAD`), refreshed `origin/main`, and API `branches/main` (`protected=false`). `git branch -vv` shows
`[origin/main]` with no ahead/behind. `pushed_at=2026-10-15T13:53:54Z`. CI: consulted, `check-runs` = 0.

Remaining changes: none.

Risks: none identified beyond the general one — the repo is public and the loader patch is now the published
behaviour of `bolge19`.

## Integrity

Canonical parity:
**VERIFIED.** 5/5 canonical inputs byte-identical to the sealed matrix, same step counts, deterministic 3/3,
against MALDOOM's sealed `artifact.mu` (`3b9bdf37…`) with the artifact untouched. Raw path still reproduces the
`02ce` corruption, so the control that distinguishes the two loaders still holds.

Byte-exact verification:
**VERIFIED.** Rebuilding from committed source reproduces the sealed binary hash exactly
(`47758a3f…` source → `2cae851d…` binary).

32 drift repairs:
**VERIFIED, 32/32.** `disk == seal == HEAD` on every row; 160,982 bytes (was 163,678 with 2,696 CRs). The repair is
recorded in `REPAIR_EXECUTED.md`, not in a commit diff, because it restored equality with `HEAD`.

17 pending entries:
**VERIFIED UNTOUCHED.** 7 `M0_*/SHA256SUMS.txt` self-hashing lines, 7 `M0_*_UNSHACKLED_V0/source.c` mixed-CR seals,
1 `UNSHACKLED_CONTINUATION_ANCHOR_V0/ABC.eir`, 2 untracked `EPOCH_TRANSPARENCY_V{0,1}/evidence.json`. Not repaired,
not normalized, not deleted, not committed, not modified. Total across 33 manifests: 284 verify / 17 fail.
Method note: `sha256sum` emits Spanish here, so a failure is `La suma no coincide` plus an `ATENCIÓN` summary line;
the first recount used only the `NO coincidió` branch and falsely reported 0 failures — corrected, then recounted to
the 17 above. Recorded because it is the kind of filter bug that would have hidden a real regression.

Secret scan:
**CLEAN.** 0 credential-pattern hits and 0 sensitive filenames across both pushed ranges, checked per commit and per
range. The one filename matching `env` is `E4/raw/00_environment.txt`, an environment capture with no credentials
(read in full). Personal-but-non-secret data (home paths + hostname) is reported under MALDOOM → Risks.

## Final Status

**PUBLISHED** — both repositories.

| repository | branch | published | local == remote | push type | CI |
|---|---|---|---|---|---|
| MALDOOM (`MalDOOM`) | `master` | `13d2255..0dd01df` (8 commits) | `0dd01df` == `0dd01df` | normal fast-forward | none (0 check-runs) |
| malbolge-lisp-forensics | `main` | `41d3cf3..a0ce164` (1 commit) | `a0ce164` == `a0ce164` | normal fast-forward | none (0 check-runs) |

No force-push, no `--force-with-lease`, no `reset --hard`, no `git clean`, no `stash`, no history rewrite, no tag,
no release, no remote change, no new commit, no amended commit, no `git add .`. Nothing was deleted; the 29
untracked MALDOOM paths and the 17 pending seal entries are exactly as found.

Two decisions deliberately left to Danny, neither blocking publication:
1. Whether to publish a follow-up that records the 17 pending entries' disposition (they are now public as failing).
2. Whether to keep `MALDOOM`'s remote URL pointing at the moved `MalDOOM` name, given the redirect notice.

## Addendum 2026-10-15 (post-publication) — remote URL updated on Danny's instruction

Danny authorised the one deferred item: *"OK ACTUALIZA LA URL Y HAZ LO QUE FALTE"*. Applied afterwards, so the
line above that says "no remote change" remains true **of the publication step itself**; this addendum records
the change that followed it.

Executed in `MALDOOM`:

```
git remote set-url origin https://github.com/DannyBaanks/MalDOOM.git
```

Before: `…/MALDOOM.git` (fetch and push both on the old name, which GitHub served through a rename redirect —
the redirect notice seen during the push). After: the current canonical name, so the notice cannot come back if
the redirect is ever retired.

Verification with the new URL, all four green:

| check | result |
|---|---|
| `git fetch --prune origin` | rc 0, **no redirect notice**, no refs changed |
| `git ls-remote origin refs/heads/master` | `0dd01df…` — matches local `master` exactly |
| `git push -n origin master` (dry run, no flags) | `Everything up-to-date` |
| `git status -sb` | `## master...origin/master` (no ahead/behind) |

Scope of the change: `remote.origin.url` only. `branch.master.remote = origin` and the tracking ref
`refs/remotes/origin/master` were untouched and still resolve correctly. Nothing was re-pushed, no commit was
created or amended, no branch or tag was added, and Forensics needed no change (its remote name already matches
`DannyBaanks/MalbolgeLispForensics`, verified clean).

A scan of every other clone under `~/Development/ISyCo Git` (`find -maxdepth 4 -name config -path '*/.git/*'`,
excluding `vendor/`) found **exactly one** file carrying the old `MALDOOM.git` URL — the repo just updated — so no
sibling checkout is left pointing at the retired name.

Remaining open item from this closure, unchanged and still Danny's call: the disposition of the **17 pending seal
entries** (7 self-hashing `M0_*/SHA256SUMS.txt`, 7 mixed `M0_*_UNSHACKLED_V0/source.c`, `ABC.eir`, 2 untracked
EPOCH `evidence.json`). They are public as failing; nothing here repairs, normalizes, deletes or commits them.

## Addendum 2026-10-15 (2) — the 17 pending seal entries are disposed (E7), and this report is under version control

The last open item of the previous addendum is closed by `evidence/E7_SEAL_DISPOSITION_V0/` in MALDOOM.
Danny's instruction was to finish the pending items, which supersedes the earlier "do not repair" hold; the
repair was still limited to entries with a proof, and no manifest and no seal value was edited.

| outcome | count | basis |
|---|---|---|
| restored byte-exact and committed | 8 | 7 `M0_*_UNSHACKLED_V0/source.c` from worktree witnesses, `UNSHACKLED_CONTINUATION_ANCHOR_V0/ABC.eir` from the unique CR placement out of 2^5 |
| left failing, proven irrecoverable | 9 | 7 `M0_*/SHA256SUMS.txt` seal themselves (only that line fails; 6/6 and 14/14 siblings verify); 2 untracked `EPOCH_TRANSPARENCY_V{0,1}/evidence.json` match nothing in the worktree or in any of the 427 repo blobs |
| `sha256sum -c` repo-wide | 303 OK / 9 FAILED of 312 | was 295 / 17 |

Published: `3f9846e` (E7 evidence + the 8 restored files) and `acbf610` (post-commit chain check), pushed
`0dd01df..acbf610` to `origin master` — normal push, no force, no tags, no other branch, remote URL unchanged.
Confirmed by `git ls-remote`, the refreshed tracking ref and the GitHub API (all `acbf610…`), `check-runs`
total 0 (no CI, verified not assumed), worktree still holding the 29 foreign untracked paths and 0 modified.

**New finding, larger than the 17, and still Danny's call.** 127 sealed entries verify on the worktree but are
stored in Git as their seal with **every CR removed**; 8 of them were fixed by E7, **119 remain**. `git status`
cannot see it — the index carries the LF blob together with the worktree's size and mtime — so `sha256sum -c`
alone is not an integrity check for this repository. Repairing the rest means re-staging 119 committed evidence
files and publishing them; it is measured and reported in `E7_DISPOSITION.md` §5, not executed.

Relocation: this file was written during the closure to `ISyCo Git/reports/git-publication/`, a directory that is
not a repository. It now lives at `MALDOOM/docs/GIT_PUBLICATION_REPORT.md` under version control; the earlier
path is the only place it ever existed before this commit, and the move carried no content change other than
this addendum.

## Addendum 2026-10-15 (3) — the 119 CR-stripped committed blobs are aligned and published (E8)

The open decision of addendum (2) was given the same day ("SÍ, LÁNZALO"), and `evidence/E8_COMMIT_SIDE_ALIGNMENT_V0/`
executes it. Nothing on disk was touched: the defect was on the stored side only.

| step | result | basis |
|---|---|---|
| measure | 346 sealed entries: 216 aligned, **119 `CR-STRIPPED`**, 2 never committed, 9 E7's irrecoverable — 0 entries outside these four relations | `raw/01` |
| `git add` as fixer | **silent no-op: restaged=0, refused=119.** The index holds the LF blob together with the worktree's size and mtime, so Git considers the file clean | `raw/02a` |
| route used | `git hash-object -w` + `git update-index --cacheinfo` (index-only; worktree bytes and mtimes untouched; reversible per path with `git reset -q -- <path>`) | `raw/02`, restaged=119 refused=0 |
| guard | five assertions per path re-checked at the moment of staging: still a candidate, `SHA-256(worktree)==seal`, `HEAD==fold(worktree)` and `!=seal`, `git hash-object == SHA-1(worktree)` (clean filters are identity), never a manifest | `raw/02` |
| pre-commit review | staged set was **exactly** those 119 paths, no deletion/rename/addition; staged content folds back to HEAD byte for byte, so the commit adds no content that is not a CR (delta 77,731 bytes over 77,731 changed lines); credential scan over the staged blobs: 0 hits, 0 suspicious filenames | `raw/03`, `raw/04`, `raw/06` |
| after | repo-wide **362** sealed entries, **351** with `worktree == seal == HEAD`, **11** mismatches — precisely E7's documented set (9 irrecoverable + 2 untracked `program.op`) and no larger | `raw/07`, `raw/10` |
| E7's own acceptance test | `stored_cr_analysis.py`: *"hypothesis holds for **0** entries"* (was 119) | `raw/08` |

Commits: `61437d3` (the 119 blobs), `a0b4bcd` (E8 evidence, 16 entries sealed with LF and no self-entry),
`4b86138` (post-commit chain check addendum), plus this addendum. Pushed to `origin master` as a normal
fast-forward — no force, no tags, no releases, no other branch, remote URL unchanged, no history rewritten.

**Consequences to keep in mind.** `b3d372b` and every earlier commit still contain the LF renderings: they are
superseded, not erased, so a clone made before this push must be updated with a normal `git pull` and not
compared against the seals in place. The published evidence bytes now match what `SHA256SUMS.txt` has always
described, which means the integrity of the older commits is unchanged as *claims* and corrected as *storage*.
What E8 does **not** demonstrate: the sealed programs were not re-executed, so behaviour rests on the original
runs, and the Windows-`core.autocrlf` mechanism remains an inference (`[NOT_DEMONSTRATED]`).

Seal ledger, closed: 312 entries counted before E8's own manifest — 295 verifying at the start of E7, 303 after
its 8 repairs, 351 three-way aligned after E8. The 9 that still fail are unsatisfiable or lost and are documented
in `E7_DISPOSITION.md` §4; they are no longer "pending".
