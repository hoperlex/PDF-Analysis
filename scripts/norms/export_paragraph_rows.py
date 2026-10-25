"""Read-only export of norm paragraph rows for the AR beta map toolchain.

``map_pack`` (``AR-V3-BETA-MAP-TOOL-01``) turns a decision file plus PARAGRAPH ROWS into the
six scope maps and checks each scope's target-only prompt part against the 22,000-character
cap. This script produces those rows from the promotion/custody database, for exactly the
spans it is asked for::

    DATABASE_URL=... python scripts/norms/export_paragraph_rows.py \
        --spans spans.json --snapshot ns_... --out .local/ar-v3-draft/paragraphs.json

``--measure`` prints, instead of rows, one JSON object of numbers per span (existence of every
ordinal, counts, character lengths, ids, digests) and no corpus text::

    python scripts/norms/export_paragraph_rows.py --spans spans.json --snapshot ns_... --measure

The spans file is a JSON list of ``{"norm_document_id", "ordinal_first", "ordinal_last"}``
(inclusive ordinals). Spans may overlap; each paragraph is exported once.

Guarantees: the database is only read, inside one ``REPEATABLE READ READ ONLY`` transaction
that is checked to be read-only before the first query; paragraphs come from the public
``norms`` reads (``get_norm_document``, ``list_norm_paragraphs``), never from SQL here. The
exporter refuses (``REFUSED: <code>`` on stderr, exit 2), and creates no file, for an
unknown document, a document of another snapshot, a missing first/last ordinal, a gap inside
a range, a paragraph the snapshot marks unreliable, rows ``map_pack`` would not accept, an
output that already exists, and an output path inside the repository tree (outside
``.local/``): the rows are corpus text, which must never enter git. The output file is
created exclusively (``O_EXCL``) with mode 0600. Nothing is repaired or skipped silently.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, NoReturn, Protocol

# Standalone operator invocation from a checkout, like other repository scripts.
_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from auditmanager.analysis.profiles.ar_v3.norm_map.map_pack import (  # noqa: E402
    PARAGRAPHS_VERSION,
    MapPackRefused,
    parse_paragraphs,
)
from auditmanager.norms.public import get_norm_document, list_norm_paragraphs  # noqa: E402
from auditmanager.shared.db.config import (  # noqa: E402
    DATABASE_URL_VAR,
    DatabaseSettings,
    parse_database_url,
)
from auditmanager.shared.db.engine import create_database_engine  # noqa: E402
from auditmanager.shared.db.errors import DatabaseConfigurationError  # noqa: E402
from auditmanager.shared.errors import DomainError, ErrorCode  # noqa: E402
from auditmanager.shared.identity import NormDocumentId, NormsSnapshotId  # noqa: E402

MEASURE_VERSION: Final[str] = "ar-beta-span-measure-v1"
MAX_SPANS_BYTES: Final[int] = 1_000_000
MAX_SPANS: Final[int] = 1_000
#: The database column is a 32-bit integer; a larger ordinal can name nothing.
MAX_ORDINAL: Final[int] = 2_147_483_647
#: A span is a clause or a table, never a document: the bound also bounds every loop below.
MAX_SPAN_PARAGRAPHS: Final[int] = 5_000
PAGE_SIZE: Final[int] = 500
#: The longest list of missing ordinals one measured span reports (the count is exact).
MAX_LISTED_ORDINALS: Final[int] = 50
_SPAN_KEYS: Final[frozenset[str]] = frozenset({
    "norm_document_id", "ordinal_first", "ordinal_last",
})


class ExportRefused(ValueError):
    """The request cannot be served; the message is the reason code."""


def _refuse(code: str) -> NoReturn:
    raise ExportRefused(code)


@dataclass(frozen=True, slots=True)
class Span:
    norm_document_id: str
    ordinal_first: int
    ordinal_last: int


@dataclass(frozen=True, slots=True)
class DocumentFacts:
    norm_document_id: str
    norms_snapshot_id: str
    designation: str
    title: str


@dataclass(frozen=True, slots=True)
class ParagraphFacts:
    norm_paragraph_id: str
    ordinal: int
    page_label: int
    clause_number: str | None
    text: str
    reliable: bool


class ParagraphSource(Protocol):
    """What the exporter needs from the corpus; the database adapter and test fakes provide it."""

    def document(self, norm_document_id: str) -> DocumentFacts | None: ...

    def paragraphs(
        self, norm_document_id: str, *, through_ordinal: int,
    ) -> Sequence[ParagraphFacts]: ...


# ---------------------------------------------------------------- spans file

def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _refuse("spans_file_invalid")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    _refuse("spans_file_invalid")


def _identity(value: object, identity: type, code: str) -> str:
    if not isinstance(value, str):
        _refuse(code)
    try:
        identity.parse(value)  # type: ignore[attr-defined]
    except (TypeError, ValueError):
        _refuse(code)
    return value


def parse_snapshot_id(value: object) -> str:
    return _identity(value, NormsSnapshotId, "snapshot_id_invalid")


def parse_spans(raw: bytes) -> tuple[Span, ...]:
    """Strictly read the spans file; every defect is the one code ``spans_file_invalid``."""
    code = "spans_file_invalid"
    if len(raw) > MAX_SPANS_BYTES:
        _refuse(code)
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                             parse_constant=_reject_constant)
    except ExportRefused:
        raise
    except (ValueError, RecursionError):
        # Bad UTF-8, bad JSON, and the plain ValueError of a 5,000-digit integer (beyond
        # Python's int/str conversion limit) all end as this code, not a traceback.
        _refuse(code)
    if not isinstance(payload, list) or not 1 <= len(payload) <= MAX_SPANS:
        _refuse(code)
    spans: list[Span] = []
    for entry in payload:
        if not isinstance(entry, dict) or set(entry) != _SPAN_KEYS:
            _refuse(code)
        document = _identity(entry["norm_document_id"], NormDocumentId, code)
        first, last = entry["ordinal_first"], entry["ordinal_last"]
        if (type(first) is not int or type(last) is not int or first < 0
                or last < first or last > MAX_ORDINAL
                or last - first + 1 > MAX_SPAN_PARAGRAPHS):
            _refuse(code)
        spans.append(Span(document, first, last))
    return tuple(sorted(set(spans), key=lambda span: (
        span.norm_document_id, span.ordinal_first, span.ordinal_last)))


# ---------------------------------------------------------------- collection

@dataclass(frozen=True, slots=True)
class _Loaded:
    document: DocumentFacts
    by_ordinal: dict[int, ParagraphFacts]


def _load(
    source: ParagraphSource, spans: Sequence[Span], snapshot_id: str,
) -> dict[str, _Loaded]:
    """Read every named document once, up to its highest requested ordinal."""
    through: dict[str, int] = {}
    for span in spans:
        through[span.norm_document_id] = max(
            through.get(span.norm_document_id, 0), span.ordinal_last)
    loaded: dict[str, _Loaded] = {}
    for document_id in sorted(through):
        document = source.document(document_id)
        if document is None:
            _refuse(f"document_unknown:{document_id}")
        if (document.norm_document_id != document_id
                or document.norms_snapshot_id != snapshot_id):
            _refuse(f"document_not_in_snapshot:{document_id}")
        by_ordinal: dict[int, ParagraphFacts] = {}
        for paragraph in source.paragraphs(document_id, through_ordinal=through[document_id]):
            if paragraph.ordinal in by_ordinal:
                _refuse(f"paragraph_ordinal_duplicate:{document_id}:{paragraph.ordinal}")
            by_ordinal[paragraph.ordinal] = paragraph
        loaded[document_id] = _Loaded(document, by_ordinal)
    return loaded


def _row(document: DocumentFacts, paragraph: ParagraphFacts) -> dict[str, Any]:
    return {
        "norm_document_id": document.norm_document_id,
        "norm_paragraph_id": paragraph.norm_paragraph_id,
        "designation": document.designation,
        "title": document.title,
        "ordinal": paragraph.ordinal,
        "clause_number": paragraph.clause_number,
        "page_label": str(paragraph.page_label),
        "text": paragraph.text,
        "reliable": paragraph.reliable,
    }


def collect_rows(
    source: ParagraphSource, spans: Sequence[Span], snapshot_id: str,
) -> list[dict[str, Any]]:
    """The paragraph rows of all spans, once each, ordered by document and ordinal."""
    loaded = _load(source, spans, snapshot_id)
    selected: dict[tuple[str, int], dict[str, Any]] = {}
    for span in spans:
        entry = loaded[span.norm_document_id]
        where = f"{span.norm_document_id}:"
        for ordinal in (span.ordinal_first, span.ordinal_last):
            if ordinal not in entry.by_ordinal:
                _refuse(f"ordinal_missing:{where}{ordinal}")
        for ordinal in range(span.ordinal_first, span.ordinal_last + 1):
            if ordinal not in entry.by_ordinal:
                _refuse(f"range_gap:{where}{ordinal}")
        for ordinal in range(span.ordinal_first, span.ordinal_last + 1):
            paragraph = entry.by_ordinal[ordinal]
            if not paragraph.reliable:
                _refuse(f"paragraph_unreliable:{where}{ordinal}")
            selected[(span.norm_document_id, ordinal)] = _row(entry.document, paragraph)
    return [selected[key] for key in sorted(selected)]


def render_rows(rows: Sequence[dict[str, Any]], snapshot_id: str) -> bytes:
    """The ``paragraphs`` input of ``map_pack`` for a real (non-synthetic) snapshot."""
    payload = {
        "paragraphs_version": PARAGRAPHS_VERSION,
        "synthetic": False,
        "norms_snapshot_id": snapshot_id,
        "paragraphs": list(rows),
    }
    try:
        data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
                + "\n").encode("utf-8")
    except UnicodeEncodeError:
        _refuse("paragraph_text_not_encodable")
    # The consumer's own strict parser has the last word: what it would refuse is not exported.
    try:
        parse_paragraphs(data)
    except MapPackRefused as exc:
        _refuse(f"rows_not_accepted_by_map_pack:{exc}")
    return data


def measure_spans(
    source: ParagraphSource, spans: Sequence[Span], snapshot_id: str,
) -> dict[str, Any]:
    """Numbers per span; unlike the export it reports a missing or unreliable paragraph."""
    loaded = _load(source, spans, snapshot_id)
    measured: list[dict[str, Any]] = []
    for span in spans:
        entry = loaded[span.norm_document_id]
        ordinals = range(span.ordinal_first, span.ordinal_last + 1)
        present = [entry.by_ordinal[o] for o in ordinals if o in entry.by_ordinal]
        missing = [o for o in ordinals if o not in entry.by_ordinal]
        unreliable = [p.ordinal for p in present if not p.reliable]
        first = entry.by_ordinal.get(span.ordinal_first)
        last = entry.by_ordinal.get(span.ordinal_last)
        texts = [p.text for p in present]
        measured.append({
            "norm_document_id": span.norm_document_id,
            "ordinal_first": span.ordinal_first,
            "ordinal_last": span.ordinal_last,
            "expected_paragraphs": len(ordinals),
            "present_paragraphs": len(present),
            "missing_count": len(missing),
            "missing_ordinals": missing[:MAX_LISTED_ORDINALS],
            "unreliable_count": len(unreliable),
            "unreliable_ordinals": unreliable[:MAX_LISTED_ORDINALS],
            "paragraph_id_first": None if first is None else first.norm_paragraph_id,
            "paragraph_id_last": None if last is None else last.norm_paragraph_id,
            "clause_number_first": None if first is None else first.clause_number,
            "clause_number_last": None if last is None else last.clause_number,
            "text_characters": sum(len(t) for t in texts),
            "longest_paragraph_characters": max((len(t) for t in texts), default=0),
            "text_sha256": hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest(),
        })
    return {
        "measure_version": MEASURE_VERSION,
        "norms_snapshot_id": snapshot_id,
        "documents": [
            {
                "norm_document_id": document_id,
                "designation": loaded[document_id].document.designation,
                "designation_characters": len(loaded[document_id].document.designation),
                "title_characters": len(loaded[document_id].document.title),
            }
            for document_id in sorted(loaded)
        ],
        "spans": measured,
    }


# ---------------------------------------------------------------- database

class DatabaseSource:
    """The corpus through the public ``norms`` reads, in the caller's read-only session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def document(self, norm_document_id: str) -> DocumentFacts | None:
        try:
            view = get_norm_document(self._session, norm_document_id)
        except DomainError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            _refuse(f"database_refused:{exc.code.value}")
        return DocumentFacts(
            norm_document_id=str(view.norm_document_id),
            norms_snapshot_id=str(view.norms_snapshot_id),
            designation=str(view.designation),
            title=str(view.title),
        )

    def paragraphs(
        self, norm_document_id: str, *, through_ordinal: int,
    ) -> Sequence[ParagraphFacts]:
        rows: list[ParagraphFacts] = []
        cursor: str | None = None
        previous = -1
        while True:
            try:
                _, page = list_norm_paragraphs(
                    self._session, norm_document_id, cursor=cursor, limit=PAGE_SIZE)
            except DomainError as exc:
                _refuse(f"database_refused:{exc.code.value}")
            for item in page.items:
                if item.ordinal <= previous:
                    _refuse(f"paragraph_order_invalid:{norm_document_id}")
                previous = item.ordinal
                if item.ordinal > through_ordinal:
                    return rows
                rows.append(ParagraphFacts(
                    norm_paragraph_id=str(item.norm_paragraph_id),
                    ordinal=int(item.ordinal),
                    page_label=int(item.page_label),
                    clause_number=None if item.clause_number is None
                    else str(item.clause_number),
                    text=str(item.text),
                    reliable=_reliable(item.text_reliability),
                ))
            if page.next_cursor is None:
                return rows
            cursor = page.next_cursor


