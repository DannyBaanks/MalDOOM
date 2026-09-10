# PURE_CONTINUATION_ANCHOR_V0 - FINAL

## Claim

Residual legal state produced by one uninterrupted Classic Malbolge execution
is a causal continuation substrate for later output phases. The demonstrated
scope is the generated `ABC.mal` program: one Zig VM, no input, no host state
injection, output `A -> B -> C -> HALT`.

This is not a claim that every legal residual state, every program, or every
translator anchor has that property.

This is a TARGET_B Classic-Malbolge micro-experiment, not a MALDOOM M0-M7
milestone and not an integration into the MALDOOM Doom runtime. It must not be
cited as evidence for Full Doom, TARGET_A, or a host-computation claim.

## Artifacts

`programs/` contains direct-text Classic Malbolge sources generated with the
proven fast generator:

```powershell
py -m malbolge_translator.cli <TEXT> --direct --no-lexicon --seed 42 \
  --output-dir <dir> --base-name <name>
```

The observer and causal-control harness is the Zig Classic engine executable:
`Malbolge-Translator/zig/zig-out/bin/malbolge-pca.exe`.

| Program | Cells | SHA-256 | Generated output |
|---|---:|---|---|
| `A.mal` | 232 | `F1ADE8C1BA89AD1C26903C5D14D887B44C177B87A5D3D9FE34538D3313232794` | `A` |
| `AA.mal` | 219 | `C5D21AA0E143C6CF0C23C6B8400F40D851261D59E3EB9E86394189AEBE5A7DE3` | `AA` |
| `AB.mal` | 212 | `BFF777A5822BE15B5BD42DBD2981792F919BD3D4187F3CE24C554F379014B576` | `AB` |
| `ABC.mal` | 333 | `17A66954C6D83017AEC6FF5CDF7621C9703BB17BFC8075AAF911EFCB10397B7D` | `ABC` |

The source hashes are duplicated in `SHA256SUMS.txt`.

## Ladder

Command executed for each row:

```powershell
& $pca <program.mal> 200000 ""
```

| Program | Result | Steps | Phase boundaries |
|---|---|---:|---|
| A | `A`, halted | 134 | `A` step 133, hash `1a0451fa735504f2b9bcda3627a336ba30f29aa2d8f6a650fcb2a88ecd16b4a1` |
| AA | `AA`, halted | 121 | `A` step 118; `A` step 120 |
| AB | `AB`, halted | 114 | `A` step 109; `B` step 113 |
| ABC | `ABC`, halted | 235 | `A` step 103; `B` step 181; `C` step 234 |

The full `ABC` receipt from the Zig harness was:

```text
status=halted steps=235
output_len=3 output=ABC
final a=29507 c=332 d=234
writes: enc=234 crazy=76 rotate=68 dload=0
phases=3
  phase[0] byte=0x41 step=103 a=65 c=200 d=102 hash=d0158a11063e4f5abc5f0421a5dee3c81a71a9b8472e2a0eaf56b0f4b9d1e1a8
  phase[1] byte=0x42 step=181 a=66 c=278 d=180 hash=f972a9125eebf37a8ffbfac58258568589c860469298aa53021d2034c284f612
  phase[2] byte=0x43 step=234 a=29507 c=331 d=233 hash=6aba6d8df353c411f00347b9c252b6e2c63d2245f485221c971c464065760cb4
```

Each transition happens in that single original VM run. No snapshot, restart,
or host injection occurs in the observed `ABC` execution.

## Causal Control

`malbolge-pca perturb` intentionally snapshots the legal post-output state and
resumes it twice. This is a separate counterfactual control, not part of the
uninterrupted core claim. The harness prints phase indices from zero, so its
`S_0` after phase 0 is the report's semantic S1 (the state after `A`).

| Residual state | Unperturbed continuation | Mandatory next instruction | Injected source value | Perturbed continuation | Verdict |
|---|---|---|---:|---|---|
| S1 after `A` in ABC | `BC`, halted in 132 steps | `c=201` | `68` (decodes to HALT at 201) | empty output, halt in 1 step | PASS |
| S2 after `B` in ABC | `C`, halted in 54 steps | `c=279` | `84` (decodes to HALT at 279) | empty output, halt in 1 step | PASS |

Executed controls:

