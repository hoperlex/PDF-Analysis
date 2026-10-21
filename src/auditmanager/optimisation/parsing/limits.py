"""The bounds of a price-list upload and of every parsed value, in one place.

Migration ``0026_price_lists`` restates the column bounds (``MAX_*_LENGTH``, ``MAX_DATA_ROWS``)
as CHECK constraints; ``tests/unit/optimisation`` holds the two spellings equal.
"""

from __future__ import annotations

from typing import Final

#: The largest accepted file, in bytes (10 MiB). Larger is refused before anything is parsed.
MAX_BYTES: Final[int] = 10 * 1024 * 1024
#: The most data rows (non-blank rows after the header) one price list may carry.
MAX_DATA_ROWS: Final[int] = 20_000
#: The header is looked for among this many first non-blank rows.
HEADER_SCAN_ROWS: Final[int] = 20
#: Cells beyond this column are not read (a header further right is not looked for).
MAX_COLUMNS: Final[int] = 200
#: The largest decompressed size of one XLSX part (the sheet, the shared strings).
MAX_XLSX_PART_BYTES: Final[int] = 64 * 1024 * 1024
#: The largest decompressed size of a small XLSX part (relationships, the workbook).
MAX_XLSX_SMALL_PART_BYTES: Final[int] = 4 * 1024 * 1024
#: The most members an XLSX archive may have.
MAX_XLSX_MEMBERS: Final[int] = 10_000
#: How many skipped rows and warnings the parse report lists one by one; the counts by
#: reason are always complete.
MAX_LISTED_ROWS: Final[int] = 1000
#: How many characters of a header cell the report keeps.
MAX_HEADER_TEXT: Final[int] = 200

MAX_NAME_LENGTH: Final[int] = 2000
MAX_CODE_LENGTH: Final[int] = 200
MAX_MARK_LENGTH: Final[int] = 500
MAX_UNIT_LENGTH: Final[int] = 50
MAX_VENDOR_LENGTH: Final[int] = 500

#: A unit price is below 10^14 and has at most six decimals; nothing is rounded to fit.
MAX_PRICE_EXCLUSIVE: Final[int] = 10**14
MAX_PRICE_DECIMALS: Final[int] = 6
#: XLSX stores numbers as binary doubles written with up to 17 significant digits; they are
#: read back at Excel's own display precision, fifteen significant digits.
XLSX_SIGNIFICANT_DIGITS: Final[int] = 15
