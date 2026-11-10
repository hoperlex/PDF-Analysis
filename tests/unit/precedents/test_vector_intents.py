"""`EMBED-01`: what the encoder is given for a case and the check of what it returns (`ADR-0029` decision 8).

The answer is checked against the real producer: the response of ``embed-texts`` of the norms package, made with a fake encoder that returns
real packed unit vectors, is what ``parse_answer`` must accept -- and the same answer with one fact moved must be refused. A consumer tested only
against fixtures it wrote itself would agree with itself.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import struct
from collections.abc import Sequence
from typing import Any

import pytest

from auditmanager.norms.embedding import profile as norms_profile
from auditmanager.norms.embedding import texts as norms_texts
from auditmanager.norms.embedding import vectors as norms_vectors
from auditmanager.norms.embedding.windowing import input_digest as norms_input_digest
from auditmanager.precedents.vectors import intents
from auditmanager.precedents.vectors.intents import (
    CUT_MARK,
    INPUT_BUDGET_CHARS,
    ImportRefused,
    build_finding_view,
    build_request,
    input_sha256,
    parse_answer,
)


def unit_vector(seed: int) -> bytes:
    values = [math.sin(seed * 7.0 + index * 0.013) for index in range(intents.DIMENSIONS)]
    norm = math.sqrt(sum(value * value for value in values))
    return norms_vectors.pack([value / norm for value in values])


class FakeEncoder:
    """The ``TextEncoder`` protocol of the norms embedder: a token is four characters, a vector is a function of the text."""

    def count_tokens(self, text: str) -> int:
        return len(text) // 4 + 2

    def encode(self, texts: Sequence[str]) -> list[bytes]:
        return [unit_vector(int(hashlib.sha256(text.encode()).hexdigest()[:6], 16)) for text in texts]


def produced(texts: Sequence[str]) -> tuple[dict[str, Any], list[str]]:
    request = build_request(texts)
    return norms_texts.embed_texts(FakeEncoder(), request), [entry["id"] for entry in request["texts"]]


# -- the profile is the one the image runs -------------------------------------------------------------------------------


def test_the_constants_are_the_norms_packages_own() -> None:
    assert (intents.EMBEDDING_PROFILE, intents.MODEL_REVISION, intents.DIMENSIONS, intents.MAX_TOKENS) == (
        norms_profile.EMBEDDING_PROFILE, norms_profile.MODEL_REVISION, norms_profile.DIMENSIONS, norms_profile.MAX_TOKENS)
    assert intents.UNIT_NORM_TOLERANCE == norms_profile.UNIT_NORM_TOLERANCE
    assert (intents.REQUEST_FORMAT, intents.RESPONSE_FORMAT) == (norms_texts.REQUEST_FORMAT, norms_texts.RESPONSE_FORMAT)


def test_the_digest_of_an_input_is_the_digest_the_container_reports() -> None:
    assert input_sha256("Категория: dimensions") == norms_input_digest("Категория: dimensions")


# -- the view -------------------------------------------------------------------------------------------------------------


def test_a_short_case_is_the_category_the_finding_and_the_recommendation() -> None:
    text = build_finding_view(category="dimensions", finding_text="Высота помещения менее 2,5 м.", recommendation_text="Увеличить высоту до 2,7 м по СП 54.")
    assert text == "Категория: dimensions\nНаходка: Высота помещения менее 2,5 м.\nРекомендация: Увеличить высоту до 2,7 м по СП 54."


def test_the_view_never_exceeds_the_budget_and_marks_every_cut() -> None:
    long = ("слово " * 400).strip()
    for finding, recommendation in ((long, "коротко"), ("коротко", long), (long, long)):
        text = build_finding_view(category="layout", finding_text=finding, recommendation_text=recommendation)
        assert len(text) <= INPUT_BUDGET_CHARS
        assert CUT_MARK in text, "a cut is marked, never silent"
    fits = build_finding_view(category="layout", finding_text="короткая находка", recommendation_text="короткий совет, который помещается целиком")
    assert CUT_MARK not in fits


def test_the_finding_comes_before_the_recommendation_when_there_is_room_for_one_only() -> None:
    text = build_finding_view(category="layout", finding_text="н" * 960, recommendation_text="р" * 500)
    assert "Находка: " in text and "Рекомендация: " not in text and len(text) <= INPUT_BUDGET_CHARS


def test_two_spellings_of_one_sentence_are_one_input() -> None:
    one = build_finding_view(category="layout", finding_text="Высота   помещения\n менее нормы", recommendation_text="Увеличить")
    two = build_finding_view(category="layout", finding_text="Высота помещения менее нормы", recommendation_text="Увеличить")
    assert one == two and input_sha256(one) == input_sha256(two)


def test_a_view_needs_a_finding() -> None:
    with pytest.raises(ValueError):
        build_finding_view(category="layout", finding_text="   ", recommendation_text="x")


# -- the request: deduplicated by the digest of the text ----------------------------------------------------------------


def test_equal_texts_are_one_entry_and_the_id_is_the_digest() -> None:
    request = build_request(["один", "два", "один", "один", "три"])
    ids = [entry["id"] for entry in request["texts"]]
    assert len(ids) == 3 and ids == sorted(ids)
    assert {entry["id"]: entry["text"] for entry in request["texts"]} == {input_sha256(text): text for text in ("один", "два", "три")}


def test_an_empty_batch_is_refused() -> None:
    with pytest.raises(ValueError):
        build_request([])


def test_the_request_is_the_one_embed_texts_accepts() -> None:
    assert norms_texts.parse_request(build_request(["один", "два"])) == [(i, t) for i, t in sorted(
        ((input_sha256(t), t) for t in ("один", "два")))]


# -- the answer ----------------------------------------------------------------------------------------------------------


def test_the_real_producers_answer_is_accepted_whole() -> None:
    response, ids = produced(["один", "два", "три"])
    parsed = parse_answer(response, None, requested=ids)
    assert set(parsed.vectors) == set(ids) and not parsed.rejected and not parsed.over_limit and not parsed.missing
    vector = parsed.vectors[ids[0]]
    assert len(vector.values) == 1024 and vector.embedding_sha256 == hashlib.sha256(
        struct.pack("!1024f", *vector.values)).hexdigest()


@pytest.mark.parametrize(("name", "value"), [
    ("embedding_profile", "bge-m3-dense-v2"), ("model_revision", "0" * 40), ("dimensions", 768), ("dtype", "float16"), ("byte_order", "little"),
    ("format", "auditmanager-embed-texts/2"),
])
def test_a_frozen_fact_that_moved_refuses_the_whole_answer(name: str, value: object) -> None:
    response, ids = produced(["один"])
    response[name] = value
    with pytest.raises(ImportRefused):
        parse_answer(response, None, requested=ids)


def test_an_id_that_was_not_asked_for_or_that_repeats_refuses_the_whole_answer() -> None:
    response, ids = produced(["один", "два"])
    with pytest.raises(ImportRefused):
        parse_answer(response, None, requested=ids[:1])
    twice = copy.deepcopy(response)
    twice["vectors"].append(copy.deepcopy(twice["vectors"][0]))
    with pytest.raises(ImportRefused):
        parse_answer(twice, None, requested=ids)


def test_a_digest_the_container_reports_that_is_not_the_id_refuses_the_whole_answer() -> None:
    response, ids = produced(["один"])
    response["vectors"][0]["input_sha256"] = "f" * 64
    with pytest.raises(ImportRefused):
        parse_answer(response, None, requested=ids)


def _replace_vector(response: dict[str, Any], index: int, packed: bytes) -> None:
    response["vectors"][index]["vector"] = base64.b64encode(packed).decode("ascii")
    response["vectors"][index]["vector_sha256"] = hashlib.sha256(packed).hexdigest()


def test_a_vector_that_is_not_unit_norm_refuses_only_itself() -> None:
    response, ids = produced(["один", "два"])
    doubled = struct.pack("!1024f", *(2.0 * value for value in struct.unpack("!1024f", base64.b64decode(response["vectors"][0]["vector"]))))
    _replace_vector(response, 0, doubled)
    parsed = parse_answer(response, None, requested=ids)
    assert set(parsed.rejected) == {ids[0]} and "norm" in parsed.rejected[ids[0]]
    assert set(parsed.vectors) == {ids[1]}, "the other vector is still taken"


def test_the_norm_is_held_at_the_databases_own_bound() -> None:
    """Just inside the CHECK of ``decision_memory_embedding`` (0.0001) is taken, just outside is refused."""
    response, ids = produced(["один", "два"])
    base = struct.unpack("!1024f", base64.b64decode(response["vectors"][0]["vector"]))
    _replace_vector(response, 0, struct.pack("!1024f", *(value * 1.00009 for value in base)))
    _replace_vector(response, 1, struct.pack("!1024f", *(value * 1.00020 for value in struct.unpack("!1024f", base64.b64decode(response["vectors"][1]["vector"])))))
    parsed = parse_answer(response, None, requested=ids)
    assert set(parsed.vectors) == {ids[0]} and set(parsed.rejected) == {ids[1]}


@pytest.mark.parametrize("broken", ["not base64 !!", base64.b64encode(b"short").decode(), base64.b64encode(struct.pack("!1024f", *([float("nan")] * 1024))).decode()])
def test_a_vector_that_cannot_be_decoded_refuses_only_itself(broken: str) -> None:
    response, ids = produced(["один", "два"])
    response["vectors"][0]["vector"] = broken
    parsed = parse_answer(response, None, requested=ids)
    assert set(parsed.rejected) == {ids[0]} and set(parsed.vectors) == {ids[1]}


def test_a_vector_whose_digest_is_not_its_own_refuses_only_itself() -> None:
    response, ids = produced(["один", "два"])
    response["vectors"][1]["vector_sha256"] = "0" * 64
    parsed = parse_answer(response, None, requested=ids)
    assert set(parsed.rejected) == {ids[1]} and set(parsed.vectors) == {ids[0]}


def test_an_id_with_no_answer_is_missing() -> None:
    response, ids = produced(["один", "два"])
    response["vectors"].pop()
    parsed = parse_answer(response, None, requested=ids)
    assert parsed.missing == {ids[1]}


# -- a text over the token limit is set aside, never cut --------------------------------------------------------------------


def over_limit(ids_and_counts: dict[str, int]) -> dict[str, Any]:
    return {"format": intents.OVER_LIMIT_FORMAT, "limit": 512, "entries": [{"id": i, "token_count": c} for i, c in ids_and_counts.items()]}


def test_a_text_over_five_hundred_twelve_tokens_is_reported_over_the_limit() -> None:
    response, ids = produced(["один"])
    long_id = input_sha256("очень длинный текст")
    parsed = parse_answer(response, over_limit({long_id: 700}), requested=[*ids, long_id])
    assert parsed.over_limit == {long_id: 700} and set(parsed.vectors) == set(ids) and not parsed.missing


@pytest.mark.parametrize("entries", [{"a" * 64: 700}, {"short": 700}])
def test_an_over_limit_id_that_was_not_asked_for_refuses_the_answer(entries: dict[str, int]) -> None:
    response, ids = produced(["один"])
    with pytest.raises(ImportRefused):
        parse_answer(response, over_limit(entries), requested=ids)


def test_a_count_not_over_the_limit_is_not_a_reason_to_set_a_text_aside() -> None:
    response, ids = produced(["один"])
    other = input_sha256("второй")
    with pytest.raises(ImportRefused):
        parse_answer(response, over_limit({other: 512}), requested=[*ids, other])


def test_a_text_both_encoded_and_over_the_limit_refuses_the_answer() -> None:
    response, ids = produced(["один"])
    with pytest.raises(ImportRefused):
        parse_answer(response, over_limit({ids[0]: 900}), requested=ids)


def test_the_literal_the_database_reads_is_the_floats_nine_digits() -> None:
    packed = unit_vector(3)
    literal = intents.pgvector_literal(struct.unpack("!1024f", packed))
    assert literal == norms_vectors.pgvector_literal(packed)
    assert json.loads(literal) and len(json.loads(literal)) == 1024
