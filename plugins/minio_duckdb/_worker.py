"""Pushdown worker subprocess: reads chunk files LOCAL to its node, applies the
declarative local steps, writes cleaned JSONL.GZ shards. Prints one JSON stats
line to stdout (the plugin parses the last line).
Usage: _worker.py <spec_json> <out_dir> <chunk1> [chunk2 ...]
"""
import gzip
import io
import json
import os
import resource
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from plugins.cleaning import apply_local_steps


def main() -> None:
    spec = json.loads(sys.argv[1])
    out_dir = sys.argv[2]
    chunks = sys.argv[3:]
    t0 = time.time()
    docs_in = docs_out = 0
    n_redact = 0
    bytes_read = 0
    out_refs = []
    sig_refs = []
    for idx, ch in enumerate(chunks):
        with open(ch, "rb") as f:
            raw = f.read()
        bytes_read += len(raw)
        out_path = os.path.join(out_dir, f"cleaned_{idx:04d}.jsonl.gz")
        sig_path = os.path.join(out_dir, f"sig_{idx:04d}.jsonl.gz")
        if ch.endswith(".parquet"):
            import pyarrow.parquet as pq
            table = pq.read_table(io.BytesIO(raw), columns=["id", "text"])
            records = ({"id": r[0], "text": r[1]}
                       for r in zip(table.column("id").to_pylist(),
                                    table.column("text").to_pylist()))
        else:
            records = (json.loads(line) for line in
                       gzip.open(io.BytesIO(raw), "rt", encoding="utf-8")
                       if line.strip())
        with gzip.open(out_path, "wt", encoding="utf-8") as fout, \
                gzip.open(sig_path, "wt", encoding="utf-8") as fsig:
            for doc in records:
                docs_in += 1
                out = apply_local_steps(doc, spec)
                if out is not None:
                    docs_out += 1
                    n_redact += out["pii_redactions"]
                    fout.write(json.dumps({"id": out["id"], "text": out["text"]},
                                          ensure_ascii=False) + "\n")
                    fsig.write(json.dumps({"id": out["id"], "minhash": out["minhash"]}) + "\n")
        out_refs.append(out_path)
        sig_refs.append(sig_path)
    bytes_written = sum(os.path.getsize(p) for p in out_refs)
    sig_bytes = sum(os.path.getsize(p) for p in sig_refs)
    # single process does all the work: RUSAGE_SELF (RUSAGE_CHILDREN is ~0 here)
    ru = resource.getrusage(resource.RUSAGE_SELF)
    cpu_s = ru.ru_utime + ru.ru_stime
    print(json.dumps({
        "docs_in": docs_in, "docs_out": docs_out,
        "pii_redactions": n_redact,
        "bytes_read": bytes_read, "bytes_written": bytes_written,
        "sig_bytes": sig_bytes,
        "cpu_seconds": round(cpu_s, 2),
        "wall_seconds": round(time.time() - t0, 2),
        "out_refs": out_refs,
        "sig_refs": sig_refs,
    }))


if __name__ == "__main__":
    main()
