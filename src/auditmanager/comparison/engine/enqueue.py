"""Put the comparison of one pair on the queue (`CMP-ENGINE-01`; `CMP-SERIES-01` calls it).

:func:`enqueue_pair_result` writes one ``comparison_work`` row of module ``versions`` and kind ``pair_result`` in the
caller's transaction -- the caller commits. The dedupe key is a function of the two page-profile identities only
(``pair_result:<page_a>:<page_b>``; the project is part of the queue's own unique index), so a double click, a retried
command and a re-run of a series enqueue a pair once while it is live; once the item has ended the next call makes a
new one, which finds the result by its content key and completes at once.

The pages must belong to the project (an item is owned by its project, and the erase of a project waits for its live
items): a page of another project, or an unknown one, is ``not_found``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.comparison.engine.handler import PAIR_RESULT_KIND, pair_result_payload
from auditmanager.comparison.engine.repository import PairResultRepository
from auditmanager.comparison.engine.service import PART_KINDS
from auditmanager.comparison.modules import MODULE_VERSIONS
from auditmanager.comparison.work.repository import ComparisonWorkRepository, Enqueued
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ComparisonPageProfileId, IdentityError

__all__ = ["enqueue_pair_result", "pair_result_dedupe_key"]

_PRIORITY: Final[int] = 0


def pair_result_dedupe_key(page_a_profile_id: str, page_b_profile_id: str) -> str:
    """The key under which one pair's live ``pair_result`` item is held (at most 256 characters)."""
    return f"{PAIR_RESULT_KIND}:{page_a_profile_id}:{page_b_profile_id}"


def enqueue_pair_result(
    session: Session,
    *,
    project_uid: str,
    page_a_profile_id: str,
    page_b_profile_id: str,
    created_by_user_uid: str,
    reasons: Sequence[str] = (),
    part: str | None = None,
    comparison_upload_id: str | None = None,
    comparison_series_id: str | None = None,
) -> Enqueued:
    """Enqueue the comparison of two page profiles, or answer the live item that already is.

    ``comparison_series_id`` attaches the item to a series (`CMP-SERIES-01`): the series' pause, resume and cancel reach it.
    It is not part of the item's identity: the dedupe key stays ``pair_result:<a>:<b>``."""
    pages = []
    for field, value in (("page_a_profile_id", page_a_profile_id), ("page_b_profile_id", page_b_profile_id)):
        try:
            pages.append(str(ComparisonPageProfileId(value)))
        except IdentityError as failure:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint="pattern") from failure
    if part is not None and part not in PART_KINDS:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="part", constraint="enum")
    if PairResultRepository().pages_of_project(session, project_uid, pages) != set(pages):
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ComparisonPageProfile")
    return ComparisonWorkRepository().enqueue(
        session,
        project_uid=project_uid,
        module=MODULE_VERSIONS,
        kind=PAIR_RESULT_KIND,
        payload=pair_result_payload(pages[0], pages[1], reasons=reasons, part=part),
        dedupe_key=pair_result_dedupe_key(pages[0], pages[1]),
        created_by_user_uid=created_by_user_uid,
        comparison_upload_id=comparison_upload_id,
        comparison_series_id=comparison_series_id,
    )
