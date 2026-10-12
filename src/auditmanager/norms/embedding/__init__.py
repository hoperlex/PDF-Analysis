"""The resumable, batch-bounded embedder of normative chunks (``bge-m3-dense-v1``).

A build has three phases, each restartable (``W54-PLAN.md`` §3.4)::

    prepare   host, DATABASE_URL     the chunk set -> plan.json + inputs/batch-*.jsonl
    build     norms-worker image,     inputs -> vectors/batch-*.jsonl (+ .sha256), skipping
              --network none          every verified batch; resumable across night windows
    load      host, DATABASE_URL     every verified checkpoint -> one transaction ending with
                                      the completion row

``embed-texts`` is the batch entry point for later waves (W57): a request file in, a response
file of base64 float32 vectors with the profile, model revision and SHA-256 out.

This package imports nothing outside the standard library and ``auditmanager.norms`` at module
level. ``encoder`` imports ``torch``/``transformers``/``sentence_transformers`` only inside
:meth:`~auditmanager.norms.embedding.encoder.BgeM3Encoder.load`, and ``operations`` (which needs
SQLAlchemy) is imported only by the ``prepare`` and ``load`` commands.
"""

from .checkpoint import (
    DEFAULT_BATCH_CHUNKS,
    BatchState,
    BuildIdentity,
    CheckpointRefused,
    Plan,
    checkpoint_digest,
    prepare_plan,
    read_plan,
)
from .digest import EMBEDDING_SET_DIGEST_VERSION, EmbeddingSetDigest
from .model import ChunkEmbedding, ChunkInput, EmbeddedWindow
from .profile import EMBEDDING_PROFILE, MAX_TOKENS, MODEL_REVISION, OVERLAP_TOKENS
from .texts import REQUEST_FORMAT, RESPONSE_FORMAT, EmbedTextsRefused
from .windowing import WindowingRefused, WindowSpan, verify_window_set, window_spans

__all__ = [
    "DEFAULT_BATCH_CHUNKS",
    "EMBEDDING_PROFILE",
    "EMBEDDING_SET_DIGEST_VERSION",
    "MAX_TOKENS",
    "MODEL_REVISION",
    "OVERLAP_TOKENS",
    "REQUEST_FORMAT",
    "RESPONSE_FORMAT",
    "BatchState",
    "BuildIdentity",
    "CheckpointRefused",
    "ChunkEmbedding",
    "ChunkInput",
    "EmbedTextsRefused",
    "EmbeddedWindow",
    "EmbeddingSetDigest",
    "Plan",
    "WindowSpan",
    "WindowingRefused",
    "checkpoint_digest",
    "prepare_plan",
    "read_plan",
    "verify_window_set",
    "window_spans",
]
