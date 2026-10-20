"""The three identities the proposals slice mints: a pass, a proposal, a proposal decision.

``opp_<ULID>`` -- one optimisation pass; ``opr_<ULID>`` -- one proposal of a pass;
``opd_<ULID>`` -- one appended expert decision on a proposal. `W60-OPT-PROPOSALS-01` phase B
contracted all three (``contracts/domain/v1/identifiers.json`` revision 17), so the shared
registry (:mod:`auditmanager.shared.identity.ids`) owns the prefixes and their patterns, and
migration ``0027_optimisation_proposals`` restates each as a format CHECK. The types here
**validate through the registry's types**, exactly as :mod:`auditmanager.optimisation.identity`
does for ``prl``/``prp``/``vnl``, and add only this boundary's refusal shape: a malformed value
is ``validation_failed`` naming the field.

A pass is identified by this value and by nothing else -- never by its version, its run or the
time it started; a proposal never by its ``ordinal`` (a display order inside its pass) or by
the specification row it came from; a decision never by its ``seq`` (``AGENTS.md`` §4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final

from auditmanager.shared import identity as registry
from auditmanager.shared.identity import OpaqueId

from ..identity import _LocalId

__all__ = [
    "OPTIMISATION_PASS_ID_PATTERN",
    "OPTIMISATION_PASS_ID_PREFIX",
    "OPTIMISATION_PROPOSAL_ID_PATTERN",
    "OPTIMISATION_PROPOSAL_ID_PREFIX",
    "PROPOSAL_DECISION_ID_PATTERN",
    "PROPOSAL_DECISION_ID_PREFIX",
    "OptimisationPassId",
    "OptimisationProposalId",
    "ProposalDecisionId",
]

OPTIMISATION_PASS_ID_PREFIX: Final[str] = registry.OptimisationPassId.prefix
OPTIMISATION_PROPOSAL_ID_PREFIX: Final[str] = registry.OptimisationProposalId.prefix
PROPOSAL_DECISION_ID_PREFIX: Final[str] = registry.ProposalDecisionId.prefix

OPTIMISATION_PASS_ID_PATTERN: Final[str] = registry.pattern_for(OPTIMISATION_PASS_ID_PREFIX)
OPTIMISATION_PROPOSAL_ID_PATTERN: Final[str] = registry.pattern_for(OPTIMISATION_PROPOSAL_ID_PREFIX)
PROPOSAL_DECISION_ID_PATTERN: Final[str] = registry.pattern_for(PROPOSAL_DECISION_ID_PREFIX)


@dataclass(frozen=True, slots=True)
class OptimisationPassId(_LocalId):
    registry_type: ClassVar[type[OpaqueId]] = registry.OptimisationPassId
    field: ClassVar[str] = "optimisation_pass_id"


@dataclass(frozen=True, slots=True)
class OptimisationProposalId(_LocalId):
    registry_type: ClassVar[type[OpaqueId]] = registry.OptimisationProposalId
    field: ClassVar[str] = "optimisation_proposal_id"


@dataclass(frozen=True, slots=True)
class ProposalDecisionId(_LocalId):
    registry_type: ClassVar[type[OpaqueId]] = registry.ProposalDecisionId
    field: ClassVar[str] = "proposal_decision_id"
