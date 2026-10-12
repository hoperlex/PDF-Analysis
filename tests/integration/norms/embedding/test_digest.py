"""`D-127`'s digest: computed keys only, a documented serialisation, canonical order enforced."""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import fields, replace

import pytest

from auditmanager.norms.embedding.digest import (
    EMBEDDING_SET_DIGEST_VERSION,
    EmbeddingSetDigest,
)
from auditmanager.norms.embedding.model import EmbeddedWindow
from tests.integration.norms.embedding.support import (
    CHUNKING_PROFILE,
    CONTENT_KEY,
    fake_vector,
)

WINDOW = EmbeddedWindow(
    window_ordinal=0,
    char_offset=0,
    char_length=10,
    token_count=7,
    paragraph_ordinal_first=3,
    paragraph_ordinal_last=4,
    input_sha256="a" * 64,
    vector=fake_vector("x"),
)


def _digest(*entries: tuple[str, int, EmbeddedWindow]) -> str:
    digest = EmbeddingSetDigest(
        content_key=CONTENT_KEY, chunking_profile=CHUNKING_PROFILE, embedding_profile="bge-m3-dense-v1"
    )
    for document_ref, ordinal, window in entries:
        digest.add(document_ref, ordinal, window)
    return digest.hexdigest()


def test_the_digest_is_the_documented_canonical_serialisation() -> None:
    second = replace(WINDOW, window_ordinal=1, char_offset=5, char_length=5, input_sha256="b" * 64)
    by_hand = hashlib.sha256()
    by_hand.update(b"norm-embedding-set/2\n")
    for window in (WINDOW, second):
        by_hand.update(
            (
                f'["{CONTENT_KEY}","doc-ё","{CHUNKING_PROFILE}",2,"bge-m3-dense-v1",'
                f'{window.window_ordinal},7,{window.char_offset},{window.char_length},3,4,'
                f'"{window.input_sha256}","{hashlib.sha256(window.vector).hexdigest()}"]\n'
            ).encode()
        )
    assert EMBEDDING_SET_DIGEST_VERSION == "norm-embedding-set/2"
    assert _digest(("doc-ё", 2, WINDOW), ("doc-ё", 2, second)) == by_hand.hexdigest()


def test_no_private_key_can_enter_the_digest() -> None:
    """The digest's inputs are the computed key and the window; nothing names a ``*_pk``."""
    assert not any(field.name.endswith("_pk") for field in fields(EmbeddedWindow))
    parameters = inspect.signature(EmbeddingSetDigest.add_values).parameters
    assert not any(name.endswith(("_pk", "_id")) for name in parameters)


@pytest.mark.parametrize(
    "change",
    [
        {"token_count": 8},
        {"char_offset": 1},
        {"char_length": 11},
        {"paragraph_ordinal_first": 2},
        {"paragraph_ordinal_last": 5},
        {"input_sha256": "c" * 64},
        {"vector": fake_vector("y")},
    ],
)
def test_every_window_field_moves_the_digest(change: dict) -> None:
    assert _digest(("doc", 0, WINDOW)) != _digest(("doc", 0, replace(WINDOW, **change)))


def test_every_computed_key_part_moves_the_digest() -> None:
    base = _digest(("doc", 0, WINDOW))
    assert base != _digest(("doc2", 0, WINDOW))
    assert base != _digest(("doc", 1, WINDOW))
    for content_key, profile in ((CONTENT_KEY + "x", CHUNKING_PROFILE), (CONTENT_KEY, "characters-v2:1000")):
        other = EmbeddingSetDigest(content_key=content_key, chunking_profile=profile, embedding_profile="bge-m3-dense-v1")
        other.add("doc", 0, WINDOW)
        assert other.hexdigest() != base


def test_a_window_out_of_canonical_order_is_refused() -> None:
    digest = EmbeddingSetDigest(
        content_key=CONTENT_KEY, chunking_profile=CHUNKING_PROFILE, embedding_profile="bge-m3-dense-v1"
    )
    digest.add("doc-b", 0, WINDOW)
    with pytest.raises(ValueError, match="canonical order"):
        digest.add("doc-a", 0, WINDOW)
    with pytest.raises(ValueError, match="canonical order"):
        digest.add("doc-b", 0, WINDOW)


def test_code_point_order_is_the_order_postgresql_gives_under_collate_c() -> None:
    """UTF-8 byte order equals code-point order, which is what ``COLLATE "C"`` sorts by."""
    refs = ["doc-é", "doc-a", "Doc", "doc-Ё", "doc-z", "док"]
    assert sorted(refs) == sorted(refs, key=lambda value: value.encode("utf-8"))