```powershell
& $pca perturb programs/ABC.mal 0 201 68 200000 ""
# CONTROL output=BC; PERTURB output=; PERTURBATION_DIVERGENCE=PASS

& $pca perturb programs/ABC.mal 1 279 84 200000 ""
# CONTROL output=C; PERTURB output=; PERTURBATION_DIVERGENCE=PASS
```

The injected values are source-cell values, not raw opcode numbers. Classic
Malbolge decodes `op = (mem[c] + c) mod 94`; thus raw `62` does not mean HALT
at arbitrary `c`. At `c=201`, `68` decodes as opcode 81 (HALT); at `c=279`,
`84` does likewise.

## Positional Audit

The Zig `trace` mode records `c_before`, `d_before`, `read_addr`, writes,
encryption, jump target, `c_after`, and `d_after`. It corrected an earlier
observer bug risk: MOVD now reports its operand address from `d_before`, not
from the already-mutated `d`.

Relevant `ABC` observations:

```text
step=1 op=chase c_before=0 d_before=0 read@0=98 J->98 c_after=99 d_after=1
step=103 op=out c_before=200 d_before=102 ... c_after=201 d_after=103
step=104 op=nop c_before=201 d_before=103 enc@201=55->110 c_after=202 d_after=104
step=106 op=nop c_before=203 d_before=105 enc@203=53->45 c_after=204 d_after=106
step=181 op=out c_before=278 d_before=180 ... c_after=279 d_after=181
step=182 op=nop c_before=279 d_before=181 enc@279=71->83 c_after=280 d_after=182
step=193 op=rot c_before=290 d_before=192 read@192=93 write@192=93->31 enc@290=125->105 c_after=291 d_after=193
step=204 op=rot c_before=301 d_before=203 read@203=45 write@203=45->15 enc@301=114->125 c_after=302 d_after=204
```

Therefore addresses 203 and 290 were not dead: 203 was executed and later
read as data; 290 was executed as ROT. The previous `62` injection was
semantically neutral at those positions because it decoded to an invalid/NOP
opcode there, not to HALT. The source-position congruence is part of the
control specification.

## Boundaries

- `ENCRYPTION_IMMUNE` is not `MUTATION_IMMUNE`: encryption only applies to
  printable cells, while ROT and CRAZY may still mutate non-printable values.
- The generator's reported `anchors: ["default"]` is its own generation term;
  it is not evidence that it enforces graph-articulation anchors for arbitrary
  programs.
- The tested mandatory cells are local instruction edges for this `ABC`
  program. A general compiler pass that forces intermediate anchors through
  articulation points remains NOT_DEMONSTRATED.
- The causal control validates necessity under these specified perturbations.
  It does not establish a universal causal theory of all Classic Malbolge
  residual states.

## Roadmap To A Reproducible Demonstration

Absolute proof for every Classic Malbolge program is out of scope. The target
is a falsifiable, hash-pinned demonstration for a specified program family,
specified engines, and specified perturbation suite.

### Current Milestone Status

| Milestone | Status | Evidence |
|---|---|---|
| R1 Freeze the claim surface | `PASS` | `evidence/PURE_CONTINUATION_ANCHOR_V0/R1_R2_MANIFEST.json`; all listed hashes validate |
| R2 Canonical positional receipts | `PASS` | `ABC.trace.jsonl`: 235 valid JSONL records; `tools/validate_pca_trace.py` reports `R2_REPLAY=PASS` |
| R3 Single uninterrupted VM run | `PASS` | `R3_ABC.raw.txt`: one memory load, one VM initialization, zero snapshots and host injections |
| R4 Automate causal controls | `PASS` | `R4_controls.json`: 9/9 controls diverge with expected unperturbed tails |
| R5 Dynamic flow map | `PASS` | `R5_flow.json`: 235-step graph with classifications, paths and jump edges; universal articulation remains NOT_DEMONSTRATED |
| R6 Independent engine checks | `PASS` | `R6_engine_crosscheck.json`: Python canonical and independent C VM agree on 4/4 programs |
| R7 Expand program family | `PASS` | `R7_full_family.json`: ABA, AAB and ABC_seed99 pass the complete automated R3-R6 family battery |
| R8 Anchor-isolated generation | `PASS` (measured subset) | `R8_anchor_isolation.json`: 10 phase anchors across 6 programs pass dynamic isolation; general generation remains `NOT_DEMONSTRATED` |
| R9 Final claims and closure | `PASS` | `R9_final_claims.json`: 32 hashes checked; 4 scoped claims PASS, 3 universal claims NOT_DEMONSTRATED |

