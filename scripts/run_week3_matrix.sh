#!/bin/bash
# run_week3_matrix.sh: week-3 A/C trial on a 5-chunk subset (100k docs, ~300MB raw).
# Full 389k-doc dataset is built (data/manifest.json); subset keeps the overnight
# run tractable on 2 vCPUs. Ratios (bytes/time) are scale-invariant for the
# checkpoint-1 signals; absolute times are not extrapolated.
# Run from ~/workspace/llm-cleaning-pushdown after data/ is ready.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=experiments/week3_ac
SUBSET="--limit-refs 5"
mkdir -p "$OUT"

run() { echo ">>> $*"; "$@"; }

# --- scheme A baselines ---
run $PY scripts/10_run_scheme.py --scheme A --format chunked_gzip $SUBSET --bandwidth-mbps 100   --out $OUT/A_chunked_100.json
run $PY scripts/10_run_scheme.py --scheme A --format whole_gzip  $SUBSET --bandwidth-mbps 100   --out $OUT/A_whole_100.json
run $PY scripts/10_run_scheme.py --scheme A --format zstd_parquet $SUBSET --bandwidth-mbps 100   --out $OUT/A_parquet_100.json
run $PY scripts/10_run_scheme.py --scheme A --format chunked_gzip $SUBSET --bandwidth-mbps 10000 --out $OUT/A_chunked_10000.json

# --- scheme C pushdown: quota sweep (H1/S1) ---
run $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip $SUBSET --cpu-quota 0.10 --bandwidth-mbps 100 --out $OUT/C_chunked_100_q10.json
run $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip $SUBSET --cpu-quota 0.25 --bandwidth-mbps 100 --out $OUT/C_chunked_100_q25.json
run $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip $SUBSET --cpu-quota 0.50 --bandwidth-mbps 100 --out $OUT/C_chunked_100_q50.json
# NOTE: no C/whole_gzip run: whole_gzip is a single 480MB object -> 1 worker,
# which at q10 would take ~3h on this box. A/whole is kept as the format
# baseline; the S3 format comparison uses chunked vs parquet.
run $PY scripts/10_run_scheme.py --scheme C --format zstd_parquet $SUBSET --cpu-quota 0.25 --bandwidth-mbps 100   --out $OUT/C_parquet_100_q25.json
run $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip $SUBSET --cpu-quota 0.25 --bandwidth-mbps 10000 --out $OUT/C_chunked_10000_q25.json

# --- H4 interference (subset) ---
run $PY scripts/31_interference.py --limit-refs 5 --out $OUT/interference.json

# --- report + checkpoint-1 verdict ---
run $PY scripts/20_report.py --runs "$OUT/A_*.json" "$OUT/C_*.json" \
    --out $OUT/report.md --cost-out $OUT/cost_onepager.md
echo "DONE. See $OUT/report.md"
