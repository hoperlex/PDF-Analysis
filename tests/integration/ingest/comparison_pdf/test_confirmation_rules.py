"""`CMP-INGEST-01`: the rules of confirming a set -- membership, state, the expert's act, the document a set joins -- and
ADR-0025 decision 11: a comparison-only version **never becomes the current version of a document that has a portal version**.

Decision 11 has a test per consumer of ``document.current_version_uid``: the statements of ``DocumentRepository`` (the listing,
the project's document count, the two section memberships), the dashboard's breakdown, and the API's own read path
(``IngestService``). A last test lists every place in ``src`` that reads the column, so a consumer added later is a red test
until it is judged here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.dashboard.repository import DashboardRepository
from auditmanager.documents.public import UPLOAD_KIND_COMPARISON_PDF, UPLOAD_KIND_PORTAL_BUNDLE, DocumentRepository
from auditmanager.ingest import IngestService
from auditmanager.ingest.comparison_pdf.public import ComparisonUploadService, ConfirmedFile
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdempotencyKey, ProjectUid
from tests.integration.ingest.comparison_pdf.support import ADMIN, CORPUS, EXPERT, table, upload_batch, vs1

ROOT = Path(__file__).resolve().parents[4]


def _refused(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def _confirm(service, view, set_index=0, *, user, key="confirm", **overrides):
    proposed = service.get_proposal(upload_id=view.upload_id).sets[set_index]
    arguments = dict(
        upload_id=view.upload_id, set_id=proposed.set_id, files=[ConfirmedFile(f.file_id) for f in proposed.files],
        designation=None, existing_document_uid=None, project_stage=None, section_code=None,
        user_uid=user, actor_roles=EXPERT, idempotency_key=key,
    )
    arguments.update(overrides)
    return proposed, service.confirm_set(**arguments)


@pytest.fixture
def one_set(comparison, project, user):
    return upload_batch(comparison, str(project.project_uid), vs1(), user=user)


@pytest.fixture
def two_sets(comparison, project, user):
    files = {"a.pdf": vs1()["v1.pdf"], "b.pdf": (CORPUS / "sp1" / "old_p.pdf").read_bytes()}
    return upload_batch(comparison, str(project.project_uid), files, user=f"usr_{'0' * 26}", key="two")


def _snapshot(factory: sessionmaker[Session]) -> list[int]:
    with factory() as session:
        return [table(session, f"SELECT count(*) FROM {name}")[0][0] for name in (
            "document", "document_version", "comparison_version_order", "document_version_classification", "command_record")]


class TestMembership:
    def _members(self, comparison, view, user, session_factory, files, constraint="comparison_set_members"):
        before = _snapshot(session_factory)
        refused = _refused(lambda: _confirm(comparison, view, user=user, files=files))
        assert refused.code is ErrorCode.VALIDATION_FAILED
        assert (refused.detail_fields["field"], refused.detail_fields["constraint"]) == ("files", constraint)
        assert _snapshot(session_factory) == before, "a refused confirmation wrote something"
        assert comparison.get_proposal(upload_id=view.upload_id).sets[0].state == "needs_confirmation"

    def test_a_file_listed_twice(self, comparison, one_set, user, session_factory) -> None:
        ids = [f.file_id for f in comparison.get_proposal(upload_id=one_set.upload_id).sets[0].files]
        self._members(comparison, one_set, user, session_factory, [ConfirmedFile(i) for i in [*ids, ids[0]]])

    def test_a_file_of_the_set_that_is_not_listed(self, comparison, one_set, user, session_factory) -> None:
        ids = [f.file_id for f in comparison.get_proposal(upload_id=one_set.upload_id).sets[0].files]
        self._members(comparison, one_set, user, session_factory, [ConfirmedFile(i) for i in ids[:-1]])

    def test_a_file_that_is_not_in_the_batch_at_all(self, comparison, one_set, user, session_factory) -> None:
        ids = [f.file_id for f in comparison.get_proposal(upload_id=one_set.upload_id).sets[0].files]
        self._members(comparison, one_set, user, session_factory, [ConfirmedFile(i) for i in [*ids, "cuf_" + "0" * 26]])

    def test_a_file_of_another_set(self, comparison, two_sets, user, session_factory) -> None:
        a, b = comparison.get_proposal(upload_id=two_sets.upload_id).sets
        before = _snapshot(session_factory)
        refused = _refused(lambda: comparison.confirm_set(
            upload_id=two_sets.upload_id, set_id=a.set_id, files=[ConfirmedFile(f.file_id) for f in (*a.files, *b.files)],
            designation=None, existing_document_uid=None, project_stage=None, section_code=None, user_uid=user,
            actor_roles=EXPERT, idempotency_key="x"))
        assert refused.detail_fields["constraint"] == "comparison_set_members" and _snapshot(session_factory) == before

    def test_the_stage_and_the_section_come_together_or_not_at_all(self, comparison, one_set, user, session_factory) -> None:
        before = _snapshot(session_factory)
        for stage, section, field in (("R", None, "section_code"), (None, "EOM", "project_stage")):
            refused = _refused(lambda: _confirm(comparison, one_set, user=user, project_stage=stage, section_code=section))
            assert (refused.detail_fields["field"], refused.detail_fields["constraint"]) == (field, "required_together")
        assert _snapshot(session_factory) == before

    def test_an_unknown_set_or_a_set_of_another_batch_is_not_found(self, comparison, two_sets, one_set, user) -> None:
        other = comparison.get_proposal(upload_id=two_sets.upload_id).sets[0]
        for upload_id, set_id in ((one_set.upload_id, "cus_" + "0" * 26), (one_set.upload_id, other.set_id)):
            refused = _refused(lambda: comparison.confirm_set(
                upload_id=upload_id, set_id=set_id, files=[ConfirmedFile("cuf_" + "0" * 26)], designation=None,
                existing_document_uid=None, project_stage=None, section_code=None, user_uid=user, actor_roles=EXPERT,
                idempotency_key="nf"))
            assert refused.code is ErrorCode.NOT_FOUND and refused.detail_fields == {"aggregate_type": "ComparisonUploadSet"}

    def test_a_set_still_uploading_is_not_awaiting_confirmation(self, comparison, project, user, session_factory) -> None:
        from tests.integration.ingest.comparison_pdf.support import complete, create, send

        files = vs1()
        view = create(comparison, str(project.project_uid), files, user=user)
        ids = {f.display_name: f.file_id for f in view.files or ()}
        send(comparison, view.upload_id, ids["v1.pdf"], files["v1.pdf"], key="k", user=user)
        complete(comparison, view.upload_id, ids["v1.pdf"], key="d", user=user)
        refused = _refused(lambda: _confirm(comparison, view, user=user))
        assert refused.code is ErrorCode.CONFLICT and refused.detail_fields["conflict_reason"] == "comparison_set_state"


class TestTheExpertsAct:
    def test_an_administrator_without_the_expert_role_is_refused_and_nothing_is_written(
        self, comparison, one_set, user, session_factory
    ) -> None:
        before = _snapshot(session_factory)
        refused = _refused(lambda: _confirm(comparison, one_set, user=user, actor_roles=ADMIN))
        assert refused.code is ErrorCode.PERMISSION_DENIED
        assert refused.detail_fields == {"required_capability": "role:expert"}
        assert _snapshot(session_factory) == before
        assert comparison.get_proposal(upload_id=one_set.upload_id).sets[0].state == "needs_confirmation"

    def test_an_account_with_both_roles_may_act(self, comparison, one_set, user) -> None:
        _proposed, done = _confirm(comparison, one_set, user=user, actor_roles=frozenset({"admin", "expert"}))
        assert done.state == "done"


class TestTheDocumentASetJoins:
    def _portal(self, service: IngestService, project, user, session_factory, baseline_bundle, *, section="AR"):
        outcome = service.upload_bundle(
            project_uid=ProjectUid.parse(str(project.project_uid)), content=baseline_bundle, source_filename="baseline.zip",
            display_title="Портальный документ", idempotency_key=IdempotencyKey("portal-1"),
        )
        with session_factory() as session:
            DocumentRepository().insert_classification(
                session, version_uid=outcome.version.version_uid, project_stage="R", section_code=section,
                confirmed_by_user_uid=user)
            session.commit()
        return outcome.version

    def test_a_document_of_another_project_is_not_found(self, comparison, one_set, service, user, session_factory, baseline_bundle) -> None:
        other = service.create_project("другой проект")
        foreign = service.upload_bundle(project_uid=other.project_uid, content=baseline_bundle, source_filename="b.zip",
                                        display_title="чужой", idempotency_key=IdempotencyKey("foreign-1")).version
        before = _snapshot(session_factory)
        refused = _refused(lambda: _confirm(comparison, one_set, user=user, existing_document_uid=str(foreign.document_uid)))
        assert refused.code is ErrorCode.NOT_FOUND and refused.detail_fields == {"aggregate_type": "Document"}
        assert _snapshot(session_factory) == before

    def test_a_set_may_join_an_existing_document_and_its_order_keeps_the_versions_already_there(
        self, comparison, one_set, service, project, user, session_factory, baseline_bundle
    ) -> None:
        portal = self._portal(service, project, user, session_factory, baseline_bundle)
        _proposed, done = _confirm(comparison, one_set, user=user, existing_document_uid=str(portal.document_uid))
        assert done.document_uid == str(portal.document_uid)
        with session_factory() as session:
            versions = list(reversed(DocumentRepository().list_versions(session, portal.document_uid)))
            order = table(session, "SELECT revision_no, version_uids FROM comparison_version_order")
        assert [v.version_ordinal for v in versions] == [1, 2, 3, 4, 5, 6]
        assert [v.upload_kind for v in versions] == [UPLOAD_KIND_PORTAL_BUNDLE, *[UPLOAD_KIND_COMPARISON_PDF] * 5]
        assert order[0][0] == 1 and [str(u) for u in order[0][1]] == [str(v.version_uid) for v in versions]

    def test_the_proposal_offers_the_document_a_designation_belongs_to_and_never_applies_it(
        self, comparison, one_set, project, user, session_factory
    ) -> None:
        _proposed, first = _confirm(comparison, one_set, user=user)
        # A second batch of the same drawing set: the proposal offers the document the first one made.
        again = upload_batch(comparison, str(project.project_uid), {"n.pdf": vs1()["v5.pdf"]}, user=user, key="second")
        offered = comparison.get_proposal(upload_id=again.upload_id).sets[0]
        assert offered.existing_document_uid == first.document_uid
        # The user's confirmation names no document, so a new one is made: an offer is never applied.
        _proposed2, second = _confirm(comparison, again, user=user, key="c2")
        assert second.document_uid != first.document_uid

    def test_a_document_whose_title_is_the_designation_is_offered_too(
        self, comparison, project, service, user, session_factory
    ) -> None:
        with session_factory() as session:
            document = DocumentRepository().create_document(session, ProjectUid.parse(str(project.project_uid)), "  синт-01-эм ")
            session.commit()
        view = upload_batch(comparison, str(project.project_uid), {"v1.pdf": vs1()["v1.pdf"]}, user=user)
        assert comparison.get_proposal(upload_id=view.upload_id).sets[0].existing_document_uid == str(document)


class TestDecisionElevenNeverTheCurrentVersionOfAPortalDocument:
    """One document with a portal version, then a confirmed comparison set added to it: every consumer of
    ``current_version_uid`` still sees the portal version."""

    @pytest.fixture
    def mixed(self, comparison, one_set, service, project, user, session_factory, baseline_bundle):
        portal = TestTheDocumentASetJoins()._portal(service, project, user, session_factory, baseline_bundle)
        _confirm(comparison, one_set, user=user, project_stage="R", section_code="EOM",
                 existing_document_uid=str(portal.document_uid))
        return portal

    def test_the_documents_row_still_points_at_the_portal_version(self, mixed, session_factory) -> None:
        with session_factory() as session:
            assert table(session, "SELECT current_version_uid FROM document") == [(str(mixed.version_uid),)]

    def test_consumer_list_documents(self, mixed, project, session_factory) -> None:
        with session_factory() as session:
            listed = DocumentRepository().list_documents(session, ProjectUid.parse(str(project.project_uid)))
        assert [(v.version_uid, v.upload_kind, v.version_ordinal) for v in listed] == [(mixed.version_uid, "portal_bundle", 1)]

    def test_consumer_the_api_read_path(self, mixed, service, project) -> None:
        assert [v.version_uid for v in service.list_documents(ProjectUid.parse(str(project.project_uid)))] == [mixed.version_uid]
        assert [r.document_count for r in service.list_projects() if str(r.project_uid) == str(project.project_uid)] == [1]

    def test_consumer_the_project_document_count(self, mixed, project, session_factory) -> None:
        with session_factory() as session:
            counts = {str(r.project_uid): r.document_count for r in DocumentRepository().list_projects(session)}
        assert counts[str(project.project_uid)] == 1

    def test_consumer_the_section_membership(self, mixed, project, session_factory) -> None:
        with session_factory() as session:
            documents = DocumentRepository()
            in_ar = documents.list_current_versions_in_section(session, section_code="AR", project_uid=ProjectUid.parse(str(project.project_uid)))
            in_eom = documents.list_current_versions_in_section(session, section_code="EOM", project_uid=ProjectUid.parse(str(project.project_uid)))
        assert [r.version_uid for r in in_ar] == [mixed.version_uid]
        assert in_eom == (), "a comparison version classified EOM became the document's current version"

    def test_consumer_the_unclassified_membership(self, mixed, project, session_factory) -> None:
        with session_factory() as session:
            assert DocumentRepository().list_unclassified_current_versions(session, project_uid=ProjectUid.parse(str(project.project_uid))) == ()

    def test_consumer_the_dashboard(self, mixed, project, session_factory) -> None:
        with session_factory() as session:
            summary = DashboardRepository().summary(session)
        by_section = {row.section: row.document_count for row in summary.section_breakdown}
        assert by_section["AR"] == 1 and by_section["EOM"] == 0 and by_section[None] == 0
        assert [r.document_count for r in summary.documents_by_project if r.project_uid == str(project.project_uid)] == [1]

    def test_every_version_is_still_listed_by_the_versions_read(self, mixed, session_factory) -> None:
        with session_factory() as session:
            versions = DocumentRepository().list_versions(session, mixed.document_uid)
        assert len(versions) == 6

    def test_a_later_portal_version_does_become_current_again(self, mixed, service, project, session_factory, baseline_bundle) -> None:
        later = service.upload_next_version(
            project_uid=ProjectUid.parse(str(project.project_uid)), document_uid=mixed.document_uid,
            content=baseline_bundle, source_filename="next.zip", idempotency_key=IdempotencyKey("portal-2")).version
        with session_factory() as session:
            assert table(session, "SELECT current_version_uid FROM document") == [(str(later.version_uid),)]

    def test_the_set_of_places_that_read_the_column_is_the_judged_one(self) -> None:
        """A consumer added later is a red test here until it is judged above (a mutation: a new reader)."""
        readers = sorted(
            str(path.relative_to(ROOT)) for path in (ROOT / "src").rglob("*.py")
            if re.search(r"\bcurrent_version_uid\b", path.read_text(encoding="utf-8"))
        )
        assert readers == [
            "src/auditmanager/dashboard/repository.py",       # the section breakdown (consumer_the_dashboard)
            "src/auditmanager/documents/models.py",           # a docstring
            "src/auditmanager/documents/repository.py",       # the writer and four statements (consumers above)
            "src/auditmanager/ingest/service.py",             # a docstring
        ]


class TestAComparisonOnlyDocument:
    def test_its_current_version_is_the_newest_comparison_version_and_a_portal_one_takes_over(
        self, comparison, one_set, service, project, user, session_factory, baseline_bundle
    ) -> None:
        _proposed, done = _confirm(comparison, one_set, user=user, project_stage="R", section_code="EOM")
        with session_factory() as session:
            versions = DocumentRepository().list_versions(session, DocumentUid.parse(done.document_uid))
            current = table(session, "SELECT current_version_uid FROM document")[0][0]
            listed = DocumentRepository().list_documents(session, ProjectUid.parse(str(project.project_uid)))
            summary = DashboardRepository().summary(session)
        assert current == str(versions[0].version_uid) and versions[0].version_ordinal == 5  # newest first
        assert [(v.version_uid, v.upload_kind) for v in listed] == [(versions[0].version_uid, "comparison_pdf")]
        assert {r.section: r.document_count for r in summary.section_breakdown}["EOM"] == 1
        portal = service.upload_next_version(
            project_uid=ProjectUid.parse(str(project.project_uid)), document_uid=DocumentUid.parse(done.document_uid),
            content=baseline_bundle, source_filename="n.zip", idempotency_key=IdempotencyKey("portal-3")).version
        with session_factory() as session:
            assert table(session, "SELECT current_version_uid FROM document") == [(str(portal.version_uid),)]


class TestTheSetsLimitOfTheStampGrouping:
    def test_the_hundred_and_first_set_is_refused_with_its_files_not_merged_into_another(
        self, store, session_factory, project, user
    ) -> None:
        """The limit at declaration is on the *names*; the stamps may group the same files into more sets. 101 files
        declared in one folder (one name group) whose stamps carry 101 designations make 101 sets: the 101st is
        ``failed`` with ``comparison_sets_limit`` and is never merged into another."""
        from datetime import date

        from auditmanager.ingest.comparison_pdf.limits import MAX_SETS
        from auditmanager.ingest.comparison_pdf.reading import PdfReading
        from auditmanager.ingest.comparison_pdf.stamp import FileStamp
        from auditmanager.ingest.envelope import PdfFacts
        from tests.integration.ingest.comparison_pdf.support import complete, declare, send

        def fake(handle, **_kwargs):
            number = int(handle.read().decode().split("#")[1])
            handle.seek(0)
            name = f"D{number:03d}-01-ЭМ"
            stamp = FileStamp(1, name, ((name, 1),), False, 0, date(2026, 1, 1), "R", "EOM", 1, ())
            return PdfReading(facts=PdfFacts(handle.seek(0, 2), 1, (100,), (True,), ((595.0, 842.0, 0),)), stamp=stamp)

        service = ComparisonUploadService(store, session_factory=session_factory, read=fake)
        files = {f"Один раздел/f{i}.pdf": f"%PDF-1.7 #{i}".encode() for i in range(MAX_SETS + 1)}
        view = service.create_upload(
            project_uid=str(project.project_uid), actor_label="Эксперт", user_uid=user, idempotency_key="decl",
            files=[declare(name, data) for name, data in files.items()],
        )
        ids = {f.display_name: f.file_id for f in view.files or ()}
        for index, (name, data) in enumerate(files.items()):
            send(service, view.upload_id, ids[name], data, key=f"k{index}", user=user)
            complete(service, view.upload_id, ids[name], key=f"d{index}", user=user)
        assert service.get_upload(upload_id=view.upload_id).state == "proposed"
        sets = service.get_proposal(upload_id=view.upload_id).sets
        assert len(sets) == MAX_SETS + 1
        assert [s.state for s in sets].count("needs_confirmation") == MAX_SETS
        failed = [s for s in sets if s.state == "failed"]
        assert [s.failure_reason for s in failed] == ["comparison_sets_limit"] and len(failed[0].files) == 1
