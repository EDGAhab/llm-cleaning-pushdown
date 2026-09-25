"""00_prepare_data.py: build the week-3 trial dataset (1-2 GB) in 3 formats.

Source: FineWeb parquet shards downloaded directly from huggingface.co via
curl (the `datasets` streaming client breaks on this machine's proxy setup;
curl works). FREE, no auth needed. Target ~1.5 GB of raw JSONL.

Synthetic PII injection: ~1% of docs get clearly-fake PII
(synthetic.user.NNNN@example.invalid, 555-01XX numbers, 900-XX-XXXX SSNs)
so the pii_redact step has something verifiable to catch. No real PII ever.

Formats (per handoff):
  fmt_whole_gzip   : one .jsonl.gz for the whole sample
  fmt_chunked_gzip : N independently-gzipped chunks of M docs each
                     (record-boundary chunked; each chunk decompresses alone)
  fmt_zstd_parquet : zstd-compressed Parquet (columns: id, text)

Writes data/manifest.json with sizes, doc counts, sha256 per file.
"""
import argparse
import gzip
import hashlib
import json
import os
import random
import subprocess
import sys

REPO = "HuggingFaceFW/fineweb"
TARGET_BYTES = 1_500_000_000
CHUNK_DOCS = 20_000
PII_FRAC = 0.01
# Shards from one Common Crawl dump; each ~150-250MB compressed.
DEFAULT_SHARDS = [
    f"data/CC-MAIN-2013-20/000_{i:05d}.parquet" for i in range(6)
]


def synth_pii(rng: random.Random, i: int):
    kind = rng.choice(["email", "phone", "ssn"])
    if kind == "email":
        return f"synthetic.user.{i}@example.invalid"
    if kind == "phone":
        return f"555-01{rng.randint(10, 99):02d}"
    return f"900-{rng.randint(10, 99):02d}-{rng.randint(1000, 9999):04d}"


def download_shard(relpath: str, dest: str) -> None:
    url = f"https://huggingface.co/datasets/{REPO}/resolve/main/{relpath}"
    print(f"downloading {relpath} ...", flush=True)
    r = subprocess.run(["curl", "-sL", "--retry", "3", "-o", dest, url],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dest) or os.path.getsize(dest) == 0:
        raise RuntimeError(f"download failed for {relpath}: {r.stderr[-500:]}")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class ChunkedWriter:
    def __init__(self, chunk_dir: str, manifest: dict):
        self.chunk_dir = chunk_dir
        self.manifest = manifest
        self.idx = self.n_in_chunk = 0
        self.f = None
        self.path = ""
        self._new_chunk()

    def _new_chunk(self):
        if self.f:
            self.f.close()
            self.manifest[self.path] = {"docs": self.n_in_chunk}
        self.path = os.path.join(self.chunk_dir, f"chunk_{self.idx:05d}.jsonl.gz")
        self.f = gzip.open(self.path, "wt", encoding="utf-8")
        self.idx += 1
        self.n_in_chunk = 0

    def write(self, line: str):
        self.f.write(line)
        self.n_in_chunk += 1
        if self.n_in_chunk >= CHUNK_DOCS:
            self._new_chunk()

    def close(self):
        if self.f:
            self.f.close()
            self.manifest[self.path] = {"docs": self.n_in_chunk}
            self.f = None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--target-bytes", type=int, default=TARGET_BYTES)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--shards", nargs="*", default=DEFAULT_SHARDS)
    ap.add_argument("--local-parquet", nargs="*", default=[],
                    help="use already-downloaded local parquet files instead of downloading")
    args = ap.parse_args()

    import pyarrow.parquet as pq
    import pyarrow as pa

    root = args.data_root
    os.makedirs(root, exist_ok=True)
    manifest = {"seed": args.seed, "source_repo": REPO, "files": {}}
    rng = random.Random(args.seed)

    chunk_dir = os.path.join(root, "fmt_chunked_gzip", "chunks")
    os.makedirs(chunk_dir, exist_ok=True)
    whole_path = os.path.join(root, "fmt_whole_gzip", "sample.jsonl.gz")
    os.makedirs(os.path.dirname(whole_path), exist_ok=True)
    pq_path = os.path.join(root, "fmt_zstd_parquet", "sample.parquet")
    os.makedirs(os.path.dirname(pq_path), exist_ok=True)
    tmpdir = os.path.join(root, "_dl")
    os.makedirs(tmpdir, exist_ok=True)

    chunked = ChunkedWriter(chunk_dir, manifest["files"])
    whole_f = gzip.open(whole_path, "wt", encoding="utf-8")
    pq_writer = None

    n_docs = pii_n = raw_bytes = 0
    stop = False
    sources = []
    if args.local_parquet:
        sources = [("local", p) for p in args.local_parquet]
    else:
        sources = [("dl", s) for s in args.shards]
    for kind, s in sources:
        if stop:
            break
        if kind == "dl":
            local = os.path.join(tmpdir, os.path.basename(s))
            if not os.path.exists(local):
                download_shard(s, local)
        else:
            local = s
        pf = pq.ParquetFile(local)
        for batch in pf.iter_batches(columns=["id", "text"], batch_size=5000):
            ids = batch.column("id").to_pylist()
            texts = batch.column("text").to_pylist()
            pq_ids, pq_texts = [], []
            for i, t in zip(ids, texts):
                if not t or not t.strip():
                    continue
                doc_id = str(i) if i is not None else f"fw-{n_docs}"
                text = t.strip()
                if rng.random() < PII_FRAC:
                    text += " Contact " + synth_pii(rng, n_docs) + " for details."
                    pii_n += 1
                line = json.dumps({"id": doc_id, "text": text}, ensure_ascii=False) + "\n"
                raw_bytes += len(line.encode("utf-8"))
                whole_f.write(line)
                chunked.write(line)
                pq_ids.append(doc_id)
                pq_texts.append(text)
                n_docs += 1
                if raw_bytes >= args.target_bytes:
                    stop = True
                    break
            if pq_ids:
                table = pa.table({"id": pq_ids, "text": pq_texts})
                if pq_writer is None:
                    pq_writer = pq.ParquetWriter(pq_path, table.schema, compression="zstd")
                pq_writer.write_table(table)
            if stop:
                break
        # free shard disk space as we go (only for downloaded shards)
        if kind == "dl":
            os.remove(local)

    whole_f.close()
    chunked.close()
    if pq_writer:
        pq_writer.close()
    manifest["files"][whole_path] = {"docs": n_docs}
    manifest["files"][pq_path] = {"docs": n_docs}
    manifest["docs_total"] = n_docs
    manifest["synthetic_pii_docs"] = pii_n
    for p in manifest["files"]:
        manifest["files"][p]["bytes"] = os.path.getsize(p)
        manifest["files"][p]["sha256"] = sha256_file(p)
    with open(os.path.join(root, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    total = sum(v["bytes"] for v in manifest["files"].values())
    print(f"docs={n_docs} synthetic_pii={pii_n} files={len(manifest['files'])} "
          f"total={total/1e9:.2f} GB")


if __name__ == "__main__":
    main()
