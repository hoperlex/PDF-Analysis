from __future__ import annotations

import hashlib
import json
from array import array
from dataclasses import replace

import pytest

from auditmanager.norms.embedding.profile import DIMENSIONS
from auditmanager.norms.retrieval.artifact import (
    ArtifactRefused,
    SetIdentity,
    SnapshotBinding,
    SourceParagraph,
    build_retrieval_set,
    canonical_json_bytes,
)
from auditmanager.norms.retrieval.ranking import (
    PromptSelection,
    RetrievalItem,
    RetrievalParagraph,
    TargetSpan,
    select_prompt_part,
)


SNAPSHOT_ID = "ns_" + "0" * 26


def _sha(text: str | bytes) -> str:
    return hashlib.sha256(text.encode("utf-8") if isinstance(text, str) else text).hexdigest()


def _fixture() -> tuple[SetIdentity, bytes, SnapshotBinding, PromptSelection, tuple[SourceParagraph, ...]]:
    mapping = {
        "reviewed_content_key": "corpus-digest-key",
        "norms_snapshot_id": SNAPSHOT_ID,
        "embedding_build": "bge-m3-dense-v1:characters-v2:1200",
        "mapped_document_ids": ["ndoc_1"],
        "items": [{"id": "item-1"}],
    }
    map_bytes = canonical_json_bytes(mapping)
    identity = SetIdentity(_sha(map_bytes), SNAPSHOT_ID, mapping["reviewed_content_key"], mapping["embedding_build"])
    snapshot = SnapshotBinding(SNAPSHOT_ID, identity.reviewed_content_key, "a" * 64, identity.embedding_build, 2)
    paragraphs = (
        RetrievalParagraph("ndoc_1", "npar_0", "СП 1", "Тест", 0, "1", "1", "Надёжный текст первого пункта"),
        RetrievalParagraph("ndoc_1", "npar_1", "СП 1", "Тест", 1, None, "1", "Скан без надёжного текста", False),
        RetrievalParagraph("ndoc_1", "npar_2", "СП 1", "Тест", 2, "2", "2", "Полный текст второго пункта"),
    )
    vector = array("f", [0.0]) * DIMENSIONS
    vector[0] = 1.0
    item = RetrievalItem("item-1", vector, (TargetSpan("ndoc_1", 0, 0),))
    selection = select_prompt_part((item,), paragraphs, ())
    source = tuple(SourceParagraph(p, _sha(p.text)) for p in paragraphs)
    return identity, map_bytes, snapshot, selection, source


def _build(parts: tuple) -> object:
    identity, map_bytes, snapshot, selection, paragraphs = parts
    return build_retrieval_set(identity=identity, map_bytes=map_bytes, snapshot=snapshot, selection=selection, paragraphs=paragraphs)


def test_exact_bytes_replay_and_complete_reliable_rebinding_text() -> None:
    parts = _fixture()
    first = _build(parts)
    replay = _build((parts[0], parts[1], parts[2], parts[3], tuple(reversed(parts[4]))))
    assert first == replay
    assert _sha(first.data) == first.sha256
    payload = json.loads(first.data)
    assert payload["identity"]["map_sha256"] == parts[0].map_sha256
    assert payload["prompt_part"] == parts[3].prompt_part
    assert payload["prompt_part_characters"] == len(parts[3].prompt_part)
    assert [row["norm_paragraph_id"] for row in payload["rebinding_paragraphs"]] == ["npar_0", "npar_2"]
    assert payload["norm_quote_version"] == "norm-quote-v1"
    assert payload["norm_value_version"] == "norm-value-v1"


def test_map_digest_and_snapshot_binding_must_match() -> None:
    identity, map_bytes, snapshot, selection, source = _fixture()
    with pytest.raises(ArtifactRefused, match="map digest mismatch"):
        _build((replace(identity, map_sha256="b" * 64), map_bytes, snapshot, selection, source))
    with pytest.raises(ArtifactRefused, match="snapshot binding"):
        _build((identity, map_bytes, replace(snapshot, embedding_build="other-build"), selection, source))
    changed = json.loads(map_bytes)
    changed["reviewed_content_key"] = "different"
    changed_bytes = canonical_json_bytes(changed)
    with pytest.raises(ArtifactRefused, match="reviewed map reviewed_content_key mismatch"):
        _build((replace(identity, map_sha256=_sha(changed_bytes)), changed_bytes, snapshot, selection, source))
    with pytest.raises(ArtifactRefused, match="not canonical"):
        noncanonical = json.dumps(json.loads(map_bytes), ensure_ascii=False).encode()
        _build((replace(identity, map_sha256=_sha(noncanonical)), noncanonical, snapshot, selection, source))
    changed = json.loads(map_bytes)
    changed["items"] = [{"id": "other-item"}]
    changed_bytes = canonical_json_bytes(changed)
    with pytest.raises(ArtifactRefused, match="selected item ids differ"):
        _build((replace(identity, map_sha256=_sha(changed_bytes)), changed_bytes, snapshot, selection, source))


def test_source_digest_duplicate_and_non_nfc_are_refused() -> None:
    identity, map_bytes, snapshot, selection, source = _fixture()
    with pytest.raises(ArtifactRefused, match="content digest mismatch"):
        _build((identity, map_bytes, snapshot, selection, (replace(source[0], text_sha256="a" * 64), *source[1:])))
    with pytest.raises(ArtifactRefused, match="duplicate paragraph identity"):
        _build((identity, map_bytes, snapshot, selection, (*source, source[0])))
    bad = replace(source[2].paragraph, text="A\u0301")
    with pytest.raises(ArtifactRefused, match="nonempty NFC"):
        _build((identity, map_bytes, snapshot, selection, (*source[:2], SourceParagraph(bad, _sha(bad.text)))))
    with pytest.raises(ArtifactRefused, match="ordinals incomplete"):
        _build((identity, map_bytes, snapshot, selection, (source[0], source[2])))


def test_prompt_row_and_exact_prompt_part_cannot_drift() -> None:
    identity, map_bytes, snapshot, selection, source = _fixture()
    changed = replace(selection.rows[0], text_sha256="b" * 64)
    with pytest.raises(ArtifactRefused, match="prompt row differs"):
        _build((identity, map_bytes, snapshot, replace(selection, rows=(changed,)), source))
    with pytest.raises(ArtifactRefused, match="prompt part differs"):
        _build((identity, map_bytes, snapshot, replace(selection, prompt_part=selection.prompt_part + " "), source))
    with pytest.raises(ArtifactRefused, match="prompt label"):
        _build((identity, map_bytes, snapshot, replace(selection, rows=(replace(selection.rows[0], label="N3"),)), source))
    duplicate = replace(selection.rows[0], label="N2")
    with pytest.raises(ArtifactRefused, match="duplicated"):
        _build((identity, map_bytes, snapshot, replace(selection, rows=(*selection.rows, duplicate)), source))
