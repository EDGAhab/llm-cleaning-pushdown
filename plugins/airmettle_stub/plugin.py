"""AirMettle plugin STUB: interface + integration guide only. NOT implemented.

Per project handoff: the paper does not depend on AirMettle's participation.
This stub exists so that an AirMettle engineer can implement the plugin in
1-2 weeks from this document alone. No AirMettle-internal material is used
anywhere in this project; the stub below is written purely against the public
PushdownPlugin interface (plugins/base.py) and public knowledge that
AirMettle's engine does in-storage parallel analytics over record-sharded data.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plugins.base import PushdownPlugin, StepResult  # noqa: E402


class AirMettlePlugin(PushdownPlugin):
    """STUB. Raises NotImplementedError until implemented by AirMettle."""

    name = "airmettle_stub"

    def declare_capabilities(self) -> Dict[str, str]:
        # Expected (to be confirmed by the implementer): full pushdown of all
        # local steps; global steps stay on compute.
        return {
            "rule_filter": "full",
            "language_id": "full",
            "pii_redact": "full",
            "minhash_sign": "full",
            "lsh_dedup": "none",
            "exact_dedup": "none",
        }

    def put_dataset(self, local_paths: List[str], dataset_id: str) -> List[str]:
        raise NotImplementedError("AirMettle plugin is a stub (see INTEGRATION.md)")

    def get_bytes(self, ref: str) -> bytes:
        raise NotImplementedError("AirMettle plugin is a stub (see INTEGRATION.md)")

    def execute_pushdown(self, spec: Dict[str, Any], input_refs: List[str],
                         cpu_quota: float | None = None) -> StepResult:
        raise NotImplementedError("AirMettle plugin is a stub (see INTEGRATION.md)")
