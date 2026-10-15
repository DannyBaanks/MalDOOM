# Repair executed — 2026-10-15 (approved by Danny: "Sí, repara los 32")

## what was attempted first, and why it silently did nothing

    git checkout HEAD -- <each of the 32 paths>       # exit 0, no output

**It was a no-op on all 32 files.** Disk hashes were still the drifted CRLF bytes
(`worktree_sha256` of `drift_snapshot.tsv`) and `git status` stayed empty. Reason,
measured: `git checkout <tree-ish> -- <path>` copies the blob into the index and
then into the worktree, but the index entry already held the correct LF blob
(`git ls-files -s` == `git rev-parse HEAD:<path>`), and git's second-phase check is
**stat-based**: with `* -text` and a matching size/mtime record it concludes the
worktree is up to date and never writes. This is the same blindness as
`mech_proof_git_blindness.txt`, now on the *restore* side — so the command proposed
in this document before the repair was insufficient, and that is recorded here
rather than quietly rewritten.

## what actually repaired

Per path, read the bytes, apply the recorded rule `CRLF -> LF`, and only then write:

1. assert `SHA-256(disk) == worktree_sha256` of `drift_snapshot.tsv` (nothing else touched the file since the audit);
2. `new = disk.replace(b"\r\n", b"\n")`;
3. assert `SHA-256(new) == seal == HEAD`;
4. write to `<name>.repairtmp` in the same directory and `os.replace()` onto the file.

Refusal-by-default: any file failing step 1 or 3 was left untouched and printed.

## result

- repaired 32 / refused 0 / already-canonical 0; no `.repairtmp` left anywhere.
- 163,678 -> 160,982 bytes, exactly 2,696 CR bytes removed — the predicted figure.
- `SHA-256(disk) == SHA-256(git show HEAD:<path>)` for **32/32**.
- `sha256sum -c` in the 13 directories: the 32 repaired entries now pass. Remaining
  failures are the pre-existing 7 `M0_*_UNSHACKLED_V0/source.c` (group 5, mixed seal —
  not part of this repair, not approved, still documented).
- `git status` initially showed ` M` for all 32 while `git diff` was **empty**
  (0 content diffs): purely stale index stat, since the bytes now equal the blob.
  `git add -- <the 32 paths>` refreshed those entries; afterwards
  `git diff --cached --name-only` = 0 and `git status -uno` = 0. Nothing was staged
  relative to HEAD, so no commit of the repair is needed or possible.

## post-repair census (`raw_audit_post_repair.tsv`)

`witness_search.py` was re-run too and its output is **byte-identical** to
`witness_search.tsv` (`diff -q` empty) — expected, because none of the 32 repaired
files was ever a `CONTENT` row; the duplicate was not kept.

| group | before | after |
|---|---|---|
| `exact` / `exact` (byte-exact chain) | 99 | **131** (99 + the 32) |
| `crlf_to_lf` / `exact` (drifted worktree) | 32 | **0** |
| `exact` / `lf_to_crlf` (commit is LF rendering) | 103 | 103 — untouched by design |
| `exact` / `CONTENT` (commit partially converted) | 13 | 13 — untouched by design |
| `CONTENT` / `CONTENT` (mixed seal or self-hash) | 15 | 15 |
| `exact` / `UNTRACKED` | 24 | 35 (24 + this directory's own 11) |
| `CONTENT` / `UNTRACKED` | 2 | 2 |
| manifests found / entries audited | 32 / 288 | 33 / 299 |

`git_says` is `git_clean` on all 299 rows, as before — the repair is invisible to
`git status` in exactly the same way the drift was, which is the point of E6.

## what this does NOT fix

- The 103 + 13 commit-side renderings: their seals verify against the worktree, so
  restoring them from `HEAD` would break a good seal. Left as-is, deliberately.
- The 7 `M0_*/SHA256SUMS.txt` self-hashing lines.
- The 7 mixed `M0_*_UNSHACKLED_V0/source.c`: their exact sealed bytes do exist in
  `engine/M0_*.c`, so a repair is *possible*, but it is a different action with a
  different evidence question attached. Not performed; ask first.
- The 2 untracked `EPOCH_TRANSPARENCY_V{0,1}/evidence.json`.
