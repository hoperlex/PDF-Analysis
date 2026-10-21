from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.norms.retrieval.artifact import ArtifactRefused, SnapshotBinding
from auditmanager.norms.retrieval.catalogue import CatalogueDocument, build_catalogue


def _snapshot() -> SnapshotBinding:
    return SnapshotBinding("ns_" + "0" * 26, "corpus-key", "a" * 64, "bge-m3-dense-v1:characters-v2:1200", 2)


def _documents() -> tuple[CatalogueDocument, ...]:
    return (
        CatalogueDocument("ndoc_2", "СП_54_13330_2022__second", ("сп", "54", "13330", "2022"), "Жилые здания", "СП"),
        CatalogueDocument("ndoc_1", "ГОСТ_10140-2003__first", ("гост", "10140", "2003"), "Первый стандарт", "ГОСТ"),
    )


def test_catalogue_bytes_sha_and_order_replay() -> None:
    docs = _documents()
    first = build_catalogue(snapshot=_snapshot(), documents=docs)
    assert first == build_catalogue(snapshot=_snapshot(), documents=tuple(reversed(docs)))
    assert hashlib.sha256(first.data).hexdigest() == first.sha256
    payload = json.loads(first.data)
    assert payload["norms_snapshot_id"] == _snapshot().snapshot_id
    assert [row["norm_document_id"] for row in payload["documents"]] == ["ndoc_1", "ndoc_2"]
    assert payload["documents"][0]["designation_tokens"] == ["гост", "10140", "2003"]


def test_totality_duplicates_and_tokens_fail_closed() -> None:
    docs = _documents()
    with pytest.raises(ArtifactRefused, match="count differs"):
        build_catalogue(snapshot=_snapshot(), documents=docs[:1])
    with pytest.raises(ArtifactRefused, match="duplicate"):
        build_catalogue(snapshot=_snapshot(), documents=(docs[0], replace(docs[1], document_id=docs[0].document_id)))
    with pytest.raises(ArtifactRefused, match="duplicate"):
        build_catalogue(snapshot=_snapshot(), documents=(docs[0], replace(docs[1], slug=docs[0].slug)))
    with pytest.raises(ArtifactRefused, match="designation tokens"):
        build_catalogue(snapshot=_snapshot(), documents=(docs[0], replace(docs[1], designation_tokens=())))
    with pytest.raises(ArtifactRefused, match="nonempty NFC"):
        build_catalogue(snapshot=_snapshot(), documents=(docs[0], replace(docs[1], title="A\u0301")))


def test_snapshot_binding_fields_are_required() -> None:
    with pytest.raises(ArtifactRefused, match="invalid snapshot"):
        build_catalogue(snapshot=replace(_snapshot(), snapshot_id="ns_bad"), documents=_documents())
    with pytest.raises(ArtifactRefused, match="snapshot content digest"):
        build_catalogue(snapshot=replace(_snapshot(), content_digest="not-sha"), documents=_documents())
