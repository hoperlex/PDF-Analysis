"""Publication — turning a gate verdict into rows, and identity allocation.

What reaches the database is decided entirely by :mod:`auditmanager.findings.grounding`:

* a **grounded** observation gets a fresh ``finding_uid``, an immutable
  ``finding_observation_id`` bound to this one run, and one ``finding_evidence`` row per
  declared anchor;
* an **ungrounded** observation gets a ``finding_observation`` row carrying
  ``grounded = false``, its ``ungrounded_reason`` and **no** ``finding_uid`` — and no
  evidence rows, because an evidence row is the record of an anchor that resolved.

``finding_uid`` is fresh per published observation, per run (§5.2). PC-01 does no
cross-run matching and no decision carryover, so two runs over the same document produce
two disjoint sets. That is not a limitation this module works around: allocating a
carried-over identity would silently attach one document's expert history to another
run's text.

The pairing ``grounded = (finding_uid IS NOT NULL)`` and
``grounded = (ungrounded_reason IS NULL)`` is a CHECK constraint in the migration. This
module writes rows that satisfy it and does **not** re-assert it in Python: a second
copy of a rule is a second place for it to be wrong, and the constraint is the one a
future caller cannot bypass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.findings.artifacts import ObservationSet
from auditmanager.findings.grounding import GateResult
from auditmanager.shared.db import SQLSTATE_TO_CATALOG_CODE, nested_transaction
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import FindingObservationId, FindingUid

_INSERT_FINDING = text(
    """
    INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category)
    VALUES (:finding_uid, :project_uid, :version_uid, :run_id, :category)
    """
)

_INSERT_OBSERVATION = text(
    """
    INSERT INTO finding_observation (
        finding_observation_id, run_id, finding_uid, stage_id, category,
        finding_text, recommendation_text, grounded, ungrounded_reason,
        analysis_profile_id, prompt_bundle_id, model_call_id, provider_mode
    ) VALUES (
        :finding_observation_id, :run_id, :finding_uid, :stage_id, :category,
        :finding_text, :recommendation_text, :grounded, :ungrounded_reason,
        :analysis_profile_id, :prompt_bundle_id, :model_call_id, :provider_mode
    )
    """
)

_INSERT_EVIDENCE = text(
    """
    INSERT INTO finding_evidence (
        finding_observation_id, evidence_ordinal, page_number, quote,
        char_start, char_end, block_id
    ) VALUES (
        :finding_observation_id, :evidence_ordinal, :page_number, :quote,
        :char_start, :char_end, :block_id
    )
    """
)


@dataclass(frozen=True, slots=True)
class PublishedFinding:
    """One observation that survived the gate, with the identities allocated for it."""

    finding_uid: str
    finding_observation_id: str
    observation_ordinal: int
    category: str
    evidence_count: int


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One observation the gate rejected. Counted as a finding nowhere."""

    finding_observation_id: str
    observation_ordinal: int
    ungrounded_reason: str


@dataclass(frozen=True, slots=True)
class PublicationResult:
    """What one publication wrote, in terms a caller can assert on."""

    run_id: str
    published: tuple[PublishedFinding, ...] = field(default_factory=tuple)
    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)

    @property
    def published_count(self) -> int:
        return len(self.published)

    @property
    def diagnostic_count(self) -> int:
        return len(self.diagnostics)

    @property
    def finding_uids(self) -> tuple[str, ...]:
        return tuple(entry.finding_uid for entry in self.published)


def _translate(exc: DBAPIError) -> DomainError:
    """Map a database refusal on **SQLSTATE**, never on message text.

    A message is a diagnostic string that a server upgrade or a locale may reword; the
    SQLSTATE is the contract. ``SQLSTATE_TO_CATALOG_CODE`` is the shared kernel's map
    and this module adds no second one.
    """
    sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None) or getattr(
        exc, "code", None
    )
    mapped = SQLSTATE_TO_CATALOG_CODE.get(str(sqlstate)) if sqlstate else None
    if mapped is not None:
        return DomainError(ErrorCode(mapped), message=f"the database refused the write ({sqlstate})")
    return DomainError(ErrorCode.INTERNAL_ERROR, message="the database refused the write")


