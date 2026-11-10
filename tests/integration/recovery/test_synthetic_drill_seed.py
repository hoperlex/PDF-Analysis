"""The drill's realistic source dataset is written by the product's own surfaces and audits clean.

This is the positive case the recovery audits never met before `RECOVERY-REBASE-01`: every
earlier test ran them against empty tables or hand-built rows. Here a migrated clone and a
private bucket are filled by ``synthetic_drill_seed`` (classification and correction, a
published recorded run with findings and decisions, work assignments, price and vendor lists,
an optimisation pass with decisions), and both audits, the Blob-reference audit and the
restored-schema audit, must accept the result and see every Blob.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import boto3
import pytest
from botocore.client import Config
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.storage import S3StorageSettings, StorageError
from scripts.recovery import synthetic_drill_seed as seed
from scripts.recovery.blob_reference_audit import audit_blob_references
from scripts.recovery.schema_coverage import audit_restored_schema
from scripts.recovery.synthetic_drill_compare import probe_guards
from tests.integration.recovery.purge_seed import PRECHECK_EVENTS, precheck_clock

_LANE_NAMES = (
    "FOUNDATION_INSTANCE", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_PORT",
    "DATABASE_URL", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD", "S3_ENDPOINT_URL", "S3_API_PORT",
    "S3_CONSOLE_PORT", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
)


def _lane_env(tmp_path: Path, **override: str) -> Path:
    values = {
        "FOUNDATION_INSTANCE": "auditmanager-w58-synthetic-source-seed", "POSTGRES_DB": "d",
        "POSTGRES_USER": "u", "POSTGRES_PASSWORD": "p", "POSTGRES_PORT": "57582",
        "DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:57582/d", "MINIO_ROOT_USER": "k",
        "MINIO_ROOT_PASSWORD": "s", "S3_ENDPOINT_URL": "http://127.0.0.1:61583",
        "S3_API_PORT": "61583", "S3_CONSOLE_PORT": "61584", "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY_ID": "k", "S3_SECRET_ACCESS_KEY": "s", "S3_BUCKET": "b",
    }
    values.update(override)
    path = tmp_path / "lane.env"
    path.write_text("# a lane\n" + "".join(f"{name}={value}\n" for name, value in values.items()),
                    encoding="ascii")
    return path


def test_the_lane_env_is_data_and_must_be_loopback(tmp_path: Path) -> None:
    assert set(seed.load_env(_lane_env(tmp_path))) == set(_LANE_NAMES)
    for override in ({"DATABASE_URL": "postgresql+psycopg://u:p@db.example:5432/d"},
                     {"S3_ENDPOINT_URL": "http://s3.example:9000"}):
        with pytest.raises(seed.SeedRefused, match="loopback"):
            seed.load_env(_lane_env(tmp_path, **override))
    path = _lane_env(tmp_path)
    path.write_text(path.read_text() + "SURPRISE=1\n", encoding="ascii")
    with pytest.raises(seed.SeedRefused, match="unknown or repeated"):
        seed.load_env(path)


def test_the_seed_never_carries_a_provider_credential() -> None:
    assert "ANTHROPIC_API_KEY" not in os.environ and "AUDITMANAGER_PROVIDER_MODE" not in os.environ


@pytest.fixture
def empty_lane(
    migrated_database_factory: Callable[[], DatabaseSettings],
) -> Iterator[tuple[DatabaseSettings, dict[str, str]]]:
    try:
        base = S3StorageSettings.from_env()
    except StorageError as exc:
        pytest.fail(f"this test needs a real S3-compatible service: {exc}")
    raw = boto3.client(
        "s3", endpoint_url=base.endpoint_url, region_name=base.region,
        aws_access_key_id=base.access_key_id, aws_secret_access_key=base.secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    bucket = f"{base.bucket[:40]}-{secrets.token_hex(8)}"
    raw.create_bucket(Bucket=bucket)
    database = migrated_database_factory()
    values = {
        "DATABASE_URL": database.url.render_as_string(hide_password=False),
        "S3_ENDPOINT_URL": base.endpoint_url, "S3_REGION": base.region,
        "S3_ACCESS_KEY_ID": base.access_key_id, "S3_SECRET_ACCESS_KEY": base.secret_access_key,
        "S3_BUCKET": bucket,
    }
    try:
        yield database, values
    finally:
        for page in raw.get_paginator("list_objects_v2").paginate(Bucket=bucket):
            for item in page.get("Contents", []):
                raw.delete_object(Bucket=bucket, Key=item["Key"])
        raw.delete_bucket(Bucket=bucket)


@pytest.fixture
def seeded_lane(
    empty_lane: tuple[DatabaseSettings, dict[str, str]],
) -> tuple[dict[str, Any], DatabaseSettings, dict[str, str]]:
    database, values = empty_lane
    return seed.seed_source_lane(values), database, values


def test_the_seeded_lane_holds_the_realistic_dataset_and_both_audits_accept_it(
    seeded_lane: tuple[dict[str, Any], DatabaseSettings, dict[str, str]],
) -> None:
    summary, database, _ = seeded_lane
    assert summary["run_state"] == "published" and summary["findings"] >= 2
    engine = create_database_engine(database)
    try:
        with Session(engine) as session:
            schema = audit_restored_schema(session)
            references = audit_blob_references(session)
            roles = {row[0] for row in session.execute(
                text("SELECT blob_role FROM analysis_artifact_publication WHERE state = 'bound'"))}
            counts = {name: session.execute(text(f"SELECT count(*) FROM {name}")).scalar_one()
                      for name in ("project", "document_version", "document_version_classification",
                                   "document_version_classification_correction", "work_assignment",
                                   "work_assignment_event", "price_list_revision", "vendor_list_revision",
                                   "optimisation_pass", "optimisation_proposal_decision",
                                   "expert_decision_event")}
    finally:
        engine.dispose()
    # `EXEC-SEAL-01`: +5 executor tables; `EXEC-PULL-01` (0031): +2; `0032`: +2 (dropped again by `0063`);
    # `0035_comparison_records`: +2; `0037_analysis_presets`: +1.
    # `0041_comparison_stage_core`: fifteen project-reachable stage tables.
    # `0042_comparison_stage_review`: twelve more, nine of them immutable.
    # `0046_executor_capacity_enroll` (`EXEC2-SEAL-1`): `executor_enrollment`, `executor_agent_install`.
    # `0047_executor_groups_rules` (`EXEC2-SEAL-2`): the group store (five tables, none seeded); `0048` adds none.
    # `0053_document_tags`, `0054_finding_execution_status`, `0055_work_schedule`: seven more (129 -> 136).
    # `0059_decision_memory`: the eight append-only tables of the decision memory (136 -> 144); `0061_decision_memory_m2` adds the settings' journal (145); `0062_hosts_stage_models` nine more (154); `0063_drop_ar_v3_beta` drops the two of `0032` (152).
    assert schema.tables == 152 and schema.guarded_tables >= 29
    assert len(references.available_blobs) >= 5
    assert dict(references.source_counts)["price_list_revision"] == 2
    assert {"geometry_crop_image", "prepared_text_layer"} <= roles
    assert counts["project"] == 4 and counts["document_version"] == 4
    assert counts["document_version_classification_correction"] == 1
    assert counts["work_assignment_event"] >= 4 and counts["optimisation_pass"] == 1
    assert counts["optimisation_proposal_decision"] == 2 and counts["expert_decision_event"] == 3


def test_a_lane_that_already_holds_a_project_is_refused(
    seeded_lane: tuple[dict[str, Any], DatabaseSettings, dict[str, str]],
) -> None:
    _, _, values = seeded_lane
    with pytest.raises(seed.SeedRefused, match="already holds a project"):
        seed.seed_source_lane(values)


def test_the_precheck_journal_is_the_throttles_and_the_held_clock_is_what_pins_it(
    empty_lane: tuple[DatabaseSettings, dict[str, str]],
) -> None:
    """`D-327`: with the throttle's clock moving 2 s per reading the journal holds EVERY receipt.

    The purge and erase tests seed with the clock held still and count `PRECHECK_EVENTS` (3) events. This
    is the other end: the same pipeline on a clock that is always late for the once-a-second throttle writes
    `started`, a `checking` receipt for 0..N pages and `completed`, N + 3 events. That the two differ is what
    shows the held clock (and not a pipeline that stopped journalling) pins the count, and it fails if the
    executor ever reads another clock for the throttle.
    """
    database, values = empty_lane
    with precheck_clock(step=2.0):
        summary = seed.seed_source_lane(values)
    engine = create_database_engine(database)
    try:
        with engine.connect() as connection:
            events = sorted(connection.execute(text(
                "SELECT payload->>'phase', (payload->>'completed_pages')::int, (payload->>'total_pages')::int "
                "FROM audit_event WHERE event_type = 'stage.pdf_precheck' AND aggregate_id = :r"),
                {"r": summary["run_id"]}).all())
            pages = connection.execute(text(
                "SELECT v.page_count FROM audit_run r JOIN document_version v ON v.version_uid = r.version_uid "
                "WHERE r.run_id = :r"), {"r": summary["run_id"]}).scalar_one()
    finally:
        engine.dispose()
    assert pages >= 2, "one page would never be throttled: the contrast would prove nothing"
    assert events == sorted(
        [("started", 0, pages), ("completed", pages, pages)]
        + [("checking", done, pages) for done in range(pages + 1)])
    assert len(events) == pages + 3 > PRECHECK_EVENTS


_ADDED_AFTER_0023 = frozenset((
    "document_version_classification", "document_version_classification_correction",
    "work_assignment", "work_assignment_event",
    "price_list_revision", "price_list_position", "vendor_list_revision", "vendor_list_entry",
    "optimisation_pass", "optimisation_proposal", "optimisation_proposal_decision",
))


def test_the_guard_probe_is_refused_everywhere_and_notices_a_dead_or_narrowed_trigger(
    seeded_lane: tuple[dict[str, Any], DatabaseSettings, dict[str, str]],
) -> None:
    """On the seeded lane every table `0024`-`0028` added is populated, so the probe can bite."""
    _, database, _ = seeded_lane
    engine = create_database_engine(database)
    try:
        def counts() -> dict[str, int]:
            with engine.connect() as connection:
                return {name: connection.execute(text(f"SELECT count(*) FROM {name}")).scalar_one()
                        for name in sorted(_ADDED_AFTER_0023)}

        before = counts()
        report = probe_guards(engine)
        assert counts() == before, "the probe must leave no trace"
        probed = {item["table"] for item in report if item["result"] != "empty"}
        assert _ADDED_AFTER_0023 <= probed, sorted(_ADDED_AFTER_0023 - probed)
        assert {item["result"] for item in report if item["result"] != "empty"} <= {"AM002", "AM003"}

        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE price_list_revision DISABLE TRIGGER trg_price_list_revision_immutable")
        disabled = probe_guards(engine)
        # The update is accepted. The delete still "raises", but it is the child rows' foreign key
        # (23503) and not the guard: asserting the guard's own SQLSTATE is what tells them apart.
        assert {item["operation"]: item["result"] for item in disabled
                if item["table"] == "price_list_revision"} == {"update": "ACCEPTED", "delete": "23503"}
        assert counts() == before, "an accepted probe write must still be rolled back"

        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE price_list_revision ENABLE TRIGGER trg_price_list_revision_immutable")
            connection.exec_driver_sql(
                "DROP TRIGGER trg_work_assignment_event_immutable ON work_assignment_event")
            connection.exec_driver_sql(
                "CREATE TRIGGER trg_work_assignment_event_immutable BEFORE DELETE ON "
                "work_assignment_event FOR EACH ROW EXECUTE FUNCTION am_immutable_row()")
        narrowed = probe_guards(engine)
        outcome = {item["operation"]: item["result"] for item in narrowed
                   if item["table"] == "work_assignment_event"}
        assert outcome == {"update": "ACCEPTED", "delete": "AM003"}
    finally:
        engine.dispose()
