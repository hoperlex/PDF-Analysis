# syntax=docker/dockerfile:1.7

# The norms worker: BGE-M3 under the frozen embedding profile `bge-m3-dense-v1`
# (docs/program/NORM_EMBEDDING_BAKEOFF.md) on a pinned CPU runtime, with the model baked in and
# no network at run time. Owner W54-BGE-IMAGE, successor writer W54-EMBED-01 (W54-PLAN.md §6),
# which baked the embedder in.
#
# Every input has an immutable identity, and this file has no build argument, so none of them
# can be redirected from a call site:
#   * the base is a literal tag-plus-index-digest FROM -- the python:3.12-slim-bookworm digest
#     infra/deploy/Dockerfile.api already pins (resolved 2026-09-18);
#   * the wheel closure comes only from requirements.lock, installed with --require-hashes,
#     --no-deps and --only-binary=:all:, so nothing is resolved or compiled at build time;
#   * every model file is fetched from the frozen revision by a literal URL and verified by
#     BuildKit against its SHA-256 (ADD --checksum) before any RUN can read it. Only the files
#     the dense path reads are fetched; the ColBERT/sparse heads and the ONNX export are not.
#
# PINS PENDING. A value recorded nowhere in the repository is not invented here: it is spelled
# TODO-PIN-WINDOW and listed under images.norms_worker.pending_pins in
# docs/program/FOUNDATION_LOCK.json, and the image-contract test keeps the two lists equal.
# A TODO-PIN-WINDOW checksum is not a digest, so BuildKit cannot complete that ADD, and the
# first RUN refuses a wheel lock that still carries the marker. An unpinned build fails; it
# never falls back to an unverified download.
#
# Network: the build fetches the pinned inputs; both self-checks then run under
# RUN --network=none, and the image sets HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 for every
# later process. reproduce-mrr.sh, check-windows.sh and run-build.sh run it with
# `docker run --network none`.
#
# The embedder (W54-EMBED-01). The image carries the repository's own
# src/auditmanager/norms package, which the build and embed-texts entry points
# (`python -m auditmanager.norms.embedding ...`) need; it imports only the standard library and
# the runtime above. The build context is therefore the repository root, cut down to an
# allowlist by infra/norms-worker/Dockerfile.dockerignore (BuildKit reads it in place of the
# root .dockerignore), so nothing else of the checkout -- above all no .local/ corpus byte --
# reaches the daemon. The code layers come after the model layers, so a code change rebuilds
# seconds of layers, not the 2.3 GB model.
#
# Build (HEAVY STEP, W54-FREEZE-01: about 6.5 GB, 3.2 GiB, 450 s), from the repository root:
#   docker build --file infra/norms-worker/Dockerfile \
#     --tag auditmanager-norms-worker:bge-m3-dense-v1-5617a9f .
FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY infra/norms-worker/requirements.lock /opt/norms-worker/requirements.lock
RUN set -eu; \
    if grep -q 'TODO-PIN' /opt/norms-worker/requirements.lock; then \
      echo "refused: infra/norms-worker/requirements.lock still carries a TODO-PIN marker;" \
           "measure the hashed wheel closure first (docs/program/W54-BGE-IMAGE.md)" >&2; \
      exit 1; \
    fi; \
    python -m venv /opt/norms-worker/venv; \
    /opt/norms-worker/venv/bin/pip install \
      --require-hashes --no-deps --only-binary=:all: \
      --requirement /opt/norms-worker/requirements.lock

# The frozen revision's files, laid out as a Hugging Face hub-cache snapshot of that commit, so
# `from_pretrained("BAAI/bge-m3", revision="5617a9f...")` resolves them with the hub offline.
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/1_Pooling/config.json \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/1_Pooling/config.json
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/README.md \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/README.md
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/config.json \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/config.json
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/config_sentence_transformers.json \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/config_sentence_transformers.json
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/modules.json \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/modules.json
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/pytorch_model.bin \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/pytorch_model.bin
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/sentence_bert_config.json \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/sentence_bert_config.json
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/sentencepiece.bpe.model \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/sentencepiece.bpe.model
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/special_tokens_map.json \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/special_tokens_map.json
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/tokenizer.json \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/tokenizer.json
ADD --chmod=0444 --checksum=sha256:TODO-PIN-WINDOW \
    https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/tokenizer_config.json \
    /opt/norms-worker/hf/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/tokenizer_config.json

COPY infra/norms-worker/self_check.py /opt/norms-worker/self_check.py
COPY src/auditmanager/__init__.py /opt/norms-worker/src/auditmanager/__init__.py
COPY src/auditmanager/norms/ /opt/norms-worker/src/auditmanager/norms/

ENV PATH=/opt/norms-worker/venv/bin:$PATH \
    PYTHONPATH=/opt/norms-worker/src \
    HF_HOME=/opt/norms-worker/hf \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=8 \
    MKL_NUM_THREADS=8 \
    AUDITMANAGER_EMBEDDING_PROFILE=bge-m3-dense-v1

# Proves, with the network absent, that the pinned files are exactly the snapshot, that the
# runtime versions are the bake-off's, and that one probe text embeds to a unit float32 vector
# of 1024 dimensions through CLS pooling.
RUN --network=none python /opt/norms-worker/self_check.py

# Proves, offline, that the baked embedder runs end to end on the real tokenizer and model: an
# over-limit text becomes its full window set, every window embeds to a unit vector, and
# embed-texts answers one request byte-identically twice.
RUN --network=none python -m auditmanager.norms.embedding self-test

RUN useradd --system --no-create-home --home-dir /tmp --uid 10001 norms

LABEL org.opencontainers.image.title="AuditManager norms worker (BGE-M3)" \
      org.opencontainers.image.base.name="python:3.12-slim-bookworm" \
      org.opencontainers.image.source="https://github.com/hoperlex/PDF-Analysis" \
      io.auditmanager.embedding.profile="bge-m3-dense-v1" \
      io.auditmanager.embedding.repository="BAAI/bge-m3" \
      io.auditmanager.embedding.revision="5617a9f61b028005a4858fdac845db406aefb181" \
      io.auditmanager.embedding.entry="python -m auditmanager.norms.embedding"

USER 10001
WORKDIR /work
CMD ["python", "/opt/norms-worker/self_check.py"]
