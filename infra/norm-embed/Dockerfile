# syntax=docker/dockerfile:1.7

# norm-embed: the stand's run-time embedder for the norm verification's semantic candidates.
# TEMPORARY (`NORM-VECTOR-TEMP-01`, owner 2026-11-11, variant C) -- docs/program/NORM-VECTOR-TEMP-01.md says why, how it is
# switched on (a quality gate and a memory gate first) and when it goes. The permanent run-time embedder is a database-side
# decision still to be made; the precedents' night encoder (`embedder`, ADR-0029 decision 8) cannot answer inside a run.
#
# Every input is pinned:
#   * the base is the python:3.12-slim-bookworm digest infra/deploy/Dockerfile.api pins;
#   * the three wheels come only from requirements.lock, --require-hashes, --no-deps, --only-binary=:all:;
#   * the model is the int8 export of BGE-M3 at a frozen revision of Xenova/bge-m3, fetched by literal URL and verified by BuildKit
#     against its SHA-256 (ADD --checksum) before any RUN reads it;
#   * the self-check runs with no network, and the image never downloads at run time.
#
# Measured on 2026-11-11 (CPU, 2 threads, arena off): 841 MB resident after load, 917 MB after long texts, 0.45 s per 512-token
# text. One text per request: a batch of sixteen long texts peaked at 2.3 GB.
#
# The build context is the repository root cut down to an allowlist by Dockerfile.dockerignore next to this file.

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NORM_EMBED_MODEL_DIR=/opt/norm-embed/model \
    NORM_EMBED_PORT=8080 \
    NORM_EMBED_THREADS=2

COPY infra/norm-embed/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes --no-deps --only-binary=:all: -r /tmp/requirements.lock \
 && rm /tmp/requirements.lock

ADD --checksum=sha256:a206e10e995aa2a833924bcd725ba5dd6c3425cd34bac3cf2b5677cd2a1c51d6 \
    https://huggingface.co/Xenova/bge-m3/resolve/4de13258303883538bd53b696b452bf8099f0858/onnx/model_int8.onnx \
    /opt/norm-embed/model/model_int8.onnx
ADD --checksum=sha256:6710678b12670bc442b99edc952c4d996ae309a7020c1fa0096dd245c2faf790 \
    https://huggingface.co/Xenova/bge-m3/resolve/4de13258303883538bd53b696b452bf8099f0858/tokenizer.json \
    /opt/norm-embed/model/tokenizer.json

COPY infra/norm-embed/server.py /opt/norm-embed/server.py
RUN chmod -R a+rX /opt/norm-embed
RUN --network=none python /opt/norm-embed/server.py --check

USER nobody
EXPOSE 8080
CMD ["python", "/opt/norm-embed/server.py"]