### R1. Freeze The Claim Surface

- Record SHA-256 for source programs, the Zig engine, `pca.zig`, generator,
  and produced executables.
- Record Zig version, host OS, exact commands, exit codes, and timestamps.
- Store each experiment in a new evidence directory; never overwrite a prior
  receipt.
- Gate: every current claim names a hash and an executable version.

### R2. Canonical Positional Receipts

- Add JSONL emission to `malbolge-pca trace` with one receipt per step:
  `step`, `a_before`, `c_before`, `d_before`, `opcode`, `read_addr`,
  `read_value`, `write_addr`, `write_before`, `write_after`, `enc_addr`,
  `enc_before`, `enc_after`, `jump_target`, `a_after`, `c_after`, `d_after`.
- Hash the complete trace and build indexes by read, write, execution, and
  phase boundary address.
- Gate: a replay of the receipt recreates the observed control output and
  final registers, or reports FAIL.

### R3. Prove One Uninterrupted VM Run

- Add a test observer that counts memory loads, VM initializations, snapshots,
  and host injections while executing `ABC`.
- Require exactly one memory load and one VM initialization; require zero
  snapshots/reloads/injections between the first `A` and final HALT.
- Gate: `SINGLE_VM_UNINTERRUPTED_EXECUTION=PASS` only when all counters match.

### R4. Automate Causal Controls

- For each residual state S1 and S2, resume an exact snapshot unmodified and
  require the expected remaining output.
- Perturb a mandatory next instruction using
  `sourceForOpcode(position, opcode)`, not a raw opcode value.
- Perturb at least one actually-read data cell before the next output.
- Test at least three distinct non-neutral values per selected cell.
- Gate: the unperturbed control matches exactly and every declared causal
  perturbation diverges. A neutral perturbation is recorded as a negative
  control, not discarded.

Executed matrix:

```powershell
cd C:\Development\ISyCo Git\MALDOOM
py tools\validate_pca_controls.py evidence\PURE_CONTINUATION_ANCHOR_V0\programs\ABC.mal evidence\PURE_CONTINUATION_ANCHOR_V0\binaries\malbolge-pca.exe
# R4_CONTROLS=PASS cases=9
```

The receipt is `evidence/PURE_CONTINUATION_ANCHOR_V0/R4_controls.json`.

### R5. Dynamic Flow Map

- Construct the observed control-flow graph from the positional trace.
- Classify every relevant cell as executed instruction, data read, data write,
  encryption write, jump target, or unvisited.
- Identify phase-to-phase dynamic cut candidates only by graph analysis; do
  not call any address an articulation point merely because it appears between
  two source offsets.
- Gate: every selected mandatory anchor has an evidence-backed path statement.

Executed:

```powershell
py tools\analyze_pca_flow.py evidence\PURE_CONTINUATION_ANCHOR_V0\ABC.trace.jsonl evidence\PURE_CONTINUATION_ANCHOR_V0\R5_flow.json
# R5_FLOW=PASS steps=235 phases=3 jumps=1 addresses=300
# R5_203=['executed_instruction', 'data_read', 'data_written', 'encryption_written']
# R5_290=['executed_instruction', 'encryption_written']
```

The graph is a dynamic receipt of this run. It is not a proof of articulation
anchors for arbitrary programs.

### R6. Independent Engine Checks

- Run the same immutable source programs through the Zig engine, canonical
  Python interpreter, and independent C/oracle backend where available.
- Compare output, halt status, and step count. Compare positional receipts only
  where the backend exposes equivalent instrumentation.
- Gate: disagreement is FAIL for the corresponding narrow claim, not silently
  normalized away.

Executed:

```powershell
py tools\validate_pca_engines.py evidence\PURE_CONTINUATION_ANCHOR_V0\programs "C:\Development\ISyCo Git\Malbolge-Engine\malbolge.exe"
# R6_ENGINE_CROSSCHECK=PASS cases=4
```

