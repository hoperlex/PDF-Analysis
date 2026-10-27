"""The reader of a ZIP set: every PDF of an archive, as temporary files, judged.

`CMP-INGEST-ZIP-01` (ADR-0025 decision 12). The archive rules are the portal reader's
(:func:`auditmanager.ingest.bundle_archive.extract_bundle`) under the set policy
(:mod:`~auditmanager.ingest.comparison_zip.policy`); this module composes them:

1. the archive is read once with the first-level judge, which accepts PDFs and ZIPs;
2. each ZIP inside it is read with the second-level judge, which accepts PDFs only, in the
   budget (entries, bytes) the first level left, and its file is then removed -- it was a
   container, not a deliverable;
3. the PDFs of every level are numbered in the order the archives list them, and each is
   handed to the PDF envelope, in that order, in a child process of its own
   (:func:`~auditmanager.ingest.envelope.inspect_pdf`).

Nothing that an archive says reaches a path: a member is a file named ``<kind>_<index>`` in a
private temporary directory of the reader (``auditmanager-bundle-*``, which
``jobs.temporaries`` sweeps when stale). **A member's identity is its ordinal in the set, its
SHA-256 and its size; its name is a display hint** (:attr:`SetMember.display_name`), scrubbed
of control and format characters and cut to :data:`MAX_HINT` characters, and it names nothing.

Any refusal -- of the archive or of a member's PDF -- refuses the whole set, as the original's
upload refused a whole candidate, and leaves no temporary directory. A PDF that fails the
envelope raises :class:`SetMemberRefused`, which keeps the envelope's own ``field`` and
``constraint`` and adds the member's ordinal; the archive's refusals say nothing about which
member they met, because the archive is what is wrong.

The PDF check is a parameter (``envelope``). It defaults to the existing envelope
(:func:`inspect_pdf_member`: 250 MiB, one to five hundred pages, unencrypted, readable by
PDFium and by the stages' readers, and the portal bundle's drawing-element ceilings).
``CMP-INGEST-01`` owns the comparison envelope with its own element limit (ADR-0025 addendum
item 3) and passes it here. ``None`` runs no check, for a caller that runs it later, one member
at a time, as separate work: each check costs two child processes, and a set of a thousand
PDFs is not one unit of work. Such a member has ``facts = None`` and **must not be stored
before the check has run**.
"""

from __future__ import annotations

import contextlib
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Final

from auditmanager.ingest.bundle_archive import (
    ArchivePolicy,
    BundleLimits,
    ExtractedBundle,
    ExtractedMember,
    extract_bundle,
)
from auditmanager.ingest.envelope import PdfFacts, inspect_pdf
from auditmanager.shared.errors import DomainError

from .policy import DEFAULT_SET_POLICY, KEY_ZIP, LevelJudge, SetPolicy
from .refusals import refuse_set, translate

__all__ = [
    "ExtractedSet",
    "MAX_HINT",
    "SetMember",
    "SetMemberRefused",
    "extract_pdf_set",
    "inspect_pdf_member",
]

#: The longest display hint kept, in characters.
MAX_HINT: Final[int] = 1024
_MAX_BASE_NAME: Final[int] = 255

#: What a hint may not carry (the portal's scrub, ``bundle_members``, and the same reasons):
#: controls, format characters (the bidirectional overrides among them), line and paragraph
#: separators, and the Hangul fillers that draw nothing.
_UNSHOWABLE: Final[frozenset[str]] = frozenset({"Cc", "Cf", "Zl", "Zp"})
_INVISIBLE_LETTERS: Final[frozenset[str]] = frozenset({"ᅟ", "ᅠ", "ㅤ", "ﾠ"})


def inspect_pdf_member(handle: BinaryIO) -> PdfFacts:
    """The existing PDF envelope for one member: the default ``envelope`` of the reader.

    Every page is read and counted; whether a page carries text is left to the caller
    (``require_text=False``), as for the PDF member of a portal bundle: a comparison reads
    drawings as well as text.
    """
    return inspect_pdf(handle, require_text=False)


class SetMemberRefused(DomainError):
    """A member's PDF failed the envelope: its refusal, and which member it was.

    It *is* the envelope's ``DomainError`` (the same code, ``field``, ``constraint`` and
    message) so any handler of that refusal handles this one. ``member_ordinal`` is the
    member's :attr:`SetMember.ordinal`; no name is carried.
    """

    def __init__(self, refused: DomainError, member_ordinal: int) -> None:
        super().__init__(
            refused.code, message=refused.custom_message, **dict(refused.detail_fields)
        )
        self.member_ordinal = member_ordinal


@dataclass(frozen=True, slots=True)
class SetMember:
    """One PDF of a set, as counted while it was unpacked.

    ``ordinal`` is its place among the set's PDFs (the archives' listing order, a nested
    archive's PDFs at the archive's place) and is the only handle a caller needs; ``sha256`` and
    ``size`` are its content. ``display_name`` is a hint for display and for proposals the user
    confirms (:attr:`folder`, :attr:`base_name`): it is never compared, never a key and never a
    path. ``level`` is ``0`` for a PDF of the archive itself and ``1`` for one of an archive
    inside it. ``path`` is the temporary file; ``facts`` is what the envelope read, or ``None``
    when no envelope was run.
    """

    ordinal: int
    level: int
    display_name: str
    size: int
    sha256: str
    path: Path
    facts: PdfFacts | None

    @property
    def base_name(self) -> str:
        """The last component of the hint: a plain base name, never blank."""
        return self.display_name.rsplit("/", 1)[-1][:_MAX_BASE_NAME] or "document.pdf"

    @property
    def folder(self) -> str:
        """The folders of the hint (a nested archive counts as one), ``""`` at the root."""
        head, separator, _tail = self.display_name.rpartition("/")
        return head if separator else ""


