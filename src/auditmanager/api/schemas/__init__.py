"""Wire shapes for ``contracts/api/v1/openapi.json``.

Every view type here restates one frozen schema's property set exactly, and every
``*_body`` function renders one. Nothing in this package reaches a database, a service,
an environment variable or a clock: given a view it produces the same body every time.

The view types are also the **seam**. A router never receives a domain record; it
receives one of these, built by whatever the composition root wired behind the ports in
:mod:`auditmanager.api.routers.ports`. That is what lets this session build the run and
export routers against shapes ``B5`` is producing in parallel: the two sides agree on
the frozen document rather than on each other's code.
"""

from __future__ import annotations

from auditmanager.api.schemas.common import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MIN_LIMIT,
    Page,
    decode_cursor,
    encode_cursor,
    page_body,
    paginate,
    parse_limit,
    timestamp,
)
from auditmanager.api.schemas.decisions import (
    AppendDecisionCommand,
    DecisionEventView,
    append_decision_body,
    decision_event_body,
    parse_append_decision_request,
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
from auditmanager.api.schemas.projects import (
    ProjectView,
    parse_create_project_request,
    project_body,
)
from auditmanager.api.schemas.runs import (
    RunStatusView,
    StageStateView,
    StartRunCommand,
    parse_start_run_request,
    run_status_body,
)

__all__ = [
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "MIN_LIMIT",
    "AppendDecisionCommand",
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
    "StartRunCommand",
    "append_decision_body",
    "decision_event_body",
    "decode_cursor",
    "document_version_body",
    "encode_cursor",
    "finding_body",
    "finding_detail_body",
    "page_body",
    "paginate",
    "parse_append_decision_request",
    "parse_create_project_request",
    "parse_limit",
    "parse_start_run_request",
    "project_body",
    "run_status_body",
    "timestamp",
]
