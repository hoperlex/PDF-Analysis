"""Custody rules that need neither PostgreSQL nor S3. They run on every invocation.

* the role table mirrors migration ``0018``'s ``ck_norm_custody_role_shape``, its states and
  its five-try limit, so a role added on one side only reddens here;
* every refusal :func:`admit` can make before touching the database is raised before it
  touches the database (the session below explodes on any use);
* every refusal builds a screened envelope, and every failure classifier the dispatcher can
  record satisfies the column's CHECK;
* the binding digest is order-independent and field-boundary-safe.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path

import pytest

from auditmanager.norms.custody import service as custody_service
from auditmanager.norms.custody.errors import d143_refusal
from auditmanager.norms.public import (
    D143_REASON,
    MAX_ATTEMPTS,
    NORM_SOURCE,
    RETRY_DELAYS_SECONDS,
    ROLE_SHAPES,
    AdmissionRequest,
    AdmissionState,
    BindingDigestEntry,
    CustodyRefused,
    CustodySlot,
    DeclaredContent,
    ManifestIndex,
    admit,
    binding_digest,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import NormDocumentId
from auditmanager.storage import (
    StorageBucketMissingError,
    StorageCredentialRefusedError,
    StorageUnavailableError,
    TemporaryBlobLostError,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = REPOSITORY_ROOT / "db/migrations/versions/20261012_0018_norm_custody.py"
#: ``ck_norm_custody_admission_failure``: the classifier every ``last_failure`` must match.
CLASSIFIER = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
DOCUMENT = str(NormDocumentId.new())
SHA = "a" * 64


def _migration():
    spec = importlib.util.spec_from_file_location("w54_custody_migration_0018", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_role_table_mirrors_the_migrations_role_shape_check() -> None:
    migration = _migration()
    arms = re.findall(
        r"role = '([a-z_]+)' AND target_kind = '([a-z_]+)' "
        r"AND target_id ~ '\^([a-z]+)_[^']*' AND anchor_kind IN \(([^)]*)\)",
        migration.ROLE_SHAPE,
    )
    assert arms, "the migration's ROLE_SHAPE no longer parses; update this mirror test"
    declared = {
        role: (kind, prefix, frozenset(re.findall(r"'([a-z_]+)'", anchors)))
        for role, kind, prefix, anchors in arms
    }
    implemented = {
        role: (shape.target_kind, shape.target_prefix, shape.anchor_kinds)
        for role, shape in ROLE_SHAPES.items()
    }
    assert implemented == declared
    assert tuple(state.value for state in AdmissionState) == migration.ADMISSION_STATES
    assert MAX_ATTEMPTS == migration.ADMISSION_MAX_ATTEMPTS
    assert len(RETRY_DELAYS_SECONDS) == MAX_ATTEMPTS - 1
    assert RETRY_DELAYS_SECONDS[0] == 30 and RETRY_DELAYS_SECONDS[-1] == 2 * 3600


class ExplodingSession:
    """Any database use is a test failure: these refusals precede every statement."""

    def __getattr__(self, name: str):
        raise AssertionError(f"the refusal touched the database ({name})")


def _request(**overrides) -> AdmissionRequest:
    values = dict(
        role=NORM_SOURCE, target_id=DOCUMENT, anchor_kind="pdf", anchor="doc_x",
        sha256=SHA, size=10, media_type="application/pdf",
    )
    values.update(overrides)
    return AdmissionRequest(**values)


def _manifest(request: AdmissionRequest, content: DeclaredContent | None = None) -> ManifestIndex:
    slot = CustodySlot(NORM_SOURCE, "norm_document", request.target_id, request.anchor_kind, request.anchor)
    return ManifestIndex({slot: content or request.content})


@pytest.mark.parametrize(
    ("request_overrides", "manifest_content", "reason"),
    (
        ({"role": "norm_retrieval_set"}, None, "unknown_role"),
        ({"target_id": "doc_not_a_norm_document"}, None, "target_id_malformed"),
        ({"anchor_kind": "page"}, None, "anchor_kind_unknown"),
        ({"anchor": ""}, None, "anchor_malformed"),
        ({"media_type": ""}, None, "media_type_malformed"),
        ({"sha256": "not-a-digest"}, None, "content_malformed"),
        ({}, "absent", "not_in_manifest"),
        ({}, DeclaredContent(sha256="b" * 64, size=10, media_type="application/pdf"), "manifest_mismatch"),
    ),
)
def test_admission_refusals_precede_every_database_statement(
    request_overrides, manifest_content, reason
) -> None:
    request = _request(**request_overrides)
    if manifest_content == "absent":
        manifest = ManifestIndex({})
    else:
        manifest = ManifestIndex({}) if request_overrides.get("anchor") == "" else _manifest(
            request, manifest_content
        )
    with pytest.raises(CustodyRefused) as refused:
        admit(ExplodingSession(), request, manifest=manifest)  # type: ignore[arg-type]
    assert refused.value.reason == reason
    assert refused.value.envelope("cid-custody-offline").error_code is refused.value.code


def test_d143_names_the_debt_and_builds_a_screened_envelope() -> None:
    refusal = d143_refusal()
    envelope = refusal.envelope("cid-d143")
    assert refusal.reason == D143_REASON
    assert envelope.error_code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert "D-143" in envelope.message
    assert envelope.details == {
        "machine": "blob",
        "current_state": "rejected",
        "requested_state": "norm_custody_admission",
    }


def test_the_media_type_conflict_and_slot_reuse_refusals_build_envelopes() -> None:
    conflict = custody_service._media_type_conflict()
    assert conflict.envelope("cid-media").details == {
        "aggregate_type": "Blob",
        "conflict_reason": "media_type_conflict",
    }
    with pytest.raises(CustodyRefused) as reuse:
        custody_service._replay_or_refuse(
            type("Live", (), {"content": DeclaredContent(SHA, 1, "application/pdf")})(),  # type: ignore[arg-type]
            DeclaredContent(SHA, 2, "application/pdf"),
        )
    assert reuse.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert reuse.value.envelope("cid-reuse").details == {"command_type": "norm_custody.admit"}


@pytest.mark.parametrize(
    "failure",
    (
        custody_service._transient_failure(StorageUnavailableError()),
        custody_service._transient_failure(StorageCredentialRefusedError()),
        custody_service._transient_failure(TemporaryBlobLostError()),
        custody_service._transient_failure(StorageBucketMissingError(field="S3_BUCKET", constraint="must_exist")),
        custody_service._transient_failure(OSError("source file vanished")),
        custody_service._domain_failure(DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR)),
        custody_service._domain_failure(DomainError(ErrorCode.STATE_TRANSITION_NOT_ALLOWED)),
        "media_type_conflict",
        "object_unverifiable",
        "canonical_object_missing",
        "blob_not_publishable",
        ErrorCode.INTERNAL_ERROR.value,
    ),
)
def test_every_failure_classifier_satisfies_the_columns_check(failure: str) -> None:
    assert CLASSIFIER.fullmatch(failure), failure


def test_a_rejected_blob_row_found_at_dispatch_is_classified_as_d143() -> None:
    assert custody_service._domain_failure(
        DomainError(ErrorCode.STATE_TRANSITION_NOT_ALLOWED)
    ) == D143_REASON


def _entry(**overrides) -> BindingDigestEntry:
    values = dict(
        role=NORM_SOURCE, target_kind="norm_document", target_id=DOCUMENT,
        blob_id="blob_" + "0" * 26, anchor_kind="pdf", anchor="doc_x",
    )
    values.update(overrides)
    return BindingDigestEntry(**values)


def test_the_binding_digest_is_order_independent_and_boundary_safe() -> None:
    a, b = _entry(anchor="doc_a"), _entry(anchor="doc_b", anchor_kind="crop")
    assert binding_digest([a, b]) == binding_digest([b, a])
    expected = hashlib.sha256(
        "".join(
            sorted(
                "\x1f".join((e.role, e.target_kind, e.target_id, e.blob_id, e.anchor_kind, e.anchor)) + "\n"
                for e in (a, b)
            )
        ).encode()
    ).hexdigest()
    assert binding_digest([a, b]) == expected
    # Moving characters across a field boundary changes the digest.
    assert binding_digest([_entry(anchor_kind="pdf", anchor="x")]) != binding_digest(
        [_entry(anchor_kind="pdfx", anchor="")]
    )
    assert binding_digest([]) == hashlib.sha256(b"").hexdigest()
