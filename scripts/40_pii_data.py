#!/usr/bin/env python3
"""40_pii_data.py: build the PII-compliance-scenario dataset.

Checkpoint-2 honest note #3 (carried from checkpoint 1): `pii_redactions`
counts in week-3/week-4 runs were contaminated by natural PII-like matches
in the raw FineWeb text (emails, phone numbers, SSN-shaped strings that
real web text contains). This script fixes that for the new PII phase:

  1. PRE-CLEAR: scan every base doc with the EXACT regexes used by the
     pipeline (imported from plugins.cleaning, not copied) and replace
     natural matches with [PRECLEARED]. Counts are recorded per tier.
  2. CONTROLLED INJECTION: inject synthetic PII (same clearly-fake
     patterns as 00_prepare_data.py: synthetic.user.N@example.invalid,
     555-01XX phones, 900-XX-XXXX SSNs) at tier-controlled densities.
     Injection happens AFTER pre-clear, so the two never interact.
  3. VERIFY: read every tier file back, run the real pii_redact step on
     each doc, and assert the total redaction count EXACTLY equals the
     injected synthetic count. Any mismatch aborts loudly.

Design for the density variable: all tiers share the SAME 20k base docs
(first non-empty docs from the cached shard, fixed order), so tiers
differ only in injected PII density, isolating the density effect.

Tiers (frac of docs receiving PII, max PII instances per doc):
  d01 : 1%  x1   (matches the old 00_prepare_data.py injection rate)
  d10 : 10% x1
  d30 : 30% x1-3 (also varies per-doc intensity)

Output: <out-root>/<tier>/fmt_chunked_gzip/chunks/chunk_00000.jsonl.gz
        (one 20k-doc chunk per tier, runnable via 10_run_scheme.py with
        --data-root <out-root>/<tier> --format chunked_gzip --limit-refs 1)
        plus <out-root>/manifest.json with exact counts and sha256.

No real PII anywhere: pre-clear only rewrites text, and the replacement
token [PRECLEARED] matches none of the PII regexes.
"""
import argparse
import gzip
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from plugins.cleaning import EMAIL_RE, PHONE_US_RE, SSN_RE, pii_redact  # noqa: E402

PII_RES = [("email", EMAIL_RE), ("phone_us", PHONE_US_RE), ("ssn_us", SSN_RE)]
PRECLEAR_TOKEN = "[PRECLEARED]"
SPEC_PII_PARAMS = {"patterns": ["email", "phone_us", "ssn_us"],
                   "replacement": "[REDACTED]"}


def synth_pii(rng: random.Random, i: int) -> str:
    kind = rng.choice(["email", "phone", "ssn"])
    if kind == "email":
        return f"synthetic.user.{i}@example.invalid"
    if kind == "phone":
        # NOTE: 00_prepare_data.py used "555-01XX" (7 digits), which the
        # pipeline's PHONE_US_RE (10-digit NANP) never matches -- those
        # synthetic phones were silently invisible to pii_redact in the
        # week-3/week-4 runs. Fixed here to a 10-digit form in the
        # reserved-fictional 555-01XX block so every injected instance
        # is verifiably catchable.
        return f"(415) 555-01{rng.randint(10, 99):02d}"
    return f"900-{rng.randint(10, 99):02d}-{rng.randint(1000, 9999):04d}"


def preclear(text: str) -> tuple[str, int]:
    """Replace natural PII-like matches with PRECLEAR_TOKEN. Returns (text, n)."""
    n = 0
    for _name, rx in PII_RES:
        text, k = rx.subn(PRECLEAR_TOKEN, text)
        n += k
    return text, n


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_base_docs(shard: str, n_docs: int):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(shard)
    docs = []
    for batch in pf.iter_batches(columns=["id", "text"], batch_size=5000):
        for i, t in zip(batch.column("id").to_pylist(),
                        batch.column("text").to_pylist()):
            if not t or not t.strip():
                continue
            docs.append({"id": str(i) if i is not None else f"fw-{len(docs)}",
                         "text": t.strip()})
            if len(docs) >= n_docs:
                return docs
    return docs


