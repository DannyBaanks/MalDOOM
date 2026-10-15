# E7 — Seal Disposition V0: the 17 failing sealed entries, measured and decided

Date: 2026-10-15 (local, `DannyISyCo`, Ubuntu 24.04). Predecessor state: `0dd01df` (E6).
Scope: every entry of every `evidence/**/SHA256SUMS.txt` that `sha256sum -c` reported as failing.
Question answered: **are the sealed bytes recoverable, and if so from what proof?**
Target (MALDOOM `AGENTS.md` §4): produce evidence, never overwrite a seal, never upgrade a claim
without a run. Nothing here changes a sealed hash value.

## 1. Method

Eight tools; all but `repair_guarded.py` only read.

| Tool | Purpose |
|---|---|
| `tools/disposition.py` | classify each failing entry: `RECOVERABLE-witness` / `RECOVERABLE-placement` / `NOT_RECOVERABLE`; writes nothing |
| `tools/witness_proof.py` | list every worktree file whose exact bytes hash to the seal |
| `tools/placement_proof.py` | the exhaustive CR-placement search for the one entry with no witness |
| `tools/not_recoverable_proof.py` | for the rest: scan the whole worktree **and** all 427 blob objects in the repository, plus the per-manifest `sha256sum -c` verdict list |
| `tools/staged_blob_check.py` | per repaired path: `seal == worktree == staged blob` |
| `tools/chain_check.py` | three-way `seal == worktree == stored` over every manifest, against `INDEX` or `HEAD` |
| `tools/stored_cr_analysis.py` | for entries where the worktree matches the seal but `HEAD` does not, test `HEAD == worktree with every CR removed` |
| `tools/repair_guarded.py` | the only writer; refuses by default |

Definitions used:

- **witness** — another file in the worktree whose bytes hash exactly to the seal. The sealed bytes
  still exist; they only sit in the wrong place.
- **placement** — the committed rendering is the seal with the CR characters removed; re-inserting
  CR before a subset of its line breaks is searched exhaustively (`2**n`) and **exactly one** subset
  reproduces the seal.
- **none** — neither, and no blob in the object database hashes to the seal either.## 2. Result

17 entries failed. **8 recovered, 9 left failing by proof, not by choice.**

| Entry | Verdict | Proof |
|---|---|---|
| `evidence/M0_A_CONST_UNSHACKLED_V0/source.c` | REPAIRED | witness: `engine/M0_A_CONST.c`, `evidence/M0_A_CONST/source.c` |
| `evidence/M0_B_ARITH_UNSHACKLED_V0/source.c` | REPAIRED | witness: `engine/M0_B_ARITH.c`, `evidence/M0_B_ARITH/source.c` |
| `evidence/M0_C_BRANCH_UNSHACKLED_V0/source.c` | REPAIRED | witness: `engine/M0_C_BRANCH.c`, `evidence/M0_C_BRANCH/source.c` |
| `evidence/M0_D_LOOP_UNSHACKLED_V0/source.c` | REPAIRED | witness: `engine/M0_D_LOOP.c`, `evidence/M0_D_LOOP/source.c` |
| `evidence/M0_E_MEMORY_UNSHACKLED_V0/source.c` | REPAIRED | witness: `engine/M0_E_MEMORY.c`, `evidence/M0_E_MEMORY/source.c` |
| `evidence/M0_F_INPUT_UNSHACKLED_V0/source.c` | REPAIRED | witness: `engine/M0_F_INPUT.c`, `evidence/M0_F_INPUT/source.c` |
| `evidence/M0_KILLER_UNSHACKLED_V0/source.c` | REPAIRED | witness: `engine/M0_KILLER.c`, `evidence/M0_KILLER/source.c` |
| `evidence/UNSHACKLED_CONTINUATION_ANCHOR_V0/ABC.eir` | REPAIRED | 1 unique CR placement out of 2^5 |
| `evidence/M0_A_CONST/SHA256SUMS.txt` | LEFT FAILING | self-referential seal line; only that line fails (6 verify) |
| `evidence/M0_B_ARITH/SHA256SUMS.txt` | LEFT FAILING | same (6 verify) |
| `evidence/M0_C_BRANCH/SHA256SUMS.txt` | LEFT FAILING | same (6 verify) |
| `evidence/M0_D_LOOP/SHA256SUMS.txt` | LEFT FAILING | same (6 verify) |
| `evidence/M0_E_MEMORY/SHA256SUMS.txt` | LEFT FAILING | same (6 verify) |
| `evidence/M0_F_INPUT/SHA256SUMS.txt` | LEFT FAILING | same (6 verify) |
| `evidence/M0_KILLER/SHA256SUMS.txt` | LEFT FAILING | same (14 verify) |
| `evidence/EPOCH_TRANSPARENCY_V0/evidence.json` | LEFT FAILING | no witness, no blob, never committed |
| `evidence/EPOCH_TRANSPARENCY_V1/evidence.json` | LEFT FAILING | no witness, no blob, never committed |

