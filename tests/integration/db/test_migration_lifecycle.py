"""Clean install, re-run safety and the reported head.

These three are the task's required migration behaviours, asserted through the
literal commands the Makefile forwards to rather than through the Python API.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text

from auditmanager.shared.db.check import SUCCESS_SENTINEL
from auditmanager.shared.db.migrations import head_revision, revision_walk
from auditmanager.shared.db.config import DatabaseSettings

#: Every relation the P02 head must create. Written out rather than derived from the
#: database, so a table silently disappearing from the migration fails here.
EXPECTED_TABLES = {
    "alembic_version",
    # `0006_app_user`: the one table outside the PC-01 analysis schema. It is listed
    # here rather than exempted, because "exactly the declared relations" is the claim.
    "app_user",
    # `0015_accounts_roles_registration`: the role set and the registration requests.
    "app_user_role",
    "registration_request",
    # `0016_release_notes`: immutable release history and each account's mark.
    "release",
    "release_revision",
    "account_release_mark",
    # `0017_execution_queue`: one durable pause-control row, inserted lazily.
    "execution_control",
    # `0018_norm_custody`: custody admissions and bindings, and the paid repair journal.
    "norm_custody_admission",
    "norm_custody_binding",
    "norm_repair_call",
    # `0023_norm_citations`: verified retrieval set and immutable partitions.
    "norm_retrieval_set",
    "finding_observation_norm_citation",
    # `0024_version_classification`: one expert-confirmed stage and section per version.
    "document_version_classification",
    # `0025_work_assignments`: work given to experts and its append-only history.
    "work_assignment",
    "work_assignment_event",
    # `0026_price_lists`: project price lists with their positions, and vendor lists.
    "price_list_revision",
    "price_list_position",
    "vendor_list_revision",
    "vendor_list_entry",
    # `0027_optimisation_proposals`: optimisation passes, their proposals and the experts'
    # append-only decisions on them.
    "optimisation_pass",
    "optimisation_proposal",
    "optimisation_proposal_decision",
    # `0028_classification_corrections`: an expert's append-only corrections of a version's
    # stage and section (revision 2 and later; revision 1 is `document_version_classification`).
    "document_version_classification_correction",
    # `0030_executor_connections`: where a process sends model work, its immutable revisions,
    # sealed secrets (ciphertext only), probes and append-only route events.
    "executor_connection",
    "executor_connection_revision",
    "executor_secret",
    "executor_probe",
    "executor_route_event",
    # `0031_executor_pull_channel`: a runner's credential (hash only) and the tasks it takes.
    "executor_runner_token",
    "executor_task",
    # `0046_executor_capacity_enroll`: a universal agent's single-use enrollment grant (hash only) and its
    # SSH install sessions (`EXEC2-SEAL-1`, ADR-0026).
    "executor_enrollment",
    "executor_agent_install",
    # `0047_executor_groups_rules` (`EXEC2-SEAL-2`, ADR-0026): executor groups, their immutable revisions and members, the
    # append-only routing rules of the work kinds and the append-only journal of the routing mode.
    "executor_group",
    "executor_group_revision",
    "executor_group_member",
    "executor_routing_rule_revision",
    "executor_routing_mode_event",
    # `0035_comparison_records`: the approved sheet pairings of two versions, as an append-only history.
    "comparison_sheet_link",
    "comparison_summary",
    # `0037_analysis_presets`: the revisions of named presets, as an append-only history.
    "analysis_preset_revision",
    # `0038_comparison_foundation`: the comparison upload, version order, page profile, queue and spend
    # journal tables (`CMP-SEAL-C0`).
    "comparison_upload",
    "comparison_upload_set",
    "comparison_upload_file",
    "comparison_upload_part",
    "comparison_version_order",
    "comparison_page_profile",
    "comparison_work",
    "comparison_work_attempt",
    "comparison_model_call",
    # `0039_comparison_core`: the builds of the matrix, its manual edits, the accepted AI links, the series of adjacent
    # transitions with their sheet pairs, and the content-keyed results (`CMP-SEAL-C1`).
    "comparison_matrix",
    "comparison_matrix_edit",
    "comparison_ai_link",
    "comparison_series",
    "comparison_transition",
    "comparison_sheet_pair_result",
    "comparison_sheet_pair",
    # `0040_comparison_ai_reports`: the consented AI jobs, the content-keyed pair-check answers and sheet descriptions, the
    # questions and sheet items, the specification extractions and comparisons, the reports with their parts and files,
    # and the launch queue with its entries (`CMP-SEAL-C2`).
    "comparison_ai_job",
    "comparison_ai_pair_answer",
    "comparison_ai_pair_question",
    "comparison_sheet_description",
    "comparison_ai_sheet_item",
    "comparison_spec_extraction",
    "comparison_spec_comparison",
    "comparison_report",
    "comparison_report_part",
    "comparison_report_artifact",
    "comparison_launch_queue",
    "comparison_launch_entry",
    # `0041_comparison_stage_core`: resumable stage intake, pairs, link revisions,
    # immutable text evidence and pinned seven-step runs (`CMP-SEAL-C3`).
    "stage_upload", "stage_upload_file", "stage_upload_part", "stage_upload_candidate",
    "stage_assembly", "stage_assembly_member", "stage_pair", "stage_link_revision",
    "stage_link_item", "stage_text_fragment", "stage_text_exclusion",
    "stage_text_difference", "stage_text_hint", "stage_chain_run", "stage_chain_step",
    # `0042_comparison_stage_review` (`CMP-SEAL-C4`): the stage AI's units and answers, graphic evidence, link
    # repairs, expert change cards with their evidence and verdicts, and the durable batch of runs with its items.
    "stage_ai_unit", "stage_ai_review", "stage_ai_classification", "stage_ai_synthesis",
    "stage_graphic_evidence", "stage_link_repair", "stage_link_repair_event", "stage_change_card",
    "stage_card_evidence", "stage_card_verdict", "stage_chain_batch", "stage_chain_batch_item",
    # `0019_execution_workers`: the worker registry.
    "worker",
    # `0053_document_tags` and `0054_finding_execution_status` (this list lacked them).
    "document_tag",
    "finding_execution_status",
    # `0055_work_schedule` (`UI-PARITY-P0P`): the five journals of «График работ» (this list lacked them).
    "engineer_absence_event",
    "schedule_plan_event",
    "schedule_setting_event",
    "work_assignment_schedule_event",
    "work_calendar_event",
    # `0059_decision_memory` (`ADR-0027`): the eight tables of the decision memory.
    "decision_memory_case",
    "decision_memory_content",
    "decision_memory_crop",
    "decision_memory_decision",
    "decision_memory_decision_text",
    "decision_memory_evidence",
    "decision_memory_norm_ref",
    "decision_memory_status_event",
    # `0061_decision_memory_m2`: the installation settings' journal of the decision memory.
    "decision_memory_setting_event",
    # `0062_hosts_stage_models` (`HOSTS-SEAL-1`): a server with its two journals, its latest report and the cooldown of a model on it; the
    # layout of models over the analysis stages with its revisions and switch; the cell-by-cell binding of a planned run.
    "executor_host",
    "executor_host_use_event",
    "executor_host_slot_event",
    "executor_host_report",
    "executor_model_cooldown",
    "stage_layout",
    "stage_layout_revision",
    "stage_layout_switch_event",
    "audit_run_cell_binding",
    # `0064_precedents_seal` (`CRIT-SEAL-50`): the memory's comments, block evidence, encoder queue and vectors; the probe of a run's candidate text, the
    # pass of a run and its advice; a finding's block evidence; the settings journal; the vectors' control and its journal; the journal of reference
    # data handed to an agent.
    "decision_memory_comment",
    "decision_memory_block_evidence",
    "decision_memory_embedding_intent",
    "decision_memory_embedding",
    "decision_memory_probe",
    "decision_memory_precedent_run",
    "decision_memory_precedent_advice",
    "finding_block_evidence",
    "precedent_setting_event",
    "vector_control",
    "vector_control_event",
    "executor_task_context_delivery",
    # `0020_norms_search`: the one current norms snapshot and its append-only history.
    "norm_current_snapshot",
    "norm_current_snapshot_event",
    "analysis_artifact_publication",
    "attempt",
    "audit_event",
    "audit_run",
    "blob",
    "command_record",
    "contract_state_transition",
    "document",
    "document_version",
    "expert_decision_event",
    "norm_chunk",
    "norm_chunk_build",
    "norm_document",
    "norm_embedding",
    "norm_embedding_build",
    "norm_embedding_profile",
    "norm_paragraph",
    "norms_snapshot",
    "finding",
    "finding_evidence",
    "finding_observation",
    "input_manifest_entry",
    "job",
    "lease",
    "model_call",
    "provider_call_effect",
    "project",
    "stage_result",
}

#: ``work_assignment_current`` (`0025_work_assignments`): each assignment's latest event and
#: current assignee, derived from the history. `0028_classification_corrections` adds the
#: classification's history (``version_classification_revision``) and its derived current
#: revision (``version_classification_current``).
EXPECTED_VIEWS = {
    "finding_current_verdict",
    "work_assignment_current",
    # `0030_executor_connections`: the latest route event of each kind of model work.
    "executor_route_current",
    "version_classification_revision",
    "version_classification_current",
    # `0061_decision_memory_m2`: a case's status from its latest event and its verdict from its latest decision.
    "decision_memory_case_current",
}

#: The alpha runner instantiates none of these aggregates. Their absence is a deliverable, so
#: it is asserted rather than assumed.
#: `W54-SEAL-01` removed ``worker`` (migration 0019 instantiates the registry under R-105).
#: ``outbox`` stays forbidden as a table name: the custody outbox is the admission row
#: itself (``norm_custody_admission``, R-76), never a generic outbox table.
FORBIDDEN_TABLES = {
    "import",
    "export",
    "export_request",
    "comparison",
    "outbox",
}


def _relnames(engine: Engine, relkind: str) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT c.relname FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relkind = :relkind"
            ),
            {"relkind": relkind},
        )
        return {row[0] for row in rows}


def test_the_database_is_empty_before_the_first_migration(
    empty_database: DatabaseSettings, empty_database_url: str
) -> None:
    """The premise of every other test in this file."""
    from auditmanager.shared.db.engine import create_database_engine

    engine = create_database_engine(empty_database)
    try:
        assert _relnames(engine, "r") == set()
    finally:
        engine.dispose()


def test_migration_applies_from_an_empty_database(
    empty_database_url: str, foundation_command, migrate_argv: list[str]
) -> None:
    result = foundation_command(migrate_argv, empty_database_url)
    assert result.returncode == 0, result.describe()


def test_clean_install_creates_exactly_the_declared_relations(
    migrated_engine: Engine,
) -> None:
    tables = _relnames(migrated_engine, "r")
    assert tables == EXPECTED_TABLES
    assert _relnames(migrated_engine, "v") == EXPECTED_VIEWS
    assert tables & FORBIDDEN_TABLES == set(), (
        "This head instantiates no Import, Export, Comparison or generic Outbox aggregate; "
        "a table for one remains a scope change, not an implementation detail."
    )


def test_clean_install_runs_against_postgresql_and_not_sqlite(
    migrated_engine: Engine,
) -> None:
    assert migrated_engine.dialect.name == "postgresql"
    assert migrated_engine.dialect.driver == "psycopg"
    with migrated_engine.connect() as connection:
        # A trigger-backed guard exists. SQLite has no such object, so this assertion
        # cannot pass anywhere the rest of the suite would be meaningless.
        count = connection.execute(
            text(
                "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE NOT t.tgisinternal AND c.relname = 'expert_decision_event'"
            )
        ).scalar_one()
    assert count >= 1


def test_the_head_is_single_and_the_history_is_linear() -> None:
    """Asserts the shape, not the enumeration.

    This test used to pin the exact revision list, so every migration broke it and the fix
    was to paste the new name in - which is not a linearity check, it is a transcription
    exercise that happens to fail. It now asserts what its own name says: the walk starts at
    the baseline, has no gaps or forks, and ends at the single declared head.
    """
    walk = revision_walk()
    assert walk, "the revision walk is empty"
    assert walk[0] == "0001_baseline", "the history does not start at the baseline"
    assert len(set(walk)) == len(walk), f"a revision appears twice: {walk}"
    assert head_revision() == walk[-1], (
        f"the declared head {head_revision()} is not the end of the walk {walk}"
    )
    assert len(walk) >= 2, "the walk is too short to have exercised the P02 head"


def test_stamped_revision_equals_the_declared_head(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        stamped = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    assert stamped == [head_revision()]


def test_rerunning_the_migration_at_head_is_safe(
    migrated_database: DatabaseSettings,
    migrated_engine: Engine,
    foundation_command,
    migrate_argv: list[str],
) -> None:
    """A second migration exits 0, changes no revision and changes no row."""
    url = migrated_database.url.render_as_string(hide_password=False)

    with migrated_engine.connect() as connection:
        before_revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        before_topology = connection.execute(
            text(
                "SELECT machine, from_state, to_state FROM contract_state_transition "
                "ORDER BY machine, from_state NULLS FIRST, to_state"
            )
        ).all()

    second = foundation_command(migrate_argv, url)
    assert second.returncode == 0, second.describe()
    third = foundation_command(migrate_argv, url)
    assert third.returncode == 0, third.describe()

    with migrated_engine.connect() as connection:
        after_revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        after_topology = connection.execute(
            text(
                "SELECT machine, from_state, to_state FROM contract_state_transition "
                "ORDER BY machine, from_state NULLS FIRST, to_state"
            )
        ).all()

    assert after_revision == before_revision
    assert after_topology == before_topology
    assert "Running upgrade" not in second.stdout + second.stderr


def test_check_db_reports_the_current_head(
    migrated_database: DatabaseSettings, foundation_command, check_db_argv: list[str]
) -> None:
    url = migrated_database.url.render_as_string(hide_password=False)
    result = foundation_command(check_db_argv, url)
    assert result.returncode == 0, result.describe()
    assert head_revision() in result.stdout
    assert result.last_output_line == SUCCESS_SENTINEL, (
        "FOUNDATION_LOCK.json requires the sentinel to be the last actual output "
        f"line. Got:\n{result.describe()}"
    )


def test_check_db_refuses_an_unmigrated_database(
    empty_database_url: str, foundation_command, check_db_argv: list[str]
) -> None:
    """The guard's proof that it can fail.

    A check that only ever reports success on a migrated database has not been shown
    to check anything. Here it is pointed at an empty one.
    """
    result = foundation_command(check_db_argv, empty_database_url)
    assert result.returncode != 0, result.describe()
    assert SUCCESS_SENTINEL not in result.stdout
    assert "migration revision" in result.stderr


@pytest.mark.parametrize(
    ("suffix", "expectation"),
    [
        ("no_such_database_a1", "could not connect"),
    ],
)
def test_check_db_refuses_an_unreachable_database(
    empty_database: DatabaseSettings,
    suffix: str,
    expectation: str,
    foundation_command,
    check_db_argv: list[str],
) -> None:
    unreachable = empty_database.url.set(database=suffix)
    result = foundation_command(
        check_db_argv, unreachable.render_as_string(hide_password=False)
    )
    assert result.returncode != 0, result.describe()
    assert SUCCESS_SENTINEL not in result.stdout
    assert expectation in result.stderr


# -- `EXEC2-SEAL-2`: migrations 0047 and 0048 (executor groups, rules, routing mode, dispatch-time binding) ---------------
#
# Written under `R-149d` and NOT RUN: no database was started for EXEC-2. Every test here needs PostgreSQL, like the
# rest of this directory (`conftest.py`: no SQLite fallback). They prove the failure cases of `EXEC2-SEAL-2`: a second write
# of the connection revision of work admitted by a group, and a write that is not the binding, are refused by the
# database; nothing existing is ever `pending`; a group is homogeneous and its history cannot be rewritten.

_SEAL2_ACTOR = f"usr_{'0' * 26}"


def _sqlstate_of(error: pytest.ExceptionInfo) -> str | None:
    return getattr(error.value.orig, "sqlstate", None)


def _group_revision(connection, group: str, *, revision_no: int, member_count: int, gateway_model: str = "anthropic/claude-opus-5") -> str:
    """A revision of `group` declaring `member_count` members; the members are the caller's to insert in the same transaction."""
    from auditmanager.shared.identity import ExecutorGroupRevisionId

    revision = str(ExecutorGroupRevisionId.new())
    connection.execute(text(
        "INSERT INTO executor_group_revision (group_revision_id, group_id, revision_no, pin_id, gateway_model, "
        "billing, input_per_mtok_usd, output_per_mtok_usd, member_count, created_by) "
        "VALUES (:r, :g, :no, 'claude-opus-5', :m, 'metered', 15.000000, 75.000000, :n, :a)"
    ), {"r": revision, "g": group, "no": revision_no, "m": gateway_model, "n": member_count, "a": _SEAL2_ACTOR})
    return revision


