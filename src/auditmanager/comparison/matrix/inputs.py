"""What a build reads, and how that is told from what a later read finds: the digest of the page profiles, the order,
the progress, the stale reasons. Pure functions; no database, no clock.

`CMP-MATRIX-01` (plan section 3.2 ``R3-32``: staleness compares stored input digests, never timestamps).
``profile_signature`` -- stored on the build -- is the digest of the page profiles the build read, one entry for each
page: version, page number, the profile's content key and its status. It does not depend on the order of the
versions (the order is stored beside it as the revision ``order_id`` and the list of versions) and it does not depend
on identities that a profile gets when it is written (the content key is a function of the page's content), so two
builds over the same pages agree.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Final

from auditmanager.comparison.matrix import settings
from auditmanager.comparison.matrix.model import BuildRecord
from auditmanager.comparison.matrix.repository import ProfileFact

__all__ = [
    "STALE_ORDER_CHANGED",
    "STALE_PROFILES_CHANGED",
    "profile_digest",
    "profile_progress",
    "profiles_complete",
    "resolve_order",
    "stale_reasons",
    "versions_missing_profiles",
]

STALE_ORDER_CHANGED: Final[str] = "order_changed"
STALE_PROFILES_CHANGED: Final[str] = "profiles_changed"
_STATUS_READY: Final[str] = "ready"


def profile_digest(facts: Iterable[ProfileFact]) -> str:
    """The digest of the profiles read: sorted, so the order of the rows is not part of it."""
    entries = sorted([f.version_uid, f.page_number, f.content_key, f.status] for f in facts)
    body = json.dumps(entries, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def resolve_order(order_revision: Sequence[str] | None, own_order: Sequence[str]) -> list[str]:
    """The versions in the order a build walks them.

    The latest revision of ``comparison_version_order`` if the document has one -- followed by any version the
    revision does not list (a version published after it), in the document's own order -- otherwise the document's
    own order (``version_ordinal``, oldest first). A revision lists every version exactly once when it is written,
    so the remainder is empty unless a version was added since; it is never a reason to drop one.
    """
    if not order_revision:
        return list(own_order)
    known = set(own_order)
    listed = [v for v in order_revision if v in known]
    seen = set(listed)
    return listed + [v for v in own_order if v not in seen]


def profiles_complete(facts: Sequence[ProfileFact], page_counts: Mapping[str, int]) -> bool:
    """Every page of every version has a stored profile of the current algorithm (``ready``, ``needs_review`` or
    ``refused``: a page that ended without a result is a stored page, built again on request)."""
    held: dict[str, set[int]] = {}
    for f in facts:
        held.setdefault(f.version_uid, set()).add(f.page_number)
    return all(held.get(version, set()) >= set(range(1, count + 1)) for version, count in page_counts.items())


def versions_missing_profiles(
    facts: Sequence[ProfileFact], order: Sequence[str], page_counts: Mapping[str, int]
) -> tuple[list[str], list[str]]:
    """``(missing, failed)``: versions that lack a profile for some page, and versions that hold a page that ended
    without a result. A version can be in both."""
    held: dict[str, dict[int, str]] = {}
    for f in facts:
        held.setdefault(f.version_uid, {})[f.page_number] = f.status
    missing = [v for v in order if set(held.get(v, {})) < set(range(1, page_counts[v] + 1))]
    failed = [v for v in order if any(s != _STATUS_READY for s in held.get(v, {}).values())]
    return missing, failed


def profile_progress(facts: Sequence[ProfileFact], page_counts: Mapping[str, int]) -> dict[str, int]:
    """``{"total", "ready", "failed"}``: pages of the document set, pages with a ``ready`` profile, and pages whose
    profile ended without a result."""
    total = sum(page_counts.values())
    ready = sum(1 for f in facts if f.status == _STATUS_READY)
    failed = sum(1 for f in facts if f.status != _STATUS_READY)
    return {"total": total, "ready": ready, "failed": failed}


def stale_reasons(
    build: BuildRecord, *, order: Sequence[str], order_id: str | None, digest: str
) -> list[str]:
    """Why a build no longer matches the current inputs (empty: it does). A change of the rules or of the algorithm
    is reported as ``profiles_changed``: the contract has no reason of its own for it."""
    reasons: list[str] = []
    if build.order_id != order_id or build.order != list(order):
        reasons.append(STALE_ORDER_CHANGED)
    if (
        build.profile_signature != digest
        or build.algo_version != settings.ALGO_VERSION
        or build.rules_version != settings.RULES_VERSION
    ):
        reasons.append(STALE_PROFILES_CHANGED)
    return reasons
