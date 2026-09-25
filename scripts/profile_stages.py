"""Per-stage CPU profiling of the fineweb_default local steps on d10 docs.

Mirrors plugins/cleaning.py::apply_local_steps ordering:
rule_filter -> language_id -> pii_redact -> minhash_sign.
Measures wall+CPU time per step on a fixed 2000-doc sample.
"""
import gzip, json, os, sys, time
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ, "plugins"))
from cleaning import rule_filter, language_id, pii_redact, minhash_signature

spec = json.load(open(os.path.join(PROJ, "pipeline_specs/fineweb_default.json")))
steps = {s["type"]: s.get("params", {}) for s in spec["steps"]}

docs = []
with gzip.open(os.path.join(PROJ, "data_pii/d10/fmt_chunked_gzip/chunks/chunk_00000.jsonl.gz"), "rt") as f:
    for line in f:
        docs.append(json.loads(line)["text"])
        if len(docs) >= 2000:
            break

t = {"rule_filter": 0.0, "language_id": 0.0, "pii_redact": 0.0, "minhash_sign": 0.0}
n_pass = {"rule_filter": 0, "language_id": 0, "minhash": 0}
alive = []

t0 = time.perf_counter()
for text in docs:
    if rule_filter(text, steps["rule_filter"]):
        n_pass["rule_filter"] += 1
        alive.append(text)
t["rule_filter"] = time.perf_counter() - t0

t0 = time.perf_counter()
alive2 = []
for text in alive:
    keep, lang, conf = language_id(text, steps["language_id"])
    if keep:
        n_pass["language_id"] += 1
        alive2.append(text)
t["language_id"] = time.perf_counter() - t0

t0 = time.perf_counter()
alive3 = []
n_red = 0
for text in alive2:
    text2, n = pii_redact(text, steps["pii_redact"])
    n_red += n
    alive3.append(text2)
t["pii_redact"] = time.perf_counter() - t0

t0 = time.perf_counter()
for text in alive3:
    minhash_signature(text, steps["minhash_sign"])
    n_pass["minhash"] += 1
t["minhash_sign"] = time.perf_counter() - t0

total = sum(t.values())
print(json.dumps({"n_docs": len(docs), "n_pass": n_pass, "n_redactions": n_red,
                  "sec_per_step": {k: round(v, 2) for k, v in t.items()},
                  "share": {k: round(v / total, 4) for k, v in t.items()},
                  "total_s": round(total, 2)}, indent=1))
