"""The whole-specification comparison of one transition: read each side once, check it, compare the two (`CMP-VC-SPEC-01`, part B).

The steps, each safe to repeat (the job that runs them is resumed after a pause or a crash, and a stored answer is never paid for twice):

1. **Read a side** (:func:`read_side`). The version's specification pages are read by the deterministic parser of part A and made into
   the numbered text of :mod:`.source`. The *content key* of the text (project, prompt version, source digest) is looked up first: a
   stored extraction is **never re-requested** -- complete or not, because an answer that failed the check was paid for and the same
   request would only be made again (the original keeps the answer and re-checks it, ``docs/whole_specification_comparison.md``
   lines 70-74). Only when nothing is stored does ``ask`` run: it is handed the text of the request and gives back the model's parsed
   answer, and it owns everything around the call (the route, the consent, the spend journal written *before* the request, the
   recorded mode of the tests); this module never calls a model. The answer is checked by :mod:`.check`; a side that does not pass is
   stored ``partial`` with its issues and yields no row.
2. **Compare the sides** (:func:`compare_sides`). Two complete sides are compared order-independently by :mod:`.whole`; a comparison
   with an incomplete side publishes **no addition, no removal and no claim of "no change"**: it is ``incomplete`` with the reason.
3. **Record it** (:meth:`TransitionRun.finish`): the contract-shaped changes, the totals, the coverage of each side and the reason go
   into the transition's row in one statement that is refused unless the row is ``running`` -- a cancelled job leaves nothing.

A side that cannot be read at all (a specification page whose table the parser could not read, no specification page, a text over the
cap) is *not sent*: it is incomplete with its reason before any request, and the sheet-by-sheet description of the AI-sheet lane
covers those sheets (the method then reads «листовой ИИ»).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.specification import check, prompt, source as source_module, views, whole, batches
from auditmanager.comparison.specification.reader import SpecificationReader
from auditmanager.comparison.specification.repository import ExtractionRow, SpecificationRepository, TransitionScope
from auditmanager.shared.db import session_scope

__all__ = [
    "Answer",
    "Ask",
    "PreparedSide",
    "REASON_NOT_PARSED",
    "Side",
    "TransitionOutcome",
    "TransitionRun",
    "compare_sides",
    "prepare_side",
    "read_side",
]

_LOG = logging.getLogger(__name__)

#: Reasons of an incomplete comparison (the contract's ``^[A-Z][A-Z0-9_]{2,63}$``). The two of :mod:`.check` are
#: ``SPEC_SOURCE_INCOMPLETE`` and ``SPEC_ANSWER_UNCONFIRMED``.
REASON_NOT_PARSED: Final[str] = "SPEC_NOT_PARSED"
REASON_STORED_UNUSABLE: Final[str] = "SPEC_STORED_ANSWER_UNCONFIRMED"
#: The coverage keys the contract carries (``ComparisonSpecCoverage``).
COVERAGE_KEYS: Final[tuple[str, ...]] = ("blocks_total", "blocks_covered", "rows_total", "rows_unresolved")


@dataclass(frozen=True, slots=True)
class Answer:
    """What ``ask`` gives back: the parsed JSON answer, the model it came from and the journal row of the call. ``recorded`` marks a
    replayed (test) answer, which is stored as such and labelled so."""

    payload: Any
    model_identity: str
    recorded: bool
    model_call_id: str | None = None


#: ``ask(prompt_text) -> Answer``. It owns the call; this module never makes one.
Ask = Callable[[str], Answer]


@dataclass(slots=True)
class Side:
    version_uid: str
    sheets: int
    complete: bool
    reason: str | None = None
    extraction_id: str | None = None
    coverage: dict[str, int] | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    #: The stored extraction answered: no request was made for this side.
    reused: bool = False
    #: A request was made for this side in this call.
    sent: bool = False
    issues: list[str] = field(default_factory=list)
    refs: dict[int, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TransitionOutcome:
    state: str  # ``completed`` or ``incomplete``
    reason: str | None
    totals: dict[str, int] | None
    changes: list[dict[str, Any]]
    coverage_a: dict[str, int] | None
    coverage_b: dict[str, int] | None
    extraction_a_id: str | None
    extraction_b_id: str | None


def _coverage(raw: dict[str, Any] | None) -> dict[str, int] | None:
    if not raw:
        return None
    return {key: int(raw.get(key, 0)) for key in COVERAGE_KEYS}


@dataclass(slots=True)
class PreparedSide:
    """What is known of a side before anything is asked: the side as far as it is known, the text a request would carry, its key,
    and the extraction that already answers it."""

    side: Side
    source: dict[str, Any] | None = None
    key: str | None = None
    stored: ExtractionRow | None = None
    batches: tuple[dict[str, Any], ...] = ()

    @property
    def sendable(self) -> bool:
        """A request is due: the text is complete and nothing is stored under its key."""
        return self.source is not None and bool(self.source["complete"]) and self.stored is None


def prepare_side(
    session_factory: sessionmaker[Session], reader: SpecificationReader, repository: SpecificationRepository, *,
    project_uid: str, version_uid: str,
) -> PreparedSide:
    """Read a version's specification pages and look the text up in the store. Asks nobody and writes nothing."""
    stream = reader.version_stream(version_uid)
    side = Side(version_uid=version_uid, sheets=len(stream.refs), complete=False, refs=dict(stream.refs))
    if not stream.parsed_pages or stream.unparsed_pages or not stream.catalogue_complete:
        side.reason = REASON_NOT_PARSED
        side.issues.append("Specification source catalogue is incomplete: " + str(stream.catalogue_reason)
            if not stream.catalogue_complete else "A specification page whose table could not be read"
            if stream.unparsed_pages else "No specification page")
        return PreparedSide(side)
    source = source_module.build_source(stream.parsed,batched=True)
    try:
        planned=batches.plan(source) if source['complete'] else ()
    except ValueError as error:
        source['issues'].append(str(error));source['complete']=False;planned=()
    key = prompt.content_key(project_uid,batches.digest({'source':source['source_sha256'],
        'plan':[row['batch_id'] for row in planned]}),batches.PROMPT_VERSION)
    with session_scope(session_factory) as session:
        stored = repository.find_extraction(session, project_uid, key)
    enriched=[]
    if stored is None:
        with session_scope(session_factory) as session:
            for batch in planned:
                batch_key=prompt.content_key(project_uid,batch['batch_id'],batches.CHECKED_VERSION)
                raw_key=prompt.content_key(project_uid,batch['batch_id'],batches.RAW_VERSION)
                enriched.append({**batch,'key':batch_key,'raw_key':raw_key,
                    'stored':repository.find_extraction(session,project_uid,batch_key),
                    'raw':repository.find_extraction(session,project_uid,raw_key)})
    prepared = PreparedSide(side, source, key, stored,tuple(enriched))
    if stored is not None:
        _from_stored(side, stored)
    elif not source["complete"]:
        side.reason = check.REASON_SOURCE
        side.issues = list(source["issues"])
    return prepared


