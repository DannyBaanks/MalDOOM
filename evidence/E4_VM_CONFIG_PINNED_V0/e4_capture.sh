#!/bin/bash
# E4 — pinned Unshackled VM capture, parameterised to the repo root.
#
# Paths resolve from the repo; OUT defaults to a scratch dir, so re-running
# this script can never overwrite the sealed logs under ./raw. E4_QUICK=1 runs
# only the canonical-pin phases (05, 09, 09_check).
set -u
E4_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="${REPO:-$(cd "$E4_DIR/../.." && pwd)}"
AM="$REPO/evidence/M0_KILLER_UNSHACKLED_V0/artifact.mu"
SRC="$REPO/vendor/Unshackled.c"
WORK="${E4_WORK:-$(mktemp -d /home/danny/tmp_engine_test/repro_XXXXXX)}"
OUT="${E4_OUT:-$WORK/raw_repeat}"
mkdir -p "$OUT"
cd "$WORK" || exit 1
BIN="$WORK/unsh_pinned"
VENDOR="$WORK/unsh_vendor"
gcc -O2 -w -o "$BIN" "$E4_DIR/unsh_pinned.c" || exit 1
gcc -O2 -w -o "$VENDOR" "$SRC" || exit 1

PIN='10 3 5 1'   # canonical pin: rotwidth0 growth_slack growth_step det_growth
TSV_COLS='input\trw\tslack\tgstep\tdet\tseed\tprob\tsteps\twall_s\tsps\tfinal_rw\tmax_ww\tstdout_hex\n'

one() { # rw sl gs det sd prob inp outfile
  local o e line
  o=$(mktemp ./x.o.XXXXXX); e=$(mktemp ./x.e.XXXXXX)
  printf '%s\n' "$7" | UNSH_SEED=$5 UNSH_ROTWIDTH=$1 UNSH_DET_GROWTH=$4 \
    UNSH_GROWTH_SLACK=$2 UNSH_GROWTH_STEP=$3 UNSH_GROWTH_PROB=$6 "$BIN" "$AM" >"$o" 2>"$e"
  line=$(grep '^UNSH_PIN' "$e")
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$7" "$1" "$2" "$3" "$4" "$5" "$6" \
    "$(sed -n 's/.*STEPS \([0-9]*\).*/\1/p' <<<"$line")" \
    "$(sed -n 's/.*WALL \([0-9.]*\)s.*/\1/p' <<<"$line")" \
    "$(sed -n 's/.*SPS \([0-9]*\).*/\1/p' <<<"$line")" \
    "$(sed -n 's/.*final{rotwidth=\([0-9]*\).*/\1/p' <<<"$line")" \
    "$(sed -n 's/.*max_wordwidth=\([0-9]*\)}/\1/p' <<<"$line")" \
    "$(xxd -p "$o" | tr -d '\n')" >> "$8"
  rm -f "$o" "$e"
}

