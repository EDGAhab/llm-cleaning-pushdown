# Pushdown trial report

- correctness [chunked_gzip/pii-d01]: PASS (3 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d01-r2]: PASS (3 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d01-r3]: PASS (3 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d10]: PASS (5 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d10-r2]: PASS (5 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d10-r3]: PASS (5 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d30]: PASS (3 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d30-r2]: PASS (3 runs, 1 distinct output hashes)
- correctness [chunked_gzip/pii-d30-r3]: PASS (3 runs, 1 distinct output hashes)

## Run summary
| scheme | format | cpu_quota | bw Mbps | GB xfer | t_ready s | filter_rate | cost_usd |
|---|---|---|---|---|---|---|---|
| A | chunked_gzip | None | 100 | 0.025 | 228.9 | 0.011 | 0.0049 |
| A | chunked_gzip | None | 100 | 0.025 | 246.1 | 0.010 | 0.0049 |
| A | chunked_gzip | None | 100 | 0.025 | 232.2 | 0.009 | 0.0049 |
| A | chunked_gzip | None | 100 | 0.025 | 232.8 | 0.011 | 0.0049 |
| A | chunked_gzip | None | 100 | 0.025 | 239.9 | 0.010 | 0.0049 |
| A | chunked_gzip | None | 100 | 0.025 | 226.2 | 0.009 | 0.0049 |
| A | chunked_gzip | None | 100 | 0.025 | 227.8 | 0.011 | 0.0049 |
| A | chunked_gzip | None | 100 | 0.025 | 228.7 | 0.010 | 0.0049 |
| A | chunked_gzip | None | 100 | 0.025 | 232.5 | 0.009 | 0.0049 |
| C | chunked_gzip | 0.1 | 100 | 0.025 | 1895.0 | 0.010 | 0.0052 |
| C | chunked_gzip | 0.1 | 100 | 0.025 | 1843.2 | 0.010 | 0.0051 |
| C | chunked_gzip | 0.1 | 100 | 0.025 | 1856.3 | 0.010 | 0.0051 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 794.3 | 0.011 | 0.0050 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 841.3 | 0.010 | 0.0051 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 845.8 | 0.009 | 0.0052 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 821.0 | 0.011 | 0.0051 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 1067.7 | 0.010 | 0.0052 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 817.9 | 0.009 | 0.0051 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 806.7 | 0.011 | 0.0051 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 829.5 | 0.010 | 0.0051 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 794.6 | 0.009 | 0.0051 |
| C | chunked_gzip | 0.5 | 100 | 0.025 | 469.5 | 0.010 | 0.0051 |
| C | chunked_gzip | 0.5 | 100 | 0.025 | 462.8 | 0.010 | 0.0051 |
| C | chunked_gzip | 0.5 | 100 | 0.025 | 465.3 | 0.010 | 0.0051 |
| E | chunked_gzip | None | 10000 | 0.025 | 227.8 | 0.011 | 0.0027 |
| E | chunked_gzip | None | 10000 | 0.025 | 230.0 | 0.010 | 0.0027 |
| E | chunked_gzip | None | 10000 | 0.025 | 246.9 | 0.009 | 0.0028 |
| E | chunked_gzip | None | 10000 | 0.025 | 232.4 | 0.011 | 0.0027 |
| E | chunked_gzip | None | 10000 | 0.025 | 233.2 | 0.010 | 0.0027 |
| E | chunked_gzip | None | 10000 | 0.025 | 233.1 | 0.009 | 0.0027 |
| E | chunked_gzip | None | 10000 | 0.025 | 228.1 | 0.011 | 0.0027 |
| E | chunked_gzip | None | 10000 | 0.025 | 230.5 | 0.010 | 0.0027 |
| E | chunked_gzip | None | 10000 | 0.025 | 228.2 | 0.009 | 0.0027 |

## Checkpoint signals (same-tier, same-bandwidth baselines)
- [chunked_gzip/pii-d01@100Mbps] C(quota=0.25) vs A: time x3.47, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d01@10000Mbps] E(quota=None) vs A: time x1.00, bytes x1.00 
- [chunked_gzip/pii-d01-r2@100Mbps] C(quota=0.25) vs A: time x3.53, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d01-r2@10000Mbps] E(quota=None) vs A: time x1.00, bytes x1.00 
- [chunked_gzip/pii-d01-r3@100Mbps] C(quota=0.25) vs A: time x3.54, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d01-r3@10000Mbps] E(quota=None) vs A: time x1.00, bytes x1.00 
- [chunked_gzip/pii-d10@100Mbps] C(quota=0.1) vs A: time x7.70, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10@100Mbps] C(quota=0.25) vs A: time x3.42, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10@100Mbps] C(quota=0.5) vs A: time x1.91, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10@10000Mbps] E(quota=None) vs A: time x0.93, bytes x1.00 
- [chunked_gzip/pii-d10-r2@100Mbps] C(quota=0.1) vs A: time x7.68, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10-r2@100Mbps] C(quota=0.25) vs A: time x4.45, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10-r2@100Mbps] C(quota=0.5) vs A: time x1.93, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10-r2@10000Mbps] E(quota=None) vs A: time x0.97, bytes x1.00 
- [chunked_gzip/pii-d10-r3@100Mbps] C(quota=0.1) vs A: time x8.12, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10-r3@100Mbps] C(quota=0.25) vs A: time x3.63, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10-r3@100Mbps] C(quota=0.5) vs A: time x2.03, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip/pii-d10-r3@10000Mbps] E(quota=None) vs A: time x1.01, bytes x1.00 
- [chunked_gzip/pii-d30@100Mbps] C(quota=0.25) vs A: time x3.64, bytes x0.99 S1(low-quota-hurts)
- [chunked_gzip/pii-d30@10000Mbps] E(quota=None) vs A: time x1.06, bytes x1.00 
- [chunked_gzip/pii-d30-r2@100Mbps] C(quota=0.25) vs A: time x3.62, bytes x0.99 S1(low-quota-hurts)
- [chunked_gzip/pii-d30-r2@10000Mbps] E(quota=None) vs A: time x1.03, bytes x1.00 
- [chunked_gzip/pii-d30-r3@100Mbps] C(quota=0.25) vs A: time x3.42, bytes x0.99 S1(low-quota-hurts)
- [chunked_gzip/pii-d30-r3@10000Mbps] E(quota=None) vs A: time x0.98, bytes x1.00 
- S3: winner consistent across groups: {('chunked_gzip', 'pii-d01'): 'A', ('chunked_gzip', 'pii-d01-r2'): 'A', ('chunked_gzip', 'pii-d01-r3'): 'A', ('chunked_gzip', 'pii-d10'): 'A', ('chunked_gzip', 'pii-d10-r2'): 'A', ('chunked_gzip', 'pii-d10-r3'): 'A', ('chunked_gzip', 'pii-d30'): 'A', ('chunked_gzip', 'pii-d30-r2'): 'A', ('chunked_gzip', 'pii-d30-r3'): 'A'} (no signal)

## Checkpoint-2: C vs E
- C loses to E in every tested config on both time and cost

**Checkpoint verdict: INTERESTING** (15 signal(s))

Overall correctness gate: PASS
