# Pushdown trial report

- correctness [chunked_gzip/pii-d01]: PASS (3 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d10]: PASS (5 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d30]: PASS (3 runs, 1 distinct output hashes)

## Run summary
| scheme | format | cpu_quota | bw Mbps | GB xfer | t_ready s | filter_rate | cost_usd |
|---|---|---|---|---|---|---|---|
| A | chunked_gzip | None | 100 | 0.025 | 228.9 | 0.011 | 0.0049 |
| A | chunked_gzip | None | 100 | 0.025 | 246.1 | 0.010 | 0.0049 |
| A | chunked_gzip | None | 100 | 0.025 | 232.2 | 0.009 | 0.0049 |
| C | chunked_gzip | 0.1 | 100 | 0.025 | 1895.0 | 0.010 | 0.0052 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 794.3 | 0.011 | 0.0050 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 841.3 | 0.010 | 0.0051 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 845.8 | 0.009 | 0.0052 |
| C | chunked_gzip | 0.5 | 100 | 0.025 | 469.5 | 0.010 | 0.0051 |
| E | chunked_gzip | None | 10000 | 0.025 | 227.8 | 0.011 | 0.0027 |
| E | chunked_gzip | None | 10000 | 0.025 | 230.0 | 0.010 | 0.0027 |
| E | chunked_gzip | None | 10000 | 0.025 | 246.9 | 0.009 | 0.0028 |

## Checkpoint signals (same-tier, same-bandwidth baselines)
- [chunked_gzip/pii-d01@100Mbps] C(quota=0.25) vs A: time x3.47, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d01@10000Mbps] E(quota=None) vs A: time x1.00, bytes x1.00 
- [chunked_gzip/pii-d10@100Mbps] C(quota=0.1) vs A: time x7.70, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10@100Mbps] C(quota=0.25) vs A: time x3.42, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10@100Mbps] C(quota=0.5) vs A: time x1.91, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10@10000Mbps] E(quota=None) vs A: time x0.93, bytes x1.00 
- [chunked_gzip/pii-d30@100Mbps] C(quota=0.25) vs A: time x3.64, bytes x0.99 S1(low-quota-hurts)
- [chunked_gzip/pii-d30@10000Mbps] E(quota=None) vs A: time x1.06, bytes x1.00 
- S3: winner consistent across groups: {('chunked_gzip', 'pii-d01'): 'A', ('chunked_gzip', 'pii-d10'): 'A', ('chunked_gzip', 'pii-d30'): 'A'} (no signal)

## Checkpoint-2: C vs E
- C loses to E in every tested config on both time and cost

**Checkpoint verdict: INTERESTING** (5 signal(s))

Overall correctness gate: PASS
