"""The public surface of the analysis boundary.

Everything another package needs is here; everything else is an implementation
detail. ``P2-RUN-01`` calls :func:`run_stage` and persists the returned results
without reaching inside a stage; ``P2-AI-01`` registers ``text_analysis`` on the same
seam; ``P2-FND-01`` resolves evidence anchors against the text layer and block index
only, and :func:`document_text` is the one implementation of what "the document-global
character sequence" means.

There is no ``JobPackage`` and no ``ResultPackage`` on this surface. Those envelopes
carry attempt authority because they cross a remote-dispatch boundary; ``PC-01`` runs
stages in process, and this seam requires no attempt authority at all.
"""

from __future__ import annotations

from auditmanager.analysis.engine.registry import (
    StageDefinition,
    StageRegistry,
    default_registry,
)
from auditmanager.analysis.engine.result import (
    CONTRACT_VERSION,
    ArtifactRef,
    StageError,
    StageResult,
    StageStatus,
)
from auditmanager.analysis.engine.runner import run_stage
from auditmanager.analysis.ports.artifacts import (
    ARTIFACT_VERSION,
    ROLE_BLOCK_INDEX,
    ROLE_DOCUMENT_GRAPH,
    ROLE_PAGE_CROPS,
    ROLE_PAGE_INVENTORY,
    ROLE_SOURCE_DOCUMENT,
    ROLE_TEXT_LAYER,
    read_artifact,
)
from auditmanager.analysis.ports.stage import StageContext, StageHandler, StageProduction
from auditmanager.analysis.stages.extraction import (
    NORMALIZATION_DESCRIPTION,
    NORMALIZATION_ID,
)
from auditmanager.analysis.stages.source_preparation import document_text

__all__ = [
    "ARTIFACT_VERSION",
    "CONTRACT_VERSION",
    "NORMALIZATION_DESCRIPTION",
    "NORMALIZATION_ID",
    "ROLE_BLOCK_INDEX",
    "ROLE_DOCUMENT_GRAPH",
    "ROLE_PAGE_CROPS",
    "ROLE_PAGE_INVENTORY",
    "ROLE_SOURCE_DOCUMENT",
    "ROLE_TEXT_LAYER",
    "ArtifactRef",
    "StageContext",
    "StageDefinition",
    "StageError",
    "StageHandler",
    "StageProduction",
    "StageRegistry",
    "StageResult",
    "StageStatus",
    "default_registry",
    "document_text",
    "read_artifact",
    "run_stage",
]
