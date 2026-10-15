#!/bin/bash
# E5 — loader-whitespace capture, parameterised to the repo root.
#
# Builds every engine from a source whose sha256 is checked first, so patching a
# sibling repo cannot silently invalidate this evidence: if a source has drifted
# the phase is SKIPPED with a line in the log, never run against a different build.
# OUT defaults to a scratch dir, so re-running can never overwrite ./raw.
set -u
E5_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="${REPO:-$(cd "$E5_DIR/../.." && pwd)}"
AM="$REPO/evidence/M0_KILLER_UNSHACKLED_V0/artifact.mu"
FORENSICS="${FORENSICS:-/home/danny/Development/ISyCo Git/malbolge-lisp-forensics}"
WORK="${E5_WORK:-$(mktemp -d /home/danny/tmp_e5_XXXXXX)}"
OUT="${E5_OUT:-$WORK/raw}"
mkdir -p "$OUT"
cd "$WORK" || exit 1

expect() { # sha path label -> 0 if match
  [ "$(sha256sum "$2" | cut -d' ' -f1)" = "$1" ] || { echo "SKIP $3: $2 drifted from $1"; return 1; }
}

expect 3b9bdf37eb708ec751d10f0dea32edde4375e526ce56fd2dd440f5a22819ba10 "$AM" "artifact.mu" || exit 1

# --- build engines from pinned sources ---
B19=./bolge19; F20=./fast20_fixed; PIN=./unsh_pinned; VAR=./b19var
expect cd77fdfc4e1ec6bf30fa9370cbcd633cac55db2f825f1a27b1f8a576e4521bc0 "$E5_DIR/bolge19_upstream.zig" "bolge19 src" \
  && zig build-exe "$E5_DIR/bolge19_upstream.zig" -O ReleaseFast -lc -femit-bin="$B19" >/dev/null || { echo "SKIP bolge19 build"; build_ok=0; }
expect 84d30e53c77c42eeaa18f0388f70428f9a561c966781ef95620f1f14d2e1201f "$E5_DIR/b19var_main.zig" "b19var src" \
  && zig build-exe "$E5_DIR/b19var_main.zig" -O ReleaseFast -lc -femit-bin="$VAR" >/dev/null || { echo "SKIP b19var build"; build_ok=0; }
expect 941d5bbd4ffca009f3284ff951ba96ef38194ecf0347413ca3604a23a481659a "$REPO/evidence/E4_VM_CONFIG_PINNED_V0/unsh_pinned.c" "unsh_pinned src" \
  && gcc -O2 -w -o "$PIN" "$REPO/evidence/E4_VM_CONFIG_PINNED_V0/unsh_pinned.c" || { echo "SKIP unsh_pinned build"; }
expect 76b32d5fab6ec39301b1fc0fac20bea321d0c5918d424c8fcfbec18f89a36f26 "$FORENSICS/src/patches/fast20_fixed.c" "fast20_fixed src" \
  && gcc -O3 -w -o "$F20" "$FORENSICS/src/patches/fast20_fixed.c" || { echo "SKIP fast20_fixed build"; }

# --- fixtures (regenerated, never stored) ---
python3 "$E5_DIR/make_fixtures.py" "$WORK" | tee "$OUT/00_fixtures.txt"
TR=artifact_trunc.mu; TOL=artifact_tol.mu

# --- phase 01: the bug, and the oracle it disagrees with ---
{ for i in 0 1 2 3 4; do
    printf '%s\n' "$i" | "$B19" "$AM" 2>/dev/null | xxd -p | tr -d '\n' | sed "s/^/bolge19  sealed_in=$i  /"
    echo
  done; } > "$OUT/01_bolge19_on_sealed.txt" 2>&1

# --- phase 02: route 1 - pre-trim the image, unmodified bolge19 ---
{ for i in 0 1 2 3 4; do
    o=$(printf '%s\n' "$i" | "$B19" "$TR" 2>/dev/null | xxd -p | tr -d '\n')
    e=$(printf '%s\n' "$i" | "$B19" "$TR" 2>&1 >/dev/null | sed -n 's/.*[Hh]alt steps=\([0-9]*\).*/\1/p')
    printf 'trim_bolge19  in=%s  stdout=%s  steps=%s\n' "$i" "$o" "$e"
  done; } > "$OUT/02_trim_bolge19_5of5.txt" 2>&1

# --- phase 03: route 1b - same fixture on fast20_fixed (stdout + final registers) ---
{ for i in 0 1 2 3 4; do
    o=$(printf '%s\n' "$i" | "$F20" "$TR" 2>/dev/null | xxd -p | tr -d '\n')
    printf 'trim_fast20   in=%s  stdout=%s\n' "$i" "$o"
  done; } > "$OUT/03_trim_fast20.txt" 2>&1