Raw records: `raw/01_disposition_table.tsv` (pre-state), `raw/03_repair_record.tsv` (the writes),
`raw/04_witness_proof.txt`, `raw/05_placement_proof.txt`, `raw/06_not_recoverable_proof.txt`,
`raw/07_epoch_transparency_state.txt`, `raw/08_post_repair_disposition.tsv`,
`raw/09_environment.txt`, `raw/10_tally.txt`, `raw/11_staged_blob_check.txt`,
`raw/12_chain_check_staged_index.txt`, `raw/13_stored_cr_analysis.txt` (both chain checks were
produced with the files staged and before this directory's own manifest existed, so their repo-wide
count is the pre-E7 312 entries). `raw/14_chain_check_after_commit.txt` is the same tool run against
`HEAD` after the commit — it additionally counts E7's own sealed entries — and is sealed separately in
`SHA256SUMS_addendum.txt`, because it cannot be sealed in the manifest the commit it verifies carries.
`raw/02_repair_record_attempt1_empty.tsv` and
`raw/02_repair_stderr_attempt1_traceback.txt` are kept as the negative result of the first repair
attempt: the writer died parsing the table header (`hdr` used inside the same assignment that binds
it) before the loop ran, so no file was touched. `before/` keeps a byte-exact copy of every file the
repair replaced, named by its repo path with `/` folded into `__`.

## 3. Root cause of the 8

Two different corruptions of the *same* misconfiguration, one visible in the worktree, one in history.

The sealed bytes of these files are **LF line endings plus one trailing bare `CR LF`** — that is what
the generator wrote and what the seal was computed over (`raw/05` shows `ABC.eir` as
`putc 65\nputc 66\nputc 67\nexit\n\r\n`, 31 bytes). Measured states before the repair:

| state | CR per file | explanation |
|---|---|---|
| seal | 1 | the generated bytes |
| worktree | one CR on **every** line | a checkout on the old Windows host wrote CRLF endings |
| HEAD blob | 0 | the same host stripped every CR on the way into the index |

So the committed evidence had **lost a content byte** and the worktree had **gained one per line**;
neither matched the seal, and `git checkout HEAD -- <path>` could never have fixed it (it restores a
blob that is already wrong).

`58a3473` added `* text=auto eol=lf` on the premise "the tree is canonical LF (sealed evidence hashes
were computed on LF bytes)". That premise is false for these files — the seals contain a CR — and the
following commit `534d6dd` replaced it with `* -text`, which is what the current HEAD carries. With
`-text` in force, `git add` stores bytes unchanged; `raw/11_staged_blob_check.txt` proves it per path
(`worktree sha == seal == staged-blob sha` for all 8) and `raw/12_chain_check_staged_index.txt`
repeats the check repo-wide against the index. Committing the restored bytes is therefore the first
moment at which HEAD agrees with the seal.

