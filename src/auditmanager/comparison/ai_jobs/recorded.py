"""Recorded mode for the tests of every C2 lane (`CMP-AI-JOBS-01`, plan `A-6`, wave brief rule 1).

No lane makes a live model call: its tests run the handler against a :class:`RecordedAnswers`, an in-memory recorded adapter that
serves a prepared answer **by the digest of the request** (``ModelRequest.request_sha256``, the checksum of the exact body that
would have gone to the provider -- the key ``analysis.text.recorded.RecordedAdapter`` uses for its committed files). A prompt edit,
another image or another parameter is another digest, so an answer is never replayed against a question it does not answer.

Properties it shares with the committed-file adapter, on purpose:

* ``provider_mode`` is a class constant (``RECORDED``): the mode the spend journal records comes from the object that produced the
  reply, so a replay cannot be presented as a live call -- and the spend wrapper journals it ``unmetered``, spends nothing and
  needs no consent;
* a request with no prepared answer is **never** a call to anything: it raises ``analysis_input_invalid`` (``recording_missing``).
  There is no client, no credential and no network code here, so "fall back to live" cannot be switched on by an edit.

The database side of recorded mode -- an executor connection routed to a work kind -- is test setup and lives with the tests:
``tests/integration/comparison/ai_jobs/ai_jobs_support.py`` (``recorded_route``).
"""

from __future__ import annotations

from typing import Final

from auditmanager.analysis.public import ModelRequest, ModelResponse, ProviderMode
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["RecordedAnswers"]

_STAGE: Final[str] = "text_analysis"


class RecordedAnswers:
    """A recorded model adapter holding prepared answers keyed by request digest. Every request it is asked is kept in
    ``requests`` (and its digest in ``digests``), so a test can assert what was -- and was not -- sent."""

    #: Read-only class constant: no caller can make a replay claim to be a live call.
    _PROVIDER_MODE: Final[ProviderMode] = ProviderMode.RECORDED

    def __init__(self) -> None:
        self._answers: dict[str, ModelResponse] = {}
        self.requests: list[ModelRequest] = []

    @property
    def provider_mode(self) -> ProviderMode:
        return type(self)._PROVIDER_MODE

    @property
    def digests(self) -> list[str]:
        return [request.request_sha256 for request in self.requests]

    @property
    def calls(self) -> int:
        return len(self.requests)

    def record(
        self, request: ModelRequest | str, output_text: str, *, input_tokens: int = 100, output_tokens: int = 50,
        stop_reason: str = "end_turn", latency_ms: int = 1,
    ) -> str:
        """Prepare the answer to ``request`` (or to a digest) and answer the digest it is filed under."""
        key = request if isinstance(request, str) else request.request_sha256
        self._answers[key] = ModelResponse(
            output_text=output_text, stop_reason=stop_reason, input_tokens=input_tokens, output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
        return key

    def has_answer(self, request: ModelRequest | str) -> bool:
        return (request if isinstance(request, str) else request.request_sha256) in self._answers

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        try:
            return self._answers[request.request_sha256]
        except KeyError:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID, message="no recorded model response is available for this request",
                stage_id=_STAGE, reason="recording_missing",
            ) from None
