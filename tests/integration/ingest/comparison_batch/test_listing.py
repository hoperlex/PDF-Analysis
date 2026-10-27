"""`CMP-INGEST-02`: ``listComparisonUploads`` -- a project's batches, newest first, without their files, by keyset."""

from __future__ import annotations

import pytest

from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.ingest.comparison_batch.support import Harness


def _batches(h: Harness, count: int) -> list[str]:
    """``count`` batches of one project, oldest first (one account may have one active batch, so each is cancelled)."""
    made: list[str] = []
    for index in range(count):
        made.append(h.declare([f"Set {index} (1).pdf"]).upload_id)
        h.cancel(made[-1])
    return made


def _walk(h: Harness, *, limit: int) -> list[list[str]]:
    pages: list[list[str]] = []
    after = None
    for _ in range(30):  # a listing whose cursor does not advance must fail here, not hang
        page = h.batches.list_uploads(project_uid=h.project_uid, after=after, limit=limit)
        pages.append([item.upload_id for item in page.items])
        if page.next_after is None:
            return pages
        after = page.next_after
    raise AssertionError(f"the listing never ended: {pages[-3:]}")


class TestTheListing:
    def test_batches_come_newest_first_with_their_states_and_without_their_files(self, h: Harness) -> None:
        made = _batches(h, 3)
        last = h.declare(["Last (1).pdf"]).upload_id
        page = h.batches.list_uploads(project_uid=h.project_uid, after=None, limit=50)
        assert [item.upload_id for item in page.items] == [last, *reversed(made)]
        assert [item.state for item in page.items] == ["uploading", "cancelled", "cancelled", "cancelled"]
        assert all(item.files is None for item in page.items), "the listing carries no files"
        assert page.next_after is None
        assert (page.items[0].declared_files, page.items[0].part_size_bytes) == (1, 16 * 1024 * 1024)

    def test_a_state_is_the_states_of_the_batch_as_it_moves(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})

        def listed() -> str:
            return h.batches.list_uploads(project_uid=h.project_uid, after=None, limit=5).items[0].state

        assert listed() == "proposed"
        h.confirm(upload_id, h.sets(upload_id)[0])
        assert listed() == "processing"
        h.pause(upload_id)
        assert listed() == "paused"
        h.resume(upload_id)
        h.cancel(upload_id)
        assert listed() == "cancelled"

    @pytest.mark.parametrize("limit", [1, 2, 3, 5, 6])
    def test_pages_cover_every_batch_once_in_order(self, h: Harness, limit: int) -> None:
        made = _batches(h, 5)
        pages = _walk(h, limit=limit)
        flat = [upload for page in pages for upload in page]
        assert flat == list(reversed(made)), "no gap, no repeat, newest first"
        assert all(len(page) <= limit for page in pages)
        assert sum(1 for page in pages if len(page) == limit) >= (5 // limit if limit < 6 else 0)

    def test_a_batch_created_between_two_pages_does_not_shift_the_next_one(self, h: Harness) -> None:
        made = _batches(h, 4)
        first = h.batches.list_uploads(project_uid=h.project_uid, after=None, limit=2)
        newer = h.declare(["Newer (1).pdf"]).upload_id
        second = h.batches.list_uploads(project_uid=h.project_uid, after=first.next_after, limit=2)
        assert [i.upload_id for i in first.items] == [made[3], made[2]]
        assert [i.upload_id for i in second.items] == [made[1], made[0]], "a keyset, not an offset"
        assert newer not in {i.upload_id for i in second.items}

    def test_an_exact_multiple_of_the_limit_ends_without_a_dangling_cursor(self, h: Harness) -> None:
        _batches(h, 4)
        assert [len(p) for p in _walk(h, limit=2)] == [2, 2]

    def test_only_the_projects_own_batches_are_listed(self, h: Harness, service, other_user: str) -> None:
        mine = h.declare(["Mine (1).pdf"]).upload_id
        elsewhere = service.create_project("another project")
        from tests.integration.ingest.comparison_batch.support import Harness as H

        other = H(comparison=h.comparison, batches=h.batches, sessions=h.sessions,
                  project_uid=str(elsewhere.project_uid), user=h.user)
        theirs = other.declare(["Theirs (1).pdf"], user=other_user).upload_id
        assert [i.upload_id for i in h.batches.list_uploads(project_uid=h.project_uid, after=None, limit=10).items] == [mine]
        assert [i.upload_id for i in h.batches.list_uploads(project_uid=other.project_uid, after=None, limit=10).items] == [theirs]

    def test_a_project_with_no_batches_is_an_empty_page_and_an_unknown_project_is_not_found(self, h: Harness) -> None:
        empty = h.batches.list_uploads(project_uid=h.project_uid, after=None, limit=10)
        assert empty.items == () and empty.next_after is None
        with pytest.raises(DomainError) as refused:
            h.batches.list_uploads(project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", after=None, limit=10)
        assert refused.value.code is ErrorCode.NOT_FOUND
