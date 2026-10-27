"""`CMP-INGEST-01`: one drawing set, end to end, on the real PostgreSQL and the real MinIO.

Five versions of one drawing set (``fixtures/comparison/vs1``) are declared **in the wrong order and under names that
mislead** (a name is a hint, never an identity), sent, completed, proposed and confirmed. The proposal is held to the
fixture's answer key: the designation, the order of the versions by their highest «Изм.», their dates. What the
confirmation makes is read back from the tables: one document, five ``comparison_pdf`` versions, the classification the
user confirmed, one order revision, and no change of any version's ordinal by the order.
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from auditmanager.documents.public import (
    MANIFEST_ROLE_COMPARISON_PDF,
    MANIFEST_ROLE_SOURCE_DOCUMENT,
    UPLOAD_KIND_COMPARISON_PDF,
    DocumentRepository,
)
from auditmanager.ingest.comparison_pdf.public import ComparisonUploadService, ConfirmedFile
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid
from tests.integration.ingest.comparison_pdf.support import (
    CORPUS,
    EXPERT,
    sha256,
    table,
    upload_batch,
    vs1,
)

KEY = json.loads((CORPUS / "vs1" / "answer_key.json").read_text(encoding="utf-8"))
#: Names that disagree with the truth: the newest version is called v1, and the numbers in the names run backwards.
MISLEADING = {"v5.pdf": "Чертежи ЭМ (1).pdf", "v4.pdf": "Чертежи ЭМ (2).pdf", "v3.pdf": "Чертежи ЭМ (3).pdf",
              "v2.pdf": "Чертежи ЭМ (4).pdf", "v1.pdf": "Чертежи ЭМ (5).pdf"}


@pytest.fixture
def batch(comparison: ComparisonUploadService, project, user):
    files = {MISLEADING[name]: data for name, data in vs1().items()}
    return upload_batch(comparison, str(project.project_uid), files, user=user), files


class TestTheProposal:
    def test_a_finished_batch_is_proposed_with_one_set_awaiting_confirmation(self, comparison, batch, user) -> None:
        view, _files = batch
        assert view.state == "proposed"
        assert [item.state for item in view.files or ()] == ["verified"] * 5
        proposal = comparison.get_proposal(upload_id=view.upload_id)
        assert proposal.state == "proposed" and len(proposal.sets) == 1
        assert proposal.sets[0].state == "needs_confirmation"

    def test_the_set_is_grouped_by_the_stamps_designation_not_by_the_names(self, comparison, batch, user) -> None:
        view, _files = batch
        only = comparison.get_proposal(upload_id=view.upload_id).sets[0]
        assert only.designation == KEY["designation"] == "СИНТ-01-ЭМ"
        assert len(only.files) == 5

    def test_the_proposed_order_is_the_answer_keys_whatever_the_names_say(self, comparison, batch, user) -> None:
        view, files = batch
        by_sha = {sha256(data): name for name, data in files.items()}
        names_by_file = {item.file_id: by_sha[item.sha256] for item in view.files or ()}
        proposed = comparison.get_proposal(upload_id=view.upload_id).sets[0]
        key_order = [MISLEADING[version["file"].split("/")[1]] for version in KEY["versions"]]
        assert [names_by_file[item.file_id] for item in proposed.files] == key_order
        # The numbers in the names run backwards, so the reader says its order disagrees with them.
        assert "order_disagrees_with_file_numbers" in proposed.warnings

    def test_the_labels_are_the_keys_label_and_date(self, comparison, batch, user) -> None:
        view, _files = batch
        proposed = comparison.get_proposal(upload_id=view.upload_id).sets[0]
        expected = [
            f"V{position} {version['label']} {version['date']}"
            for position, version in enumerate(KEY["versions"], start=1)
        ]
        assert [item.version_label for item in proposed.files] == expected

    def test_the_scan_page_is_a_warning_and_the_stage_and_section_are_proposals(self, comparison, batch, user) -> None:
        view, _files = batch
        proposed = comparison.get_proposal(upload_id=view.upload_id).sets[0]
        assert proposed.warnings == ("order_disagrees_with_file_numbers", "scan_without_text")
        assert (proposed.project_stage, proposed.section_code) == ("R", "EOM")
        assert proposed.existing_document_uid is None and proposed.document_uid is None

    def test_nothing_is_a_version_before_the_user_confirms(self, batch, session_factory) -> None:
        with session_factory() as session:
            assert table(session, "SELECT count(*) FROM document_version") == [(0,)]
            assert table(session, "SELECT count(*) FROM document") == [(0,)]


class TestTheConfirmation:
    def _confirm(self, comparison, view, user, **overrides):
        proposed = comparison.get_proposal(upload_id=view.upload_id).sets[0]
        arguments = dict(
            upload_id=view.upload_id, set_id=proposed.set_id,
            files=[ConfirmedFile(item.file_id) for item in proposed.files],
            designation=None, existing_document_uid=None, project_stage="R", section_code="EOM",
            user_uid=user, actor_roles=EXPERT, idempotency_key="confirm-1",
        )
        arguments.update(overrides)
        return proposed, comparison.confirm_set(**arguments)

    def test_one_document_and_one_comparison_version_per_file_in_the_confirmed_order(
        self, comparison, batch, session_factory
    , user) -> None:
        view, _files = batch
        proposed, done = self._confirm(comparison, view, user)
        assert done.state == "done" and done.document_uid is not None
        with session_factory() as session:
            versions = DocumentRepository().list_versions(session, DocumentUid.parse(done.document_uid))
        ascending = list(reversed(versions))
        assert [v.version_ordinal for v in ascending] == [1, 2, 3, 4, 5]
        assert {v.upload_kind for v in ascending} == {UPLOAD_KIND_COMPARISON_PDF}
        assert [v.sha256 for v in ascending] == [version["sha256"] for version in KEY["versions"]]
        assert all(v.page_count == k["page_count"] for v, k in zip(ascending, KEY["versions"], strict=True))
        assert all(v.text_character_count is None and v.textless_pages is None for v in ascending)

    def test_a_comparison_version_binds_its_pdf_under_the_distinct_manifest_role(self, comparison, batch, session_factory, user) -> None:
        view, _files = batch
        _proposed, done = self._confirm(comparison, view, user)
        with session_factory() as session:
            versions = DocumentRepository().list_versions(session, DocumentUid.parse(done.document_uid))
        for version in versions:
            assert [entry.role for entry in version.manifest] == [MANIFEST_ROLE_COMPARISON_PDF]
            assert version.source.role == MANIFEST_ROLE_COMPARISON_PDF  # the bytes accessor finds it
            with pytest.raises(KeyError):
                version.entry(MANIFEST_ROLE_SOURCE_DOCUMENT)  # ... and the run's own accessor does not

    def test_the_confirmed_classification_is_written_for_every_version(self, comparison, batch, session_factory, user) -> None:
        view, _files = batch
        _proposed, done = self._confirm(comparison, view, user)
        with session_factory() as session:
            rows = table(
                session,
                "SELECT c.project_stage, c.section_code, c.confirmed_by_user_uid FROM document_version_classification c "
                "JOIN document_version v ON v.version_uid = c.version_uid WHERE v.document_uid = :d",
                d=done.document_uid,
            )
        assert rows == [("R", "EOM", user)] * 5

    def test_without_a_stage_and_section_no_version_is_classified(self, comparison, batch, session_factory, user) -> None:
        view, _files = batch
        self._confirm(comparison, view, user, project_stage=None, section_code=None)
        with session_factory() as session:
            assert table(session, "SELECT count(*) FROM document_version_classification") == [(0,)]

    def test_the_document_is_titled_by_the_designation_the_user_confirmed(self, comparison, batch, session_factory, user) -> None:
        view, _files = batch
        _proposed, done = self._confirm(comparison, view, user, designation="Изменённое обозначение")
        with session_factory() as session:
            assert table(session, "SELECT display_title, section FROM document WHERE document_uid = :d", d=done.document_uid) == [
                ("Изменённое обозначение", "EOM")
            ]
        assert done.designation == "Изменённое обозначение"

    def test_the_order_is_recorded_as_a_revision_and_the_ordinal_is_untouched(self, comparison, batch, session_factory, user) -> None:
        view, _files = batch
        _proposed, done = self._confirm(comparison, view, user)
        with session_factory() as session:
            rows = table(
                session,
                "SELECT revision_no, source, jsonb_array_length(version_uids), actor_user_uid FROM comparison_version_order "
                "WHERE document_uid = :d",
                d=done.document_uid,
            )
            listed = table(session, "SELECT version_uids FROM comparison_version_order WHERE document_uid = :d", d=done.document_uid)
            by_ordinal = table(
                session, "SELECT version_uid FROM document_version WHERE document_uid = :d ORDER BY version_ordinal",
                d=done.document_uid,
            )
        assert rows == [(1, "proposal", 5, user)]  # the user accepted the proposed order unchanged
        assert [str(uid) for uid in listed[0][0]] == [row[0] for row in by_ordinal]

    def test_a_reordered_confirmation_is_an_expert_revision(self, comparison, batch, session_factory, user) -> None:
        view, _files = batch
        proposed = comparison.get_proposal(upload_id=view.upload_id).sets[0]
        reordered = [ConfirmedFile(item.file_id, f"моя метка {n}") for n, item in enumerate(reversed(proposed.files), 1)]
        done = comparison.confirm_set(
            upload_id=view.upload_id, set_id=proposed.set_id, files=reordered, designation=None,
            existing_document_uid=None, project_stage=None, section_code=None, user_uid=user, actor_roles=EXPERT,
            idempotency_key="confirm-reordered",
        )
        assert [item.version_label for item in done.files] == [f"моя метка {n}" for n in range(1, 6)]
        with session_factory() as session:
            assert table(session, "SELECT source FROM comparison_version_order") == [("expert",)]
            versions = list(reversed(DocumentRepository().list_versions(session, DocumentUid.parse(done.document_uid))))
        # The versions were made in the confirmed order: the oldest file (Изм.0) is now the last.
        assert [v.sha256 for v in versions] == [version["sha256"] for version in reversed(KEY["versions"])]

    def test_the_labels_are_kept_with_the_version_they_belong_to(self, comparison, batch, session_factory, user) -> None:
        view, _files = batch
        _proposed, done = self._confirm(comparison, view, user)
        from auditmanager.ingest.comparison_pdf.public import ComparisonUploadRepository

        with session_factory() as session:
            labels = ComparisonUploadRepository().version_labels(session, done.document_uid)
            versions = list(reversed(DocumentRepository().list_versions(session, DocumentUid.parse(done.document_uid))))
        assert [labels[str(v.version_uid)] for v in versions] == [
            f"V{n} {k['label']} {k['date']}" for n, k in enumerate(KEY["versions"], start=1)
        ]

    def test_the_batch_is_completed_when_its_only_set_is_done(self, comparison, batch, user) -> None:
        view, _files = batch
        self._confirm(comparison, view, user)
        assert comparison.get_upload(upload_id=view.upload_id).state == "completed"
        assert comparison.get_proposal(upload_id=view.upload_id).sets[0].state == "done"

    def test_a_repeat_under_the_same_key_answers_the_first_and_makes_nothing(self, comparison, batch, session_factory, user) -> None:
        view, _files = batch
        _proposed, first = self._confirm(comparison, view, user)
        _proposed2, second = self._confirm(comparison, view, user)
        assert second.document_uid == first.document_uid
        with session_factory() as session:
            assert table(session, "SELECT count(*) FROM document_version") == [(5,)]

    def test_the_same_key_for_another_payload_is_refused(self, comparison, batch, user) -> None:
        view, _files = batch
        self._confirm(comparison, view, user)
        with pytest.raises(DomainError) as refused:
            self._confirm(comparison, view, user, designation="другое")
        assert refused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE

    def test_a_set_that_is_not_awaiting_confirmation_is_a_conflict(self, comparison, batch, user) -> None:
        view, _files = batch
        self._confirm(comparison, view, user)
        with pytest.raises(DomainError) as refused:
            self._confirm(comparison, view, user, idempotency_key="confirm-2")
        assert refused.value.code is ErrorCode.CONFLICT
        assert refused.value.detail_fields["conflict_reason"] == "comparison_set_state"
