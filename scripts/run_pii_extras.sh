#!/bin/bash
# run_pii_extras.sh: Experiment A (redact-only scheme R) + Experiment B
# (repeat each of the 11 pii_matrix cells x2 more -> n=3).
#
# Sequential, nice'd, memory-gated (skip-run only if available RAM < 1.5GB),
# resume-safe: reruns skip existing outputs.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python

wait_for_mem() {
  while true; do
    avail_mb=$(free -m | awk '/^Mem:/ {print $7}')
    if [ "$avail_mb" -ge 1536 ]; then return 0; fi
    echo "[mem] only ${avail_mb}MB available, waiting 300s..."
    sleep 300
  done
}

run() { # run <out> <tier> <args...>
  local out="$1"; local tier="$2"; shift 2
  if [ -f "$out" ]; then echo "SKIP (exists): $out"; return 0; fi
  wait_for_mem
  echo ">>> [tier $tier] ${*} -> $out"
  nice -n 10 "$@" --data-root "data_pii/$tier" --out "$out"
}

STD="--format chunked_gzip --limit-refs 1"

# ---- Experiment A: redact-only pushdown (scheme R), compliance lower bound ----
OUTR=experiments/pii_redact_only
mkdir -p "$OUTR"
for TIER in d01 d10 d30; do
  run "$OUTR/${TIER}_R_q25_100.json" "$TIER" $PY scripts/10_run_scheme.py --scheme R $STD --cpu-quota 0.25 --bandwidth-mbps 100 --label "pii-$TIER-redact-only"
done
# optional quota scans on d10 (lower priority)
run "$OUTR/d10_R_q10_100.json" "d10" $PY scripts/10_run_scheme.py --scheme R $STD --cpu-quota 0.10 --bandwidth-mbps 100 --label "pii-d10-redact-only"
run "$OUTR/d10_R_q50_100.json" "d10" $PY scripts/10_run_scheme.py --scheme R $STD --cpu-quota 0.50 --bandwidth-mbps 100 --label "pii-d10-redact-only"

# ---- Experiment B: repeats r2/r3 for the 11 original pii_matrix cells ----
OUT2=experiments/pii_matrix_r2
mkdir -p "$OUT2"
for REP in r2 r3; do
  for TIER in d01 d10 d30; do
    run "$OUT2/${TIER}_A_100_${REP}.json"     "$TIER" $PY scripts/10_run_scheme.py --scheme A $STD --bandwidth-mbps 100   --label "pii-$TIER-$REP"
    run "$OUT2/${TIER}_C_q25_100_${REP}.json" "$TIER" $PY scripts/10_run_scheme.py --scheme C $STD --cpu-quota 0.25 --bandwidth-mbps 100 --label "pii-$TIER-$REP"
    run "$OUT2/${TIER}_E_10000_${REP}.json"   "$TIER" $PY scripts/10_run_scheme.py --scheme E $STD --bandwidth-mbps 10000 --label "pii-$TIER-$REP"
  done
  run "$OUT2/d10_C_q10_100_${REP}.json" "d10" $PY scripts/10_run_scheme.py --scheme C $STD --cpu-quota 0.10 --bandwidth-mbps 100 --label "pii-d10-$REP"
  run "$OUT2/d10_C_q50_100_${REP}.json" "d10" $PY scripts/10_run_scheme.py --scheme C $STD --cpu-quota 0.50 --bandwidth-mbps 100 --label "pii-d10-$REP"
done

echo "EXTRAS DONE."
