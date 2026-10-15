# E6 — Seal integrity across the whole MALDOOM evidence tree

Date: 2026-10-15 · Host: Ubuntu 24.04, repo `/home/danny/Development/ISyCo Git/MALDOOM`
Origin: step (iii) of the loader-convention investigation, which asked whether the
5 `observed_*.bin` of `evidence/M0_KILLER_UNSHACKLED_V0/` should be "re-sealed"
because their worktree bytes no longer match their `SHA256SUMS.txt` entries while
`git status` reports the directory clean. Measurement widened the question to every
manifest in the repository before anything was decided.

**Answer to the question as asked: no re-sealing.** For those 5 files the seal is
intact, the canonical bytes are already committed, and the worktree held a CRLF
rendering of them. Re-sealing would have overwritten a verified record with the
drifted bytes, which is rewriting evidence. What was done instead, after Danny's
approval the same day, is CR-stripping the 32 files of that group — see
`REPAIR_EXECUTED.md`.

**Headline of the wider audit: no evidence content was lost.** 262 of the 288
sealed entries are tracked, and for **every one of those 262** the worktree and
the commit are the same bytes once CR is folded away. Every remaining mismatch
against a seal is a line-ending rendering, except 9 entries: 7 manifests that seal
themselves (unverifiable by construction) and 2 untracked `evidence.json`.
Counts are the sealed 2026-10-15 capture (`raw_audit.tsv`, 32 manifests); sealing
this directory added a 33rd manifest, which is recorded in Regression controls.

## Labels

| Label | Meaning here |
|---|---|
| DEMONSTRATED | reproducible from the tooling + raw files in this directory |
| OBSERVED | single measurement, recorded but not reproduced |
| NOT_DEMONSTRATED | asked, but this repository cannot currently answer |

## Method

Three scripts, all run from the repository root, all read-only (they only ever
run `git status/diff/show/ls-files/cat-file/rev-parse/hash-object/log`):

- `tools/seal_audit.py` — for every `evidence/*/SHA256SUMS.txt` entry, compares
  three byte sources (seal hash, worktree, `git show HEAD:path`) and names the
  line-ending rule that relates each pair (`exact`, `crlf_to_lf`, `lf_to_crlf`,
  `cr_to_lf`, `lf_to_cr`, `canonical_lf`, `canonical_crlf`, or `CONTENT` when no
  global rule explains it). Also records whether `git status` noticed.
  Output: `raw_audit.tsv` — 288 entries over 32 manifests, repo-relative paths
  (the capture taken before this directory had a manifest; running it today prints
  one more manifest and one untracked row per file this directory seals).
- `tools/derive_lists.py` — from that TSV, the repairable subset
  (`restore_manifest.txt`, 32 paths) and `drift_snapshot.tsv` with the three
  hashes per path, so the byte rule can be re-checked without re-running the audit.
- `tools/witness_search.py` — refines each `CONTENT` row: does the worktree and
  the commit hold the same text modulo CR; is there a CR *placement* (exhaustive
  up to 12 breaks) that reproduces the seal; and does any other file in the
  repository already hold the exact sealed bytes. Output: `witness_search.tsv`.

No index-mutating command was run (`git update-index --refresh`,
`--really-refresh`, `git stash`, `git checkout .`): this worktree is shared with
other agents through the bridge, and those commands mutate shared state.

## Files in this directory

| file | what it is |
|---|---|
| `E6_FINDINGS.md` | this document |
| `raw_audit.tsv` | the 288-entry sealed capture (dated, see Regression controls) |
| `raw_audit_regeneration.txt` | the post-sealing re-run and its exact 10-row delta |
| `witness_search.tsv` | 30 `CONTENT` rows: same-text-modulo-CR / CR placement / in-repo witness |
| `restore_manifest.txt` | the 32 repairable paths, one per line — the approval manifest |
| `drift_snapshot.tsv` | those 32 rows with worktree/seal/HEAD hashes + the byte rule |
| `raw_census.txt` | config, check-attr, `ls-files -v`, commit attribution, mtime minutes, NUL controls, blast radius |
| `mech_proof_git_blindness.txt` | the read-only git-blindness proof + `.gitattributes` history |
| `tools/*.py` | the three read-only tools |
| `SHA256SUMS.txt` | this directory's seal: LF, no self-entry |

