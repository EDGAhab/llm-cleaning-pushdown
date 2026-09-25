# Pushdown Is Not Free: Measuring the Performance and Compliance Trade-offs of Storage-Side Data Cleaning for LLM Pipelines

**Feilian Huang**
Independent Researcher

*Draft v0.1, 2026-09-24. All numbers are from `experiments/pii_matrix/report.md` and `cost_onepager.md` (11 measured runs). No cloud was used; pricing is placeholder.*

## Abstract

Pushing data cleaning down to storage nodes is an appealing idea for LLM data pipelines: filter and redact near the data, transfer less, and keep sensitive content from ever leaving storage. We built a pushdown benchmark harness and measured three placement schemes on a PII-redaction cleaning pipeline over FineWeb-style text: A (pull everything, clean on compute, the status quo), C (full pushdown: rule filtering, language identification, and PII regex redaction all run on the storage side under a CPU quota), and E (same-region CPU cluster, the strongest baseline). Across 11 measured runs, full pushdown at 100 Mbps is slower than the pull-everything baseline in every configuration: 8.28x slower at 10% storage CPU quota, 3.47-3.70x at 25% quota, and still 2.05x at 50% quota, with zero byte reduction (1.00x transferred in all runs). The same-region CPU cluster is both the fastest and the cheapest ($0.0027/run vs $0.0049 for A and $0.0050-$0.0052 for C). Pushdown's defensible value is not performance but compliance: in scheme C, PII redaction happens on the storage side and zero unredacted PII leaves storage, while schemes A and E necessarily pull the raw documents, exposing every injected PII instance (208, 1,970, and 12,001 across our three density tiers) before redaction. We quantify this compliance premium (roughly 3.5x time-to-ready at 25% quota) and report the result honestly as a negative performance result with a compliance-shaped consolation: pushdown is not free, quota is the decisive knob, and the honest justification for storage-side cleaning is regulatory, not economic.

## 1. Introduction

Modern LLM datasets are built by cleaning web-scale text: heuristic quality filtering, language identification, PII scrubbing, and deduplication, as exemplified by the public DataTrove/FineWeb pipeline (Penedo et al., 2024). In the standard architecture, all of this compute happens on the compute cluster after the raw data has been pulled across the network. Storage nodes sit mostly idle.

The pushdown intuition is simple: storage nodes have CPUs too, so run the cleaning steps where the data lives, transfer only clean data, and as a bonus, sensitive content never leaves storage in raw form. Prior work has explored pushdown for adjacent problems: HAPI (SoCC 2024) and SOPHON (HotStorage 2024) push image preprocessing to object stores during training, OffloadFS (arXiv 2026) offloads RocksDB compaction and image prep to disaggregated storage, and the database literature (PushdownDB, ICDE 2020; FlexPushdownDB, VLDB 2021) has studied S3-side query pushdown for years. But training-time image preprocessing is not training-time text cleaning, and none of this work measures where the break-even point lies for an LLM cleaning pipeline, which steps are even pushable (global deduplication is inherently cross-shard), and what the compliance story costs in wall-clock time.

We set out to answer "when does pushdown pay off" with a neutral measurement study, preregistering four hypotheses (H1: below some storage CPU quota, pushdown is slower than pull-everything; H2: same-region CPU wins single-round but pushdown wins over iterations; H3: chunked compression changes the winner; H4: pushdown interferes with foreground reads above some quota). This paper reports the PII-compliance phase of that study, the phase the project pivoted to after an early checkpoint showed full pushdown has no robust performance advantage over the same-region CPU baseline. Our contributions:

1. A pushdown benchmark harness with declarative pipeline specs, pluggable storage backends, and automatic correctness gating (per-document output hashing across schemes).
2. An 11-run measurement matrix on a PII-redaction pipeline with synthetic PII injected at three densities, comparing pull-everything (A), full pushdown under storage CPU quotas of 10/25/50% (C), and same-region CPU cluster (E).
3. An honest negative result: full pushdown loses on time and cost in every tested configuration at 100 Mbps, quota is the decisive variable, and byte transfer is unchanged (1.00x).
4. A quantified compliance trade-off: storage-side redaction keeps all PII inside storage at a measured premium of about 3.5x time-to-ready (25% quota) over the status quo.

We also report exactly where our methodology is weak (Section 7), because a measurement paper that hides its error bars is worse than no measurement paper.

## 2. Design

### 2.1 Placement schemes

We compare three schemes, deliberately skipping fancier hybrids until the simple ones are understood:

