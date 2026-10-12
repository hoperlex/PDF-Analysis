"""Offline self-check of the norms-worker image (embedding profile ``bge-m3-dense-v1``).

The image runs this twice: at build time under ``RUN --network=none`` and as its default
command. Both runs prove the same thing: the baked model loads from the frozen revision with
the network absent, under the exact runtime versions the bake-off recorded, and produces one
L2-normalized float32 vector of the profile's dimension through CLS pooling.

Nothing heavy is imported at module level. The repository's static image-contract test reads
the constants below without torch installed, and asserts them against the bake-off record
(``docs/program/NORM_EMBEDDING_BAKEOFF.md``, ``fixtures/evaluation/norms/results/bge-m3.json``)
and the ``0013_norm_embeddings`` profile row, so this file cannot drift from the frozen profile
without a red test.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path


PROFILE_ID = "bge-m3-dense-v1"
REPOSITORY = "BAAI/bge-m3"
REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
POOLING = "cls"
DIMENSIONS = 1024
DTYPE = "float32"
MAX_TOKENS = 512
OVERLAP_TOKENS = 64
SPECIAL_TOKENS = 2
THREADS = 8

#: The exact runtime of the bake-off (``NORM_EMBEDDING_BAKEOFF.md``, "Models and runtime").
RUNTIME = {
    "torch": "2.7.1+cpu",
    "transformers": "4.53.3",
    "sentence_transformers": "5.0.0",
    "tokenizers": "0.21.4",
    "numpy": "2.5.3",
}

#: Every file the image holds for the frozen revision, and nothing else. The dense path needs
#: the sentence-transformers module chain, the XLM-R config and weights, and the tokenizer;
#: the ColBERT/sparse heads and the ONNX export of the same repository are deliberately absent.
MODEL_FILES = (
    "1_Pooling/config.json",
    "README.md",
    "config.json",
    "config_sentence_transformers.json",
    "modules.json",
    "pytorch_model.bin",
    "sentence_bert_config.json",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
)

OFFLINE_ENVIRONMENT = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
}

PROBE_TEXT = "Ширина дверного проёма для маломобильных групп населения"


def snapshot_directory(hf_home: Path) -> Path:
    """The hub-cache snapshot directory of the frozen revision under ``hf_home``."""
    return (
        hf_home
        / "hub"
        / f"models--{REPOSITORY.replace('/', '--')}"
        / "snapshots"
        / REVISION
    )


def _check_files(failures: list[str]) -> None:
    hf_home = os.environ.get("HF_HOME")
    if not hf_home:
        failures.append("HF_HOME is unset")
        return
    snapshot = snapshot_directory(Path(hf_home))
    if not snapshot.is_dir():
        failures.append(f"no snapshot directory for revision {REVISION}: {snapshot}")
        return
    present = sorted(
        path.relative_to(snapshot).as_posix() for path in snapshot.rglob("*") if path.is_file()
    )
    if present != sorted(MODEL_FILES):
        failures.append(f"snapshot files {present} != pinned {sorted(MODEL_FILES)}")


def _check_runtime(failures: list[str]) -> None:
    import numpy
    import sentence_transformers
    import tokenizers
    import torch
    import transformers

    measured = {
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "sentence_transformers": sentence_transformers.__version__,
        "tokenizers": tokenizers.__version__,
        "numpy": numpy.__version__,
    }
    if measured != RUNTIME:
        failures.append(f"runtime {measured} != pinned {RUNTIME}")


def _check_model(failures: list[str]) -> str:
    import torch
    from sentence_transformers import SentenceTransformer
    from transformers import AutoTokenizer

    torch.set_num_threads(THREADS)
    tokenizer = AutoTokenizer.from_pretrained(REPOSITORY, revision=REVISION)
    if not getattr(tokenizer, "is_fast", False):
        failures.append("the tokenizer is not a fast tokenizer; lossless windows need offsets")
    special = tokenizer.num_special_tokens_to_add(pair=False)
    if special != SPECIAL_TOKENS:
        failures.append(f"special tokens {special} != {SPECIAL_TOKENS}")

    model = SentenceTransformer(REPOSITORY, revision=REVISION, device="cpu")
    model.max_seq_length = MAX_TOKENS
    pooling = model[1]
    if not getattr(pooling, "pooling_mode_cls_token", False):
        failures.append("the bundled pooling module is not CLS pooling")
    vectors = model.encode(
        [PROBE_TEXT],
        batch_size=1,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    if tuple(vectors.shape) != (1, DIMENSIONS):
        failures.append(f"vector shape {tuple(vectors.shape)} != (1, {DIMENSIONS})")
    if str(vectors.dtype) != DTYPE:
        failures.append(f"vector dtype {vectors.dtype} != {DTYPE}")
    norm = math.sqrt(float((vectors[0].astype("float64") ** 2).sum()))
    if abs(norm - 1.0) > 1e-5:
        failures.append(f"vector L2 norm {norm} is not 1")
    return f"dim={vectors.shape[1]} dtype={vectors.dtype} norm={norm:.6f}"


def main() -> int:
    failures: list[str] = []
    for name, value in OFFLINE_ENVIRONMENT.items():
        if os.environ.get(name) != value:
            failures.append(f"{name} must be {value!r}, found {os.environ.get(name)!r}")
    _check_files(failures)
    if failures:
        for failure in failures:
            print(f"norms-worker self-check FAILED: {failure}", file=sys.stderr)
        return 1
    _check_runtime(failures)
    measured = _check_model(failures)
    if failures:
        for failure in failures:
            print(f"norms-worker self-check FAILED: {failure}", file=sys.stderr)
        return 1
    print(
        f"norms-worker self-check OK: {PROFILE_ID} {REPOSITORY}@{REVISION} offline {measured}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
