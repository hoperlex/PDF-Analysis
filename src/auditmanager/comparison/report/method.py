"""The ``report`` method of the shared AI-job core (`CMP-VC-REPORT-01`; `CMP-AI-JOBS-01` section 2): the counts of an estimate and the work items of a job.

A lane supplies an :class:`~auditmanager.comparison.ai_jobs.model.AiMethod` and calls ``ComparisonAiJobService``; it writes no row of
``comparison_ai_job`` and no ``comparison_work`` row of its AI items. The core's scope of a report job is its series; a series has several
reports, so the method is built **per report** (one :class:`ReportSpec`): its counts and its items are those of that report's MD, kind and
reuse flag. A draft has a spec with no report identity yet (the estimate is part of what the draft stores).

Units. A transition is one unit: for the client kind one call, for the analytic kind two (the analyst and the verifier); the analytic kind's
composer is one more call at the end. A transition that is the confirmed absence of changes needs no call and is finished by the program; a
transition whose finished part of an earlier report has the same content key is **reused** when the report asks for it (never requested again).
The one write the method makes is the link of the report to its job (``comparison_report`` ``draft -> queued``, in the transaction that creates the
job), because that is the only place where the job and the report can be bound atomically; it is also what keeps **one live job per report**.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.comparison.ai_jobs.model import (
    AiCallGroup,
    AiCounts,
    AiEstimateRequest,
    AiJobRecord,
    AiMode,
    AiWorkItemSpec,
)
from auditmanager.comparison.report import disciplines, plan as plan_module, chunks as chunk_module
from auditmanager.comparison.report.model import (
    CONFLICT_REPORT_STATE,
    KIND_ANALYTIC,
    KIND_CLIENT,
    METHOD,
    STAGE_CLIENT_WRITING,
    STAGE_TRANSITION_ANALYSIS,
    conflict,
)
from auditmanager.comparison.report.plan import SourceDoc, Unit
from auditmanager.comparison.report.repository import PartRow, ReportRepository

__all__ = [
    "FINAL_PRIORITY",
    "FINAL_UNIT",
    "ReportAiMethod",
    "ReportSpec",
    "UNIT_PREFIX",
    "analysis_mark",
    "part_done",
    "program_part",
    "transition_unit",
]

FINAL_UNIT: Final[str] = "final"
UNIT_PREFIX: Final[str] = "t:"
#: The final item (the composer and the PDF) is claimed after every transition item of the job (higher priority is claimed first).
FINAL_PRIORITY: Final[int] = -50


def transition_unit(transition_id: str) -> str:
    return f"{UNIT_PREFIX}{transition_id}"


@dataclass(frozen=True, slots=True)
class ReportSpec:
    """What the method needs to know of one report. ``report_id`` is ``None`` for a draft that does not exist yet (an estimate only)."""

    kind: str
    reuse: bool
    project_uid: str
    series_id: str
    report_id: str | None
    #: transitions of the report's series, by their number: ``{transition_no: comparison_transition_id}``
    transitions: dict[int, str]
    #: the transition identities of the MD (``T01`` …) that are treated as the absence of changes (a client report prepared from an analytic one)
    unchanged: frozenset[str] = frozenset()


def part_done(part: PartRow | None, kind: str) -> bool:
    if part is None:
        return False
    if kind == KIND_CLIENT:
        return part.selection == "done"
    return part.analysis == "done" and part.verification == "done"


def analysis_mark(part: PartRow | None, kind: str) -> str:
    """The mark that decides a unit's state: the client kind's «Отбор», the analytic kind's weaker of «Анализ» and «Проверка»."""
    if part is None:
        return "pending"
    if kind == KIND_CLIENT:
        return part.selection or "pending"
    marks = [part.analysis or "pending", part.verification or "pending"]
    for mark in ("failed", "running", "pending"):
        if mark in marks:
            return mark
    return "done"


def program_part(kind: str, unit: Unit) -> dict[str, Any]:
    """The part of a transition the program finishes without a model: the confirmed absence of changes. Every field of ``comparison_report_part``
    of the kind, as ``add_part`` takes them."""
    facts: dict[str, Any] = {"content_key": unit.key, "program": unit.reason or "unchanged"}
    if kind == KIND_CLIENT:
        return {"selection": "done", "facts": facts, "points": 0, "questions": 0}
    facts.update({"found": 0, "confirmed": 0, "contradicted": 0, "unconfirmed": 0})
    return {"analysis": "done", "verification": "done", "facts": facts, "warnings": 0}


