"""The recorded adapter: replay a committed response, keyed by request checksum.

``OD-13`` makes automated suites recorded-only, so this adapter is what every test
runs against and it must be deterministic and offline. Two properties carry that:

* **Keyed by ``request_sha256``.** The key is the checksum of the exact body that
  would have gone to the provider. A prompt edit, a parameter change or a different
  document changes the key, so a stale recording is reported missing rather than
  replayed against a question it does not answer.
* **A missing recording is never a live call.** There is no fallback path in this
  class: it holds no client, no credential and no network code, so "fall back to live"
  is not something a future edit can accidentally switch on - it would have to be
  written from scratch.

Four ways a corpus fails to answer, one code
--------------------------------------------
A recording can be absent, filed under a key it does not declare, written at an
unsupported version, or malformed. All four are the same fact about the same local
directory: **the corpus this adapter was given does not answer this request**, and no
second attempt at the same request can change that. All four therefore report
``analysis_input_invalid`` with a ``recording_*`` reason.

The absent case used to report ``dependency_unavailable`` instead. That code is
``retryable: true`` in the frozen catalog, and :mod:`auditmanager.runs.retry` is right to
ladder it -- for a provider that is unreachable, a second attempt can answer differently.
A file that is not on this disk will not be on this disk in ten seconds, so the ladder
bought three attempts and both pinned backoffs, ``W28-LIVE`` measured the cost at 10.0 s
of a 16.1 s run, and the terminal it reached told an operator to retry a run that cannot
succeed. The policy was behaving correctly on the information it was given; what was
wrong was what this adapter said about itself. The code is the whole of that
classification (``retry.py`` takes it from the catalog and nowhere else), so the code is
where the repair is.

A recording file carries **no provider mode**. The mode is stamped by this adapter's
read-only class constant, so a hand-edited recording cannot present itself as a live
response: there is no field in which to make the claim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final, Mapping

from auditmanager.analysis.text.adapter import ModelRequest, ModelResponse
from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.lock import STAGE_ID
from auditmanager.shared.errors import DomainError, ErrorCode

#: ``src/auditmanager/analysis/text/recorded.py`` -> repository root.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]
RECORDINGS_RELPATH: Final[str] = "fixtures/recorded/text_analysis"
RECORDING_VERSION: Final[str] = "1.0.0"


def default_recording_dir() -> Path:
    return _REPO_ROOT / RECORDINGS_RELPATH


def recording_document(
    *,
    request: ModelRequest,
    output_text: str,
    stop_reason: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    note: str,
) -> dict[str, Any]:
    """Build a recording for ``request``. The only supported way to add one.

    Deliberately has no ``provider_mode`` parameter and writes no such field.
    """
    return {
        "recording_version": RECORDING_VERSION,
        "request_sha256": request.request_sha256,
        "model_id": request.model_id,
        "stop_reason": stop_reason,
        "output_text": output_text,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "latency_ms": latency_ms,
        "note": note,
    }


class RecordedAdapter:
    """Replays committed responses. Holds no client and no credential."""

    #: Read-only class constant. Not a constructor argument and not settable, so no
    #: caller and no configuration can make a replay claim to be a live call.
    _PROVIDER_MODE: Final[ProviderMode] = ProviderMode.RECORDED

    __slots__ = ("_directory",)

    def __init__(self, recording_dir: Path | None = None) -> None:
        self._directory = recording_dir or default_recording_dir()

    @property
    def provider_mode(self) -> ProviderMode:
        return type(self)._PROVIDER_MODE

    @property
    def recording_dir(self) -> Path:
        return self._directory

    def path_for(self, request_sha256: str) -> Path:
        return self._directory / f"{request_sha256}.json"

    def complete(self, request: ModelRequest) -> ModelResponse:
        key = request.request_sha256
        path = self.path_for(key)
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            # No recording, no call - and not a transport failure. An absent file is
            # the fourth way this corpus fails to answer, and it takes the same code
            # and the same reason vocabulary as the other three, so nothing ladders it.
            # The message names no path: the envelope screen forbids one.
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="no recorded model response is available for this request",
                stage_id=STAGE_ID,
                reason="recording_missing",
            ) from None
        return self._response_from(json.loads(raw), expected_key=key)

    def _response_from(
        self, document: Mapping[str, Any], *, expected_key: str
    ) -> ModelResponse:
        if document.get("recording_version") != RECORDING_VERSION:
            raise self._corrupt("recording_version_unsupported")
        if document.get("request_sha256") != expected_key:
            # A recording filed under a key it does not declare is not a provider
            # outage; it is a corrupt fixture, and replaying it would answer the
            # wrong question with a straight face.
            raise self._corrupt("recording_key_mismatch")
        usage = document.get("usage") or {}
        try:
            return ModelResponse(
                output_text=str(document["output_text"]),
                stop_reason=str(document["stop_reason"]),
                input_tokens=int(usage["input_tokens"]),
                output_tokens=int(usage["output_tokens"]),
                latency_ms=int(document["latency_ms"]),
            )
        except (KeyError, TypeError, ValueError):
            raise self._corrupt("recording_malformed") from None

    @staticmethod
    def _corrupt(reason: str) -> DomainError:
        return DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the recorded model response is not usable",
            stage_id=STAGE_ID,
            reason=reason,
        )
