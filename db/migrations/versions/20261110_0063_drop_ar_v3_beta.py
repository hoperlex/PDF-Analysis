"""0063 -- the six-scope АР beta is dropped (`AR-V3-BE-RM-01`, owner rulings `R-154a` and `R-154c`; contract 1.50.0).

Revision ID: 0063_drop_ar_v3_beta
Revises: 0062_hosts_stage_models

The beta was added by three revisions and this one takes all three back:

``0032_ar_v3_run_group``
    The tables ``ar_v3_run_group`` and ``ar_v3_run_group_member`` with the triggers ``trg_ar_v3_run_group_frozen`` and
    ``trg_ar_v3_run_group_member_frozen`` (``am_immutable_row``), the function ``am_ar_v3_group_complete()`` and the deferred constraint
    trigger ``trg_ar_v3_group_complete``. All of it is dropped: the member table first (it references the group), the group, then the function.
``0033_ar_v3_cite_stage_id``
    ``stage_result.ck_stage_result_stage_id`` admitted the beta's tenth stage id. It is restored to the nine ids of ``0002``.
``0036_cite_partition_v3``
    ``am_verify_norm_citation_partition()`` admitted the beta's CITE stage beside ``norm_verification``. It is restored to ``0023``'s body,
    in which the stage test reads ``st.stage_id = 'norm_verification'``; its two triggers keep their names and are not touched.

What the upgrade refuses
------------------------
It refuses, naming every count, while any of the beta's rows exists, because dropping the tables or narrowing the CHECK would otherwise
destroy or orphan them: a row of either table; a run pinned to the beta's profile and prompt bundle; a finding observation of that
profile; a ``stage_result`` named ``ar_v3_citation_review``; a command record of the type ``start_ar_v3_beta_group``; a job of such a run;
and a model call or provider effect whose ``parameters`` carry a key that starts with ``ar_v3_``. The operator's purge removes them first
(``scripts/recovery``); nothing here deletes a row.

Downgrade
---------
Recreates the previous head exactly -- the two tables, their triggers, the function and the constraint trigger of ``0032`` in ``0032``'s
order, the ten-id CHECK of ``0033`` and the function of ``0036`` -- so that a schema digest taken at ``0062`` equals the one taken after
``0063`` up and down (``tests/integration/db/test_ar_v3_beta_drop_migration.py``). The vocabulary is restated here and not imported: a
migration is history and must not move when the application does.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0063_drop_ar_v3_beta"
down_revision: str | None = "0062_hosts_stage_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: The beta's sealed profile and prompt-bundle pair (``analysis/profiles/ar_v3/v3_profile.py`` at ``0062``).
_PROFILE_ID = "ap_01M5M28ZCDD8VPSP1BTAEW92YE"
_BUNDLE_ID = "pb_01M5M28ZCDVCR37BX1884JGSPM"
_CITE_STAGE_ID = "ar_v3_citation_review"
_COMMAND_TYPE = "start_ar_v3_beta_group"

#: The nine stages of the analysis registry that ``0002`` admitted.
_REGISTRY_STAGE_IDS = (
    "source_preparation",
    "page_geometry_extraction",
    "document_context_build",
    "text_analysis",
    "block_analysis",
    "finding_merge",
    "finding_review",
    "finding_correction",
    "norm_verification",
)
_WITH_CITE_STAGE_IDS = (*_REGISTRY_STAGE_IDS, _CITE_STAGE_ID)

#: What the beta left behind, as (label, SQL counting it). The two tables are counted last and only while they exist.
_MARKERS = (
    ("audit_run of the beta's profile and bundle",
     "SELECT count(*) FROM audit_run WHERE analysis_profile_id = :profile AND prompt_bundle_id = :bundle"),
    ("finding_observation of the beta's profile",
     "SELECT count(*) FROM finding_observation WHERE analysis_profile_id = :profile"),
    ("job of a run of the beta",
     "SELECT count(*) FROM job j JOIN audit_run r ON r.run_id = j.run_id "
     "WHERE r.analysis_profile_id = :profile AND r.prompt_bundle_id = :bundle"),
    ("stage_result named ar_v3_citation_review",
     "SELECT count(*) FROM stage_result WHERE stage_id = :cite"),
    ("command_record of type start_ar_v3_beta_group",
     "SELECT count(*) FROM command_record WHERE command_type = :command"),
    ("model_call with an ar_v3_ parameter",
     "SELECT count(*) FROM model_call m WHERE EXISTS "
     "(SELECT 1 FROM jsonb_object_keys(m.parameters) AS key WHERE key LIKE 'ar\\_v3\\_%')"),
    ("provider_call_effect with an ar_v3_ parameter",
     "SELECT count(*) FROM provider_call_effect e WHERE EXISTS "
     "(SELECT 1 FROM jsonb_object_keys(e.parameters) AS key WHERE key LIKE 'ar\\_v3\\_%')"),
    ("ar_v3_run_group row", "SELECT count(*) FROM ar_v3_run_group"),
    ("ar_v3_run_group_member row", "SELECT count(*) FROM ar_v3_run_group_member"),
)


def _sql_values(values: tuple[str, ...]) -> str:
    """Quote only fixed, source-controlled enum literals, never database input."""
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


def _stage_check(values: tuple[str, ...]) -> None:
    op.execute(
        "ALTER TABLE stage_result "
        "DROP CONSTRAINT ck_stage_result_stage_id, "
        f"ADD CONSTRAINT ck_stage_result_stage_id CHECK (stage_id IN ({_sql_values(values)}))"
    )


# ``0023``'s function with the stage test as a parameter: ``0036`` widened exactly that line and this revision narrows it back.
_PARTITION_FUNCTION = """
        CREATE OR REPLACE FUNCTION am_verify_norm_citation_partition() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            observation_id text;
            observation_run text;
            certified_count integer;
            actual_count integer;
        BEGIN
            observation_id := NEW.finding_observation_id;
            SELECT run_id, norm_citation_count INTO observation_run, certified_count
              FROM finding_observation
             WHERE finding_observation_id = observation_id;
            SELECT count(*) INTO actual_count FROM finding_observation_norm_citation
             WHERE finding_observation_id = observation_id;
            IF (certified_count IS NULL AND actual_count <> 0)
               OR (certified_count IS NOT NULL AND certified_count <> actual_count) THEN
                RAISE EXCEPTION 'state_transition_not_allowed: citation partition count mismatch'
                    USING ERRCODE = 'AM001';
            END IF;
            IF certified_count IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM audit_run r
                JOIN norm_retrieval_set s
                  ON s.norm_retrieval_set_id = r.norm_retrieval_set_id
                 AND s.norms_snapshot_id = r.norms_snapshot_id
                 AND s.state = 'verified'
                JOIN stage_result st ON st.run_id = r.run_id
                 AND {STAGE_TEST} AND st.status = 'succeeded'
                WHERE r.run_id = observation_run
            ) THEN
                RAISE EXCEPTION 'state_transition_not_allowed: certified citation partition needs succeeded CITE stage and pinned verified set'
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NULL;
        END $fn$;
        """

#: ``0023``'s stage test, verbatim: the upgrade restores exactly this.
_STAGE_TEST_0023 = "st.stage_id = 'norm_verification'"
#: ``0036``'s test: the registry CITE stage or the beta's CITE stage. The downgrade restores exactly this.
_STAGE_TEST_0036 = "st.stage_id IN ('norm_verification', 'ar_v3_citation_review')"


def _partition_function(stage_test: str) -> str:
    return _PARTITION_FUNCTION.replace("{STAGE_TEST}", stage_test)


def _tables_exist(connection) -> bool:
    return bool(connection.execute(text("SELECT to_regclass('ar_v3_run_group') IS NOT NULL")).scalar_one())


def upgrade() -> None:
    connection = op.get_bind()
    params = {"profile": _PROFILE_ID, "bundle": _BUNDLE_ID, "cite": _CITE_STAGE_ID, "command": _COMMAND_TYPE}
    found = []
    for label, statement in _MARKERS:
        count = int(connection.execute(text(statement), params).scalar_one())
        if count:
            found.append(f"{count} {label}")
    if found:
        raise RuntimeError(
            "0063 upgrade refused: the six-scope АР beta still holds data (" + "; ".join(found) + "); "
            "remove it with the operator's purge first, nothing is deleted here"
        )
    op.execute("DROP TABLE ar_v3_run_group_member")
    op.execute("DROP TABLE ar_v3_run_group")
    op.execute("DROP FUNCTION am_ar_v3_group_complete()")
    _stage_check(_REGISTRY_STAGE_IDS)
    op.execute(_partition_function(_STAGE_TEST_0023))


def downgrade() -> None:
    # ``0032``: verbatim, in its order.
    op.execute(f"""
        CREATE TABLE ar_v3_run_group (
            group_id text PRIMARY KEY CHECK (group_id ~ '^arg_{ULID}$'),
            project_uid text NOT NULL REFERENCES project(project_uid)
                CHECK (project_uid ~ '^prj_{ULID}$'),
            version_uid text NOT NULL REFERENCES document_version(version_uid)
                CHECK (version_uid ~ '^ver_{ULID}$'),
            command_id text NOT NULL UNIQUE REFERENCES command_record(command_id)
                CHECK (command_id ~ '^cmd_{ULID}$'),
            norms_snapshot_id text NOT NULL REFERENCES norms_snapshot(norms_snapshot_id)
                CHECK (norms_snapshot_id ~ '^ns_{ULID}$'),
            analysis_profile_id text NOT NULL CHECK (analysis_profile_id ~ '^ap_{ULID}$'),
            prompt_bundle_id text NOT NULL CHECK (prompt_bundle_id ~ '^pb_{ULID}$'),
            pack_sha256 text NOT NULL CHECK (pack_sha256 ~ '^[0-9a-f]{{64}}$'),
            composition_sha256 text NOT NULL CHECK (composition_sha256 ~ '^[0-9a-f]{{64}}$'),
            policy_sha256 text NOT NULL CHECK (policy_sha256 ~ '^[0-9a-f]{{64}}$'),
            provider_mode text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute(f"""
        CREATE TABLE ar_v3_run_group_member (
            group_id text NOT NULL REFERENCES ar_v3_run_group(group_id)
                CHECK (group_id ~ '^arg_{ULID}$'),
            ordinal integer NOT NULL CHECK (ordinal BETWEEN 1 AND 6),
            scope_id text NOT NULL CHECK (scope_id IN ('F1','F2','A1','A2','S1','S2')),
            run_id text NOT NULL UNIQUE REFERENCES audit_run(run_id)
                CHECK (run_id ~ '^run_{ULID}$'),
            map_sha256 text NOT NULL CHECK (map_sha256 ~ '^[0-9a-f]{{64}}$'),
            norm_retrieval_set_id text NOT NULL REFERENCES norm_retrieval_set(norm_retrieval_set_id)
                CHECK (norm_retrieval_set_id ~ '^nrs_{ULID}$'),
            frozen_input_digest text NOT NULL CHECK (frozen_input_digest ~ '^[0-9a-f]{{64}}$'),
            PRIMARY KEY (group_id, ordinal),
            UNIQUE (group_id, scope_id),
            CHECK ((ordinal, scope_id) IN ((1,'F1'),(2,'F2'),(3,'A1'),(4,'A2'),(5,'S1'),(6,'S2')))
        )
    """)
    for table in ("ar_v3_run_group", "ar_v3_run_group_member"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_frozen BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
        )
    op.execute("""
        CREATE FUNCTION am_ar_v3_group_complete() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (SELECT count(*) FROM ar_v3_run_group_member WHERE group_id = NEW.group_id) <> 6 THEN
                RAISE EXCEPTION 'AR v3 group requires six members' USING ERRCODE = '23514';
            END IF;
            IF EXISTS (
                SELECT 1 FROM ar_v3_run_group_member m
                JOIN audit_run r ON r.run_id = m.run_id
                JOIN norm_retrieval_set s ON s.norm_retrieval_set_id = m.norm_retrieval_set_id
                WHERE m.group_id = NEW.group_id AND (
                    r.project_uid IS DISTINCT FROM NEW.project_uid
                    OR r.version_uid IS DISTINCT FROM NEW.version_uid
                    OR r.norms_snapshot_id IS DISTINCT FROM NEW.norms_snapshot_id
                    OR r.analysis_profile_id IS DISTINCT FROM NEW.analysis_profile_id
                    OR r.prompt_bundle_id IS DISTINCT FROM NEW.prompt_bundle_id
                    OR r.provider_mode IS DISTINCT FROM NEW.provider_mode
                    OR r.norm_retrieval_set_id IS DISTINCT FROM m.norm_retrieval_set_id
                    OR r.frozen_input_digest IS DISTINCT FROM m.frozen_input_digest
                    OR r.command_id IS DISTINCT FROM NEW.command_id
                    OR s.map_sha256 IS DISTINCT FROM m.map_sha256
                    OR s.norms_snapshot_id IS DISTINCT FROM NEW.norms_snapshot_id
                    OR s.state IS DISTINCT FROM 'verified'
                )
            ) THEN
                RAISE EXCEPTION 'AR v3 member pin mismatch' USING ERRCODE = '23514';
            END IF;
            RETURN NULL;
        END $$
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER trg_ar_v3_group_complete
        AFTER INSERT ON ar_v3_run_group DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION am_ar_v3_group_complete()
    """)
    # ``0033`` and ``0036``.
    _stage_check(_WITH_CITE_STAGE_IDS)
    op.execute(_partition_function(_STAGE_TEST_0036))
