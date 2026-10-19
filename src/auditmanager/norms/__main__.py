"""The re-recognition runner: the only place in this context that spends money.

`R-19` re-recognises the pages whose text is the recognition model's own reasoning. `R-106`
(`W54-PLAN.md` §3.3) puts every paid call through the durable repair journal
(:mod:`auditmanager.norms.repair_journal`): a local fsynced file first, the
``norm_repair_call`` row second, the dispatch third. This module composes that journal with
the LLM proxy, and it is deliberately the only file in `auditmanager.norms` that knows a
provider exists.

    # what it would read, render and bound, with no call, no database and no credential
    PYTHONPATH=src .venv/bin/python -m auditmanager.norms repair plan \\
        --corpus <drop> --model claude-opus-5

    # the priced sample (R-95): the three largest crops, then the projection and its verdict
    PYTHONPATH=src .venv/bin/python -m auditmanager.norms repair sample \\
        --corpus <drop> --sums <SHA256SUMS> --journal-dir .local/norms/repairs

    # the full run, only after a `proceed` verdict or a recorded owner decision
    PYTHONPATH=src .venv/bin/python -m auditmanager.norms repair full \\
        --corpus <drop> --sums <SHA256SUMS> --journal-dir .local/norms/repairs

    # the ledger the journal implies, and the journal against the database
    ... repair ledger --corpus <drop> --journal-dir <dir> --out <ledger.json>
    ... repair status --journal-dir <dir>

    # `R-137`: the same pages re-read in a Claude Code session instead of through the proxy
    ... repair session-prepare --corpus <drop> --sums <SHA256SUMS> --session-dir <dir>
    ... repair session-ledger --corpus <drop> --sums <SHA256SUMS> --session-dir <dir> \\
        --model <session model> --transcribed-at <iso> --out <ledger.json>

``sample`` and ``full`` read ``DATABASE_URL`` (the promotion database) and the three
``PROXY_LLM_*`` values from the process environment. Exit status: 0 done, 2 refused before
anything was spent, 3 stopped on a rule (the ceiling, the sample stop, a refused answer).

**The credential is read from the process environment and from nowhere else.** Not from a
path this module knows, not from a lane `.env`, and it is never printed — not into the
journal, not into an error, not into the summary. `D-42` measured `docker compose config`
printing such a value in clear; the same care applies.

**Refusals before a single call.** A proxy URL with no host (``ProxySettings`` accepts
``http://:59990``); a model that is a stub or is not on the rate card (an unknown outcome
could not be bounded); a crop that differs from the operator's ``SHA256SUMS``; a corpus that
is not the journal's base snapshot; a journal the database does not agree with.

**The checkpoint is taken inside the transport.** The W53 proxy adapter reads the body and
parses it in one method. The opener this module hands it wraps the HTTP response so the
complete 200 body is written to the journal — bytes to disk, row to ``response_received`` —
*before* the adapter parses a byte of it. Replays parse the stored bytes through the same
adapter with a stored-response opener, so the live and the replayed answer are read by one
parser and no replay opens a connection.

The legacy flat form (``--corpus --ledger [--dry-run]``) is kept for the dry run; its live
form still refuses (``durable_call_journal_required``) and names the commands above.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import struct
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Self

from auditmanager.norms.corpus_source import (
    DropSums,
    DropSumsInvalid,
    crop_path,
    degenerate_pages,
    read_drop_sums,
    snapshot_of,
)
from auditmanager.norms.repair_journal import (
    CEILING_USD,
    CallFailure,
    DurableRepairRunner,
    Failure,
    JournalRefused,
    LocalJournal,
    ModelNotPriced,
    PreparedRequest,
    RunStopped,
    SqlCallStore,
    UnreadableAnswer,
    build_ledger,
    ledger_document,
    money,
    rate_for,
    unknown_outcome_bound,
)
from auditmanager.norms.repair_journal.pricing import OUTPUT_TOKEN_CEILING
from auditmanager.norms.rerecognition import (
    RECOGNITION_SYSTEM_PROMPT,
    PageToRecognise,
    RecognisedPage,
)
from auditmanager.norms.session_repair import (
    ReadsOutstanding,
    SessionRefused,
    prepare_session,
    session_ledger,
)

#: `R-29`'s first stopping condition, kept for the legacy dry run's report only. The paid
#: run's ceiling is `R-106`'s cumulative $10 (:data:`CEILING_USD`) and is not an argument.
DEFAULT_CEILING_USD: float = 5.00

#: The render resolution for a crop. 150 dpi over an A4 page is 1241×1754, which is what the
#: original recognition pass worked from and is enough for the 8 pt footnotes in these norms.
RENDER_DPI: int = 150

ENV_BASE_URL = "PROXY_LLM_BASE_URL"
ENV_TOKEN = "PROXY_LLM_TOKEN"
ENV_MODEL = "PROXY_LLM_MODEL"
ENV_DATABASE_URL = "DATABASE_URL"

DEFAULT_JOURNAL_DIR = Path(".local/norms/repairs")
LEDGER_FILENAME = "ledger.json"

EXIT_REFUSED = 2
EXIT_STOPPED = 3

_RULING = re.compile(r"^R-[0-9]{1,4}$")


class RunRefused(RuntimeError):
    """The run stopped before spending, and says why in words, never in values."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --- the crop ---------------------------------------------------------------------------


