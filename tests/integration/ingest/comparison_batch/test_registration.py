"""`CMP-INGEST-02`: the two work kinds are registered, the product knows the five command types, and the one keyword this
lane added to the profile queue's enqueue attaches an item to its batch without changing what makes it unique."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from auditmanager.bootstrap.composition import build_comparison_work
from auditmanager.comparison.public import (
    HANDLER_FACTORIES,
    ComparisonWorkRepository,
    HandlerRegistry,
    HandlerRegistryError,
    WorkDependencies,
    WorkQueueError,
    enqueue_version_page_profiles,
)
from auditmanager.comparison.work.model import KIND_PATTERN, LIVE_STATES
from auditmanager.ingest.comparison_batch import rules
from auditmanager.ingest.comparison_batch.public import (
    BATCH_HANDLER_FACTORIES,
    DRIVE_KIND,
    SWEEP_KIND,
    batch_drive_handler,
)
from auditmanager.shared.db import session_scope
from tests.integration.ingest.comparison_batch.support import Harness


def _deps(session_factory, engine, store) -> WorkDependencies:
    return WorkDependencies(engine=engine, session_factory=session_factory, blob_store=store, work=ComparisonWorkRepository())


class TestTheWorkKinds:
    def test_the_live_states_this_lane_counts_are_the_queues(self) -> None:
        assert rules.LIVE_ITEM_STATES == LIVE_STATES

    def test_the_kinds_are_valid_and_new(self, session_factory, engine, store) -> None:
        assert KIND_PATTERN.match(DRIVE_KIND) and KIND_PATTERN.match(SWEEP_KIND) and DRIVE_KIND != SWEEP_KIND
        existing = {factory(_deps(session_factory, engine, store)).kind for factory in HANDLER_FACTORIES}
        assert not existing & {DRIVE_KIND, SWEEP_KIND}
        batch = [factory(_deps(session_factory, engine, store)).kind for factory in BATCH_HANDLER_FACTORIES]
        assert sorted(batch) == sorted([DRIVE_KIND, SWEEP_KIND])

    def test_the_registry_takes_both_beside_the_queues_own_and_refuses_a_second_handler_of_a_kind(
        self, session_factory, engine, store
    ) -> None:
        deps = _deps(session_factory, engine, store)
        registry = HandlerRegistry.build((*HANDLER_FACTORIES, *BATCH_HANDLER_FACTORIES), deps)
        assert {DRIVE_KIND, SWEEP_KIND, "page_profile"} <= registry.kinds
        with pytest.raises((HandlerRegistryError, WorkQueueError)):
            HandlerRegistry.build((*HANDLER_FACTORIES, *BATCH_HANDLER_FACTORIES, batch_drive_handler), deps)

    def test_the_composition_root_builds_a_runner_that_claims_both(self, session_factory, engine, store) -> None:
        runner = build_comparison_work(
            sessions=session_factory, engine=engine, blob_store=store,
            environ={"AUDITMANAGER_COMPARISON_MODULES": "versions"},
        )
        assert {DRIVE_KIND, SWEEP_KIND, "page_profile"} <= runner.kinds
        runner.verify()  # the worker's start check: no live item of a kind without a handler

    def test_the_five_command_types_are_product_receipts_of_the_purge(self) -> None:
        from scripts.recovery.product_purge import PRODUCT_COMMAND_TYPES

        mine = {rules.COMMAND_EXCLUDE_SET, rules.COMMAND_RETRY_SET, rules.COMMAND_PAUSE_UPLOAD,
                rules.COMMAND_RESUME_UPLOAD, rules.COMMAND_CANCEL_UPLOAD}
        assert mine <= PRODUCT_COMMAND_TYPES and len(mine) == 5


class TestTheKeywordOfTheProfileQueue:
    def test_an_item_is_attached_to_its_batch_and_its_identity_is_the_versions_alone(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.confirm(upload_id, alpha, hook=False)
        h.confirm(upload_id, beta, hook=False)
        proposal_a, proposal_b = [
            h.rows("SELECT proposal FROM comparison_upload_set WHERE comparison_upload_set_id = :s", s=one.set_id)[0][0]
            for one in (alpha, beta)
        ]
        version_a = proposal_a["confirmed"]["files"][0]["version_uid"]
        version_b = proposal_b["confirmed"]["files"][0]["version_uid"]
        with session_scope(h.sessions) as session:
            attached = enqueue_version_page_profiles(
                session, project_uid=h.project_uid, version_uid=version_a, created_by_user_uid=h.user,
                comparison_upload_id=upload_id)
            plain = enqueue_version_page_profiles(
                session, project_uid=h.project_uid, version_uid=version_b, created_by_user_uid=h.user)
            again = enqueue_version_page_profiles(
                session, project_uid=h.project_uid, version_uid=version_a, created_by_user_uid=h.user)
        assert attached.created and plain.created and not again.created and again.work_id == attached.work_id
        rows = {w["id"]: w for w in h.work(kind="page_profile")}
        assert rows[attached.work_id]["upload"] == upload_id and rows[plain.work_id]["upload"] is None
        assert rows[attached.work_id]["dedupe_key"] == f"page_profile:{version_a}"

    def test_the_database_refuses_an_item_attached_to_a_batch_that_does_not_exist(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.confirm(upload_id, alpha, hook=False)
        proposal = h.rows("SELECT proposal FROM comparison_upload_set WHERE comparison_upload_set_id = :s", s=alpha.set_id)[0][0]
        version = proposal["confirmed"]["files"][0]["version_uid"]
        with pytest.raises(IntegrityError) as refused:
            with session_scope(h.sessions) as session:
                enqueue_version_page_profiles(
                    session, project_uid=h.project_uid, version_uid=version, created_by_user_uid=h.user,
                    comparison_upload_id="cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV")
        assert "fk_comparison_work_upload" in str(refused.value)
        assert h.work(kind="page_profile") == []
