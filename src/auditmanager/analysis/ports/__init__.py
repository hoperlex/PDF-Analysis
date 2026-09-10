"""Ports of the analysis boundary: artifact roles and the stage seam."""

from __future__ import annotations

from auditmanager.analysis.ports.artifacts import (
    ARTIFACT_VERSION,
    ROLE_BLOCK_INDEX,
    ROLE_DOCUMENT_GRAPH,
    ROLE_PAGE_CROPS,
    ROLE_PAGE_INVENTORY,
    ROLE_SOURCE_DOCUMENT,
    ROLE_TEXT_LAYER,
    blob_role_for,
    envelope,
    publish_artifact,
    read_artifact,
)
from auditmanager.analysis.ports.stage import StageContext, StageHandler, StageProduction

__all__ = [
    "ARTIFACT_VERSION",
    "ROLE_BLOCK_INDEX",
    "ROLE_DOCUMENT_GRAPH",
    "ROLE_PAGE_CROPS",
    "ROLE_PAGE_INVENTORY",
    "ROLE_SOURCE_DOCUMENT",
    "ROLE_TEXT_LAYER",
    "StageContext",
    "StageHandler",
    "StageProduction",
    "blob_role_for",
    "envelope",
    "publish_artifact",
    "read_artifact",
]