def read_side(
    session_factory: sessionmaker[Session], reader: SpecificationReader, repository: SpecificationRepository, *,
    project_uid: str, version_uid: str, ask: Ask | None, ask_batch: Callable | None = None, progress: Callable | None = None,
) -> Side:
    """One version's specification: from the store if it was read under this text, else by one request (see the module).

    ``ask`` is ``None`` for a read that must not request anything (an estimate, a replay): a side the store does not hold is then
    ``sent=False`` and ``complete=False`` with ``reason == "SPEC_NOT_READ"``."""
    prepared = prepare_side(session_factory, reader, repository, project_uid=project_uid, version_uid=version_uid)
    side = prepared.side
    if not prepared.sendable:
        return side
    assert prepared.source is not None and prepared.key is not None
    source = prepared.source
    records=[]
    last_answer=None
    for batch in prepared.batches:
        record=batch['stored']
        if record is None:
            raw=batch['raw']
            if raw is not None:
                from auditmanager.analysis.public import ModelResponse
                packet=raw.coverage
                if packet.get('prompt_sha256')!=prompt.prompt_sha256(prompt.prompt_for(batch['source'])):
                    side.reason=check.REASON_SOURCE;side.issues=['Saved paid input changed'];return side
                try:
                    response=ModelResponse(**packet['response'])
                    if response.response_sha256!=packet.get('response_sha256'):raise ValueError()
                except (ValueError,KeyError,TypeError):
                    side.reason=check.REASON_ANSWER;side.issues=['Saved paid reply integrity mismatch'];return side
                payload=None if response.truncated else batches.parse_reply(response.output_text)
                answer=Answer(payload,raw.model_identity,raw.recorded,raw.model_call_id)
            elif ask_batch is not None or ask is not None:
                text=prompt.prompt_for(batch['source'])
                metadata={'project_uid':project_uid,'version_uid':version_uid,'raw_key':batch['raw_key'],
                    'source_sha256':batch['source_sha256'],'batch_id':batch['batch_id'],
                    'source_key':prepared.key,'prompt_sha256':prompt.prompt_sha256(text)}
                answer=ask_batch(text,metadata) if ask_batch is not None else ask(text)
                side.sent=True
            else:
                side.reason='SPEC_NOT_READ';return side
            last_answer=answer
            checked=check.check_extraction(batch['source'],answer.payload)
            detail={**checked['coverage'],'record_kind':'checked_batch','planning_revision':batches.REVISION,
                'issues':checked['issues'],'reason':checked['reason'],'batch_id':batch['batch_id'],
                'owned_line_ids':batch['owned_line_ids'],'context_line_ids':batch['context_line_ids']}
            if ask is None and ask_batch is None:
                record=_BatchRecord('complete' if checked['complete'] else 'partial',checked['rows'],detail)
            else:
                with session_scope(session_factory) as session:
                    record=repository.insert_extraction(session,project_uid=project_uid,version_uid=version_uid,
                        content_key=batch['key'],state='complete' if checked['complete'] else 'partial',
                        prompt_version=batches.CHECKED_VERSION,model_identity=answer.model_identity,recorded=answer.recorded,
                        source_sha256=batch['source_sha256'],positions=checked['rows'],coverage=detail,
                        model_call_id=answer.model_call_id)
        records.append(record)
        if progress is not None:
            _,_,current=batches.aggregate(source,prepared.batches,records)
            progress(version_uid,{**current,'source_key':prepared.key})
        if record.state!='complete':break
    # Every unrequested tail has a real plan entry, never an invented successful row.
    for batch in prepared.batches[len(records):]:
        records.append(_BatchRecord('pending',[],{'issues':['Not requested after incomplete batch']},None))
    complete,positions,coverage=batches.aggregate(source,prepared.batches,records)
    coverage['source_key']=prepared.key
    coverage['model_identities']=sorted({record.model_identity for record in records
        if getattr(record,'model_identity',None)})
    coverage['model_call_ids']=list(dict.fromkeys(record.model_call_id for record in records
        if getattr(record,'model_call_id',None)))
    if ask is None and ask_batch is None:
        side.coverage=_coverage(coverage);side.rows=positions;side.complete=complete
        side.issues=coverage['issues'];side.reason=coverage['reason'];side.reused=True
        return side
    with session_scope(session_factory) as session:
        row = repository.insert_extraction(
            session, project_uid=project_uid, version_uid=version_uid, content_key=prepared.key,
            state="complete" if complete else "partial", prompt_version=batches.PROMPT_VERSION,
            model_identity=last_answer.model_identity if last_answer else records[0].model_identity,
            recorded=all(getattr(record,'recorded',False) for record in records if record.state!='pending'),
            source_sha256=source["source_sha256"],
            positions=positions, coverage=coverage, model_call_id=last_answer.model_call_id if last_answer else None,
        )
    return _from_stored(side, row, sent=True)


