"""The night encoder's entry (`EMBED-01`, `ADR-0029` decision 8): ``embed-texts`` under the window's limits, with the over-length texts set aside.

::

    python /opt/norms-worker/embed_intents.py --in /embed/request.json --out /embed/response.json --over-limit-out /embed/over_limit.json

It is the ``embed-texts`` of ``python -m auditmanager.norms.embedding`` -- the same request, the same response, the same encoder, the same unit-norm
check on every vector -- with the three things the window needs and that command does not do:

* **two threads and a batch of eight** (``THREADS``, ``BATCH``): the window runs next to a 4 GB stand's services, and a smaller batch is a smaller
  peak. The command's own defaults are the bake-off's eight threads and batch sixteen (``profile.py``); they are not changed there, because the
  norms build is measured at them;
* **a text over 512 tokens is not an error of the whole file**: ``embed-texts`` refuses the request at the first one, and a night's batch of a
  thousand cases must not be lost to one long text. Each such text is counted, left out of the encoder and written to ``--over-limit-out``
  with its token count; the worker poisons those intents and the administrator sees them. A text is never cut to fit;
* **a response with nothing in it is a response**: if every text was over the limit the answer is the same document with no vectors.

No database and no network (the image sets the hub offline and the compose service has no network); the files are the whole interface. The
response and the sidecar are never overwritten, as ``embed-texts`` never overwrites.

**It is not in the image.** The service ``embedder`` of ``infra/deploy/compose.server.yml`` mounts this one file read-only at
``/opt/norms-worker/embed_intents.py``: the image (``infra/norms-worker/Dockerfile``, 5.5 GB) already holds the ``auditmanager.norms`` package and the
model, and changing a Dockerfile of that cost for twenty lines of entry would break its pinned build contract
(``tests/integration/composition/test_norms_worker_image_contract.py``) and ask for a rebuild at every edit.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from auditmanager.norms.embedding.checkpoint import write_atomically
from auditmanager.norms.embedding.profile import (
    DIMENSIONS,
    EMBEDDING_PROFILE,
    MAX_TOKENS,
    MODEL_REPOSITORY,
    MODEL_REVISION,
)
from auditmanager.norms.embedding.texts import (
    REQUEST_FORMAT,
    RESPONSE_FORMAT,
    EmbedTextsRefused,
    TextEncoder,
    embed_texts,
    parse_request,
    render,
)

#: The window's limits: two threads (the container has two CPUs) and eight texts to a batch.
THREADS = 2
BATCH = 8
OVER_LIMIT_FORMAT = "auditmanager-embed-over-limit/1"
EXIT_REFUSED = 2


def split_by_length(encoder: TextEncoder, entries: Sequence[tuple[str, str]]) -> tuple[list[tuple[str, str]], list[tuple[str, int]]]:
    """``(encodable, over_limit)``: the entries the encoder can take, and ``(id, token count)`` of the ones over :data:`MAX_TOKENS` tokens."""
    encodable: list[tuple[str, str]] = []
    over: list[tuple[str, int]] = []
    for identifier, text in entries:
        count = encoder.count_tokens(text)
        if count > MAX_TOKENS:
            over.append((identifier, count))
        else:
            encodable.append((identifier, text))
    return encodable, over


def answer(encoder: TextEncoder, request: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """``(response, over_limit)`` for a request document. Raises :class:`EmbedTextsRefused` for a request that is not one."""
    entries = parse_request(request)
    encodable, over = split_by_length(encoder, entries)
    if encodable:
        response = embed_texts(encoder, {"format": REQUEST_FORMAT, "texts": [{"id": i, "text": t} for i, t in encodable]})
    else:
        response = {
            "format": RESPONSE_FORMAT, "embedding_profile": EMBEDDING_PROFILE, "model_repository": MODEL_REPOSITORY,
            "model_revision": MODEL_REVISION, "dimensions": DIMENSIONS, "dtype": "float32", "byte_order": "big", "vectors": [],
        }
    return response, {"format": OVER_LIMIT_FORMAT, "limit": MAX_TOKENS, "entries": [{"id": i, "token_count": c} for i, c in over]}


def load_window_encoder() -> TextEncoder:
    """The real encoder at the window's limits. ``torch`` and the model load here and nowhere else."""
    from auditmanager.norms.embedding.encoder import BgeM3Encoder

    encoder = BgeM3Encoder.load(threads=THREADS)
    encoder._batch_size = BATCH  # the constructor takes it, ``load`` does not; one attribute, set once
    return encoder


def run(encoder: TextEncoder, request_path: Path, response_path: Path, over_limit_path: Path) -> tuple[int, int]:
    """Read the request, write the response and the sidecar atomically, and return ``(vectors, over_limit)``."""
    for path in (response_path, over_limit_path):
        if path.exists():
            raise EmbedTextsRefused(f"{path} exists; the window's encoder never overwrites an answer")
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise EmbedTextsRefused(f"{request_path} is not JSON") from exc
    response, over_limit = answer(encoder, request)
    # The sidecar first: the host reports the container done only after both are in place, and a response without its sidecar is not read.
    write_atomically(over_limit_path, [(json.dumps(over_limit, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")])
    write_atomically(response_path, [render(response)])
    return len(response["vectors"]), len(over_limit["entries"])


def main(argv: Sequence[str] | None = None, *, load: Callable[[], TextEncoder] = load_window_encoder) -> int:
    parser = argparse.ArgumentParser(prog="embed_intents.py", description=__doc__.split("\n", 1)[0])
    parser.add_argument("--in", dest="request", type=Path, required=True)
    parser.add_argument("--out", dest="response", type=Path, required=True)
    parser.add_argument("--over-limit-out", dest="over_limit", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        encoder = load()
        vectors, over = run(encoder, args.request, args.response, args.over_limit)
    except EmbedTextsRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    print(f"embed_intents: {vectors} vectors written to {args.response}, {over} texts over {MAX_TOKENS} tokens set aside")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