## The whole-repository picture (DEMONSTRATED)

| # | entries | worktree vs seal | commit vs seal | who is the outlier | repair that preserves evidence |
|---|---|---|---|---|---|
| 1 | 99 | `exact` | `exact` | nobody — chain is byte-exact | none needed |
| 2 | 103 | `exact` | `lf_to_crlf` | the **commit** (LF rendering) | none: the seal verifies on disk today |
| 3 | 32 | `crlf_to_lf` | `exact` | the **worktree** (CRLF rendering) | **done 2026-10-15**: CR dropped, disk == seal == HEAD (`REPAIR_EXECUTED.md`) |
| 4 | 13 | `exact` | `CONTENT` | the **commit**, partially-converted | none: seal verifies on disk |
| 5 | 15 | `CONTENT` | `CONTENT` | mixed CR placement, or self-hash | resolved row by row in `witness_search.tsv` |
| 6 | 24 | `exact` | `UNTRACKED` | never committed | not a seal problem |
| 7 | 2 | `CONTENT` | `UNTRACKED` | content changed after sealing | `NOT_DEMONSTRATED` — see the addendum in `raw_audit_regeneration.txt` for this shape reproducing itself inside E6 |

288 = 99 + 103 + 32 + 13 + 15 + 24 + 2. `git_says` is `git_clean` for **every one
of the 288**: 49 sealed files whose worktree differs from its seal and 131 whose
commit differs from its seal, and git noticed none of them.

Group 3 is where the 5 `observed_*.bin` live; it is the only group with a
non-destructive repair available, and it is the M0_KILLER question.

## Rows 2, 4 and 5 are one mechanism: CR rendered three different ways

For **all 262 tracked entries** `SHA-256(fold CR(worktree)) == SHA-256(fold CR(commit))`
— re-asserted directly over the whole sealed capture with 0 failures (the first
heredoc in *Reproduce*), which is stronger than the `same_text_modulo_CR` column of
`witness_search.tsv`, which only samples the 30 `CONTENT` rows. What differs is
where the CRs sit:

- **row 2 (103)** — pure CRLF sealed, pure CRLF on disk, pure LF committed:
  `lf_to_crlf(commit)` reconstructs the seal exactly, one rule, every time.
- **row 3 (32)** — pure LF sealed and committed, CRLF on disk: `crlf_to_lf(worktree)`
  is the seal and the commit at once. This is the only repairable row.