def publish_gate_result(
    session: Session,
    *,
    gate_result: GateResult,
    observation_set: ObservationSet,
    run_id: str,
    project_uid: str,
    version_uid: str,
    model_call_ids: Mapping[int, str] | None = None,
) -> PublicationResult:
    """Write the gate's decision, in one savepoint inside the caller's unit of work.

    The caller owns the transaction — this module opens no engine, commits nothing and
    writes no rollback of its own. The savepoint means a publication that violates a
    constraint discards only the publication, leaving the run's own bookkeeping for the
    caller to finish or abandon.

    ``model_call_ids`` maps ``observation_ordinal`` to the ``model_call_id`` that
    produced it, for the provenance §5 requires. An observation with no entry is written
    with a NULL ``model_call_id`` rather than a fabricated one.
    """
    calls = dict(model_call_ids or {})
    published: list[PublishedFinding] = []
    diagnostics: list[Diagnostic] = []

    try:
        with nested_transaction(session):
            for verdict in gate_result.verdicts:
                observation = verdict.observation
                observation_id = FindingObservationId.new().value
                model_call_id = calls.get(observation.observation_ordinal) or (
                    observation.model_call_id
                )

                if verdict.grounded:
                    # Fresh identity, this run only. §5.2.
                    finding_uid: str | None = FindingUid.new().value
                    session.execute(
                        _INSERT_FINDING,
                        {
                            "finding_uid": finding_uid,
                            "project_uid": project_uid,
                            "version_uid": version_uid,
                            "run_id": run_id,
                            "category": observation.category,
                        },
                    )
                    reason: str | None = None
                else:
                    finding_uid = None
                    failing = verdict.reason
                    assert failing is not None  # an ungrounded verdict always carries one
                    reason = failing.value

                session.execute(
                    _INSERT_OBSERVATION,
                    {
                        "finding_observation_id": observation_id,
                        "run_id": run_id,
                        "finding_uid": finding_uid,
                        "stage_id": observation_set.stage_id,
                        "category": observation.category,
                        "finding_text": observation.finding_text,
                        "recommendation_text": observation.recommendation_text,
                        "grounded": verdict.grounded,
                        "ungrounded_reason": reason,
                        "analysis_profile_id": observation_set.analysis_profile_id,
                        "prompt_bundle_id": observation_set.prompt_bundle_id,
                        "model_call_id": model_call_id,
                        "provider_mode": observation_set.provider_mode,
                    },
                )

                if verdict.grounded:
                    for item in observation.evidence:
                        session.execute(
                            _INSERT_EVIDENCE,
                            {
                                "finding_observation_id": observation_id,
                                "evidence_ordinal": item.evidence_ordinal,
                                "page_number": item.page_number,
                                "quote": item.quote,
                                "char_start": item.char_start,
                                "char_end": item.char_end,
                                "block_id": item.block_id,
                            },
                        )
                    assert finding_uid is not None
                    published.append(
                        PublishedFinding(
                            finding_uid=finding_uid,
                            finding_observation_id=observation_id,
                            observation_ordinal=observation.observation_ordinal,
                            category=observation.category,
                            evidence_count=len(observation.evidence),
                        )
                    )
                else:
                    assert reason is not None
                    diagnostics.append(
                        Diagnostic(
                            finding_observation_id=observation_id,
                            observation_ordinal=observation.observation_ordinal,
                            ungrounded_reason=reason,
                        )
                    )
    except DBAPIError as exc:
        raise _translate(exc) from exc

    return PublicationResult(
        run_id=run_id,
        published=tuple(published),
        diagnostics=tuple(diagnostics),
    )
