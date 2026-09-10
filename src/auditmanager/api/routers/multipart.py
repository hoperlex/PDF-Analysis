"""A strict ``multipart/form-data`` reader for the one upload the surface declares.

``uploadDocument`` is the only multipart operation in the frozen document, and its
schema declares exactly two parts: a required binary ``file`` and an optional
``display_title``. This reader accepts that and refuses everything else.

It is written on the standard library's ``email`` parser rather than on a form-parsing
dependency, because ``docs/program/P02_LOCK.json`` pins no such dependency and a Gate B
session may not add one.

Deliberately strict, because a lenient multipart reader is a security surface: a missing
boundary, a part with no name, a repeated part and an unknown part are each a refusal
rather than a best guess.
"""

from __future__ import annotations

import email.parser
import email.policy
from dataclasses import dataclass
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["MultipartUpload", "parse_multipart_upload"]

#: The upload envelope refuses anything larger long before this, but a reader that will
#: happily materialise an unbounded body is a denial-of-service surface of its own.
#: 25 MiB is the declared maximum; the slack covers part headers and the boundary.
MAX_BODY: Final[int] = 26 * 1024 * 1024

_FILE_PART: Final[str] = "file"
_TITLE_PART: Final[str] = "display_title"


@dataclass(frozen=True, slots=True)
class MultipartUpload:
    """The two declared parts of ``UploadDocumentRequest``."""

    content: bytes
    filename: str
    display_title: str | None


def _refuse(message: str, *, field: str, constraint: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message=message, field=field, constraint=constraint
    )


def parse_multipart_upload(body: bytes, content_type: str | None) -> MultipartUpload:
    """Read the ``file`` and optional ``display_title`` parts, or refuse.

    The returned ``filename`` is the client's own and is passed to the ingest command,
    which records it. It is **never** rendered into a response: see the note in
    :mod:`auditmanager.api.schemas.documents`.
    """
    if not content_type or "multipart/form-data" not in content_type.lower():
        raise _refuse(
            "This operation expects a multipart/form-data body.",
            field="Content-Type",
            constraint="media_type",
        )
    if len(body) > MAX_BODY:
        raise _refuse(
            "The upload exceeds the maximum accepted size.",
            field="file",
            constraint="max_bytes",
        )

    # `email` wants the content-type header alongside the body to find the boundary.
    raw = b"Content-Type: " + content_type.encode("latin-1", "replace") + b"\r\n\r\n" + body
    parsed = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(raw)
    if not parsed.is_multipart():
        raise _refuse(
            "The multipart body could not be read; the boundary may be missing.",
            field="Content-Type",
            constraint="boundary",
        )

    content: bytes | None = None
    filename: str | None = None
    display_title: str | None = None
    seen: set[str] = set()

    for part in parsed.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not isinstance(name, str) or not name:
            raise _refuse(
                "A multipart part carries no name.",
                field="file",
                constraint="part_name",
            )
        if name in seen:
            raise _refuse(
                "A multipart part is repeated.", field=name, constraint="unique_part"
            )
        seen.add(name)

        if name == _FILE_PART:
            payload = part.get_payload(decode=True)
            if not isinstance(payload, bytes):
                raise _refuse(
                    "The file part could not be decoded.",
                    field="file",
                    constraint="encoding",
                )
            content = payload
            candidate = part.get_filename()
            filename = candidate if isinstance(candidate, str) and candidate else None
        elif name == _TITLE_PART:
            payload = part.get_payload(decode=True)
            if not isinstance(payload, bytes):
                raise _refuse(
                    "The display_title part could not be decoded.",
                    field="display_title",
                    constraint="encoding",
                )
            try:
                display_title = payload.decode("utf-8")
            except UnicodeDecodeError:
                raise _refuse(
                    "The display_title part is not valid UTF-8.",
                    field="display_title",
                    constraint="encoding",
                ) from None
        else:
            # `UploadDocumentRequest` is closed. An unknown part is refused rather than
            # ignored, for the same reason an unknown JSON property is.
            raise _refuse(
                "The upload carries a part the schema does not declare.",
                field=name,
                constraint="additionalProperties",
            )

    if content is None:
        raise _refuse("The upload requires a file part.", field="file", constraint="required")
    if filename is None:
        raise _refuse(
            "The file part requires a filename.", field="file", constraint="filename"
        )
    return MultipartUpload(content=content, filename=filename, display_title=display_title)
