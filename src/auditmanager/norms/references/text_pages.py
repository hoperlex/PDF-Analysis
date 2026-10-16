"""Map one validated analysis text layer to W57b PDF reference pages.

The caller supplies the Version identity and its independently known page count.
This pure bridge does not authenticate the artifact, read a PDF or change text.
"""

from __future__ import annotations

from auditmanager.analysis.public import TextLayer
from auditmanager.norms.references.observation_plan import ReferencePage
from auditmanager.norms.references.resolution import ReferenceRefused


def reference_pages_from_text_layer(
    *, text_layer: TextLayer, version_uid: str, page_count: int
) -> tuple[ReferencePage, ...]:
    """Preserve exact page-global Unicode offsets, including empty pages."""
    if not isinstance(text_layer, TextLayer):
        raise ReferenceRefused("reference source is not a validated text layer")
    if not isinstance(version_uid, str) or not version_uid or text_layer.version_uid != version_uid:
        raise ReferenceRefused("reference text layer Version differs from the pinned Version")
    if isinstance(page_count, bool) or not isinstance(page_count, int) or page_count < 1:
        raise ReferenceRefused("reference Version page count is invalid")
    if not isinstance(text_layer.pages, tuple) or len(text_layer.pages) != page_count:
        raise ReferenceRefused("reference text layer page count differs from the pinned Version")
    if not isinstance(text_layer.normalization_id, str) or not text_layer.normalization_id:
        raise ReferenceRefused("reference text layer normalization is undeclared")

    pages: list[ReferencePage] = []
    source_parts: list[str] = []
    expected_start = 0
    for page_number, page in enumerate(text_layer.pages, start=1):
        number = getattr(page, "page_number", None)
        start = getattr(page, "char_start", None)
        end = getattr(page, "char_end", None)
        page_text = getattr(page, "text", None)
        if (
            isinstance(number, bool)
            or not isinstance(number, int)
            or number != page_number
        ):
            raise ReferenceRefused("reference text layer pages are not numbered 1..N")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or start != expected_start
            or isinstance(end, bool)
            or not isinstance(end, int)
            or not isinstance(page_text, str)
            or end != start + len(page_text)
        ):
            raise ReferenceRefused("reference text layer page offsets differ from its text")
        pages.append(
            ReferencePage(
                page_label=str(page_number),
                page_number=page_number,
                char_start=start,
                text=page_text if page_text else None,
            )
        )
        source_parts.append(page_text)
        expected_start = end

    if not isinstance(text_layer.document_text, str) or text_layer.document_text != "".join(source_parts):
        raise ReferenceRefused("reference document text differs from its ordered pages")
    return tuple(pages)


__all__ = ["reference_pages_from_text_layer"]
