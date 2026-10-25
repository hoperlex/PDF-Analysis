"""The promotion command against real PostgreSQL 0023 custody and a real S3-compatible store.

Unlike ``test_retrieval_set_promotion.py`` this does not substitute preparation: one tiny
snapshot (one document, two reliable paragraphs, one chunk, one embedding window, a confirmed
source PDF binding) is seeded so the real readers, the real set builder and the real catalogue
builder produce the bytes. It proves persistence mechanics and the command's exit statuses
only; the snapshot is synthetic and is not a reviewed or qualified normative corpus.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import InternalError

from auditmanager.norms.custody import (
    NORM_CATALOGUE,
    NORM_RETRIEVAL_SET,
    NORM_SOURCE,
    CustodyDispatcher,
    admit,
    publish_bindings,
    report,
    requeue,
)
from auditmanager.norms.embedding import vectors
from auditmanager.norms.embedding.digest import EmbeddingSetDigest
from auditmanager.norms.embedding.profile import DIMENSIONS, EMBEDDING_PROFILE
from auditmanager.norms.retrieval import promote_cli, promotion
from auditmanager.norms.retrieval.artifact import SetIdentity, canonical_json_bytes
from auditmanager.shared.db import reset_session_factory, session_scope
from auditmanager.shared.db.engine import dispose_engine
from auditmanager.shared.identity import (
    NormDocumentId,
    NormParagraphId,
    NormRetrievalSetId,
    NormsSnapshotId,
)

from .conftest import CustodyKit

CHUNKING = "characters-v2:1200"
SLUG = "synthetic_slug"
SOURCE_REF = "synthetic-source"
PARAGRAPHS = (
    "Минимальная ширина прохода в чистоте составляет 1,2 м.",
    "Двери эвакуационных выходов открываются по направлению выхода из здания.",
)
VECTOR = vectors.pack([1.0] + [0.0] * (DIMENSIONS - 1))
WATCHED = (
    "norm_retrieval_set", "norm_custody_admission", "norm_custody_binding", "blob", "audit_event",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Seed:
    snapshot: str
    key: str
    document: str
    content_digest: str
    embedding_digest: str


def _seed(kit: CustodyKit) -> Seed:
    """The smallest snapshot the real W57a readers accept, plus its PDF custody binding."""
    for paragraph in PARAGRAPHS:
        assert unicodedata.normalize("NFC", paragraph) == paragraph
    snapshot = str(NormsSnapshotId.new())
    key = f"synthetic-promote-cli-{snapshot[-12:].lower()}"
    document = str(NormDocumentId.new())
    joined = "\n".join(PARAGRAPHS)
    window = EmbeddingSetDigest(
        content_key=key, chunking_profile=CHUNKING, embedding_profile=EMBEDDING_PROFILE,
    )
    window.add_values(
        SOURCE_REF, 0, window_ordinal=0, token_count=10, char_offset=0, char_length=len(joined),
        paragraph_ordinal_first=0, paragraph_ordinal_last=1,
        input_sha256="c" * 64, embedding_sha256=vectors.sha256(VECTOR),
    )
    embedding_digest = window.hexdigest()
    with session_scope(kit.session_factory) as session:
        session.execute(text(
            "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
            "content_digest, undated_documents, document_count, segmentation_profile) "
            "VALUES (:snapshot, :key, :key, :digest, 0, 1, 'markdown-v1')"
        ), {"snapshot": snapshot, "key": key, "digest": "a" * 64})
        document_pk = session.execute(text(
            "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, "
            "source_document_ref, slug, title, doc_type, source_attribution, "
            "pdf_page_count, block_count, page_heading_count, recognised_characters, "
            "paragraph_count) VALUES (:document, :snapshot, :ref, :slug, "
            "'Synthetic document', 'СП', 'unattributed', 1, 2, 0, :length, 2) "
            "RETURNING norm_document_pk"
        ), {"document": document, "snapshot": snapshot, "ref": SOURCE_REF, "slug": SLUG,
            "length": len(joined)}).scalar_one()
        offset = 0
        for ordinal, body in enumerate(PARAGRAPHS):
            session.execute(text(
                "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, "
                "norm_document_pk, ordinal, page_label, block_ref, char_offset, char_length, "
                "kind, text) VALUES (:paragraph, :snapshot, :document_pk, :ordinal, 1, "
                ":block, :offset, :length, 'body', :body)"
            ), {"paragraph": str(NormParagraphId.new()), "snapshot": snapshot,
                "document_pk": document_pk, "ordinal": ordinal, "block": f"block-{ordinal}",
                "offset": offset, "length": len(body), "body": body})
            offset += len(body) + 1
        session.execute(text(
            "INSERT INTO norm_chunk_build (norms_snapshot_id, chunking_profile, "
            "target_characters, chunk_count) VALUES (:snapshot, :chunking, 1200, 1)"
        ), {"snapshot": snapshot, "chunking": CHUNKING})
        chunk_pk = session.execute(text(
            "INSERT INTO norm_chunk (norms_snapshot_id, norm_document_pk, chunking_profile, "
            "ordinal, page_first, page_last, char_offset, char_length, "
            "paragraph_ordinal_first, paragraph_ordinal_last, paragraph_count, "
            "contains_clause, text, content_sha256) VALUES (:snapshot, :document_pk, "
            ":chunking, 0, 1, 1, 0, :length, 0, 1, 2, false, :body, :sha) "
            "RETURNING norm_chunk_pk"
        ), {"snapshot": snapshot, "document_pk": document_pk, "chunking": CHUNKING,
            "length": len(joined), "body": joined, "sha": _sha(joined.encode())}).scalar_one()
        session.execute(text(
            "INSERT INTO norm_embedding_build (norms_snapshot_id, chunking_profile, "
            "embedding_profile, chunk_count, window_count, embedding_set_sha256) "
            "VALUES (:snapshot, :chunking, :embedding, 1, 1, :sha)"
        ), {"snapshot": snapshot, "chunking": CHUNKING, "embedding": EMBEDDING_PROFILE,
            "sha": embedding_digest})
        session.execute(text(
            "INSERT INTO norm_embedding (norms_snapshot_id, norm_chunk_pk, chunking_profile, "
            "embedding_profile, window_ordinal, token_count, char_offset, char_length, "
            "paragraph_ordinal_first, paragraph_ordinal_last, input_sha256, embedding_sha256, "
            "embedding) VALUES (:snapshot, :chunk, :chunking, :embedding, 0, 10, 0, :length, "
            "0, 1, :input_sha, :embedding_sha, CAST(:vector AS vector))"
        ), {"snapshot": snapshot, "chunk": chunk_pk, "chunking": CHUNKING,
            "embedding": EMBEDDING_PROFILE, "length": len(joined), "input_sha": "c" * 64,
            "embedding_sha": vectors.sha256(VECTOR),
            "vector": vectors.pgvector_literal(VECTOR)})
    # The snapshot's source PDF is confirmed and bound, as the real import leaves it.
    request = kit.request(document, SOURCE_REF, b"%PDF-1.7 synthetic source", anchor_kind="pdf")
    with session_scope(kit.session_factory) as session:
        admit(session, request, manifest=kit.manifest)
    assert CustodyDispatcher(
        kit.store, source=kit.source, session_factory=kit.session_factory,
    ).dispatch().is_idle_and_complete
    with session_scope(kit.session_factory) as session:
        publish_bindings(session, NORM_SOURCE, [document])
    return Seed(snapshot, key, document, "a" * 64, embedding_digest)


def _bundle(root: Path, seed: Seed, *, set_id: str, name: str = "bundle") -> Path:
    mapping = canonical_json_bytes({
        "mapped_document_ids": [seed.document],
        "norms_snapshot_id": seed.snapshot,
        "reviewed_content_key": seed.key,
        "embedding_build": f"{EMBEDDING_PROFILE}:{CHUNKING}",
        "items": [{"id": "C01"}],
    })
    directory = root / name
    directory.mkdir()
    (directory / "map.json").write_bytes(mapping)
    (directory / "request.json").write_text(json.dumps({
        "format": promote_cli.REQUEST_FORMAT,
        "set_id": set_id,
        "snapshot_id": seed.snapshot,
        "reviewed_content_key": seed.key,
        "embedding_build": f"{EMBEDDING_PROFILE}:{CHUNKING}",
        "chunking_profile": CHUNKING,
        "independently_checked_source_digest": seed.content_digest,
        "independently_checked_embedding_digest": seed.embedding_digest,
        "designations": [
            {"document_id": seed.document, "slug": SLUG, "designation": "СП 99.1"},
        ],
        "items": [{
            "item_id": "C01",
            "query_vector_base64": vectors.to_base64(VECTOR),
            "provenance": {"query_text_sha256": "3" * 64,
                           "query_vector_sha256": vectors.sha256(VECTOR)},
            "targets": [{"document_id": seed.document, "ordinal_first": 0, "ordinal_last": 1}],
        }],
    }, ensure_ascii=False), encoding="utf-8")
    return directory


def _expect(directory: Path, set_sha256: str, catalogue_sha256: str) -> None:
    path = directory / "request.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["expected_set_sha256"] = set_sha256
    value["expected_catalogue_sha256"] = catalogue_sha256
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _field(output: str, name: str) -> str:
    found = re.search(rf"^{name}: (.+)$", output, re.MULTILINE)
    assert found, f"{name} missing from: {output!r}"
    return found.group(1)


class Stand:
    """The command wired to the kit's database and store, with an optional dispatch hook."""

    def __init__(self, kit: CustodyKit) -> None:
        self.kit = kit
        self.checkpoint: Callable[[str], None] | None = None
        self.built: list[bool] = []

    def __call__(self, with_store: bool) -> promote_cli.PromotionRunner:
        self.built.append(with_store)
        return promote_cli.DatabaseRunner(
            self.kit.session_factory, self.kit.store if with_store else None,
            checkpoint=self.checkpoint,
        )

    def run(self, command: str, bundle: Path) -> int:
        return promote_cli.main([command, str(bundle)], runner_factory=self)

    def counts(self) -> dict[str, int]:
        return {name: self.kit.scalar(f"SELECT count(*) FROM {name}") for name in WATCHED}