def _executor_group(connection, member_revision: str, member_connection: str, *, gateway_model: str = "anthropic/claude-opus-5") -> tuple[str, str]:
    """A group and its first revision with one member (declared as one), for a connection revision pinning `claude-opus-5`, metered."""
    from auditmanager.shared.identity import ExecutorGroupId

    group = str(ExecutorGroupId.new())
    connection.execute(text(
        "INSERT INTO executor_group (group_id, display_name, created_by) VALUES (:g, :n, :a)"
    ), {"g": group, "n": f"group-{group[-6:]}", "a": _SEAL2_ACTOR})
    revision = _group_revision(connection, group, revision_no=1, member_count=1, gateway_model=gateway_model)
    connection.execute(text(
        "INSERT INTO executor_group_member (group_revision_id, connection_id, connection_revision_id, tie_break_order) "
        "VALUES (:r, :c, :cr, 1)"
    ), {"r": revision, "c": member_connection, "cr": member_revision})
    return group, revision


def _pending_run(connection, group_revision: str) -> str:
    """A run admitted on a group revision: `pending`, no connection revision."""
    from auditmanager.shared.identity import (
        AnalysisProfileId, DocumentUid, ProjectUid, PromptBundleId, RunId, VersionUid,
    )

    ids = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()),
           "version": str(VersionUid.new()), "run": str(RunId.new())}
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:project, 'seal2')"), ids)
    connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                            "VALUES (:document, :project, 'seal2')"), ids)
    connection.execute(text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
                            "byte_size, sha256, page_count) VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"),
                       {**ids, "sha": "a" * 64})
    connection.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, prompt_bundle_id, provider_mode, "
        "frozen_input_digest, binding_state, executor_group_revision_id) "
        "VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest, 'pending', :g)"
    ), {**ids, "profile": str(AnalysisProfileId.new()), "bundle": str(PromptBundleId.new()),
        "digest": "b" * 64, "g": group_revision})
    return ids["run"]


