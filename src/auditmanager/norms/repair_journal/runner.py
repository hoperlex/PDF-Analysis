"""The durable repair runner: every paid call through the journal, and nothing paid twice.

`W54-PLAN.md` §3.3 and `R-106`, as code:

- **Write order.** The intent is appended to the fsynced file (:class:`LocalJournal`), the
  ``norm_repair_call`` row is committed, and only then is the call dispatched. The response
  body is checkpointed *before* it is parsed — bytes to file, row to ``response_received``,
  then the file line — and the settlement commits to the database before the file records it.
- **Reconciliation on start, both directions.** An intent in the file and not in the
  database becomes ``outcome_unknown`` at its bound (it may have been dispatched); an intent
  in the database and not in the file refuses the start. A database restored from an older
  dump after a lost volume is carried forward from the file's recorded effects. A row left
  ``prepared`` is ``outcome_unknown`` unless its body was checkpointed to disk; a row left
  ``response_received`` is completed from the bytes on file. **No call is ever dispatched
  twice:** progress is recomputed from the journal, so a page whose answer is on file is
  replayed, not re-paid.
- **Tries (`R-79`).** At most three provider tries per recognition, 2 s and 8 s apart (a
  ``Retry-After`` of up to 60 s wins), and only after a try the transport proved was not
  processed. Every 503 and every other ambiguous failure is ``outcome_unknown`` (`R-85`,
  D-153) and is never re-paid; 400/401/403/413 end the call and stop the run.
- **Price.** ``usage.cost`` is the charge; an unpriced answer is charged at its bound and
  stops the run; an answer from another model than the configured one is charged and
  refused and stops the run (H-6). The ceiling is cumulative over every row in the
  database, checked before each call against the call's bound and after it against the
  actual charge.
- **Sample first (`R-95`).** The three largest crops by area run first; the full run proceeds
  only if ``mean sample cost x pages x 1.25 <= ceiling``, and otherwise stops for the
  owner's decision, which is recorded in the journal when given.
- **Outcomes (`F-4`).** The ledger is a pure function of the journal and the corpus pages:
  a page not ending ``REPAIRED`` is unreliable, and a page the run never finished is
  ``NOT_ATTEMPTED``.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from auditmanager.shared.identity import NormRepairCallId

from ..repair import PageRepair, RepairAttempt, RepairLedger, RepairOutcome, ledger_of
from ..rerecognition import MAX_ATTEMPTS, PageToRecognise, judge
from .file_journal import LocalJournal
from .model import (
    CEILING_USD,
    MAX_CONSECUTIVE_UNKNOWN,
    MAX_PROVIDER_TRIES,
    REFUSED_ANSWERS,
    RETRY_AFTER_CAP_SECONDS,
    RETRY_DELAYS_SECONDS,
    RETRY_SAFE_FAILURES,
    SAMPLE_MARGIN,
    SAMPLE_SIZE,
    AnswerReader,
    CallFailure,
    CallIntent,
    CallState,
    Failure,
    JournalCall,
    JournalRefused,
    PreparedRequest,
    RepairTransport,
    RunStopped,
    Settlement,
    StopReason,
    UnreadableAnswer,
    money,
)
from .pricing import rate_for, unknown_outcome_bound
from .repository import CallStore

#: Failures that end the whole run, not only the call.
_RUN_STOPPING: dict[str, str] = {
    Failure.CREDENTIAL_REFUSED: "the proxy refused the credential (401/403)",
    Failure.REQUEST_REFUSED: "the proxy refused the request (400/413)",
    Failure.MODEL_MISMATCH: "the answer names another model than the configured one (H-6)",
    Failure.UNPRICED: "the answer carries no usage.cost, so the ceiling cannot be held",
}

SAMPLE_PROCEED = "proceed"
SAMPLE_STOP = "stop_for_owner"


def _no_fault(_point: str) -> None:
    return None


@dataclass(frozen=True, slots=True)
class PageProgress:
    """Where one page stands, recomputed from the journal alone."""

    outcome: RepairOutcome | None
    attempts: tuple[RepairAttempt, ...] = ()
    replacement: str | None = None
    next_ordinal: int = 0
    next_try: int = 0
    delay_seconds: float = 0.0

    @property
    def finished(self) -> bool:
        return self.outcome is not None


@dataclass(slots=True)
class ReconcileReport:
    """What a start found and did. Every count is a call."""

    restored_rows: int = 0
    forwarded_effects: int = 0
    file_forwarded: int = 0
    recovered_bodies: int = 0
    completed_from_checkpoint: int = 0
    reconciled_unknown: int = 0
    dropped_torn_tail: bool = False

    def as_document(self) -> dict[str, Any]:
        return {
            "restored_rows": self.restored_rows,
            "forwarded_effects": self.forwarded_effects,
            "file_forwarded": self.file_forwarded,
            "recovered_bodies": self.recovered_bodies,
            "completed_from_checkpoint": self.completed_from_checkpoint,
            "reconciled_unknown": self.reconciled_unknown,
            "dropped_torn_tail": self.dropped_torn_tail,
        }


@dataclass(slots=True)
class RunSummary:
    pages: int
    finished_pages: int
    dispatched_calls: int
    charged_usd: Decimal
    stop: str | None = None
    outcomes: dict[str, int] = field(default_factory=dict)

    def as_document(self) -> dict[str, Any]:
        return {
            "pages": self.pages,
            "finished_pages": self.finished_pages,
            "dispatched_calls": self.dispatched_calls,
            "charged_usd": str(self.charged_usd),
            "stop": self.stop,
            "outcomes": dict(sorted(self.outcomes.items())),
        }


def _page_calls(journal: LocalJournal, page: PageToRecognise, model: str) -> list[JournalCall]:
    crop = page.crop_sha256
    return [
        call
        for call in journal.calls.values()
        if call.intent.block_anchor == page.block_id
        and call.intent.crop_sha256 == crop
        and call.intent.model == model
    ]


def page_progress(
    journal: LocalJournal, page: PageToRecognise, reader: AnswerReader, *, model: str
) -> PageProgress:
    """The page's state as the journal records it: finished with an outcome, or the next try.

    The same rule as :func:`~auditmanager.norms.rerecognition.rerecognise` (two reads, a
    clean answer applied, a truncated or empty one unusable), with three additions: a refused
    answer is ``UNUSABLE``, an unknown or unprocessed call is ``CALL_FAILED``, and a retry-safe
    failure is tried again up to `R-79`'s limit.
    """
    by_ordinal: dict[int, list[JournalCall]] = {}
    for call in _page_calls(journal, page, model):
        by_ordinal.setdefault(call.intent.ordinal, []).append(call)
    attempts: list[RepairAttempt] = []
    for ordinal in range(1, MAX_ATTEMPTS + 1):
        tries = sorted(by_ordinal.get(ordinal, ()), key=lambda c: c.intent.try_number)
        if not tries:
            return PageProgress(None, tuple(attempts), next_ordinal=ordinal, next_try=1)
        last = tries[-1]
        settlement = last.settlement
        if settlement is None:
            raise JournalRefused(
                f"{last.intent.call_id}: unsettled after reconciliation; refusing to guess"
            )
        if settlement.state is CallState.COMPLETED:
            if settlement.failure in REFUSED_ANSWERS:
                return PageProgress(RepairOutcome.UNUSABLE, tuple(attempts))
            raw = journal.read_response(last.intent.call_id, last.response_sha256)
            try:
                answer = reader.read_answer(raw)
            except UnreadableAnswer:
                raise JournalRefused(
                    f"{last.intent.call_id}: an answer accepted when it arrived no longer "
                    "reads; refusing to guess"
                ) from None
            attempt, ended = judge(answer, ordinal=ordinal, now=last.settled_at or "")
            attempts.append(attempt)
            if ended is RepairOutcome.REPAIRED:
                return PageProgress(ended, tuple(attempts), replacement=answer.text.strip())
            if ended is not None:
                return PageProgress(ended, tuple(attempts))
            continue
        if settlement.state is CallState.NOT_PROCESSED and (
            settlement.failure in RETRY_SAFE_FAILURES and len(tries) < MAX_PROVIDER_TRIES
        ):
            scheduled = RETRY_DELAYS_SECONDS[len(tries) - 1]
            asked = min(max(settlement.retry_after_seconds, 0.0), RETRY_AFTER_CAP_SECONDS)
            return PageProgress(
                None,
                tuple(attempts),
                next_ordinal=ordinal,
                next_try=len(tries) + 1,
                delay_seconds=max(scheduled, asked),
            )
        return PageProgress(RepairOutcome.CALL_FAILED, tuple(attempts))
    return PageProgress(RepairOutcome.STILL_DEGENERATE, tuple(attempts))


def build_ledger(
    journal: LocalJournal,
    pages: Sequence[PageToRecognise],
    reader: AnswerReader,
    *,
    model: str,
    base_snapshot_id: str,
    generated_at: str,
) -> RepairLedger:
    """The repair ledger the journal implies. Pure: no call, no database, no clock."""
    repairs = []
    for page in pages:
        progress = page_progress(journal, page, reader, model=model)
        outcome = progress.outcome or RepairOutcome.NOT_ATTEMPTED
        repairs.append(
            PageRepair(
                document_slug=page.document_slug,
                block_id=page.block_id,
                page_label=page.page_label,
                original_sha256=page.original_sha256,
                original_characters=len(page.original_text),
                crop_sha256=page.crop_sha256,
                outcome=outcome,
                replacement=progress.replacement if outcome is RepairOutcome.REPAIRED else None,
                attempts=progress.attempts,
            )
        )
    return ledger_of(base_snapshot_id, generated_at, repairs)


def charged_for(journal: LocalJournal, page: PageToRecognise, model: str) -> Decimal:
    total = Decimal(0)
    for call in _page_calls(journal, page, model):
        if call.settlement is not None:
            total += call.settlement.charged_usd
    return money(total)


class DurableRepairRunner:
    """Runs pages through ``transport`` with every try journaled first.

    ``fault`` is called with a named point after each durable step; tests raise there to
    simulate a kill. ``clock`` returns an ISO timestamp; ``sleep`` waits between tries.
    """

    def __init__(
        self,
        *,
        journal: LocalJournal,
        store: CallStore,
        transport: RepairTransport,
        clock: Callable[[], str],
        sleep: Callable[[float], None] = time.sleep,
        ceiling_usd: Decimal = CEILING_USD,
        fault: Callable[[str], None] = _no_fault,
    ) -> None:
        rate_for(transport.model)  # refuses a stub or an unpriced model before anything
        if journal.header is None or journal.header.get("model") != transport.model:
            raise JournalRefused("the journal is not open for this transport's model")
        self.journal = journal
        self.store = store
        self.transport = transport
        self.model = transport.model
        self.clock = clock
        self.sleep = sleep
        self.ceiling = money(ceiling_usd)
        self.fault = fault
        self.dispatched = 0
        self._unknown_streak = 0
        self._prepared: dict[tuple[str, str], PreparedRequest] = {}

    # --- reconciliation -----------------------------------------------------------------

    def reconcile(self) -> ReconcileReport:
        """Bring the database and the file to one state before anything is dispatched."""
        report = ReconcileReport(dropped_torn_tail=self.journal.dropped_torn_tail)
        rows = {row.call_id: row for row in self.store.all_calls()}
        foreign = sorted(set(rows) - set(self.journal.calls))
        if foreign:
            raise JournalRefused(
                f"intent_missing_from_file: the database holds {len(foreign)} repair call(s) "
                f"this journal never recorded (first: {foreign[0]}). The file is written "
                "before the database, so this journal is not the one that ran them; refusing "
                "to start"
            )
        for call in list(self.journal.calls.values()):
            self._reconcile_call(call, rows.get(call.intent.call_id), report)
        return report

    def _reconcile_call(self, call: JournalCall, row: Any, report: ReconcileReport) -> None:
        intent = call.intent
        call_id = intent.call_id
        if row is None:
            # Lost (or never committed) in the database: carried forward from the file.
            self.store.insert_prepared(intent)
            report.restored_rows += 1
            row = self.store.get(call_id)
        elif row.identity() != intent.identity():
            raise JournalRefused(f"{call_id}: the database row and the journal intent differ")

        if call.response_sha256 is not None:
            if row.state is CallState.PREPARED:
                self.journal.read_response(call_id, call.response_sha256)
                self.store.checkpoint(call_id, call.response_sha256)
                report.forwarded_effects += 1
                row = self.store.get(call_id)
            elif row.response_sha256 != call.response_sha256:
                raise JournalRefused(f"{call_id}: two different checkpointed responses")
        elif row.response_sha256 is not None:
            self.journal.append_response(call_id, row.response_sha256, self.clock())
            report.file_forwarded += 1

        if call.settlement is not None:
            if not row.state.terminal:
                self.store.settle(call_id, call.settlement)
                report.forwarded_effects += 1
                row = self.store.get(call_id)
            elif not row.settlement.same_outcome(call.settlement):
                raise JournalRefused(f"{call_id}: the database and the file settled it differently")
            return

        if row.state is CallState.PREPARED:
            if self.journal.has_response(call_id):
                raw = self.journal.read_response(call_id, None)
                sha = hashlib.sha256(raw).hexdigest()
                self.store.checkpoint(call_id, sha)
                self.journal.append_response(call_id, sha, self.clock())
                report.recovered_bodies += 1
                row = self.store.get(call_id)
            else:
                settlement = Settlement(
                    state=CallState.OUTCOME_UNKNOWN,
                    charged_usd=intent.bound_usd,
                    failure=Failure.RECONCILED_UNKNOWN,
                )
                self.store.settle(call_id, settlement)
                self.journal.append_settled(call_id, settlement, self.clock())
                report.reconciled_unknown += 1
                return
        if row.state is CallState.RESPONSE_RECEIVED:
            self._complete(intent, self.journal.read_response(call_id, row.response_sha256))
            report.completed_from_checkpoint += 1
            return
        if row.state.terminal:
            self.journal.append_settled(call_id, row.settlement, self.clock())
            report.file_forwarded += 1

    # --- one call -----------------------------------------------------------------------

    def _prepare(self, page: PageToRecognise) -> PreparedRequest:
        key = (page.block_id, page.crop_sha256)
        prepared = self._prepared.get(key)
        if prepared is None:
            prepared = self.transport.prepare(page)
            self._prepared[key] = prepared
        return prepared

    def _next_attempt_number(self, page: PageToRecognise) -> int:
        numbers = [c.intent.attempt_number for c in _page_calls(self.journal, page, self.model)]
        return max(numbers, default=0) + 1

    def _call(self, page: PageToRecognise, ordinal: int, try_number: int) -> Settlement:
        prepared = self._prepare(page)
        bound = unknown_outcome_bound(
            self.model, pixels=prepared.pixels, max_output_tokens=prepared.max_output_tokens
        )
        charged = self.store.charged_total()
        if charged + bound > self.ceiling:
            raise RunStopped(
                StopReason.CEILING,
                f"charged {charged} + this call's bound {bound} would pass the "
                f"{self.ceiling} ceiling; the remaining pages are NOT_ATTEMPTED",
            )
        intent = CallIntent(
            call_id=str(NormRepairCallId.new()),
            document_slug=page.document_slug,
            block_anchor=page.block_id,
            page_label=page.page_label,
            crop_sha256=page.crop_sha256,
            request_sha256=prepared.request_sha256,
            model=self.model,
            attempt_number=self._next_attempt_number(page),
            ordinal=ordinal,
            try_number=try_number,
            bound_usd=bound,
            prepared_at=self.clock(),
        )
        self.journal.append_intent(intent)
        self.fault("intent_appended")
        self.store.insert_prepared(intent)
        self.fault("row_committed")

        failure: CallFailure | None = None
        self.dispatched += 1
        try:
            self.transport.dispatch(
                prepared,
                call_id=intent.call_id,
                checkpoint=lambda raw: self._checkpoint(intent, raw),
            )
        except CallFailure as raised:
            failure = raised
        self.fault("dispatched")

        row = self.store.get(intent.call_id)
        if row is None:
            raise JournalRefused(f"{intent.call_id}: the committed row disappeared")
        if row.state is CallState.RESPONSE_RECEIVED:
            settlement = self._complete(
                intent, self.journal.read_response(intent.call_id, row.response_sha256)
            )
        elif row.state is CallState.PREPARED:
            settlement = self._unanswered(intent, failure)
            self._settle(intent, settlement)
        else:
            raise JournalRefused(f"{intent.call_id}: settled behind the runner's back")
        self._after(settlement)
        return settlement

    def _checkpoint(self, intent: CallIntent, raw: bytes) -> None:
        """The response, made durable before a byte of it is parsed."""
        sha = self.journal.write_response(intent.call_id, raw)
        self.fault("response_written")
        self.store.checkpoint(intent.call_id, sha)
        self.fault("checkpoint_committed")
        self.journal.append_response(intent.call_id, sha, self.clock())
        self.fault("response_appended")

    def _unanswered(self, intent: CallIntent, failure: CallFailure | None) -> Settlement:
        if failure is None:
            return Settlement(
                CallState.OUTCOME_UNKNOWN, intent.bound_usd, failure=Failure.NO_ANSWER_BODY
            )
        if failure.failure in (Failure.CREDENTIAL_REFUSED, Failure.REQUEST_REFUSED):
            return Settlement(CallState.NOT_PROCESSED, money(0), failure=failure.failure)
        if failure.retry_safe:
            return Settlement(
                CallState.NOT_PROCESSED,
                money(0),
                failure=failure.failure,
                retry_after_seconds=failure.retry_after_seconds,
            )
        return Settlement(CallState.OUTCOME_UNKNOWN, intent.bound_usd, failure=failure.failure)

    def _complete(self, intent: CallIntent, raw: bytes) -> Settlement:
        """Price and accept (or refuse) a checkpointed answer. Never dispatches."""
        try:
            answer = self.transport.read_answer(raw)
        except UnreadableAnswer as unreadable:
            settlement = Settlement(
                CallState.COMPLETED,
                unreadable.cost_usd if unreadable.cost_usd is not None else intent.bound_usd,
                cost_usd=unreadable.cost_usd,
                failure=Failure.UNREADABLE,
            )
        else:
            answered = (answer.model or "").strip()[:200] or None
            if answer.cost_usd is None:
                settlement = Settlement(
                    CallState.COMPLETED,
                    intent.bound_usd,
                    response_model=answered,
                    failure=Failure.UNPRICED,
                )
            else:
                cost = money(answer.cost_usd)
                settlement = Settlement(
                    CallState.COMPLETED,
                    cost,
                    cost_usd=cost,
                    response_model=answered,
                    failure=None if answered == intent.model else Failure.MODEL_MISMATCH,
                )
        self._settle(intent, settlement)
        return settlement

    def _settle(self, intent: CallIntent, settlement: Settlement) -> None:
        self.store.settle(intent.call_id, settlement)
        self.fault("settled_committed")
        self.journal.append_settled(intent.call_id, settlement, self.clock())
        self.fault("settled_appended")

    def _after(self, settlement: Settlement) -> None:
        if settlement.failure in _RUN_STOPPING:
            raise RunStopped(settlement.failure, _RUN_STOPPING[settlement.failure])
        if settlement.state is CallState.OUTCOME_UNKNOWN:
            self._unknown_streak += 1
            if self._unknown_streak >= MAX_CONSECUTIVE_UNKNOWN:
                raise RunStopped(
                    StopReason.PROXY_UNAVAILABLE,
                    f"{self._unknown_streak} calls in a row ended outcome_unknown; each is "
                    "counted at its bound and none is re-paid",
                )
        else:
            self._unknown_streak = 0
        charged = self.store.charged_total()
        if charged > self.ceiling:
            raise RunStopped(StopReason.CEILING, f"charged {charged} passed {self.ceiling}")

    # --- pages --------------------------------------------------------------------------

    def run(self, pages: Sequence[PageToRecognise]) -> RunSummary:
        """Every page to an outcome, or a :class:`RunStopped` on a rule."""
        for page in pages:
            while True:
                progress = page_progress(self.journal, page, self.transport, model=self.model)
                if progress.finished:
                    break
                if progress.delay_seconds:
                    self.sleep(progress.delay_seconds)
                self._call(page, progress.next_ordinal, progress.next_try)
            self.fault("page_done")
        return self.summary(pages)

    def summary(self, pages: Sequence[PageToRecognise], stop: str | None = None) -> RunSummary:
        outcomes: dict[str, int] = {}
        finished = 0
        for page in pages:
            progress = page_progress(self.journal, page, self.transport, model=self.model)
            outcome = progress.outcome or RepairOutcome.NOT_ATTEMPTED
            finished += progress.finished
            outcomes[outcome.value] = outcomes.get(outcome.value, 0) + 1
        return RunSummary(
            pages=len(pages),
            finished_pages=finished,
            dispatched_calls=self.dispatched,
            charged_usd=self.store.charged_total(),
            stop=stop,
            outcomes=outcomes,
        )

    def sample(
        self, pages: Sequence[PageToRecognise], area_of: Callable[[PageToRecognise], float]
    ) -> dict[str, Any]:
        """`R-95`: the three largest crops, live, then the projection and its verdict.

        The verdict is appended to the journal. Above the ceiling the run stops with
        :data:`StopReason.SAMPLE_ABOVE_CEILING` for the owner's decision.
        """
        if self.journal.sample_verdict is not None:
            verdict = self.journal.sample_verdict
        else:
            chosen = sorted(
                pages, key=lambda p: (-area_of(p), p.document_slug, p.block_id)
            )[:SAMPLE_SIZE]
            if not chosen:
                raise RunStopped(StopReason.NO_SAMPLE_VERDICT, "there are no pages to sample")
            self.run(chosen)
            total = sum((charged_for(self.journal, page, self.model) for page in chosen), Decimal(0))
            mean = money(total / len(chosen))
            projected = money(mean * len(pages) * SAMPLE_MARGIN)
            verdict = {
                "sample_blocks": [page.block_id for page in chosen],
                "sample_charged_usd": str(money(total)),
                "mean_usd": str(mean),
                "pages": len(pages),
                "margin": str(SAMPLE_MARGIN),
                "projected_usd": str(projected),
                "ceiling_usd": str(self.ceiling),
                "decision": SAMPLE_PROCEED if projected <= self.ceiling else SAMPLE_STOP,
            }
            self.journal.append_sample_verdict(verdict, self.clock())
        if verdict["decision"] != SAMPLE_PROCEED and not self.journal.owner_decisions:
            raise RunStopped(
                StopReason.SAMPLE_ABOVE_CEILING,
                f"the sample projects {verdict['projected_usd']} for {verdict['pages']} pages "
                f"against {verdict['ceiling_usd']}; the run stops for the owner's decision (K-8)",
            )
        return verdict

    def full(self, pages: Sequence[PageToRecognise]) -> RunSummary:
        verdict = self.journal.sample_verdict
        if verdict is None:
            raise RunStopped(
                StopReason.NO_SAMPLE_VERDICT, "the full run needs the sample's verdict first"
            )
        if int(verdict["pages"]) != len(pages):
            raise JournalRefused(
                f"the sample was projected over {verdict['pages']} pages and this run has "
                f"{len(pages)}; the corpus is not the one sampled"
            )
        if verdict["decision"] != SAMPLE_PROCEED and not self.journal.owner_decisions:
            raise RunStopped(
                StopReason.SAMPLE_ABOVE_CEILING,
                f"the sample projected {verdict['projected_usd']}; no owner decision is recorded",
            )
        return self.run(pages)