# --- phase 04: the tolerance control - 5 junk bytes, three loaders ---
{ O=$(mktemp ./tol.o.XXXXXX); E=$(mktemp ./tol.e.XXXXXX)
  printf '0\n' | UNSH_SEED=7 UNSH_ROTWIDTH=10 UNSH_GROWTH_SLACK=3 UNSH_GROWTH_STEP=5 UNSH_DET_GROWTH=1 \
    "$PIN" "$TOL" >"$O" 2>"$E"
  printf 'canonical_loader (E4 pin)   stdout=%s  %s\n' \
    "$(xxd -p "$O" | tr -d '\n')" "$(grep -o 'STEPS [0-9]*' "$E" | head -1)"
  : > "$O"; printf '0\n' | "$B19" "$TOL" >"$O" 2>/dev/null
  printf 'intolerant_loader (bolge19) stdout=%s  <- the bug, same file\n' "$(xxd -p "$O" | tr -d '\n')"
  : > "$O"; printf '0\n' | B19_TRIM=1 "$VAR" "$TOL" >"$O" 2>"$E"
  printf 'ported_loader (b19var TRIM) stdout=%s  %s\n' \
    "$(xxd -p "$O" | tr -d '\n')" "$(grep -o 'halt steps=[0-9]*' "$E" | head -1)"
  rm -f "$O" "$E"; } > "$OUT/04_tolerance_control.txt" 2>&1

# --- phase 05: route 2 - loader port on the FULL untruncated sealed image, 5/5 + determinism ---
{ for i in 0 1 2 3 4; do
    o=$(printf '%s\n' "$i" | B19_TRIM=1 "$VAR" "$AM" 2>/dev/null | xxd -p | tr -d '\n')
    e=$(printf '%s\n' "$i" | B19_TRIM=1 "$VAR" "$AM" 2>&1 >/dev/null | sed -n 's/.*[Hh]alt steps=\([0-9]*\).*/\1/p')
    printf 'port_bolge19  in=%s  stdout=%s  steps=%s\n' "$i" "$o" "$e"
  done
  for r in 1 2 3; do
    o=$(printf '0\n' | B19_TRIM=1 "$VAR" "$AM" 2>/dev/null | xxd -p | tr -d '\n')
    e=$(printf '0\n' | B19_TRIM=1 "$VAR" "$AM" 2>&1 >/dev/null | sed -n 's/.*[Hh]alt steps=\([0-9]*\).*/\1/p')
    printf 'rep=%s  stdout=%s  steps=%s\n' "$r" "$o" "$e"
  done; } > "$OUT/05_port_full_image.txt" 2>&1

# --- phase 06: throughput ---
{ for r in 1 2 3; do
    /usr/bin/time -f "trim_bolge19_wall=%e" sh -c "printf '0\n' | '$B19' '$TR' >/dev/null" 2>>"$OUT/06_throughput.txt"
  done
  for r in 1 2 3; do
    /usr/bin/time -f "pinned_canonical_wall=%e" sh -c \
      "printf '0\n' | UNSH_SEED=7 UNSH_ROTWIDTH=10 UNSH_GROWTH_SLACK=3 UNSH_GROWTH_STEP=5 UNSH_DET_GROWTH=1 '$PIN' '$AM' >/dev/null" 2>>"$OUT/06_throughput.txt"
  done; } 2>&1 | tee -a "$OUT/06_throughput.txt" >/dev/null

# --- phase 07: offs[] derivation, pure arithmetic ---
python3 - > "$OUT/07_offs_derivation.txt" <<'PY'
m=564
for r in (0,1,2):
    print(f"head={r} canonical mod() -> {(-r*((3**19-1)//2) + r*(29524 % m)) % m % 94} mod 94")
