#!/bin/bash
# run_pii_matrix.sh: PII-compliance-scenario matrix (phase 4).
#
# Research question: when an enterprise must redact PII before data leaves
# storage (compliance), what is the time/cost premium of pushdown (C) vs
# full pull (A), and how does PII density shift the pushdown boundary?
#
# Data: data_pii/<tier>/ (scripts/40_pii_data.py) -- 20k docs/tier, natural
# PII-like matches pre-cleared, synthetic PII injected at tier density.
# All tiers share identical base docs; tiers differ ONLY in PII density.
#
# Design (mirrors week-4 Part 1, per tier):
#   Per tier (d01/d10/d30): A @100Mbps, C q25 @100Mbps, E @10000Mbps
#       -> the "compliance premium": how much slower/pricier is keeping
#          PII inside storage vs pulling raw docs out?
#   Quota sweep on d10: C q10 / q25 / q50 @100Mbps
#       -> the boundary: at what storage CPU quota does pushdown become
#          viable for PII-heavy data?
#
# Compliance metric (derived, no new instrumentation): injected PII
# instances crossing the storage boundary UNREDACTED. Scheme A/E transfer
# raw docs then redact at compute => exposure = injected_total (exact,
# from data_pii/manifest.json). Scheme C redacts at storage => exposure 0.
#
# 11 runs x ~20 min on this 2vCPU box. Resume-safe: reruns skip existing.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=experiments/pii_matrix
mkdir -p "$OUT"

run() { # run <out> <tier> <args...>
  local out="$1"; local tier="$2"; shift 2
  if [ -f "$out" ]; then echo "SKIP (exists): $out"; return 0; fi
  echo ">>> [tier $tier] ${*} -> $out"
  "$@" --data-root "data_pii/$tier" --out "$out"
}

STD="--format chunked_gzip --limit-refs 1"

for TIER in d01 d10 d30; do
  run "$OUT/${TIER}_A_100.json"     "$TIER" $PY scripts/10_run_scheme.py --scheme A $STD --bandwidth-mbps 100   --label "pii-$TIER"
  run "$OUT/${TIER}_C_q25_100.json" "$TIER" $PY scripts/10_run_scheme.py --scheme C $STD --cpu-quota 0.25 --bandwidth-mbps 100 --label "pii-$TIER"
  run "$OUT/${TIER}_E_10000.json"   "$TIER" $PY scripts/10_run_scheme.py --scheme E $STD --bandwidth-mbps 10000 --label "pii-$TIER"
done

# quota sweep on the middle tier (d10)
run "$OUT/d10_C_q10_100.json" "d10" $PY scripts/10_run_scheme.py --scheme C $STD --cpu-quota 0.10 --bandwidth-mbps 100 --label "pii-d10"
run "$OUT/d10_C_q50_100.json" "d10" $PY scripts/10_run_scheme.py --scheme C $STD --cpu-quota 0.50 --bandwidth-mbps 100 --label "pii-d10"

echo "MATRIX DONE. Generating report..."
$PY scripts/20_report.py --runs "$OUT"/*.json --out $OUT/report.md --cost-out $OUT/cost_onepager.md
echo "DONE. See $OUT/report.md"