def render_crop_png(crop: bytes, *, dpi: int = RENDER_DPI) -> bytes:
    """One single-page crop PDF, rendered to PNG.

    `pdfplumber` is the repository's pinned PDF library (`OD-01`, MIT over MIT `pdfminer.six`)
    and it already carries the rasteriser. Nothing is added to `pyproject.toml` for this.
    """
    import pdfplumber

    with pdfplumber.open(io.BytesIO(crop)) as document:
        if not document.pages:
            raise RunRefused("a crop carries no page, so there is nothing to re-recognise")
        image = document.pages[0].to_image(resolution=dpi)
        buffer = io.BytesIO()
        image.original.convert("RGB").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def png_pixels(png: bytes) -> int:
    """Width x height from a PNG's IHDR, without decoding the image."""
    if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
        raise RunRefused("a rendered crop is not a PNG")
    width, height = struct.unpack(">II", png[16:24])
    return width * height


def crop_area(page: PageToRecognise) -> float:
    """The crop's page area in PDF points, for `R-95`'s "three largest crops by area"."""
    import pdfplumber

    with pdfplumber.open(io.BytesIO(page.crop)) as document:
        if not document.pages:
            raise RunRefused(f"{page.document_slug}/{page.block_id}: the crop carries no page")
        first = document.pages[0]
        return float(first.width) * float(first.height)


def recognition_body(png: bytes, *, model: str, max_output_tokens: int) -> dict[str, Any]:
    """The Anthropic-shaped body the proxy adapter translates. A constant prompt (`R-19`)."""
    encoded = base64.b64encode(png).decode("ascii")
    return {
        "model": model,
        "max_tokens": max_output_tokens,
        "system": RECOGNITION_SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                ],
            }
        ],
    }


def verify_crops_against_sums(root: Path, pages: Iterable[PageToRecognise], sums: Path) -> DropSums:
    """Every crop to be paid for, checked against the operator's ``SHA256SUMS`` (step 0).

    The file is ``sha256sum`` output taken over the drop, read by the one parser the bundle
    export also uses (:func:`~auditmanager.norms.corpus_source.read_drop_sums`: lowercase
    digests, a leading ``./`` accepted, a path named twice refused). A crop with no line, or
    with other bytes than its line says, refuses the run before anything is spent. Returns
    the parsed file, whose SHA-256 the journal header and the ledger record (`W54-JUDGE-Y` F3).
    """
    import hashlib

    if not sums.is_file():
        raise RunRefused("no SHA256SUMS file at the path given to --sums")
    try:
        parsed = read_drop_sums(sums)
    except DropSumsInvalid as invalid:
        raise RunRefused(f"{invalid.reason}: {invalid.message}") from None
    for page in pages:
        relative = crop_path(root, page.document_slug, page.block_id).relative_to(root).as_posix()
        expected = parsed.entries.get(relative)
        if expected is None:
            raise RunRefused(f"{page.document_slug}/{page.block_id}: the crop has no SHA256SUMS line")
        if hashlib.sha256(page.crop).hexdigest() != expected:
            raise RunRefused(
                f"{page.document_slug}/{page.block_id}: the crop differs from its SHA256SUMS "
                "line; the drop changed since step 0"
            )
    return parsed


