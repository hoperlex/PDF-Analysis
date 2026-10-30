"""The ``sheet_changes`` method of the AI-job core (`CMP-VC-AISHEET-01`): what a job would send and the work items a job needs.

``counts`` answers the estimate without a model call and without a write: for each sheet pair that has to be described and has **no
stored description under its content key** it plans the packet (the candidates, the text of the request, the pictures -- planned, not
cut) and makes a call group of one request; a pair whose key already has a description is ``reused`` (never sent again); a pair with no
candidate gets a description with no call. ``work_items`` is called after the job row exists and answers one item per pair, and writes the
pair's ``comparison_ai_sheet_item`` (``queued``) in the same transaction so that a cancelled or waiting sheet has a row to show.

A job's modes (:class:`~auditmanager.comparison.ai_jobs.model.AiMode`):

* ``START`` -- the sheets with no stored description; with ``restart`` every eligible sheet (the ones with a stored description are
  resolved by the handler without a call), so «Описать заново» shows the whole series done;
* ``LEFT`` («Досчитать», a resume after a pause for money) -- the sheets with no stored description;
* ``FAILED`` («Повторить листы с ошибкой») -- the sheets with no stored description whose newest item failed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.comparison.ai_jobs.model import AiCallGroup, AiCounts, AiEstimateRequest, AiJobRecord, AiMode, AiWorkItemSpec
from auditmanager.comparison.ai_sheets import packet as pk
from auditmanager.comparison.ai_sheets import schema as sc
from auditmanager.comparison.ai_sheets.material import SheetMaterial
from auditmanager.comparison.ai_sheets.model import KIND_PAIR, KIND_SINGLE, MAX_OUTPUT_TOKENS, METHOD, SINGLE_TEXT_LIMIT
from auditmanager.comparison.ai_sheets.repository import AiSheetRepository, PairFacts, content_key, prompt_version_of
from auditmanager.comparison.ai_sheets.views import eligible
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["SheetChangesMethod", "facts_of", "keys_for", "kind_of", "model_reader_of_route", "prompt_for"]

#: A single sheet: the instructions, the sheet's text (at most ``SINGLE_TEXT_LIMIT`` characters) and the title lines.
_SINGLE_OVERHEAD_CHARS: Final[int] = 600


def kind_of(pair: PairFacts) -> str:
    return KIND_SINGLE if pair.one_sided else KIND_PAIR


def prompt_for(kind: str) -> str:
    """The ``prompt_version`` column of a description of this kind (the name and the start of the digest)."""
    if kind == KIND_SINGLE:
        return prompt_version_of(sc.SINGLE_PROMPT_VERSION, sc.SINGLE_PROMPT_DIGEST)
    return prompt_version_of(sc.PROMPT_VERSION, sc.PROMPT_DIGEST)


def keys_for(pairs: Sequence[PairFacts], model: str) -> dict[str, str]:
    """``{pair id: content key}`` of the pairs that have a subject."""
    out: dict[str, str] = {}
    for pair in pairs:
        subject = pair.subject_key
        if subject is None:
            continue
        out[pair.pair_id] = content_key(
            project_uid=pair.project_uid, kind=kind_of(pair), subject_key=subject, prompt_version=prompt_for(kind_of(pair)), model=model,
        )
    return out


def facts_of(pair: PairFacts) -> pk.SheetFacts:
    """The header of the packet from the stored rows (a version is named by its ordinal, never by a file name)."""
    return pk.SheetFacts(
        sheet_pair_id=pair.pair_id, title=pair.title, project_title=pair.document_title or pair.project_name,
        designation=pair.designation or "", label_a=f"версия №{pair.ordinal_a}" if pair.ordinal_a else "прежняя версия",
        label_b=f"версия №{pair.ordinal_b}" if pair.ordinal_b else "новая версия", page_a=pair.page_a or 0, page_b=pair.page_b or 0,
        sheet_number=pair.sheet_number, status=pair.result_status or pair.status or "", reasons=tuple(pair.result_reasons),
        page_profile_a=pair.page_a_profile_id or "", page_profile_b=pair.page_b_profile_id or "", version_a=pair.version_a,
        version_b=pair.version_b,
    )


def model_reader_of_route(session: Session) -> str:
    """The model the work kind is routed to now: the pin of the primary connection's current revision."""
    from auditmanager.comparison.ai_jobs.estimate import read_route
    from auditmanager.comparison.ai_sheets.model import WORK_KIND

    return read_route(session, WORK_KIND, "live").pinned_model


