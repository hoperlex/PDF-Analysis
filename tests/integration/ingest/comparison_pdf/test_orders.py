"""`CMP-INGEST-01`: «Порядок версий» -- append-only revisions, an expert's act, and **never the documents' ordinal**
(ADR-0025 decisions 14 and 16, ``D-5``).

The order is a document's own history in ``comparison_version_order``; ``document_version.version_ordinal`` is the
publication order that runs and finding carry-over use, and no order revision changes it. A stale base is a conflict the
caller rebases; a revision lists **every** version of the document exactly once; an administrator without the expert role is
refused; and the table refuses an update or a delete of a revision whoever asks.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.comparison_pdf.public import ConfirmedFile
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, new_ulid
from tests.integration.ingest.comparison_pdf.support import ADMIN, EXPERT, LABEL, table, upload_batch, vs1


def _refused(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


@pytest.fixture
def document(comparison, project, user, session_factory):
    """One document of five comparison versions; its first order revision is the confirmation's."""
    view = upload_batch(comparison, str(project.project_uid), vs1(), user=user)
    proposed = comparison.get_proposal(upload_id=view.upload_id).sets[0]
    done = comparison.confirm_set(
        upload_id=view.upload_id, set_id=proposed.set_id, files=[ConfirmedFile(f.file_id) for f in proposed.files],
        designation=None, existing_document_uid=None, project_stage=None, section_code=None, user_uid=user,
        actor_roles=EXPERT, idempotency_key="confirm")
    with session_factory() as session:
        versions = list(reversed(DocumentRepository().list_versions(session, DocumentUid.parse(done.document_uid))))
    return done.document_uid, [str(v.version_uid) for v in versions]


def _append(orders, project, document_uid, versions, base, user, *, key="a1", roles=EXPERT):
    return orders.append_order(
        project_uid=str(project.project_uid), document_uid=document_uid, version_uids=versions, base_revision_no=base,
        user_uid=user, actor_label=LABEL, actor_roles=roles, idempotency_key=key)


class TestAppendingARevision:
    def test_a_new_revision_follows_the_latest_and_is_the_experts(self, orders, project, document, user, session_factory) -> None:
        document_uid, versions = document
        reordered = list(reversed(versions))
        revision = _append(orders, project, document_uid, reordered, 1, user)
        assert (revision.revision_no, revision.source, revision.created_by) == (2, "expert", user)
        assert list(revision.version_uids) == reordered and revision.order_id.startswith("cvo_")
        with session_factory() as session:
            assert table(session, "SELECT revision_no, source, actor_label FROM comparison_version_order ORDER BY revision_no") == [
                (1, "proposal", LABEL), (2, "expert", LABEL)]

    def test_the_documents_ordinal_never_changes(self, orders, project, document, user, session_factory) -> None:
        document_uid, versions = document
        with session_factory() as session:
            before = table(session, "SELECT version_uid, version_ordinal FROM document_version ORDER BY version_ordinal")
        _append(orders, project, document_uid, list(reversed(versions)), 1, user)
        _append(orders, project, document_uid, [versions[2], *versions[:2], *versions[3:]], 2, user, key="a2")
        with session_factory() as session:
            assert table(session, "SELECT version_uid, version_ordinal FROM document_version ORDER BY version_ordinal") == before
            assert [r[1] for r in before] == [1, 2, 3, 4, 5]

    def test_a_repeat_under_the_same_key_answers_the_first_revision(self, orders, project, document, user, session_factory) -> None:
        document_uid, versions = document
        first = _append(orders, project, document_uid, list(reversed(versions)), 1, user)
        again = _append(orders, project, document_uid, list(reversed(versions)), 1, user)
        assert again == first
        with session_factory() as session:
            assert table(session, "SELECT count(*) FROM comparison_version_order") == [(2,)]

    def test_the_same_key_for_another_order_is_refused(self, orders, project, document, user) -> None:
        document_uid, versions = document
        _append(orders, project, document_uid, list(reversed(versions)), 1, user)
        refused = _refused(lambda: _append(orders, project, document_uid, versions, 1, user))
        assert refused.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


