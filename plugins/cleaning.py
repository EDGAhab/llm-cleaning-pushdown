"""Shared, deterministic cleaning-step implementations.

All steps are pure functions of (text, params, seed) so every scheme (A/B/C/D/E)
produces byte-identical output for the same spec + input. Randomness is seeded
only via the spec seed; MinHash uses a fixed seed.
"""
from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from typing import Any, Dict, Tuple


class _TextExtractor(HTMLParser):
    """Collect visible text; drop script/style/head content."""

    SKIP = {"script", "style", "head", "noscript"}

    def __init__(self):
        super().__init__()
        self.parts: list = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth:
            s = data.strip()
            if s:
                self.parts.append(s)

    def text(self) -> str:
        return "\n".join(self.parts)


def html_extract(text: str, params: Dict[str, Any]) -> str:
    """WARC->text style boilerplate extraction (week-4 high-shrinkage probe).

    Models the HTML-extraction stage of web-scale cleaning pipelines
    (e.g. FineWeb's trafilatura step): input is raw HTML, output is the
    visible text. Pure function of (text, params).
    """
    ex = _TextExtractor()
    try:
        ex.feed(text)
    except Exception:
        return text
    out = ex.text()
    return out if out.strip() else text


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_US_RE = re.compile(r"(?<!\d)(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)")
SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")


def rule_filter(text: str, params: Dict[str, Any]) -> bool:
    """True = keep. Simplified public Gopher/FineWeb-style heuristic filters."""
    words = text.split()
    if len(words) < params.get("min_words", 50):
        return False
    n_chars = max(len(text), 1)
    for sym in params.get("symbols", []):
        if text.count(sym) / max(len(words), 1) > params.get("max_symbol_ratio", 0.1):
            return False
    upper = sum(1 for c in text if c.isupper())
    if upper / n_chars > params.get("max_uppercase_ratio", 0.2):
        return False
    return True


def language_id(text: str, params: Dict[str, Any]) -> Tuple[bool, str, float]:
    """(keep, lang, confidence). Uses langdetect; deterministic via fixed seed."""
    from langdetect import DetectorFactory, detect_langs
    DetectorFactory.seed = 0
    try:
        scored = detect_langs(text[:2000])
        top = scored[0]
        lang, conf = top.lang, top.prob
    except Exception:
        lang, conf = "unknown", 0.0
    keep = lang in params.get("keep", ["en"]) and conf >= params.get("min_confidence", 0.9)
    return keep, lang, conf


def pii_redact(text: str, params: Dict[str, Any]) -> Tuple[str, int]:
    """Regex redaction. Trial PII is SYNTHETIC (injected by 00_prepare_data.py)."""
    repl = params.get("replacement", "[REDACTED]")
    count = 0
    patterns = {
        "email": EMAIL_RE,
        "phone_us": PHONE_US_RE,
        "ssn_us": SSN_RE,
    }
    for name in params.get("patterns", []):
        rx = patterns[name]
        text, n = rx.subn(repl, text)
        count += n
    return text, count


def minhash_signature(text: str, params: Dict[str, Any]) -> str:
    """128-perm MinHash over k-shingles; hex digest string (carried, not compared)."""
    from datasketch import MinHash
    k = params.get("shingle_k", 5)
    m = MinHash(num_perm=params.get("num_perm", 128), seed=params.get("seed", 42))
    toks = text.split()
    if len(toks) < k:
        m.update(text.encode("utf-8"))
    else:
        for i in range(len(toks) - k + 1):
            m.update(" ".join(toks[i:i + k]).encode("utf-8"))
    return m.digest().tobytes().hex()


def apply_local_steps(doc: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any] | None:
    """Run html_extract (if present) -> rule_filter -> language_id -> pii_redact -> minhash_sign.
    Returns None if the doc is filtered out, else the cleaned doc dict."""
    steps = {s["type"]: s.get("params", {}) for s in spec["steps"]}
    text = doc["text"]
    if "html_extract" in steps:
        text = html_extract(text, steps["html_extract"])
    if "rule_filter" in steps and not rule_filter(text, steps["rule_filter"]):
        return None
    if "language_id" in steps:
        keep, lang, conf = language_id(text, steps["language_id"])
        if not keep:
            return None
    else:
        lang, conf = "en", 1.0
    if "pii_redact" in steps:
        text, n_red = pii_redact(text, steps["pii_redact"])
    else:
        n_red = 0
    sig = ""
    if "minhash_sign" in steps:
        sig = minhash_signature(text, steps["minhash_sign"])
    return {"id": doc["id"], "text": text, "lang": lang,
            "pii_redactions": n_red, "minhash": sig}


def exact_dedup_key(doc: Dict[str, Any]) -> str:
    return hashlib.sha256(doc["text"].encode("utf-8")).hexdigest()
