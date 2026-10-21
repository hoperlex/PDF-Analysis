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

Six ways a corpus fails to answer, one code
-------------------------------------------
A recording can be absent, filed under a key it does not declare, written at an
unsupported version, declare a different model, be malformed, or be present in two
searched directories at once. All six are the same fact about the same local
corpus: **the corpus this adapter was given does not answer this request**, and no
second attempt at the same request can change that. All of them therefore report
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

Section recordings (`W59-ANALYSIS-SETTINGS-01`)
-----------------------------------------------
A run routed to a section's own text profile sends that profile's system prompt, so its
request key differs from every AR key and from every other section's key. Recordings for
those requests live one directory per section under ``fixtures/recorded/sections/``. The
adapter built **without** a directory -- the one the composition root serves -- searches
the canonical AR directory and then each section directory; an adapter given a directory
reads that directory alone, exactly as before. The key alone decides which file answers,
so no directory can answer another profile's request: a different prompt is a different
key. A key found in more than one searched directory is refused as
``recording_ambiguous`` rather than answered from whichever directory came first. Every
section recording carries an ``origin`` block declaring it **synthetic** -- authored to
prove routing, never a model's reply -- and none of them counts as field evidence for a
profile's review.
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
#: One sub-directory per section whose text profile has synthetic recordings.
SECTION_RECORDINGS_RELPATH: Final[str] = "fixtures/recorded/sections"
RECORDING_VERSION: Final[str] = "1.0.0"
#: Field names a recording may never carry, at its top level or in its ``origin``.
_MODE_FIELDS: Final[frozenset[str]] = frozenset({"provider_mode", "mode"})


def default_recording_dir() -> Path:
    return _REPO_ROOT / RECORDINGS_RELPATH


def default_section_recordings_root() -> Path:
    return _REPO_ROOT / SECTION_RECORDINGS_RELPATH


def default_recording_dirs() -> tuple[Path, ...]:
    """The canonical directory, then every section directory, in name order.

    Plain files (a README, the builder) and names starting with ``_`` or ``.`` are not
    section directories and are skipped. A missing sections root adds nothing.
    """
    root = default_section_recordings_root()
    sections: tuple[Path, ...] = ()
    if root.is_dir():
        sections = tuple(
            sorted(
                (
                    entry
                    for entry in root.iterdir()
                    if entry.is_dir() and not entry.name.startswith(("_", "."))
                ),
                key=lambda entry: entry.name,
            )
        )
    return (default_recording_dir(), *sections)


def recording_document(
    *,
    request: ModelRequest,
    output_text: str,
    stop_reason: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    note: str,
    origin: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a recording for ``request``. The only supported way to add one.

    Deliberately has no ``provider_mode`` parameter and writes no such field. ``origin``
    (optional, written only when given) says where the reply came from -- the section
    recordings declare ``kind: synthetic`` there; it may not name a provider mode either.
    """
    document: dict[str, Any] = {
        "recording_version": RECORDING_VERSION,
        "request_sha256": request.request_sha256,
        "model_id": request.model_id,
        "stop_reason": stop_reason,
        "output_text": output_text,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "latency_ms": latency_ms,
        "note": note,
    }
    if origin is not None:
        if _MODE_FIELDS & set(origin):
            raise ValueError("a recording's origin cannot carry a provider mode")
        document["origin"] = dict(origin)
    return document


class RecordedAdapter:
    """Replays committed responses. Holds no client and no credential."""

    #: Read-only class constant. Not a constructor argument and not settable, so no
    #: caller and no configuration can make a replay claim to be a live call.
    _PROVIDER_MODE: Final[ProviderMode] = ProviderMode.RECORDED

    __slots__ = ("_directory", "_directories")

    def __init__(self, recording_dir: Path | None = None) -> None:
        # No directory: the canonical one plus the section recordings (module note). A
        # directory: that directory alone, as every variant and every suite relies on.
        self._directories: tuple[Path, ...] = (
            default_recording_dirs() if recording_dir is None else (recording_dir,)
        )
        self._directory = self._directories[0]

    @property
    def provider_mode(self) -> ProviderMode:
        return type(self)._PROVIDER_MODE

    @property
    def recording_dir(self) -> Path:
        """The canonical directory (or the one directory this adapter was given)."""
        return self._directory

    @property
    def recording_dirs(self) -> tuple[Path, ...]:
        """Every directory this adapter searches, canonical first."""
        return self._directories

    def path_for(self, request_sha256: str) -> Path:
        return self._directory / f"{request_sha256}.json"

    def complete(self, request: ModelRequest) -> ModelResponse:
        key = request.request_sha256
        found = [
            path
            for path in (directory / f"{key}.json" for directory in self._directories)
            if path.is_file()
        ]
        if len(found) > 1:
            # Two answers to one question, chosen between by directory order, would be a
            # silent pick. The corpus is defective; it says so.
            raise self._corrupt("recording_ambiguous")
        try:
            if not found:
                raise FileNotFoundError(key)
            raw = found[0].read_text(encoding="utf-8")
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
        return self._response_from(
            json.loads(raw), expected_key=key, expected_model_id=request.model_id
        )

    def _response_from(
        self, document: Mapping[str, Any], *, expected_key: str, expected_model_id: str
    ) -> ModelResponse:
        if document.get("recording_version") != RECORDING_VERSION:
            raise self._corrupt("recording_version_unsupported")
        if document.get("request_sha256") != expected_key:
            # A recording filed under a key it does not declare is not a provider
            # outage; it is a corrupt fixture, and replaying it would answer the
            # wrong question with a straight face.
            raise self._corrupt("recording_key_mismatch")
        if document.get("model_id") != expected_model_id:
            raise self._corrupt("recording_model_mismatch")
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