def _reliable(value: object) -> bool:
    if value == "reliable":
        return True
    if value == "unreliable":
        return False
    _refuse("text_reliability_unknown")


def require_read_only(session: Session) -> None:
    """Prove the transaction is read-only before any corpus query runs."""
    if session.execute(text("SHOW transaction_read_only")).scalar() != "on":
        _refuse("database_not_read_only")


@contextlib.contextmanager
def open_database_source(database_url: str) -> Iterator[ParagraphSource]:
    """One ``REPEATABLE READ READ ONLY`` transaction over the real database."""
    try:
        settings = DatabaseSettings(url=parse_database_url(database_url))
    except DatabaseConfigurationError:
        _refuse("database_url_invalid")  # the message of the parser could echo the value
    engine = create_database_engine(settings)
    try:
        with Session(engine) as session:
            try:
                session.connection(execution_options={
                    "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
                })
                require_read_only(session)
                yield DatabaseSource(session)
            finally:
                session.rollback()
    except SQLAlchemyError as exc:
        raise ExportRefused(f"database_unavailable:{type(exc).__name__}") from None
    finally:
        engine.dispose()


# ---------------------------------------------------------------- files and CLI

def require_untracked_location(path: Path) -> None:
    """Corpus text may only be written outside the repository tree or under its ignored ``.local/``."""
    target = Path(os.path.realpath(path.parent)) / path.name
    try:
        relative = target.relative_to(_ROOT)
    except ValueError:
        return
    if relative.parts[:1] != (".local",):
        _refuse("output_inside_repository_tree")