The receipt is `evidence/PURE_CONTINUATION_ANCHOR_V0/R6_engine_crosscheck.json`.

### R7. Expand The Program Family

- Generate and retain independently hashed cases: `ABA`, `AAB`, and at least
  one 4-8 byte program from a different seed.
- Apply R3-R6 to each case.
- Gate: report the exact pass count and keep failures. Do not generalize from
  `ABC` alone.

Current run:

```powershell
py tools\validate_pca_family.py evidence\PURE_CONTINUATION_ANCHOR_V0\programs "C:\Development\ISyCo Git\Malbolge-Translator\zig\zig-out\bin\malbolge-pca.exe" ABA AAB ABC_seed99
# R7_PCA_FAMILY=PASS cases=3
py tools\validate_pca_engines.py evidence\PURE_CONTINUATION_ANCHOR_V0\programs "C:\Development\ISyCo Git\Malbolge-Engine\malbolge.exe" ABA AAB ABC_seed99
# ENGINE_CROSSCHECK=PASS cases=3
```

The full family runner is:

```powershell
py tools\validate_pca_family_full.py evidence\PURE_CONTINUATION_ANCHOR_V0\programs "C:\Development\ISyCo Git\Malbolge-Translator\zig\zig-out\bin\malbolge-pca.exe" "C:\Development\ISyCo Git\Malbolge-Engine\malbolge.exe" ABA AAB ABC_seed99
# R7_FULL_FAMILY=PASS cases=3
```

### R8. Anchor-Isolated Generation

- Only after R5, add an optional generator constraint that places a phase
  boundary before an observed mandatory dynamic instruction edge.
- Reject candidates whose proposed next phase can be skipped by a `chase` in
  the measured run.
- Verify every accepted candidate with the real engine; the search model is a
  proposer, never the acceptance authority.
- Gate: label this `ANCHOR_ISOLATED_GENERATION=PASS` only for the measured
  subset. General generation remains `NOT_DEMONSTRATED` until coverage exists.

Executed measured-subset gate:

```powershell
py tools\validate_anchor_isolation.py evidence\PURE_CONTINUATION_ANCHOR_V0\programs "C:\Development\ISyCo Git\Malbolge-Translator\zig\zig-out\bin\malbolge-pca.exe" AA AB ABC ABA AAB ABC_seed99
# status=PASS; 6 programs; 10 phase anchors; zero chase crossings
```

The receipt records the exact mandatory next-`c` cell and the position-aware
HALT source value for every phase transition. This validates isolated anchors
for the measured family; it does not establish a universal generator property.

### R9. Final Claims Table

- `PASS`: the concrete `ABC` run contains A, B, C and HALT in one VM run, and
  selected S1/S2 perturbations demonstrably alter the future output.
- `NOT_DEMONSTRATED`: every residual state, every Classic program, universal
  articulation anchors, or a universal causal theory.
- `FAIL`: any hash mismatch, extra VM load, host injection, engine divergence,
  or failed control that contradicts a claimed guarantee.

Executed:

```powershell
py tools\finalize_pca_claims.py evidence\PURE_CONTINUATION_ANCHOR_V0 evidence\PURE_CONTINUATION_ANCHOR_V0\R9_final_claims.json
# R9_FINAL=PASS hashes=32 claims=7
```

The machine-readable final table is
`evidence/PURE_CONTINUATION_ANCHOR_V0/R9_final_claims.json`.

## Verification

```powershell
cd C:\Development\ISyCo Git\Malbolge-Translator\zig
zig build
zig test src\generator.zig
zig test src\pca.zig
cd C:\Development\ISyCo Git\MALDOOM
py tools\validate_pca_trace.py evidence\PURE_CONTINUATION_ANCHOR_V0\ABC.trace.jsonl evidence\PURE_CONTINUATION_ANCHOR_V0\programs\ABC.mal evidence\PURE_CONTINUATION_ANCHOR_V0\binaries\malbolge-pca.exe
# R2_REPLAY=PASS lines=235 output=ABC final=(29507, 332, 234)
```

Observed: `zig build` passed; generator plus engine tests passed 8/8; the PCA
module compiled under `zig test` (0 direct tests); receipt replay passed; R3
single-VM audit passed with `ABC` and empty stdin; R4 causal matrix passed
9/9.
