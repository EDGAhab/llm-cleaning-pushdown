"""30_pushdown_matrix.py: emit the pushdownability matrix for a spec x plugins.

Usage:
  python3 scripts/30_pushdown_matrix.py --spec pipeline_specs/fineweb_default.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plugins.minio_duckdb.plugin import LocalShardedPlugin  # noqa: E402
from plugins.airmettle_stub.plugin import AirMettlePlugin  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="pipeline_specs/fineweb_default.json")
    ap.add_argument("--storage-root", default="experiments/storage_nodes")
    args = ap.parse_args()
    with open(args.spec) as f:
        spec = json.load(f)

    plugins = [LocalShardedPlugin(args.storage_root),
               AirMettlePlugin()]
    steps = [s["type"] for s in spec["steps"]]
    rows = []
    for p in plugins:
        try:
            caps = p.declare_capabilities()
        except Exception as e:  # stub safety
            caps = {s: f"error: {e}" for s in steps}
        rows.append([p.name] + [caps.get(s, "none") for s in steps])

    header = ["plugin"] + steps
    widths = [max(len(str(c)) for c in col) for col in zip(header, *rows)]
    out = ["# Pushdownability matrix", "",
           "Capability: full = runs on storage; partial = split; none = compute fallback.",
           ""]
    out.append("| " + " | ".join(h.ljust(w) for h, w in zip(header, widths)) + " |")
    out.append("| " + " | ".join("-" * w for w in widths) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(c).ljust(w) for c, w in zip(row, widths)) + " |")
    text = "\n".join(out)
    print(text)
    os.makedirs("docs", exist_ok=True)
    with open("docs/pushdownability_matrix.md", "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
