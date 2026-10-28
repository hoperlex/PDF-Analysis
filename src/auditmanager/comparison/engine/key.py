"""The content key of a result (ADR-0025 decision 15, plan R3-09).

`CMP-ENGINE-01`. A sheet-pair result is keyed by: the content Merkle of page A (its content stream and every resource,
XObjects and images included; computed by the page profile), the same for page B, the annotation hashes of both, the
sorted link reasons, the split part, the parameters, ``ALGO_VERSION`` -- and the project, so that a result is reused
within one project only. The key is a SHA-256 over a canonical JSON of those, and it is the ``content_key`` column the
table makes unique together with ``project_uid``.

A page that has no Merkle (it was refused, or ended without a result) is keyed by the content key the page profile gave
it, which holds the version's digest, so that two failed pages of different files never share a result.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from auditmanager.comparison.engine.child.settings import ALGO_VERSION, PARAMS
from auditmanager.comparison.profile.models import PageProfileRow

__all__ = ["content_key", "page_part"]


def page_part(row: PageProfileRow) -> dict[str, Any]:
    summary = row.summary
    merkle = summary.get("content_merkle")
    return {
        "profile_algo": row.algo_version,
        "status": row.status,
        "merkle": merkle,
        "annotations": sorted(str(h) for h in summary.get("annotation_hashes") or ()),
        "profile": None if merkle else row.content_key,
    }


def content_key(
    project_uid: str, a: PageProfileRow, b: PageProfileRow, *, reasons: Iterable[str] = (), part: str | None = None
) -> str:
    document = {
        "algo": ALGO_VERSION,
        "project": project_uid,
        "a": page_part(a),
        "b": page_part(b),
        "reasons": sorted(set(reasons)),
        "part": part,
        "params": PARAMS,
    }
    raw = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()
