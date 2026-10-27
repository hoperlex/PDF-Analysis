"""What a file *name* hints at, for the grouping proposal. A hint, never an identity.

ADR-0025 decision 10: "file names and folders only feed the proposal that the user confirms". Nothing here
decides anything: it reads the number in a name ("Чертежи (2).pdf"), an «изм N» suffix, the folder of a path
and a base name with those taken off, so that two files of one drawing set group together when their stamps
say nothing. The rules are the original's (`ORIGINAL-VERSION-COMPARISON-INVENTORY.md` section 3.2 item 2:
``_FILE_NUMBER``, ``_IZM_IN_NAME``, ``name_base``), restated here because the original is not a dependency.

A name can come as a path (a browser folder upload sends ``Папка/Файл.pdf``). The folder and the file part are
separated at the **last** separator, either slash; the file name never leaves this module as a path.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Final

__all__ = ["NameHint", "clean_display_name", "group_key", "name_hint", "source_filename_of"]

#: ``(2)`` at the end of the stem: the number a browser or a person appended to a copy.
_FILE_NUMBER: Final[re.Pattern[str]] = re.compile(r"\((\d{1,3})\)\s*$")
#: ``изм 3``, ``Изм.3``, ``_изм_3`` anywhere in the stem.
_IZM_IN_NAME: Final[re.Pattern[str]] = re.compile(r"изм[\s._-]*(\d{1,3})", re.IGNORECASE)
#: What is taken off the end of a stem to get the base: an «изм N», a version marker, a trailing copy number.
_SUFFIX: Final[re.Pattern[str]] = re.compile(
    r"[\s._-]*(?:изм|v|ред)[\s._-]*\d*\s*$|\s*\(\d{1,3}\)\s*$", re.IGNORECASE
)
_PDF_EXTENSION: Final[re.Pattern[str]] = re.compile(r"\.pdf\s*$", re.IGNORECASE)
_CONTROL: Final[re.Pattern[str]] = re.compile(r"[\x00-\x1f\x7f]")
_SEPARATORS: Final[tuple[str, str]] = ("/", "\\")


@dataclass(frozen=True, slots=True)
class NameHint:
    """The hints one display name gives. Every member is optional and none is a fact about the file."""

    #: The folder part, folded for comparison (``None`` for a bare name).
    folder: str | None
    #: The number in ``(N)`` at the end of the stem.
    file_number: int | None
    #: The number after «изм» in the stem.
    izm_in_name: int | None
    #: The stem without its extension, copy number and «изм N» suffix, folded for comparison.
    name_base: str
    #: The file part as sent (extension kept), cleaned of control characters; what a person reads.
    file_name: str


def clean_display_name(display_name: str) -> str:
    """The display name as it is stored: no control character (a NUL cannot be stored, and none is a name's), the
    ends trimmed. Empty when nothing is left -- the caller refuses that, it is not named ``file.pdf``."""
    return _CONTROL.sub("", display_name).strip()


def _fold(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().replace("_", " ").split())


def _split(display_name: str) -> tuple[str | None, str]:
    cleaned = _CONTROL.sub("", display_name).strip()
    cut = max(cleaned.rfind(separator) for separator in _SEPARATORS)
    if cut < 0:
        return None, cleaned
    folder = cleaned[:cut].strip("/\\ ").replace("\\", "/")
    return (folder or None), cleaned[cut + 1 :].strip()


def name_hint(display_name: str) -> NameHint:
    """The hints of one display name, a path or a bare name."""
    folder, file_name = _split(display_name)
    stem = _PDF_EXTENSION.sub("", file_name)
    number = _FILE_NUMBER.search(stem)
    izm = _IZM_IN_NAME.search(stem)
    base = stem
    while True:  # a copy number and an «изм N» can both end a stem, in either order
        stripped = _SUFFIX.sub("", base)
        if stripped == base:
            break
        base = stripped
    return NameHint(
        folder=None if folder is None else _fold(folder),
        file_number=None if number is None else int(number.group(1)),
        izm_in_name=None if izm is None else int(izm.group(1)),
        name_base=_fold(base) or _fold(stem) or _fold(file_name),
        file_name=file_name,
    )


def group_key(hint: NameHint) -> str:
    """The key two files share when nothing else groups them: their folder, else their base name.

    A folder is one drawing set in the original's batch (each folder is a project), so it wins over the base
    name; a bare name groups by its base. Two keys never collide across the two kinds (the prefix says which).
    """
    return f"folder:{hint.folder}" if hint.folder else f"name:{hint.name_base}"


def source_filename_of(display_name: str, *, fallback: str = "document.pdf") -> str:
    """A plain base name for ``document_version.source_filename``: the file part, at most 255 characters.

    The stored name is display evidence, never an identity (foundation invariant 3); the portal path
    validates it as a plain base name, so a path from a folder upload keeps its file part only.
    """
    _folder, file_name = _split(display_name)
    file_name = file_name[:255].strip()
    return file_name if file_name and file_name not in (".", "..") else fallback
