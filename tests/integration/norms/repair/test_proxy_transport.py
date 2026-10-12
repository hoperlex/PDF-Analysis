"""The proxy behind the journal: W53's classification, the checkpoint before the parse, the CLI.

Every HTTP answer here comes from a stub opener handed to the transport; the suite's
no-network guard would fail any test that reached ``urllib.request.urlopen``.
"""

from __future__ import annotations

import argparse
import email.message
import hashlib
import io
import json
import urllib.error
from decimal import Decimal
from pathlib import Path
from typing import Any, Self

import pytest

from auditmanager.analysis.public import ProxyDispatchError
from auditmanager.analysis.text import proxy as proxy_module
from auditmanager.norms import __main__ as command
from auditmanager.norms.__main__ import (
    ProxyRepairTransport,
    RunRefused,
    png_pixels,
    read_proxy_answer,
    render_crop_png,
)
from auditmanager.norms.repair_journal import (
    CallFailure,
    CallState,
    DurableRepairRunner,
    Failure,
    LocalJournal,
    UnreadableAnswer,
    unknown_outcome_bound,
)
from tests.integration.norms.repair.support import (
    BASE,
    CLEAN_PAGE,
    DEGENERATE_PAGE,
    MODEL,
    SUMS,
    MemoryStore,
    openai_body,
    page,
)


def minimal_pdf(width: int = 200, height: int = 300) -> bytes:
    """A one-page PDF with an empty page of the given size, written by hand."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] >>".encode(),
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return out.getvalue()


TINY_PNG = render_crop_png(minimal_pdf(20, 30), dpi=72)


class StubResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.headers = email.message.Message()
        self._body = body

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self, amount: int | None = None) -> bytes:
        return self._body if amount is None else self._body[:amount]


class StubOpener:
    """Answers from a list; records each request's headers and body."""

    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)
        self.requests: list[Any] = []

    def __call__(self, request: Any, timeout: Any = None) -> StubResponse:
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        status, body = answer
        if status != 200:
            headers = email.message.Message()
            if isinstance(body, tuple):
                body, retry_after = body
                headers["Retry-After"] = str(retry_after)
            raise urllib.error.HTTPError(
                "https://proxy.invalid/agent/v1/chat/completions", status, "x", headers,
                io.BytesIO(body),
            )
        return StubResponse(status, body)


def _transport(opener: StubOpener) -> ProxyRepairTransport:
    return ProxyRepairTransport(
        base_url="https://proxy.invalid/agent/v1", token="secret-token", model=MODEL,
        opener=opener, render=lambda _crop: TINY_PNG,
    )


def _dispatch(transport: ProxyRepairTransport, call_id: str = "nrc_01HZZZZZZZZZZZZZZZZZZZZZZZ"):
    seen: list[bytes] = []
    prepared = transport.prepare(page())
    try:
        transport.dispatch(prepared, call_id=call_id, checkpoint=seen.append)
    except CallFailure as failure:
        return seen, failure
    return seen, None


# --- classification (W53's, unchanged) -------------------------------------------------------


def test_proxy_dispatch_error_is_on_the_analysis_surface() -> None:
    assert ProxyDispatchError is proxy_module.ProxyDispatchError


