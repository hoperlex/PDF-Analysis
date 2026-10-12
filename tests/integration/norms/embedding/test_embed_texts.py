"""``embed-texts`` is stable: a fixed format, byte-equal answers to equal requests, loud refusals."""

from __future__ import annotations

import base64
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from auditmanager.norms.embedding import texts
from auditmanager.norms.embedding.texts import (
    REQUEST_FORMAT,
    EmbedTextsRefused,
    embed_texts,
    render,
    run,
)
from tests.integration.norms.embedding.support import ROOT, FakeEncoder, fake_vector

REQUEST = {
    "format": REQUEST_FORMAT,
    "texts": [
        {"id": "q-01", "text": "Ширина эвакуационного выхода из помещения"},
        {"id": "q-02", "text": "Высота ограждения лестничного марша"},
        {"id": "crop:7f3a", "text": "REI 45 | Предел огнестойкости"},
    ],
}
#: The rendered response of REQUEST under the fake encoder. A change to the format, the key
#: order, the byte order or the digests changes this value: that is what "stable" pins.
GOLDEN_SHA256 = "6753f69bde0f4e860bc3ea7aa308fe6c228e59f0b6ad1f30bdf81e030307cba4"


def test_the_response_format_is_exact() -> None:
    response = embed_texts(FakeEncoder(), REQUEST)
    assert list(response) == [
        "format", "embedding_profile", "model_repository", "model_revision",
        "dimensions", "dtype", "byte_order", "vectors",
    ]
    assert response["format"] == "auditmanager-embed-texts/1"
    assert response["embedding_profile"] == "bge-m3-dense-v1"
    assert response["model_repository"] == "BAAI/bge-m3"
    assert response["model_revision"] == "5617a9f61b028005a4858fdac845db406aefb181"
    assert (response["dimensions"], response["dtype"], response["byte_order"]) == (1024, "float32", "big")
    assert [entry["id"] for entry in response["vectors"]] == ["q-01", "q-02", "crop:7f3a"]
    for entry, request in zip(response["vectors"], REQUEST["texts"], strict=True):
        packed = base64.b64decode(entry["vector"])
        assert packed == fake_vector(request["text"])
        assert entry["vector_sha256"] == hashlib.sha256(packed).hexdigest()
        assert entry["input_sha256"] == hashlib.sha256(request["text"].encode()).hexdigest()
        values = struct.unpack("!1024f", packed)
        assert abs(sum(value * value for value in values) - 1.0) < 1e-4
        assert set(entry) == {"id", "input_sha256", "token_count", "vector_sha256", "vector"}


def test_equal_requests_give_byte_equal_responses_and_the_bytes_are_pinned() -> None:
    first = render(embed_texts(FakeEncoder(), REQUEST))
    second = render(embed_texts(FakeEncoder(), json.loads(json.dumps(REQUEST))))
    assert first == second
    assert first.endswith(b"}\n") and b"\n" not in first[:-1]
    assert hashlib.sha256(first).hexdigest() == GOLDEN_SHA256


@pytest.mark.parametrize(
    ("request_document", "match"),
    [
        ({"format": "other", "texts": [{"id": "a", "text": "b"}]}, "is not"),
        ({"format": REQUEST_FORMAT, "texts": []}, "no texts"),
        ({"format": REQUEST_FORMAT, "texts": [{"id": "a", "text": "b"}], "x": 1}, "other than"),
        ({"format": REQUEST_FORMAT, "texts": [{"id": "", "text": "b"}]}, "non-empty string"),
        ({"format": REQUEST_FORMAT, "texts": [{"id": 3, "text": "b"}]}, "non-empty string"),
        ({"format": REQUEST_FORMAT, "texts": [{"id": "a", "text": "b"}, {"id": "a", "text": "c"}]}, "repeats"),
        ({"format": REQUEST_FORMAT, "texts": [{"id": "a", "text": "  "}]}, "empty"),
        ({"format": REQUEST_FORMAT, "texts": [{"id": "a"}]}, "is not"),
        ({"format": REQUEST_FORMAT, "texts": [{"id": "long", "text": "слово " * 400}]}, "not truncated"),
    ],
)
def test_a_bad_request_is_refused(request_document: dict, match: str) -> None:
    encoder = FakeEncoder()
    with pytest.raises(EmbedTextsRefused, match=match):
        embed_texts(encoder, request_document)
    assert encoder.calls == []


def test_run_writes_atomically_and_never_overwrites(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(REQUEST, ensure_ascii=False), encoding="utf-8")
    response_path = tmp_path / "response.json"
    run(FakeEncoder(), request_path, response_path)
    assert hashlib.sha256(response_path.read_bytes()).hexdigest() == GOLDEN_SHA256
    with pytest.raises(EmbedTextsRefused, match="never overwrites"):
        run(FakeEncoder(), request_path, response_path)
    refused = tmp_path / "refused.json"
    request_path.write_text(json.dumps({"format": REQUEST_FORMAT, "texts": []}), encoding="utf-8")
    with pytest.raises(EmbedTextsRefused):
        run(FakeEncoder(), request_path, refused)
    assert not refused.exists() and not list(tmp_path.glob("*.tmp"))


def test_the_command_refuses_outside_the_image_without_importing_a_model_runtime(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(REQUEST, ensure_ascii=False), encoding="utf-8")
    for environment, expected in (
        ({}, "HF_HUB_OFFLINE must be '1'"),
        ({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}, "runs only inside the norms-worker image"),
    ):
        completed = subprocess.run(
            [sys.executable, "-m", "auditmanager.norms.embedding", "embed-texts",
             "--in", str(request_path), "--out", str(tmp_path / "response.json")],
            cwd=ROOT,
            env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT / "src"), **environment},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert completed.returncode == 2, completed.stderr
        assert expected in completed.stderr
        assert not (tmp_path / "response.json").exists()


def test_the_package_imports_no_model_runtime_or_database_driver() -> None:
    probe = (
        "import sys, auditmanager.norms.embedding, auditmanager.norms.embedding.__main__, "
        "auditmanager.norms.embedding.encoder, auditmanager.norms.embedding.builder, "
        "auditmanager.norms.embedding.selftest\n"
        "heavy = sorted(name for name in sys.modules if name.split('.')[0] in "
        "{'torch', 'transformers', 'tokenizers', 'sentence_transformers', 'numpy', 'sqlalchemy', 'psycopg'})\n"
        "print(heavy)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT / "src")},
        capture_output=True, text=True, timeout=60, check=True,
    )
    assert completed.stdout.strip() == "[]"
    assert texts.MAX_TOKENS == 512
