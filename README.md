# Pushdown Is Not Free: Storage-Side PII Redaction in Text-Cleaning Pipelines

A small-scale measurement study of **storage-side pushdown for LLM data-cleaning pipelines**, with an open, pluggable benchmark toolkit. The headline result: pushing PII redaction into storage is 3.4-3.6x slower than pulling raw data out at the same network speed, and the pushdown-vs-pull decision flips with PII density and storage CPU quota.

## The three schemes (paper notation)

- **Scheme A (full pull):** transfer raw documents out of storage, then clean at compute. Baseline.
- **Scheme C (full pushdown):** run the whole cleaning pipeline at the storage side under a CPU quota, then transfer cleaned documents.
- **Scheme E (same-region CPU cluster):** transfer raw documents to a co-located CPU cluster over a fast link (10 Gbps), then clean there. Models "cheap local compute".

Scheme R (redaction-only pushdown: redact at storage, clean at compute) is also implemented in `scripts/10_run_scheme.py`.

The cleaning pipeline: rule filter -> language ID -> PII redaction -> MinHash signature -> exact dedup. All PII is **synthetic** (injected into public FineWeb text at controlled densities d01/d10/d30); no real personal data is used anywhere.

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 1. Build the synthetic-PII corpus (20k docs x 3 density tiers; ~72MB)
.venv/bin/python scripts/40_pii_data.py

# 2. Run the 11-run measurement matrix (~4 hours on a 2-vCPU box; resume-safe)
bash scripts/run_pii_matrix.sh

# 3. Reports
#    experiments/pii_matrix/report.md        (timings, bytes, correctness)
#    experiments/pii_matrix/cost_onepager.md (cost model)
```

For repeat runs with 95% CIs (n=3, t=4.303): `bash scripts/run_pii_extras.sh`, then
`python scripts/25_repeat_ci.py --orig "experiments/pii_matrix/*.json" --reps "experiments/pii_matrix_r2/*.json" --extra "experiments/pii_redact_only/*.json" --out experiments/repeat_ci_report.md`.

## Results

- `experiments/pii_matrix/report.md` - per-run timings, network bytes, output hashes, correctness gate
- `experiments/pii_matrix/cost_onepager.md` - derived cost model
- `experiments/pii_matrix/*.json` - raw per-run records (small, committed)
- `data_pii/` - synthetic PII corpus + `manifest.json` (committed, 72MB)

Large raw corpora (`data/`) and intermediate shards (`experiments/subsets/`, `experiments/storage_nodes/`) are regenerable and intentionally not committed.

## Paper

> **Pushdown Is Not Free: A Small-Scale Measurement of Storage-Side PII Redaction in Text-Cleaning Pipelines**
> Feilian Huang, Independent Researcher, 2026. (arXiv: TBD)

See `paper/paper.md` for the full manuscript and `paper/references.bib` for the bibliography.

## Layout

- `plugins/base.py` - plugin interface; `plugins/cleaning.py` - deterministic cleaning steps
- `plugins/minio_duckdb/` - reference storage/compute implementation (local-shard version)
- `plugins/airmettle_stub/` - reserved plugin slot (not implemented)
- `pipeline_specs/` - declarative pipeline specs
- `scripts/` - 00 data prep / 10 scheme runner / 20 reporting / 25 repeat CI / 40 PII data / run_*.sh
- `costs/pricing.yaml` - cost constants
- `docs/` - literature review, pushdownability matrix, venue notes
- `paper/` - manuscript, bibliography, release checklist

## License

Apache 2.0 (see `LICENSE`).
