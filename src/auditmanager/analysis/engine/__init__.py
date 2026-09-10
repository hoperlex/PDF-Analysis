"""The stage engine: registry, result value and in-process runner."""

from __future__ import annotations

from auditmanager.analysis.engine.registry import (
    CONTRACT_PATH,
    StageDefinition,
    StageRegistry,
    default_registry,
)
from auditmanager.analysis.engine.result import (
    CONTRACT_VERSION,
    ArtifactRef,
    MetricValue,
    StageError,
    StageResult,
    StageStatus,
)
from auditmanager.analysis.engine.runner import assert_status_allowed, run_stage
from auditmanager.analysis.engine.serialization import (
    ARTIFACT_MEDIA_TYPE,
    canonical_bytes,
    sha256_hex,
)

__all__ = [
    "ARTIFACT_MEDIA_TYPE",
    "CONTRACT_PATH",
    "CONTRACT_VERSION",
    "ArtifactRef",
    "MetricValue",
    "StageDefinition",
    "StageError",
    "StageRegistry",
    "StageResult",
    "StageStatus",
    "assert_status_allowed",
    "canonical_bytes",
    "default_registry",
    "run_stage",
    "sha256_hex",
]