# --- the proxy behind the journal's transport port ----------------------------------------


class _CheckpointingResponse:
    """Wraps one HTTP response so a complete 200 body is checkpointed before it is parsed."""

    def __init__(self, inner: Any, checkpoint: Callable[[bytes], None]) -> None:
        self._inner = inner
        self._checkpoint = checkpoint

    def __enter__(self) -> Self:
        self._inner.__enter__()
        return self

    def __exit__(self, *exc: object) -> Any:
        return self._inner.__exit__(*exc)

    @property
    def status(self) -> int:
        return self._inner.status

    @property
    def headers(self) -> Any:
        return getattr(self._inner, "headers", None)

    def read(self, amount: int | None = None) -> bytes:
        if amount is not None:
            return self._inner.read(amount)
        raw = self._inner.read()
        if self.status == 200:
            self._checkpoint(raw)
        return raw


class _StoredResponse:
    """A checkpointed body served to the adapter as if it had just arrived. No socket."""

    status = 200
    headers = None

    def __init__(self, raw: bytes) -> None:
        self._raw = raw

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self, amount: int | None = None) -> bytes:
        return self._raw if amount is None else self._raw[:amount]


def _usage_cost(raw: bytes) -> Decimal | None:
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeError):
        return None
    usage = document.get("usage") if isinstance(document, dict) else None
    value = usage.get("cost") if isinstance(usage, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return money(value)


def read_proxy_answer(raw: bytes) -> RecognisedPage:
    """Parse a checkpointed proxy body with the W53 adapter's own parser, offline.

    ``model`` is the answer's own ``model`` field (H-6 compares it with the configured one);
    ``cost_usd`` is ``usage.cost`` or ``None``.
    """
    from auditmanager.analysis.public import (
        ModelRequest,
        ProxyAdapter,
        ProxyDispatchError,
        ProxySettings,
    )

    adapter = ProxyAdapter(
        ProxySettings(base_url="http://replay.invalid", token="replay", model="replay"),
        opener=lambda _request, timeout=None: _StoredResponse(raw),
    )
    try:
        response = adapter.complete(
            ModelRequest(model_id="replay", body={"max_tokens": 1, "messages": []})
        )
    except ProxyDispatchError:
        raise UnreadableAnswer(
            "the checkpointed body is not a usable chat-completions answer",
            cost_usd=_usage_cost(raw),
        ) from None
    document = json.loads(raw)
    answered = document.get("model") if isinstance(document, dict) else None
    return RecognisedPage(
        text=response.output_text,
        model=answered if isinstance(answered, str) else "",
        stop_reason=response.stop_reason,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost_usd=response.reported_cost_usd,
    )


class ReplayReader:
    """An :class:`~auditmanager.norms.repair_journal.AnswerReader` for ledger export."""

    def read_answer(self, raw: bytes) -> RecognisedPage:
        return read_proxy_answer(raw)


def _failure_of(error: Any) -> str:
    from auditmanager.shared.errors import ErrorCode

    if error.dispatch_class == "not_sent":
        return Failure.NOT_SENT
    if error.dispatch_class == "rate_limited":
        return Failure.RATE_LIMITED
    if error.dispatch_class == "definite_refusal":
        if error.code is ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED:
            return Failure.CREDENTIAL_REFUSED
        return Failure.REQUEST_REFUSED
    return Failure.OUTCOME_UNKNOWN


class ProxyRepairTransport:
    """The journal's :class:`~auditmanager.norms.repair_journal.RepairTransport` over the proxy.

    ``opener`` is the HTTP opener (``urllib.request.urlopen`` by default); tests inject a
    stub, so no test opens a connection. Each try sends the call's own ``nrc`` id as its
    idempotency scope.
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        model: str,
        max_output_tokens: int = OUTPUT_TOKEN_CEILING,
        dpi: int = RENDER_DPI,
        opener: Callable[..., Any] | None = None,
        render: Callable[[bytes], bytes] | None = None,
    ) -> None:
        from auditmanager.analysis.public import ProxySettings

        self.model = model
        self._settings = ProxySettings(base_url=base_url, token=token, model=model)
        self._max_output_tokens = max_output_tokens
        self._dpi = dpi
        self._opener = opener or urllib.request.urlopen
        self._render = render or (lambda crop: render_crop_png(crop, dpi=self._dpi))

    def prepare(self, page: PageToRecognise) -> PreparedRequest:
        from auditmanager.analysis.public import ModelRequest

        png = self._render(page.crop)
        body = recognition_body(png, model=self.model, max_output_tokens=self._max_output_tokens)
        request = ModelRequest(model_id=self.model, body=body)
        return PreparedRequest(
            request_sha256=request.request_sha256,
            pixels=png_pixels(png),
            max_output_tokens=self._max_output_tokens,
            payload=body,
        )

    def dispatch(
        self, prepared: PreparedRequest, *, call_id: str, checkpoint: Callable[[bytes], None]
    ) -> None:
        from auditmanager.analysis.public import (
            ModelRequest,
            ProxyAdapter,
            ProxyDispatchError,
        )
        from auditmanager.shared.errors import DomainError

        inner = self._opener

        def opener(request: Any, timeout: Any = None) -> _CheckpointingResponse:
            return _CheckpointingResponse(inner(request, timeout=timeout), checkpoint)

        adapter = ProxyAdapter(self._settings, opener=opener)
        try:
            adapter.complete(
                ModelRequest(model_id=self.model, body=prepared.payload, idempotency_scope=call_id)
            )
        except ProxyDispatchError as error:
            failure = _failure_of(error)
            raise CallFailure(
                failure,
                retry_safe=error.retry_safe and failure in (Failure.NOT_SENT, Failure.RATE_LIMITED),
                retry_after_seconds=error.retry_after_seconds,
            ) from None
        except DomainError:
            raise CallFailure(Failure.OUTCOME_UNKNOWN, retry_safe=False) from None

    def read_answer(self, raw: bytes) -> RecognisedPage:
        return read_proxy_answer(raw)


class ProxyPageRecogniser:
    """A :class:`~auditmanager.norms.rerecognition.PageRecogniser` over the LLM proxy.

    Kept for the unjournaled seam :func:`~auditmanager.norms.rerecognition.rerecognise`; the
    paid run never uses it — it goes through :class:`ProxyRepairTransport` and the journal.
    """

    __slots__ = ("_adapter", "_dpi", "_max_output_tokens", "_model")

    def __init__(self, *, base_url: str, token: str, model: str, max_output_tokens: int, dpi: int) -> None:
        from auditmanager.analysis.public import ProxyAdapter, ProxySettings

        self._adapter = ProxyAdapter(ProxySettings(base_url=base_url, token=token, model=model))
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._dpi = dpi

    def recognise(self, page: PageToRecognise) -> RecognisedPage:
        from auditmanager.analysis.public import ModelRequest

        png = render_crop_png(page.crop, dpi=self._dpi)
        body = recognition_body(png, model=self._model, max_output_tokens=self._max_output_tokens)
        response = self._adapter.complete(ModelRequest(model_id=self._model, body=body))
        return RecognisedPage(
            text=response.output_text,
            model=self._model,
            stop_reason=response.stop_reason,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.reported_cost_usd,
        )


def resolve_transport(environment: dict[str, str] | None = None) -> tuple[str, str, str]:
    """The three proxy values, or a refusal that names the missing one and never its value."""
    source = os.environ if environment is None else environment
    base_url = (source.get(ENV_BASE_URL) or "").strip()
    token = (source.get(ENV_TOKEN) or "").strip()
    model = (source.get(ENV_MODEL) or "").strip()

    missing = [
        name
        for name, value in ((ENV_BASE_URL, base_url), (ENV_TOKEN, token), (ENV_MODEL, model))
        if not value
    ]
    if missing:
        raise RunRefused(
            "the provider credential is not in this process's environment: "
            + ", ".join(sorted(missing))
            + " is unset. It is injected for the command and never read from a file here."
        )

    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise RunRefused(
            f"{ENV_BASE_URL} names no host. A URL of the form 'http://:<port>' is accepted by "
            f"ProxySettings, which checks only the scheme, and then fails at call time as a "
            f"transport error that reads like a provider outage. It is a lane pointed at "
            f"nothing, and a paid run does not start against one."
        )
    return base_url, token, model


# --- the repair commands ------------------------------------------------------------------


def _write_json_atomically(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(document, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _session_factory(environment: dict[str, str]) -> Any:
    from sqlalchemy import text

    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine
    from auditmanager.shared.db.session import create_session_factory

    raw = (environment.get(ENV_DATABASE_URL) or "").strip()
    if not raw:
        raise RunRefused(f"{ENV_DATABASE_URL} (the promotion database) is unset")
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    with engine.connect() as connection:
        present = connection.execute(text("SELECT to_regclass('public.norm_repair_call')")).scalar()
    if present is None:
        raise RunRefused(
            "the promotion database has no norm_repair_call table; apply the migration head "
            "(0018 or later) before a paid run"
        )
    return create_session_factory(engine)


def sql_store(environment: dict[str, str]) -> SqlCallStore:
    """The promotion database's ``norm_repair_call``, from ``DATABASE_URL``."""
    return SqlCallStore(_session_factory(environment))


def _pages(corpus: Path) -> list[PageToRecognise]:
    return list(degenerate_pages(corpus))


def _command_plan(args: argparse.Namespace, environment: dict[str, str]) -> int:
    model = (args.model or environment.get(ENV_MODEL) or "").strip()
    rate_for(model)
    pages = _pages(args.corpus)
    bounds: list[Decimal] = []
    areas: list[tuple[float, PageToRecognise]] = []
    for page in pages:
        png = render_crop_png(page.crop, dpi=args.dpi)
        bounds.append(unknown_outcome_bound(model, pixels=png_pixels(png)))
        areas.append((crop_area(page), page))
    sample = sorted(areas, key=lambda item: (-item[0], item[1].document_slug, item[1].block_id))[:3]
    print(
        json.dumps(
            {
                "dry_run": True,
                "model": model,
                "pages": len(pages),
                "base_snapshot": snapshot_of(args.corpus).snapshot_id,
                "ceiling_usd": str(CEILING_USD),
                "max_call_bound_usd": str(max(bounds, default=Decimal(0))),
                "sample_blocks": [page.block_id for _area, page in sample],
                "spent_usd": "0",
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def _open_run(
    args: argparse.Namespace,
    environment: dict[str, str],
    *,
    transport_factory: Callable[..., Any],
    store_factory: Callable[[dict[str, str]], Any],
) -> tuple[DurableRepairRunner, list[PageToRecognise], LocalJournal, str]:
    base_url, token, model = resolve_transport(environment)
    rate_for(model)
    pages = _pages(args.corpus)
    sums = verify_crops_against_sums(args.corpus, pages, args.sums)
    base = snapshot_of(args.corpus).snapshot_id
    if args.base_snapshot and args.base_snapshot != base:
        raise RunRefused(
            f"the corpus is snapshot {base!r}, not the {args.base_snapshot!r} this run names"
        )
    store = store_factory(environment)
    transport = transport_factory(base_url=base_url, token=token, model=model, dpi=args.dpi)
    journal = LocalJournal(args.journal_dir).open(
        base_snapshot=base, model=model, ceiling_usd=CEILING_USD,
        drop_sums_sha256=sums.sha256, now=_now(),
    )
    runner = DurableRepairRunner(journal=journal, store=store, transport=transport, clock=_now)
    return runner, pages, journal, base


def _journal_sums(header: dict[str, Any] | None) -> str:
    """The SHA-256 of the ``SHA256SUMS`` the journal's crops were checked against."""
    value = (header or {}).get("drop_sums_sha256")
    if not isinstance(value, str) or not value:
        raise RunRefused(
            "journal_sums_unrecorded: the journal header records no SHA256SUMS digest, so a "
            "ledger from it could not name the drop its crops came from"
        )
    return value


def _finish(
    runner: DurableRepairRunner,
    pages: Sequence[PageToRecognise],
    base: str,
    journal_dir: Path,
    document: dict[str, Any],
    *,
    write_ledger: bool,
) -> None:
    if write_ledger:
        ledger = build_ledger(
            runner.journal, pages, runner.transport, model=runner.model,
            base_snapshot_id=base, generated_at=_now(),
        )
        _write_json_atomically(
            journal_dir / LEDGER_FILENAME,
            ledger_document(ledger, drop_sums_sha256=_journal_sums(runner.journal.header)),
        )
        document["ledger"] = {
            "path": str(journal_dir / LEDGER_FILENAME),
            "applied": len(ledger.applied),
            "unreliable": ledger.unreliable_count,
        }
    print(json.dumps(document, indent=2, ensure_ascii=False))


def _command_run(
    args: argparse.Namespace,
    environment: dict[str, str],
    *,
    transport_factory: Callable[..., Any] = ProxyRepairTransport,
    store_factory: Callable[[dict[str, str]], Any] | None = None,
) -> int:
    runner, pages, journal, base = _open_run(
        args, environment, transport_factory=transport_factory,
        store_factory=store_factory or sql_store,
    )
    try:
        report = runner.reconcile()
        document: dict[str, Any] = {"stage": args.stage, "reconcile": report.as_document()}
        if args.stage == "full" and args.owner_decision:
            if not _RULING.match(args.owner_decision):
                raise RunRefused("--owner-decision names a ruling, such as R-111")
            verdict = journal.sample_verdict
            recorded = {d.get("ruling") for d in journal.owner_decisions}
            if verdict is not None and args.owner_decision not in recorded:
                journal.append_owner_decision(
                    {"ruling": args.owner_decision, "projected_usd": verdict["projected_usd"]},
                    _now(),
                )
        try:
            if args.stage == "sample":
                document["verdict"] = runner.sample(pages, crop_area)
                summary = runner.summary(pages)
            else:
                summary = runner.full(pages)
        except RunStopped as stopped:
            document["summary"] = runner.summary(pages, stop=stopped.reason).as_document()
            document["stopped"] = str(stopped)
            if journal.sample_verdict is not None and "verdict" not in document:
                document["verdict"] = journal.sample_verdict
            _finish(runner, pages, base, args.journal_dir, document, write_ledger=args.stage == "full")
            return EXIT_STOPPED
        document["summary"] = summary.as_document()
        _finish(runner, pages, base, args.journal_dir, document, write_ledger=args.stage == "full")
        return 0
    finally:
        journal.close()


def _command_ledger(args: argparse.Namespace, _environment: dict[str, str]) -> int:
    journal = LocalJournal(args.journal_dir).open(read_only=True)
    try:
        header = journal.header or {}
        base = snapshot_of(args.corpus).snapshot_id
        if header.get("base_snapshot") != base:
            raise RunRefused("the corpus is not the snapshot this journal was taken against")
        drop_sums = _journal_sums(header)
        ledger = build_ledger(
            journal, _pages(args.corpus), ReplayReader(), model=str(header.get("model")),
            base_snapshot_id=base, generated_at=_now(),
        )
    finally:
        journal.close()
    _write_json_atomically(args.out, ledger_document(ledger, drop_sums_sha256=drop_sums))
    print(json.dumps({"ledger": str(args.out), "applied": len(ledger.applied),
                      "unreliable": ledger.unreliable_count}, indent=2))
    return 0


def _session_drop(args: argparse.Namespace) -> tuple[list[PageToRecognise], DropSums, str]:
    """The pages, the checked sums and the base snapshot, as a session step must see them."""
    pages = _pages(args.corpus)
    sums = verify_crops_against_sums(args.corpus, pages, args.sums)
    base = snapshot_of(args.corpus).snapshot_id
    if args.base_snapshot and args.base_snapshot != base:
        raise RunRefused(
            f"the corpus is snapshot {base!r}, not the {args.base_snapshot!r} this run names"
        )
    return pages, sums, base


def _command_session_prepare(args: argparse.Namespace, _environment: dict[str, str]) -> int:
    pages, sums, base = _session_drop(args)
    try:
        document = prepare_session(
            pages, directory=args.session_dir, base_snapshot=base,
            drop_sums_sha256=sums.sha256, dpi=args.dpi,
            render=lambda crop: render_crop_png(crop, dpi=args.dpi), now=_now(),
        )
    except SessionRefused as refused:
        raise RunRefused(str(refused)) from None
    print(json.dumps({"session": str(args.session_dir), "pages": len(document["pages"]),
                      "base_snapshot": base, "drop_sums_sha256": sums.sha256,
                      "prompt_sha256": document["prompt_sha256"]}, indent=2, ensure_ascii=False))
    return 0


def _command_session_ledger(args: argparse.Namespace, _environment: dict[str, str]) -> int:
    pages, sums, base = _session_drop(args)
    try:
        ledger = session_ledger(
            pages, directory=args.session_dir, base_snapshot=base,
            drop_sums_sha256=sums.sha256, model=args.model,
            transcribed_at=args.transcribed_at, generated_at=_now(), dpi=args.dpi,
            render=lambda crop: render_crop_png(crop, dpi=args.dpi),
        )
    except ReadsOutstanding as owed:
        print(json.dumps({"stopped": owed.reason, "outstanding": [
            {"document_slug": slug, "block_id": block, "read": read}
            for slug, block, read in owed.outstanding
        ]}, indent=2, ensure_ascii=False))
        return EXIT_STOPPED
    except SessionRefused as refused:
        raise RunRefused(str(refused)) from None
    _write_json_atomically(args.out, ledger_document(ledger, drop_sums_sha256=sums.sha256))
    print(json.dumps({"ledger": str(args.out), "repairs": len(ledger.repairs),
                      "applied": len(ledger.applied), "unreliable": ledger.unreliable_count,
                      "unpriced_attempts": ledger.unpriced_attempts}, indent=2))
    return 0


def _command_status(
    args: argparse.Namespace,
    environment: dict[str, str],
    *,
    store_factory: Callable[[dict[str, str]], Any] | None = None,
) -> int:
    journal = LocalJournal(args.journal_dir).open(read_only=True)
    try:
        rows = (store_factory or sql_store)(environment).all_calls()
        by_state: dict[str, int] = {}
        for row in rows:
            by_state[row.state.value] = by_state.get(row.state.value, 0) + 1
        file_ids = set(journal.calls)
        row_ids = {row.call_id for row in rows}
        charged = sum(
            (row.settlement.charged_usd for row in rows if row.settlement is not None), Decimal(0)
        )
        print(
            json.dumps(
                {
                    "header": journal.header,
                    "file_calls": len(file_ids),
                    "database_calls": len(row_ids),
                    "only_in_file": len(file_ids - row_ids),
                    "only_in_database": len(row_ids - file_ids),
                    "states": dict(sorted(by_state.items())),
                    "charged_usd": str(money(charged)),
                    "ceiling_usd": str(CEILING_USD),
                    "sample_verdict": journal.sample_verdict,
                    "owner_decisions": journal.owner_decisions,
                    "dropped_torn_tail": journal.dropped_torn_tail,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    finally:
        journal.close()
    return 0


def repair_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auditmanager.norms repair", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("plan", help="enumerate, render and bound; no call, no database")
    plan.add_argument("--corpus", type=Path, required=True)
    plan.add_argument("--model", default="", help=f"defaults to {ENV_MODEL}")
    plan.add_argument("--dpi", type=int, default=RENDER_DPI)

    for stage in ("sample", "full"):
        run = commands.add_parser(stage)
        run.set_defaults(stage=stage)
        run.add_argument("--corpus", type=Path, required=True)
        run.add_argument("--sums", type=Path, required=True, help="the operator's SHA256SUMS over the drop")
        run.add_argument("--journal-dir", type=Path, default=DEFAULT_JOURNAL_DIR)
        run.add_argument("--base-snapshot", default="", help="refuse unless the corpus is this snapshot")
        run.add_argument("--dpi", type=int, default=RENDER_DPI)
        if stage == "full":
            run.add_argument(
                "--owner-decision", default="",
                help="the ruling that approves a full run the sample stopped (K-8)",
            )

    ledger = commands.add_parser("ledger", help="the ledger the journal implies; no call")
    ledger.add_argument("--corpus", type=Path, required=True)
    ledger.add_argument("--journal-dir", type=Path, default=DEFAULT_JOURNAL_DIR)
    ledger.add_argument("--out", type=Path, required=True)

    status = commands.add_parser("status", help="the journal against the database; no call")
    status.add_argument("--journal-dir", type=Path, default=DEFAULT_JOURNAL_DIR)

    for name, help_text in (
        ("session-prepare", "R-137: render the pages for a session's readers; no call"),
        ("session-ledger", "R-137: the ledger the session's answers imply; no call"),
    ):
        session = commands.add_parser(name, help=help_text)
        session.add_argument("--corpus", type=Path, required=True)
        session.add_argument("--sums", type=Path, required=True, help="the operator's SHA256SUMS over the drop")
        session.add_argument("--session-dir", type=Path, required=True)
        session.add_argument("--base-snapshot", default="", help="refuse unless the corpus is this snapshot")
        session.add_argument("--dpi", type=int, default=RENDER_DPI)
        if name == "session-ledger":
            session.add_argument("--model", required=True, help="the session model's exact identifier")
            session.add_argument("--transcribed-at", required=True, help="when the answers were written (ISO 8601)")
            session.add_argument("--out", type=Path, required=True)
    return parser


def repair_main(argv: list[str], environment: dict[str, str] | None = None) -> int:
    source = dict(os.environ if environment is None else environment)
    args = repair_parser().parse_args(argv)
    if args.command == "plan":
        return _command_plan(args, source)
    if args.command in ("sample", "full"):
        return _command_run(args, source)
    if args.command == "ledger":
        return _command_ledger(args, source)
    if args.command == "session-prepare":
        return _command_session_prepare(args, source)
    if args.command == "session-ledger":
        return _command_session_ledger(args, source)
    return _command_status(args, source)


# --- the legacy flat form -----------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["repair"]:
        return repair_main(arguments[1:])

    parser = argparse.ArgumentParser(prog="auditmanager.norms", description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True, help="the corpus root directory")
    parser.add_argument("--ledger", type=Path, required=True, help="where the repair ledger is written")
    parser.add_argument("--snapshot-id", default="", help="the base corpus snapshot the ledger is taken against")
    parser.add_argument("--ceiling-usd", type=float, default=DEFAULT_CEILING_USD)
    parser.add_argument("--max-output-tokens", type=int, default=8000)
    parser.add_argument("--dpi", type=int, default=RENDER_DPI)
    parser.add_argument("--limit", type=int, default=0, help="stop after this many pages; 0 means all")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="enumerate and render, make no call, spend nothing",
    )
    parser.add_argument("--allow-unpriced", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(arguments)

    pages = degenerate_pages(args.corpus)

    if args.dry_run:
        rendered = 0
        crop_bytes = png_bytes = 0
        for page in pages:
            png = render_crop_png(page.crop, dpi=args.dpi)
            rendered += 1
            crop_bytes += len(page.crop)
            png_bytes += len(png)
            if args.limit and rendered >= args.limit:
                break
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "pages": rendered,
                    "crop_bytes": crop_bytes,
                    "png_bytes": png_bytes,
                    "spent_usd": 0.0,
                },
                indent=2,
            )
        )
        return 0

    raise RunRefused(
        "live re-recognition outside the durable call journal is disabled: "
        "durable_call_journal_required. Use `repair sample` and `repair full`. "
        "No provider transport was constructed and no call was made."
    )


def _entry() -> int:
    try:
        return main()
    except (RunRefused, JournalRefused, ModelNotPriced) as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(_entry())