phase05() { # canonical pin replication + seed invariance
  printf "$TSV_COLS" > "$OUT/05_canonical_pin.tsv"
  for sd in 1 7 4242; do for inp in 0 2; do one 10 3 5 1 "$sd" 0 "$inp" "$OUT/05_canonical_pin.tsv"; done; done
}
phase06() { # SINGLE-SHOT -O comparison — kept as a negative result: it is noise. Superseded by 08.
  : > "$OUT/06_opt_levels_single_shot.txt"
  export UNSH_SEED=7 UNSH_ROTWIDTH=10 UNSH_DET_GROWTH=1 UNSH_GROWTH_SLACK=3 UNSH_GROWTH_STEP=5
  for O in -O0 -O1 -O2 -O3; do
    gcc $O -w -o ./opt_probe "$E4_DIR/unsh_pinned.c"
    printf '0\n' | ./opt_probe "$AM" 2>&1 >/dev/null | sed "s/^/$O /" >> "$OUT/06_opt_levels_single_shot.txt"
  done
  rm -f ./opt_probe
}
phase08() { # replicated -O comparison, 5 reps per level
  printf 'opt\trep\tsteps\twall_s\tsps\n' > "$OUT/08_opt_replicated.tsv"
  export UNSH_SEED=7 UNSH_ROTWIDTH=10 UNSH_DET_GROWTH=1 UNSH_GROWTH_SLACK=3 UNSH_GROWTH_STEP=5
  for rep in 1 2 3 4 5; do for lvl in 0 1 2 3; do
    [ -x "./probe_O$lvl" ] || gcc -O$lvl -w -o "./probe_O$lvl" "$E4_DIR/unsh_pinned.c"
    r=$(printf '0\n' | "./probe_O$lvl" "$AM" 2>&1 >/dev/null | grep -o 'STEPS [0-9]* WALL [0-9.]*s SPS [0-9]*')
    printf 'O%s\t%s\t%s\n' "$lvl" "$rep" "$(sed -n 's/^STEPS \([0-9]*\) WALL \([0-9.]*\)s SPS \(.*\)$/\1\t\2\t\3/p' <<<"$r")" >> "$OUT/08_opt_replicated.tsv"
  done; done
  rm -f ./probe_O0 ./probe_O1 ./probe_O2 ./probe_O3
  unset UNSH_SEED UNSH_ROTWIDTH UNSH_DET_GROWTH UNSH_GROWTH_SLACK UNSH_GROWTH_STEP
}
phase09() { # all five sealed killer inputs at the canonical pin, vs run.json's observed strings
  printf "$TSV_COLS" > "$OUT/09_killer_all_inputs_pin.tsv"
  for i in 0 1 2 3 4; do one 10 3 5 1 7 0 "$i" "$OUT/09_killer_all_inputs_pin.tsv"; done
  # M0_KILLER run.json records input i -> digit (2i+1) then \n  => hex %02x0a of 49+2i
  printf 'input\texpected_hex_from_run_json\tobserved_hex\tsigma\n' > "$OUT/09_expected_vs_observed.txt"
  awk -F'\t' 'NR>1{printf "%s\t%s\t%s\t%s\n", $1, sprintf("%02x0a", 49+2*$1), $13, ($13==sprintf("%02x0a",49+2*$1))?"MATCH":"MISMATCH"}' \
    "$OUT/09_killer_all_inputs_pin.tsv" >> "$OUT/09_expected_vs_observed.txt"
}
phase_all() {
  printf "$TSV_COLS" > "$OUT/01_rotwidth_sweep.tsv"
  for inp in 0 2; do for rw in 10 11 12 13 14 15; do one "$rw" 0 8 1 7 0 "$inp" "$OUT/01_rotwidth_sweep.tsv"; done; done

  printf "$TSV_COLS" > "$OUT/02_slack_gstep_det1.tsv"
  for inp in 0 2; do for sl in 0 1 2 3 4 5; do for gs in 4 8 12; do one 13 "$sl" "$gs" 1 7 0 "$inp" "$OUT/02_slack_gstep_det1.tsv"; done; done; done

  printf "$TSV_COLS" > "$OUT/03_det1_grid_hunt_input0.tsv"
  for rw in 10 11 12; do for sl in 0 3 5; do for gs in 4 5 6 7 8 9 10 11 12; do one "$rw" "$sl" "$gs" 1 7 0 0 "$OUT/03_det1_grid_hunt_input0.tsv"; done; done; done

  printf "$TSV_COLS" > "$OUT/04_det0_controls.tsv"
  for sd in 7 99 123; do for p in 214748365 1073741824 858993459; do
    one 13 0 8 0 "$sd" "$p" 0 "$OUT/04_det0_controls.tsv"
    one 13 3 8 0 "$sd" "$p" 0 "$OUT/04_det0_controls.tsv"
  done; done

  phase06; phase08; phase05; phase09

  : > "$OUT/07_vendor_unmodified_wall.txt"
  for i in 1 2 3 4 5 6; do
    printf '0\n' | { /usr/bin/time -f "%es" "$VENDOR" "$AM" >/dev/null; } 2>> "$OUT/07_vendor_unmodified_wall.txt"
  done
}
[ "${E4_QUICK:-0}" = 1 ] && { phase05; phase09; } || phase_all

{ gcc --version | head -1; uname -a; nproc
  sha256sum "$AM" "$SRC" "$E4_DIR/unsh_pinned.c" "$BIN" "$VENDOR"
  printf 'sealed observed_0.bin: '; xxd -p "$REPO/evidence/M0_KILLER_UNSHACKLED_V0/observed_0.bin" | tr -d '\n'; echo
} > "$OUT/00_environment.txt" 2>&1
echo "E4 capture done -> $OUT"
