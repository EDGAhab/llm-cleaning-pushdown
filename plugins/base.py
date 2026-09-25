"""Plugin interface for the llm-cleaning-pushdown benchmark toolkit.

A plugin adapts ONE storage/compute backend (e.g. MinIO+DuckDB, SeaweedFS,
Garage, or a vendor engine such as AirMettle). The toolkit core:

1. takes a DECLARATIVE pipeline spec (pipeline_specs/*.json),
2. asks each plugin which steps it can push down,
3. runs pushable steps on the storage side via the plugin,
4. falls back to the compute side for anything the plugin cannot do,
5. emits a pushdownability matrix and a cost comparison report.

Plugins receive declarative specs, never raw S3 request streams.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal

Capability = Literal["full", "partial", "none"]


@dataclass
class StepResult:
    """Result of executing (a shard of) pushed-down steps on the storage side."""
    output_refs: List[str]          # backend-local references to cleaned shards
    docs_in: int
    docs_out: int
    bytes_read: int                 # raw bytes read from storage media
    bytes_written: int              # cleaned bytes staged for compute pickup
    cpu_seconds: float              # CPU time consumed on the storage side
    wall_seconds: float
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PushdownPlugin(ABC):
    """Interface every storage backend plugin must implement."""

    name: str = "base"

    # -- capability declaration -------------------------------------------
    @abstractmethod
    def declare_capabilities(self) -> Dict[str, Capability]:
        """Map pipeline step type -> full | partial | none.

        Step types (see docs/pipeline_spec_schema.md):
          rule_filter, language_id, pii_redact, minhash_sign,
          lsh_dedup, exact_dedup
        "partial" means the plugin can do part of the step (e.g. apply the
        filter but not emit MinHash signatures); the toolkit then runs the
        remainder on the compute side and records it in the matrix.
        """

    # -- data access --------------------------------------------------------
    @abstractmethod
    def put_dataset(self, local_paths: List[str], dataset_id: str) -> List[str]:
        """Upload local files, return backend refs (e.g. s3://bucket/key)."""

    @abstractmethod
    def get_bytes(self, ref: str) -> bytes:
        """Fetch bytes for a ref. The toolkit counts bytes for egress stats."""

    # -- pushdown execution ---------------------------------------------------
    @abstractmethod
    def execute_pushdown(
        self,
        spec: Dict[str, Any],
        input_refs: List[str],
        cpu_quota: float | None = None,
    ) -> StepResult:
        """Run all spec steps this plugin claims (full/partial) on storage.

        cpu_quota: fraction of one CPU the executor may use (e.g. 0.10).
        Must be deterministic given spec["seed"].
        """

    # -- housekeeping ---------------------------------------------------------
    def pushdownability_matrix(self, spec: Dict[str, Any]) -> Dict[str, str]:
        caps = self.declare_capabilities()
        return {
            step["type"]: caps.get(step["type"], "none")
            for step in spec.get("steps", [])
        }