def _plan_digests(stand: Stand, bundle: Path, capsys: pytest.CaptureFixture[str]) -> tuple[str, str]:
    assert stand.run("plan", bundle) == 0
    out = capsys.readouterr().out
    assert _field(out, "verdict") == "not_compared"
    return _field(out, "set_sha256"), _field(out, "catalogue_sha256")


@pytest.mark.usefixtures("clean_tables")
def test_plan_computes_the_real_digests_and_writes_nothing(
    custody: CustodyKit, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    seed = _seed(custody)
    stand = Stand(custody)
    bundle = _bundle(tmp_path, seed, set_id=str(NormRetrievalSetId.new()))
    before, objects = stand.counts(), custody.bucket_keys()
    set_sha, catalogue_sha = _plan_digests(stand, bundle, capsys)
    assert stand.built == [False]  # plan never opens the object store
    assert stand.counts() == before and custody.bucket_keys() == objects
    assert len(set_sha) == len(catalogue_sha) == 64 and set_sha != catalogue_sha
    # The digests are a pure function of the snapshot and the bundle.
    assert _plan_digests(stand, bundle, capsys) == (set_sha, catalogue_sha)
    assert stand.counts() == before


@pytest.mark.usefixtures("clean_tables")
def test_plan_runs_in_one_repeatable_read_read_only_transaction(
    custody: CustodyKit, monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    def probe(session: Any, request: Any) -> None:
        observed["read_only"] = session.execute(text("SHOW transaction_read_only")).scalar_one()
        observed["isolation"] = session.execute(text("SHOW transaction_isolation")).scalar_one()
        with pytest.raises(InternalError, match="read-only"):
            session.execute(text("INSERT INTO norms_snapshot DEFAULT VALUES"))

    monkeypatch.setattr(promotion, "prepare_promotion", probe)
    promote_cli.DatabaseRunner(custody.session_factory).prepare(None)  # type: ignore[arg-type]
    assert observed == {"read_only": "on", "isolation": "repeatable read"}


@pytest.mark.usefixtures("clean_tables")
def test_promote_publishes_two_blobs_and_one_verified_set_then_replays_exactly(
    custody: CustodyKit, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    seed = _seed(custody)
    stand = Stand(custody)
    set_id = str(NormRetrievalSetId.new())
    bundle = _bundle(tmp_path, seed, set_id=set_id)
    set_sha, catalogue_sha = _plan_digests(stand, bundle, capsys)
    _expect(bundle, set_sha, catalogue_sha)
    objects = custody.bucket_keys()
    assert stand.run("plan", bundle) == 0
    assert _field(capsys.readouterr().out, "verdict") == "matched"

    assert stand.run("promote", bundle) == 0
    out = capsys.readouterr().out
    assert _field(out, "replayed") == "false" and _field(out, "set_sha256") == set_sha
    assert len(custody.bucket_keys()) == len(objects) + 2
    row = custody.scalar(
        "SELECT state || '/' || observed_set_sha256 || '/' || observed_catalogue_sha256 "
        "FROM norm_retrieval_set WHERE norm_retrieval_set_id = :set_id", set_id=set_id,
    )
    assert row == f"verified/{set_sha}/{catalogue_sha}"
    assert custody.scalar(
        "SELECT count(*) FROM norm_custody_binding WHERE target_id = :set_id", set_id=set_id,
    ) == 2
    with session_scope(custody.session_factory) as session:
        selected = promotion.select_verified_retrieval_set(
            session,
            identity=SetIdentity(
                _sha((tmp_path / "bundle" / "map.json").read_bytes()),
                seed.snapshot, seed.key, f"{EMBEDDING_PROFILE}:{CHUNKING}",
            ),
            chunking_profile=CHUNKING,
        )
    assert (selected.set_id, selected.set_sha256, selected.catalogue_sha256) == (
        set_id, set_sha, catalogue_sha,
    )
    assert _field(out, "set_blob_id") == selected.set_blob_id

    settled = stand.counts()
    assert stand.run("promote", bundle) == 0  # exact replay, same set_id
    replay = capsys.readouterr().out
    assert _field(replay, "replayed") == "true"
    assert stand.counts() == settled and len(custody.bucket_keys()) == len(objects) + 2

    # The same verified identity under a different set_id is refused, never duplicated.
    twin = _bundle(tmp_path, seed, set_id=str(NormRetrievalSetId.new()), name="twin")
    _expect(twin, set_sha, catalogue_sha)
    assert stand.run("promote", twin) == promote_cli.EXIT_REFUSED
    assert "already belongs to another set" in capsys.readouterr().err
    assert stand.counts() == settled


@pytest.mark.usefixtures("clean_tables")
def test_a_mismatched_expected_digest_exits_2_with_no_admission_row_or_object(
    custody: CustodyKit, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    seed = _seed(custody)
    stand = Stand(custody)
    bundle = _bundle(tmp_path, seed, set_id=str(NormRetrievalSetId.new()))
    set_sha, catalogue_sha = _plan_digests(stand, bundle, capsys)
    _expect(bundle, "f" * 64, catalogue_sha)
    before, objects = stand.counts(), custody.bucket_keys()
    assert stand.run("promote", bundle) == promote_cli.EXIT_REFUSED
    captured = capsys.readouterr()
    assert "REFUSED [expected_digest_mismatch]" in captured.err and "retrieval_set" in captured.err
    assert _field(captured.out, "set_sha256") == set_sha
    assert stand.counts() == before and custody.bucket_keys() == objects
    # Nothing consumed the set_id: the corrected digests promote under the same identity.
    _expect(bundle, set_sha, catalogue_sha)
    assert stand.run("promote", bundle) == 0


@pytest.mark.usefixtures("clean_tables")
def test_an_interrupted_dispatch_exits_3_and_the_rerun_completes_without_duplicates(
    custody: CustodyKit, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    seed = _seed(custody)
    stand = Stand(custody)
    set_id = str(NormRetrievalSetId.new())
    bundle = _bundle(tmp_path, seed, set_id=set_id)
    _expect(bundle, *_plan_digests(stand, bundle, capsys))

    def lost(point: str) -> None:
        if point == "temporary_staged":
            raise KeyboardInterrupt  # the operator's process is lost mid-publication

    stand.checkpoint = lost
    assert stand.run("promote", bundle) == promote_cli.EXIT_UNCERTAIN
    err = capsys.readouterr().err
    assert "UNCERTAIN [interrupted]" in err and f"set_id: {set_id}" in err
    assert f"promote_cli promote {bundle}" in err
    assert custody.scalar(
        "SELECT count(*) FROM norm_custody_admission WHERE target_id = :set_id", set_id=set_id,
    ) == 2
    assert custody.scalar(
        "SELECT count(*) FROM norm_retrieval_set WHERE norm_retrieval_set_id = :set_id",
        set_id=set_id,
    ) == 0

    stand.checkpoint = None
    assert stand.run("promote", bundle) == 0
    assert _field(capsys.readouterr().out, "replayed") == "false"
    assert custody.scalar(
        "SELECT count(*) FROM norm_custody_admission WHERE target_id = :set_id", set_id=set_id,
    ) == 2
    assert custody.scalar(
        "SELECT count(*) FROM norm_custody_binding WHERE target_id = :set_id", set_id=set_id,
    ) == 2
    assert stand.run("promote", bundle) == 0
    assert _field(capsys.readouterr().out, "replayed") == "true"


@pytest.mark.usefixtures("clean_tables")
def test_a_failed_try_leaves_the_admission_pending_and_exit_3_until_it_is_due(
    custody: CustodyKit, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    seed = _seed(custody)
    stand = Stand(custody)
    set_id = str(NormRetrievalSetId.new())
    bundle = _bundle(tmp_path, seed, set_id=set_id)
    _expect(bundle, *_plan_digests(stand, bundle, capsys))

    def broken(point: str) -> None:
        if point == "temporary_staged":
            raise RuntimeError("unclassified failure inside a dispatch step")

    stand.checkpoint = broken
    assert stand.run("promote", bundle) == promote_cli.EXIT_UNCERTAIN  # counted one try
    assert "UNCERTAIN [interrupted]" in capsys.readouterr().err
    stand.checkpoint = None
    # The retry is scheduled 30 s out: nothing is due, so the command reports it instead of
    # finalizing, and says what to do.
    assert stand.run("promote", bundle) == promote_cli.EXIT_UNCERTAIN
    err = capsys.readouterr().err
    assert "UNCERTAIN [dispatch_unsettled]" in err and "norm_retrieval_set=pending" in err
    assert custody.scalar(
        "SELECT count(*) FROM norm_retrieval_set WHERE norm_retrieval_set_id = :set_id",
        set_id=set_id,
    ) == 0
    with custody.engine.begin() as connection:
        connection.execute(text(
            "UPDATE norm_custody_admission SET available_at = clock_timestamp() "
            "WHERE target_id = :set_id AND state = 'pending'"
        ), {"set_id": set_id})
    assert stand.run("promote", bundle) == 0


@pytest.mark.usefixtures("clean_tables")
def test_a_foreign_pending_admission_refuses_before_this_sets_admission(
    custody: CustodyKit, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    seed = _seed(custody)
    stand = Stand(custody)
    set_id = str(NormRetrievalSetId.new())
    bundle = _bundle(tmp_path, seed, set_id=set_id)
    _expect(bundle, *_plan_digests(stand, bundle, capsys))
    foreign = custody.request(str(NormDocumentId.new()), "foreign-source", b"%PDF-1.7 another")
    with session_scope(custody.session_factory) as session:
        admit(session, foreign, manifest=custody.manifest)
    before = stand.counts()
    assert stand.run("promote", bundle) == promote_cli.EXIT_REFUSED
    assert "REFUSED [foreign_pending_admissions]" in capsys.readouterr().err
    assert stand.counts() == before  # neither this set's admissions nor the foreign one touched
    assert custody.scalar(
        "SELECT count(*) FROM norm_custody_admission WHERE state = 'pending'"
    ) == 1


@pytest.mark.usefixtures("clean_tables")
def test_the_default_runner_is_built_from_the_application_environment(
    custody: CustodyKit, custody_database: Any, s3_settings: Any, tmp_path: Path,
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = _seed(custody)
    set_id = str(NormRetrievalSetId.new())
    bundle = _bundle(tmp_path, seed, set_id=set_id)
    monkeypatch.setenv("DATABASE_URL", custody_database.url.render_as_string(hide_password=False))
    monkeypatch.setenv("S3_ENDPOINT_URL", s3_settings.endpoint_url)
    monkeypatch.setenv("S3_REGION", s3_settings.region)
    monkeypatch.setenv("S3_ACCESS_KEY_ID", s3_settings.access_key_id)
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", s3_settings.secret_access_key)
    monkeypatch.setenv("S3_BUCKET", s3_settings.bucket)
    reset_session_factory()
    dispose_engine()
    try:
        assert promote_cli.main(["plan", str(bundle)]) == 0
        out = capsys.readouterr().out
        _expect(bundle, _field(out, "set_sha256"), _field(out, "catalogue_sha256"))
        assert promote_cli.main(["promote", str(bundle)]) == 0
        assert _field(capsys.readouterr().out, "replayed") == "false"
    finally:
        reset_session_factory()
        dispose_engine()
    assert custody.scalar(
        "SELECT state FROM norm_retrieval_set WHERE norm_retrieval_set_id = :set_id",
        set_id=set_id,
    ) == "verified"


@pytest.mark.usefixtures("clean_tables")
def test_a_poisoned_admission_is_reported_and_completes_after_the_documented_requeue(
    custody: CustodyKit, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    seed = _seed(custody)
    stand = Stand(custody)
    set_id = str(NormRetrievalSetId.new())
    bundle = _bundle(tmp_path, seed, set_id=set_id)
    _expect(bundle, *_plan_digests(stand, bundle, capsys))

    def broken(point: str) -> None:
        if point == "temporary_staged":
            raise RuntimeError("the store keeps failing")

    def poisoned() -> list[str]:
        with session_scope(custody.session_factory) as session:
            return [
                admission.admission_id
                for role in (NORM_RETRIEVAL_SET, NORM_CATALOGUE)
                for admission in report(session, role=role, targets=[set_id]).poisoned
            ]

    stand.checkpoint = broken
    for _attempt in range(12):  # five counted tries poison one admission
        assert stand.run("promote", bundle) == promote_cli.EXIT_UNCERTAIN
        with custody.engine.begin() as connection:
            connection.execute(text(
                "UPDATE norm_custody_admission SET available_at = clock_timestamp() "
                "WHERE target_id = :set_id AND state = 'pending'"
            ), {"set_id": set_id})
        if poisoned():
            break
    capsys.readouterr()
    stand.checkpoint = None
    assert poisoned()
    assert stand.run("promote", bundle) == promote_cli.EXIT_UNCERTAIN
    err = capsys.readouterr().err
    assert "UNCERTAIN [dispatch_unsettled]" in err and "=poisoned" in err and "requeue" in err

    # The runbook's recovery: list this set's poisoned admissions, requeue exactly those.
    with session_scope(custody.session_factory) as session:
        assert requeue(session, poisoned())
    with custody.engine.begin() as connection:
        connection.execute(text(
            "UPDATE norm_custody_admission SET available_at = clock_timestamp() "
            "WHERE target_id = :set_id AND state = 'pending'"
        ), {"set_id": set_id})
    assert stand.run("promote", bundle) == 0
    assert _field(capsys.readouterr().out, "replayed") == "false"
    assert not poisoned()
