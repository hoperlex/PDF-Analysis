"""Promotion's refusal, replay and exact saved-Blob boundary.

The existing W57 pure tests cover ranking and canonical bytes; these tests hold
the new admission/finalization order. PostgreSQL 0023 constraints and the real
S3 dispatcher need the separate lane acceptance named in the task report.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import replace
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from auditmanager.norms.custody import AdmissionState, DeclaredContent
from auditmanager.norms.embedding.profile import EMBEDDING_PROFILE
from auditmanager.norms.retrieval import promotion
from auditmanager.norms.retrieval.artifact import (
    CanonicalBlob, SetIdentity, canonical_json_bytes,
)
from auditmanager.norms.retrieval.candidate import RetrievalCandidate
from auditmanager.norms.retrieval.qualification_decision import DigestComparison
from auditmanager.norms.retrieval.ranking import PromptSelection
from auditmanager.shared.identity import NormRetrievalSetId


SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
DOCUMENT = "ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B"
CHUNKING = "characters-v2:1000"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _prepared(*, matched: bool = True, set_id: str | None = None) -> promotion.PreparedPromotion:
    mapping = canonical_json_bytes({"mapped_document_ids": [DOCUMENT]})
    set_bytes = canonical_json_bytes({"set": "canonical paragraph"})
    catalogue_bytes = canonical_json_bytes({"catalogue": "canonical documents"})
    identity = SetIdentity(
        map_sha256=_sha(mapping), snapshot_id=SNAPSHOT,
        reviewed_content_key="reviewed-drop", embedding_build=f"{EMBEDDING_PROFILE}:{CHUNKING}",
    )
    request = promotion.PromotionRequest(
        set_id=set_id or str(NormRetrievalSetId.new()), identity=identity,
        map_bytes=mapping, reviewed_designations=(), items=(),
        chunking_profile=CHUNKING,
        independently_checked_source_digest="1" * 64,
        independently_checked_embedding_digest="2" * 64,
        expected_set_sha256=_sha(set_bytes) if matched else "3" * 64,
        expected_catalogue_sha256=_sha(catalogue_bytes),
    )
    candidate = RetrievalCandidate(
        retrieval_set=CanonicalBlob(set_bytes, _sha(set_bytes)),
        catalogue=CanonicalBlob(catalogue_bytes, _sha(catalogue_bytes)),
        selection=PromptSelection((), "bounded prompt", 0, False),
        embedding_set_sha256="2" * 64,
    )
    comparison = DigestComparison(
        status="matched" if matched else "rejected",
        expected_set_sha256=request.expected_set_sha256,
        observed_set_sha256=_sha(set_bytes),
        expected_catalogue_sha256=request.expected_catalogue_sha256,
        observed_catalogue_sha256=_sha(catalogue_bytes),
        different_artifacts=() if matched else ("retrieval_set",),
    )
    return promotion.PreparedPromotion(request, candidate, comparison)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE norm_retrieval_set (
                norm_retrieval_set_id text PRIMARY KEY, norms_snapshot_id text,
                map_sha256 text, reviewed_content_key text, chunking_profile text,
                embedding_profile text, builder_version text, state text,
                expected_set_sha256 text, observed_set_sha256 text,
                expected_catalogue_sha256 text, observed_catalogue_sha256 text,
                set_blob_id text, set_size_bytes integer, catalogue_blob_id text,
                catalogue_size_bytes integer, prompt_part_characters integer
            )
        """))
    with Session(engine) as value:
        yield value
    engine.dispose()


def _row_count(session: Session) -> int:
    return session.execute(text("SELECT count(*) FROM norm_retrieval_set")).scalar_one()


def test_wrong_map_digest_refuses_before_any_reader_or_write(monkeypatch: pytest.MonkeyPatch) -> None:
    prepared = _prepared()
    wrong = replace(prepared.request, map_bytes=b"{}")
    monkeypatch.setattr(promotion, "read_snapshot_build_facts", lambda *_a, **_k: pytest.fail("read reached"))
    with pytest.raises(promotion.PromotionRefused, match="map bytes"):
        promotion.prepare_promotion(object(), wrong)  # type: ignore[arg-type]


