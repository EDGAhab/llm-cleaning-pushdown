"""20_report.py: compare scheme runs, verify correctness, evaluate checkpoint-1
signals, and emit a one-page cost report.

Usage:
  python3 scripts/20_report.py --runs experiments/week3_ac/*.json \
      --out experiments/week3_ac/report.md --cost-out experiments/week3_ac/cost_onepager.md

Correctness gate: runs over the same (format, tier label) input must share the
same output_sha256. Any mismatch FAILS the report. Runs are grouped by tier
label (e.g. "pii-d01") because different tiers have different injected PII
and legitimately produce different hashes; comparing across tiers is a bug.

Checkpoint-1 signals (quantified, per project plan):
  S1 (H1 direction): C slower than A at cpu_quota=0.10  -> low quota hurts pushdown
  S2 (promise)     : bytes(C)/bytes(A) <= 0.5 AND time(C) <= 1.2*time(A)
  S3 (H3 direction): the time_to_ready winner (A vs C) differs across formats
  S4 (H4 direction): evaluated separately by scripts/31_interference.py
"Interesting" = any of S1/S2/S3 with >=20% effect size.
"""
import argparse
import glob
import json
import os


def load_runs(patterns):
    runs = []
    for pat in patterns:
        for p in glob.glob(pat):
            with open(p) as f:
                runs.append((p, json.load(f)))
    return runs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cost-out", required=True)
    args = ap.parse_args()

    runs = load_runs(args.runs)
    # Group by (format, tier label): tiers differ in injected PII, so their
    # output hashes legitimately differ. Correctness is per-tier.
    by_group = {}
    for path, r in runs:
        by_group.setdefault((r["format"], r.get("label", "")), []).append((path, r))

    lines = ["# Pushdown trial report", ""]
    ok = True
    # correctness gate
    for (fmt, label), rs in sorted(by_group.items()):
        hashes = {r["output_sha256"] for _, r in rs}
        status = "PASS" if len(hashes) == 1 else "FAIL"
        if len(hashes) != 1:
            ok = False
        lines.append(f"- correctness [{fmt}/{label}]: {status} "
                     f"({len(rs)} runs, {len(hashes)} distinct output hashes)")
    lines.append("")

    # comparison table
    lines.append("## Run summary")
    lines.append("| scheme | format | cpu_quota | bw Mbps | GB xfer | t_ready s | "
                 "filter_rate | cost_usd |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for _, r in sorted(runs, key=lambda x: (x[1]["format"], x[1]["scheme"],
                                            str(x[1].get("cpu_quota")))):
        lines.append(f"| {r['scheme']} | {r['format']} | {r.get('cpu_quota')} | "
                     f"{r['bandwidth_mbps']:g} | "
                     f"{r['bytes_storage_to_compute']/1e9:.3f} | "
                     f"{r['time_to_ready_s']:.1f} | {r['filter_rate']:.3f} | "
                     f"{r['cost_usd']:.4f} |")
    lines.append("")

    # checkpoint signals: compare every non-A scheme against the A baseline
    # at the SAME (format, tier) and bandwidth.
    lines.append("## Checkpoint signals (same-tier, same-bandwidth baselines)")
    interesting = []

    def same_tier_baseline(group, bw, rs):
        a_runs = [r for _, r in rs if r["scheme"] == "A"]
        if not a_runs:
            return None
        return min(a_runs, key=lambda r: abs(r["bandwidth_mbps"] - bw))

    for (fmt, label), rs in sorted(by_group.items()):
        for _, r in sorted(rs, key=lambda x: (x[1]["scheme"],
                                              str(x[1].get("cpu_quota")))):
            if r["scheme"] == "A":
                continue
            a = same_tier_baseline((fmt, label), r["bandwidth_mbps"], rs)
            if not a:
                lines.append(f"- [{fmt}/{label}] no scheme-A baseline for "
                             f"{r['scheme']}@{r['bandwidth_mbps']:g}Mbps; skipped")
                continue
            t_ratio = r["time_to_ready_s"] / max(a["time_to_ready_s"], 1e-9)
            b_ratio = r["bytes_storage_to_compute"] / max(a["bytes_storage_to_compute"], 1)
            s1 = r["scheme"] == "C" and t_ratio >= 1.2
            s2 = b_ratio <= 0.5 and t_ratio <= 1.2
            tag = []
            if s1:
                tag.append("S1(low-quota-hurts)")
            if s2:
                tag.append("S2(promise)")
            if s1 or s2:
                interesting.append((fmt, label, r["scheme"], r.get("cpu_quota"),
                                    t_ratio, b_ratio))
            lines.append(f"- [{fmt}/{label}@{r['bandwidth_mbps']:g}Mbps] "
                         f"{r['scheme']}(quota={r.get('cpu_quota')}) vs A: "
                         f"time x{t_ratio:.2f}, bytes x{b_ratio:.2f} "
                         f"{' '.join(tag)}")
    # S3: winner differs across groups (A vs best-C per group)
    winners = {}
    for (fmt, label), rs in sorted(by_group.items()):
        d = {(r["scheme"], str(r.get("cpu_quota"))): r for _, r in rs}
        a = d.get(("A", "None"))
        c_best = min([r for (s, _), r in d.items() if s == "C"],
                     key=lambda r: r["time_to_ready_s"], default=None)
        if a and c_best:
            winners[(fmt, label)] = "C" if c_best["time_to_ready_s"] < a["time_to_ready_s"] else "A"
    if len(set(winners.values())) > 1:
        interesting.append(("cross-group", "", "", 0, 0, 0))
        lines.append(f"- S3(winner-differs): {winners}")
    else:
        lines.append(f"- S3: winner consistent across groups: {winners} (no signal)")
    lines.append("")
    # Checkpoint-2 verdict (handoff s8): does C beat E in ANY config?
    lines.append("## Checkpoint-2: C vs E")
    c_beats_e = []
    for (fmt, label), rs in sorted(by_group.items()):
        e_runs = [r for _, r in rs if r["scheme"] == "E"]
        c_runs = [r for _, r in rs if r["scheme"] == "C"]
        for er in e_runs:
            bw = er["bandwidth_mbps"]
            cs = [c for c in c_runs if c["bandwidth_mbps"] == bw]
            if not cs:
                continue
            best_c = min(cs, key=lambda c: c["time_to_ready_s"])
            beats_time = best_c["time_to_ready_s"] < er["time_to_ready_s"]
            beats_cost = best_c["cost_usd"] < er["cost_usd"]
            lines.append(f"- [{fmt}/{label}@{bw:g}Mbps] best C "
                         f"(q={best_c.get('cpu_quota')}, {best_c['time_to_ready_s']:.1f}s, "
                         f"${best_c['cost_usd']:.4f}) vs E "
                         f"({er['time_to_ready_s']:.1f}s, ${er['cost_usd']:.4f}): "
                         f"time {'C WINS' if beats_time else 'E wins'}, "
                         f"cost {'C WINS' if beats_cost else 'E wins'}")
            if beats_time or beats_cost:
                c_beats_e.append((fmt, label, bw))
    if c_beats_e:
        lines.append(f"- C beats E in {len(c_beats_e)} config(s): {c_beats_e}")
    else:
        lines.append("- C loses to E in every tested config on both time and cost")
    lines.append("")
    lines.append(f"**Checkpoint verdict: {'INTERESTING' if interesting else 'NO SIGNAL'}** "
                 f"({len(interesting)} signal(s))")
    if not interesting:
        lines.append("Per handoff: do NOT force a positive story. Report honestly and "
                     "discuss a pivot (PII-compliance framing / pushdown boundaries).")
    lines.append("")
    lines.append(f"Overall correctness gate: {'PASS' if ok else 'FAIL'}")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write("\n".join(lines) + "\n")

    # one-page cost report
    cl = ["# One-page cost report (placeholder pricing 2026-09-24)", ""]
    cl.append("Pricing constants: see costs/pricing.yaml (placeholders; real cloud "
              "pricing collected week 8).")
    cl.append("")
    cl.append("| config | $/run | GB egress | CPU-h |")
    cl.append("|---|---|---|---|")
    for _, r in sorted(runs, key=lambda x: x[1]["cost_usd"]):
        cpu_h = (r["storage_cpu_s"] + r["compute_cpu_s"]) / 3600
        cl.append(f"| {r['scheme']}/{r['format']}/q={r.get('cpu_quota')}/"
                  f"{r['bandwidth_mbps']:g}Mbps | ${r['cost_usd']:.4f} | "
                  f"{r['bytes_storage_to_compute']/1e9:.3f} | {cpu_h:.3f} |")
    with open(args.cost_out, "w") as f:
        f.write("\n".join(cl) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