class TestARevisionIsRebasedNotOverwritten:
    def test_a_stale_base_is_a_conflict_and_nothing_is_written(self, orders, project, document, user, session_factory) -> None:
        document_uid, versions = document
        _append(orders, project, document_uid, list(reversed(versions)), 1, user)
        refused = _refused(lambda: _append(orders, project, document_uid, versions, 1, user, key="a2"))
        assert refused.code is ErrorCode.CONFLICT and refused.detail_fields["conflict_reason"] == "comparison_version_order_stale"
        with session_factory() as session:
            assert table(session, "SELECT count(*) FROM comparison_version_order") == [(2,)]

    def test_a_base_ahead_of_the_history_is_stale_too(self, orders, project, document, user) -> None:
        document_uid, versions = document
        refused = _refused(lambda: _append(orders, project, document_uid, versions, 5, user))
        assert refused.detail_fields["conflict_reason"] == "comparison_version_order_stale"

    def test_a_document_with_no_order_yet_takes_base_zero(self, orders, project, comparison, user, session_factory, service) -> None:
        """A document that was never confirmed through a comparison upload has no revision: base 0."""
        from auditmanager.shared.identity import ProjectUid

        with session_factory() as session:
            repo = DocumentRepository()
            document = repo.create_document(session, ProjectUid.parse(str(project.project_uid)), "без порядка")
            session.commit()
        refused = _refused(lambda: _append(orders, project, str(document), [], 0, user))
        assert refused.code is ErrorCode.VALIDATION_FAILED  # a document with no version has nothing to order

    def test_two_requests_on_one_base_make_one_revision(self, orders, project, document, user, session_factory) -> None:
        from concurrent.futures import ThreadPoolExecutor

        document_uid, versions = document

        def attempt(number: int):
            order = versions if number % 2 else list(reversed(versions))
            try:
                return _append(orders, project, document_uid, order, 1, user, key=f"race-{number}")
            except DomainError as refused:
                return refused

        with ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(attempt, range(4)))
        assert sum(1 for o in outcomes if not isinstance(o, DomainError)) == 1
        assert all(o.detail_fields["conflict_reason"] == "comparison_version_order_stale" for o in outcomes if isinstance(o, DomainError))
        with session_factory() as session:
            assert [r[0] for r in table(session, "SELECT revision_no FROM comparison_version_order ORDER BY revision_no")] == [1, 2]


class TestTheStaleCheckAndTheInsertAreOneDecision:
    def test_a_request_that_arrives_while_a_revision_is_being_written_waits_and_is_then_stale(
        self, orders, project, document, user, session_factory
    ) -> None:
        """Session A holds the document's order lock with revision 2 written and not yet committed. A request on
        base 1 must **wait for the lock** and, when A commits, be refused as stale -- never read revision 1, pass the
        stale check and die on the chain trigger with a database error."""
        import time
        from concurrent.futures import ThreadPoolExecutor

        from auditmanager.ingest import CommandRepository, payload_fingerprint
        from auditmanager.ingest.comparison_pdf.public import ComparisonUploadRepository
        from auditmanager.ingest.comparison_pdf.repository import new_order_id
        from auditmanager.shared.identity import IdempotencyKey

        document_uid, versions = document
        repo = ComparisonUploadRepository()
        a = session_factory()
        try:
            claim = CommandRepository().begin(a, command_type="append_comparison_version_order",
                                              idempotency_key=IdempotencyKey("holder"),
                                              fingerprint=payload_fingerprint({"holder": 1}))
            repo.lock_document_order(a, document_uid)
            repo.insert_order(a, order_id=new_order_id(), project_uid=str(project.project_uid), document_uid=document_uid,
                              revision_no=2, version_uids=list(reversed(versions)), source="expert", actor_user_uid=user,
                              actor_label=LABEL, command_id=str(claim.command_id))
            with ThreadPoolExecutor(max_workers=1) as pool:
                waiting = pool.submit(lambda: _attempt(orders, project, document_uid, versions, user))
                time.sleep(1.0)
                assert not waiting.done(), "the request did not wait for the order lock"
                a.commit()
                outcome = waiting.result(timeout=30)
        finally:
            a.close()
        assert isinstance(outcome, DomainError), outcome
        assert outcome.code is ErrorCode.CONFLICT and outcome.detail_fields["conflict_reason"] == "comparison_version_order_stale"


def _attempt(orders, project, document_uid, versions, user):
    try:
        return _append(orders, project, document_uid, versions, 1, user, key="late")
    except Exception as failure:  # noqa: BLE001 - the test reads what kind of failure it was
        return failure


class TestARevisionListsTheDocumentsVersions:
    @pytest.mark.parametrize("make", [
        lambda v: v[:-1],                       # one left out
        lambda v: [*v, v[0]],                   # one twice
        lambda v: [*v[:-1], "ver_" + new_ulid()],  # one that is not the document's
        lambda v: [],                           # none
    ], ids=["left-out", "twice", "foreign", "none"])
    def test_every_version_of_the_document_exactly_once(self, orders, project, document, user, session_factory, make) -> None:
        document_uid, versions = document
        refused = _refused(lambda: _append(orders, project, document_uid, make(versions), 1, user))
        assert refused.code is ErrorCode.VALIDATION_FAILED
        assert (refused.detail_fields["field"], refused.detail_fields["constraint"]) == ("version_uids", "comparison_set_members")
        with session_factory() as session:
            assert table(session, "SELECT count(*) FROM comparison_version_order") == [(1,)]

    def test_a_version_of_another_document_is_refused(self, orders, comparison, project, document, user, session_factory) -> None:
        document_uid, versions = document
        other = upload_batch(comparison, str(project.project_uid), {"x.pdf": vs1()["v3.pdf"]}, user=f"usr_{'0' * 26}", key="other")
        proposed = comparison.get_proposal(upload_id=other.upload_id).sets[0]
        done = comparison.confirm_set(
            upload_id=other.upload_id, set_id=proposed.set_id, files=[ConfirmedFile(f.file_id) for f in proposed.files],
            designation="другой", existing_document_uid=None, project_stage=None, section_code=None, user_uid=user,
            actor_roles=EXPERT, idempotency_key="c2")
        with session_factory() as session:
            foreign = str(DocumentRepository().list_versions(session, DocumentUid.parse(done.document_uid))[0].version_uid)
        refused = _refused(lambda: _append(orders, project, document_uid, [*versions[:-1], foreign], 1, user))
        assert refused.detail_fields["constraint"] == "comparison_set_members"


