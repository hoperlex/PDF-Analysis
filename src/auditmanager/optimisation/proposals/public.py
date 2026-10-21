"""The surface of the proposals slice (`W60-OPT-PROPOSALS-01`).

Inside the optimisation context; the composition root reaches it through
:mod:`auditmanager.optimisation.public`, which re-exports these names once the operations are
contracted (phase B). Nothing outside this package imports its other modules.
"""

from __future__ import annotations

from auditmanager.optimisation.proposals.commands import (
    PassStart,
    ProposalDecision,
    decide_optimisation_proposal,
    start_optimisation_pass,
)
from auditmanager.optimisation.proposals.export import (
    COLUMNS as PROPOSAL_CSV_COLUMNS,
)
from auditmanager.optimisation.proposals.export import (
    CONTENT_TYPE as PROPOSAL_CSV_CONTENT_TYPE,
)
from auditmanager.optimisation.proposals.export import (
    ProposalsCsv,
    escape_formula,
    export_optimisation_proposals_csv,
)
from auditmanager.optimisation.proposals.generator import (
    ANALOG_BASES,
    GENERATOR_VERSION,
    MAX_PROPOSALS_PER_ROW,
    NAME_SIMILARITY_THRESHOLD,
    PROPOSAL_TYPE_CHEAPER_ANALOG,
    PROPOSAL_TYPES,
    GeneratorOutcome,
    ProposalDraft,
    generate_cheaper_analogs,
)
from auditmanager.optimisation.proposals.identity import (
    OPTIMISATION_PASS_ID_PATTERN,
    OPTIMISATION_PASS_ID_PREFIX,
    OPTIMISATION_PROPOSAL_ID_PATTERN,
    OPTIMISATION_PROPOSAL_ID_PREFIX,
    PROPOSAL_DECISION_ID_PATTERN,
    PROPOSAL_DECISION_ID_PREFIX,
    OptimisationPassId,
    OptimisationProposalId,
    ProposalDecisionId,
)
from auditmanager.optimisation.proposals.policy import (
    AGGREGATE_OPTIMISATION_PASS,
    AGGREGATE_OPTIMISATION_PROPOSAL,
    COMMAND_TYPE_DECIDE_PROPOSAL,
    COMMAND_TYPE_START_PASS,
    DECISION_FILTERS,
    DECISION_PENDING,
    DEFAULT_PROPOSAL_PAGE,
    MAX_COMMENT_LENGTH,
    MAX_PASS_PAGE,
    MAX_PROPOSAL_PAGE,
    PASS_REFUSAL_REASONS,
    REFUSAL_VENDOR_LIST_MISSING,
    VERDICTS,
)
from auditmanager.optimisation.proposals.queries import (
    ProposalPage,
    get_optimisation_pass,
    list_optimisation_passes,
    list_optimisation_proposals,
    list_proposal_decisions,
)
from auditmanager.optimisation.proposals.repository import (
    OptimisationPassRecord,
    OptimisationProposalRecord,
    PositionSummary,
    ProposalDecisionRecord,
)

__all__ = [
    "AGGREGATE_OPTIMISATION_PASS",
    "AGGREGATE_OPTIMISATION_PROPOSAL",
    "ANALOG_BASES",
    "COMMAND_TYPE_DECIDE_PROPOSAL",
    "COMMAND_TYPE_START_PASS",
    "DECISION_FILTERS",
    "DECISION_PENDING",
    "DEFAULT_PROPOSAL_PAGE",
    "GENERATOR_VERSION",
    "MAX_COMMENT_LENGTH",
    "MAX_PASS_PAGE",
    "MAX_PROPOSALS_PER_ROW",
    "MAX_PROPOSAL_PAGE",
    "NAME_SIMILARITY_THRESHOLD",
    "OPTIMISATION_PASS_ID_PATTERN",
    "OPTIMISATION_PASS_ID_PREFIX",
    "OPTIMISATION_PROPOSAL_ID_PATTERN",
    "OPTIMISATION_PROPOSAL_ID_PREFIX",
    "PASS_REFUSAL_REASONS",
    "PROPOSAL_CSV_COLUMNS",
    "PROPOSAL_CSV_CONTENT_TYPE",
    "PROPOSAL_DECISION_ID_PATTERN",
    "PROPOSAL_DECISION_ID_PREFIX",
    "PROPOSAL_TYPES",
    "PROPOSAL_TYPE_CHEAPER_ANALOG",
    "REFUSAL_VENDOR_LIST_MISSING",
    "VERDICTS",
    "GeneratorOutcome",
    "OptimisationPassId",
    "OptimisationPassRecord",
    "OptimisationProposalId",
    "OptimisationProposalRecord",
    "PassStart",
    "PositionSummary",
    "ProposalDecision",
    "ProposalDecisionId",
    "ProposalDecisionRecord",
    "ProposalDraft",
    "ProposalPage",
    "ProposalsCsv",
    "decide_optimisation_proposal",
    "escape_formula",
    "export_optimisation_proposals_csv",
    "generate_cheaper_analogs",
    "get_optimisation_pass",
    "list_optimisation_passes",
    "list_optimisation_proposals",
    "list_proposal_decisions",
    "start_optimisation_pass",
]