@dataclass
class _BatchRecord:
    state: str
    positions: list
    coverage: dict
    extraction_id: str | None = None


def _from_stored(side: Side, stored: ExtractionRow, *, sent: bool = False) -> Side:
    side.extraction_id = stored.extraction_id
    side.coverage = _coverage(stored.coverage)
    side.issues = list(stored.coverage.get("issues") or [])
    side.reused = not sent
    if stored.state == "complete":
        side.complete, side.rows = True, list(stored.positions)
    else:
        side.reason = stored.coverage.get("reason") or REASON_STORED_UNUSABLE
    return side


def compare_sides(old: Side, new: Side, *, versions: tuple[str, str]) -> TransitionOutcome:
    """The comparison of two read sides: ``completed`` only if both are complete (see the module)."""
    result = whole.compare({"complete": old.complete, "rows": old.rows}, {"complete": new.complete, "rows": new.rows})
    if not (old.complete and new.complete):
        reason = (old.reason if not old.complete else new.reason) or REASON_STORED_UNUSABLE
        return TransitionOutcome("incomplete", reason, None, [], old.coverage, new.coverage, old.extraction_id, new.extraction_id)
    refs = {
        "a": {n: {"version_uid": versions[0], "page_number": n, **({"page_profile_id": r["page_profile_id"]} if r.get("page_profile_id") else {})} for n, r in old.refs.items()},
        "b": {n: {"version_uid": versions[1], "page_number": n, **({"page_profile_id": r["page_profile_id"]} if r.get("page_profile_id") else {})} for n, r in new.refs.items()},
    }
    listed = whole.changes_of(result)
    changes = [views.change_dict(c, refs=refs) for c in listed]
    totals = {kind: 0 for kind in whole.KIND_ORDER}
    for change in listed:
        totals[change["kind"]] += 1
    return TransitionOutcome("completed", None, totals, changes, old.coverage, new.coverage, old.extraction_id, new.extraction_id)


