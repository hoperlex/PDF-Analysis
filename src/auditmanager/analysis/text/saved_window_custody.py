"""Select W56b TEXT bytes from a supplied run-scoped saved stage envelope.

``StageResultRow`` has no Run ID. The future calling service must attach the
Run ID of its authoritative query and fence the current Attempt before and
after reading the referenced Blob. Constructing this wrapper proves neither
database provenance nor current execution authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.engine.registry import default_registry
from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import ARTIFACT_MEDIA_TYPE
from auditmanager.analysis.ports.artifacts import (
    ROLE_PAGE_INVENTORY,
    ROLE_RECOGNISED_TEXT,
    ROLE_TEXT_LAYER,
)
from auditmanager.analysis.text.source_bytes import (
    CheckedTextWindowSource,
    SuppliedTextSourceRefused,
    check_supplied_text_window_bytes,
)
from auditmanager.shared.identity import IdentityError, RunId


_STAGE: Final[str] = "source_preparation"
_REQUIRED: Final[frozenset[str]] = frozenset({ROLE_PAGE_INVENTORY, ROLE_TEXT_LAYER})
_ALLOWED: Final[frozenset[str]] = _REQUIRED | {ROLE_RECOGNISED_TEXT}


class SavedTextCustodyRefused(ValueError):
    """The supplied stage and text bytes cannot form one W56b input."""


@dataclass(frozen=True, slots=True)
class RunScopedTextStage:
    """A caller's claim about one authoritative run-scoped StageResult read."""

    run_id: str
    stage_id: str
    stage_version: str
    status: str
    artifacts: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True, slots=True)
class CheckedRunTextWindowInput:
    run_id: str
    source: CheckedTextWindowSource


def select_run_text_layer_ref(
    *, run_id: str, stage: RunScopedTextStage
) -> ArtifactRef:
    """Return the sole saved TEXT ref from one supplied complete stage row."""
    try:
        RunId.parse(run_id)
    except IdentityError:
        raise SavedTextCustodyRefused("run_identity_invalid") from None
    try:
        expected_version = default_registry().stage(_STAGE).stage_version
    except Exception as exc:  # a missing registry is a refusal, not a guessed version
        raise SavedTextCustodyRefused("stage_registry_unavailable") from exc
    if (
        not isinstance(stage, RunScopedTextStage)
        or stage.run_id != run_id
        or stage.stage_id != _STAGE
        or stage.stage_version != expected_version
        or stage.status != "succeeded"
        or not isinstance(stage.artifacts, tuple)
    ):
        raise SavedTextCustodyRefused("saved_stage_identity_or_status_invalid")

    refs: dict[str, ArtifactRef] = {}
    blob_ids: set[str] = set()
    for raw in stage.artifacts:
        if not isinstance(raw, Mapping):
            raise SavedTextCustodyRefused("saved_artifact_reference_invalid")
        try:
            ref = ArtifactRef(**dict(raw))
        except (TypeError, ValueError):
            raise SavedTextCustodyRefused("saved_artifact_reference_invalid") from None
        if (
            ref.role not in _ALLOWED
            or ref.role in refs
            or ref.blob_id in blob_ids
            or type(ref.size_bytes) is not int
            or ref.size_bytes < 1
            or ref.media_type != ARTIFACT_MEDIA_TYPE
        ):
            raise SavedTextCustodyRefused("saved_artifact_reference_invalid")
        refs[ref.role] = ref
        blob_ids.add(ref.blob_id)
    if not _REQUIRED <= refs.keys():
        raise SavedTextCustodyRefused("saved_text_reference_missing")
    return refs[ROLE_TEXT_LAYER]


def check_run_text_window_input(
    *,
    run_id: str,
    version_uid: str,
    expected_page_count: int,
    stage: RunScopedTextStage,
    supplied_text_bytes: bytes,
    max_chunk_characters: int,
) -> CheckedRunTextWindowInput:
    """Bind supplied bytes to the exact stage ref and partition all pages."""
    text_ref = select_run_text_layer_ref(run_id=run_id, stage=stage)
    try:
        source = check_supplied_text_window_bytes(
            version_uid=version_uid,
            expected_page_count=expected_page_count,
            text_layer_ref=text_ref,
            supplied_bytes=supplied_text_bytes,
            max_chunk_characters=max_chunk_characters,
        )
    except SuppliedTextSourceRefused as exc:
        raise SavedTextCustodyRefused("supplied_text_source_invalid") from exc
    return CheckedRunTextWindowInput(run_id, source)
