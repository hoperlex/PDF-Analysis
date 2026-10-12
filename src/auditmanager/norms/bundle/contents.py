"""The rows and the build as bundle files, and back.

``SnapshotRows`` has no file format of its own (`W54-SNAPSHOT-01` §5): the bundle owns it.

* ``rows/snapshot.json`` -- ``{"format": "auditmanager-bundle-rows/1", "snapshot": {...}}``;
* ``rows/documents.jsonl`` -- one document row per line, ascending ``norm_document_id``;
* ``rows/paragraphs.jsonl`` -- one paragraph row per line, ascending
  ``(norm_document_id, ordinal)``.

Each row is a JSON object with exactly the declared columns of ``snapshot.py`` (no private
key, no timestamp), so the row digest computed from the files equals the one computed from
the origin database.

The build is ``build/chunks-<5 digits>.jsonl`` (format ``auditmanager-bundle-build/1``): one
chunk per line in canonical ``(source_document_ref, ordinal)`` order, keyed by the computed
chunk key (`D-127`), never by a private ``norm_chunk_pk``. Each window carries its vector
base64-encoded (1024 big-endian float32, the one representation ``embedding/vectors.py``
fixes) and its ``embedding_sha256``, which the reader checks before the repository does.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import IO, Any, Final

from ..embedding import vectors
from ..embedding.model import ChunkEmbedding, EmbeddedWindow
from ..snapshot import DocumentRow, ParagraphRow, SnapshotRow, SnapshotRows
from .errors import BundleRefused
from .layout import BUILD_DIR, ROWS_DIR

ROWS_FORMAT: Final[str] = "auditmanager-bundle-rows/1"
BUILD_FORMAT: Final[str] = "auditmanager-bundle-build/1"
SNAPSHOT_FILE: Final[str] = f"{ROWS_DIR}/snapshot.json"
DOCUMENTS_FILE: Final[str] = f"{ROWS_DIR}/documents.jsonl"
PARAGRAPHS_FILE: Final[str] = f"{ROWS_DIR}/paragraphs.jsonl"
#: Chunks per build file: about 9 MB of base64 vectors at the corpus's 1.12 windows/chunk.
CHUNKS_PER_BUILD_FILE: Final[int] = 1024

_WINDOW_KEYS = (
    "window_ordinal", "char_offset", "char_length", "token_count", "paragraph_ordinal_first",
    "paragraph_ordinal_last", "input_sha256", "embedding_sha256", "vector",
)


def _line(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _refuse(message: str) -> BundleRefused:
    return BundleRefused("bundle_rows_invalid", message)


# --- rows -----------------------------------------------------------------------------


def write_rows(directory: Path, rows: SnapshotRows) -> tuple[str, ...]:
    """Write the three row files under ``directory``; return their bundle paths."""
    (directory / ROWS_DIR).mkdir(parents=True, exist_ok=True)
    (directory / SNAPSHOT_FILE).write_bytes(
        (
            json.dumps(
                {"format": ROWS_FORMAT, "snapshot": dataclasses.asdict(rows.snapshot)},
                sort_keys=True,
                indent=1,
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")
    )
    with (directory / DOCUMENTS_FILE).open("wb") as handle:
        for document in sorted(rows.documents, key=lambda row: row.norm_document_id):
            handle.write(_line(dataclasses.asdict(document)))
    with (directory / PARAGRAPHS_FILE).open("wb") as handle:
        for paragraph in sorted(rows.paragraphs, key=lambda row: (row.norm_document_id, row.ordinal)):
            handle.write(_line(dataclasses.asdict(paragraph)))
    return (SNAPSHOT_FILE, DOCUMENTS_FILE, PARAGRAPHS_FILE)


def _typed(cls: type, document: Any, where: str) -> Any:
    if not isinstance(document, dict):
        raise _refuse(f"{where} is not an object")
    fields = {field.name: field for field in dataclasses.fields(cls)}
    if set(document) != set(fields):
        raise _refuse(f"{where} has keys {sorted(document)!r}; expected {sorted(fields)!r}")
    for name, field in fields.items():
        value = document[name]
        allowed = str(field.type)
        if value is None:
            if "None" not in allowed:
                raise _refuse(f"{where}.{name} is null")
        elif "int" in allowed and not ("str" in allowed):
            if not isinstance(value, int) or isinstance(value, bool):
                raise _refuse(f"{where}.{name} is not an integer")
        elif not isinstance(value, str):
            raise _refuse(f"{where}.{name} is not text")
    return cls(**document)


def _jsonl(path: Path) -> Iterator[tuple[int, Any]]:
    with path.open("rb") as handle:
        for number, raw in enumerate(handle, start=1):
            try:
                yield number, json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _refuse(f"{path.name}:{number} is not JSON: {exc}") from None


def read_rows(directory: Path) -> SnapshotRows:
    """The snapshot's rows from the bundle files, each checked against its declared columns."""
    try:
        head = json.loads((directory / SNAPSHOT_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _refuse(f"{SNAPSHOT_FILE} is unreadable: {exc}") from None
    if not isinstance(head, dict) or set(head) != {"format", "snapshot"} or head["format"] != ROWS_FORMAT:
        raise _refuse(f"{SNAPSHOT_FILE} is not {ROWS_FORMAT}")
    snapshot = _typed(SnapshotRow, head["snapshot"], SNAPSHOT_FILE)
    documents = tuple(
        _typed(DocumentRow, value, f"{DOCUMENTS_FILE}:{number}")
        for number, value in _jsonl(directory / DOCUMENTS_FILE)
    )
    paragraphs = tuple(
        _typed(ParagraphRow, value, f"{PARAGRAPHS_FILE}:{number}")
        for number, value in _jsonl(directory / PARAGRAPHS_FILE)
    )
    return SnapshotRows(snapshot=snapshot, documents=documents, paragraphs=paragraphs)


# --- the build ------------------------------------------------------------------------


def build_file(index: int) -> str:
    return f"{BUILD_DIR}/chunks-{index:05d}.jsonl"


class BuildWriter:
    """Writes chunks in the order given, :data:`CHUNKS_PER_BUILD_FILE` to a file."""

    def __init__(self, directory: Path, *, chunks_per_file: int = CHUNKS_PER_BUILD_FILE) -> None:
        self._directory = directory
        self._per_file = chunks_per_file
        self._handle: IO[bytes] | None = None
        self._in_file = 0
        self._last: tuple[str, int] | None = None
        self.paths: list[str] = []
        self.chunks = 0
        self.windows = 0

    def add(self, chunk: ChunkEmbedding) -> None:
        if self._last is not None and not chunk.key > self._last:
            raise BundleRefused(
                "build_order", f"chunk {chunk.key!r} is out of canonical order after {self._last!r}"
            )
        self._last = chunk.key
        if self._handle is None or self._in_file == self._per_file:
            self._rotate()
        assert self._handle is not None
        self._handle.write(
            _line(
                {
                    "document_ref": chunk.document_ref,
                    "chunk_ordinal": chunk.chunk_ordinal,
                    "windows": [
                        {
                            "window_ordinal": window.window_ordinal,
                            "char_offset": window.char_offset,
                            "char_length": window.char_length,
                            "token_count": window.token_count,
                            "paragraph_ordinal_first": window.paragraph_ordinal_first,
                            "paragraph_ordinal_last": window.paragraph_ordinal_last,
                            "input_sha256": window.input_sha256,
                            "embedding_sha256": window.embedding_sha256,
                            "vector": vectors.to_base64(window.vector),
                        }
                        for window in chunk.windows
                    ],
                }
            )
        )
        self._in_file += 1
        self.chunks += 1
        self.windows += len(chunk.windows)

    def _rotate(self) -> None:
        self.close()
        path = build_file(len(self.paths))
        (self._directory / BUILD_DIR).mkdir(parents=True, exist_ok=True)
        self._handle = (self._directory / path).open("wb")
        self.paths.append(path)
        self._in_file = 0

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def write_all(self, chunks: Iterable[ChunkEmbedding]) -> tuple[str, ...]:
        try:
            for chunk in chunks:
                self.add(chunk)
        finally:
            self.close()
        return tuple(self.paths)


def _integer(document: dict[str, Any], key: str, where: str) -> int:
    value = document[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise BundleRefused("bundle_build_invalid", f"{where}.{key} is not an integer")
    return value


def _text(document: dict[str, Any], key: str, where: str) -> str:
    value = document[key]
    if not isinstance(value, str):
        raise BundleRefused("bundle_build_invalid", f"{where}.{key} is not text")
    return value


def iter_build(directory: Path, paths: Iterable[str]) -> Iterator[ChunkEmbedding]:
    """Every chunk of the build files, in file then line order; vectors checked."""
    for path in sorted(paths):
        for number, value in _jsonl(directory / path):
            where = f"{path}:{number}"
            if not isinstance(value, dict) or set(value) != {"document_ref", "chunk_ordinal", "windows"}:
                raise BundleRefused("bundle_build_invalid", f"{where} is not a build chunk")
            windows = []
            for raw in value["windows"] if isinstance(value["windows"], list) else ():
                if not isinstance(raw, dict) or set(raw) != set(_WINDOW_KEYS):
                    raise BundleRefused("bundle_build_invalid", f"{where} holds a malformed window")
                try:
                    packed = vectors.from_base64(raw["vector"])
                except (vectors.VectorRefused, AttributeError) as exc:
                    raise BundleRefused("bundle_build_invalid", f"{where}: {exc}") from None
                window = EmbeddedWindow(
                    window_ordinal=_integer(raw, "window_ordinal", where),
                    char_offset=_integer(raw, "char_offset", where),
                    char_length=_integer(raw, "char_length", where),
                    token_count=_integer(raw, "token_count", where),
                    paragraph_ordinal_first=_integer(raw, "paragraph_ordinal_first", where),
                    paragraph_ordinal_last=_integer(raw, "paragraph_ordinal_last", where),
                    input_sha256=_text(raw, "input_sha256", where),
                    vector=packed,
                )
                if window.embedding_sha256 != raw["embedding_sha256"]:
                    raise BundleRefused(
                        "bundle_build_invalid", f"{where}: a vector does not hash to its embedding_sha256"
                    )
                windows.append(window)
            if not windows:
                raise BundleRefused("bundle_build_invalid", f"{where} holds no window")
            yield ChunkEmbedding(
                document_ref=_text(value, "document_ref", where),
                chunk_ordinal=_integer(value, "chunk_ordinal", where),
                windows=tuple(windows),
            )


__all__ = [
    "BUILD_FORMAT",
    "CHUNKS_PER_BUILD_FILE",
    "DOCUMENTS_FILE",
    "PARAGRAPHS_FILE",
    "ROWS_FORMAT",
    "SNAPSHOT_FILE",
    "BuildWriter",
    "build_file",
    "iter_build",
    "read_rows",
    "write_rows",
]