def test_prepare_reads_only_the_pinned_snapshot_and_compares_canonical_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    calls: list[tuple[str, object]] = []

    def facts(_session: object, **kwargs: object) -> object:
        calls.append(("facts", kwargs))
        return "build-facts"

    def source(_session: object, **kwargs: object) -> object:
        calls.append(("source", kwargs))
        return "source-evidence"

    def windows(_session: object, **kwargs: object) -> object:
        calls.append(("windows", kwargs))
        return "retrieval-windows"

    def assemble(**kwargs: object) -> RetrievalCandidate:
        calls.append(("assemble", kwargs))
        return prepared.candidate

    def compare(**kwargs: object) -> DigestComparison:
        calls.append(("compare", kwargs))
        return prepared.comparison

    monkeypatch.setattr(promotion, "read_snapshot_build_facts", facts)
    monkeypatch.setattr(promotion, "read_snapshot_evidence", source)
    monkeypatch.setattr(promotion, "read_retrieval_windows", windows)
    monkeypatch.setattr(promotion, "assemble_retrieval_candidate", assemble)
    monkeypatch.setattr(promotion, "compare_retrieval_candidate", compare)
    assert promotion.prepare_promotion(object(), prepared.request) == prepared  # type: ignore[arg-type]
    assert [name for name, _kwargs in calls] == [
        "facts", "source", "windows", "assemble", "compare",
    ]
    for name, kwargs in calls[:3]:
        assert kwargs["snapshot_id"] == SNAPSHOT, name
        assert kwargs["expected_content_key"] == "reviewed-drop", name
    assert calls[2][1]["mapped_document_ids"] == (DOCUMENT,)
    assert calls[3][1]["map_bytes"] == prepared.request.map_bytes
    assert calls[4][1]["expected_set_sha256"] == prepared.request.expected_set_sha256


