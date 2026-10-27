"""The model seam of the comparison summary, with a recorded implementation (`COMPARE-PERSISTED-SUMMARY-01`, B2).

``comparison`` takes other contexts only through their ports, so the seam is this context's own small
protocol, in the shape of the text-profile and AR v3 adapters it mirrors:

* ``provider_mode`` is a **class constant** of the implementation, exposed read-only. It is not a
  constructor argument and not something derived from configuration, so a recording cannot present
  itself as a live call: the mode written with a stored summary comes from the object that actually
  produced the reply.
* :class:`RecordedSummaryModel` replays a committed reply, **keyed by the digest of the exact request
  body** (instructions, prompt version, response schema and the input including its digest). A
  different input or prompt is a different key. A missing file is an explicit refusal and never a call:
  the class holds no client, no credential and no network code, so "fall back to live" is not a
  thing a later edit can switch on by accident; it would have to be written from scratch.

The live implementation is **not wired in this wave** and no live call is made or tested (`R-29`):
the composition root offers this seam only a recorded implementation, and a process that is not in
recorded mode answers the command with ``dependency_unavailable``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Mapping, Protocol, runtime_checkable

from auditmanager.comparison.summary_prompt import SummaryRequest
from auditmanager.shared.errors import DomainError, ErrorCode

#: ``src/auditmanager/comparison/summary_model.py`` -> repository root.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORDINGS_RELPATH: Final[str] = "fixtures/recorded/comparison"
RECORDING_VERSION: Final[str] = "1.0.0"
STAGE_ID: Final[str] = "comparison_summary"
MODE_RECORDED: Final[str] = "recorded"
MODEL_IDENTITY_RECORDED: Final[str] = "recorded"
#: Field names a recording may never carry, at its top level or in its ``origin``.
_MODE_FIELDS: Final[frozenset[str]] = frozenset({"provider_mode", "mode", "model_identity"})


def default_recording_dir() -> Path:
    return _REPO_ROOT / RECORDINGS_RELPATH


@dataclass(frozen=True, slots=True)
class SummaryReply:
    """What a model returns. Identical in shape for a recorded and (later) a live implementation."""

    output_text: str
    input_tokens: int
    output_tokens: int


@runtime_checkable
class SummaryModel(Protocol):
    """The seam. ``provider_mode`` and ``model_identity`` are read-only properties; ``unmetered``
    says the implementation reports no cost of its own (the recorded binding only)."""

    @property
    def provider_mode(self) -> str: ...

    @property
    def model_identity(self) -> str: ...

    @property
    def unmetered(self) -> bool: ...

    def complete(self, request: SummaryRequest) -> SummaryReply: ...


def recording_document(
    *, request: SummaryRequest, output_text: str, input_tokens: int, output_tokens: int,
    note: str, origin: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a recording for ``request``. The only supported way to add one.

    Deliberately has no ``provider_mode`` parameter and writes no such field.
    """
    document: dict[str, Any] = {
        "recording_version": RECORDING_VERSION,
        "request_sha256": request.request_sha256,
        "input_sha256": request.input_sha256,
        "output_text": output_text,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "note": note,
    }
    if origin is not None:
        if _MODE_FIELDS & set(origin):
            raise ValueError("a recording's origin cannot carry a provider mode")
        document["origin"] = dict(origin)
    return document


def _refusal(reason: str) -> DomainError:
    """The corpus this model was given does not answer this request; no retry can change that."""
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="no usable recorded model response is available for this request",
        stage_id=STAGE_ID,
        reason=reason,
    )


class RecordedSummaryModel:
    """Replays committed replies. Holds no client and no credential."""

    __slots__ = ("_directory",)

    #: Read-only class constants. Not constructor arguments and not settable.
    _PROVIDER_MODE: Final[str] = MODE_RECORDED
    _MODEL_IDENTITY: Final[str] = MODEL_IDENTITY_RECORDED

    def __init__(self, recording_dir: Path | None = None) -> None:
        self._directory = default_recording_dir() if recording_dir is None else recording_dir

    @property
    def provider_mode(self) -> str:
        return type(self)._PROVIDER_MODE

    @property
    def model_identity(self) -> str:
        return type(self)._MODEL_IDENTITY

    @property
    def unmetered(self) -> bool:
        """A replayed reply costs nothing and carries no amount (the explicit exception of ``D-225``)."""
        return True

    @property
    def recording_dir(self) -> Path:
        return self._directory

    def path_for(self, request_sha256: str) -> Path:
        return self._directory / f"{request_sha256}.json"

    def complete(self, request: SummaryRequest) -> SummaryReply:
        key = request.request_sha256
        path = self.path_for(key)
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            # No recording, no call -- and not a transport failure: it takes a code no retry ladder
            # climbs. The message names no path (the envelope screen forbids one).
            raise _refusal("recording_missing") from None
        try:
            document = json.loads(raw)
        except ValueError:
            raise _refusal("recording_malformed") from None
        if not isinstance(document, dict):
            raise _refusal("recording_malformed")
        if document.get("recording_version") != RECORDING_VERSION:
            raise _refusal("recording_version_unsupported")
        if document.get("request_sha256") != key or document.get("input_sha256") != request.input_sha256:
            # A recording filed under a key it does not declare would answer the wrong question
            # with a straight face.
            raise _refusal("recording_key_mismatch")
        if _MODE_FIELDS & set(document):
            raise _refusal("recording_malformed")
        usage = document.get("usage")
        try:
            return SummaryReply(
                output_text=str(document["output_text"]),
                input_tokens=int(usage["input_tokens"]),
                output_tokens=int(usage["output_tokens"]),
            )
        except (KeyError, TypeError, ValueError):
            raise _refusal("recording_malformed") from None


__all__ = [
    "MODEL_IDENTITY_RECORDED", "MODE_RECORDED", "RECORDINGS_RELPATH", "RECORDING_VERSION",
    "RecordedSummaryModel", "STAGE_ID", "SummaryModel", "SummaryReply", "default_recording_dir",
    "recording_document",
]
