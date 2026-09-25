"""25_repeat_ci.py: group runs by (tier, scheme, quota, bandwidth), verify
output-hash consistency per tier, and compute mean +/- 95% CI (t=4.303, n=3)
for time_to_ready_s. Also prints per-scheme values for manual inspection.

Usage:
  python3 scripts/25_repeat_ci.py --orig "experiments/pii_matrix/*.json" \
      --reps "experiments/pii_matrix_r2/*.json" \
      --extra "experiments/pii_redact_only/*.json" \
      --out experiments/repeat_ci_report.md
"""
import argparse
import glob
import json
import math
import os
import re

T95_N3 = 4.303  # t_{0.975, df=2}


def tier_of(path):
    m = re.match(r"(d\d+)_", os.path.basename(path))
    if m:
        return m.group(1)
    return "unknown"


def load(pattern):
    out = []
    for p in sorted(glob.glob(pattern)):
        try:
            with open(p) as f:
                r = json.load(f)
            out.append((p, r))
        except Exception as e:
            print(f"WARN: could not load {p}: {e}")
    return out


def key_of(r):
    return (r["scheme"], r.get("cpu_quota"), r["bandwidth_mbps"])


def mean(xs):
    return sum(xs) / len(xs)


def sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig", default="")
    ap.add_argument("--reps", default="")
    ap.add_argument("--extra", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    runs = load(args.orig) + load(args.reps) + load(args.extra)

    # per-tier hash check (R may legitimately differ: reported, not failed)
    lines = ["# Repeat / redact-only analysis", ""]
    lines.append("## Per-tier output-hash consistency")
    by_tier = {}
    for p, r in runs:
        by_tier.setdefault(tier_of(p), []).append((p, r))
    for tier in sorted(by_tier):
        hs = {}
        for p, r in by_tier[tier]:
            hs.setdefault(r["output_sha256"][:12], []).append(
                (r["scheme"], os.path.basename(p)))
        n_hash = len(hs)
        lines.append(f"- tier {tier}: {n_hash} distinct hash(es)")
        for h, who in sorted(hs.items()):
            lines.append(f"  - {h}: {who}")
    lines.append("")

    # stats table: group by (tier, scheme, quota, bw)
    lines.append("## time_to_ready_s: mean +/- 95% CI (t=4.303)")
    lines.append("| tier | scheme | quota | bw | n | mean s | 95% CI half-width | values |")
    lines.append("|---|---|---|---|---|---|---|---|")
    groups = {}
    for p, r in runs:
        groups.setdefault((tier_of(p),) + key_of(r), []).append(r)
    rows = []
    for (tier, scheme, quota, bw), rs in sorted(groups.items(),
                                               key=lambda x: (x[0][0], x[0][1],
                                                              str(x[0][2]))):
        vals = [r["time_to_ready_s"] for r in rs]
        n = len(vals)
        m = mean(vals)
        if n >= 3:
            ci = T95_N3 * sd(vals) / math.sqrt(n)
            ci_s = f"+/- {ci:.1f}"
        else:
            ci_s = f"n={n}, no CI"
        lines.append(f"| {tier} | {scheme} | {quota} | {bw:g} | {n} | "
                     f"{m:.1f} | {ci_s} | "
                     f"{', '.join(f'{v:.1f}' for v in vals)} |")
        rows.append({"tier": tier, "scheme": scheme, "quota": quota, "bw": bw,
                     "n": n, "mean": round(m, 2),
                     "ci_hw": round(T95_N3 * sd(vals) / math.sqrt(n), 2) if n >= 3 else None,
                     "values": vals})
    lines.append("")

    # C/A and R/A premium ratios per tier (per-repeat means)
    lines.append("## Compliance premium ratios (per-tier, n=3 means)")
    for tier in sorted({g[0] for g in groups}):
        g = {(s, str(q), bw): rs for (t, s, q, bw), rs in groups.items() if t == tier}
        def mval(scheme, quota="None", bw=100):
            rs = g.get((scheme, quota, bw))
            return mean([r["time_to_ready_s"] for r in rs]) if rs else None
        a = mval("A")
        if not a:
            continue
        parts = [f"- tier {tier}: A mean = {a:.1f}s"]
        for label, (s, q) in [("C(q10)", ("C", "0.1")), ("C(q25)", ("C", "0.25")),
                              ("C(q50)", ("C", "0.5")), ("R(q25)", ("R", "0.25")),
                              ("R(q10)", ("R", "0.1")), ("R(q50)", ("R", "0.5"))]:
            v = mval(*[s, q])
            if v:
                parts.append(f"{label} = {v:.1f}s (x{v/a:.2f} vs A)")
        e = mval("E", "None", 10000)
        if e:
            parts.append(f"E = {e:.1f}s (x{e/a:.2f} vs A)")
        lines.append(" ".join(parts))
    lines.append("")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    json_path = args.out.replace(".md", ".json")
    with open(json_path, "w") as f:
        json.dump(rows, f, indent=2)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