def test_the_body_is_checkpointed_before_the_adapter_parses_it(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []
    real = proxy_module._from_openai_response

    def parse(document: Any, latency_ms: int) -> Any:
        order.append("parsed")
        return real(document, latency_ms)

    monkeypatch.setattr(proxy_module, "_from_openai_response", parse)
    raw = openai_body(CLEAN_PAGE)
    transport = _transport(StubOpener((200, raw)))
    prepared = transport.prepare(page())
    transport.dispatch(
        prepared, call_id="nrc_01HZZZZZZZZZZZZZZZZZZZZZZZ",
        checkpoint=lambda body: order.append(f"checkpointed:{hashlib.sha256(body).hexdigest()}"),
    )
    assert order == [f"checkpointed:{hashlib.sha256(raw).hexdigest()}", "parsed"]


def test_an_unparseable_body_is_checkpointed_and_then_classified() -> None:
    seen, failure = _dispatch(_transport(StubOpener((200, b"not json at all"))))
    assert seen == [b"not json at all"]
    assert failure is not None and not failure.retry_safe


def test_a_503_is_ambiguous_and_never_retry_safe() -> None:
    seen, failure = _dispatch(_transport(StubOpener((503, b'{"error": {"code": "x"}}'))))
    assert seen == []
    assert failure.failure == Failure.OUTCOME_UNKNOWN
    assert failure.retry_safe is False


def test_a_429_is_retry_safe_and_carries_retry_after() -> None:
    seen, failure = _dispatch(_transport(StubOpener((429, (b"{}", 30)))))
    assert (failure.failure, failure.retry_safe, failure.retry_after_seconds) == (
        Failure.RATE_LIMITED, True, 30.0,
    )
    assert seen == []


def test_a_refused_connection_is_not_sent_and_a_reset_is_unknown() -> None:
    _, refused = _dispatch(_transport(StubOpener(urllib.error.URLError(ConnectionRefusedError()))))
    assert (refused.failure, refused.retry_safe) == (Failure.NOT_SENT, True)
    _, reset = _dispatch(_transport(StubOpener(urllib.error.URLError(TimeoutError()))))
    assert (reset.failure, reset.retry_safe) == (Failure.OUTCOME_UNKNOWN, False)


@pytest.mark.parametrize(
    ("status", "expected"),
    [(400, Failure.REQUEST_REFUSED), (413, Failure.REQUEST_REFUSED),
     (401, Failure.CREDENTIAL_REFUSED), (403, Failure.CREDENTIAL_REFUSED)],
)
def test_a_definite_refusal_is_named(status: int, expected: str) -> None:
    _, failure = _dispatch(_transport(StubOpener((status, b"{}"))))
    assert (failure.failure, failure.retry_safe) == (expected, False)


def test_each_try_sends_its_own_idempotency_scope() -> None:
    opener = StubOpener((200, openai_body(CLEAN_PAGE)), (200, openai_body(CLEAN_PAGE)))
    transport = _transport(opener)
    _dispatch(transport, "nrc_01HAAAAAAAAAAAAAAAAAAAAAAA")
    _dispatch(transport, "nrc_01HBBBBBBBBBBBBBBBBBBBBBBB")
    keys = [request.get_header("X-idempotency-key") for request in opener.requests]
    assert len(set(keys)) == 2
    assert opener.requests[0].data == opener.requests[1].data


def test_the_request_names_the_configured_model_and_carries_the_crop() -> None:
    opener = StubOpener((200, openai_body(CLEAN_PAGE)))
    _dispatch(_transport(opener))
    body = json.loads(opener.requests[0].data)
    assert body["model"] == MODEL
    assert body["max_tokens"] == 8000
    assert body["messages"][1]["content"][0]["type"] == "image_url"


# --- reading a checkpointed body -------------------------------------------------------------


def test_the_answer_names_its_own_model_and_price() -> None:
    answer = read_proxy_answer(openai_body(CLEAN_PAGE, model="claude-sonnet-5", cost=0.07))
    assert (answer.model, answer.cost_usd, answer.text) == ("claude-sonnet-5", 0.07, CLEAN_PAGE)
    assert read_proxy_answer(openai_body(CLEAN_PAGE, cost=None)).cost_usd is None
    assert read_proxy_answer(openai_body(CLEAN_PAGE, finish_reason="length")).truncated


def test_an_unreadable_body_keeps_its_price_when_usage_has_one() -> None:
    with pytest.raises(UnreadableAnswer) as unreadable:
        read_proxy_answer(b'{"choices": [], "usage": {"cost": 0.04}}')
    assert unreadable.value.cost_usd == Decimal("0.04")


# --- the runner over the real transport ------------------------------------------------------


def test_a_503_through_the_real_transport_is_paid_at_most_once(tmp_path: Path) -> None:
    opener = StubOpener((503, b"{}"))
    transport = _transport(opener)
    store = MemoryStore()
    for _restart in range(2):
        journal = LocalJournal(tmp_path / "j").open(
            base_snapshot=BASE, model=MODEL, ceiling_usd=Decimal(10), drop_sums_sha256=SUMS, now="t"
        )
        runner = DurableRepairRunner(journal=journal, store=store, transport=transport,
                                     clock=lambda: "t", sleep=lambda _s: None)
        runner.reconcile()
        runner.run([page()])
        journal.close()
    assert len(opener.requests) == 1
    (row,) = store.all_calls()
    assert row.state is CallState.OUTCOME_UNKNOWN
    assert row.settlement.charged_usd == unknown_outcome_bound(MODEL, pixels=png_pixels(TINY_PNG))


# --- the command ------------------------------------------------------------------------------

SLUG = "СП_63_13330_2018"
BLOCK = "blk_" + "a" * 32


def _corpus(root: Path, crop: bytes) -> Path:
    document = root / SLUG
    (document / "crops").mkdir(parents=True)
    (document / "results.md").write_text(
        f"""# Document: {SLUG}.pdf

Path: normative/{SLUG}.pdf

Generated: 2026-08-25 09:47:54 UTC

## Page 70

### BLOCK #1 [TEXT]: {BLOCK}

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://example.invalid/crop)

{DEGENERATE_PAGE}
""",
        encoding="utf-8",
    )
    (document / "blocks.json").write_text(json.dumps({"document_id": "doc_1"}), encoding="utf-8")
    (document / "crops" / f"{BLOCK}.pdf").write_bytes(crop)
    (root / "MANIFEST.json").write_text(
        json.dumps({"documents": [{"slug": SLUG, "document_id": "doc_1", "document_name": SLUG,
                                   "doc_type": "СП", "pdf_pages": 70, "blocks_count": 1}]},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    return root


def _sums(path: Path, root: Path, *, tamper: bool = False) -> Path:
    crop = (root / SLUG / "crops" / f"{BLOCK}.pdf").read_bytes()
    digest = hashlib.sha256(crop + (b"x" if tamper else b"")).hexdigest()
    path.write_text(f"{digest}  ./{SLUG}/crops/{BLOCK}.pdf\n", encoding="utf-8")
    return path


def _args(tmp_path: Path, stage: str = "sample", **extra: Any) -> argparse.Namespace:
    values = {
        "stage": stage, "corpus": tmp_path / "corpus", "sums": tmp_path / "SHA256SUMS",
        "journal_dir": tmp_path / "repairs", "base_snapshot": "", "dpi": 72,
        "owner_decision": "",
    }
    values.update(extra)
    return argparse.Namespace(**values)


ENVIRONMENT = {
    "PROXY_LLM_BASE_URL": "https://proxy.invalid/agent/v1",
    "PROXY_LLM_TOKEN": "secret-token",
    "PROXY_LLM_MODEL": MODEL,
}


def _factory(opener: StubOpener):
    def build(**kwargs: Any) -> ProxyRepairTransport:
        return ProxyRepairTransport(opener=opener, **kwargs)

    return build


def test_the_sample_command_runs_through_the_journal_and_prints_no_credential(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _corpus(tmp_path / "corpus", minimal_pdf())
    _sums(tmp_path / "SHA256SUMS", root)
    opener = StubOpener((200, openai_body(CLEAN_PAGE, cost=0.03)))
    store = MemoryStore()
    code = command._command_run(
        _args(tmp_path), ENVIRONMENT, transport_factory=_factory(opener),
        store_factory=lambda _env: store,
    )
    printed = capsys.readouterr().out
    assert code == 0
    assert len(opener.requests) == 1
    assert json.loads(printed)["verdict"]["decision"] == "proceed"
    assert "secret-token" not in printed
    assert "secret-token" not in (tmp_path / "repairs" / "journal.jsonl").read_text(encoding="utf-8")

    code = command._command_run(
        _args(tmp_path, stage="full"), ENVIRONMENT, transport_factory=_factory(opener),
        store_factory=lambda _env: store,
    )
    assert code == 0
    assert len(opener.requests) == 1, "the full run re-paid the sample"
    ledger = json.loads((tmp_path / "repairs" / "ledger.json").read_text(encoding="utf-8"))
    assert [r["outcome"] for r in ledger["repairs"]] == ["repaired"]
    assert ledger["version"] == "2"


def test_a_crop_that_differs_from_its_sums_refuses_before_anything(tmp_path: Path) -> None:
    root = _corpus(tmp_path / "corpus", minimal_pdf())
    _sums(tmp_path / "SHA256SUMS", root, tamper=True)
    opener = StubOpener()
    with pytest.raises(RunRefused, match="differs from its SHA256SUMS"):
        command._command_run(_args(tmp_path), ENVIRONMENT, transport_factory=_factory(opener),
                             store_factory=lambda _env: MemoryStore())
    assert opener.requests == []
    assert not (tmp_path / "repairs").exists()


def test_a_base_snapshot_other_than_the_corpus_refuses(tmp_path: Path) -> None:
    root = _corpus(tmp_path / "corpus", minimal_pdf())
    _sums(tmp_path / "SHA256SUMS", root)
    with pytest.raises(RunRefused, match="not the"):
        command._command_run(
            _args(tmp_path, base_snapshot="2026-01-01..2026-01-01+0d.000000000000"), ENVIRONMENT,
            transport_factory=_factory(StubOpener()), store_factory=lambda _env: MemoryStore(),
        )
    assert not (tmp_path / "repairs").exists()


@pytest.mark.parametrize("model", ["proxy", "gpt-5"])
def test_a_stub_or_unpriced_model_refuses_before_anything(tmp_path: Path, model: str) -> None:
    from auditmanager.norms.repair_journal import ModelNotPriced

    _corpus(tmp_path / "corpus", minimal_pdf())
    with pytest.raises(ModelNotPriced):
        command._command_run(
            _args(tmp_path), dict(ENVIRONMENT, PROXY_LLM_MODEL=model),
            transport_factory=_factory(StubOpener()), store_factory=lambda _env: MemoryStore(),
        )
    assert not (tmp_path / "repairs").exists()


def test_the_plan_command_spends_nothing_and_names_the_sample(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _corpus(tmp_path / "corpus", minimal_pdf())
    code = command.repair_main(["plan", "--corpus", str(tmp_path / "corpus"), "--model", MODEL],
                               environment={})
    printed = json.loads(capsys.readouterr().out)
    assert code == 0
    assert printed["pages"] == 1 and printed["sample_blocks"] == [BLOCK]
    assert printed["spent_usd"] == "0"


def test_the_ledger_command_replays_the_journal_without_a_credential(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _corpus(tmp_path / "corpus", minimal_pdf())
    _sums(tmp_path / "SHA256SUMS", root)
    store = MemoryStore()
    opener = StubOpener((200, openai_body(CLEAN_PAGE, cost=0.03)))
    command._command_run(_args(tmp_path), ENVIRONMENT, transport_factory=_factory(opener),
                         store_factory=lambda _env: store)
    capsys.readouterr()
    out = tmp_path / "export" / "ledger.json"
    code = command.repair_main(
        ["ledger", "--corpus", str(root), "--journal-dir", str(tmp_path / "repairs"),
         "--out", str(out)],
        environment={},
    )
    assert code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["repairs"][0]["outcome"] == "repaired"