- **rows 4 and 5 (28)** — the sealed file was **mixed** (some CRLF lines, some LF
  lines). The worktree is the all-CRLF rendering and the commit the all-LF
  rendering, so no single global rule maps either one onto the seal — that is why
  `seal_audit.py` calls them `CONTENT`. `witness_search.tsv` covers these 28 plus
  the 2 untracked rows of group 7 (30 rows) and answers them on three axes:

  `same_text_modulo_CR` — `YES` on 28 of the 30. Only the 2 untracked
  `EPOCH_TRANSPARENCY_V{0,1}/evidence.json` differ in content, not just in CR.

  `seal_witness` — where the exact sealed bytes live right now:
  - **row 4 (13)** — the **worktree itself**: every group-4 path is `exact` against
    its seal, so the disk holds the canonical bytes and only the commit is an LF
    rendering. 8 of them are additionally mirrored in-repo: `engine/M0_*.c` hashes
    equal the seal of the matching `evidence/M0_*/source.c` (7 rows) and
    `doomgeneric_headless.c` equals the seal of `evidence/DOOM_SMOKE/headless.c`,
    because `scripts/build_m0.py:65` copies `engine/<NAME>.c` into the evidence
    directory as `source.c` without touching bytes. The other 5 are their own only
    witness: `CLASSIC_ANCHOR_SMOKE_V1/{CLASSIC_RUNTIME_AUDIT,GENERATOR_AUDIT,HOST_AUDIT,RESULT}.md`
    and `DOOM_SMOKE/run.json`.
  - **row 5 (7)** — `M0_*_UNSHACKLED_V0/source.c`: neither worktree nor commit is the
    seal, but the sealed bytes exist in the repository at `engine/M0_*.c` and
    `evidence/M0_*/source.c`.
  - **row 5 (1)** — `UNSHACKLED_CONTINUATION_ANCHOR_V0/ABC.eir`: no in-repo witness;
    only the placement search below recovers its seal.
  - **row 5 (7)** — `evidence/M0_{A_CONST,B_ARITH,C_BRANCH,D_LOOP,E_MEMORY,F_INPUT,
    KILLER}/SHA256SUMS.txt` sealing **themselves** (e.g. line 15 of
    `evidence/M0_KILLER/SHA256SUMS.txt` records `f8b72be9…` for `SHA256SUMS.txt`,
    whose actual hash is `fd247f09…`). A file cannot contain its own final hash, so
    those lines are unverifiable by construction — a manifest-authoring defect, not
    evidence loss. In `evidence/M0_KILLER/` that self-line is the only entry that
    fails `sha256sum -c`.
  - **row 7 (2)** — the untracked `evidence.json` files: found nowhere.

  `cr_placement` — does a CR insertion pattern reconstruct the seal from the LF text
  (exhaustive up to 12 breaks, `SKIPPED` beyond, since the space is 2^n):
  - **8 rows, exactly one placement**: `CLASSIC_RUNTIME_AUDIT.md` (CR before break 3),
    `GENERATOR_AUDIT.md` (7), `RESULT.md` (10), `M0_A_CONST/source.c` (10),
    `M0_A_CONST_UNSHACKLED_V0/source.c` (10), `M0_D_LOOP/source.c` (11),
    `M0_D_LOOP_UNSHACKLED_V0/source.c` (11), `ABC.eir` (4). A mixed seal is a
    precisely recoverable shape, not an unknown one.
  - **6 rows, searched and none**: the six `M0_{A_CONST,B_ARITH,C_BRANCH,D_LOOP,
    E_MEMORY,F_INPUT}/SHA256SUMS.txt` self-entries (all ≤ 12 breaks) — as expected,
    since no placement can produce a hash of the file that contains it.
  - **16 rows `SKIPPED (> 12 breaks)`**: 13 mixed `source.c` / `headless.c` /
    `run.json` / `HOST_AUDIT.md` files, `M0_KILLER/SHA256SUMS.txt`, and the 2
    untracked JSONs. The bound is deliberate (2^n placements), and 13 of those 16
    are answered by the witness axis instead. Only 3 rows depend on the skipped
    search: the 2 untracked `evidence.json` (which are also
    `same_text_modulo_CR=n/a`, i.e. real content changes) and the self-entry of
    `M0_KILLER/SHA256SUMS.txt` — none of them a case of lost canonical bytes.

  Net: every row of groups 4 and 5 is either byte-present (worktree or in-repo
  witness) or hash-recoverable (unique placement), **except** the 7 self-hashing
  manifests and the 2 untracked `evidence.json` — which is exactly the "9 entries"
  the headline above counts as unexplained.

## Mechanism (DEMONSTRATED read-only, see `mech_proof_git_blindness.txt`)

1. **No conversion is configured today.** `core.autocrlf` and `core.eol` are
   unset; `git check-attr text eol` reports `text: unset`, `eol: unspecified` for
   the affected paths because `.gitattributes` says `* -text`.