class TransitionRun:
    """The part-B work of one transition for a job: read both sides, compare, record."""

    def __init__(
        self, session_factory: sessionmaker[Session], blob_store: Any, *, repository: SpecificationRepository | None = None,
        reader: SpecificationReader | None = None,
    ) -> None:
        self._factory = session_factory
        self._repository = repository or SpecificationRepository()
        self._reader = reader or SpecificationReader(session_factory, blob_store)

    def prepared(self,scope:TransitionScope):
        return tuple(prepare_side(self._factory,self._reader,self._repository,project_uid=scope.project_uid,version_uid=version)
            for version in (scope.source_version_uid,scope.target_version_uid))

    def read(self, scope: TransitionScope, *, ask: Ask | None, ask_batch: Callable | None = None,progress:Callable|None=None) -> tuple[Side, Side]:
        old = read_side(self._factory, self._reader, self._repository, project_uid=scope.project_uid, version_uid=scope.source_version_uid, ask=ask,ask_batch=ask_batch,progress=progress)
        new = read_side(self._factory, self._reader, self._repository, project_uid=scope.project_uid, version_uid=scope.target_version_uid, ask=ask if old.complete else None,ask_batch=ask_batch if old.complete else None,progress=progress)
        return old, new

    def compare(self, scope: TransitionScope, old: Side, new: Side) -> TransitionOutcome:
        return compare_sides(old, new, versions=(scope.source_version_uid, scope.target_version_uid))

    def finish(self, scope: TransitionScope, outcome: TransitionOutcome, *, fence: Callable[[Session], None] | None = None) -> bool:
        """Record the outcome on the transition's row. ``False`` when the row is not ``running`` (the job was cancelled or the row was
        taken back): nothing is written. ``fence`` runs in the same transaction first (the handler proves its lease and the job's
        state there); whatever it raises, nothing is written."""
        with session_scope(self._factory) as session:
            if fence is not None:
                fence(session)
            return self._repository.finish_whole(
                session, scope.transition_id, state=outcome.state, extraction_a_id=outcome.extraction_a_id,
                extraction_b_id=outcome.extraction_b_id, coverage_a=outcome.coverage_a, coverage_b=outcome.coverage_b,
                totals=outcome.totals, changes=outcome.changes, reason=outcome.reason,
            )

    def run(self, scope: TransitionScope, *, ask: Ask) -> TransitionOutcome:
        old, new = self.read(scope, ask=ask)
        outcome = self.compare(scope, old, new)
        if not self.finish(scope, outcome):
            _LOG.info("specification of transition %s not recorded: the row is not running", scope.transition_id)
        return outcome