def test_the_binding_columns_default_to_frozen_at_start_so_nothing_existing_is_pending(migrated_engine: Engine) -> None:
    """Every existing row takes the column default, and the default is the only way an old writer's INSERT lands."""
    with migrated_engine.connect() as connection:
        for table in ("audit_run", "comparison_ai_job"):
            row = connection.execute(text(
                "SELECT column_default, is_nullable FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t AND column_name = 'binding_state'"
            ), {"t": table}).one()
            assert row.column_default is not None and "frozen_at_start" in row.column_default, (table, row)
            assert row.is_nullable == "NO", table
            for column in ("executor_group_revision_id", "routing_rule_revision_id", "wait_reason", "waiting_since"):
                nullable = connection.execute(text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
                ), {"t": table, "c": column}).scalar_one()
                assert nullable == "YES", (table, column)
        assert connection.execute(text(
            "SELECT is_nullable FROM information_schema.columns WHERE table_schema = 'public' "
            "AND table_name = 'comparison_ai_job' AND column_name = 'connection_revision_id'"
        )).scalar_one() == "YES"
        tying = connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_comparison_ai_job_pending_has_no_revision'"
        )).scalar_one()
        assert "connection_revision_id IS NULL" in tying and "pending" in tying, tying
        assert connection.execute(text("SELECT count(*) FROM audit_run WHERE binding_state <> 'frozen_at_start'")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM comparison_ai_job WHERE binding_state <> 'frozen_at_start'")).scalar_one() == 0
        frozen = connection.execute(text(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trg_audit_run_frozen_guard'"
        )).scalar_one()
        for column in ("connection_revision_id", "executor_group_revision_id", "routing_rule_revision_id", "preset_revision_id"):
            assert f"'{column}'" in frozen, frozen


def test_a_pending_run_is_bound_once_and_every_other_write_of_its_connection_is_refused(migrated_engine: Engine) -> None:
    """ADR-0026 decision 12: NULL -> value exactly once, with `pending` -> `bound`; nothing else moves."""
    from sqlalchemy.exc import DBAPIError
    from tests.integration.db.test_executor_connections_migration import _connection, _revision

    with migrated_engine.begin() as connection:
        first, second = _connection(connection), _connection(connection)
        first_revision, second_revision = _revision(connection, first), _revision(connection, second)
        _, group_revision = _executor_group(connection, first_revision, first)
        pending, other = _pending_run(connection, group_revision), _pending_run(connection, group_revision)

    def refused(statement: str, sqlstate: str, **parameters: str) -> None:
        with migrated_engine.connect() as connection:
            transaction = connection.begin()
            with pytest.raises(DBAPIError) as error:
                connection.execute(text(statement), parameters)
            transaction.rollback()
        assert _sqlstate_of(error) == sqlstate, (statement, _sqlstate_of(error))

    # a connection revision written while the run stays pending is not a binding
    refused("UPDATE audit_run SET connection_revision_id = :c WHERE run_id = :r", "AM003", c=first_revision, r=pending)
    # a binding that names no connection violates the shape the row must have
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DBAPIError):
            connection.execute(text("UPDATE audit_run SET binding_state = 'bound' WHERE run_id = :r"), {"r": pending})
        transaction.rollback()
    # the states move pending -> bound only
    refused("UPDATE audit_run SET binding_state = 'frozen_at_start' WHERE run_id = :r", "AM001", r=pending)
    # a binding names a member of the run's group revision: a real connection revision that is no member is refused
    refused(
        "UPDATE audit_run SET binding_state = 'bound', connection_revision_id = :c WHERE run_id = :r",
        "AM001", c=second_revision, r=pending)

    with migrated_engine.begin() as connection:
        connection.execute(text(
            "UPDATE audit_run SET binding_state = 'bound', connection_revision_id = :c WHERE run_id = :r"
        ), {"c": first_revision, "r": pending})

    # a second write, a different value, a return to NULL, and a return to `pending`: all refused
    refused("UPDATE audit_run SET connection_revision_id = :c WHERE run_id = :r", "AM003", c=second_revision, r=pending)
    refused("UPDATE audit_run SET connection_revision_id = NULL WHERE run_id = :r", "AM003", r=pending)
    refused("UPDATE audit_run SET binding_state = 'pending' WHERE run_id = :r", "AM001", r=pending)
    # the admission columns are frozen with the rest
    refused("UPDATE audit_run SET executor_group_revision_id = NULL WHERE run_id = :r", "AM003", r=other)
    with migrated_engine.connect() as connection:
        row = connection.execute(text(
            "SELECT binding_state, connection_revision_id FROM audit_run WHERE run_id = :r"
        ), {"r": pending}).one()
    assert (row.binding_state, row.connection_revision_id) == ("bound", first_revision)


