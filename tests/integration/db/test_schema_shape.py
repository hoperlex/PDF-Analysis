"""Column- and trigger-level claims, asserted against the live database.

These belong here rather than in the contract suite. Grepping the migration source
for a column name also matches the comment that explains why the column is absent,
so such a test ends up proving that a docstring exists. ``information_schema`` and
``pg_trigger`` describe what was actually created.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

#: Names that would turn an address or a presentation value into a de facto key.
BANNED_COLUMN_NAMES = {
    "bucket",
    "bucket_name",
    "object_key",
    "s3_key",
    "storage_key",
    "storage_path",
    "file_path",
    "filesystem_path",
    "directory",
    "url",
    "presigned_url",
    "download_url",
    "password",
    "secret",
    "credential",
    "api_key",
    "token",
    "execution_token",
    "fencing_token",
    "authority_token",
    "prompt",
    "prompt_text",
    "raw_response",
    "response_body",
}

APPEND_ONLY_TABLES = {"expert_decision_event", "audit_event"}

IMMUTABLE_TABLES = {
    "document_version",
    "input_manifest_entry",
    "finding_observation",
    "finding_evidence",
    "model_call",
    "contract_state_transition",
}


def _columns(engine: Engine) -> list[tuple[str, str]]:
    with engine.connect() as connection:
        return [
            (row[0], row[1])
            for row in connection.execute(
                text(
                    "SELECT table_name, column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public'"
                )
            )
        ]


def _trigger_functions(engine: Engine, table: str) -> set[str]:
    with engine.connect() as connection:
        return {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT p.proname FROM pg_trigger t "
                    "JOIN pg_class c ON c.oid = t.tgrelid "
                    "JOIN pg_proc p ON p.oid = t.tgfoid "
                    "WHERE NOT t.tgisinternal AND c.relname = :table"
                ),
                {"table": table},
            )
        }


def test_no_column_names_an_address_a_secret_or_a_model_payload(
    migrated_engine: Engine,
) -> None:
    offenders = [
        f"{table}.{column}"
        for table, column in _columns(migrated_engine)
        if column in BANNED_COLUMN_NAMES
    ]
    assert offenders == [], (
        "the object-key layout is confined to the S3 adapter and secrets are stored "
        f"nowhere; found {offenders}"
    )


def test_the_columns_that_are_not_identities_exist_and_are_referenced_by_nothing(
    migrated_engine: Engine,
) -> None:
    """A path, a file name, an ordinal and a checksum may be columns - never keys."""
    columns = set(_columns(migrated_engine))
    for expected in (
        ("document_version", "source_filename"),
        ("document_version", "version_ordinal"),
        ("blob", "sha256"),
        ("expert_decision_event", "sequence_no"),
    ):
        assert expected in columns, f"{expected} is missing"

    with migrated_engine.connect() as connection:
        referencing = connection.execute(
            text(
                "SELECT c.conname, a.attname FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.confrelid "
                "JOIN unnest(c.confkey) AS k(attnum) ON TRUE "
                "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum "
                "WHERE c.contype = 'f'"
            )
        ).all()
    referenced_columns = {row[1] for row in referencing}
    for non_identity in ("source_filename", "version_ordinal", "sha256", "sequence_no"):
        assert non_identity not in referenced_columns, (
            f"{non_identity} is the target of a foreign key; the contract lists it "
            "among the non-identities"
        )


def test_exactly_the_declared_tables_are_append_only(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r'"
                )
            )
        }
    with_append_only = {
        table for table in tables if "am_append_only" in _trigger_functions(migrated_engine, table)
    }
    assert with_append_only == APPEND_ONLY_TABLES


def test_exactly_the_declared_tables_are_immutable(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r'"
                )
            )
        }
    with_immutability = {
        table
        for table in tables
        if "am_immutable_row" in _trigger_functions(migrated_engine, table)
    }
    assert with_immutability == IMMUTABLE_TABLES


def test_every_state_column_carries_the_transition_guard(migrated_engine: Engine) -> None:
    for table in ("audit_run", "blob", "command_record"):
        assert "am_guard_state_transition" in _trigger_functions(migrated_engine, table), (
            f"{table} has a state column with no transition guard"
        )


#: Columns whose name ends in ``_id`` but which are not contract identities.
#: ``sequence_no`` is a server row order, ``aggregate_id`` holds any prefix by design,
#: ``correlation_id`` is declared ``is_entity_identity: false``, ``block_id`` and
#: ``section_id`` are anchors inside one artifact, and ``stage_id`` is a registry name.
NON_CONTRACT_IDENTITY_COLUMNS = {
    "aggregate_id",
    "block_id",
    "correlation_id",
    "section_id",
    "sequence_no",
    "stage_id",
}


def test_every_identity_column_carries_a_format_check(migrated_engine: Engine) -> None:
    """A CHECK per identity column, so raw SQL cannot bypass the value type.

    Matched on the constraint *definition*, not its name: a constraint named
    ``..._format`` that checks nothing would pass a name-based test.
    """
    from auditmanager.shared.identity import IDENTITY_TYPES_BY_ENTITY, pattern_for

    prefix_by_column = {
        "project_uid": "prj",
        "document_uid": "doc",
        "current_version_uid": "ver",
        "version_uid": "ver",
        "blob_id": "blob",
        "run_id": "run",
        "allocated_by_run_id": "run",
        "command_id": "cmd",
        "analysis_profile_id": "ap",
        "prompt_bundle_id": "pb",
        "norms_snapshot_id": "ns",
        "model_call_id": "mc",
        "finding_uid": "fnd",
        "finding_observation_id": "fobs",
        "decision_id": "dec",
        "audit_event_id": "evt",
    }
    assert set(prefix_by_column.values()) <= {
        identity.prefix for identity in IDENTITY_TYPES_BY_ENTITY.values()
    }

    with migrated_engine.connect() as connection:
        base_tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r'"
                )
            )
        }
        definitions: dict[str, list[str]] = {}
        for table, definition in connection.execute(
            text(
                "SELECT t.relname, pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "JOIN pg_namespace n ON n.oid = t.relnamespace "
                "WHERE n.nspname = 'public' AND c.contype = 'c'"
            )
        ):
            definitions.setdefault(table, []).append(definition)

    identity_columns = [
        (table, column)
        for table, column in _columns(migrated_engine)
        if table in base_tables
        and column.endswith(("_uid", "_id"))
        and column not in NON_CONTRACT_IDENTITY_COLUMNS
    ]
    assert len(identity_columns) >= 20, "the identity-column query found too few columns"

    missing = []
    for table, column in identity_columns:
        prefix = prefix_by_column.get(column)
        assert prefix is not None, f"{table}.{column} has no declared prefix in this test"
        needle = pattern_for(prefix)
        if not any(
            column in definition and needle in definition
            for definition in definitions.get(table, [])
        ):
            missing.append(f"{table}.{column} (expects {needle})")
    assert missing == [], f"identity columns with no contract-pattern CHECK: {sorted(missing)}"


def test_the_current_verdict_view_reads_only_the_ledger(migrated_engine: Engine) -> None:
    """The projection must be rebuildable, so it may not read a cached column."""
    with migrated_engine.connect() as connection:
        definition = connection.execute(
            text("SELECT pg_get_viewdef('finding_current_verdict'::regclass, true)")
        ).scalar_one()
    assert "expert_decision_event" in definition
    assert "finding" in definition
    for cached in ("current_verdict_cache", "verdict_projection", "materialized"):
        assert cached not in definition