class ReportAiMethod:
    """The ``report`` method for one report. Built per command; it keeps what it computed (the plan of the MD, the model of the route)."""

    method: str = METHOD

    def __init__(
        self, spec: ReportSpec, *, load_source: Callable[[Session], SourceDoc], pinned_model: Callable[[Session], str],
        repository: ReportRepository | None = None,
    ) -> None:
        self._spec = spec
        self._load = load_source
        self._model = pinned_model
        self._repo = repository or ReportRepository()
        self._cache: tuple[str, SourceDoc, list[Unit]] | None = None

    @property
    def prompt_version(self) -> str:
        return plan_module.prompt_version_of(self._spec.kind)

    @property
    def can_run_without_model(self) -> bool:
        """Opt in only after the estimate built a genuine nonempty zero-call assembly plan."""
        return (self._spec.kind==KIND_ANALYTIC and self._cache is not None
            and bool(self._cache[2]) and not any(unit.too_large for unit in self._cache[2])
            and plan_module.composition_mode(self._cache[2])=="deterministic_chunk_sections")

    # -- the plan ------------------------------------------------------------------------------------
    def _plan(self, session: Session) -> tuple[SourceDoc, list[Unit]]:
        model = self._model(session)
        if self._cache is None or self._cache[0] != model:
            doc = self._load(session)
            profile = disciplines.resolve(doc.manifest.get("project_code"))
            units = plan_module.build_units(
                self._spec.kind, doc, profile, project_uid=self._spec.project_uid, model=model, unchanged=self._spec.unchanged,
            )
            self._cache = (model, doc, units)
        return self._cache[1], self._cache[2]

    def _parts(self, session: Session) -> dict[str, PartRow]:
        if self._spec.report_id is None:
            return {}
        return {p.transition_id: p for p in self._repo.parts(session, self._spec.report_id)}

    def _reusable(self, session: Session, unit: Unit) -> PartRow | None:
        transition_id = self._spec.transitions.get(unit.number)
        if not self._spec.reuse or transition_id is None:
            return None
        return self._repo.reusable(
            session, series_id=self._spec.series_id, transition_id=transition_id, kind=self._spec.kind, content_key=unit.key,
            report_id=self._spec.report_id or "",
        )

    # -- the estimate ---------------------------------------------------------------------------------
    def counts(self, session: Session, request: AiEstimateRequest) -> AiCounts:
        doc, units = self._plan(session)
        parts = self._parts(session)
        groups: list[AiCallGroup] = []
        working = reused = needing = 0
        for unit in units:
            if not unit.editable or unit.too_large:
                continue
            working += 1
            transition_id = self._spec.transitions.get(unit.number)
            part = parts.get(transition_id) if transition_id else None
            if request.mode is AiMode.START:
                needs = self._reusable(session, unit) is None
            elif request.mode is AiMode.LEFT:
                needs = not part_done(part, self._spec.kind)
            else:
                needs = analysis_mark(part, self._spec.kind) == "failed"
            if not needs:
                reused += 1
                continue
            needing += 1
            for label,chars,tokens in unit.calls:
                if unit.chunks and part is not None:
                    stored=part.facts or {}
                    if label in stored.get("paid_replies",{}):
                        continue
                    chunk_id,stage,_=label.rsplit(":",2)
                    row=next((row for row in stored.get("chunks",[]) if row["chunk_id"]==chunk_id),None)
                    if row and row.get("analysis" if stage=="analyst" else "verification")=="done":
                        continue
                groups.append(AiCallGroup(calls=1,prompt_chars=chars,output_tokens=tokens))
        if (self._spec.kind == KIND_ANALYTIC and (needing or request.mode is AiMode.START)
                and plan_module.composition_mode(units)=="model_composer"):
            for _ in range(plan_module.ANALYTIC_RETRIES+1):
                groups.append(AiCallGroup(calls=1, prompt_chars=plan_module.composer_chars(units), output_tokens=plan_module.MAX_TOKENS["composer"]))
        return AiCounts(groups=tuple(groups), units=working, reused=reused, transitions=len(doc.manifest["transitions"]))

    # -- the work items of a job ----------------------------------------------------------------------
    def work_items(self, session: Session, job: AiJobRecord, mode: AiMode) -> Sequence[AiWorkItemSpec]:
        spec = self._spec
        if spec.report_id is None:
            raise ValueError("a draft that does not exist has no work items")
        doc, units = self._plan(session)
        if mode is AiMode.START:
            stage = STAGE_CLIENT_WRITING if spec.kind == KIND_CLIENT else STAGE_TRANSITION_ANALYSIS
            if not self._repo.link_job(session, spec.report_id, job.job_id, stage=stage):
                raise conflict(CONFLICT_REPORT_STATE)  # not a draft: a second start never makes a second live job
        parts = self._parts(session)
        items: list[AiWorkItemSpec] = []
        for unit in units:
            transition_id = spec.transitions.get(unit.number)
            if transition_id is None:
                continue
            part = parts.get(transition_id)
            if not unit.editable:
                if part is None:
                    self._repo.add_part(session, spec.report_id, transition_id, **program_part(spec.kind, unit))
                continue
            if unit.too_large:
                if part is None:  # never sent: a transition over the size of a request is a failed unit of its own, named by its reason
                    self._repo.add_part(session, spec.report_id, transition_id, **self._failed(unit, unit.reason or "transition_too_large"))
                continue
            if mode is AiMode.START and part is None:
                finished = self._reusable(session, unit)
                if finished is not None:  # a finished part under the same content key is copied, not requested again
                    self._repo.add_part(
                        session, spec.report_id, transition_id, analysis=finished.analysis, verification=finished.verification,
                        selection=finished.selection, facts=finished.facts, warnings=finished.warnings, points=finished.points,
                        questions=finished.questions,
                    )
                    continue
                self._repo.add_part(session, spec.report_id, transition_id, **self._pending(unit))
            elif mode is not AiMode.START:
                if part_done(part, spec.kind) or (mode is AiMode.FAILED and analysis_mark(part, spec.kind) != "failed"):
                    continue
                if part is None:
                    self._repo.add_part(session, spec.report_id, transition_id, **self._pending(unit))
                else:
                    self._repo.set_part(session, spec.report_id, transition_id, **self._pending(unit, part))
            items.append(AiWorkItemSpec(
                unit_key=transition_unit(transition_id), priority=0,
                payload={"report_id": spec.report_id, "unit": "transition", "transition_id": transition_id, "number": unit.number},
            ))
        items.append(AiWorkItemSpec(
            unit_key=FINAL_UNIT, priority=FINAL_PRIORITY, payload={"report_id": spec.report_id, "unit": "final"},
        ))
        return items

    def _failed(self, unit: Unit, reason: str) -> dict[str, Any]:
        facts = {"content_key": unit.key, "error": reason}
        if self._spec.kind == KIND_CLIENT:
            return {"selection": "failed", "facts": facts}
        return {"analysis": "failed", "verification": "pending", "facts": facts}

    def _pending(self, unit: Unit, part: PartRow | None = None) -> dict[str, Any]:
        """A part that waits for its model: every mark of the kind ``pending``, the content key stored beside. A part of the analytic kind whose
        analyst has answered keeps that answer (a continue goes on with the verifier and never asks the analyst again)."""
        if part is not None and self._spec.kind == KIND_ANALYTIC:
            if (part.facts or {}).get("content_key")!=unit.key:
                raise conflict(CONFLICT_REPORT_STATE)
            if unit.chunks and (part.facts or {}).get("planning_revision")==chunk_module.REVISION:
                return {"analysis":"done" if part.analysis=="done" else "pending","verification":"pending",
                    "selection":None,"warnings":part.warnings,"points":None,"questions":None,
                    "facts":{key:value for key,value in (part.facts or {}).items() if key!="error"}}
        if part is not None and self._spec.kind == KIND_ANALYTIC and part.analysis == "done" and (part.facts or {}).get("analysis"):
            return {
                "analysis": "done", "verification": "pending", "selection": None, "warnings": None, "points": None, "questions": None,
                "facts": {k: v for k, v in (part.facts or {}).items() if k != "error"},
            }
        facts = {"content_key": unit.key}
        if unit.chunks:
            facts.update(planning_revision=chunk_module.REVISION,
                chunks=[dict(chunk,analysis="pending",verification="pending") for chunk in unit.chunks],paid_replies={})
            facts["chunk_coverage"]=chunk_module.coverage(facts)
        if self._spec.kind == KIND_CLIENT:
            return {"selection": "pending", "facts": facts, "analysis": None, "verification": None, "warnings": None, "points": None, "questions": None}
        return {
            "analysis": "pending", "verification": "pending", "facts": facts, "selection": None, "warnings": None, "points": None,
            "questions": None,
        }
