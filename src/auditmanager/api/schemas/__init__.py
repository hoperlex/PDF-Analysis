"""Wire shapes for ``contracts/api/v1/openapi.json``.

Two layers, and the split is the point.

**:mod:`~auditmanager.api.schemas.models`** holds the 43 Pydantic models named exactly as
the contract's ``components.schemas`` keys. They declare the **document** FastAPI serves and
they validate the four request bodies. `T-1` makes the generated document a second authority
and `W13-CONF`'s conformance gate is the machine that stops it drifting from the frozen one.

**The ``*View`` dataclasses and the ``*_body`` functions** in the modules beside it are the
**seam and the bytes**. A handler never receives a domain record; it receives one of these
views, built by whatever the composition root wired behind the ports in
:mod:`auditmanager.api.routers.ports`, and renders it with a ``*_body`` function. Those
functions produce the exact dictionaries the response baseline's 33 records contain, and
nothing in this package reaches a database, a service, an environment variable or a clock:
given a view they produce the same body every time.

**Why the bodies are not rendered by the Pydantic models.** A handler returns a
``WireResponse``, which FastAPI passes through untouched, so ``response_model`` describes the
response without serializing it. That is deliberate: ``model_dump_json`` would emit compact
separators and its own key order, and every one of the 33 recorded bodies would differ from
the record in a way that means nothing -- inside the one safety net the wave has for
differences that mean something.
"""

from __future__ import annotations

from auditmanager.api.schemas import models
from auditmanager.api.schemas.common import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MIN_LIMIT,
    Page,
    decode_cursor,
    encode_cursor,
    page_body,
    paginate,
    timestamp,
)
from auditmanager.api.schemas.decisions import (
    DecisionEventView,
    append_decision_body,
    check_comment_is_present_for_a_comment_event,
    decision_event_body,
)
from auditmanager.api.schemas.documents import (
    DocumentVersionView,
    ManifestEntryView,
    document_version_body,
)
from auditmanager.api.schemas.findings import (
    EvidenceView,
    FindingDetailView,
    FindingView,
    ObservationView,
    ProvenanceView,
    finding_body,
    finding_detail_body,
)
from auditmanager.api.schemas.projects import ProjectView, project_body
from auditmanager.api.schemas.runs import (
    RunStatusView,
    StageStateView,
    run_status_body,
)

__all__ = [
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "MIN_LIMIT",
    "DecisionEventView",
    "DocumentVersionView",
    "EvidenceView",
    "FindingDetailView",
    "FindingView",
    "ManifestEntryView",
    "ObservationView",
    "Page",
    "ProjectView",
    "ProvenanceView",
    "RunStatusView",
    "StageStateView",
    "append_decision_body",
    "check_comment_is_present_for_a_comment_event",
    "decision_event_body",
    "decode_cursor",
    "document_version_body",
    "encode_cursor",
    "finding_body",
    "finding_detail_body",
    "models",
    "page_body",
    "paginate",
    "project_body",
    "run_status_body",
    "timestamp",
]
