"""The stage implementations, bound to canonical registry identity.

The mapping is keyed by canonical ``stage_id`` and by nothing else. There is no legacy
alias here and there must never be one: the registry's ``alias_resolution`` rule puts
name resolution at the control plane's boundary and says the engine never accepts a
legacy name.

``handler_for`` refuses an unimplemented stage rather than returning a no-op. A stage
the registry declares but this package does not implement - ``text_analysis`` and the
five after it, which belong to other tasks - must be a refusal, because a no-op would
report ``succeeded`` with no artifact and turn a missing implementation into a silent
empty result.
"""

from __future__ import annotations

from typing import Final, Mapping

from auditmanager.analysis.ports.stage import StageHandler
from auditmanager.analysis.stages import (
    document_context_build,
    page_geometry_extraction,
    source_preparation,
)
from auditmanager.shared.errors import DomainError, ErrorCode

#: Canonical ``stage_id`` to implementation. The three deterministic preparation
#: stages of ``P2-ENG-01``, and only those.
HANDLERS: Final[Mapping[str, StageHandler]] = {
    source_preparation.STAGE_ID: source_preparation.run,
    page_geometry_extraction.STAGE_ID: page_geometry_extraction.run,
    document_context_build.STAGE_ID: document_context_build.run,
}


def handler_for(stage_id: str) -> StageHandler:
    """The implementation registered for ``stage_id``, or a typed refusal."""
    handler = HANDLERS.get(stage_id)
    if handler is None:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the stage is declared by the registry but not implemented by this "
                "engine; it refuses rather than reporting an empty success"
            ),
            stage_id=stage_id,
            reason="stage_not_implemented",
        )
    return handler


__all__ = [
    "HANDLERS",
    "document_context_build",
    "handler_for",
    "page_geometry_extraction",
    "source_preparation",
]