- **A (pull everything):** the status quo. The compute cluster reads all raw documents from storage, then runs the full cleaning pipeline locally.
- **C (full pushdown):** every local (per-document) pipeline step runs on the storage side; only cleaned documents cross the network. Storage-side CPU is throttled with cpulimit to simulate a quota (10%, 25%, 50% of the storage node's CPU), since real storage nodes must reserve cycles for foreground serving.
- **E (same-region CPU cluster):** the strongest baseline. The identical pipeline runs on CPUs located in the same region as the data (modeled as 10 Gbps), i.e., move the compute to the data instead of moving the cleaning into the storage software.

Scheme D (split: MinHash signatures computed storage-side, global LSH bucketing on compute) and scheme B (column pruning) exist in the project roadmap but are not measured in this paper.

### 2.2 Pipeline

The pipeline under test is a FineWeb-style local cleaning pipeline declared in `pipeline_specs/fineweb_default.json`:

1. `rule_filter`: Gopher/FineWeb-style heuristic filters (length, symbol ratio, uppercase ratio).
2. `language_id`: keep English above 0.9 confidence.
3. `pii_redact`: regex redaction of email, US phone, and US SSN patterns, replaced with `[REDACTED]`.
4. `minhash_sign`: 128-permutation MinHash signatures (computed storage-side in scheme C).
5. `exact_dedup`: global exact deduplication, always on compute in every scheme (it is inherently cross-shard).

Fixed seed 42 throughout; outputs are sorted by document id and hashed per document for the cross-scheme correctness gate.

### 2.3 PII tiers and compliance metric

The compliance scenario (handoff "scenario one"): an enterprise fine-tunes on internal sensitive data and wants PII redacted before raw documents ever leave storage. We inject synthetic PII (never real personal data) into a shared base of 20k FineWeb documents, varying only PII density across three tiers: d01 (1% of documents, 208 PII instances), d10 (10%, 1,970 instances), d30 (30%, 1-3 per document, 12,001 instances). Before injection, we precleaned the base text with the pipeline's own regexes, replacing 3,076 naturally occurring PII-shaped matches with `[PRECLEARED]`, so redaction counts measure exactly the synthetic injection. A build-time validation re-runs the true `pii_redact` over every tier file and asserts the redaction count exactly equals the injected count (208/1970/12001, all pass) with zero PII-shaped residue afterward.

The derived compliance metric needs no new instrumentation: **unredacted PII leaving storage**. Schemes A and E pull raw documents first and redact on compute, so their exposure equals the tier's injected total. Scheme C redacts on the storage side, so its exposure is 0. The compliance premium is the time and cost ratio of C (at a given quota) to A within the same tier.

### 2.4 Experimental setup

Single-machine simulation: storage and compute are co-located processes, and transfer time is computed from a bandwidth model (100 Mbps for the cross-cloud scenario, 10 Gbps for same-region). This is the study's largest limitation (Section 7): absolute times do not transfer to real clouds, but the compared schemes share the identical model, so ratios are internally consistent. Each of A, C-at-25%-quota, and E ran once per PII tier; C was additionally scanned at 10% and 50% quota on the middle tier, for 11 runs total. Data format is chunked gzip JSONL in all runs. Cost uses placeholder pricing constants (`costs/pricing.yaml`; real cloud pricing was scheduled for a later project week), so cost conclusions are directional only.

## 3. Evaluation

### 3.1 Full pushdown is slower, at every quota

Table 1 summarizes the 11 measured runs. At 100 Mbps, full pushdown (C) is slower than pull-everything (A) in every configuration, and the slowdown is monotone in the storage CPU quota:

| scheme | quota | time_to_ready (s) | vs A | cost ($/run) | GB transferred |
|---|---|---|---|---|---|
| A | n/a | 228.9 / 246.1 / 232.2 | 1.00x | 0.0049 | 0.025 |
| C | 10% | 1895.0 | 8.28x | 0.0052 | 0.025 |
| C | 25% | 794.3 / 841.3 / 845.8 | 3.47x / 3.68x / 3.70x | 0.0050-0.0052 | 0.025 |
| C | 50% | 469.5 | 2.05x | 0.0051 | 0.025 |
| E | n/a | 227.8 / 230.0 / 246.9 | 1.00x / 1.00x / 1.08x | 0.0027-0.0028 | 0.025 |

(Ratios use the 228.9 s A run as baseline, as computed by the automated report. The three times per scheme are one run per PII-density tier.)

Three observations. First, quota is the decisive knob: halving the storage CPU quota roughly doubles the slowdown, and at 10% quota pushdown is 8.28x slower than doing nothing clever at all. Storage nodes that must protect foreground serving cycles cannot afford to donate them to cleaning. Second, pushdown buys zero byte reduction here: every run transfers exactly 0.025 GB (1.00x). The pipeline's filter rate is only about 1% and redaction does not shrink documents, so there is nothing for pushdown to save on the wire; the classic pushdown argument (ship less data) simply does not apply to this workload shape. Third, the same-region CPU cluster (E) matches or beats pull-everything on time (1.00-1.08x) while costing roughly 45% less ($0.0027 vs $0.0049), because same-region transfer is cheap in the cost model. E is the baseline that pushdown must beat, and it does not beat it.

### 3.2 Cost: pushdown is not cheaper either

Under placeholder pricing, per-run cost is $0.0049 for A (all three runs), $0.0050-$0.0052 for C (rising slightly as quota falls, since longer wall time burns more CPU-hours: 0.069 CPU-h at 10% quota vs 0.062-0.064 for A), and $0.0027-$0.0028 for E. The ordering E < A < C is structural (same-region transfer < cross-region transfer; throttled storage CPU burns wall time), even though the absolute dollar magnitudes should not be quoted as predictions. The automated checkpoint verdict for this matrix is INTERESTING with 5 signals, all of them of the form "low quota hurts."

### 3.3 The compliance premium: what zero exposure costs

If the objective is compliance rather than speed, scheme C is the only one that satisfies "PII never leaves storage in raw form":

| tier | injected PII | exposure A | exposure E | exposure C | time premium C(25%) vs A |
|---|---|---|---|---|---|
| d01 | 208 | 208 | 208 | 0 | 3.47-3.70x (tier-pooled) |
| d10 | 1,970 | 1,970 | 1,970 | 0 | 3.47-3.70x (tier-pooled) |
| d30 | 12,001 | 12,001 | 12,001 | 0 | 3.47-3.70x (tier-pooled) |

(Time premiums are pooled across tiers because the automated report does not label runs by tier; see Section 7. The per-tier C-at-25% times are 794.3, 841.3, and 845.8 s against A times of 228.9, 246.1, and 232.2 s.)

In words: keeping PII inside storage costs roughly a 3.5x time-to-ready premium at 25% storage CPU quota (about 2x at 50% quota, 8.3x at 10%), and a small cost premium ($0.0050-$0.0052 vs $0.0049 per run). Whether that premium is worth paying is a regulatory judgment, not a performance one, which is exactly the paper's reframing: the honest justification for storage-side cleaning is compliance, and now it has a measured price tag.

### 3.4 Preregistered hypotheses, honestly scored

- **H1 (low quota hurts):** supported. 8.28x/3.5-3.7x/2.05x slowdowns at 10%/25%/50% quota are monotone and large.
- **H2 (E wins single-round, pushdown wins over iterations):** half tested. E wins single-round decisively; the multi-iteration experiment was not run, so the second clause is untested, not supported.
- **H3 (chunked compression changes the winner):** untested in this matrix (single format). An earlier probe with WARC input found a 0.93x byte ratio because the test HTML was barely larger than extracted text; the high-shrinkage case remains untested.
- **H4 (foreground interference quota):** untested; no foreground-read interference runs were performed.

## 4. Related Work

**Training-time preprocessing pushdown.** HAPI (SoCC 2024) splits transfer-learning DNNs to run feature extraction on cloud object stores (up to 11x application speedup); SOPHON (HotStorage 2024) shows full pushdown of image preprocessing can hurt and proposes selective pushdown via a two-phase profiler (2.2x traffic reduction on OpenImages at 500 Mbps); OffloadFS (arXiv 2026) offloads RocksDB compaction and image prep to NVMeoF storage nodes. FastFlow (VLDB 2023), Pecan (ATC 2024), and tf.data service (SoCC 2023) optimize training-time input pipelines via placement and ordering. All of these target training-time image/audio preprocessing; we study training-time text cleaning, where the workload shape (tiny filter rates, regex CPU cost, global dedup) behaves differently.

**Database pushdown.** PushdownDB (ICDE 2020) used S3 Select for filter/projection pushdown (30% cheaper, 6.7x faster on TPC-H); FlexPushdownDB (VLDB 2021, extended in VLDBJ 2024) added hybrid pushdown/caching and adaptive pushback. The operators differ (SQL aggregates vs. regex redaction and MinHash), but the cautionary parallel holds: FlexPushdownDB's pushback mechanism exists precisely because blind pushdown under resource pressure loses, which is what our quota scan reproduces for text cleaning.

**Cleaning pipelines and dedup.** DataTrove and FineWeb (Penedo et al., 2024) define the reference text-cleaning pipeline we mirror; their compute runs entirely on compute clusters with no storage-side concept. Lee et al. (ACL 2022) established the value of deduplication for language models; we treat global dedup as the canonical unpushable step. Klimovic's SIGARCH blog (2021) argued for pushing data-reducing transforms near storage; our measurement suggests text cleaning rarely reduces data enough for that argument to bite. US patent 12438943B2 (Nutanix, 2025) describes offloading ML preprocessing, including PII masking templates, to storage nodes; we cite it as related public art only, with no legal analysis.

## 5. Threats to Validity

We list these plainly because they bound every claim above.

1. **Single-machine simulation.** Storage and compute share one box; transfer time comes from a bandwidth model. Ratios are internally consistent, but absolute times (e.g., 228.9 s) must not be extrapolated to any real cloud.
2. **Placeholder pricing.** `cost_usd` uses placeholder constants. The ordering E < A < C is structural (same-region vs cross-region transfer, throttled CPU burning wall time); dollar magnitudes are not predictions.
3. **Single measurements, no repeats.** Every ratio in Table 1 is one run per cell; there are no error bars. The 3.47x/3.68x/3.70x spread across tiers hints at run-to-run noise of a few percent, which does not change any qualitative conclusion but forbids fine distinctions.
4. **Synthetic PII on a 20k-document subset.** Real PII has messier distributions; our densities (208/1970/12001) are controlled, not representative.
5. **Correctness gate false alarm.** The automated report flags correctness FAIL (3 distinct output hashes across 11 runs). This is a reporting artifact: the three hashes correspond to the three PII-density tiers, and within each tier the A, C, and E outputs are hash-identical. The gate compared across tiers by mistake.
6. **Legacy phone-template artifact.** In earlier project weeks, the synthetic phone template `555-01XX` produced 7-digit numbers that the pipeline's 10-digit NANP regex never matched, a silent under-redaction in old data. Phase 4 fixed the template to `(415) 555-01XX` and validated exact redaction counts; old results were left as-is and are not used in this paper.
7. **Compliance metric scope.** "Compliance = PII never leaves storage" ignores alternatives such as encrypted transfer with compute-side redaction inside a trusted enclave; we do not claim pushdown is the only compliant architecture.
8. **Untested hypotheses.** H2's iteration clause, H3, and H4 were not tested in this matrix; the density-boundary question (does C's disadvantage grow with PII density) was planned but the auto-report does not label runs by tier, so it remains future work.