The asymmetry inside each pair (`evidence/M0_*/source.c` kept its sealed bytes,
`evidence/M0_*_UNSHACKLED_V0/source.c` did not) is **not explained** by anything measured here; both
are recorded as they are.

## 4. The 9 left failing — why repairing them is not an option

**Seven `M0_*/SHA256SUMS.txt`.** Each manifest seals *itself*: the only failing line in each is
`SHA256SUMS.txt` itself, while 6 of 6 (14 of 14 in `M0_KILLER`) sibling entries verify
(`raw/06`). No bytes can satisfy that line: the file would have to carry the SHA-256 of a file that
already carries that SHA-256. The scan found 0 worktree files and 0 repository blobs matching any of
the seven seals, and the CR-placement search returns 0 candidates. Repair would mean editing a sealed
manifest, which `AGENTS.md` §4 forbids ("Overwriting `evidence/` without new hash = chain broken").
The correct fix for the future is the convention E5/E6/E7 already follow: no self-entry. These seven
manifests stay as they are, with the failure documented rather than silenced.

**Two `EPOCH_TRANSPARENCY_V{0,1}/evidence.json`.** Whole directories are untracked (Sep 8, foreign
to this task, `raw/07`). Each manifest seals `program.op` + `evidence.json`, does **not** seal itself,
`program.op` verifies, and the sealed `evidence.json` bytes exist nowhere — not in the worktree, not in
any of the 427 blobs, not in HEAD (never committed). The most likely mechanism is reuse of one
evidence output path across runs (`AGENTS.md` §6 forbids exactly that): `V0` is stamped Sep 8 01:25,
`V1` Sep 8 03:15, each carrying a different `program.op` and a manifest that seals an `evidence.json`
neither directory now holds. That is an inference and is labelled as such. The originals are gone;
recreating them would be writing new evidence under an old hash. The directories are left
byte-for-byte untouched.

## 5. Collateral finding, larger than the 17: 127 committed blobs are their seal minus every CR

While checking the three-way chain (`seal == worktree == HEAD`) for the 303 entries that verify on
the worktree, `tools/stored_cr_analysis.py` found that **127 of them are stored in Git as the sealed
bytes with every carriage return removed** — including the 8 this experiment just restored, whose
committed versions were still LF-only before this commit. `raw/13_stored_cr_analysis.txt` lists all
127 with both hashes and both sizes; the hypothesis `HEAD == worktree.replace(CR)` holds for 127 and
fails for **0**, so a single mechanism explains all of them. Repo-wide this means:

| relation | entries |
|---|---|
| worktree == seal | 303 of 312 |
| worktree == seal, HEAD == seal | 174 before this commit |
| worktree == seal, HEAD == seal minus CR | 127 before this commit |
| worktree == seal, not in HEAD at all | 2 (`EPOCH_TRANSPARENCY_V{0,1}/program.op`, untracked dirs) |
| worktree != seal | 9 |

Two consequences that matter more than the repair itself:

1. **`git status` cannot see this.** For these paths the index entry carries the worktree's
   size and mtime while holding the LF blob, so Git treats the file as unchanged forever. Confirmed
   on `evidence/CLASSIC_ANCHOR_SMOKE_V0/anchors.txt`: worktree 70 B (seal matches), index blob 65 B,
   `git status` and `git diff HEAD` both silent. This is the same blindness that made
   `git checkout HEAD -- <path>` a no-op during E6, now measured across the whole evidence tree.
2. **`sha256sum -c` alone is not an integrity check for this repo.** It compares worktree to seal and
   passes for these 127 while the *committed* evidence differs from the seal. The three-way check is
   the one that has to run, and the published history contains LF renderings of files the seals
   describe as CRLF-terminated.

Fixing the remaining 119 (127 minus the 8 repaired here) means re-staging 119 committed evidence
files and publishing the result. That is a larger change than E7 was asked to make, so it is
**measured and reported here, not executed**; the decision is Danny's. `tools/stored_cr_analysis.py`
re-run after such a commit should print `hypothesis holds for 0 entries`.