class TestTheExpertsAct:
    def test_an_administrator_without_the_expert_role_is_refused_and_nothing_is_written(
        self, orders, project, document, user, session_factory
    ) -> None:
        document_uid, versions = document
        refused = _refused(lambda: _append(orders, project, document_uid, list(reversed(versions)), 1, user, roles=ADMIN))
        assert refused.code is ErrorCode.PERMISSION_DENIED and refused.detail_fields == {"required_capability": "role:expert"}
        with session_factory() as session:
            assert table(session, "SELECT count(*) FROM comparison_version_order") == [(1,)]

    def test_listing_is_open_to_any_role_the_edge_lets_through(self, orders, project, document) -> None:
        document_uid, _versions = document
        assert len(orders.list_orders(project_uid=str(project.project_uid), document_uid=document_uid, before_revision=None, limit=10).items) == 1


class TestTheHistoryIsAppendOnly:
    @pytest.mark.parametrize("statement", [
        "UPDATE comparison_version_order SET source = 'proposal'",
        "UPDATE comparison_version_order SET version_uids = '[]'::jsonb",
        "DELETE FROM comparison_version_order",
    ])
    def test_the_table_refuses_an_update_or_a_delete_whoever_asks(self, document, session_factory, statement) -> None:
        with session_factory() as session:
            with pytest.raises(DBAPIError) as refused:
                session.execute(text(statement))
            assert getattr(refused.value.orig, "sqlstate", None) == "AM003"

    def test_a_revision_that_skips_a_number_is_refused_by_the_chain(self, document, session_factory, user) -> None:
        document_uid, versions = document
        with session_factory() as session:
            with pytest.raises(DBAPIError) as refused:
                session.execute(text(
                    "INSERT INTO comparison_version_order (comparison_version_order_id, project_uid, document_uid, revision_no, "
                    "version_uids, source, actor_user_uid, actor_label, command_id) "
                    "SELECT 'cvo_' || substr(comparison_version_order_id, 5), project_uid, document_uid, 9, version_uids, 'expert', "
                    "actor_user_uid, actor_label, command_id FROM comparison_version_order LIMIT 1"))
            assert getattr(refused.value.orig, "sqlstate", None) in ("AM001", "23505", "23503")


class TestListing:
    def test_the_revisions_come_newest_first_and_page_by_revision(self, orders, project, document, user) -> None:
        document_uid, versions = document
        for number in range(2, 6):
            _append(orders, project, document_uid, versions if number % 2 else list(reversed(versions)), number - 1, user, key=f"a{number}")
        first = orders.list_orders(project_uid=str(project.project_uid), document_uid=document_uid, before_revision=None, limit=2)
        assert [r.revision_no for r in first.items] == [5, 4] and first.next_before_revision == 4
        second = orders.list_orders(project_uid=str(project.project_uid), document_uid=document_uid, before_revision=4, limit=2)
        assert [r.revision_no for r in second.items] == [3, 2] and second.next_before_revision == 2
        last = orders.list_orders(project_uid=str(project.project_uid), document_uid=document_uid, before_revision=2, limit=2)
        assert [r.revision_no for r in last.items] == [1] and last.next_before_revision is None

    def test_an_unknown_project_or_document_or_a_document_of_another_project_is_not_found(self, orders, project, document, service) -> None:
        document_uid, _versions = document
        other = service.create_project("другой")
        for project_uid, doc, aggregate in (
            (f"prj_{new_ulid()}", document_uid, "Project"),
            (str(project.project_uid), f"doc_{new_ulid()}", "Document"),
            (str(other.project_uid), document_uid, "Document"),
        ):
            refused = _refused(lambda: orders.list_orders(project_uid=project_uid, document_uid=doc, before_revision=None, limit=10))
            assert refused.code is ErrorCode.NOT_FOUND and refused.detail_fields == {"aggregate_type": aggregate}