2. **Git decides "unchanged" from index stat data, not bytes.** For
   `evidence/M0_KILLER_UNSHACKLED_V0/observed_0.bin`: index size 3 / disk 3 bytes
   (`310d0a`) / committed blob 2 bytes (`310a`), `git hash-object` gives
   `f33dfa25…` while the index and HEAD both hold `d00491fd…` (the SHA-1 of `1\n`).
   Because the worktree matches the *stat* record, git never re-hashes, so
   `git status` and `git diff HEAD` are both empty for a file whose bytes differ.
3. **The same blindness with perfectly matching stat data.** For
   `evidence/DOOM_SMOKE/headless.c` the index size (2553) and mtime
   (2026-09-01 21:21:12) equal the worktree's and the index SHA-1 equals HEAD's,
   yet `git hash-object` yields `8e6c25b8…` ≠ `cdc854ce…`. No assume-unchanged or
   skip-worktree is involved: `git ls-files -v` reports 395 entries, every one
   flagged `H`.
4. **Conversion was configured when the drifted blobs were written.**
   `.gitattributes` appeared on 2026-10-09 in `58a3473` (21:01:18,
   `* text=auto eol=lf`, "the tree is canonical LF") and was reverted 9 minutes
   later by `534d6dd` (21:10:33, `* -text`, "disable EOL conversion, not force
   LF"). Before `58a3473` there was no attributes file at all, and the Windows-era
   commits that wrote today's blobs are `faf65bc` (2026-09-03), `d7c07a1`
   (2026-09-06) and `35bc289` (2026-09-09). Attribution is exhaustive per row
   (`raw_census.txt`): row 2 = 76×`35bc289` + 27×`faf65bc`; row 3 = 30×`35bc289` +
   2×`d7c07a1`; row 4 = 13×`faf65bc`; and 74 of the 99 byte-exact rows come from
   those same Windows commits — which is the control, because a Windows-era commit
   produced byte-exact blobs whenever the worktree was already LF at add time.
5. **Git's own text detection predicts the split, and it holds.** Git will not
   convert content it deems binary (a NUL byte). Of the 103 CRLF-sealed files,
   **0** contain a NUL; all 12 NUL-bearing sealed files in the repository sit in
   the byte-exact row (5 LF, 6 lone-CR, 1 CRLF) (`raw_census.txt`).
6. **Which host setting performed the conversion is NOT_DEMONSTRATED.**
   `core.autocrlf=true` (the Git for Windows installer default) produces exactly
   this signature — LF on check-in, CRLF on checkout — but the Windows build
   host's configuration lived on the disk lost on 2026-09-23 and cannot be read.

## One bulk event explains the worktree side (OBSERVED, mtimes)

All 32 repairable files share a single worktree mtime minute: **2026-09-09 21:58**.
So do 76 of the 103 files in row 2. Everything else in those rows carries
spread-out generation timestamps (2026-09-01 20:55 … 22:16). That is the shape of
one Windows-side operation — a checkout or a restore — stamping 108 files with CRLF
renderings at 21:58 on 2026-09-09: for the 76 the bytes were already CRLF so
nothing changed, and for the 32 CR was *added* to files whose seal had recorded LF.
After the Linux migration and `* -text`, nothing converts anymore, so both states
froze and git stopped being able to see either one. NOT_DEMONSTRATED: the command
that performed it (its invocation was never recorded).

## `.gitattributes` — both comments are wrong, the rule is right

`* -text` is the correct policy: sealed bytes must stay the committed bytes, and
nothing may convert between them. But the prose in each version asserts something
measurement contradicts:

- `58a3473`: "sealed evidence hashes were computed on LF bytes" — false for the
  103 pure-CRLF seals and the 6 lone-CR ones.
- current: hashes are "computed on the exact committed bytes (CRLF, as generated
  on the Windows build host)" — the CRLF half is false for the 32 repairable files
  (their seal *and* their commit are LF) and for the 92 LF seals of row 1; the
  "exact committed bytes" half is false for the 116 files of rows 2 and 4, whose
  commit is an LF rendering of the sealed bytes.

