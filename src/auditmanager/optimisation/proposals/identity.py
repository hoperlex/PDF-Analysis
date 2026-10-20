"""The three identities the proposals slice mints: a pass, a proposal, a proposal decision.

``opp_<ULID>`` -- one optimisation pass; ``opr_<ULID>`` -- one proposal of a pass;
``opd_<ULID>`` -- one appended expert decision on a proposal. Each prefix is free in the
shared registry and on every branch of the night window, and each is restated in migration
``0027_optimisation_proposals`` as a format CHECK.

They follow the shared registry's conventions **without registering**, exactly as
:mod:`auditmanager.optimisation.identity` mints ``prl``/``prp``/``vnl``: phase A of the task
owns neither ``contracts/domain/v1/identifiers.json`` nor ``shared/identity``. Contracting
them (phase B) moves the prefixes into the registry.

A pass is identified by this value and by nothing else -- never by its version, its run or
the time it started; a proposal never by its ``ordinal`` (a display order inside its pass)
or by the specification row it came from; a decision never by its ``seq`` (``AGENTS.md`` §4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, Final

from auditmanager.shared.identity import pattern_for

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

OPTIMISATION_PASS_ID_PREFIX: Final[str] = "opp"
OPTIMISATION_PROPOSAL_ID_PREFIX: Final[str] = "opr"
PROPOSAL_DECISION_ID_PREFIX: Final[str] = "opd"

OPTIMISATION_PASS_ID_PATTERN: Final[str] = pattern_for(OPTIMISATION_PASS_ID_PREFIX)
OPTIMISATION_PROPOSAL_ID_PATTERN: Final[str] = pattern_for(OPTIMISATION_PROPOSAL_ID_PREFIX)
PROPOSAL_DECISION_ID_PATTERN: Final[str] = pattern_for(PROPOSAL_DECISION_ID_PREFIX)


@dataclass(frozen=True, slots=True)
class OptimisationPassId(_LocalId):
    prefix: ClassVar[str] = OPTIMISATION_PASS_ID_PREFIX
    field: ClassVar[str] = "optimisation_pass_id"
    _pattern: ClassVar[re.Pattern[str]] = re.compile(OPTIMISATION_PASS_ID_PATTERN)


@dataclass(frozen=True, slots=True)
class OptimisationProposalId(_LocalId):
    prefix: ClassVar[str] = OPTIMISATION_PROPOSAL_ID_PREFIX
    field: ClassVar[str] = "optimisation_proposal_id"
    _pattern: ClassVar[re.Pattern[str]] = re.compile(OPTIMISATION_PROPOSAL_ID_PATTERN)


@dataclass(frozen=True, slots=True)
class ProposalDecisionId(_LocalId):
    prefix: ClassVar[str] = PROPOSAL_DECISION_ID_PREFIX
    field: ClassVar[str] = "proposal_decision_id"
    _pattern: ClassVar[re.Pattern[str]] = re.compile(PROPOSAL_DECISION_ID_PATTERN)
