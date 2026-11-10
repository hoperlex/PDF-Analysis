"""`EMBED-01`: the in-image entry of the night encoder (`infra/norms-worker/embed_intents.py`), with a fake encoder.

What it adds to ``embed-texts`` is shown by the texts it sets aside: a text over 512 tokens is not an error of the whole file, it is counted, left
out of the encoder and listed with its token count, and no text is ever cut. The files it writes are the ones the worker's ``parse_answer`` reads.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

import pytest

from auditmanager.norms.embedding import vectors as norms_vectors
from auditmanager.precedents.vectors.intents import build_request, input_sha256, parse_answer

ENTRY = Path(__file__).resolve().parents[3] / "infra" / "norms-worker" / "embed_intents.py"


def load_entry() -> ModuleType:
    spec = importlib.util.spec_from_file_location("embed_intents_under_test", ENTRY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


entry = load_entry()


class CountingEncoder:
    """A token is a word; the batch it was asked to encode is recorded, so what reached the model can be read."""

    def __init__(self) -> None:
        self.encoded: list[str] = []

    def count_tokens(self, text: str) -> int:
        return len(text.split()) + 2

    def encode(self, texts: Sequence[str]) -> list[bytes]:
        self.encoded.extend(texts)
        values = [math.cos(0.01 * index) for index in range(1024)]
        norm = math.sqrt(sum(value * value for value in values))
        return [norms_vectors.pack([value / norm for value in values]) for _ in texts]


SHORT = "короткая находка"
LONG = "слово " * 600


def write_request(path: Path, texts: Sequence[str]) -> list[str]:
    request = build_request(texts)
    path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    return [item["id"] for item in request["texts"]]


def test_a_text_over_the_token_limit_is_set_aside_with_its_count_and_never_reaches_the_encoder(tmp_path: Path) -> None:
    encoder = CountingEncoder()
    ids = write_request(tmp_path / "in.json", [SHORT, LONG, "ещё одна короткая находка"])
    code = entry.main(
        ["--in", str(tmp_path / "in.json"), "--out", str(tmp_path / "out.json"), "--over-limit-out", str(tmp_path / "over.json")],
        load=lambda: encoder)
    assert code == 0
    assert LONG not in encoder.encoded and not any("слово" in text for text in encoder.encoded), "a long text is not cut and tried"
    response = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    over = json.loads((tmp_path / "over.json").read_text(encoding="utf-8"))
    assert over["entries"] == [{"id": input_sha256(LONG), "token_count": 602}]
    parsed = parse_answer(response, over, requested=ids)
    assert set(parsed.over_limit) == {input_sha256(LONG)} and len(parsed.vectors) == 2 and not parsed.missing and not parsed.rejected


def test_a_batch_of_only_long_texts_is_an_answer_with_no_vectors(tmp_path: Path) -> None:
    ids = write_request(tmp_path / "in.json", [LONG])
    code = entry.main(
        ["--in", str(tmp_path / "in.json"), "--out", str(tmp_path / "out.json"), "--over-limit-out", str(tmp_path / "over.json")],
        load=CountingEncoder)
    assert code == 0
    parsed = parse_answer(json.loads((tmp_path / "out.json").read_text(encoding="utf-8")),
                          json.loads((tmp_path / "over.json").read_text(encoding="utf-8")), requested=ids)
    assert not parsed.vectors and set(parsed.over_limit) == set(ids)


def test_a_text_at_the_limit_is_encoded(tmp_path: Path) -> None:
    at_limit = "слово " * 510
    encoder = CountingEncoder()
    write_request(tmp_path / "in.json", [at_limit])
    assert encoder.count_tokens(at_limit) == 512
    entry.main(["--in", str(tmp_path / "in.json"), "--out", str(tmp_path / "out.json"), "--over-limit-out", str(tmp_path / "over.json")],
               load=lambda: encoder)
    assert encoder.encoded == [at_limit]
    assert json.loads((tmp_path / "over.json").read_text(encoding="utf-8"))["entries"] == []


def test_an_answer_is_never_overwritten(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_request(tmp_path / "in.json", [SHORT])
    (tmp_path / "out.json").write_text("earlier", encoding="utf-8")
    code = entry.main(["--in", str(tmp_path / "in.json"), "--out", str(tmp_path / "out.json"), "--over-limit-out", str(tmp_path / "over.json")],
                      load=CountingEncoder)
    assert code == entry.EXIT_REFUSED and "never overwrites" in capsys.readouterr().err
    assert (tmp_path / "out.json").read_text(encoding="utf-8") == "earlier" and not (tmp_path / "over.json").exists()


@pytest.mark.parametrize("body", ["not json", json.dumps({"format": "other", "texts": []}), json.dumps({"format": "auditmanager-embed-texts-request/1", "texts": []})])
def test_a_request_that_is_not_one_is_refused_and_nothing_is_written(tmp_path: Path, body: str, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "in.json").write_text(body, encoding="utf-8")
    code = entry.main(["--in", str(tmp_path / "in.json"), "--out", str(tmp_path / "out.json"), "--over-limit-out", str(tmp_path / "over.json")],
                      load=CountingEncoder)
    assert code == entry.EXIT_REFUSED and "refused:" in capsys.readouterr().err
    assert not (tmp_path / "out.json").exists() and not (tmp_path / "over.json").exists()


def test_the_windows_limits_are_two_threads_and_a_batch_of_eight() -> None:
    assert (entry.THREADS, entry.BATCH) == (2, 8)
