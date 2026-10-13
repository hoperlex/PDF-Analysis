"""The portal's stamp audit (`<stem>_stamp_audit.json`), as the owner's bundles carry it.

An audit with no stamps is the common case in the owner's bundles and has the empty
shape: `stamps` empty, empty volume and per-page dictionaries. A bundle with STAMP blocks
gets an entry per stamp with the fields it was read as, and the volume-level values the
stamps agree on. The product stores the file and parses it as JSON; it uses nothing in it.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from . import portal_format as fmt
from .blocklist import Block


def _empty_page(index: int) -> dict[str, object]:
    return {"page_index": index, "fields": {}, "origins": {}, "conflicts": {}, "excluded": []}


def build(stem: str, page_count: int, stamps: Sequence[Block]) -> bytes:
    volume: dict[str, object] = {"fields": {}, "origins": {}, "conflicts": {}, "excluded": []}
    pages = [_empty_page(i) for i in range(page_count)]
    entries: list[dict[str, object]] = []
    for block in stamps:
        fields = dict(block.fields)
        entries.append({"page_index": block.page_index, "block_id": block.block_id,
                        "fields": fields})
        page = pages[block.page_index]
        page["fields"] = fields
        page["origins"] = {name: block.block_id for name in fields}
    if entries:
        # Volume-level values are the ones every stamp agrees on.
        first = dict(stamps[0].fields)
        agreed = {k: v for k, v in first.items()
                  if all(dict(s.fields).get(k) == v for s in stamps)}
        volume["fields"] = agreed
        volume["origins"] = {name: "stamps" for name in agreed}
    document = {
        "schema_version": fmt.SCHEMA_VERSION,
        "document_id": fmt.document_id(stem),
        "document_name": f"{stem}.pdf",
        "generated_at": fmt.STAMP_AUDIT_GENERATED_AT,
        "enabled": True,
        "stamps": entries,
        "volume": volume,
        "pages": pages,
    }
    return json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
