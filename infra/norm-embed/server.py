"""norm-embed: one text in, one BGE-M3 vector out (`NORM-VECTOR-TEMP-01`, TEMPORARY -- docs/program/NORM-VECTOR-TEMP-01.md).

The stand's run-time embedder for the norm verification's semantic candidates, until the database side gets its own embedder decision
(the precedents' night encoder, ADR-0029 decision 8, cannot answer inside a run). It serves the **int8-quantized** BGE-M3 export
(``Xenova/bge-m3`` ``onnx/model_int8.onnx``) baked into the image; the corpus vectors it is compared with are the full-precision
``bge-m3-dense-v1`` ones, which is why ``docs/program/NORM-VECTOR-TEMP-01.md`` puts a quality gate before the worker is pointed here.

Protocol (internal network only, no published port):

* ``POST /v1/embed`` ``{"texts": [str]}`` (one text: a batch of 16 long texts peaks at 2.3 GB, one at 0.92 GB; the stand has ~2 GB) → ``{"vectors": [[1024 floats], ...]}``: CLS pooling of the last hidden
  state, L2-normalised -- the dense head of BGE-M3, as the profile's ``normalize_embeddings=True`` CLS pooling;
* ``GET /healthz`` → ``{"status": "ok", "model": ..., "dimensions": 1024}``.

Texts are truncated at 512 tokens, as the profile's ``max_seq_length``. Standard library HTTP; nothing is logged but the request shape.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import numpy
import onnxruntime
from tokenizers import Tokenizer

MODEL_DIR = os.environ.get("NORM_EMBED_MODEL_DIR", "/opt/norm-embed/model")
MODEL_NAME = "Xenova/bge-m3@4de13258303883538bd53b696b452bf8099f0858 onnx/model_int8.onnx"
DIMENSIONS = 1024
MAX_TOKENS = 512
MAX_TEXTS = 1
MAX_BODY_BYTES = 1_000_000
THREADS = int(os.environ.get("NORM_EMBED_THREADS", "2"))


class Embedder:
    def __init__(self, model_dir: str = MODEL_DIR, threads: int = THREADS) -> None:
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = False  # 841 MB resident after load instead of 1 184 MB (measured 2026-11-11)
        self._session = onnxruntime.InferenceSession(os.path.join(model_dir, "model_int8.onnx"), options,
                                                     providers=["CPUExecutionProvider"])
        self._inputs = {item.name for item in self._session.get_inputs()}
        if not {"input_ids", "attention_mask"} <= self._inputs:
            raise RuntimeError(f"unexpected model inputs: {sorted(self._inputs)}")
        self._tokenizer = Tokenizer.from_file(os.path.join(model_dir, "tokenizer.json"))
        self._tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self._lock = threading.Lock()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(value) for value in texts]  # one at a time: memory, not throughput, is the stand's constraint

    def _embed_one(self, value: str) -> list[float]:
        encoding = self._tokenizer.encode(value)
        ids = numpy.array([encoding.ids], dtype=numpy.int64)
        mask = numpy.array([encoding.attention_mask], dtype=numpy.int64)
        feed: dict[str, Any] = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._inputs:
            feed["token_type_ids"] = numpy.zeros_like(ids)
        with self._lock:  # one inference at a time: the stand's memory, not throughput, is the constraint
            hidden = self._session.run(None, feed)[0]
        if hidden.ndim != 3 or hidden.shape[-1] != DIMENSIONS:
            raise RuntimeError(f"unexpected model output shape {hidden.shape}")
        cls = hidden[0, 0, :].astype(numpy.float64)
        norm = float(numpy.linalg.norm(cls))
        if not numpy.isfinite(norm) or norm == 0.0:
            raise RuntimeError("a zero or non-finite vector")
        return (cls / norm).astype(numpy.float32).tolist()


def _handler(embedder: Embedder) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "norm-embed/1"

        def _send(self, status: int, body: dict[str, Any]) -> None:
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/healthz":
                self._send(200, {"status": "ok", "model": MODEL_NAME, "dimensions": DIMENSIONS})
            else:
                self._send(404, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/embed":
                self._send(404, {"error": "not_found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if not 0 < length <= MAX_BODY_BYTES:
                self._send(413, {"error": "body_size"})
                return
            try:
                texts = json.loads(self.rfile.read(length).decode("utf-8")).get("texts")
            except (ValueError, AttributeError):
                self._send(400, {"error": "body_invalid"})
                return
            if (not isinstance(texts, list) or not 1 <= len(texts) <= MAX_TEXTS
                    or any(not isinstance(item, str) or not item.strip() for item in texts)):
                self._send(400, {"error": "texts_invalid"})
                return
            try:
                self._send(200, {"vectors": embedder.embed(texts)})
            except RuntimeError as error:
                self._send(500, {"error": "embed_failed", "detail": str(error)[:200]})

        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("norm-embed %s %s\n" % (self.command, self.path))

    return Handler


def self_check(embedder: Embedder) -> None:
    """Run at build (no network) and at start: one vector of the right shape and unit norm, and a sane neighbour order."""
    vectors = numpy.array(embedder.embed(["катет углового сварного шва", "минимальный катет сварного шва", "лестница жилого дома"]))
    if vectors.shape != (3, DIMENSIONS) or not numpy.allclose(numpy.linalg.norm(vectors, axis=1), 1.0, atol=1e-3):
        raise SystemExit(f"self-check: bad vectors {vectors.shape}")
    near, far = float(vectors[0] @ vectors[1]), float(vectors[0] @ vectors[2])
    if not near > far:
        raise SystemExit(f"self-check: similar texts are not nearer ({near:.3f} <= {far:.3f})")
    print(f"norm-embed self-check ok: near {near:.3f} > far {far:.3f}", flush=True)


def main() -> None:
    embedder = Embedder()
    self_check(embedder)
    if "--check" in sys.argv:
        return
    port = int(os.environ.get("NORM_EMBED_PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), _handler(embedder)).serve_forever()  # noqa: S104 -- the stack's internal network only


if __name__ == "__main__":
    main()