def test_a_group_is_homogeneous_its_history_is_immutable_and_a_rule_names_an_active_group(migrated_engine: Engine) -> None:
    from sqlalchemy.exc import DBAPIError
    from auditmanager.shared.identity import (
        ExecutorConnectionRevisionId, ExecutorGroupRevisionId, ExecutorRoutingRuleRevisionId,
    )
    from tests.integration.db.test_executor_connections_migration import _connection, _revision

    with migrated_engine.begin() as connection:
        member, stranger = _connection(connection), _connection(connection)
        member_revision = _revision(connection, member)
        stranger_revision = str(ExecutorConnectionRevisionId.new())
        connection.execute(text(
            "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, pin_id, "
            "gateway_model, billing, allow_client_documents, timeout_seconds, api_flavour, base_url, transport) "
            "VALUES (:id, :c, 1, :a, 'claude-sonnet-5', 'anthropic/claude-sonnet-5', 'metered', false, 60, "
            "'openai_chat', 'https://proxy.test', 'direct')"
        ), {"id": stranger_revision, "c": stranger, "a": _SEAL2_ACTOR})
        group, revision = _executor_group(connection, member_revision, member)

    def refused(statement: str, **parameters: str) -> str | None:
        with migrated_engine.connect() as connection:
            transaction = connection.begin()
            with pytest.raises(DBAPIError) as error:
                connection.execute(text(statement), parameters)
            transaction.rollback()
        return _sqlstate_of(error)

    # a member that pins another model than the group revision is refused; a revision and a member cannot be rewritten
    assert refused(
        "INSERT INTO executor_group_member (group_revision_id, connection_id, connection_revision_id) VALUES (:r, :c, :cr)",
        r=revision, c=stranger, cr=stranger_revision) == "AM001"
    assert refused("UPDATE executor_group_revision SET pin_id = 'other' WHERE group_revision_id = :r", r=revision) == "AM003"
    assert refused("DELETE FROM executor_group_member WHERE group_revision_id = :r", r=revision) == "AM003"
    # a revision is numbered without a gap
    assert refused(
        "INSERT INTO executor_group_revision (group_revision_id, group_id, revision_no, pin_id, gateway_model, billing, "
        "input_per_mtok_usd, output_per_mtok_usd, member_count, created_by) VALUES (:id, :g, 3, 'claude-opus-5', "
        "'anthropic/claude-opus-5', 'metered', 15, 75, 1, :a)",
        id=str(ExecutorGroupRevisionId.new()), g=group, a=_SEAL2_ACTOR) == "AM001"

    rule = str(ExecutorRoutingRuleRevisionId.new())
    with migrated_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO executor_routing_rule_revision (rule_revision_id, work_kind, rule_no, group_revision_id, set_by) "
            "VALUES (:id, 'text_analysis', 1, :r, :a)"
        ), {"id": rule, "r": revision, "a": _SEAL2_ACTOR})
    assert refused("UPDATE executor_routing_rule_revision SET rule_no = 2 WHERE rule_revision_id = :id", id=rule) == "AM002"

    # archiving is one-way, and an archived group takes no rule
    with migrated_engine.begin() as connection:
        connection.execute(text("UPDATE executor_group SET archived_at = now(), archived_by = :a WHERE group_id = :g"),
                           {"a": _SEAL2_ACTOR, "g": group})
    assert refused("UPDATE executor_group SET archived_at = NULL, archived_by = NULL WHERE group_id = :g", g=group) == "AM003"
    assert refused(
        "INSERT INTO executor_routing_rule_revision (rule_revision_id, work_kind, rule_no, group_revision_id, set_by) "
        "VALUES (:id, 'text_analysis', 2, :r, :a)",
        id=str(ExecutorRoutingRuleRevisionId.new()), r=revision, a=_SEAL2_ACTOR) == "AM001"


