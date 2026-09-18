"""`D-18`: two opposite blob faults, and the envelope that could not tell them apart.

`W18-OPS` measured it. `BlobAttributeConflictError` (*stop — the instance was restored
wrong*) and `TemporaryBlobLostError` (*retry the upload*) both raised ``conflict`` with
``aggregate_type: "Blob"``. `conflict`'s ``safe_detail_keys`` are
``["aggregate_type", "expected_revision"]``, so ``blob_id``, ``role`` and ``media_type``
were screened off; and the message went too, because
:func:`auditmanager.shared.errors.build` renders the *catalog's* summary rather than the
class's own sentence. The two envelopes were **byte-identical apart from
``correlation_id``** — same status, same code, same message, same details, ``retryable:
false`` on both — for two situations calling for opposite operator responses.

Owner ruling `R-8` of 2026-09-18 settled it with a second code rather than a wider key
set, and the reason is the one this file asserts: **a detail key cannot fix
``retryable``**. That flag is read from the catalog for the reported code and from nowhere
else, so two situations sharing a code share its value whatever details they carry.

**These tests pin the envelope, not the code name**, which is `W16-ERR`'s `D-12` lesson:
the lie there was the ``retryable`` flag, and a test that had only checked the class's
``code`` attribute would have watched it sail past. Every assertion below is on the bytes
that leave the edge.
"""

from __future__ import annotations

import json

from auditmanager.ingest.failures import domain_error_from_storage
from auditmanager.api.routers.errors import envelope_response
from auditmanager.shared.errors import ErrorCode
from auditmanager.storage.errors import (
    BlobAttributeConflictError,
    TemporaryBlobLostError,
)

_CID_A = "cid-w20-attribute-conflict"
_CID_B = "cid-w20-staged-upload-lost"


def _envelope(exc: Exception, correlation_id: str) -> tuple[int, dict]:
    """The bytes the edge would send, through the shipped mapping and nothing else."""
    response = envelope_response(domain_error_from_storage(exc), correlation_id)
    return response.status_code, json.loads(response.body)


def _attribute_conflict() -> tuple[int, dict]:
    return _envelope(
        BlobAttributeConflictError(
            blob_id="blb_01J0000000000000000000000",
            role="source_document",
            media_type="application/pdf",
        ),
        _CID_A,
    )


def _staged_upload_lost() -> tuple[int, dict]:
    return _envelope(TemporaryBlobLostError(), _CID_B)


# ---------------------------------------------------------------------------
# The defect, and that it is gone
# ---------------------------------------------------------------------------


def test_the_two_envelopes_differ_in_more_than_the_correlation_id() -> None:
    """`D-18`'s exact measurement, inverted.

    Before `R-8` the only key on which these two disagreed was ``correlation_id``. The
    assertion is written that way on purpose: it is the measurement `W18-OPS` made, and
    it reddens again the moment anything puts them back on one code.
    """
    status_a, a = _attribute_conflict()
    status_b, b = _staged_upload_lost()

    differing = {key for key in set(a) | set(b) if a.get(key) != b.get(key)}
    assert differing - {"correlation_id"}, (
        "the two envelopes are byte-identical apart from correlation_id -- D-18 is back"
    )
    assert {"error_code", "message", "retryable"} <= differing
    assert status_a != status_b


def test_an_operator_reads_stop_from_one_and_retry_from_the_other() -> None:
    """The flag is the whole point, and it is the thing a detail key could not have fixed."""
    status_a, a = _attribute_conflict()
    status_b, b = _staged_upload_lost()

    assert a["error_code"] == "conflict"
    assert a["retryable"] is False
    assert status_a == 409

    assert b["error_code"] == "staged_upload_lost"
    assert b["retryable"] is True
    assert status_b == 503


def test_retryable_is_the_catalogs_and_not_the_call_sites() -> None:
    """Neither envelope's flag is set here; both are read from the catalog for the code.

    ``build`` takes no ``retryable`` argument at all, so this asserts the consequence
    rather than the mechanism.
    """
    _, a = _attribute_conflict()
    _, b = _staged_upload_lost()
    assert a["retryable"] is ErrorCode.CONFLICT.retryable
    assert b["retryable"] is ErrorCode.STAGED_UPLOAD_LOST.retryable
    assert ErrorCode.CONFLICT.retryable is not ErrorCode.STAGED_UPLOAD_LOST.retryable


def test_neither_envelope_carries_a_location_or_the_callers_own_declaration() -> None:
    """The split did not widen what leaves the edge.

    `conflict` still screens off ``blob_id``, ``role`` and ``media_type`` -- the class
    is constructed with all three above and the envelope carries none of them -- and the
    new code carries only the stable dependency class name.
    """
    _, a = _attribute_conflict()
    _, b = _staged_upload_lost()

    assert a.get("details") == {"aggregate_type": "Blob"}
    assert b.get("details") == {"dependency": "blob_storage"}
    for body in (a, b):
        rendered = json.dumps(body)
        for forbidden in ("blb_01J", "application/pdf", "source_document", "bucket", "://"):
            assert forbidden not in rendered, (body, forbidden)


def test_conflict_with_aggregate_type_blob_now_means_exactly_one_thing() -> None:
    """The half of `D-18` that keeps `conflict` is the only storage error that carries it."""
    import inspect

    from auditmanager.storage import errors as storage_errors

    carrying = sorted(
        name
        for name, member in vars(storage_errors).items()
        if inspect.isclass(member)
        and issubclass(member, storage_errors.StorageError)
        and getattr(member, "code", None) == "conflict"
    )
    assert carrying == ["BlobAttributeConflictError"], carrying


# ---------------------------------------------------------------------------
# Shown able to fail
# ---------------------------------------------------------------------------


def test_the_comparison_reddens_when_the_two_share_a_code() -> None:
    """The pre-`R-8` world, reconstructed, so the assertion above is not vacuous.

    Both errors are rendered through ``conflict``, exactly as they were until `R-8`, and
    the envelopes come back differing in ``correlation_id`` and nothing else. If this ever
    stops reproducing the defect, the test above has stopped meaning anything.
    """
    from auditmanager.shared.errors import DomainError

    before_a = json.loads(
        envelope_response(DomainError(ErrorCode.CONFLICT, aggregate_type="Blob"), _CID_A).body
    )
    before_b = json.loads(
        envelope_response(DomainError(ErrorCode.CONFLICT, aggregate_type="Blob"), _CID_B).body
    )
    differing = {
        key for key in set(before_a) | set(before_b) if before_a.get(key) != before_b.get(key)
    }
    assert differing == {"correlation_id"}, (
        "the pre-R-8 shape no longer reproduces D-18; this proof is stale"
    )