## 6. Verification

| measure | before | after |
|---|---|---|
| sealed entries, repo-wide | 312 | 312 |
| `sha256sum -c` OK | 295 | 303 |
| `sha256sum -c` FAILED | 17 | 9 |
| entries missing on disk | 0 | 0 |

Counted with `LC_ALL=C.UTF-8 sha256sum -c` per manifest over 38 manifests, summing the `OK` /
`FAILED` verdict lines (`raw/10_tally.txt`). **Correction appended, not rewritten:** the figure
"284 verify / 17 fail" quoted during E6 came from a counter that matched lowercase hex only; 75
entries use uppercase hex, so it under-counted the total. The method above is the canonical one for
this repo, and the failure count (17 then, 9 now) is unchanged by the correction.

The repair gate (all three conditions re-checked at the moment of each write, `raw/03`):

1. current worktree bytes equal the `disk_sha256` recorded in `raw/01` — nothing changed in between;
2. a candidate exists (witness file, or the unique placement);
3. `SHA-256(candidate) == the seal in that directory's manifest`.

Anything else is refused and was. Outcome: `repaired=8 refused=9`, no `FAILED-VERIFY` row, and the 9
refusals are recorded with the reason `REFUSED-not-recoverable`.

## 7. What this does *not* claim

- No gameplay, VM, toolchain or milestone claim is made or changed by E7. This is a seal-integrity
  disposition, nothing more. `M0` status stays exactly as E3/E6 recorded it.
- The 8 repaired files are byte-equal to their seals, and their *content* is unchanged apart from
  line endings: none of them was re-executed, so "the sealed program still behaves as reported" is
  `[NOT_DEMONSTRATED]` here — it rests on the earlier M0 runs, not on this one.
- The mechanism attributed to the old Windows host (`core.autocrlf=true`) is an inference from the
  three measured byte states; the host itself is not available. `[NOT_DEMONSTRATED]`.
- The 9 remaining failures stay open. They are documented, not resolved.

## 8. Reproduction

```bash
cd <MALDOOM repo root>
python3 evidence/E7_SEAL_DISPOSITION_V0/tools/disposition.py            # read-only classify
python3 evidence/E7_SEAL_DISPOSITION_V0/tools/witness_proof.py          # read-only
python3 evidence/E7_SEAL_DISPOSITION_V0/tools/placement_proof.py        # read-only
python3 evidence/E7_SEAL_DISPOSITION_V0/tools/not_recoverable_proof.py  # read-only
python3 evidence/E7_SEAL_DISPOSITION_V0/tools/staged_blob_check.py      # read-only, needs the files staged
python3 evidence/E7_SEAL_DISPOSITION_V0/tools/chain_check.py INDEX      # read-only, 3-way vs index
python3 evidence/E7_SEAL_DISPOSITION_V0/tools/chain_check.py HEAD       # read-only, 3-way vs HEAD
python3 evidence/E7_SEAL_DISPOSITION_V0/tools/stored_cr_analysis.py     # read-only, HEAD-vs-seal CR test
# the writer is evidence/E7_SEAL_DISPOSITION_V0/tools/repair_guarded.py; it is a no-op now
# (every remaining entry is refused), and was run exactly once, producing raw/03.
```

`scripts/build_m0.py` was **not** run as a verifier: `build_m0.py:65` writes into `evidence/` in
place, which would re-drift the files this experiment just restored.

Claim status: `DEMONSTRATED` — 8 sealed entries restored under a triple guard and byte-verified;
9 sealed entries are irrecoverable, proven by exhaustive worktree and object-database search;
`DEMONSTRATED` — 127 committed evidence blobs equal their seal with every CR removed (§5), which is
the largest integrity gap found in this repo and is reported without being repaired;
`PARTIAL` — the repo-wide chain is 303/312 sealed entries verifying on the worktree, not 312/312.