def _refused(engine: Engine, statement: str, **parameters: object) -> pytest.ExceptionInfo:
    """Run one statement that the database must refuse, in a transaction that is rolled back."""
    from sqlalchemy.exc import DBAPIError

    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DBAPIError) as error:
            connection.execute(text(statement), parameters)
        transaction.rollback()
    return error


_MEMBER_INSERT = (
    "INSERT INTO executor_group_member (group_revision_id, connection_id, connection_revision_id) VALUES (:r, :c, :cr)"
)


def test_a_group_revision_commits_with_exactly_the_members_it_declares_and_takes_none_afterwards(
    migrated_engine: Engine,
) -> None:
    """Row immutability alone left INSERT open. The revision declares `member_count`: a member beyond it is refused at
    once, a revision that holds fewer cannot commit, and one that holds exactly what it declared does."""
    from sqlalchemy.exc import DBAPIError
    from tests.integration.db.test_executor_connections_migration import _connection, _revision

    with migrated_engine.begin() as connection:
        member, extra = _connection(connection), _connection(connection)
        member_revision, extra_revision = _revision(connection, member), _revision(connection, extra)
        group, revision = _executor_group(connection, member_revision, member)   # declares one, holds one: commits
        deferred = connection.execute(text(
            "SELECT tgdeferrable AND tginitdeferred FROM pg_trigger WHERE tgname = 'trg_executor_group_revision_has_members'"
        )).scalar_one()
    assert deferred is True, "the count is checked at commit, so the members can follow the revision in one transaction"

    # a later INSERT into the committed revision is refused although the member would fit the group (same pin, model and
    # billing): only the closed membership refuses it
    later = _refused(migrated_engine, _MEMBER_INSERT, r=revision, c=extra, cr=extra_revision)
    assert _sqlstate_of(later) == "AM001" and "declared members" in str(later.value)

    # inside the creating transaction too: the second member of a revision that declared one is refused
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        one = _group_revision(connection, group, revision_no=2, member_count=1)
        connection.execute(text(_MEMBER_INSERT), {"r": one, "c": member, "cr": member_revision})
        with pytest.raises(DBAPIError) as over:
            connection.execute(text(_MEMBER_INSERT), {"r": one, "c": extra, "cr": extra_revision})
        transaction.rollback()
    assert _sqlstate_of(over) == "AM001"

    # a revision that declares two and brings one cannot commit: the refusal is the COMMIT's and nothing is left behind
    with pytest.raises(DBAPIError) as short:
        with migrated_engine.begin() as connection:
            fewer = _group_revision(connection, group, revision_no=2, member_count=2)
            connection.execute(text(_MEMBER_INSERT), {"r": fewer, "c": member, "cr": member_revision})
    assert _sqlstate_of(short) == "AM001" and "declares 2 members and holds 1" in str(short.value)
    with migrated_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT count(*) FROM executor_group_revision WHERE group_id = :g"), {"g": group}).scalar_one() == 1

    # control: the same revision with the two members it declares commits
    with migrated_engine.begin() as connection:
        full = _group_revision(connection, group, revision_no=2, member_count=2)
        connection.execute(text(_MEMBER_INSERT), {"r": full, "c": member, "cr": member_revision})
        connection.execute(text(_MEMBER_INSERT), {"r": full, "c": extra, "cr": extra_revision})
    with migrated_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT count(*) FROM executor_group_member WHERE group_revision_id = :r"), {"r": full}).scalar_one() == 2

    # a revision declares one to sixteen members
    for declared in (0, 17):
        with migrated_engine.connect() as connection:
            transaction = connection.begin()
            with pytest.raises(DBAPIError) as range_error:
                _group_revision(connection, group, revision_no=3, member_count=declared)
            transaction.rollback()
        assert _sqlstate_of(range_error) == "23514", declared


