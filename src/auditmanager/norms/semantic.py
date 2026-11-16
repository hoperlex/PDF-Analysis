"""TEMPORARY: norm paragraphs near an observation's meaning (`NORM-VECTOR-TEMP-01`, owner 2026-11-11, variant C).

**This is a stop-gap.** The permanent way for a run to embed its own text is not decided: the precedents' night encoder
(`ADR-0029` decision 8) is the stand's only sanctioned embedder, and it works in a night window over a file exchange, so it cannot
answer inside a run. Until the database side has its own decision, a small service on the stand embeds one text at a time with a
**quantized** BGE-M3 (ONNX int8); the corpus vectors it is compared with were made by the full-precision model of profile
``bge-m3-dense-v1``. The two agree closely but not exactly, so the paragraphs found here are a *candidate* source only -- each one is
still judged by the norm review, never taken as a citation. The service's deployment is a plan
(``docs/program/NORM-VECTOR-TEMP-01.md``); until it is deployed ``AUDITMANAGER_NORM_EMBED_URL`` is unset and nothing here is called.
Remove this module when the permanent embedder lands.

`NORM-ALL-FINDINGS-01`: a query that names a document (``СП 16.13330 ...``) is answered by :func:`semantic_norm_candidates_in_documents` --
the same question, asked only of the windows of the documents the designation resolves to in the snapshot -- never over the whole snapshot.

How it works: the observation's title and description go to the service. The vector goes to the corpus' HNSW index through
:meth:`NormEmbeddingRepository.nearest`, and each nearest window gives one paragraph -- the longest reliable one in the window's
paragraph span -- as a candidate in the exact shape the word search gives (``candidate_not_verified``).
"""

from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from auditmanager.norms.embedding import vectors
from auditmanager.norms.embedding.profile import DIMENSIONS, EMBEDDING_PROFILE
from auditmanager.norms.embedding_repository import NormEmbeddingConflict, NormEmbeddingRepository
from auditmanager.norms.search.display import reader_designation

__all__ = [
    "EMBED_URL_ENV",
    "SEMANTIC_LOOKUP",
    "ScopedSemanticResult",
    "SemanticUnavailable",
    "embed_text",
    "norm_embed_url",
    "observation_text",
    "semantic_norm_candidates",
    "semantic_norm_candidates_in_documents",
]

#: The service's address on the stack's internal network. Unset or blank: the semantic lookup is off.
EMBED_URL_ENV: Final[str] = "AUDITMANAGER_NORM_EMBED_URL"
#: What an observation records when its candidates came from here (``norm_lookup_method``).
SEMANTIC_LOOKUP: Final[str] = "semantic_temporary"
_TIMEOUT_SECONDS: Final[float] = 20.0
_MAX_TEXT_CHARACTERS: Final[int] = 4000
_QUOTE_CHARACTERS: Final[int] = 2000


class SemanticUnavailable(RuntimeError):
    """The service gave no usable vector, or the corpus has no build to search; the caller stops asking for this run."""


def norm_embed_url(environ: Mapping[str, str] | None = None) -> str | None:
    value = (os.environ if environ is None else environ).get(EMBED_URL_ENV, "").strip()
    return value or None