The comment is documentation, not a control, so it was left alone: editing a
tracked root file in a worktree other agents are committing from is not this
evidence's business. Recorded here instead.

## What the repair would be, and why it stops at a human gate

Row 3 (`restore_manifest.txt`, **32 files across 13 directories**):

```
evidence/PURE_CONTINUATION_ANCHOR_V0/sources      11
evidence/M0_KILLER_UNSHACKLED_V0                   5
evidence/M0_F_INPUT_UNSHACKLED_V0                  3
evidence/PURE_CONTINUATION_ANCHOR_V0               2
evidence/M3A_P_RANDOM_UNSHACKLED_V0                2
evidence/DOOM_NATIVE_BASELINE                      2
evidence/M0_A_CONST_UNSHACKLED_V0                  1
evidence/M0_B_ARITH_UNSHACKLED_V0                  1
evidence/M0_C_BRANCH_UNSHACKLED_V0                 1
evidence/M0_D_LOOP_UNSHACKLED_V0                   1
evidence/M0_E_MEMORY_UNSHACKLED_V0                 1
evidence/M1_WAD_HEADER_UNSHACKLED_V0               1
evidence/M2A_LUMP_FIND_UNSHACKLED_V0               1
```

163,678 worktree bytes would become 160,982 by removing exactly 2,696 CR bytes.
For each of the 32, `SHA-256(worktree with CRLF→LF) == seal == HEAD`
(`drift_snapshot.tsv`, 32 rows, 0 rule failures), so the repair is

```
git checkout HEAD -- <the 32 paths>      # or: strip CR from each file
sha256sum -c SHA256SUMS.txt              # per directory, must pass again
```

It is content-preserving and reversible (the CRLF bytes are reproducible by adding
CR back, and the rule is recorded per file), and it changes no hash in any
manifest. It is still **32 files**, above the ">5 files" threshold of `AGENTS.md`
§0c.6, so **nothing was written at authoring time**: this document plus
`restore_manifest.txt` is the deletion-equivalent manifest, and the write waited for
Danny's approval.

**Approval given and repair executed the same day — see `REPAIR_EXECUTED.md`.** All
32 are now byte-identical to seal and to `HEAD`; the audit's byte-exact group went
99 → 131 and the drifted group 32 → 0. That record also corrects the command above:
`git checkout HEAD -- <path>` was a **no-op** here, because the index already held
the right blob and git's worktree check is stat-based — the same blindness, now
demonstrated on the restore side. The repair had to compare bytes and write them.

Also removed from the proposed command list: `sha256sum -c` is the right verifier,
but 7 failures remain afterwards in `M0_*_UNSHACKLED_V0/` and they are **expected**
(the mixed `source.c` of group 5, which this repair deliberately does not touch).

For reference, the 5 M0_KILLER files named in the original question:

| file | worktree (3 B, CRLF) | seal == HEAD (2 B, LF) |
|---|---|---|
| `observed_0.bin` | `f1b2f662…` | `4355a46b…` |
| `observed_1.bin` | `24ba1e99…` | `1121cfcc…` |
| `observed_2.bin` | `7fb2aaea…` | `f0b5c2c2…` |
| `observed_3.bin` | `9b6dd0f5…` | `10159baf…` |
| `observed_4.bin` | `69fa4dd4…` | `2e6d31a5…` |

## What must NOT be done

- **Re-seal row 3 to CRLF.** `sha256sum *> SHA256SUMS.txt` after the drift would
  replace a record that matches the committed bytes with one that matches only the
  worktree. That is rewriting raw evidence (`AGENTS.md` §5.10, MALDOOM `AGENTS.md`
  §4 "Overwriting `evidence/` without new hash = chain broken") and it destroys
  the only thing that currently proves the canonical bytes.
- **`git checkout HEAD --` on rows 2 and 4** (116 files). Their seals are the
  CRLF/mixed bytes on disk; the commit is the odd side. Restoring from HEAD would
  break a seal that verifies right now.
