# E5 — why LMFAO `.mu` images break on fixed-19 engines: the loader convention, not the semantics

**Sealed 2026-10-15.** Host Ubuntu 24.04 (Linux `7.0.0-38-generic`), x86_64, zig 0.16.0, gcc 13.3.0.
Question (option (b) of the three-engine cross-test): `bolge19` and `fast20_fixed` agree with each other
and emit `02ce` (garbage) on `evidence/M0_KILLER_UNSHACKLED_V0/artifact.mu`, while the canonical
Unshackled VM emits the sealed oracle `310a`. Why?

## Answer (DEMONSTRATED, with controls)

**Root cause is the loader, not the epochal semantics.** `fast20.c` / `bolge19` map *every byte of the
file* to one cell. The canonical Unshackled loader:
- skips `' ' \t \r \n`;
- requires `33 <= v < 127`;
- requires `(v + pos) % 94` to be an instruction opcode `{4,5,23,39,40,62,68,81}`;
- increments `pos` (mod 564) **only for accepted cells**.

`artifact.mu` is 2,888,171 bytes; the **last two** (`CR@2888169`, `LF@2888170`) are whitespace. The
intolerant loader appends two junk cells and — decisively — **seeds the epochal crazy-chain from those
junk cells**, corrupting every cell past the image:

```
intolerant loader :  pat=[10, 581130723, 10, ...]   <- seeded from the LF/CR
canonical loader  :  pat=[81, 581130652, 81, ...]
```

LMFAO's relocation machinery reads that chain, so the trajectory collapses to `02ce` within ~20k steps.

Fixtures (`make_fixtures.py` regenerates both from the sealed image):
- `artifact_trunc.mu` = image minus its 2 trailing whitespace bytes (sha `fd390dd4…`, 2,888,169 B);
- `artifact_tol.mu` = the 2,888,169 code chars **+ 5** whitespace bytes ` \r\n\t\n` (sha `0c8c85fb…`)
  — a tolerance probe, not just a 2-byte trim.

| engine / config | image | stdout (in=0) | steps |
|---|---|---|---|
| `bolge19` unmodified | `artifact.mu` | `02ce` | 20,163 |
| `bolge19` unmodified | `artifact_trunc.mu` | **`310a`** | 8,623,625 |
| `bolge19` unmodified | `artifact_tol.mu` (5 junk bytes) | *(empty)* | — |
| canonical pinned VM (E4 pin 10/3/5/det=1) | `artifact_tol.mu` | **`310a`** | 10,347,959 |
| `b19var` `B19_TRIM=1` (canonical loader ported) | `artifact_tol.mu` | **`310a`** | 8,623,625 |

**5/5 on all sealed killer inputs** (`310a 330a 350a 370a 390a`, LF-only per the E4/M0 CR finding) for
three independent routes: (1) `bolge19` + `artifact_trunc.mu`; (2) `fast20_fixed` + `artifact_trunc.mu`;
(3) `b19var TRIM=1` + the full untruncated `artifact.mu`. Route 3 is deterministic across 3 repeats
(8,623,625 steps, `310a`).

## Two image conventions, not one bug (the sharper finding)

The census (`raw/09_specimen_census.txt`, `raw/10_convention_matrix.txt`) shows the fixed-19 engines are not
merely "buggy" — **two incompatible image conventions exist in the tree, and no engine here implements both**:

| specimen | bytes | whitespace | strict (text) loader | raw (byte-per-cell) loader |
|---|---|---|---|---|
| `artifact.mu` (LMFAO `.mu`) | 2,888,171 | 2, at EOF | **`310a` oracle** ✓ | `02ce` garbage, halts @20,163 ✗ |
| `init_module.mb` | 19,392 | 1, at EOF | halts @19,301 ✓ | halts @**19,337** ✓ |
| `core.mb` (MalbolgeLISP epochal core) | 371,312,023 | **0** | **aborts** `invalid character byte=7 v=99 instr=12` ✗ | runs ✓ |
| `lisp.mb` | 371,331,415 | 1, **MID-FILE** @19,391 | **aborts** `invalid character byte=19392 v=40 instr=67` ✗ | runs ✓ |

Controls: `lisp.mb` is *exactly* `init_module.mb || core.mb` (`19,392 + 371,312,023 = 371,331,415`, and
`lisp[:19392] == init_module`, prefix-verified here, full-concatenation hash equality verified separately).
The strict-rule prediction from the census (first non-opcode core byte at **core-offset 0**, `value=40
instr=67`) matches the engine's *runtime* rejection (file byte 19,392, `v=40 instr=67`) — static and dynamic
agree.

So LMFAO emits **opcode-aligned text** (`.mu`, `.mb` init module) while the MalbolgeLISP epochal core is a
**raw cell dump**. The three-engine cross-test compared the *raw* convention against the *text* convention and
recorded the difference as a semantic divergence between engines. It was a container mismatch: `bolge19` and
`fast20_fixed` were **right** about `lisp.mb`/`core.mb` and **wrong** about `artifact.mu`, agreeing with each
other because they share a loader.

