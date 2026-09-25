# Pushdown trial report

- correctness [chunked_gzip/pii-d01-redact-only]: PASS (1 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d10-redact-only]: PASS (3 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d30-redact-only]: PASS (1 runs, 1 distinct output hashes)

## Run summary
| scheme | format | cpu_quota | bw Mbps | GB xfer | t_ready s | filter_rate | cost_usd |
|---|---|---|---|---|---|---|---|
| R | chunked_gzip | 0.1 | 100 | 0.025 | 360.5 | 0.010 | 0.0050 |
| R | chunked_gzip | 0.25 | 100 | 0.025 | 288.7 | 0.010 | 0.0050 |
| R | chunked_gzip | 0.25 | 100 | 0.025 | 295.0 | 0.011 | 0.0051 |
| R | chunked_gzip | 0.25 | 100 | 0.025 | 283.9 | 0.009 | 0.0050 |
| R | chunked_gzip | 0.5 | 100 | 0.025 | 259.0 | 0.010 | 0.0050 |

## Checkpoint signals (same-tier, same-bandwidth baselines)
- [chunked_gzip/pii-d01-redact-only] no scheme-A baseline for R@100Mbps; skipped
- [chunked_gzip/pii-d10-redact-only] no scheme-A baseline for R@100Mbps; skipped
- [chunked_gzip/pii-d10-redact-only] no scheme-A baseline for R@100Mbps; skipped
- [chunked_gzip/pii-d10-redact-only] no scheme-A baseline for R@100Mbps; skipped
- [chunked_gzip/pii-d30-redact-only] no scheme-A baseline for R@100Mbps; skipped
- S3: winner consistent across groups: {} (no signal)

## Checkpoint-2: C vs E
- C loses to E in every tested config on both time and cost

**Checkpoint verdict: NO SIGNAL** (0 signal(s))
Per handoff: do NOT force a positive story. Report honestly and discuss a pivot (PII-compliance framing / pushdown boundaries).

Overall correctness gate: PASS
