"""The portal's recognised text (`W55B-RECOGNISED-01`, plan section B3.6).

``source_preparation`` reads a portal bundle's stored ``_results.md`` and ``_blocks.json``
through this package and publishes ``prepared.recognised_text`` (``P02_SEAMS`` section 4.8):
per block, the portal's OCR text marked ``quote_source: recognised`` with quality flags, and
the portal's descriptions of its IMAGE blocks. **Nothing here reaches analysis** (``R-117``):
the text is never merged into ``prepared.text_layer``, carries no offsets, and no module of
``auditmanager.analysis.text`` imports this package (a test holds that).

* :mod:`.markdown` -- the markdown, one body per block header;
* :mod:`.portal` -- the block list, and the two members held equal both ways;
* :mod:`.flags` -- the quality flags, pure functions;
* :mod:`.artifact` -- the artifact document.
"""

from __future__ import annotations

from auditmanager.analysis.recognised.artifact import (
    KIND_PORTAL_DESCRIPTION,
    KIND_RECOGNISED_TEXT,
    QUOTE_SOURCE_RECOGNISED,
    build_recognised_text,
    recognised_entries,
)
from auditmanager.analysis.recognised.flags import (
    DESIGNATION,
    FLAG_ORDER,
    FlagReport,
    flags_for,
    inspect_recognised,
)
from auditmanager.analysis.recognised.markdown import MarkdownBlock, read_blocks
from auditmanager.analysis.recognised.portal import (
    PortalBlock,
    PortalRecognition,
    read_block_list,
    read_portal,
)

__all__ = [
    "DESIGNATION",
    "FLAG_ORDER",
    "KIND_PORTAL_DESCRIPTION",
    "KIND_RECOGNISED_TEXT",
    "QUOTE_SOURCE_RECOGNISED",
    "FlagReport",
    "MarkdownBlock",
    "PortalBlock",
    "PortalRecognition",
    "build_recognised_text",
    "flags_for",
    "inspect_recognised",
    "read_block_list",
    "read_blocks",
    "read_portal",
    "recognised_entries",
]
