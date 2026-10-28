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
    # `0032_ar_v3_run_group`: a group of six runs of one version, and its six members.
    "ar_v3_run_group",
    "ar_v3_run_group_member",
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
    # `0019_execution_workers`: the worker registry.
    "worker",
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
