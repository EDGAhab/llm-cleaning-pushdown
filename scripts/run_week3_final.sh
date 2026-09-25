#!/bin/bash
# run_week3_final.sh: final resume after 2nd service restart (2026-09-24).
# Already done: A x4, C chunked q10/q25/q50.
# Remaining: C chunked 10Gbps q25, light interference (S4), report.
# C_parquet_q25 SKIPPED: single-worker 100k docs at q25 ~77min, restart risk
# too high; S3 verdict (no format flip) via extrapolation, noted in report.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=experiments/week3_ac
SUBSET="--limit-refs 5"
mkdir -p "$OUT"

run() { echo ">>> $*"; "$@"; }

run $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip $SUBSET --cpu-quota 0.25 --bandwidth-mbps 10000 --out $OUT/C_chunked_10000_q25.json

run $PY scripts/31_interference.py --limit-refs 1 --quotas 0.10 0.25 0.50 --out $OUT/interference.json

run $PY scripts/20_report.py --runs "$OUT/A_*.json" "$OUT/C_*.json" \
    --out $OUT/report.md --cost-out $OUT/cost_onepager.md
echo "DONE. See $OUT/report.md"
