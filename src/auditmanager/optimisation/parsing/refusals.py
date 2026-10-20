"""Why a whole file is refused, as ``validation_failed`` with ``field: content``.

A refused file creates nothing: no Blob, no command record, no revision. Each refusal names
one ``constraint`` (the catalog's safe detail) and an English message that never echoes the
file's own text -- header and cell values are user data and stay out of the envelope.
"""

from __future__ import annotations

from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

from .limits import MAX_BYTES, MAX_DATA_ROWS, MAX_XLSX_PART_BYTES

__all__ = [
    "CONSTRAINT_EMPTY",
    "CONSTRAINT_ENCODING",
    "CONSTRAINT_FORMAT",
    "CONSTRAINT_HEADER",
    "CONSTRAINT_HEADER_AMBIGUOUS",
    "CONSTRAINT_NO_POSITIONS",
    "CONSTRAINT_ROWS",
    "CONSTRAINT_SIZE",
    "CONSTRAINT_UNREADABLE",
    "CONSTRAINT_XLSX_PART_SIZE",
    "FILE_CONSTRAINTS",
    "refuse",
]

FIELD: Final[str] = "content"

CONSTRAINT_EMPTY: Final[str] = "non_empty"
CONSTRAINT_SIZE: Final[str] = f"byte_size <= {MAX_BYTES}"
CONSTRAINT_FORMAT: Final[str] = "price_list_format"
CONSTRAINT_UNREADABLE: Final[str] = "price_list_unreadable"
CONSTRAINT_ENCODING: Final[str] = "price_list_encoding"
CONSTRAINT_XLSX_PART_SIZE: Final[str] = f"xlsx_part_size <= {MAX_XLSX_PART_BYTES}"
CONSTRAINT_HEADER: Final[str] = "price_list_header"
CONSTRAINT_HEADER_AMBIGUOUS: Final[str] = "price_list_header_ambiguous"
CONSTRAINT_ROWS: Final[str] = f"data_rows <= {MAX_DATA_ROWS}"
CONSTRAINT_NO_POSITIONS: Final[str] = "price_list_no_positions"

#: Every constraint a refused file can carry, for the UI's copy table and the tests.
FILE_CONSTRAINTS: Final[tuple[str, ...]] = (
    CONSTRAINT_EMPTY,
    CONSTRAINT_SIZE,
    CONSTRAINT_FORMAT,
    CONSTRAINT_UNREADABLE,
    CONSTRAINT_ENCODING,
    CONSTRAINT_XLSX_PART_SIZE,
    CONSTRAINT_HEADER,
    CONSTRAINT_HEADER_AMBIGUOUS,
    CONSTRAINT_ROWS,
    CONSTRAINT_NO_POSITIONS,
)


def refuse(constraint: str, message: str) -> DomainError:
    """The one refusal shape for a file that cannot become a price list."""
    assert constraint in FILE_CONSTRAINTS, constraint
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=message,
        field=FIELD,
        constraint=constraint,
        aggregate_type="PriceList",
    )