def test_a_group_is_never_deleted_and_the_routing_mode_journal_is_numbered_without_a_gap(migrated_engine: Engine) -> None:
    import json

    from auditmanager.shared.identity import ExecutorGroupId, ExecutorRoutingModeEventId

    group = str(ExecutorGroupId.new())
    with migrated_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO executor_group (group_id, display_name, created_by) VALUES (:g, 'never deleted', :a)"
        ), {"g": group, "a": _SEAL2_ACTOR})
    assert _sqlstate_of(_refused(migrated_engine, "DELETE FROM executor_group WHERE group_id = :g", g=group)) == "AM003"
    with migrated_engine.connect() as connection:   # archiving is the way out, and it is not a deletion
        assert connection.execute(text("SELECT count(*) FROM executor_group WHERE group_id = :g"), {"g": group}).scalar_one() == 1

    event = (
        "INSERT INTO executor_routing_mode_event (mode_event_id, event_no, mode, preview_digest, mapping, changed_by) "
        "VALUES (:id, :no, :mode, :digest, CAST(:mapping AS jsonb), :a)"
    )

    def parameters(number: int, mode: str) -> dict[str, object]:
        return {"id": str(ExecutorRoutingModeEventId.new()), "no": number, "mode": mode, "a": _SEAL2_ACTOR,
                "digest": "a" * 64 if mode == "rules" else None,
                "mapping": json.dumps([{"work_kind": "text_analysis"}] if mode == "rules" else [])}

    # the journal starts at 1, and a number that is taken or that skips one is refused by the trigger (not only by the key)
    assert _sqlstate_of(_refused(migrated_engine, event, **parameters(2, "rules"))) == "AM001"
    with migrated_engine.begin() as connection:
        connection.execute(text(event), parameters(1, "rules"))
    assert _sqlstate_of(_refused(migrated_engine, event, **parameters(1, "legacy"))) == "AM001"
    assert _sqlstate_of(_refused(migrated_engine, event, **parameters(3, "legacy"))) == "AM001"
    with migrated_engine.begin() as connection:
        connection.execute(text(event), parameters(2, "legacy"))
    with migrated_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT array_agg(event_no ORDER BY event_no) FROM executor_routing_mode_event")).scalar_one() == [1, 2]


@pytest.mark.parametrize("function", [
    "am_check_executor_group_revision", "am_check_executor_group_member", "am_check_executor_routing_rule",
])
def test_the_insert_triggers_read_the_archive_they_decide_on_with_a_share_lock(migrated_engine: Engine, function: str) -> None:
    """Archiving locks the group row `FOR UPDATE` (the connection row is updated); a plain SELECT would let an archive and a
    concurrent revision, rule or member insert both pass, so each trigger reads the row it decides on `FOR SHARE`."""
    with migrated_engine.connect() as connection:
        body = connection.execute(text(
            "SELECT pg_get_functiondef(p.oid) FROM pg_proc p WHERE p.proname = :f"), {"f": function}).scalar_one()
    assert "FOR SHARE" in body, function