## 6. Conclusion

Pushdown is not free. For a PII-redaction text cleaning pipeline at 100 Mbps, full storage-side pushdown is 2.05-8.28x slower than pull-everything depending on storage CPU quota, transfers exactly as many bytes, and costs slightly more; a same-region CPU cluster is faster and roughly 45% cheaper. The result is negative on performance and we report it as such. Pushdown's remaining justification is compliance: it is the only tested scheme under which zero unredacted PII leaves storage, at a measured premium of about 3.5x time-to-ready at 25% quota. If your threat model is regulatory, that premium now has a number attached; if your objective is speed or cost, move the compute to the data instead.

Our benchmark harness, pipeline specs, and measurement data are released open source (Apache 2.0) for reproduction and extension; the natural next steps are the untested preregistered hypotheses (iteration effects, interference quotas, high-shrinkage inputs) and the split scheme D, which keeps global dedup on compute while pushing signatures to storage.

## References

- Petrescu et al., HAPI: Accelerating Transfer Learning with Near-Data Computation on Cloud Object Stores, SoCC 2024.
- Wang, Waldspurger, Sundararaman, SOPHON: A Selective Preprocessing Offloading Framework for Reducing Data Traffic in DL Training, HotStorage 2024.
- Moon et al., OffloadFS: Leveraging Disaggregated Storage for Computation Offloading, arXiv:2604.13743, 2026.
- Yu et al., PushdownDB: Accelerating a DBMS Using S3 Computation, ICDE 2020.
- Yang et al., FlexPushdownDB: Hybrid Pushdown and Caching in a Cloud DBMS, VLDB 2021; extended in VLDBJ 2024.
- Audibert et al., tf.data service: A Case for Disaggregating ML Input Data Processing, SoCC 2023.
- Graur et al., Pecan: Cost-Efficient ML Data Preprocessing with Automatic Transformation Ordering and Hybrid Placement, USENIX ATC 2024.
- Um et al., FastFlow: Accelerating Deep Learning Model Training with Smart Offloading of Input Data Pipeline, VLDB 2023.
- Penedo et al., The FineWeb Datasets, arXiv:2406.17557, 2024; DataTrove, https://github.com/huggingface/datatrove.
- Lee et al., Deduplicating Training Data Makes Language Models Better, ACL 2022.
- Klimovic, Rethinking Data Storage and Preprocessing for ML, ACM SIGARCH blog, 2021.
- US Patent 12438943B2, System and method for offloading preprocessing of machine learning data to remote storage, Nutanix Inc., 2025. Cited as public related art only; no legal analysis.

## Artifact Note

Code, declarative pipeline specs, experiment scripts, and raw results: to be released on GitHub under Apache 2.0 (link to be added before arXiv posting). Raw result files: `experiments/pii_matrix/report.md`, `experiments/pii_matrix/cost_onepager.md`. Reproduction: `scripts/run_pii_matrix.sh` reruns the 11-run matrix; per-document output hashes provide the cross-scheme correctness check.
