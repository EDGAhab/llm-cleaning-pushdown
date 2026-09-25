# Pushdown trial report

- correctness [chunked_gzip]: PASS (6 runs, 1 distinct output hashes)
- correctness [warc_html]: PASS (2 runs, 1 distinct output hashes)

## Run summary
| scheme | format | cpu_quota | bw Mbps | GB xfer | t_ready s | filter_rate | cost_usd |
|---|---|---|---|---|---|---|---|
| A | chunked_gzip | None | 100 | 0.025 | 301.9 | 0.011 | 0.0050 |
| C | chunked_gzip | 0.1 | 100 | 0.025 | 1878.9 | 0.011 | 0.0051 |
| C | chunked_gzip | 0.25 | 100 | 0.025 | 820.3 | 0.011 | 0.0051 |
| C | chunked_gzip | 0.5 | 100 | 0.025 | 477.3 | 0.011 | 0.0052 |
| C | chunked_gzip | 1.0 | 10000 | 0.025 | 246.8 | 0.011 | 0.0051 |
| E | chunked_gzip | None | 10000 | 0.025 | 251.7 | 0.011 | 0.0027 |
| A | warc_html | None | 100 | 0.027 | 288.4 | 0.001 | 0.0058 |
| C | warc_html | 0.25 | 100 | 0.025 | 1043.0 | 0.001 | 0.0059 |

## Checkpoint signals (same-bandwidth baselines)
- [chunked_gzip@100Mbps] C(quota=0.1) vs A: time x6.22, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip@100Mbps] C(quota=0.25) vs A: time x2.72, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip@100Mbps] C(quota=0.5) vs A: time x1.58, bytes x1.00 S1(low-quota-hurts)
- [chunked_gzip@10000Mbps] C(quota=1.0) vs A: time x0.82, bytes x1.00 
- [chunked_gzip@10000Mbps] E(quota=None) vs A: time x0.83, bytes x1.00 
- [warc_html@100Mbps] C(quota=0.25) vs A: time x3.62, bytes x0.93 S1(low-quota-hurts)
- S3(format-changes-winner): {'chunked_gzip': 'C', 'warc_html': 'A'}

## Checkpoint-2: C vs E
- [chunked_gzip@10000Mbps] best C (q=1.0, 246.8s, $0.0051) vs E (251.7s, $0.0027): time C WINS, cost E wins
- C beats E in 1 config(s): [('chunked_gzip', 10000.0)]

**Checkpoint verdict: INTERESTING** (5 signal(s))

Overall correctness gate: PASS