END=1162261467; T=END//3
a1=94-((END-1)//6-29524)%94; a2=94-((END-1)//3-59048)%94
print("fast20 offs =", 0, (a1-T)%94+94, (a2-2*T)%94+94, "-> mod 94 =", 0, ((a1-T)%94+94)%94, ((a2-2*T)%94+94)%94)
PY

# --- phase 08 (opt-in): the 152-config semantic sweep, ~4 min single-threaded ---
if [ "${E5_SWEEP:-0}" = "1" ]; then
  : > "$OUT/08_sweep_152.tsv"; printf 'w\tio\ttrim\toffs\thexout\tsteps\treason\n' >> "$OUT/08_sweep_152.tsv"
  for trim in 0 1; do for io in 0 1; do for offs in 0 1; do for w in $(seq 1 19); do
    printf '0\n' | B19_ROTW=$w B19_IO_CANON=$io B19_TRIM=$trim B19_OFFS_ZERO=$offs "$VAR" "$AM" \
      > sw.o 2> sw.e || true
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$w" "$io" "$trim" "$offs" \
      "$(xxd -p sw.o | tr -d '\n')" "$(sed -n 's/.*steps=\([0-9]*\).*/\1/p' sw.e)" "$(tr -d '\n' < sw.e)" \
      >> "$OUT/08_sweep_152.tsv"
  done; done; done; done
  rm -f sw.o sw.e
fi

# --- phase 09: whitespace census + container and loadability controls ---
python3 "$E5_DIR/specimen_census.py" > "$OUT/09_specimen_census.txt" 2>&1

# --- phase 10: the two-convention matrix - same file, strict vs raw loader ---
RT="${MALBOLGE_LISP_RUNTIME:-/home/danny/Development/ISyCo/CoEvoLang/experiments/malbolge_lisp_petri_dish/runtime}"
{ printf '# bounded probe: B19_MAXSTEPS=2000000, so a "maxsteps" row is a budget cut, not a halt.\n'
  printf '# artifact.mu under the strict loader needs ~8.6M steps, so it shows maxsteps here; see raw/05.\n'
  printf 'spec\ttrim\tresult\n'
  declare -A PINNED=(
    [artifact.mu]="$AM|3b9bdf37eb708ec751d10f0dea32edde4375e526ce56fd2dd440f5a22819ba10"
    [init_module.mb]="$RT/init_module.mb|4b3080fd250a4193030ec647e6c496f90540c1546f717b923284ea31b411e812"
    [core.mb]="$RT/core.mb|70e9155bbe44b58a0a44795cf0c614b214c8f31f82270f4913394e07f1f3e53a"
    [lisp.mb]="$RT/lisp.mb|092df5cdc240de33a355d3cf82bdf09e0859c5827ee57a65bf93dfc37e8f3256"
  )
  for spec in artifact.mu init_module.mb core.mb lisp.mb; do
    f="${PINNED[$spec]%%|*}"; want="${PINNED[$spec]##*|}"
    if ! expect "$want" "$f" "$spec"; then printf '%s\t-\tSKIPPED (drifted)\n' "$spec"; continue; fi
    for t in 0 1; do
      printf '0\n' | B19_MAXSTEPS=2000000 B19_TRIM=$t "$VAR" "$f" >m.o 2>m.e || true
      res=$(grep -oE 'invalid character byte=[0-9]+ v=[0-9]+ instr=[0-9]+|=> (halt|maxsteps|abort|eof) steps=[0-9]+.*a=[0-9]+' m.e | head -1)
      printf '%s\t%s\t%s | stdout=%s\n' "$spec" "$t" "${res:-no-report}" "$(xxd -p m.o | tr -d '\n')"
    done
    rm -f m.o m.e
  done; } > "$OUT/10_convention_matrix.txt" 2>&1

# --- phase 11: init_module under both loaders - the 19,337-step claim's provenance ---
{ for t in 0 1; do
    printf '0\n' | B19_TRIM=$t "$VAR" "$RT/init_module.mb" >h.o 2>h.err || true
    printf 'init_module trim=%s stdout=%s  %s\n' "$t" "$(xxd -p h.o | tr -d '\n')" "$(grep -o '=> halt steps=[0-9]*.*' h.err | head -1)"
  done
  rm -f h.o h.err; } > "$OUT/11_init_module_loaders.txt" 2>&1

# --- phase 12: the canonical reference VM on the native specimen (expected to fail on memory) ---
{ printf 'attempt: unsh_pinned (E4 pin) on init_module.mb, host with ~3 GB available\n'
  printf '0\n' | UNSH_SEED=7 UNSH_ROTWIDTH=10 UNSH_GROWTH_SLACK=3 UNSH_GROWTH_STEP=5 UNSH_DET_GROWTH=1 \
    "$PIN" "$RT/init_module.mb" >c.o 2>c.e; rc=$?
  printf 'exit=%s  stdout=%s\n' "$rc" "$(xxd -p c.o | tr -d '\n')"
  printf 'report: %s\n' "$(grep -o 'UNSH_PIN.*' c.e | head -1 || echo 'none - the VM never reached hlt')"
  printf 'free: %s\n' "$(free -m | sed -n 2p)"
  rm -f c.o c.e; } > "$OUT/12_canonical_on_native.txt" 2>&1

echo "E5 capture complete -> $OUT"