def embed_text(url: str, value: str, *, timeout: float = _TIMEOUT_SECONDS) -> list[float]:
    """The unit vector of ``value`` from the service (``POST {url}/v1/embed`` ``{"texts": [value]}`` → ``{"vectors": [[...]]}``)."""
    body = json.dumps({"texts": [value[:_MAX_TEXT_CHARACTERS]]}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url.rstrip("/") + "/v1/embed", data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 -- an internal, configured address
            answer = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        raise SemanticUnavailable(f"norm-embed did not answer: {type(error).__name__}") from None
    vectors = answer.get("vectors") if isinstance(answer, dict) else None
    if not isinstance(vectors, list) or len(vectors) != 1 or not isinstance(vectors[0], list) or len(vectors[0]) != DIMENSIONS:
        raise SemanticUnavailable("norm-embed answered without one vector of the profile's dimensions")
    try:
        values = [float(component) for component in vectors[0]]
    except (TypeError, ValueError):
        raise SemanticUnavailable("norm-embed answered a vector that is not numbers") from None
    norm = math.sqrt(sum(component * component for component in values))
    if not math.isfinite(norm) or norm == 0.0:
        raise SemanticUnavailable("norm-embed answered a zero or non-finite vector")
    return [component / norm for component in values]


_BUILD = text(
    "SELECT chunking_profile FROM norm_embedding_build "
    "WHERE norms_snapshot_id = :snapshot AND embedding_profile = :profile ORDER BY built_at DESC LIMIT 1"
)
_WINDOW_PARAGRAPH = text(
    """
    SELECT p.norm_paragraph_id, p.clause_number, p.text, p.page_label, d.norm_document_id, d.slug
      FROM norm_embedding e
      JOIN norm_chunk c ON c.norm_chunk_pk = e.norm_chunk_pk
      JOIN norm_document d ON d.norms_snapshot_id = c.norms_snapshot_id AND d.norm_document_pk = c.norm_document_pk
      JOIN norm_paragraph p ON p.norms_snapshot_id = c.norms_snapshot_id AND p.norm_document_pk = c.norm_document_pk
                           AND p.ordinal BETWEEN e.paragraph_ordinal_first AND e.paragraph_ordinal_last
                           AND p.text_reliability = 'reliable'
     WHERE e.norm_chunk_pk = :chunk AND e.window_ordinal = :window
       AND e.norms_snapshot_id = :snapshot AND e.embedding_profile = :profile
     ORDER BY length(p.text) DESC, p.ordinal
     LIMIT 1
    """
)


def semantic_norm_candidates(
    session: Session, *, snapshot_id: str, value: str, url: str, limit: int = 3,
    embed: Callable[[str, str], list[float]] = embed_text,
) -> list[dict[str, Any]]:
    """Up to ``limit`` candidates near ``value``'s meaning, in the word search's candidate shape, nearest first."""
    vector = embed(url, value)
    try:
        return _nearest_paragraphs(session, snapshot_id=snapshot_id, vector=vector, limit=limit)
    except NormEmbeddingConflict as error:
        # An incomplete build or a short HNSW scan (`D-124`): a defect of the corpus side, named, never read as "nothing near".
        raise SemanticUnavailable(f"{type(error).__name__}: {error}") from None


def _nearest_paragraphs(session: Session, *, snapshot_id: str, vector: list[float], limit: int) -> list[dict[str, Any]]:
    build = session.execute(_BUILD, {"snapshot": snapshot_id, "profile": EMBEDDING_PROFILE}).scalar_one_or_none()
    if build is None:
        raise SemanticUnavailable("the snapshot has no embedding build")
    nearest = NormEmbeddingRepository(session).nearest(
        snapshot_id=snapshot_id, chunking_profile=str(build), query=vector, limit=limit * 2)  # type: ignore[arg-type]
    return _window_candidates(session, snapshot_id=snapshot_id, windows=nearest, limit=limit)


# --- `NORM-ALL-FINDINGS-01` (B3): by meaning, inside the document a query names -----------------------------------------------------
#
# A query that names a document ("СП 16.13330 ...", "ГОСТ 5264-80 ...") is a question about that document. The whole-snapshot lookup
# above would answer it with another standard's neighbour, and the any-words fallback with whichever paragraph holds most of the words
# (a concrete modulus of elasticity for an embedded-plate question). This variant asks the same index the same question and keeps only the
# windows of the documents the designation resolves to **in this snapshot**. A designation that resolves to none gives no candidates and
# never another standard.

#: The documents a designation names in a snapshot: the search's own rule (``norms/search/service.py`` ``_DESIGNATION_FILTER``) -- a
#: document matches when the designation's tokens equal its *leading* tokens, so ``СП 54`` finds ``СП_54_13330_2022`` and never
#: ``СП_542_1325800_2024``.
_DOCUMENTS = text(
    """
    SELECT d.norm_document_pk, d.norm_document_id
      FROM norm_document d
     WHERE d.norms_snapshot_id = :snapshot
       AND d.designation_tokens @> norm_designation_tokens(:designation)
       AND d.designation_tokens[1:cardinality(norm_designation_tokens(:designation))] = norm_designation_tokens(:designation)
     ORDER BY d.norm_document_pk
    """
)
#: Exact nearest windows of those documents. ``+ 0`` keeps the ORDER BY from matching the HNSW index: the index is one for every snapshot and
#: document, a filter this narrow is applied after its scan (`D-124`) and a short scan would read as "nothing near". A document holds at most a
#: few thousand windows, so the exact order costs less than the guess and cannot come back short.
_NEAREST_IN_DOCUMENTS = text(
    """
    SELECT e.norm_chunk_pk, e.window_ordinal,
           -(e.embedding <#> CAST(:query AS vector(1024))) AS inner_product
      FROM norm_embedding e
      JOIN norm_chunk c ON c.norm_chunk_pk = e.norm_chunk_pk
     WHERE e.norms_snapshot_id = :snapshot AND e.chunking_profile = :chunking_profile
       AND e.embedding_profile = :profile AND c.norm_document_pk IN :documents
     ORDER BY (e.embedding <#> CAST(:query AS vector(1024))) + 0, e.norm_chunk_pk, e.window_ordinal
     LIMIT :limit
    """
).bindparams(bindparam("documents", expanding=True))


@dataclass(frozen=True, slots=True)
class ScopedSemanticResult:
    """What a document-scoped lookup found: the documents the designation resolved to (none: nothing was searched) and the candidates."""

    designation: str
    document_ids: tuple[str, ...]
    candidates: list[dict[str, Any]]


def semantic_norm_candidates_in_documents(
    session: Session, *, snapshot_id: str, value: str, url: str, designation: str, limit: int = 3,
    embed: Callable[[str, str], list[float]] = embed_text,
) -> ScopedSemanticResult:
    """Up to ``limit`` candidates near ``value``'s meaning among the paragraphs of the documents ``designation`` names, nearest first.

    The designation is resolved first, in the snapshot: when it names no document nothing is embedded and nothing is returned. The
    clause of a query is not a filter here (a meaning search has no clause); the candidates are still ``candidate_not_verified``.
    """
    rows = session.execute(_DOCUMENTS, {"snapshot": snapshot_id, "designation": designation}).all()
    if not rows:
        return ScopedSemanticResult(designation, (), [])
    vector = embed(url, value)
    build = session.execute(_BUILD, {"snapshot": snapshot_id, "profile": EMBEDDING_PROFILE}).scalar_one_or_none()
    if build is None:
        raise SemanticUnavailable("the snapshot has no embedding build")
    try:
        literal = vectors.pgvector_literal(vectors.pack(vector))
    except vectors.VectorRefused as error:
        raise SemanticUnavailable(f"VectorRefused: {error}") from None
    windows = session.execute(_NEAREST_IN_DOCUMENTS, {
        "snapshot": snapshot_id, "chunking_profile": str(build), "profile": EMBEDDING_PROFILE, "query": literal,
        "documents": [int(row.norm_document_pk) for row in rows], "limit": limit * 2}).all()
    nearest = [_Window(chunk_pk=int(row.norm_chunk_pk), window_ordinal=int(row.window_ordinal)) for row in windows]
    return ScopedSemanticResult(designation, tuple(str(row.norm_document_id) for row in rows),
                                _window_candidates(session, snapshot_id=snapshot_id, windows=nearest, limit=limit))


@dataclass(frozen=True, slots=True)
class _Window:
    chunk_pk: int
    window_ordinal: int


def _window_candidates(session: Session, *, snapshot_id: str, windows: Any, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for window in windows:
        row = session.execute(_WINDOW_PARAGRAPH, {"chunk": window.chunk_pk, "window": window.window_ordinal,
                                                  "snapshot": snapshot_id, "profile": EMBEDDING_PROFILE}).one_or_none()
        if row is None or any(candidate["paragraph_id"] == str(row.norm_paragraph_id) for candidate in candidates):
            continue
        candidates.append({"snapshot_id": snapshot_id, "document_id": str(row.norm_document_id),
                           "paragraph_id": str(row.norm_paragraph_id), "designation": reader_designation(str(row.slug)),
                           "clause_number": None if row.clause_number is None else str(row.clause_number),
                           "quote": str(row.text)[:_QUOTE_CHARACTERS], "page_label": int(row.page_label),
                           "status": "candidate_not_verified"})
        if len(candidates) >= limit:
            break
    return candidates


def observation_text(item: Mapping[str, Any]) -> str:
    """What is embedded for an observation: its title and description."""
    return "\n".join(part for part in (str(item.get("title") or "").strip(), str(item.get("description") or "").strip()) if part)
