# AirMettle Plugin Integration Guide (for the vendor engineer)

> Status: STUB. Nothing here is implemented and nothing here uses AirMettle-internal
> material. This guide is written so that an engineer with access to the AirMettle
> engine can implement `plugins/airmettle_stub/plugin.py` in roughly 1-2 weeks.

## What the toolkit expects

Implement the `PushdownPlugin` interface in `plugins/base.py`:

1. **`declare_capabilities() -> {step_type: "full"|"partial"|"none"}`**
   Step types: `rule_filter`, `language_id`, `pii_redact`, `minhash_sign`,
   `lsh_dedup`, `exact_dedup`. Anything not `"full"` falls back to the compute
   side automatically and shows up in the pushdownability matrix.

2. **`put_dataset(local_paths, dataset_id) -> [refs]`**
   Ingest local files into the engine. Shard by record (document) boundaries so
   each shard can be processed independently; the reference implementation
   shards into per-node directories (`LocalShardedPlugin.put_dataset`).

3. **`get_bytes(ref) -> bytes`**
   Metered fetch used for egress accounting.

4. **`execute_pushdown(spec, input_refs, cpu_quota) -> StepResult`**
   - Input: the declarative pipeline spec (`pipeline_specs/fineweb_default.json`),
     NOT raw S3 request streams.
   - Run every step your capabilities claim, deterministically (respect
     `spec["seed"]`).
   - `cpu_quota`: fraction of one CPU the executor may use (e.g. 0.10 = 10%).
     Honor it via cgroups; report whether it was enforced in `StepResult.notes`.
   - Return per-shard output refs plus `docs_in/docs_out/bytes_read/
     bytes_written/cpu_seconds/wall_seconds`.

## Step semantics (shared, deterministic)

Import and reuse `plugins/cleaning.py` (`apply_local_steps`) so outputs are
byte-identical with the reference plugin. If your engine has native equivalents
(e.g. SIMD regex), you may use them as long as `scripts/verify_correctness`
(output hash comparison across schemes) still passes.

## Testing your implementation

```bash
python3 scripts/10_run_scheme.py --scheme C --plugin airmettle --format chunked_gzip
python3 scripts/20_report.py --compare A C
```

Both must show `output_sha256` identical to scheme A for the same config.

## What we need from you (nothing else)

- The plugin code + this checklist filled in: which steps are `"full"`,
  how `cpu_quota` is enforced, and the engine version used.
- No access to our data, no changes to the toolkit core.