def test_digest_mismatch_records_only_a_rejected_row_and_exact_replay(
    session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared(matched=False)
    changed = _prepared(matched=False, set_id=prepared.request.set_id)
    changed_request = replace(changed.request, expected_set_sha256="4" * 64)
    changed_comparison = replace(changed.comparison, expected_set_sha256="4" * 64)
    changed_prepared = promotion.PreparedPromotion(
        changed_request, changed.candidate, changed_comparison,
    )
    monkeypatch.setattr(promotion, "prepare_promotion", lambda _session, request: (
        prepared if request == prepared.request else changed_prepared
    ))
    first = promotion.record_rejection(session, prepared)
    assert (first.state, first.replayed, _row_count(session)) == ("rejected", False, 1)
    assert promotion.record_rejection(session, prepared).replayed is True
    assert _row_count(session) == 1
    assert session.execute(text("SELECT set_blob_id FROM norm_retrieval_set")).scalar_one() is None
    with pytest.raises(promotion.PromotionRefused, match="reused"):
        promotion.record_rejection(session, changed_prepared)
    assert _row_count(session) == 1


def test_mismatch_and_manifest_refuse_before_any_admission(
    session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(promotion, "admit", lambda *_a, **_k: pytest.fail("admission reached"))
    with pytest.raises(promotion.PromotionRefused, match="mismatched"):
        promotion.admit_matched(session, _prepared(matched=False), manifest=SimpleNamespace())
    matched = _prepared()
    monkeypatch.setattr(promotion, "prepare_promotion", lambda _session, _request: matched)
    manifest = SimpleNamespace(declared=lambda slot: (
        DeclaredContent(matched.comparison.observed_set_sha256,
                        len(matched.candidate.retrieval_set.data), "application/json")
        if slot.role == "norm_retrieval_set" else None
    ))
    with pytest.raises(promotion.PromotionRefused, match="manifest"):
        promotion.admit_matched(session, matched, manifest=manifest)
    assert _row_count(session) == 0


def test_forged_comparison_refuses_before_admission_or_blob_access(
    session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    forged = replace(prepared, comparison=replace(
        prepared.comparison, observed_set_sha256="f" * 64,
    ))
    monkeypatch.setattr(promotion, "admit", lambda *_a, **_k: pytest.fail("admission reached"))
    with pytest.raises(promotion.PromotionRefused, match="comparison digests"):
        promotion.admit_matched(session, forged, manifest=SimpleNamespace())
    store = SimpleNamespace(open_stream=lambda *_a, **_k: pytest.fail("Blob read reached"))
    with pytest.raises(promotion.PromotionRefused, match="comparison digests"):
        promotion.finalize_matched(session, forged, blob_store=store)
    assert _row_count(session) == 0


def test_stale_preparation_refuses_before_any_admission_or_blob_access(
    session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    fresh = replace(prepared, candidate=replace(
        prepared.candidate, selection=PromptSelection((), "changed prompt", 0, False),
    ))
    monkeypatch.setattr(promotion, "prepare_promotion", lambda _session, _request: fresh)
    monkeypatch.setattr(promotion, "admit", lambda *_a, **_k: pytest.fail("admission reached"))
    with pytest.raises(promotion.PromotionRefused, match="differs from pinned"):
        promotion.admit_matched(session, prepared, manifest=SimpleNamespace())
    store = SimpleNamespace(open_stream=lambda *_a, **_k: pytest.fail("Blob read reached"))
    with pytest.raises(promotion.PromotionRefused, match="differs from pinned"):
        promotion.finalize_matched(session, prepared, blob_store=store)
    assert _row_count(session) == 0


def test_unsupported_builder_refuses_before_verified_set_query(
    session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = replace(_prepared().request.identity, builder_version="unknown-builder")
    monkeypatch.setattr(promotion, "verified_for_identity", lambda *_a, **_k: pytest.fail("query reached"))
    with pytest.raises(promotion.PromotionRefused, match="selection identity"):
        promotion.select_verified_retrieval_set(
            session, identity=identity, chunking_profile=CHUNKING,
        )


def test_two_admissions_replay_with_one_stable_set_id(
    session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    monkeypatch.setattr(promotion, "prepare_promotion", lambda _session, _request: prepared)
    expected = {
        role: DeclaredContent(sha, len(data), "application/json")
        for role, _anchor, data, sha in promotion._slots(prepared)
    }
    manifest = SimpleNamespace(declared=lambda slot: expected.get(slot.role))
    admitted: list[tuple[str, str]] = []

    def admit(_session: Session, request: object, *, manifest: object) -> object:
        assert manifest is not None
        admitted.append((request.role, request.target_id))
        return SimpleNamespace(admission=SimpleNamespace(admission_id=f"nad-{request.role}"))

    monkeypatch.setattr(promotion, "admit", admit)
    assert promotion.admit_matched(session, prepared, manifest=manifest) == (
        "nad-norm_retrieval_set", "nad-norm_catalogue",
    )
    assert admitted == [("norm_retrieval_set", prepared.request.set_id),
                        ("norm_catalogue", prepared.request.set_id)]


def test_finalize_requires_both_confirmed_slots_before_blob_read(
    session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    monkeypatch.setattr(promotion, "prepare_promotion", lambda _session, _request: prepared)
    monkeypatch.setattr(promotion, "CustodyRepository", lambda: SimpleNamespace(
        live_in_slot=lambda _session, slot: None if slot.role == "norm_catalogue" else
        SimpleNamespace(state=AdmissionState.CONFIRMED,
                        declared_sha256=prepared.comparison.observed_set_sha256,
                        declared_size_bytes=len(prepared.candidate.retrieval_set.data),
                        media_type="application/json",
                        blob_id=promotion.blob_id_for(
                            prepared.comparison.observed_set_sha256,
                            len(prepared.candidate.retrieval_set.data))),
    ))
    store = SimpleNamespace(open_stream=lambda *_a, **_k: pytest.fail("Blob read reached"))
    with pytest.raises(promotion.PromotionRefused, match="confirmed custody"):
        promotion.finalize_matched(session, prepared, blob_store=store)
    assert _row_count(session) == 0


def test_finalize_checks_saved_bytes_then_inserts_and_replays(
    session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    monkeypatch.setattr(promotion, "prepare_promotion", lambda _session, _request: prepared)
    slots = {
        role: SimpleNamespace(
            state=AdmissionState.CONFIRMED, declared_sha256=sha,
            declared_size_bytes=len(data), media_type="application/json",
            blob_id=promotion.blob_id_for(sha, len(data)),
        )
        for role, _anchor, data, sha in promotion._slots(prepared)
    }
    monkeypatch.setattr(promotion, "CustodyRepository", lambda: SimpleNamespace(
        live_in_slot=lambda _session, slot: slots[slot.role],
    ))
    bindings: list[str] = []
    monkeypatch.setattr(promotion, "publish_bindings", lambda _session, role, _targets: bindings.append(role))
    bytes_by_id = {
        promotion.blob_id_for(sha, len(data)): data
        for _role, _anchor, data, sha in promotion._slots(prepared)
    }
    reads: list[str] = []

    def open_stream(blob_id: object, **_kwargs: object) -> io.BytesIO:
        reads.append(str(blob_id))
        return io.BytesIO(bytes_by_id[str(blob_id)])

    store = SimpleNamespace(open_stream=open_stream)
    set_blob_id = promotion.blob_id_for(
        prepared.comparison.observed_set_sha256,
        len(prepared.candidate.retrieval_set.data),
    )
    bytes_by_id[set_blob_id] = b"poisoned saved bytes"
    with pytest.raises(promotion.PromotionRefused, match="Blob bytes differ"):
        promotion.finalize_matched(session, prepared, blob_store=store)
    assert not bindings and _row_count(session) == 0
    bytes_by_id[set_blob_id] = prepared.candidate.retrieval_set.data
    reads.clear()
    assert promotion.finalize_matched(session, prepared, blob_store=store) == promotion.PromotionOutcome(
        prepared.request.set_id, "verified", False,
    )
    assert bindings == ["norm_retrieval_set", "norm_catalogue"]
    assert _row_count(session) == 1
    assert promotion.finalize_matched(session, prepared, blob_store=store).replayed is True
    assert len(reads) == 4  # both saved objects re-read even on replay
    assert _row_count(session) == 1