def build_tier(base_docs, tier_name: str, frac: float, max_per_doc: int,
               seed: int, out_path: str) -> dict:
    rng = random.Random(seed)
    injected = 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        for j, doc in enumerate(base_docs):
            text = doc["text"]
            if rng.random() < frac:
                k = rng.randint(1, max_per_doc)
                for _ in range(k):
                    text += " Contact " + synth_pii(rng, j) + " for details."
                    injected += 1
            f.write(json.dumps({"id": doc["id"], "text": text},
                               ensure_ascii=False) + "\n")
    return {"tier": tier_name, "frac": frac, "max_per_doc": max_per_doc,
            "docs": len(base_docs), "synthetic_injected": injected,
            "bytes": os.path.getsize(out_path),
            "sha256": sha256_file(out_path)}


def verify_tier(out_path: str, expected: int) -> None:
    """Assert pii_redact on the tier file catches EXACTLY the injected PII."""
    total, docs = 0, 0
    leftover = 0
    with gzip.open(out_path, "rt", encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            redacted, n = pii_redact(doc["text"], SPEC_PII_PARAMS)
            total += n
            docs += 1
            for _name, rx in PII_RES:  # nothing PII-shaped may survive
                if rx.search(redacted):
                    leftover += 1
                    break
    assert total == expected, (
        f"VERIFICATION FAILED for {out_path}: pii_redact caught {total}, "
        f"but {expected} synthetic instances were injected "
        f"(diff={total - expected}). Pre-clear is incomplete or the "
        f"injection template leaks.")
    assert leftover == 0, (
        f"VERIFICATION FAILED for {out_path}: {leftover} docs still "
        f"contain PII-shaped strings after redaction.")
    print(f"  verify OK: {docs} docs, redactions={total} == injected={expected}, "
          f"no PII-shaped leftovers", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default="data/_dl/fw_shard.parquet")
    ap.add_argument("--out-root", default="data_pii")
    ap.add_argument("--n-docs", type=int, default=20_000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    tiers = [("d01", 0.01, 1), ("d10", 0.10, 1), ("d30", 0.30, 3)]
    os.makedirs(args.out_root, exist_ok=True)

    print(f"reading {args.n_docs} base docs from {args.shard} ...", flush=True)
    raw_docs = read_base_docs(args.shard, args.n_docs)
    print(f"  got {len(raw_docs)} docs; pre-clearing natural PII matches ...",
          flush=True)
    base_docs, precleared = [], 0
    for d in raw_docs:
        text, n = preclear(d["text"])
        precleared += n
        base_docs.append({"id": d["id"], "text": text})
    print(f"  pre-cleared {precleared} natural PII-like matches", flush=True)

    manifest = {"seed": args.seed, "n_docs": len(base_docs),
                "precleared_natural_total": precleared,
                "method": ("pre-clear with pipeline-exact regexes, then "
                           "tier-controlled synthetic injection; all tiers "
                           "share identical base docs"),
                "tiers": {}}
    for ti, (name, frac, mpd) in enumerate(tiers):
        chunk_dir = os.path.join(args.out_root, name,
                                 "fmt_chunked_gzip", "chunks")
        out_path = os.path.join(chunk_dir, "chunk_00000.jsonl.gz")
        if os.path.exists(out_path):
            print(f"tier {name}: exists, re-verifying ...", flush=True)
        else:
            print(f"tier {name}: building (frac={frac}, max/doc={mpd}) ...",
                  flush=True)
        info = build_tier(base_docs, name, frac, mpd,
                          args.seed + 1000 * (ti + 1), out_path)
        info["precleared_natural"] = precleared  # same base docs every tier
        print(f"  wrote {out_path}: injected={info['synthetic_injected']}",
              flush=True)
        verify_tier(out_path, info["synthetic_injected"])
        manifest["tiers"][name] = info

    mp = os.path.join(args.out_root, "manifest.json")
    with open(mp, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"manifest -> {mp}")
    print("DONE. All tiers verified: redaction counts are pure synthetic.")


if __name__ == "__main__":
    main()
