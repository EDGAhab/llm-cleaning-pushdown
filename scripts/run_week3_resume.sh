#!/bin/bash
# run_week3_resume.sh: resume week-3 matrix after the 2026-09-24 service restart.
# A_chunked_100 and A_whole_100 already done; run the rest.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=experiments/week3_ac
SUBSET="--limit-refs 5"
mkdir -p "$OUT"

run() { echo ">>> $*"; "$@"; }

run $PY scripts/10_run_scheme.py --scheme A --format zstd_parquet $SUBSET --bandwidth-mbps 100   --out $OUT/A_parquet_100.json
run $PY scripts/10_run_scheme.py --scheme A --format chunked_gzip $SUBSET --bandwidth-mbps 10000 --out $OUT/A_chunked_10000.json

run $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip $SUBSET --cpu-quota 0.10 --bandwidth-mbps 100 --out $OUT/C_chunked_100_q10.json
run $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip $SUBSET --cpu-quota 0.25 --bandwidth-mbps 100 --out $OUT/C_chunked_100_q25.json
run $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip $SUBSET --cpu-quota 0.50 --bandwidth-mbps 100 --out $OUT/C_chunked_100_q50.json
run $PY scripts/10_run_scheme.py --scheme C --format zstd_parquet $SUBSET --cpu-quota 0.25 --bandwidth-mbps 100   --out $OUT/C_parquet_100_q25.json
run $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip $SUBSET --cpu-quota 0.25 --bandwidth-mbps 10000 --out $OUT/C_chunked_10000_q25.json

run $PY scripts/31_interference.py --limit-refs 5 --out $OUT/interference.json

run $PY scripts/20_report.py --runs "$OUT/A_*.json" "$OUT/C_*.json" \
    --out $OUT/report.md --cost-out $OUT/cost_onepager.md
echo "DONE. See $OUT/report.md"