def _read_spans(path: Path) -> bytes:
    try:
        with path.open("rb") as handle:
            return handle.read(MAX_SPANS_BYTES + 1)
    except OSError:
        _refuse("spans_file_unreadable")


def write_new_file(path: Path, data: bytes) -> None:
    """Create ``path`` exclusively with mode 0600; never overwrite, never leave half a file."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        _refuse("output_exists")
    except OSError:
        _refuse("output_unwritable")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
    except BaseException as exc:
        with contextlib.suppress(OSError):
            path.unlink()
        if isinstance(exc, OSError):
            raise ExportRefused("output_unwritable") from exc
        raise


def run(
    args: argparse.Namespace,
    opener: Callable[[], contextlib.AbstractContextManager[ParagraphSource]],
) -> str | None:
    """Do the work; return the text to print, or ``None`` after writing the output file."""
    snapshot_id = parse_snapshot_id(args.snapshot)
    spans = parse_spans(_read_spans(args.spans))
    if args.out is not None:
        require_untracked_location(args.out)
        if os.path.lexists(args.out):
            _refuse("output_exists")
    with opener() as source:
        if args.measure:
            return json.dumps(measure_spans(source, spans, snapshot_id),
                              ensure_ascii=False, sort_keys=True, indent=2)
        data = render_rows(collect_rows(source, spans, snapshot_id), snapshot_id)
    write_new_file(args.out, data)
    return None


def _database_opener() -> contextlib.AbstractContextManager[ParagraphSource]:
    url = os.environ.get(DATABASE_URL_VAR, "")
    if not url.strip():
        _refuse("database_url_missing")
    return open_database_source(url)


def main(
    argv: Sequence[str] | None = None,
    *,
    opener: Callable[[], contextlib.AbstractContextManager[ParagraphSource]] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="export_paragraph_rows",
        description="Export paragraph rows (or measure spans) from the norms database, read-only.")
    parser.add_argument("--spans", type=Path, required=True)
    parser.add_argument("--snapshot", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--out", type=Path)
    mode.add_argument("--measure", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = run(args, opener or _database_opener)
    except ExportRefused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    if report is not None:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
