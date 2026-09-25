#!/usr/bin/env python3
"""02_warc_probe.py: build a synthetic high-shrinkage WARC-like variant.

Takes --n-chunks chunks from data/fmt_chunked_gzip/chunks and wraps each
document's text in deterministic HTML boilerplate (header/nav/article/footer/
script/style), producing data/fmt_warc_html/chunks/chunk_NNNN.jsonl.gz.

Purpose (week 4, checkpoint 2): checkpoint 1 found that pushdown has ~zero
byte dividend on the FineWeb local pipeline (filter rate 1.1%, bytes ratio
0.996) because the pipeline is compute-bound with low shrinkage. This probe
tests the "pushdown boundary": with a realistic WARC->text extraction stage
(first stage of every web-scale cleaning pipeline, e.g. FineWeb's trafilatura
step), does pushdown gain a byte/time advantage?

NOT a rigged rule: the extraction step is a standard, public pipeline stage;
the wrapper is synthetic but its shrinkage ratio is measured and reported.
The same declarative spec (pipeline_specs/fineweb_warc.json) runs under both
schemes, and the correctness gate (identical output hashes) still applies.

Usage:
  python3 scripts/02_warc_probe.py --n-chunks 1
"""
import argparse
import gzip
import hashlib
import json
import os

NAV_LINKS = "".join(
    f'<li><a href="/section{i}">Section {i} headline archive</a></li>'
    for i in range(1, 13))
STYLE = ("body{font-family:Georgia,serif;max-width:72ch;margin:0 auto}"
         ".ad-slot{border:1px solid #ccc;padding:8px;margin:12px 0}"
         "nav ul{list-style:none;display:flex;gap:12px}"
         "footer{margin-top:40px;border-top:2px solid #333}")
SCRIPT = ("window.__CFG={sid:\"%SID%\",v:3,ab:[\"a\",\"b\"]};"
          "(function(){var q=document.querySelectorAll('.ad-slot');"
          "for(var i=0;i<q.length;i++){q[i].dataset.loaded=1;}})();")


def wrap_html(doc_id: str, text: str) -> str:
    """Deterministic HTML page around the doc text."""
    sents = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
    paras = []
    for i in range(0, len(sents), 3):
        chunk = ". ".join(sents[i:i + 3])
        if not chunk.endswith("."):
            chunk += "."
        paras.append(f"<p>{chunk}</p>")
    body = "\n".join(paras) if paras else f"<p>{text}</p>"
    title = f"Article {doc_id} - Example News Portal"
    script = SCRIPT.replace("%SID%", doc_id)
    return (
        "<!DOCTYPE html><html lang=\"en\"><head>"
        f"<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">"
        f"<title>{title}</title>"
        f"<meta name=\"description\" content=\"Archived article {doc_id} for research.\">"
        f"<style>{STYLE}</style><script>{script}</script>"
        "</head><body>"
        "<header><div class=\"masthead\"><h1>Example News Portal</h1>"
        f"<nav><ul>{NAV_LINKS}</ul></nav></div></header>"
        "<main><article>"
        f"<h2>{title}</h2>"
        "<div class=\"ad-slot\">Advertisement placeholder</div>"
        f"{body}"
        "<div class=\"ad-slot\">Advertisement placeholder</div>"
        "</article></main>"
        "<aside><h3>Related stories</h3><ul>"
        + "".join(f"<li><a href=\"/r{i}\">Related story {i}</a></li>" for i in range(1, 9))
        + "</ul></aside>"
        "<footer><p>&copy; 2026 Example News Portal. All rights reserved.</p>"
        "<p><a href=\"/privacy\">Privacy</a> | <a href=\"/terms\">Terms</a> | "
        "<a href=\"/contact\">Contact</a></p></footer>"
        "</body></html>"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-chunks", type=int, default=1)
    ap.add_argument("--data-root", default="data")
    args = ap.parse_args()

    src_d = os.path.join(args.data_root, "fmt_chunked_gzip", "chunks")
    out_d = os.path.join(args.data_root, "fmt_warc_html", "chunks")
    os.makedirs(out_d, exist_ok=True)
    srcs = sorted(f for f in os.listdir(src_d) if f.endswith(".gz"))[:args.n_chunks]

    manifest = {"variant": "warc_html", "chunks": [], "note":
                "Synthetic HTML wrapper around FineWeb sample text; "
                "shrinkage measured below. Deterministic (no RNG)."}
    for src in srcs:
        n_in = n_out = 0
        bytes_in = bytes_out = 0
        h = hashlib.sha256()
        out_path = os.path.join(out_d, src)
        with gzip.open(os.path.join(src_d, src), "rt", encoding="utf-8") as fin, \
                gzip.open(out_path, "wt", encoding="utf-8") as fout:
            for line in fin:
                if not line.strip():
                    continue
                doc = json.loads(line)
                n_in += 1
                html = wrap_html(str(doc["id"]), doc["text"])
                rec = json.dumps({"id": doc["id"], "text": html},
                                 ensure_ascii=False)
                bytes_in += len(line.encode("utf-8"))
                bytes_out += len(rec.encode("utf-8"))
                fout.write(rec + "\n")
                n_out += 1
                h.update(rec.encode("utf-8"))
        manifest["chunks"].append({
            "file": src, "docs": n_out,
            "raw_jsonl_bytes": bytes_in, "html_jsonl_bytes": bytes_out,
            "shrinkage_x": round(bytes_out / max(bytes_in, 1), 3),
            "sha256": h.hexdigest(),
        })
        print(f"{src}: {n_out} docs, html/raw = "
              f"{bytes_out / max(bytes_in, 1):.2f}x")
    with open(os.path.join(args.data_root, "fmt_warc_html", "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print("wrote", os.path.join(args.data_root, "fmt_warc_html", "manifest.json"))


if __name__ == "__main__":
    main()
