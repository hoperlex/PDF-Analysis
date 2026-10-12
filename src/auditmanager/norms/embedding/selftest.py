"""The embedder's own offline check, run at image build time under ``RUN --network=none``.

It proves, with the real tokenizer and model of the frozen revision, that the baked embedder
imports and runs end to end: an over-limit synthetic text is cut into several windows that
form its full window set (`D-127`), every window is embedded to a unit float32 vector, and
``embed-texts`` answers a two-text request canonically. Equality of the windows with the
bake-off runner's is a separate window step (``infra/norms-worker/check_windows.py``), because
the runner is not part of the image.
"""

from __future__ import annotations

from typing import Any

from .builder import embed_batch
from .model import ChunkInput
from .texts import REQUEST_FORMAT, embed_texts, render

#: Long enough to need several 512-token windows; Russian, numbered, with a table row.
_CLAUSE = (
    "{n}. Ширина дверного проёма в свету для маломобильных групп населения должна быть не менее "
    "0,9 м, а высота порога не более 0,014 м; | {n} | Предел огнестойкости | REI 45 |"
)
SELF_TEST_TEXT = " ".join(_CLAUSE.format(n=number) for number in range(1, 61))


def run_self_test(encoder: Any) -> str:
    chunk = ChunkInput(
        document_ref="self-test",
        chunk_ordinal=0,
        text=SELF_TEST_TEXT,
        paragraph_ordinal_first=0,
        paragraph_ordinal_last=0,
        paragraph_lengths=(len(SELF_TEST_TEXT),),
    )
    (embedding,) = embed_batch(encoder, [chunk])
    if len(embedding.windows) < 2:
        raise RuntimeError("the self-test text did not need more than one window")
    request = {
        "format": REQUEST_FORMAT,
        "texts": [{"id": "a", "text": "Высота ограждения лестничного марша"}, {"id": "b", "text": "Ширина эвакуационного выхода"}],
    }
    first = render(embed_texts(encoder, request))
    second = render(embed_texts(encoder, request))
    if first != second:
        raise RuntimeError("embed-texts gave two different responses to one request")
    tokens = sum(window.token_count for window in embedding.windows)
    return (
        f"norms-worker embedder self-test OK: windows={len(embedding.windows)} "
        f"tokens={tokens} embed-texts=stable"
    )