- **"Fix" the 116 by re-committing the worktree bytes.** Additive (history keeps
  the LF blobs) but it changes the committed rendering of sealed evidence for a
  cosmetic gain — `sha256sum -c` already passes for them. Not done, not proposed
  as a default.
- **`scripts/build_m0.py`, `git clean`, `git reset --hard`, `git stash`,
  recursive deletion.** `build_m0.py` writes `source.c`, `8cc.stdout`,
  `8cc.stderr`, `artifact.eir` straight into `evidence/<M0_*>/`, so the "run the
  smallest relevant verifier" step of MALDOOM `AGENTS.md` §9 would overwrite
  sealed files in-place here; it was deliberately not run for this evidence-only
  change. `scripts/verify_*.py`-style hash checks are the right smallest test, and
  they are exactly what `seal_audit.py` performs.
- **`git update-index --really-refresh`**: it would make git re-hash and report
  ~49 evidence files modified, and in this shared worktree any later `git add` by
  another agent could then commit drifted bytes as if they were canonical.
- **Deleting the self-hashing lines from the 7 `M0_*/SHA256SUMS.txt` manifests.**
  That would rewrite a sealed manifest to make a symptom disappear; the defect is
  documented above and stays open for Danny.
- Editing `evidence/M0_REPORT.md` line 88 ("Observed is normalized `CRLF→LF`
  (Windows text mode)") — it is the contemporaneous record that predicts exactly
  the LF seals measured here, and it stays as written.

## NOT_DEMONSTRATED

1. Which host-side setting performed the LF↔CRLF conversions (`core.autocrlf` on
   the lost Windows disk). Inference only, from the byte signatures and controls.
2. Why the 2026-09-09 21:58 operation touched exactly those 108 files: the
   timestamp coincidence is the only evidence, the command was never recorded.
3. Whether `evidence/EPOCH_TRANSPARENCY_V0/evidence.json` and
   `evidence/EPOCH_TRANSPARENCY_V1/evidence.json` were appended after they were
   sealed. They are untracked, they are **not** the same text modulo CR
   (`same_text_modulo_CR=n/a` — a real content difference), the placement search was
   bounded and skipped them (39 and 1266 breaks), and no file in the repository
   holds the sealed bytes.
4. Whether the partially-converted seals of rows 4/5 are "the" canonical bytes for
   those claims. The sealed hash is authoritative for the worktree at seal time,
   but the mixed CR placement itself was never declared as part of the protocol.
5. Whether the 7 self-hashing manifests were intended to include themselves.

## Regression controls

- `sha256sum -c` in `evidence/M0_KILLER_UNSHACKLED_V0` fails for exactly 6 entries
  (the 5 `observed_*.bin` + `source.c`), matching rows 3 and 5.
- `sha256sum -c` in `evidence/M0_KILLER/` fails only for the manifest's own line.
- `git status --porcelain` for those directories: empty. `git ls-files -v`: 395
  entries, all `H`.
- 0 of the 103 CRLF-sealed files contain a NUL byte; all 12 NUL-bearing sealed
  files are byte-exact. Predicted by git's text auto-detection, and it held.
- The audit was run three times on 2026-10-15 (coarse rules, extended rules, and
  the final sealed tooling); `raw_audit.tsv` from the sealed tool is byte-identical
  to the run that produced it (`diff -q` empty), and the group counts are stable.
  That was the state **before** this directory had a manifest — see the next bullet.
- **A fourth re-run, after this directory was sealed, differs — and the difference
  is fully explained** (`raw_audit_regeneration.txt`): `seal_audit.py` globs
  `evidence/*/SHA256SUMS.txt`, so E6's own manifest became the 33rd, adding 10
  untracked rows to group 6 (24 → 34). 0 of the 288 originally audited rows changed
  category, and `witness_search.py` re-ran byte-identical. The sealed capture is
  therefore a **dated** count, not a live one — the same self-reference that makes
  the 7 `M0_*/SHA256SUMS.txt` self-entries unverifiable, so it is stated rather than
  hidden.
- This directory's own `SHA256SUMS.txt` follows the convention the audit says is
  correct: **LF line endings and no entry for itself**, so it verifies
  (`sha256sum -c` → 11/11 `OK`, one line per file in the directory) and is
  re-runnable. Adding a file here changes that count, which is the point of the
  bullet above: a manifest with no self-entry is still a dated statement.

## Reproduce

```
cd "/home/danny/Development/ISyCo Git/MALDOOM"
python3 evidence/E6_SEAL_INTEGRITY_V0/tools/seal_audit.py > /home/danny/tmp_e6/audit.tsv
  # today this prints seal_files 33 and one row per file this directory seals
  # (299 with 11 sealed files), not 32/288: raw_audit.tsv is the dated pre-sealing
  # capture. The added rows are all exact/UNTRACKED except a document edited after
  # its own seal — see raw_audit_regeneration.txt, which records both runs.
python3 evidence/E6_SEAL_INTEGRITY_V0/tools/derive_lists.py
  # NOTE: this one WRITES restore_manifest.txt and drift_snapshot.tsv in this
  # directory. Run it only to regenerate them deliberately, then re-seal; if
  # nothing drifted the bytes are unchanged. The other two print to stdout.
python3 evidence/E6_SEAL_INTEGRITY_V0/tools/witness_search.py   # refines the CONTENT rows
python3 - <<'PY'   # assert the headline: 262/262 tracked rows, same text modulo CR
import hashlib, pathlib, subprocess
rows=[l.split("\t") for l in pathlib.Path("evidence/E6_SEAL_INTEGRITY_V0/raw_audit.tsv").read_text().splitlines()
      if len(l.split("\t"))==5 and not l.startswith("seal_files") and not l.startswith("path")]
fold=lambda b: b.replace(b"\r\n",b"\n").replace(b"\r",b"\n")
tracked=[r for r in rows if r[2]!="UNTRACKED"]
bad=[r[0] for r in tracked if hashlib.sha256(fold(pathlib.Path(r[0]).read_bytes())).hexdigest()
     != hashlib.sha256(fold(subprocess.run(["git","show","HEAD:"+r[0]],capture_output=True).stdout)).hexdigest()]
print(len(tracked),"tracked rows,",len(bad),"failures")
PY
python3 - <<'PY'   # assert the 32-file byte rule, read-only
import hashlib, pathlib
rows=[l.split("\t") for l in pathlib.Path("evidence/E6_SEAL_INTEGRITY_V0/drift_snapshot.tsv").read_text().splitlines()[1:]]
for rel,wb,ws,ss,hs,rule in rows:
    b=pathlib.Path(rel).read_bytes()
    assert hashlib.sha256(b.replace(b"\r\n",b"\n")).hexdigest()==ss==hs, rel
print("rule holds for", len(rows), "files")
PY
sha256sum -c evidence/E6_SEAL_INTEGRITY_V0/SHA256SUMS.txt
  # if a file here was edited after that seal was written, this line fails for it
  # (row-7 shape); regenerate the manifest last, LF, no self-entry, then verify.
```

`SHA256SUMS.txt` is generated **last**, one line per file in this directory, LF
endings, no self-entry — after any edit to anything here it must be regenerated and
re-verified, otherwise this directory itself falls into row 7.

## Scope

This directory documents the integrity of *sealed bytes* in MALDOOM's `evidence/`
tree as measured on 2026-10-15. It does not claim that any computational result in
this repository is wrong: every divergence found is a line-ending rendering or an
uncommitted/untracked content edit, and no step count, artifact hash, or claim
status changes because of it. It says nothing about `malbolge-lisp-forensics`,
which has its own differently-caused manifest failures (57 line-ending-only and 6
content out of 150) measured in `evidence/loader_convention_v1/` there.
