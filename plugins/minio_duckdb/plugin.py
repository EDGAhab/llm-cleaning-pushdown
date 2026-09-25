"""Reference plugin: local sharded storage + in-process pushdown executor.

Week-3 role: stands in for "MinIO+DuckDB on storage nodes" on a single machine.
- Storage = N shard directories (default 4) acting as storage nodes.
- Pushdown executor = worker subprocesses, optionally CPU-throttled
  (cpulimit -> systemd-run -> unenforced, recorded in notes).
- Byte counting: every get_bytes() is metered; the trial converts bytes to
  transfer time with an explicit bandwidth model (see costs/pricing.yaml).

A moto-backed S3 variant (same interface, real S3 API) can be added later;
the plugin interface is unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plugins.base import PushdownPlugin, StepResult  # noqa: E402
from plugins.cleaning import apply_local_steps  # noqa: E402

LOCAL_STEPS = ("html_extract", "rule_filter", "language_id", "pii_redact", "minhash_sign")


class LocalShardedPlugin(PushdownPlugin):
    name = "local_sharded"

    def __init__(self, root: str, shards: int = 4):
        self.root = root
        self.shards = shards
        self.bytes_served = 0  # metered egress from "storage" to "compute"

    # -- capabilities ------------------------------------------------------
    def declare_capabilities(self):
        return {
            "html_extract": "full",
            "rule_filter": "full",
            "language_id": "full",
            "pii_redact": "full",
            "minhash_sign": "full",
            "lsh_dedup": "none",      # global step: stays on compute
            "exact_dedup": "none",    # global step: stays on compute
        }

    # -- data access --------------------------------------------------------
    def _shard_dir(self, i: int) -> str:
        return os.path.join(self.root, f"node{i}")

    def put_dataset(self, local_paths: List[str], dataset_id: str) -> List[str]:
        refs = []
        for i, p in enumerate(local_paths):
            node = i % self.shards
            d = os.path.join(self._shard_dir(node), dataset_id)
            os.makedirs(d, exist_ok=True)
            dst = os.path.join(d, os.path.basename(p))
            shutil.copyfile(p, dst)
            refs.append(dst)
        return refs

    def get_bytes(self, ref: str) -> bytes:
        with open(ref, "rb") as f:
            data = f.read()
        self.bytes_served += len(data)
        return data

    # -- pushdown execution ---------------------------------------------------
    def execute_pushdown(self, spec: Dict[str, Any], input_refs: List[str],
                         cpu_quota: float | None = None) -> StepResult:
        t0 = time.time()
        docs_in = docs_out = b_read = b_written = 0
        cpu_s = 0.0
        out_refs: List[str] = []
        enforced = cpu_quota is not None
        notes: Dict[str, Any] = {}

        # Group refs by node so each worker reads its node locally (no "network").
        by_node: Dict[str, List[str]] = {}
        for r in input_refs:
            node = os.path.dirname(os.path.dirname(r))
            by_node.setdefault(node, []).append(r)

        def run_node(args):
            node_dir, refs, out_dir = args
            worker = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "_worker.py")
            wnotes: Dict[str, Any] = {}
            cmd = [sys.executable, worker, json.dumps(spec), out_dir] + refs
            cmd = self._apply_cpu_quota(cmd, cpu_quota, wnotes)
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return proc, wnotes.get("throttle", "none")

        tasks = []
        for node_dir, refs in sorted(by_node.items()):
            out_dir = os.path.join(node_dir, "pushdown_out")
            os.makedirs(out_dir, exist_ok=True)
            tasks.append((node_dir, refs, out_dir))

        t_par0 = time.time()
        with ThreadPoolExecutor(max_workers=min(4, len(tasks))) as ex:
            results = list(ex.map(run_node, tasks))
        notes["parallel_workers"] = len(tasks)
        notes["parallel_wall_s"] = round(time.time() - t_par0, 2)
        notes["throttle"] = results[0][1] if results else "none"

        for proc, _ in results:
            if proc.returncode != 0:
                raise RuntimeError(f"pushdown worker failed: {proc.stderr[-2000:]}")
            # cpulimit/systemd-run may print to stdout; take last JSON-looking line
            json_lines = [ln for ln in proc.stdout.strip().splitlines()
                          if ln.lstrip().startswith("{")]
            if not json_lines:
                raise RuntimeError(f"pushdown worker produced no JSON: {proc.stdout[-500:]}"
                                   f" / {proc.stderr[-1500:]}")
            stat = json.loads(json_lines[-1])
            docs_in += stat["docs_in"]
            docs_out += stat["docs_out"]
            b_read += stat["bytes_read"]
            b_written += stat["bytes_written"]
            cpu_s += stat["cpu_seconds"]
            out_refs.extend(stat["out_refs"])
            notes["pii_redactions"] = notes.get("pii_redactions", 0) + stat.get("pii_redactions", 0)
            notes["sig_bytes"] = notes.get("sig_bytes", 0) + stat.get("sig_bytes", 0)
            notes["sig_refs"] = notes.get("sig_refs", []) + stat.get("sig_refs", [])

        notes["cpu_quota_requested"] = cpu_quota
        notes["cpu_quota_enforced"] = enforced and notes.get("throttle") != "none"
        return StepResult(
            output_refs=out_refs, docs_in=docs_in, docs_out=docs_out,
            bytes_read=b_read, bytes_written=b_written,
            cpu_seconds=cpu_s, wall_seconds=time.time() - t0, notes=notes)

    # -- helpers --------------------------------------------------------------
    @staticmethod
    def _apply_cpu_quota(cmd: List[str], quota: float | None,
                         notes: Dict[str, Any]) -> List[str]:
        if quota is None:
            notes["throttle"] = "none"
            return cmd
        pct = max(int(quota * 100), 1)
        if shutil.which("cpulimit"):
            notes["throttle"] = f"cpulimit-{pct}%"
            return ["cpulimit", "-l", str(pct), "--"] + cmd
        # Fallback: our own SIGSTOP/SIGCONT throttler (cpulimit was wiped by
        # service restarts; systemd-run needs D-Bus which is unavailable).
        throttle_py = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), "scripts", "throttle.py")
        if os.path.exists(throttle_py):
            notes["throttle"] = f"throttle.py-{pct}%"
            return [sys.executable, throttle_py, str(pct), "--"] + cmd
        if shutil.which("systemd-run"):
            notes["throttle"] = f"systemd-run-CPUQuota={pct}%"
            return ["systemd-run", "--user", "--scope", "-p",
                    f"CPUQuota={pct}%", "--"] + cmd
        notes["throttle"] = "none"
        return cmd


def run_local_steps_on_bytes(data: bytes, spec: Dict[str, Any]):
    """Shared by the worker: bytes (one .jsonl.gz chunk) -> cleaned docs."""
    import gzip
    import resource
    t0 = time.time()
    docs_in = 0
    cleaned = []
    with gzip.open(__import__("io").BytesIO(data), "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            docs_in += 1
            doc = json.loads(line)
            out = apply_local_steps(doc, spec)
            if out is not None:
                cleaned.append(out)
    cpu_s = resource.getrusage(resource.RUSAGE_SELF).ru_utime + \
        resource.getrusage(resource.RUSAGE_SELF).ru_stime
    return cleaned, docs_in, t0, cpu_s
