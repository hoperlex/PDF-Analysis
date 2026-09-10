"""The grounding gate, finding publication and the finding read surface.

The one rule this package exists to enforce: an observation becomes a published finding
only when every evidence item's exact quotation resolves at its declared anchor
(P02 §5.1). Everything else here — identity allocation, the read queries, terminal
selection — hangs off that decision.

Offsets are Unicode code points into one document-global sequence (§4.1), and the
comparison is exact after the single normalization ``source_preparation`` already
applied. Nothing in this package normalizes, repairs or searches for a better anchor.
"""

from auditmanager.findings.artifacts import (
    BLOCK_INDEX_ROLE,
    OBSERVATIONS_ROLE,
    TEXT_LAYER_ROLE,
    Block,
    BlockIndex,
    EvidenceItem,
    Observation,
    ObservationSet,
    Page,
    TextLayer,
)
from auditmanager.findings.grounding import (
    UNGROUNDED_REASONS,
    EvidenceVerdict,
    GateResult,
    ObservationVerdict,
    UngroundedReason,
    check_evidence,
    check_observation,
    run_grounding_gate,
)
from auditmanager.findings.publication import (
    Diagnostic,
    PublicationResult,
    PublishedFinding,
    publish_gate_result,
)
from auditmanager.findings.queries import (
    DiagnosticRow,
    EvidenceRow,
    FindingRow,
    diagnostics,
    evidence_resolves,
    finding_exists,
    observation_belongs_to_finding,
    published_finding_count,
    published_finding_evidence,
    published_findings,
)
from auditmanager.findings.terminal import (
    STAGE_STATUSES,
    TERMINALS_FROM_VALIDATING,
    TerminalSelection,
    select_terminal,
)

__all__ = [
    "BLOCK_INDEX_ROLE",
    "OBSERVATIONS_ROLE",
    "STAGE_STATUSES",
    "TERMINALS_FROM_VALIDATING",
    "TEXT_LAYER_ROLE",
    "UNGROUNDED_REASONS",
    "Block",
    "BlockIndex",
    "Diagnostic",
    "DiagnosticRow",
    "EvidenceItem",
    "EvidenceRow",
    "EvidenceVerdict",
    "FindingRow",
    "GateResult",
    "Observation",
    "ObservationSet",
    "ObservationVerdict",
    "Page",
    "PublicationResult",
    "PublishedFinding",
    "TerminalSelection",
    "TextLayer",
    "UngroundedReason",
    "check_evidence",
    "check_observation",
    "diagnostics",
    "evidence_resolves",
    "finding_exists",
    "observation_belongs_to_finding",
    "publish_gate_result",
    "published_finding_count",
    "published_finding_evidence",
    "published_findings",
    "run_grounding_gate",
    "select_terminal",
]