class ExtractedSet:
    """The PDFs of one accepted ZIP set, as files in private temporary directories.

    Close it (or use it as a context manager) to remove the directories. It is created by
    :func:`extract_pdf_set`, which removes them itself when the set is refused.
    """

    __slots__ = ("members", "entries_seen", "bytes_seen", "_stack")

    def __init__(
        self,
        members: tuple[SetMember, ...],
        entries_seen: int,
        bytes_seen: int,
        stack: contextlib.ExitStack,
    ) -> None:
        self.members = members
        #: The entries of every archive of the set, directory entries included.
        self.entries_seen = entries_seen
        #: The uncompressed bytes of every member of every level, archives included.
        self.bytes_seen = bytes_seen
        self._stack = stack

    def open(self, member: SetMember) -> BinaryIO:
        return member.path.open("rb")

    def close(self) -> None:
        self._stack.close()

    def __enter__(self) -> ExtractedSet:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _hint(shown: str) -> str:
    """A name as a display hint: the unshowable code points replaced by ``_``, then cut."""
    cleaned = "".join(
        "_" if unicodedata.category(ch) in _UNSHOWABLE or ch in _INVISIBLE_LETTERS else ch
        for ch in shown
    )
    return cleaned.strip()[:MAX_HINT]


def _extract_level(
    handle: BinaryIO,
    policy: SetPolicy,
    judge: LevelJudge,
    *,
    entries: int,
    total_bytes: int,
    stack: contextlib.ExitStack,
) -> ExtractedBundle:
    """One archive of the set, read under the budget the levels before it left."""
    bundle = extract_bundle(
        handle,
        limits=BundleLimits(
            member_bytes=policy.member_bytes,
            total_bytes=total_bytes,
            ratio=policy.ratio,
            entries=entries,
        ),
        policy=ArchivePolicy(
            judge=judge, translate=translate, max_directory_bytes=policy.directory_bytes
        ),
    )
    stack.callback(bundle.close)
    return bundle


def _path_of(member: ExtractedMember) -> Path:
    """The temporary file of a member that was kept (every member of a set is)."""
    if member.path is None:
        raise RuntimeError("a member of a ZIP set was not kept")
    return member.path


@dataclass(frozen=True, slots=True)
class _Draft:
    member: ExtractedMember
    level: int
    hint: str


def extract_pdf_set(
    handle: BinaryIO,
    *,
    policy: SetPolicy = DEFAULT_SET_POLICY,
    envelope: Callable[[BinaryIO], PdfFacts] | None = inspect_pdf_member,
) -> ExtractedSet:
    """Apply the set policy to an upload and take its PDFs out as temporary files.

    ``handle`` is a seekable binary handle on the whole ZIP; it is left where the reader left
    it. Raises ``validation_failed`` (``field: "file"``, one of
    :data:`~auditmanager.ingest.comparison_zip.refusals.CONSTRAINTS`) for an archive that is not
    a ZIP set, and :class:`SetMemberRefused` for a PDF that fails ``envelope``; in either case
    every temporary directory is removed before the refusal leaves. On success the caller owns
    the returned set and must close it.
    """
    with contextlib.ExitStack() as stack:
        first = LevelJudge(archives_allowed=policy.nesting_levels >= 1, files_required=True)
        outer = _extract_level(
            handle, policy, first, entries=policy.entries, total_bytes=policy.total_bytes,
            stack=stack,
        )
        entries_seen = first.entries_seen
        bytes_seen = sum(member.size for member in outer.members.values())

        drafts: list[_Draft] = []
        for key, member in outer.members.items():
            shown = _hint(member.display_name)
            if not key.startswith(KEY_ZIP):
                drafts.append(_Draft(member, 0, shown))
                continue
            second = LevelJudge(archives_allowed=False, files_required=False)
            container = _path_of(member)
            with container.open("rb") as inner_handle:
                inner = _extract_level(
                    inner_handle, policy, second,
                    entries=policy.entries - entries_seen,
                    total_bytes=policy.total_bytes - bytes_seen,
                    stack=stack,
                )
            # The container is not a deliverable: its bytes are counted, then its file goes.
            container.unlink()
            entries_seen += second.entries_seen
            bytes_seen += sum(inner_member.size for inner_member in inner.members.values())
            folder = shown[: -len(".zip")] if shown.lower().endswith(".zip") else shown
            for inner_member in inner.members.values():
                drafts.append(
                    _Draft(inner_member, 1, _hint(f"{folder}/{inner_member.display_name}"))
                )

        if not drafts:
            raise refuse_set("comparison_zip_empty")

        members: list[SetMember] = []
        for ordinal, draft in enumerate(drafts):
            path = _path_of(draft.member)
            facts: PdfFacts | None = None
            if envelope is not None:
                try:
                    with path.open("rb") as pdf:
                        facts = envelope(pdf)
                except DomainError as refused:
                    raise SetMemberRefused(refused, ordinal) from None
            members.append(
                SetMember(
                    ordinal=ordinal,
                    level=draft.level,
                    display_name=draft.hint,
                    size=draft.member.size,
                    sha256=draft.member.sha256,
                    path=path,
                    facts=facts,
                )
            )
        return ExtractedSet(tuple(members), entries_seen, bytes_seen, stack.pop_all())
