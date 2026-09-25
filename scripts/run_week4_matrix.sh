#!/bin/bash
# run_week4_matrix.sh: week-4 (checkpoint 2) trial matrix.
# Scheme E (same-region CPU cluster) vs C (pushdown) vs A (full pull),
# plus the warc_html high-shrinkage probe.
# All runs are --limit-refs 1 (20k docs, single chunk) so each run fits in
# ~20 min on this 2vCPU box. Each run writes its own JSON; reruns skip
# existing outputs (resume-safe across service restarts).
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=experiments/week4_be
SUBSET="--limit-refs 1"
mkdir -p "$OUT"

run() { # run <out> <args...>
  local out="$1"; shift
  if [ -f "$out" ]; then echo "SKIP (exists): $out"; return 0; fi
  echo ">>> ${*} -> $out"
  "$@" --out "$out"
}

# Part 1: E vs C vs A on the standard pipeline (cross-cloud 100Mbps / same-region 10Gbps)
run $OUT/A_chunked_100.json      $PY scripts/10_run_scheme.py --scheme A --format chunked_gzip --bandwidth-mbps 100 $SUBSET
run $OUT/E_chunked_10000.json    $PY scripts/10_run_scheme.py --scheme E --format chunked_gzip --bandwidth-mbps 10000 $SUBSET
run $OUT/C_chunked_100_q10.json  $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip --cpu-quota 0.10 --bandwidth-mbps 100 $SUBSET
run $OUT/C_chunked_100_q25.json  $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip --cpu-quota 0.25 --bandwidth-mbps 100 $SUBSET
run $OUT/C_chunked_100_q50.json  $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip --cpu-quota 0.50 --bandwidth-mbps 100 $SUBSET
run $OUT/C_chunked_10000_q100.json $PY scripts/10_run_scheme.py --scheme C --format chunked_gzip --cpu-quota 1.00 --bandwidth-mbps 10000 $SUBSET

# Part 2: high-shrinkage probe (WARC->text extraction first stage)
run $OUT/A_warc_100.json   $PY scripts/10_run_scheme.py --scheme A --format warc_html --bandwidth-mbps 100 --spec pipeline_specs/fineweb_warc.json $SUBSET
run $OUT/C_warc_100_q25.json $PY scripts/10_run_scheme.py --scheme C --format warc_html --cpu-quota 0.25 --bandwidth-mbps 100 --spec pipeline_specs/fineweb_warc.json $SUBSET

echo "MATRIX DONE. Generating report..."
$PY scripts/20_report.py --runs "$OUT"/*.json --out $OUT/report.md --cost-out $OUT/cost_onepager.md
echo "DONE. See $OUT/report.md"