class SheetChangesMethod:
    """The :class:`~auditmanager.comparison.ai_jobs.model.AiMethod` of the sheet descriptions."""

    method: str = METHOD

    def __init__(
        self, material: SheetMaterial | Callable[[], SheetMaterial] | None = None, *, repository: AiSheetRepository | None = None,
        model_reader: Callable[[Session], str] = model_reader_of_route,
    ) -> None:
        self._material = material
        self._repo = repository or AiSheetRepository()
        self._model_reader = model_reader

    @property
    def prompt_version(self) -> str:
        """Part of the estimate digest: a new prompt (or a new schema) is a new estimate."""
        return prompt_for(KIND_PAIR)

    def material(self) -> SheetMaterial:
        if self._material is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_ai_sheets")
        if not hasattr(self._material, "page"):  # a factory: the real material opens the page-profile reader on first use
            self._material = self._material()  # type: ignore[operator]
        return self._material  # type: ignore[return-value]

    # -- which sheets ---------------------------------------------------------------------------------------------------
    def eligible_pairs(self, session: Session, scope: Any) -> list[PairFacts]:
        if scope.series_id is not None:
            pairs = [p for p in self._repo.pairs_of_series(session, scope.series_id) if p.transition_state == "completed"]
        else:
            pair = self._repo.pair(session, scope.sheet_pair_id)
            pairs = [] if pair is None else [pair]
        return [p for p in pairs if eligible(p)]

    def wanted(self, session: Session, scope: Any, mode: AiMode, model: str, *, restart: bool) -> tuple[list[PairFacts], dict[str, str], set[str]]:
        """``(the pairs of the job's items, their content keys, the keys that are stored)``."""
        everything = self.eligible_pairs(session, scope)
        keys = keys_for(everything, model)
        stored = set(self._repo.stored_keys(session, scope.project_uid, list(keys.values())))
        lacking = [p for p in everything if keys[p.pair_id] not in stored]
        if mode is AiMode.START:
            return (everything if restart else lacking), keys, stored
        if mode is AiMode.LEFT:
            return lacking, keys, stored
        failed = self._failed_ids(session, scope)
        return [p for p in lacking if p.pair_id in failed], keys, stored

    def _failed_ids(self, session: Session, scope: Any) -> set[str]:
        """The pairs whose newest item failed (any job): what «Повторить листы с ошибкой» describes again."""
        if scope.series_id is not None:
            return {ps.pair_id for ps in self._repo.states_of_series(session, scope.series_id) if ps.item_state == "failed"}
        ps = self._repo.state_of_pair(session, scope.sheet_pair_id)
        return set() if ps is None or ps.item_state != "failed" else {ps.pair_id}

    # -- the estimate ---------------------------------------------------------------------------------------------------
    def counts(self, session: Session, request: AiEstimateRequest) -> AiCounts:
        scope = request.scope
        model = self._model_reader(session)
        chosen, keys, stored = self.wanted(session, scope, request.mode, model, restart=False)
        everything = self.eligible_pairs(session, scope)
        groups: list[AiCallGroup] = []
        for pair in chosen:
            group = self._group_of(session, pair)
            if group is not None:
                groups.append(group)
        reused = sum(1 for p in everything if keys[p.pair_id] in stored)
        units = len(chosen) if request.mode is not AiMode.START else len(everything)
        return AiCounts(
            groups=tuple(groups), units=units, reused=min(reused, units) if request.mode is AiMode.START else 0, sheets=units,
            pairs=sum(1 for p in chosen if not p.one_sided),
            transitions=len({p.transition_id for p in (everything if request.mode is AiMode.START else chosen)}),
        )

    def _group_of(self, session: Session, pair: PairFacts) -> AiCallGroup | None:
        """One request's shape for a pair, or ``None`` when no call is needed (a pair with no candidate)."""
        from auditmanager.comparison.ai_sheets import images as pix

        if pair.one_sided:
            overview = self._single_image_size(pair)
            return AiCallGroup(
                calls=1, prompt_chars=len(sc.SYSTEM_PROMPT) + len(sc.SINGLE_PROMPT) + SINGLE_TEXT_LIMIT + _SINGLE_OVERHEAD_CHARS,
                output_tokens=MAX_OUTPUT_TOKENS,
                images=1 if overview else 0, image_bytes=overview,
            )
        result = self._repo.result_document(session, pair.result_id) if pair.result_id else None
        if result is None:
            return None
        try:
            planned = pk.assemble(facts_of(pair), result, self.material(), render=False, xrefs=False)
        except DomainError:
            # the page profiles cannot be read now: a request of the usual size is priced, and the run reports what it finds
            return AiCallGroup(calls=1, prompt_chars=12000 + len(sc.SYSTEM_PROMPT), output_tokens=MAX_OUTPUT_TOKENS,
                               images=2, image_bytes=pix.estimate_bytes(1400, 1000) * 2)
        if not planned.candidates:
            return None
        budget = planned.document["budget"]
        return AiCallGroup(
            calls=1, prompt_chars=int(budget["prompt_chars"]) + len(sc.SYSTEM_PROMPT), output_tokens=MAX_OUTPUT_TOKENS,
            images=int(budget["images"]),
            image_bytes=int(budget["image_bytes"]),
        )

    @staticmethod
    def _single_image_size(pair: PairFacts) -> int:
        from auditmanager.comparison.ai_sheets import images as pix

        return pix.estimate_bytes(1400, 1000)

    # -- the work items -------------------------------------------------------------------------------------------------
    def work_items(self, session: Session, job: AiJobRecord, mode: AiMode) -> list[AiWorkItemSpec]:
        scope = job.scope
        chosen, _keys, _stored = self.wanted(session, scope, mode, job.pinned_model, restart=job.restart)
        if mode is AiMode.FAILED:
            # «Повторить листы с ошибкой» describes the failed sheets and nothing else: a sheet that was waiting when the job was
            # cancelled stays cancelled, so no row of this job says it is still to come.
            wanted = {p.pair_id for p in chosen}
            for item in self._repo.items_of_job(session, job.job_id):
                if item.pair_id not in wanted and item.state in ("queued", "running"):
                    self._repo.move_item(session, job_id=job.job_id, pair_id=item.pair_id, from_states=("queued", "running"),
                                         to_state="cancelled")
        specs: list[AiWorkItemSpec] = []
        for pair in sorted(chosen, key=lambda p: (p.transition_no, p.pair_no)):
            self._repo.ensure_item(session, job_id=job.job_id, project_uid=job.project_uid, pair_id=pair.pair_id)
            if mode is not AiMode.START:
                self._repo.requeue_item(session, job_id=job.job_id, pair_id=pair.pair_id)
            specs.append(AiWorkItemSpec(unit_key=pair.pair_id, payload={"sheet_pair_id": pair.pair_id, "kind": kind_of(pair)}))
        return specs
