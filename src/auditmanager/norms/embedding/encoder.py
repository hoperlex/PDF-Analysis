"""The real ``bge-m3-dense-v1`` encoder, for the norms-worker image only.

``torch``, ``transformers`` and ``sentence_transformers`` are imported inside
:meth:`BgeM3Encoder.load`, never at module level: they are not in the root lock
(`W54-PLAN.md` §3.4), and every other module of this package must import without them.

The load is refused unless the hub is offline (``HF_HUB_OFFLINE=1``, ``TRANSFORMERS_OFFLINE=1``),
so a missing baked file is an error, never a download. The model is loaded exactly as the
bake-off loaded it — the frozen revision, CPU, ``max_seq_length = 512``, eight threads, batch
16, ``normalize_embeddings=True`` — and every vector is checked to be 1024 float32 values of unit
norm before it leaves.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

from . import vectors
from .profile import (
    DIMENSIONS,
    ENCODE_BATCH_SIZE,
    MAX_TOKENS,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    SPECIAL_TOKENS,
    THREADS,
)

OFFLINE_ENVIRONMENT = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}


class EncoderRefused(RuntimeError):
    """The runtime cannot embed under the frozen profile."""


def require_offline(environ: dict[str, str] | None = None) -> None:
    environment = os.environ if environ is None else environ
    for name, value in OFFLINE_ENVIRONMENT.items():
        if environment.get(name) != value:
            raise EncoderRefused(
                f"{name} must be {value!r} (found {environment.get(name)!r}); the embedder runs "
                "only offline, inside the norms-worker image"
            )


class BgeM3Encoder:
    """Tokenizer and model of the frozen revision."""

    def __init__(self, tokenizer: Any, model: Any, *, batch_size: int = ENCODE_BATCH_SIZE) -> None:
        self.tokenizer = tokenizer
        self._model = model
        self._batch_size = batch_size

    @classmethod
    def load(cls, *, threads: int = THREADS) -> BgeM3Encoder:
        require_offline()
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise EncoderRefused(
                f"{exc.name or 'the model runtime'} is not installed here; the embedder's model "
                "runs only inside the norms-worker image (infra/norms-worker)"
            ) from exc

        torch.set_num_threads(threads)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_REPOSITORY, revision=MODEL_REVISION)
        if not getattr(tokenizer, "is_fast", False):
            raise EncoderRefused("the tokenizer is not a fast tokenizer; windows need offsets")
        if tokenizer.num_special_tokens_to_add(pair=False) != SPECIAL_TOKENS:
            raise EncoderRefused("the tokenizer does not add exactly two special tokens")
        model = SentenceTransformer(MODEL_REPOSITORY, revision=MODEL_REVISION, device="cpu")
        model.max_seq_length = MAX_TOKENS
        if not getattr(model[1], "pooling_mode_cls_token", False):
            raise EncoderRefused("the bundled pooling module is not CLS pooling")
        return cls(tokenizer, model)

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=True, truncation=False))

    def encode(self, texts: Sequence[str]) -> list[bytes]:
        if not texts:
            return []
        matrix = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        if tuple(matrix.shape) != (len(texts), DIMENSIONS) or str(matrix.dtype) != "float32":
            raise EncoderRefused(
                f"the model returned {tuple(matrix.shape)} {matrix.dtype}, "
                f"expected ({len(texts)}, {DIMENSIONS}) float32"
            )
        return [vectors.pack(row) for row in matrix.tolist()]
