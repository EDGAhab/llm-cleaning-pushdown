#!/bin/bash
# watch_extras.sh: wait until all Experiment A/B outputs exist, then exit 0.
# Polls every 10 min; gives up after 12h (exit 1). Read-only, no CPU load.
cd "$(dirname "$0")/.."
LOG=experiments/watch_progress.log
expected=""
for f in d01_R_q25_100 d10_R_q25_100 d30_R_q25_100 d10_R_q10_100 d10_R_q50_100; do
  expected="$expected experiments/pii_redact_only/$f.json"
done
for rep in r2 r3; do
  for t in d01 d10 d30; do
    expected="$expected experiments/pii_matrix_r2/${t}_A_100_${rep}.json"
    expected="$expected experiments/pii_matrix_r2/${t}_C_q25_100_${rep}.json"
    expected="$expected experiments/pii_matrix_r2/${t}_E_10000_${rep}.json"
  done
  expected="$expected experiments/pii_matrix_r2/d10_C_q10_100_${rep}.json"
  expected="$expected experiments/pii_matrix_r2/d10_C_q50_100_${rep}.json"
done
n_expected=$(echo "$expected" | wc -w)
deadline=$(( $(date +%s) + 43200 ))
while [ $(date +%s) -lt $deadline ]; do
  n=0; missing=""
  for f in $expected; do
    if [ -f "$f" ]; then n=$((n+1)); else missing="$missing $(basename $f)"; fi
  done
  runner=$(pgrep -f "run_pii_extras.sh" | head -1)
  echo "$(date -u +%FT%TZ) $n/$n_expected files, runner_pid=${runner:-none}, mem_avail=$(free -m | awk '/^Mem:/{print $7}')MB" >> "$LOG"
  if [ "$n" -eq "$n_expected" ]; then echo "ALL DONE: $n/$n_expected" >> "$LOG"; exit 0; fi
  sleep 600
done
echo "TIMEOUT with missing:$missing" >> "$LOG"
exit 1
