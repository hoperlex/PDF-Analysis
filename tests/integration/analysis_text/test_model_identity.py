"""`MODEL-IDENTITY-CHECK-01` (`R-133`): a reply from another model than the configured one fails.

In proxy mode the adapter holds the chat-completions reply to the model the installation
configured, when that model is *pinned*. A reply that names another model, or names none, is the
typed stage failure ``model_identity_mismatch``: no finding is published, the usage evidence of
what the call cost is kept, and nothing in the failure carries a model name, the key or the base
URL. A matching reply behaves as it always did, and recorded mode never reads a model at all.

A configured name is pinned unless it is one of the two placeholders the tree already uses,
``proxy`` and ``replay``. For those the check is not applied, and
``ProxyAdapter.identity_pinned`` says so; the placeholder is refused at start-up on the day
`W56A-MODEL-PIN-01` lands, by the bootstrap owner.

Everything here is container-free. The adapter and the stage are the real ones; the proxy is
a local stub and the call journal is a recording double. Every guard below is paired with the
reply that must still pass, because a check that refuses everything would also pass the
negative cases.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Self

import pytest

from auditmanager.analysis.text.adapter import ModelRequest, ModelResponse
from auditmanager.analysis.text.config import ProviderConfig, ProviderMode
from auditmanager.analysis.text.proxy import (
    MODEL_STUBS,
    ProxyAdapter,
    ProxyDispatchError,
    ProxySettings,
    ReceivedResponse,
    _UNPINNED_MODEL_NAMES,
)
from auditmanager.analysis.text.stage import (
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    run_text_analysis,
)
from auditmanager.runs import RETRYABLE_STAGE_ERRORS
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId, RunId
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE

MODEL_ID = "claude-opus-5"
BASE_URL = "https://proxy.example/agent/v1"
TOKEN = "tok-identity-secret"
#: The configured name. A gateway-style slug, because that is what `PROXY_LLM_MODEL` holds.
CONFIGURED = "anthropic/claude-opus-5"
FOREIGN = "openai/gpt-5-mini"
USAGE = {"prompt_tokens": 1200, "completion_tokens": 340, "cost": 0.0402}
REQUEST = ModelRequest(model_id=MODEL_ID, body={"max_tokens": 16, "messages": []})

PAGE = "Отчёт за год. Выручка выросла.\n"
_USABLE_REPLY = json.dumps(
    {
        "observations": [
            {
                "category": "internal_contradiction",
                "finding_text": "Две формулировки о выручке не сходятся.",
                "recommendation_text": "Сверить показатели.",
                "evidence": [{"page_number": 1, "quote": "Выручка выросла"}],
            }
        ]
    },
    ensure_ascii=False,
)


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.status, self._payload = 200, payload

    def read(self, size: int = -1) -> bytes:
        return self._payload if size < 0 else self._payload[:size]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _document(model: Any = CONFIGURED, *, content: str = "{}", usage: Any = USAGE) -> dict[str, Any]:
    """A chat-completions answer; ``model=...`` is left out of it when ``model`` is ``_ABSENT``."""
    document: dict[str, Any] = {
        "id": "chatcmpl-identity",
        "choices": [
            {"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        ],
    }
    if usage is not None:
        document["usage"] = usage
    if model is not _ABSENT:
        document["model"] = model
    return document


_ABSENT: Any = object()


def _raw(document: dict[str, Any]) -> bytes:
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


def _adapter(
    raw: bytes, *, model: str = CONFIGURED, aliases: tuple[str, ...] = ()
) -> ProxyAdapter:
    def answer(_request: Any, timeout: int | None = None) -> _Response:
        return _Response(raw)

    return ProxyAdapter(
        ProxySettings(base_url=BASE_URL, token=TOKEN, model=model, model_aliases=aliases),
        opener=answer,
    )


def _refused(raw: bytes, **settings: Any) -> ProxyDispatchError:
    with pytest.raises(ProxyDispatchError) as caught:
        _adapter(raw, **settings).complete(REQUEST)
    return caught.value


# --- the matching reply passes, unchanged -------------------------------------------------


def test_a_reply_naming_the_configured_model_passes_and_keeps_its_name() -> None:
    response = _adapter(_raw(_document(CONFIGURED, content="{}"))).complete(REQUEST)

    assert response.model == CONFIGURED
    # Everything the adapter returned before this check is exactly what it returns now.
    assert (response.output_text, response.stop_reason) == ("{}", "end_turn")
    assert (response.input_tokens, response.output_tokens) == (1200, 340)
    assert response.reported_cost_usd == 0.0402


# --- another model, or none, is the typed refusal -----------------------------------------


def test_a_reply_naming_another_model_is_a_typed_identity_mismatch_that_keeps_the_usage() -> None:
    raw = _raw(_document(FOREIGN))
    failure = _refused(raw)

    assert failure.code is ErrorCode.MODEL_IDENTITY_MISMATCH
    # An answer arrived, so the call may have been paid: never "not processed", never retried.
    assert failure.dispatch_class == "outcome_unknown"
    assert failure.retry_safe is False
    assert failure.retry_after_seconds == 0.0
    # The evidence of what was spent survives the refusal.
    assert isinstance(failure.received, ReceivedResponse)
    assert (failure.received.input_tokens, failure.received.output_tokens) == (1200, 340)
    assert failure.received.response_sha256 == hashlib.sha256(raw).hexdigest()
    assert failure.received.latency_ms >= 0


@pytest.mark.parametrize(
    "named",
    [
        pytest.param(_ABSENT, id="field absent"),
        pytest.param(None, id="null"),
        pytest.param("", id="empty string"),
        pytest.param(7, id="number"),
        pytest.param(True, id="boolean"),
        pytest.param([CONFIGURED], id="list holding the right name"),
        pytest.param({"name": CONFIGURED}, id="object holding the right name"),
    ],
)
def test_a_reply_that_names_no_model_fails_closed(named: Any) -> None:
    """A reply that does not say which model answered is never read as the configured one."""
    failure = _refused(_raw(_document(named)))

    assert failure.code is ErrorCode.MODEL_IDENTITY_MISMATCH
    assert failure.dispatch_class == "outcome_unknown"
    assert failure.retry_safe is False
    assert failure.received is not None


@pytest.mark.parametrize(
    "variant",
    [
        pytest.param(CONFIGURED.upper(), id="other case"),
        pytest.param(CONFIGURED + "-20260101", id="dated suffix"),
        pytest.param("claude-opus-5", id="without the vendor prefix"),
        pytest.param(" " + CONFIGURED, id="padded"),
        pytest.param(CONFIGURED + "\n", id="trailing newline"),
    ],
)
def test_the_match_is_exact_never_a_prefix_or_a_case_fold(variant: str) -> None:
    failure = _refused(_raw(_document(variant)))
    assert failure.code is ErrorCode.MODEL_IDENTITY_MISMATCH


def test_a_mismatched_reply_without_a_readable_usage_block_is_still_typed() -> None:
    failure = _refused(_raw(_document(FOREIGN, usage=None)))

    assert failure.code is ErrorCode.MODEL_IDENTITY_MISMATCH
    assert failure.dispatch_class == "outcome_unknown"
    assert failure.received is None


# --- aliases ------------------------------------------------------------------------------


def test_a_listed_alias_is_accepted_and_reported_as_the_name_that_answered() -> None:
    dated = CONFIGURED + "-20260101"
    response = _adapter(_raw(_document(dated)), aliases=(dated,)).complete(REQUEST)

    assert response.model == dated


def test_the_configured_name_still_passes_when_aliases_are_listed() -> None:
    dated = CONFIGURED + "-20260101"
    response = _adapter(_raw(_document(CONFIGURED)), aliases=(dated,)).complete(REQUEST)

    assert response.model == CONFIGURED


def test_a_name_that_is_not_listed_is_refused_even_when_aliases_exist() -> None:
    dated = CONFIGURED + "-20260101"
    failure = _refused(_raw(_document(FOREIGN)), aliases=(dated,))

    assert failure.code is ErrorCode.MODEL_IDENTITY_MISMATCH


def test_an_alias_is_matched_exactly_too() -> None:
    dated = CONFIGURED + "-20260101"
    failure = _refused(_raw(_document(dated + "x")), aliases=(dated,))

    assert failure.code is ErrorCode.MODEL_IDENTITY_MISMATCH


def test_a_listed_alias_does_not_rescue_a_reply_that_names_nothing() -> None:
    failure = _refused(_raw(_document(_ABSENT)), aliases=(CONFIGURED + "-20260101",))

    assert failure.code is ErrorCode.MODEL_IDENTITY_MISMATCH


# --- the failure carries no name, key or address ------------------------------------------


def test_the_failure_carries_no_model_name_no_key_and_no_base_url() -> None:
    failure = _refused(_raw(_document(FOREIGN)))
    envelope = json.dumps(failure.envelope("corr-identity").as_dict(), ensure_ascii=False)

    surfaces = {
        "str": str(failure),
        "custom_message": failure.custom_message or "",
        "details": json.dumps(dict(failure.detail_fields)),
        "envelope": envelope,
    }
    for label, text in surfaces.items():
        for secret in (FOREIGN, CONFIGURED, TOKEN, BASE_URL, "proxy.example"):
            assert secret not in text, f"{label} carries {secret!r}"
    # The caller-safe envelope builds: the message passes the catalog's own screen.
    assert json.loads(envelope)["error_code"] == "model_identity_mismatch"
    assert json.loads(envelope)["retryable"] is False


def test_the_reported_name_goes_to_the_log_only_and_bounded(
    caplog: pytest.LogCaptureFixture,
) -> None:
    long_name = "n" * 500
    with caplog.at_level(logging.WARNING, logger="auditmanager.analysis.text.proxy"):
        _refused(_raw(_document(long_name)))

    lines = [r.getMessage() for r in caplog.records if "identity mismatch" in r.getMessage()]
    assert len(lines) == 1
    assert "n" * 40 in lines[0]
    assert "n" * 81 not in lines[0], "an untrusted name was logged without a bound"
    assert TOKEN not in lines[0]
    assert BASE_URL not in lines[0]


def test_a_matching_reply_logs_nothing_about_identity(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="auditmanager.analysis.text.proxy"):
        _adapter(_raw(_document(CONFIGURED))).complete(REQUEST)

    assert not [r for r in caplog.records if "identity" in r.getMessage()]


# --- which configured names are pinned ----------------------------------------------------


def test_the_default_configuration_is_the_unpinned_placeholder() -> None:
    """The model has the default it always had: nothing outside this module had to change."""
    settings = ProxySettings(base_url=BASE_URL, token=TOKEN)

    assert settings.model == "proxy"
    assert settings.model_aliases == ()
    assert ProxyAdapter(settings).identity_pinned is False


@pytest.mark.parametrize("placeholder", sorted(_UNPINNED_MODEL_NAMES))
def test_the_placeholder_names_are_unpinned(placeholder: str) -> None:
    adapter = ProxyAdapter(ProxySettings(base_url=BASE_URL, token=TOKEN, model=placeholder))

    assert adapter.identity_pinned is False


def test_the_placeholder_set_is_exactly_proxy_and_replay() -> None:
    """Both names are used in the tree; a third silently unpinning a model is a defect."""
    assert _UNPINNED_MODEL_NAMES == frozenset({"proxy", "replay"})


@pytest.mark.parametrize(
    "named",
    [CONFIGURED, "claude-opus-5", "default", "auto", "Proxy", "PROXY", "replay2", " proxy", "m"],
)
def test_every_other_configured_name_is_pinned_exactly(named: str) -> None:
    """Exact names only: ``default`` and ``auto`` are held to, and so is ``Proxy``."""
    adapter = ProxyAdapter(ProxySettings(base_url=BASE_URL, token=TOKEN, model=named))

    assert adapter.identity_pinned is True
    failure = _refused(_raw(_document(FOREIGN)), model=named)
    assert failure.code is ErrorCode.MODEL_IDENTITY_MISMATCH


def test_identity_pinned_is_read_only_and_follows_the_settings() -> None:
    adapter = _adapter(_raw(_document()))

    assert adapter.identity_pinned is True
    with pytest.raises(AttributeError):
        adapter.identity_pinned = False  # type: ignore[misc]
    assert adapter.identity_pinned is True


# --- an unpinned model is not checked, and says so ----------------------------------------


@pytest.mark.parametrize("placeholder", sorted(_UNPINNED_MODEL_NAMES))
@pytest.mark.parametrize(
    "named",
    [
        pytest.param(FOREIGN, id="another model"),
        pytest.param(_ABSENT, id="no model field"),
        pytest.param(None, id="null model"),
        pytest.param(7, id="model that is not text"),
    ],
)
def test_an_unpinned_placeholder_passes_whatever_the_reply_names(
    placeholder: str, named: Any
) -> None:
    adapter = _adapter(_raw(_document(named)), model=placeholder)

    response = adapter.complete(REQUEST)

    assert adapter.identity_pinned is False
    # The reply's own name is still evidence on the response, whatever the configuration says.
    assert response.model == (named if isinstance(named, str) else None)
    assert (response.input_tokens, response.output_tokens) == (1200, 340)


@pytest.mark.parametrize(
    "aliases",
    [
        pytest.param([CONFIGURED + "-x"], id="a list, not a tuple"),
        pytest.param(CONFIGURED + "-x", id="a bare string"),
        pytest.param(("",), id="an empty alias"),
        pytest.param(("  ",), id="a blank alias"),
        pytest.param(("ok-name", ""), id="a blank alias after a good one"),
        pytest.param((7,), id="a number"),
        pytest.param((None,), id="null"),
    ],
)
def test_aliases_that_could_accept_any_model_are_refused(aliases: Any) -> None:
    with pytest.raises(DomainError) as caught:
        ProxySettings(base_url=BASE_URL, token=TOKEN, model=CONFIGURED, model_aliases=aliases)

    assert caught.value.code is ErrorCode.INTERNAL_ERROR
    assert "aliases" in str(caught.value)


def test_the_alias_list_is_empty_by_default_and_a_good_tuple_is_kept() -> None:
    assert ProxySettings(base_url=BASE_URL, token=TOKEN, model=CONFIGURED).model_aliases == ()
    kept = ProxySettings(
        base_url=BASE_URL, token=TOKEN, model=CONFIGURED, model_aliases=("a-1", "a-2")
    )
    assert kept.model_aliases == ("a-1", "a-2")


def test_no_model_name_is_refused_by_the_settings() -> None:
    """Refusing a placeholder at start-up is `W56A-MODEL-PIN-01`'s, not this slice's."""
    for name in (*sorted(MODEL_STUBS), "replay", "PROXY", ""):
        assert ProxySettings(base_url=BASE_URL, token=TOKEN, model=name).model == name


# --- the stage: nothing is published, the spend is journalled ------------------------------


class _Journal:
    def __init__(self) -> None:
        self.model_call_id = ModelCallId.new()
        self.calls: list[tuple[str, Any]] = []

    def prepare(self, request: Any, *, mode: ProviderMode) -> ModelCallId:
        self.calls.append(("prepare", mode))
        return self.model_call_id

    def response_received(self, model_call_id: ModelCallId, response: Any) -> None:
        self.calls.append(("response_received", response))

    def complete(self, call: Any) -> None:
        self.calls.append(("complete", call))

    def outcome_unknown(self, model_call_id: ModelCallId, error: Any) -> None:
        self.calls.append(("outcome_unknown", error))

    def not_processed(self, model_call_id: ModelCallId, error: Any, dispatch_class: str) -> None:
        self.calls.append(("not_processed", dispatch_class))


def _text_layer_document() -> dict[str, Any]:
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": len(PAGE),
        "pages": [{"page_number": 1, "char_start": 0, "char_end": len(PAGE), "text": PAGE}],
    }


def _stage(raw: bytes, *, model: str = CONFIGURED) -> tuple[Any, _Journal]:
    journal = _Journal()
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=_text_layer_document(),
        adapter=_adapter(raw, model=model),
        config=ProviderConfig(
            mode=ProviderMode.LIVE, model_id=MODEL_ID, run_cost_ceiling_usd=1.00,
            api_key=None, ceiling_is_explicit=True,
        ),
        call_journal=journal,
        profile=V1_REFERENCE_PROFILE,
    )
    return outcome, journal


def test_a_foreign_model_publishes_no_finding_and_journals_what_was_spent() -> None:
    """The reply is otherwise perfect, grounded and complete: only its author is wrong."""
    raw = _raw(_document(FOREIGN, content=_USABLE_REPLY))
    outcome, journal = _stage(raw)

    assert outcome.status == STATUS_FAILED
    assert outcome.artifact is None, "a finding was published from another model's answer"
    assert outcome.model_calls == ()
    assert outcome.error is not None
    assert outcome.error.code is ErrorCode.MODEL_IDENTITY_MISMATCH
    assert [name for name, _ in journal.calls] == ["prepare", "response_received"]
    evidence = journal.calls[1][1]
    assert (evidence.input_tokens, evidence.output_tokens) == (1200, 340)
    assert evidence.response_sha256 == hashlib.sha256(raw).hexdigest()
    # Spent, so uncertain; and a second attempt would pay again for the same refusal.
    assert outcome.provider_effect_uncertain is True
    assert outcome.provider_retry_allowed is False
    assert outcome.error.code.retryable is False
    assert outcome.error.code not in RETRYABLE_STAGE_ERRORS


def test_a_reply_naming_no_model_publishes_no_finding() -> None:
    outcome, journal = _stage(_raw(_document(_ABSENT, content=_USABLE_REPLY)))

    assert outcome.status == STATUS_FAILED
    assert outcome.artifact is None
    assert outcome.error.code is ErrorCode.MODEL_IDENTITY_MISMATCH
    assert [name for name, _ in journal.calls] == ["prepare", "response_received"]


def test_the_same_reply_from_the_configured_model_still_publishes() -> None:
    """Anti-vacuity: the two stage tests above fail for the author, not for the content."""
    outcome, journal = _stage(_raw(_document(CONFIGURED, content=_USABLE_REPLY)))

    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.error is None
    assert outcome.artifact is not None
    assert [name for name, _ in journal.calls][-1] == "complete"


def test_an_unpinned_placeholder_still_publishes_from_any_model_and_says_so() -> None:
    """The documented gap, pinned so closing it is a deliberate act (`W56A-MODEL-PIN-01`)."""
    raw = _raw(_document(FOREIGN, content=_USABLE_REPLY))

    outcome, _journal = _stage(raw, model="proxy")

    assert outcome.status == STATUS_SUCCEEDED
    assert _adapter(raw, model="proxy").identity_pinned is False


# --- recorded mode never reads a model ----------------------------------------------------


def test_the_recorded_adapter_names_no_model_and_the_stage_is_unchanged(
    text_layer_document: dict[str, Any], recorded_adapter: Any
) -> None:
    from auditmanager.analysis.text import build_request, load_text_layer

    request = build_request(
        model_id=MODEL_ID,
        bundle=V1_REFERENCE_PROFILE.prompt_bundle,
        text_layer=load_text_layer(text_layer_document),
    )
    replayed = recorded_adapter.complete(request)
    assert replayed.model is None

    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=recorded_adapter,
        config=ProviderConfig(
            mode=ProviderMode.RECORDED, model_id=MODEL_ID, run_cost_ceiling_usd=1.00,
            api_key=None, ceiling_is_explicit=True,
        ),
        profile=V1_REFERENCE_PROFILE,
    )
    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.artifact["provider_mode"] == "recorded"


def test_the_response_shape_is_backward_compatible_and_its_checksum_ignores_the_name() -> None:
    old_style = ModelResponse("{}", "end_turn", 1, 2, 3)
    assert old_style.model is None
    assert old_style.reported_cost_usd is None

    named = ModelResponse("{}", "end_turn", 1, 2, 3, None, CONFIGURED)
    assert named.model == CONFIGURED
    # A replay and a proxied answer to one question keep one checksum.
    assert named.response_sha256 == old_style.response_sha256
