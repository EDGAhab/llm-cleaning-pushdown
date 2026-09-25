# One-page cost report (week-3 trial, placeholder pricing 2026-09-24)

Pricing constants: see costs/pricing.yaml (placeholders; real cloud pricing collected week 8).

| config | $/run | GB egress | CPU-h |
|---|---|---|---|
| A/chunked_gzip/q=None/100Mbps | $0.0111 | 0.123 | 0.001 |
| C/chunked_gzip/q=0.1/100Mbps | $0.0111 | 0.123 | 0.002 |
| C/chunked_gzip/q=0.25/100Mbps | $0.0111 | 0.123 | 0.002 |
| C/chunked_gzip/q=0.5/100Mbps | $0.0111 | 0.123 | 0.002 |
| A/chunked_gzip/q=None/10000Mbps | $0.0112 | 0.123 | 0.001 |
| A/whole_gzip/q=None/100Mbps | $0.0116 | 0.123 | 0.012 |
| A/zstd_parquet/q=None/100Mbps | $0.0122 | 0.134 | 0.001 |
