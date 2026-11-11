"""The quality gate of the TEMPORARY run-time embedder (`NORM-VECTOR-TEMP-01`, docs/program/NORM-VECTOR-TEMP-01.md, step 3).

The stand's ``norm-embed`` serves the int8 export of BGE-M3; the corpus vectors were made by the full-precision model of profile
``bge-m3-dense-v1``. Before the worker is pointed at the service this asks, on a fixed sample of corpus windows, whether the two
agree well enough to search the corpus' index with the service's vectors:

* the inner product of the service's vector of a window's own text with the stored vector of that window -- mean ≥ 0.97 (owner);
* self-recall@10 -- the window is among the ten nearest of its own text through the HNSW index -- ≥ 0.90 (owner).

Run inside the worker container (it has the database and the stack's network)::

    docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml exec -T worker \\
        python -m auditmanager.norms.semantic_check --url http://norm-embed:8080 --windows 500

It reads and writes nothing else, prints one JSON line, and exits 0 on PASS and 1 on FAIL. Remove it with the stop-gap.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from sqlalchemy import text

from auditmanager.norms.embedding.profile import EMBEDDING_PROFILE
from auditmanager.norms.embedding_repository import NormEmbeddingRepository
from auditmanager.norms.semantic import embed_text

MIN_MEAN_INNER_PRODUCT: Final[float] = 0.97
MIN_SELF_RECALL_AT_10: Final[float] = 0.90

_CURRENT_SNAPSHOT = text("SELECT norms_snapshot_id FROM norm_current_snapshot ORDER BY 1 LIMIT 1")
_BUILD = text(
    "SELECT chunking_profile FROM norm_embedding_build "
    "WHERE norms_snapshot_id = :snapshot AND embedding_profile = :profile ORDER BY built_at DESC LIMIT 1"
)
_SAMPLE = text(
    """
    SELECT e.norm_chunk_pk, e.window_ordinal, substr(c.text, e.char_offset + 1, e.char_length) AS window_text,
           e.embedding::text AS stored
      FROM norm_embedding e
      JOIN norm_chunk c ON c.norm_chunk_pk = e.norm_chunk_pk
     WHERE e.norms_snapshot_id = :snapshot AND e.chunking_profile = :chunking AND e.embedding_profile = :profile
     ORDER BY md5(e.norm_embedding_pk::text)
     LIMIT :windows
    """
)


@dataclass(frozen=True, slots=True)
class WindowResult:
    inner_product: float
    found_in_top10: bool


def parse_vector(literal: str) -> list[float]:
    """A pgvector text literal (``[0.1,0.2,...]``) as floats."""
    return [float(value) for value in literal.strip().strip("[]").split(",")]


def inner_product(left: Sequence[float], right: Sequence[float]) -> float:
    return math.fsum(a * b for a, b in zip(left, right, strict=True))


def verdict(results: Sequence[WindowResult]) -> dict[str, object]:
    """The gate's summary: the two measures, the thresholds and PASS or FAIL. No window is no verdict but FAIL."""
    count = len(results)
    mean = math.fsum(result.inner_product for result in results) / count if count else 0.0
    ordered = sorted(result.inner_product for result in results)
    p05 = ordered[max(0, math.ceil(0.05 * count) - 1)] if count else 0.0
    recall = sum(result.found_in_top10 for result in results) / count if count else 0.0
    passed = count > 0 and mean >= MIN_MEAN_INNER_PRODUCT and recall >= MIN_SELF_RECALL_AT_10
    return {"windows": count, "mean_inner_product": round(mean, 4), "p05_inner_product": round(p05, 4),
            "self_recall_at_10": round(recall, 4), "min_mean_inner_product": MIN_MEAN_INNER_PRODUCT,
            "min_self_recall_at_10": MIN_SELF_RECALL_AT_10, "verdict": "PASS" if passed else "FAIL"}


def run(url: str, windows: int, snapshot: str | None = None) -> dict[str, object]:
    from auditmanager.shared.db.session import get_session_factory

    with get_session_factory()() as session:
        snapshot_id = snapshot or session.execute(_CURRENT_SNAPSHOT).scalar_one()
        chunking = session.execute(_BUILD, {"snapshot": snapshot_id, "profile": EMBEDDING_PROFILE}).scalar_one()
        rows = session.execute(_SAMPLE, {"snapshot": snapshot_id, "chunking": chunking, "profile": EMBEDDING_PROFILE,
                                         "windows": windows}).all()
        repository = NormEmbeddingRepository(session)
        results = []
        for row in rows:
            vector = embed_text(url, str(row.window_text))
            nearest = repository.nearest(snapshot_id=snapshot_id, chunking_profile=str(chunking), query=vector, limit=10)
            results.append(WindowResult(
                inner_product=inner_product(vector, parse_vector(str(row.stored))),
                found_in_top10=any((hit.chunk_pk, hit.window_ordinal) == (row.norm_chunk_pk, row.window_ordinal) for hit in nearest)))
    return {"snapshot": snapshot_id, "chunking_profile": chunking, **verdict(results)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m auditmanager.norms.semantic_check")
    parser.add_argument("--url", required=True)
    parser.add_argument("--windows", type=int, default=500)
    parser.add_argument("--snapshot")
    arguments = parser.parse_args(argv)
    summary = run(arguments.url, arguments.windows, arguments.snapshot)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
