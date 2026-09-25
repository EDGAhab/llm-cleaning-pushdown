"""10_run_scheme.py: run scheme A (full pull), C (full pushdown) or E
(same-region CPU cluster) for one config.

All schemes run the SAME declarative spec; global exact_dedup always runs on
the compute side. Output correctness: final doc sets must be byte-identical
(sha256 compared in 20_report.py).

Metrics recorded per run (results JSON):
  bytes_storage_to_compute, transfer_time_s (= bytes / bandwidth),
  storage_cpu_s, storage_wall_s, compute_cpu_s, compute_wall_s,
  time_to_ready_s (= transfer + compute + storage wall for C),
  docs_in/out, filter_rate, pii_redactions, output_sha256, cost_usd.

Usage:
  python3 scripts/10_run_scheme.py --scheme A --format chunked_gzip \
      --bandwidth-mbps 100 --out experiments/week3_ac/A_chunked_100.json
  python3 scripts/10_run_scheme.py --scheme C --format chunked_gzip \
      --cpu-quota 0.10 --bandwidth-mbps 100 --out experiments/week3_ac/C_chunked_100_q10.json
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import resource
import sys
import time

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plugins.cleaning import apply_local_steps, exact_dedup_key  # noqa: E402
from plugins.minio_duckdb.plugin import LocalShardedPlugin  # noqa: E402

FORMATS = {
    "whole_gzip": ["fmt_whole_gzip/sample.jsonl.gz"],
    "chunked_gzip": ["fmt_chunked_gzip/chunks"],   # directory -> all chunks
    "zstd_parquet": ["fmt_zstd_parquet/sample.parquet"],
    "warc_html": ["fmt_warc_html"],                # directory -> synthetic HTML-wrapped chunks
}


def resolve_inputs(data_root: str, fmt: str):
    if fmt in ("chunked_gzip", "warc_html"):
        sub = "fmt_chunked_gzip" if fmt == "chunked_gzip" else "fmt_warc_html"
        d = os.path.join(data_root, sub, "chunks")
        return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".gz"))
    return [os.path.join(data_root, p) for p in FORMATS[fmt]]


def maybe_subset_single_file(src: str, limit_refs: int, tmpdir: str) -> str:
    """Build a temp subset file with the first limit_refs*CHUNK_DOCS docs.

    Single-file formats (whole_gzip / zstd_parquet) hold the full 389k docs;
    --limit-refs must cut docs, not files, to keep the subset comparable
    across formats.
    """
    CHUNK_DOCS = 20_000
    n_want = limit_refs * CHUNK_DOCS
    os.makedirs(tmpdir, exist_ok=True)
    if src.endswith(".parquet"):
        import pyarrow.parquet as pq
        out = os.path.join(tmpdir, f"subset_{n_want}.parquet")
        if not os.path.exists(out):
            pf = pq.ParquetFile(src)
            tbl = pf.read().slice(0, n_want)
            pq.write_table(tbl, out, compression="zstd")
        return out
    out = os.path.join(tmpdir, f"subset_{n_want}.jsonl.gz")
    if not os.path.exists(out):
        n = 0
        with gzip.open(src, "rt", encoding="utf-8") as fin, \
             gzip.open(out, "wt", encoding="utf-8") as fout:
            for line in fin:
                if n >= n_want:
                    break
                fout.write(line)
                n += 1
    return out


def read_docs_from_bytes(raw: bytes, path: str):
    if path.endswith(".parquet"):
        import pyarrow.parquet as pq
        table = pq.read_table(io.BytesIO(raw), columns=["id", "text"])
        for i, t in zip(table.column("id").to_pylist(), table.column("text").to_pylist()):
            yield {"id": i, "text": t}
    else:
        with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def order_independent_dedup(docs):
    """Exact dedup that does not depend on input order: keep smallest id per text."""
    best = {}
    for d in docs:
        k = exact_dedup_key(d)
        if k not in best or str(d["id"]) < str(best[k]["id"]):
            best[k] = d
    return sorted(best.values(), key=lambda d: str(d["id"]))


def _process_ref(args):
    """Module-level (picklable) worker: one chunk -> cleaned docs + stats."""
    ref, spec, count_bytes = args
    from plugins.minio_duckdb.plugin import LocalShardedPlugin  # noqa
    # lightweight: read without a plugin instance
    import gzip as _gzip, io as _io, json as _json
    with open(ref, "rb") as f:
        raw = f.read()
    if count_bytes:
        nbytes = len(raw)
    else:
        nbytes = 0
    cleaned, docs_in, n_redact = [], 0, 0
    for doc in read_docs_from_bytes(raw, ref):
        docs_in += 1
        out = apply_local_steps(doc, spec)
        if out is not None:
            n_redact += out["pii_redactions"]
            cleaned.append({"id": out["id"], "text": out["text"]})
    return cleaned, docs_in, n_redact, nbytes


def run_scheme_A(plugin: LocalShardedPlugin, spec, refs):
    """Full pull: compute downloads raw bytes, runs local steps + dedup."""
    import multiprocessing as mp
    t0 = time.time()
    # bytes are metered through plugin.get_bytes (counts egress)
    with mp.Pool(processes=min(2, len(refs))) as pool:
        parts = pool.map(_process_ref,
                         [(r, spec, False) for r in refs])
    # meter egress
    for r in refs:
        plugin.get_bytes(r)
    cleaned, docs_in, n_redact = [], 0, 0
    for c, di, nr, _ in parts:
        cleaned.extend(c)
        docs_in += di
        n_redact += nr
    deduped = order_independent_dedup(cleaned)
    # RUSAGE_SELF misses the mp.Pool workers; add RUSAGE_CHILDREN (pool is
    # joined by the context manager above, so children are reaped here).
    cpu = resource.getrusage(resource.RUSAGE_SELF)
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    return deduped, {
        "docs_in": docs_in, "docs_out": len(deduped), "pii_redactions": n_redact,
        "wall_s": round(time.time() - t0, 2),
        "cpu_s": round(cpu.ru_utime + cpu.ru_stime + ch.ru_utime + ch.ru_stime, 2),
    }


def run_scheme_C_compute(plugin: LocalShardedPlugin, out_refs):
    """Full pushdown: compute pulls already-cleaned docs, runs dedup only."""
    t0 = time.time()
    cleaned = []
    for r in out_refs:
        raw = plugin.get_bytes(r)
        with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cleaned.append(json.loads(line))
    deduped = order_independent_dedup(cleaned)
    cpu = resource.getrusage(resource.RUSAGE_SELF)
    return deduped, {
        "docs_out": len(deduped),
        "wall_s": round(time.time() - t0, 2),
        "cpu_s": round(cpu.ru_utime + cpu.ru_stime, 2),
    }


def run_scheme_R(plugin: LocalShardedPlugin, spec, refs, cpu_quota):
    """Redaction-only pushdown: storage runs ONLY pii_redact (the compliance
    minimum for PII to leave storage); compute pulls the redacted docs and
    runs the remaining local steps (rule_filter -> language_id -> minhash_sign)
    plus global exact_dedup. Measures the LOWER BOUND of the compliance premium
    (vs full-pushdown scheme C = upper bound).

    Note: redact runs before rule_filter here (filter at compute sees redacted
    text), while scheme A filters raw text first. "[REDACTED]" is whitespace-
    neutral (word count unchanged) but shifts uppercase/symbol ratios, so a few
    boundary docs may flip filter decisions; output_sha256 comparison against
    scheme A detects this.
    """
    storage_spec = dict(spec)
    storage_spec["steps"] = [s for s in spec["steps"] if s["type"] == "pii_redact"]
    if not storage_spec["steps"]:
        raise ValueError("scheme R requires a pii_redact step in the spec")
    pres = plugin.execute_pushdown(storage_spec, refs, cpu_quota=cpu_quota)

    compute_spec = dict(spec)
    compute_spec["steps"] = [s for s in spec["steps"]
                             if s["type"] in ("rule_filter", "language_id",
                                               "minhash_sign")]
    t0 = time.time()
    import multiprocessing as mp
    with mp.Pool(processes=min(2, len(pres.output_refs))) as pool:
        parts = pool.map(_process_ref,
                         [(r, compute_spec, False) for r in pres.output_refs])
    # meter egress of the redacted docs
    for r in pres.output_refs:
        plugin.get_bytes(r)
    cleaned, _, n_redact = [], 0, 0
    for c, _, nr, _ in parts:
        cleaned.extend(c)
        n_redact += nr  # expected 0: redaction already done at storage
    deduped = order_independent_dedup(cleaned)
    # pool is joined by the context manager, so RUSAGE_CHILDREN is safe to add
    cpu = resource.getrusage(resource.RUSAGE_SELF)
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    return pres, deduped, {
        "docs_in": pres.docs_in, "docs_out": len(deduped),
        "pii_redactions": pres.notes.get("pii_redactions", 0),
        "wall_s": round(time.time() - t0, 2),
        "cpu_s": round(cpu.ru_utime + cpu.ru_stime + ch.ru_utime + ch.ru_stime, 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scheme", choices=["A", "C", "E", "R"], required=True)
    ap.add_argument("--format", choices=list(FORMATS), required=True)
    ap.add_argument("--cpu-quota", type=float, default=None,
                    help="storage CPU quota fraction, e.g. 0.10 (scheme C only)")
    ap.add_argument("--bandwidth-mbps", type=float, required=True)
    ap.add_argument("--spec", default="pipeline_specs/fineweb_default.json")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--storage-root", default="experiments/storage_nodes")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--limit-refs", type=int, default=None,
                    help="use only the first N input refs (subset trial)")
    args = ap.parse_args()

    with open(args.spec) as f:
        spec = json.load(f)
    with open("costs/pricing.yaml") as f:
        pricing = yaml.safe_load(f)

    plugin = LocalShardedPlugin(args.storage_root, shards=4)
    src_files = resolve_inputs(args.data_root, args.format)
    if args.limit_refs:
        if args.format in ("chunked_gzip", "warc_html"):
            src_files = src_files[:args.limit_refs]
        else:
            src_files = [maybe_subset_single_file(
                src_files[0], args.limit_refs,
                os.path.join("experiments", "subsets"))]
    refs = plugin.put_dataset(src_files, f"{args.format}")
    plugin.bytes_served = 0  # reset meter; put_dataset used local copy, not "network"

    result = {"scheme": args.scheme, "format": args.format,
              "cpu_quota": args.cpu_quota, "bandwidth_mbps": args.bandwidth_mbps,
              "label": args.label}
    t_all = time.time()
    if args.scheme == "R":
        pres, docs, cstat = run_scheme_R(plugin, spec, refs, args.cpu_quota)
        result["storage_cpu_s"] = round(pres.cpu_seconds, 2)
        result["storage_wall_s"] = round(pres.wall_seconds, 2)
        result["pushdown_notes"] = pres.notes
        result["compute_cpu_s"] = cstat["cpu_s"]
        result["compute_wall_s"] = cstat["wall_s"]
        result["docs_in"] = cstat["docs_in"]
        result["docs_out"] = cstat["docs_out"]
        result["pii_redactions"] = cstat["pii_redactions"]
        result["redact_only"] = True
    elif args.scheme in ("A", "E"):
        # A: full pull to the user's own compute (cross-cloud egress).
        # E: same pipeline on a CPU cluster colocated with the data
        #    (same-region transfer, regional CPU rental). In this harness E
        #    is A's compute path at regional bandwidth with regional
        #    egress pricing; the distinction is cost + bandwidth scenario,
        #    not compute speed.
        docs, cstat = run_scheme_A(plugin, spec, refs)
        result["storage_cpu_s"] = 0.0
        result["storage_wall_s"] = 0.0
        result["compute_cpu_s"] = cstat["cpu_s"]
        result["compute_wall_s"] = cstat["wall_s"]
        result["docs_in"] = cstat["docs_in"]
        result["docs_out"] = cstat["docs_out"]
        result["pii_redactions"] = cstat["pii_redactions"]
    else:
        pres = plugin.execute_pushdown(spec, refs, cpu_quota=args.cpu_quota)
        result["storage_cpu_s"] = round(pres.cpu_seconds, 2)
        result["storage_wall_s"] = round(pres.wall_seconds, 2)
        result["pushdown_notes"] = pres.notes
        docs, cstat = run_scheme_C_compute(plugin, pres.output_refs)
        result["compute_cpu_s"] = cstat["cpu_s"]
        result["compute_wall_s"] = cstat["wall_s"]
        result["docs_in"] = pres.docs_in
        result["docs_out"] = cstat["docs_out"]
        result["pii_redactions"] = pres.notes.get("pii_redactions", 0)
        result["sig_bytes_not_transferred"] = pres.notes.get("sig_bytes", 0)

    result["bytes_storage_to_compute"] = plugin.bytes_served
    bw_Bps = args.bandwidth_mbps * 1e6 / 8
    result["transfer_time_s"] = round(plugin.bytes_served / bw_Bps, 2)
    # time-to-ready: storage work and transfer are sequential in this harness
    result["time_to_ready_s"] = round(
        result["storage_wall_s"] + result["transfer_time_s"] + result["compute_wall_s"], 2)
    result["filter_rate"] = round(1 - result["docs_out"] / max(result["docs_in"], 1), 4)
    # NOTE: do NOT recompute pii_redactions from `docs` here: scheme-A docs are
    # {"id","text"} (count already in result from cstat), scheme-C docs carry
    # the worker-side count in pushdown_notes. Summing d.get(...) would zero it.
    result["output_sha256"] = hashlib.sha256(
        "".join(json.dumps(d, sort_keys=True, ensure_ascii=False)
                for d in docs).encode("utf-8")).hexdigest()
    result["total_wall_s"] = round(time.time() - t_all, 2)
    total_cpu_h = (result["storage_cpu_s"] + result["compute_cpu_s"]) / 3600
    gb = plugin.bytes_served / 1e9
    if args.scheme == "E":
        egress_price = pricing["usd_per_gb_egress_same_region"]
    else:
        egress_price = pricing["usd_per_gb_egress_cross_cloud"]  # cross-cloud placeholder
    result["cost_usd"] = round(
        total_cpu_h * pricing["usd_per_cpu_hour"] + gb * egress_price, 4)
    result["cost_usd_ex_egress"] = round(total_cpu_h * pricing["usd_per_cpu_hour"], 4)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({k: result[k] for k in
                      ("scheme", "format", "cpu_quota", "bandwidth_mbps",
                       "bytes_storage_to_compute", "transfer_time_s",
                       "storage_wall_s", "compute_wall_s", "time_to_ready_s",
                       "docs_in", "docs_out", "filter_rate",
                       "output_sha256", "cost_usd")}, indent=2))


if __name__ == "__main__":
    main()
