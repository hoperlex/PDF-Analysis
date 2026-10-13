"""``prepared.recognised_text``: the portal's recognised text, marked and kept apart.

`W55B-RECOGNISED-01`, the shape sealed in ``P02_SEAMS`` section 4.8::

    {
      "artifact_role": "prepared.recognised_text",
      "artifact_version": "1.0.0",
      "version_uid": "ver_...",
      "results_sha256": "<SHA-256 of the stored _results.md bytes>",
      "entries": [
        {"portal_block_id": "blk_...", "page_number": 1, "kind": "recognised_text",
         "quote_source": "recognised", "text": "...", "flags": ["mixed_script"]},
        {"portal_block_id": "blk_...", "page_number": 13, "kind": "portal_description",
         "text": "..."}
      ]
    }

* one entry per TEXT or IMAGE block the markdown holds; a STAMP block has none;
* a TEXT body is ``kind: recognised_text`` with ``quote_source: recognised`` and its flags
  (:mod:`.flags`); an IMAGE body is ``kind: portal_description`` with its text only -- no
  ``quote_source``, no ``flags`` -- and is never an input of any analysis stage (``R-117``);
* entries are ordered by page, then by the block's place in the markdown, then by
  ``portal_block_id``;
* ``text`` is the body exactly as :mod:`.markdown` reads it: markdown, kept as text;
* **no entry has an offset**, and nothing here is merged into ``prepared.text_layer``
  (section 4.1).

The document is built by the one :func:`~auditmanager.analysis.ports.artifacts.envelope`
every artifact uses and published by
:func:`~auditmanager.analysis.ports.artifacts.publish_artifact`, whose canonical
serialization makes equal input give equal bytes and so one ``blob_id``.
"""

from __future__ import annotations

import hashlib
from typing import Any, Final

from auditmanager.analysis.ports.artifacts import ROLE_RECOGNISED_TEXT, envelope
from auditmanager.analysis.recognised.flags import flags_for
from auditmanager.analysis.recognised.portal import IMAGE, TEXT, PortalRecognition

KIND_RECOGNISED_TEXT: Final[str] = "recognised_text"
KIND_PORTAL_DESCRIPTION: Final[str] = "portal_description"
#: The marker every recognised entry carries, and the wire's ``PortalRecognisedText``.
QUOTE_SOURCE_RECOGNISED: Final[str] = "recognised"


def recognised_entries(portal: PortalRecognition) -> list[dict[str, Any]]:
    """The entries of the artifact, in their order (module docstring)."""
    ranked: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
    by_id = {block.portal_block_id: block for block in portal.blocks}
    for body in portal.bodies:
        block = by_id[body.portal_block_id]
        if block.block_type == TEXT:
            entry: dict[str, Any] = {
                "portal_block_id": block.portal_block_id,
                "page_number": block.page_number,
                "kind": KIND_RECOGNISED_TEXT,
                "quote_source": QUOTE_SOURCE_RECOGNISED,
                "text": body.body,
                "flags": list(flags_for(body.body)),
            }
        elif block.block_type == IMAGE:
            entry = {
                "portal_block_id": block.portal_block_id,
                "page_number": block.page_number,
                "kind": KIND_PORTAL_DESCRIPTION,
                "text": body.body,
            }
        else:  # pragma: no cover - read_portal admits no header for any other type
            raise AssertionError("the markdown holds a header for a block of another type")
        ranked.append(((block.page_number, body.position, block.portal_block_id), entry))
    ranked.sort(key=lambda pair: pair[0])
    return [entry for _key, entry in ranked]


def build_recognised_text(
    portal: PortalRecognition, *, version_uid: str, markdown: bytes
) -> dict[str, Any]:
    """The ``prepared.recognised_text`` document for one version's stored members."""
    return envelope(
        ROLE_RECOGNISED_TEXT,
        version_uid,
        results_sha256=hashlib.sha256(markdown).hexdigest(),
        entries=recognised_entries(portal),
    )


__all__ = [
    "KIND_PORTAL_DESCRIPTION",
    "KIND_RECOGNISED_TEXT",
    "QUOTE_SOURCE_RECOGNISED",
    "build_recognised_text",
    "recognised_entries",
]
