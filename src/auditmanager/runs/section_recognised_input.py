"""The recognised text of a section run's text-less pages, read from the run's own saved artifact.

`SECTION-CATEGORY-OCR-01` (`R-146aq`, gap report option P8). A portal bundle's pages with almost no
text-layer text (the version's ``textless_pages``) have their text only in ``prepared.recognised_text``,
which ``source_preparation`` published for this run. The section stage never read it. This loader hands the
stage those pages' recognised text, **as context only**: the stage renders it into the user message as a
marked block and resolves every quote against the text layer alone, so nothing found only in recognised text
can confirm a finding (``analysis.text.recognised_input``).

What it does, and what it refuses to do silently:

* a version with no bundle (``textless_pages is None``) or with no text-less page has nothing to send: ``()``;
* otherwise it reads the run's ``prepared.recognised_text`` reference with the artifact reader that checks
  role, version and bytes, and selects through the one selector the product has
  (:func:`~auditmanager.analysis.public.select_recognised_context`: TEXT entries on the stored text-less
  pages only; portal IMAGE descriptions and recognised text on pages that have text are never input, ``R-117``);
* text-less pages with no recognised artifact, or an artifact that disagrees with the version, are an
  inconsistent input and fail the stage explicitly (``analysis_input_invalid``,
  ``recognised_input_invalid``); an empty context is never substituted for a missing one;
* the blocks of one page are merged in artifact order, their quality flags merged in the canonical order, and
  a page whose recognised text is blank is left out (there is nothing to send, and it is not an error).

Nothing here reads the database or writes anything.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from auditmanager.analysis.public import (
    ROLE_RECOGNISED_TEXT,
    ArtifactRef,
    RecognisedContextError,
    RecognisedPage,
    read_artifact,
    select_recognised_context,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore, parse_blob_id

_STAGE = "text_analysis"
_REASON = "recognised_input_invalid"


def _refuse(message: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID, message=message, stage_id=_STAGE, reason=_REASON
    )


def load_section_recognised_pages(
    *,
    blob_store: BlobStore,
    refs: Mapping[str, ArtifactRef],
    version_uid: str,
    textless_pages: tuple[int, ...] | None,
) -> tuple[RecognisedPage, ...]:
    """The recognised pages a section call carries as context, or a refusal. ``()`` when there are none."""
    if not textless_pages:
        # No bundle, or a bundle with no text-less page: nothing to send. (An artifact on a version
        # that has no text-less page is not read, and nothing in it can reach a prompt.)
        return ()
    ref = refs.get(ROLE_RECOGNISED_TEXT)
    document: dict[str, Any] | None = None
    if ref is not None:
        document, _ = read_artifact(
            blob_store, parse_blob_id(ref.blob_id), expected_role=ROLE_RECOGNISED_TEXT
        )
    try:
        context = select_recognised_context(
            document, version_uid=version_uid, textless_pages=textless_pages
        )
    except RecognisedContextError as exc:
        raise _refuse(
            f"the saved recognised text does not fit the version's text-less pages ({exc})"
        ) from exc

    merged: dict[int, tuple[list[str], list[str]]] = {}
    for item in context:
        texts, flags = merged.setdefault(item.page_number, ([], []))
        texts.append(item.text)
        flags.extend([flag for flag in item.flags if flag not in flags])
    pages: list[RecognisedPage] = []
    for page_number in sorted(merged):
        texts, flags = merged[page_number]
        body = "\n".join(text for text in texts if text.strip())
        if body.strip():
            pages.append(RecognisedPage(page_number=page_number, text=body, flags=tuple(flags)))
    return tuple(pages)


__all__ = ["load_section_recognised_pages"]
