"""31_interference.py: foreground-read interference test (H4).

While a pushdown run executes at a given CPU quota, a foreground reader loop
issues random get_bytes() reads; records p50/p99 latency and throughput with
and without pushdown. A "knee" in p99 degradation vs quota supports H4.

Usage:
  python3 scripts/31_interference.py --format chunked_gzip \
      --quotas 0.10 0.25 0.50 --out experiments/week3_ac/interference.json
"""
import argparse
import json
import os
import random
import statistics
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plugins.minio_duckdb.plugin import LocalShardedPlugin  # noqa: E402

READS = 120


def foreground_probe(plugin: LocalShardedPlugin, refs, stop: threading.Event,
                     out: list):
    rng = random.Random(7)
    while not stop.is_set():
        r = rng.choice(refs)
        t0 = time.time()
        plugin.get_bytes(r)
        out.append(time.time() - t0)
        if len(out) >= READS and stop.is_set():
            break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", default="chunked_gzip")
    ap.add_argument("--quotas", nargs="+", type=float, default=[0.10, 0.25, 0.50])
    ap.add_argument("--spec", default="pipeline_specs/fineweb_default.json")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--storage-root", default="experiments/storage_nodes")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit-refs", type=int, default=None)
    args = ap.parse_args()

    with open(args.spec) as f:
        spec = json.load(f)
    plugin = LocalShardedPlugin(args.storage_root, shards=4)
    if args.format == "chunked_gzip":
        d = os.path.join(args.data_root, "fmt_chunked_gzip", "chunks")
        src = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".gz"))
        if args.limit_refs:
            src = src[:args.limit_refs]
    else:
        raise ValueError("interference test uses chunked_gzip")
    refs = plugin.put_dataset(src, "interference")
    plugin.bytes_served = 0

    results = {}
    # baseline: no pushdown
    lat, stop = [], threading.Event()
    t = threading.Thread(target=foreground_probe, args=(plugin, refs, stop, lat))
    t.start()
    time.sleep(8)
    stop.set()
    t.join()
    lat.sort()
    results["baseline"] = {"p50_ms": round(statistics.median(lat) * 1e3, 2),
                           "p99_ms": round(lat[int(0.99 * (len(lat) - 1))] * 1e3, 2),
                           "reads": len(lat)}

    for q in args.quotas:
        lat, stop = [], threading.Event()
        t = threading.Thread(target=foreground_probe, args=(plugin, refs, stop, lat))
        t.start()
        pres = plugin.execute_pushdown(spec, refs, cpu_quota=q)
        stop.set()
        t.join()
        lat.sort()
        p50 = statistics.median(lat) * 1e3
        p99 = lat[int(0.99 * (len(lat) - 1))] * 1e3
        results[f"quota_{q}"] = {
            "p50_ms": round(p50, 2), "p99_ms": round(p99, 2), "reads": len(lat),
            "p99_degradation_x": round(p99 / max(results["baseline"]["p99_ms"], 1e-9), 2),
            "pushdown_wall_s": round(pres.wall_seconds, 1),
            "throttle": pres.notes.get("throttle"),
            "quota_enforced": pres.notes.get("cpu_quota_enforced"),
        }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