### Provenance of the forensics repo's "exactly 19,337 steps"

That headline number is now identified: it is `init_module.mb` halted under the **raw** loader
(`steps=19337 c=19435 d=19 a=710270897`, `raw/11_init_module_loaders.txt`). Under the canonical strict loader
the same bytes give **19,301 steps** and completely different final registers
(`c=19399 d=387450038 a=182815712`). The two engines agreed at 19,337 because they share a convention, not
because either was validated against Unshackled. This closes the open question "how was the 19,337 column
actually produced".

### Why `artifact_tol.mu` and `lisp.mb` fail differently

`artifact.mu`'s whitespace is at **EOF**, so dropping it displaces nothing — that is why a 2-byte pre-trim
restores 5/5. `lisp.mb`'s single LF is at **the seam between the init module and the core**, so raw loading
keeps a junk cell at 19,391 and shifts the entire 371 MB core one cell late relative to the canonical load.
**A trim is only a valid repair for trailing whitespace; a mid-file byte needs the loader port.**

## What is NOT the cause (measured — `semantic_sweep_152.tsv`)

152-config sweep. Columns: `w` = rotation window in trits, `io` = 0 raw / 1 canonical sentinels,
`trim` = canonical loader, `offs` = 0 fast20 per-region offsets active / 1 offsets zeroed.
**Matches occur only where `trim=1 ∧ offs=0 ∧ w ∈ {14..19}`.**

- **I/O convention is NOT load-bearing here.** `io=0` and `io=1` rows are byte-identical (same steps).
  Raw mode reaches the same output by a different route: the LF read is the literal 10 that gets printed.
  This **refutes** the leading hypothesis recorded in the cross-test (that the newline/EOF encoding was
  the divergence).
- **The rotation window has a floor, but is not the wall.** Fixed windows `w ≤ 13` never match; `w ≥ 14`
  do. Consistent with the canonical VM starting `rotwidth = 10+rand()%6` and *growing* (E4: 10 → 20) —
  a fixed small window cannot substitute for epochal growth. Steps by window: 14→9,852,167; 15→5,995,542;
  16→6,912,647; 17→7,759,736; 18→8,623,625; 19→9,484,189.
- **`offs[]` ARE load-bearing**: zeroing them gives 0/5.

## `offs[]` resolved from first principles (was an open "quirk")

`Unshackled.c` decodes with `pos = mod(c, 564)`, and its `mod()` is
`value − head·(3^w−1)/2 + head·(29524 mod m)  (mod m)`. For a 19-trit ring with `head = region = c/3^18`:

```
head=0 -> 0  mod 94       head=1 -> 23  mod 94       head=2 -> 46  mod 94
fast20/bolge19 offs      = 0, 117, 140   ->  mod 94 = 0, 23, 46     # exact match
```

So the per-region offsets are the **sign-class (`head`) correction** of the canonical instruction pointer,
not a hack — `region` *is* the 3-adic sign class of the address. This also means the earlier reading
"canonical decode is just `(mem[c]+c)%94`, so the offsets are a fast20 deviation" is **wrong**: that form
holds only for `head = T0`.

## Cost (relevant to MALDOOM's tick wall)

- `bolge19`: 8,623,625 steps in **0.09–0.10 s** ⇒ ~87–96 M steps/s, deterministic, native.
- Canonical pinned VM (E4): 10,347,959 steps in 1.518–1.543 s ⇒ ~6.7–6.8 M steps/s.

**≈14× faster** than the bignum reference VM, with no rotwidth lottery. A Doom tick estimated at
1e10–1e12 steps moves from *hours* to roughly **2 min–3 h** at this throughput. That is one order of
magnitude recovered, **not** the two or three needed for real-time play — the wall stands, it just moves.

## Scope / NOT_DEMONSTRATED

- `bolge19`+trim is an **equivalent for this artifact, not a faithful epochal emulation**: its step count
  (8.62 M) differs from the pinned canonical (10.35 M), and per-input deltas differ.
- NOT_DEMONSTRATED: that `w ≥ 14` suffices for *other* LMFAO images — only the sealed M0_KILLER artifact
  was run through the sweep.
- NOT_DEMONSTRATED: that fast20's fixed-18 `mrot` (which pins trit 18 while `mcrz` spans 19) is harmless
  in general; it happens not to matter for this artifact.
- NOT_DEMONSTRATED: that `fast20_fixed`'s step counter is usable — it printed ~1.05e14 for a ~10 M-step
  run (broken counter). Its stdout and final registers (`c=581135934 d=581139251 a=10`) match `bolge19`
  exactly, so the *behaviour* agrees even though the *count* does not.
- The sealed `artifact.mu` (sha `3b9bdf37…`) was **not modified**; every experiment ran on scratch copies.
  Whether its trailing CRLF came from LMFAO on the Windows build host or from repo handling is
  NOT_DEMONSTRATED here.

## Reproduce

`commands.txt` (exact commands, from the scratch dir) and `e5_capture.sh` (parameterised re-run that
writes to its own scratch dir and cannot overwrite `raw/`). Binaries are pinned by sha in `hashes.txt`.
