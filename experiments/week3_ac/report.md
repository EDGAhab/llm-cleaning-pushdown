# Week-3 A/C trial report

- correctness [chunked_gzip]: PASS (5 runs, 1 distinct output hashes)
- correctness [whole_gzip]: PASS (1 runs, 1 distinct output hashes)
- correctness [zstd_parquet]: PASS (1 runs, 1 distinct output hashes)

## Run summary
| scheme | format | cpu_quota | bw Mbps | GB xfer | t_ready s | filter_rate | cost_usd |
|---|---|---|---|---|---|---|---|
| A | chunked_gzip | None | 100 | 0.123 | 859.0 | 0.011 | 0.0111 |
| A | chunked_gzip | None | 10000 | 0.123 | 1109.1 | 0.011 | 0.0112 |
| C | chunked_gzip | 0.1 | 100 | 0.123 | 4695.2 | 0.011 | 0.0111 |
| C | chunked_gzip | 0.25 | 100 | 0.123 | 2138.0 | 0.011 | 0.0111 |
| C | chunked_gzip | 0.5 | 100 | 0.123 | 1501.9 | 0.011 | 0.0111 |
| A | whole_gzip | None | 100 | 0.123 | 1132.2 | 0.011 | 0.0116 |
| A | zstd_parquet | None | 100 | 0.134 | 1597.1 | 0.011 | 0.0122 |

## Checkpoint-1 signals
- [chunked_gzip] C(quota=0.1) vs A: time x4.23, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip] C(quota=0.25) vs A: time x1.93, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip] C(quota=0.5) vs A: time x1.35, bytes x1.00 S1(low-quota-hurts)
- S3: winner consistent across formats: {'chunked_gzip': 'A'} (no signal)

**Checkpoint-1 verdict: INTERESTING** (3 signal(s))

Overall correctness gate: PASS
