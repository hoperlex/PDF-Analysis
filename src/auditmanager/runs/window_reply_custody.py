"""Custody of a finished text window's reply, so a restarted run does not pay for it again.

`SECTION-CHUNKED-ANALYSIS-01`. A window of a windowed ``text_analysis`` is a provider call like any other,
journaled by the executor's call journal; this module is what keeps its **answer**. The journal records
that the provider answered (a checksum and token counts), not what it said, so without the text a run
killed between two windows could only call the finished window again.

* :meth:`WindowReplyCustody.preserve` runs after the answer is journaled (``response_received``) and before
  the call is completed. It writes the parsed adapter answer, with the call binding, as a private blob
  (the shape of the AR v3 reply blob, role :data:`REPLY_BLOB_ROLE`) and returns the three
  ``model_call.parameters`` that name it. The read-back must equal what was written.
* :meth:`WindowReplyCustody.recover` answers a window key with the saved reply of the finished call that
  carries it (:meth:`~auditmanager.jobs.repository.JobRepository.completed_window_calls`: the call and its
  effect cross-checked, same Job), after verifying the blob byte for byte against the references on the
  ``model_call`` row and the envelope against that call. Any disagreement is a refusal; nothing is guessed
  and no window is called again to make a refusal go away.

The blob is private custody, never a stage artifact: it is not bound, not listed in the stage result and not
read by anything but this module. It leaves the Run's evidence as it was: the answer is untrusted text that
goes through the same parser and the same grounding as a fresh one.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Final, Mapping

from sqlalchemy.orm import Session

from auditmanager.analysis.public import (
    TEXT_WINDOW_PARAM_REPLY_BLOB_ID,
    TEXT_WINDOW_PARAM_REPLY_BLOB_SHA256,
    TEXT_WINDOW_PARAM_REPLY_BLOB_SIZE,
    ModelRequest,
    ModelResponse,
    ProviderMode,
    RecoveredWindow,
    WindowIdentity,
)
from auditmanager.jobs.public import AttemptAuthority, CompletedWindowCall, JobRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, ModelCallId
from auditmanager.storage.public import (
    BlobStore,
    StorageError,
    parse_blob_id,
    parse_blob_role,
)

REPLY_FORMAT: Final[str] = "text-window-reply/1"
REPLY_BLOB_ROLE: Final[str] = "analysis_text_window_reply"
#: A reply is at most the output ceiling's worth of text (16 000 tokens); a megabyte is a wide margin.
MAX_REPLY_BYTES: Final[int] = 1_048_576

_FIELDS: Final[frozenset[str]] = frozenset({
    "format", "run_id", "model_call_id", "provider", "window_key", "window_index",
    "window_count", "first_page", "last_page", "request_sha256", "response_sha256",
    "output_text", "stop_reason", "input_tokens", "output_tokens", "latency_ms",
    "reported_cost_usd", "reported_model",
})


def _refuse(reason: str, message: str = "the saved window reply does not match its completed call") -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID, message=message, stage_id="text_analysis", reason=reason,
    )


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate reply key")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON constant {value}")


class WindowReplyCustody:
    """The executor's :class:`~auditmanager.analysis.public.WindowCustody` for one Attempt of one Run."""

    __slots__ = ("_session", "_jobs", "_authority", "_store", "_mode", "_provider")

    def __init__(
        self,
        *,
        session: Session,
        jobs: JobRepository,
        authority: AttemptAuthority,
        store: BlobStore,
        mode: ProviderMode,
        provider: str,
    ) -> None:
        self._session = session
        self._jobs = jobs
        self._authority = authority
        self._store = store
        self._mode = mode
        self._provider = provider

    # -- preserve --------------------------------------------------------------------------

    def preserve(
        self,
        *,
        model_call_id: Any,
        window: WindowIdentity,
        request: ModelRequest,
        response: ModelResponse,
    ) -> Mapping[str, Any]:
        cost = response.reported_cost_usd
        if cost is not None and (
            isinstance(cost, bool) or not isinstance(cost, (int, float))
            or not math.isfinite(cost) or cost < 0
        ):
            raise _refuse("window_reply_cost_invalid", "the provider returned an invalid cost amount")
        try:
            payload = json.dumps({
                "format": REPLY_FORMAT,
                "run_id": self._authority.run_id,
                "model_call_id": str(model_call_id),
                "provider": self._provider,
                "window_key": window.key,
                "window_index": window.index,
                "window_count": window.count,
                "first_page": window.first_page,
                "last_page": window.last_page,
                "request_sha256": request.request_sha256,
                "response_sha256": response.response_sha256,
                "output_text": response.output_text,
                "stop_reason": response.stop_reason,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
                "reported_cost_usd": cost,
                "reported_model": response.model,
            }, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise _refuse(
                "window_reply_unserialisable", "the provider answer cannot be kept"
            ) from exc
        data = payload.encode("utf-8")
        if len(data) > MAX_REPLY_BYTES:
            raise _refuse(
                "window_reply_too_large", "the provider answer exceeds the window custody limit"
            )
        digest = hashlib.sha256(data).hexdigest()
        try:
            published = self._store.put_blob(
                data, declared_sha256=digest, declared_size=len(data),
                role=parse_blob_role(REPLY_BLOB_ROLE), media_type="application/json",
            )
            unchanged = (
                published.sha256 == digest and published.size == len(data)
                and self._store.read(parse_blob_id(str(published.blob_id)), verify=True) == data
            )
        except StorageError as exc:
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE,
                message="the window reply could not be kept in the private store",
                dependency="blob_storage",
            ) from exc
        if not unchanged:
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR,
                message="the window reply read back differently from what was written",
                blob_id=str(published.blob_id), role=REPLY_BLOB_ROLE,
            )
        return {
            TEXT_WINDOW_PARAM_REPLY_BLOB_ID: str(published.blob_id),
            TEXT_WINDOW_PARAM_REPLY_BLOB_SHA256: digest,
            TEXT_WINDOW_PARAM_REPLY_BLOB_SIZE: len(data),
        }

    # -- recover ---------------------------------------------------------------------------

    def recover(self, key: str) -> RecoveredWindow | None:
        call = self._jobs.completed_window_calls(self._session, self._authority).get(key)
        if call is None:
            return None
        if call.provider_mode != self._mode.value or call.provider != self._provider:
            raise _refuse("window_call_binding_mismatch")
        return RecoveredWindow(
            model_call_id=ModelCallId.parse(call.model_call_id),
            response=self._read(call),
        )

    def _read(self, call: CompletedWindowCall) -> ModelResponse:
        try:
            data = self._store.read(parse_blob_id(call.reply_blob_id), verify=True)
        except (StorageError, IdentityError) as exc:
            raise _refuse("window_reply_unreadable") from exc
        if (
            len(data) != call.reply_blob_size or len(data) > MAX_REPLY_BYTES
            or hashlib.sha256(data).hexdigest() != call.reply_blob_sha256
        ):
            raise _refuse("window_reply_blob_digest_mismatch")
        try:
            document = json.loads(
                data.decode("utf-8"), object_pairs_hook=_unique_pairs,
                parse_constant=_reject_constant,
            )
        except (UnicodeError, ValueError, TypeError) as exc:
            raise _refuse("window_reply_json_invalid") from exc
        if not isinstance(document, dict) or frozenset(document) != _FIELDS:
            raise _refuse("window_reply_envelope_invalid")
        expected = {
            "format": REPLY_FORMAT,
            "run_id": call.run_id,
            "model_call_id": call.model_call_id,
            "provider": call.provider,
            "window_key": call.key,
            "window_index": call.window_index,
            "window_count": call.window_count,
            "first_page": call.first_page,
            "last_page": call.last_page,
            "request_sha256": call.request_sha256,
            "response_sha256": call.response_sha256,
            "input_tokens": call.input_tokens,
            "output_tokens": call.output_tokens,
            "latency_ms": call.latency_ms,
        }
        for field, value in expected.items():
            if document[field] != value or type(document[field]) is not type(value):
                raise _refuse("window_reply_call_binding_mismatch")
        cost = document["reported_cost_usd"]
        model = document["reported_model"]
        if (
            not isinstance(document["output_text"], str)
            or not isinstance(document["stop_reason"], str)
            or (model is not None and not isinstance(model, str))
            or (cost is not None and (
                isinstance(cost, bool) or not isinstance(cost, (int, float))
                or not math.isfinite(cost) or cost < 0
            ))
        ):
            raise _refuse("window_reply_fields_invalid")
        response = ModelResponse(
            output_text=document["output_text"],
            stop_reason=document["stop_reason"],
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            latency_ms=call.latency_ms,
            reported_cost_usd=cost,
            model=model,
        )
        if response.response_sha256 != call.response_sha256:
            raise _refuse("window_reply_response_digest_mismatch")
        if response.truncated != (call.status == "truncated"):
            raise _refuse("window_reply_status_mismatch")
        return response


__all__ = ["MAX_REPLY_BYTES", "REPLY_BLOB_ROLE", "REPLY_FORMAT", "WindowReplyCustody"]
