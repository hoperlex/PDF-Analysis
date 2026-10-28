"""`STAND-PURGE-TOOL-01`: the product purge keeps the accounts and the corpus, and every guard bites.

Real PostgreSQL and a real S3-compatible bucket (the lane's), a stand in miniature built by
``purge_seed`` (the recorded run, decisions, price lists, an optimisation pass, accounts with a
changed administrator password, a pending registration, a corpus with a verified retrieval set and
its custody, and one product graph that CITES the corpus). Each test gets its own clone of that
database and its own copy of the bucket.

**What "kept" means is measured with the test's own digest** (``purge_seed.digest_of``, over
``row_to_json``), not with the tool's: a comparison that shared the tool's bug would prove nothing.

**Every guard is shown able to fail.** ``# >>> guard: <name>`` / ``# <<< guard: <name>`` blocks in
``scripts/recovery/product_purge.py`` are deleted one at a time from a COPY of the source (the
convention of ``reset.sh``'s refusal suite). Each scenario below makes the guard's condition true;
the real module must REFUSE (exit 3, the reason in the message, nothing changed), and the copy
without that block must not say that reason. The mutation table in
``docs/program/STAND-PURGE-TOOL-01.md`` is this file's ``SCENARIOS`` with the observed effect.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import sys
import types
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from auditmanager.access import audit as access_audit
from auditmanager.access.public import UserRepository
from auditmanager.ingest import IngestService
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.migrations import head_revision
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import AuditEventId, RunId
from auditmanager.storage import S3BlobStore, S3StorageSettings
from scripts.recovery import product_purge as tool
from scripts.recovery.schema_coverage import EXEMPT_FROM_FINGERPRINT, TABLES
from tests.integration.recovery.purge_seed import NEW_ADMIN_PASSWORD, STRAY_KEY, bucket_profile, digest_of
from tests.integration.recovery.purge_stand import (  # noqa: F401  (the fixtures are used by name)
    Stand, _line, full_purge, invoke, seeded, stand, state_of,
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "scripts/recovery/product_purge.py"
ALL_TABLES = sorted(TABLES)


# --- the declaration -------------------------------------------------------------------------


def test_the_declaration_partitions_exactly_the_tables_schema_coverage_declares() -> None:
    assert tool.classification_problems() == []
    # `EXEC-SEAL-01`: the five executor tables (connection, revision, secret, probe, route event)
    # are configuration, like accounts, and join the kept tables: 23 -> 28.
    # `EXEC-PULL-01`: the runner tokens are configuration too (KEEP 28 -> 29) and the tasks carry
    # the stand's documents and answers (PRODUCT 29 -> 30).
    # `0032_ar_v3_run_group`: the group and its six members are product data (PRODUCT 30 -> 32).
    assert {"ar_v3_run_group", "ar_v3_run_group_member"} <= tool.PRODUCT_TABLES
    # `0035_comparison_records`: the sheet-link history and the summaries are product data
    # (PRODUCT 32 -> 34).
    assert {"comparison_sheet_link", "comparison_summary"} <= tool.PRODUCT_TABLES
    # `0037_analysis_presets`: the revisions of a named preset are executor configuration, like the
    # connections they name (KEEP 29 -> 30); a run (PRODUCT) references them, never the reverse.
    assert "analysis_preset_revision" in tool.KEEP_TABLES and "analysis_preset_revision" not in tool.PRODUCT_TABLES
    # `0038_comparison_foundation`: the nine comparison tables carry product data and reference the
    # project, document versions and executor tasks, so they are truncated with the rest (PRODUCT 34 -> 43).
    assert {"comparison_upload", "comparison_upload_set", "comparison_upload_file", "comparison_upload_part",
            "comparison_version_order", "comparison_page_profile", "comparison_work",
            "comparison_work_attempt", "comparison_model_call"} <= tool.PRODUCT_TABLES
    assert len(tool.PRODUCT_TABLES) == 43 and len(tool.KEEP_TABLES) == 30 and len(tool.MIXED_TABLES) == 3
    assert tool.PRODUCT_TABLES | tool.KEEP_TABLES | tool.MIXED_TABLES == TABLES
    # the corpus half of KEEP is schema_coverage's own list, not a copy of it
    assert tool.KEEP_NORM_TABLES is EXEMPT_FROM_FINGERPRINT
    assert tool.KEEP_ACCOUNT_TABLES == {"app_user", "app_user_role", "registration_request", "account_release_mark"}


def test_every_event_type_and_command_type_the_source_writes_is_classified() -> None:
    """A new ``event_type=`` or command constant in ``src/`` that nobody classified fails HERE,
    not on the stand: the tool would refuse there, but a refusal on the stand is the late way."""
    events, commands = set(), set()
    for path in (ROOT / "src").rglob("*.py"):
        body = path.read_text(encoding="utf-8")
        events |= set(re.findall(r'event_type\s*=\s*"([a-z_][a-z0-9_.]*)"', body))
        commands |= set(re.findall(r'command_type\s*=\s*"([a-z][a-z0-9_]*)"', body))
        commands |= set(re.findall(
            r'^[A-Z_]*COMMAND(?:_TYPE[A-Z_]*)?(?::[^=\n]+)?\s*=\s*"([a-z][a-z0-9_]*)"', body, re.MULTILINE))
    assert {"audit_run.created", "norm_custody.bound", "provider.prepared"} <= events
    assert {"create_project", "approve_registration", "upload_price_list"} <= commands
    prefixes = tool.KEEP_EVENT_PREFIXES + tool.PRODUCT_EVENT_PREFIXES
    assert sorted(e for e in events if not e.startswith(prefixes)) == []
    assert sorted(commands - tool.KEEP_COMMAND_TYPES - tool.PRODUCT_COMMAND_TYPES) == []
    assert not (tool.KEEP_COMMAND_TYPES & tool.PRODUCT_COMMAND_TYPES)


def test_the_temporary_prefix_is_the_storage_adapters(tmp_path: Path) -> None:
    from auditmanager.storage import _object_layout as layout  # the one place that may know it

    assert layout.temporary_key("tok") == tool.temporary_key("tok")


# --- the purge --------------------------------------------------------------------------------


def test_a_dry_run_prints_the_classification_with_exact_counts_and_changes_nothing(stand: Stand) -> None:
    before = state_of(stand)
    code, out, err = invoke(tool, stand, "plan", "--dry-run")
    assert code == 0, err
    assert state_of(stand) == before
    for table in tool.PRODUCT_TABLES:
        assert re.search(rf"^  {table}  \({before['tables'][table][0]} rows\)$", out, re.MULTILINE), table
    assert f"  project  ({before['tables']['project'][0]} rows)" in out
    assert "-- PRODUCT tables: every row goes (TRUNCATE) --" in out and "-- KEEP tables: never written --" in out
    # `PROD-06`: 3 `norm_custody.*` (the custody ledger) + 4 `access.*` that the seed journals
    # through the real writer: three role grants (`synthetic_drill_seed`, host-style) and the
    # administrator's changed password. The keep side was 3 rows before the access events existed.
    assert digest_of(stand.engine, "audit_event", "starts_with(event_type, 'norm_custody.')")[0] == 3
    assert digest_of(stand.engine, "audit_event", "starts_with(event_type, 'access.')")[0] == 4
    assert "  audit_event  (delete 24 rows, keep 7 rows)" in out
    assert "  command_record  (delete 10 rows, keep 1 rows)" in out
    assert "norm-owned objects (the custody ledger's, never touched): 2" in out
    assert "other objects (named by no row; never touched): 1 (blobs/ 1)" in out
    assert "--dry-run: NOTHING ABOVE WAS CHANGED." in out and "nothing-to-purge: no" in out
    stray = stand.client.head_object(Bucket=stand.bucket, Key=STRAY_KEY)
    assert stray["ContentLength"] > 0


def test_the_purge_removes_every_product_row_and_object_and_keeps_the_rest_byte_for_byte(
    stand: Stand, tmp_path: Path
) -> None:
    before = state_of(stand)
    keep_tables = sorted(tool.KEEP_TABLES)
    custody_keep = digest_of(stand.engine, "audit_event", "starts_with(event_type, 'norm_custody.')")
    # `PROD-06`: the account side's journal is kept as well; the test's own predicate, not the tool's.
    access_keep = digest_of(stand.engine, "audit_event", "starts_with(event_type, 'access.')")
    audit_keep = digest_of(
        stand.engine, "audit_event",
        "starts_with(event_type, 'norm_custody.') OR starts_with(event_type, 'access.')")
    command_keep = digest_of(stand.engine, "command_record", "command_type = 'approve_registration'")
    blob_keep = digest_of(stand.engine, "blob", "blob_id IN (SELECT blob_id FROM norm_custody_binding "
                          "UNION SELECT set_blob_id FROM norm_retrieval_set "
                          "UNION SELECT catalogue_blob_id FROM norm_retrieval_set)")
    with stand.engine.connect() as connection:
        triggers = connection.execute(text(
            "SELECT tgrelid::regclass::text, tgname, tgenabled::text FROM pg_trigger "
            "WHERE NOT tgisinternal ORDER BY 1, 2")).all()
        sequences = dict(connection.execute(text("SELECT sequencename, last_value FROM pg_sequences")).all())
    assert all(before["tables"][t][0] > 0 for t in ("project", "document_version", "audit_run", "finding",
                                                    "expert_decision_event", "price_list_revision",
                                                    "optimisation_pass", "work_assignment",
                                                    "document_version_classification_correction",
                                                    "finding_observation_norm_citation"))
    assert sum(1 for key in before["bucket"] if key.startswith("blobs/")) >= 5

    steps = full_purge(tool, stand, tmp_path / "dump")
    assert steps["apply"][0] == 0 and steps["delete"][0] == 0, steps

    after = state_of(stand)
    # every PRODUCT table is empty
    assert {t: after["tables"][t][0] for t in tool.PRODUCT_TABLES} == {t: 0 for t in tool.PRODUCT_TABLES}
    # accounts, registration requests and the whole corpus: the same rows, byte for byte
    for table in keep_tables:
        assert after["tables"][table] == before["tables"][table], table
    assert before["tables"]["alembic_version"] == after["tables"]["alembic_version"]
    assert digest_of(stand.engine, "app_user")[0] == before["tables"]["app_user"][0] >= 4
    # the mixed tables hold exactly their keep rows
    assert digest_of(stand.engine, "audit_event") == audit_keep and audit_keep[0] == 7
    assert custody_keep[0] == 3 and access_keep[0] == 4
    assert digest_of(stand.engine, "audit_event", "starts_with(event_type, 'norm_custody.')") == custody_keep
    assert digest_of(stand.engine, "audit_event", "starts_with(event_type, 'access.')") == access_keep
    assert digest_of(stand.engine, "command_record") == command_keep and command_keep[0] == 1
    assert digest_of(stand.engine, "blob") == blob_keep and blob_keep[0] == 2
    # objects: product gone, the custody ledger's and the stray untouched, byte for byte
    gone = set(before["bucket"]) - set(after["bucket"])
    assert len(gone) >= 14 and STRAY_KEY not in gone
    assert set(after["bucket"]) == set(stand.summary["norm_keys"]) | {STRAY_KEY}
    assert all(after["bucket"][key] == before["bucket"][key] for key in after["bucket"])
    assert stand.summary["temporary_key"] in gone
    # triggers (a purge must leave the append-only guard enabled) and sequences (monotonic)
    with stand.engine.connect() as connection:
        assert connection.execute(text(
            "SELECT tgrelid::regclass::text, tgname, tgenabled::text FROM pg_trigger "
            "WHERE NOT tgisinternal ORDER BY 1, 2")).all() == triggers
        assert {n: v for n, v in connection.execute(text(
            "SELECT sequencename, last_value FROM pg_sequences")).all()} == sequences
    # the dump half: the key list names exactly what went, in reset.sh's sidecar format
    listed = [line.split("\t") for line in (tmp_path / "dump/product-objects.tsv").read_text().splitlines()]
    assert {row[0] for row in listed if row[1] != "-"} == gone
    for row in (tmp_path / "dump/objects.attrs").read_text().splitlines():
        assert re.fullmatch(r"[^\t]+(\t[^\t]+){5}", row), row
    mirrored = {p.relative_to(tmp_path / "dump/objects").as_posix() for p in (tmp_path / "dump/objects").rglob("*") if p.is_file()}
    assert mirrored == gone

    # and the stand WORKS: the administrator signs in with the changed password; a project can be made
    session_factory = create_session_factory(stand.engine)
    with session_factory() as session:
        assert UserRepository().authenticate(session, "admin", NEW_ADMIN_PASSWORD) is not None
        assert UserRepository().authenticate(session, "admin", "password") is None
    store = S3BlobStore(S3StorageSettings.from_env())
    assert IngestService(store, session_factory=session_factory).create_project(name="after the purge")


def test_a_second_run_finds_nothing_and_says_so(stand: Stand, tmp_path: Path) -> None:
    full_purge(tool, stand, tmp_path / "dump")
    settled = state_of(stand)
    code, out, err = invoke(tool, stand, "plan")
    assert code == 0, err
    assert "nothing-to-purge: yes" in out and "nothing to purge" in out
    assert state_of(stand) == settled


def test_the_purge_survives_a_second_pass_through_the_same_dumped_list(stand: Stand, tmp_path: Path) -> None:
    """``--finish-objects`` after a half-done deletion: absent keys are counted, not errors."""
    steps = full_purge(tool, stand, tmp_path / "dump")
    listing = _line(steps["snapshot"][1], "objects-sha256")
    code, out, err = invoke(tool, stand, "delete-objects", "--objects-file",
                            str(tmp_path / "dump/product-objects.tsv"), "--objects-sha256", listing)
    assert code == 0, err
    assert "0 deleted (0 bytes)" in out


# --- the schema guards ------------------------------------------------------------------------


def test_the_live_schema_passes_every_catalog_guard(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        assert tool.check_schema(connection) == head_revision()
        keep, product = tool.blob_columns(connection)
    assert ("norm_custody_binding", "blob_id") in keep and ("norm_retrieval_set", "set_blob_id") in keep
    assert ("input_manifest_entry", "blob_id") in product and ("price_list_revision", "blob_id") in product


# --- every guard shown able to fail ------------------------------------------------------------

_BLOCK = r"^[ \t]*# >>> guard: {name}\n.*?^[ \t]*# <<< guard: {name}\n"
_MUTANTS = iter(range(10**6))


def mutant(*guards: str) -> types.ModuleType:
    """The module with exactly those guard blocks deleted, run from a copy of the source."""
    source = SOURCE.read_text(encoding="utf-8")
    for name in guards:
        source, count = re.subn(_BLOCK.format(name=re.escape(name)), "", source, flags=re.DOTALL | re.MULTILINE)
        assert count == 1, f"the guard markers for {name!r} are not a single block"
    module = types.ModuleType(f"scripts.recovery.product_purge_mutant_{next(_MUTANTS)}")
    module.__file__ = str(SOURCE)
    sys.modules[module.__name__] = module
    exec(compile(source, f"<product_purge without {guards}>", "exec"), module.__dict__)  # noqa: S102
    return module


def sql(stand: Stand, statement: str, **parameters: object) -> None:
    with stand.engine.begin() as connection:
        connection.execute(text(statement), parameters)


class Harness:
    """One scenario's stand, scratch directory and before-state."""

    def __init__(self, stand: Stand, tmp: Path) -> None:
        self.stand, self.tmp = stand, tmp
        self.before: dict[str, Any] = {}

    def checkpoint(self) -> None:
        self.before = state_of(self.stand)

    def dump(self) -> str:
        """The preflight and the object copy, through the REAL module. Returns the plan digest."""
        plan = invoke(tool, self.stand, "plan")
        snapshot = invoke(tool, self.stand, "snapshot-objects", "--dump-dir", str(self.tmp / "dump"))
        assert plan[0] == 0 and snapshot[0] == 0, (plan, snapshot)
        assert _line(plan[1], "plan-sha256") == _line(snapshot[1], "plan-sha256")
        return _line(plan[1], "plan-sha256")

    def apply(self, module: types.ModuleType, sha: str) -> tuple[int, str, str]:
        return invoke(module, self.stand, "apply", "--expect-plan", sha,
                      "--objects-file", str(self.tmp / "dump/product-objects.tsv"))

    def delete(self, module: types.ModuleType, *, rewrite: Callable[[str], str] | None = None,
               sha: str | None = None, purged: bool = True) -> tuple[int, str, str]:
        """``delete-objects`` through ``module`` over the dumped list, optionally edited."""
        if purged:
            listing = _line(full_purge(tool, self.stand, self.tmp / "dump")["snapshot"][1], "objects-sha256")
        else:
            self.dump()
            listing = hashlib.sha256((self.tmp / "dump/product-objects.tsv").read_bytes()).hexdigest()
        path = self.tmp / "dump/product-objects.tsv"
        if rewrite is not None:
            path.write_text(rewrite(path.read_text()), encoding="utf-8")
            listing = hashlib.sha256(path.read_bytes()).hexdigest()
        return invoke(module, self.stand, "delete-objects", "--objects-file", str(path),
                      "--objects-sha256", sha or listing)


def new_role(stand: Stand) -> str:
    name = f"purge_probe_{secrets.token_hex(4)}"
    with stand.engine.begin() as connection:
        connection.execute(text(f"CREATE ROLE {name} LOGIN PASSWORD 'probe-password'"))
        connection.execute(text(f'GRANT CONNECT ON DATABASE "{stand.database}" TO {name}'))
        connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {name}"))
        connection.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {name}"))
    return name


def drop_role(stand: Stand, name: str) -> None:
    with stand.engine.begin() as connection:
        connection.execute(text(f"DROP OWNED BY {name}"))
        connection.execute(text(f"DROP ROLE {name}"))


def norm_row(stand: Stand) -> str:
    """A key-list line that names a corpus object, exactly as a real line would."""
    from auditmanager.storage.public import canonical_object_key_for_recovery

    with stand.engine.connect() as connection:
        blob = connection.execute(text("SELECT blob_id FROM norm_custody_binding ORDER BY 1 LIMIT 1")).scalar_one()
    return "\t".join((canonical_object_key_for_recovery(blob), "10", "canonical", blob, "0" * 64, "no")) + "\n"


def first_canonical(listing: str) -> list[str]:
    return next(line.split("\t") for line in listing.splitlines() if "\tcanonical\t" in line and "\t-\t" not in line)


def _widen(predicates: Callable[..., Any], replacement: str) -> Callable[..., dict[str, tuple[str, str]]]:
    def patched(keep_pairs: Any) -> dict[str, tuple[str, str]]:
        result = predicates(keep_pairs)
        result["audit_event"] = (result["audit_event"][0], replacement)
        return result
    return patched


def _unclassified_event(s: Stand) -> None:
    sql(s, "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
           "VALUES ('evt_01M5F21PBT7E8WRN3M61BDQFDD', 'zz.unclassified', 'Zzz', 'zz_01M5F21PBT7E8WRN3M61BDQFDD', "
           "CAST('{}' AS jsonb))")


def _unclassified_command(s: Stand) -> None:
    sql(s, "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint, state) "
           "VALUES ('cmd_01M5F21PBT7E8WRN3M61BDQFDD', 'zz_unclassified', 'zz-1', :f, 'in_progress')", f="a" * 64)


def _a_run_is_running(s: Stand) -> None:
    sql(s, "ALTER TABLE audit_run DISABLE TRIGGER trg_audit_run_state_guard")
    sql(s, "UPDATE audit_run SET state = 'running' WHERE state = 'created'")
    sql(s, "ALTER TABLE audit_run ENABLE TRIGGER trg_audit_run_state_guard")


def _truncate_guard(s: Stand) -> None:
    sql(s, "CREATE FUNCTION zz_refuse() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'no'; END $$")
    sql(s, "CREATE TRIGGER zz_no_truncate BEFORE TRUNCATE ON project FOR EACH STATEMENT EXECUTE FUNCTION zz_refuse()")


def act_plan(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return invoke(m, h.stand, "plan")


def act_versioned_bucket(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    h.stand.client.put_bucket_versioning(Bucket=h.stand.bucket, VersioningConfiguration={"Status": "Enabled"})
    return invoke(m, h.stand, "plan")


def act_ambient_libpq(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    import os

    os.environ["PGHOSTADDR"] = "127.0.0.1"  # the same host as the URL, so the copy that ignores it still works
    try:
        return invoke(m, h.stand, "plan")
    finally:
        del os.environ["PGHOSTADDR"]


def act_wrong_name(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return invoke(m, h.stand, "plan", database="some_other_database")


def act_apply(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return h.apply(m, h.dump())


def act_not_the_owner(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    import os

    role = new_role(h.stand)
    previous = os.environ["DATABASE_URL"]
    os.environ["DATABASE_URL"] = h.stand.settings.url.set(
        username=role, password="probe-password").render_as_string(hide_password=False)
    try:
        return invoke(m, h.stand, "plan")
    finally:
        os.environ["DATABASE_URL"] = previous
        drop_role(h.stand, role)


def act_late_write(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    sha = h.dump()
    sql(h.stand, "INSERT INTO project (project_uid, name) VALUES ('prj_01M5F21PBT7E8WRN3M61BDQFDD', 'late')")
    h.checkpoint()
    return h.apply(m, sha)


def act_busy(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    sha = h.dump()
    engine = create_database_engine(h.stand.settings)
    holder = engine.connect()
    holder.execute(text("SELECT count(*) FROM project"))  # ACCESS SHARE, held until rollback
    try:
        return h.apply(m, sha)
    finally:
        holder.rollback()
        holder.close()
        engine.dispose()


def act_short_list(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    sha = h.dump()
    path = h.tmp / "dump/product-objects.tsv"
    path.write_text("".join(path.read_text().splitlines(keepends=True)[1:]))  # one key quietly dropped
    return h.apply(m, sha)


def act_tampered_object(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    stand = h.stand
    key = next(k for k in bucket_profile(stand.client, stand.bucket)
               if k.startswith("blobs/") and k != STRAY_KEY and k not in stand.summary["norm_keys"])
    head = stand.client.head_object(Bucket=stand.bucket, Key=key)
    stand.client.put_object(Bucket=stand.bucket, Key=key, Body=b"bytes that are not what was recorded",
                            ContentType=head["ContentType"], Metadata=head["Metadata"])
    h.checkpoint()
    return invoke(m, stand, "snapshot-objects", "--dump-dir", str(h.tmp / "dump"))


def act_stale_mirror(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    (h.tmp / "dump/objects").mkdir(parents=True)
    (h.tmp / "dump/objects/left-over-from-an-earlier-run").write_bytes(b"x")
    return invoke(m, h.stand, "snapshot-objects", "--dump-dir", str(h.tmp / "dump"))


def act_edited_list_sha(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return h.delete(m, sha="0" * 64)


def act_list_names_the_stray(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    def rewrite(body: str) -> str:
        row = first_canonical(body)
        row[0] = STRAY_KEY  # the ref is a product Blob's; the key is an object nothing names
        return "\t".join(row) + "\n" + body
    return h.delete(m, rewrite=rewrite)


def act_list_names_the_corpus(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return h.delete(m, rewrite=lambda body: body + norm_row(h.stand))


def act_delete_before_the_purge(m: types.ModuleType, h: Harness) -> tuple[int, str, str]:
    return h.delete(m, purged=False)


@dataclass
class Scenario:
    guard: str
    says: str
    act: Callable[[types.ModuleType, Harness], tuple[int, str, str]]
    prepare: Callable[[Stand], None] = lambda s: None
    patch: Callable[[pytest.MonkeyPatch, types.ModuleType], None] | None = None
    #: the guard sits before ``COMMIT`` and a refusal rolls back: nothing at all changed
    unchanged: bool = True
    #: what the deleted guard lets happen, when that is more than "the refusal is gone"
    effect: Callable[[Stand, Harness, int], bool] | None = None


def _object_names(stand: Stand) -> set[str]:
    return set(bucket_profile(stand.client, stand.bucket))


def _norm_events(stand: Stand) -> int:
    return digest_of(stand.engine, "audit_event", "starts_with(event_type, 'norm_custody.')")[0]


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("names-match", "the typed names are not the connected ones", act_wrong_name,
             effect=lambda s, h, code: code == 0),
    Scenario("no-ambient-libpq", "can redirect the connection that DATABASE_URL names", act_ambient_libpq,
             effect=lambda s, h, code: code == 0),
    Scenario("bucket-unversioned", "is versioned", act_versioned_bucket, effect=lambda s, h, code: code == 0),
    Scenario("relations-recognised", "a relation the purge does not understand", act_plan,
             prepare=lambda s: (sql(s, "CREATE SCHEMA zz_stray"), sql(s, "CREATE TABLE zz_stray.t (a int)")) and None),
    Scenario("classification-total", "classified as neither PRODUCT, KEEP nor MIXED: ['zz_throwaway']", act_plan,
             prepare=lambda s: sql(s, "CREATE TABLE zz_throwaway (a int)"), effect=lambda s, h, code: code == 0),
    Scenario("declaration-matches-coverage", "the purge declaration is inconsistent", act_plan,
             patch=lambda mp, m: mp.setattr(m, "TABLES", frozenset(TABLES - {"project"}))),
    Scenario("blob-columns-closed", "differ from blob_reference_audit's closed set", act_plan,
             prepare=lambda s: sql(s, "ALTER TABLE app_user_role ADD COLUMN zz_blob text REFERENCES blob (blob_id)")),
    Scenario("keep-never-references-product", "has a foreign key into a PRODUCT table", act_plan,
             prepare=lambda s: sql(s, "ALTER TABLE app_user_role ADD COLUMN zz_project text "
                                      "REFERENCES project (project_uid)")),
    Scenario("no-truncate-guard-on-product", "carries a BEFORE TRUNCATE trigger", act_plan, prepare=_truncate_guard),
    Scenario("owner-may-write", "does not own", act_not_the_owner, effect=lambda s, h, code: code == 0),
    Scenario("event-types-classified", "event type(s) nobody classified", act_plan, prepare=_unclassified_event),
    Scenario("command-types-classified", "command type(s) nobody classified", act_plan,
             prepare=_unclassified_command),
    Scenario("quiescent", "work is running right now", act_plan, prepare=_a_run_is_running,
             effect=lambda s, h, code: code == 0),
    Scenario("norm-key-not-in-product-list", "owned by the norm custody ledger", act_plan,
             patch=lambda mp, m: mp.setattr(m, "norm_owned_keys", lambda c, p: {k for k, _, _ in m._wanted_objects(c, p)})),
    Scenario("lock-available", "could not lock the tables", act_busy,
             patch=lambda mp, m: mp.setattr(m, "LOCK_TIMEOUT", "300ms"),
             effect=lambda s, h, code: code == tool.EXIT_FAILED),
    Scenario("plan-unchanged", "the product data changed since the plan", act_late_write,
             effect=lambda s, h, code: code == 0 and digest_of(s.engine, "project")[0] == 0),
    Scenario("object-list-matches-plan", "dumped key list is not the key list of this plan", act_short_list,
             effect=lambda s, h, code: code == 0),
    Scenario("keep-unchanged", "the purge would have changed KEEP data", act_apply,
             patch=lambda mp, m: mp.setattr(m, "_predicates", _widen(m._predicates, "true")),
             effect=lambda s, h, code: code == 0 and _norm_events(s) == 0),
    Scenario("product-emptied", "hold product rows after the purge", act_apply,
             patch=lambda mp, m: mp.setattr(m, "_predicates", _widen(m._predicates, "false")),
             effect=lambda s, h, code: code == 0 and digest_of(s.engine, "audit_event")[0] > 3),
    Scenario("triggers-restored", "a trigger's state differs after the purge", act_apply,
             prepare=lambda s: sql(s, "ALTER TABLE audit_event DISABLE TRIGGER trg_audit_event_append_only"),
             effect=lambda s, h, code: code == 0 and digest_of(s.engine, "project")[0] == 0),
    Scenario("mirror-bytes-match", "does not match the object", act_tampered_object,
             effect=lambda s, h, code: code == 0),
    Scenario("mirror-complete", "the object mirror is not complete", act_stale_mirror,
             effect=lambda s, h, code: code == 0),
    Scenario("object-list-intact", "is not the key list that was dumped", act_edited_list_sha, unchanged=False,
             effect=lambda s, h, code: code == 0),
    Scenario("key-shape", "is not exactly the key of", act_list_names_the_stray, unchanged=False,
             effect=lambda s, h, code: STRAY_KEY not in _object_names(s)),
    Scenario("norm-owned-key", "key(s) the norm custody ledger owns", act_list_names_the_corpus, unchanged=False),
    Scenario("row-gone", "still (or again) names key(s) from the list", act_delete_before_the_purge,
             effect=lambda s, h, code: code == 0 and digest_of(s.engine, "project")[0] > 0
             and len(_object_names(s)) < len(h.before["bucket"])),
)


def test_every_guard_in_the_module_has_a_scenario() -> None:
    body = SOURCE.read_text(encoding="utf-8")
    markers = re.findall(r"^[ \t]*# >>> guard: ([a-z-]+)$", body, re.MULTILINE)
    assert len(markers) == len(set(markers)) == len(SCENARIOS) == 26
    assert sorted(markers) == sorted(s.guard for s in SCENARIOS)
    for name in markers:
        assert len(re.findall(rf"^[ \t]*# <<< guard: {re.escape(name)}$", body, re.MULTILINE)) == 1


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.guard for s in SCENARIOS])
def test_the_guard_refuses_and_a_refusal_changes_nothing(
    scenario: Scenario, stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario.prepare(stand)
    harness = Harness(stand, tmp_path)
    harness.checkpoint()
    if scenario.patch:
        scenario.patch(monkeypatch, tool)
    code, out, err = scenario.act(tool, harness)
    assert code == tool.EXIT_REFUSED, (code, out, err)
    assert scenario.says in err, err
    if scenario.unchanged:
        assert state_of(stand) == harness.before, "a refusal must leave the database and the bucket as they were"
    else:
        names = _object_names(stand)
        assert STRAY_KEY in names and set(stand.summary["norm_keys"]) <= names


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.guard for s in SCENARIOS])
def test_deleting_the_guard_removes_the_refusal(
    scenario: Scenario, stand: Stand, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario.prepare(stand)
    harness = Harness(stand, tmp_path)
    harness.checkpoint()
    broken = mutant(scenario.guard)
    if scenario.patch:
        # the dump half is taken through the real module, so the same wrong classification must
        # reach both, or the plan digests disagree and the run refuses for the wrong reason
        scenario.patch(monkeypatch, tool)
        scenario.patch(monkeypatch, broken)
    code, out, err = scenario.act(broken, harness)
    assert scenario.says not in err, (
        f"the {scenario.guard} guard was deleted and the refusal happened anyway, so the scenario "
        f"was never testing that guard: {err}")
    if scenario.effect is not None:
        assert scenario.effect(stand, harness, code), (
            f"{scenario.guard}: the copy without the guard did not do what the guard prevents "
            f"(exit {code}): {err or out[-300:]}")


def test_the_corpus_is_only_safe_because_two_independent_guards_agree(stand: Stand, tmp_path: Path) -> None:
    """``norm-owned-key`` and ``row-gone`` each refuse an edited list that names a corpus object;
    delete BOTH and the corpus object is deleted. Neither alone is the harm, the pair is."""
    code, out, err = Harness(stand, tmp_path / "one").delete(mutant("norm-owned-key"), rewrite=lambda b: b + norm_row(stand))
    assert code == tool.EXIT_REFUSED and "still (or again) names" in err
    assert set(stand.summary["norm_keys"]) <= _object_names(stand)
    code, out, err = Harness(stand, tmp_path / "two").delete(
        mutant("norm-owned-key", "row-gone"), rewrite=lambda b: b + norm_row(stand), purged=False)
    assert code == 0, (out, err)
    assert not set(stand.summary["norm_keys"]) <= _object_names(stand)


def test_the_executor_configuration_is_kept_by_a_product_purge() -> None:
    """`EXEC-SEAL-01`: connections, revisions, secrets, probes and route events are configuration.

    Each of the five tables, the seven command types and the ``executor.`` event family is KEEP,
    and none is PRODUCT: a purge of product data must never delete a sealed secret or a route.
    The event family is declared in the tuple AND must reach the SQL that decides which rows stay
    (``DEV-PURGE-EXECUTOR-EVENTS-01``); the purge of real rows is
    ``test_product_purge_executor_events.py``.
    """
    tables = {"executor_connection", "executor_connection_revision", "executor_probe",
              "executor_route_event", "executor_secret"}
    assert tables <= tool.KEEP_TABLES and not tables & tool.PRODUCT_TABLES
    commands = {"create_executor_connection", "revise_executor_connection",
                "archive_executor_connection", "set_executor_secret",
                "generate_executor_ssh_key", "request_executor_probe", "set_executor_route"}
    assert commands <= tool.KEEP_COMMAND_TYPES and not commands & tool.PRODUCT_COMMAND_TYPES
    assert "executor." in tool.KEEP_EVENT_PREFIXES
    assert "starts_with(t.event_type, 'executor.')" in tool._predicates([])["audit_event"][0]
    assert not any("executor." .startswith(prefix) for prefix in tool.PRODUCT_EVENT_PREFIXES)


def test_the_access_journal_is_kept_by_a_product_purge() -> None:
    """`PROD-06`, ADR-0023 section 4: "the 1.0 purge keeps these events" -- the six ``access.*`` types.

    No database: the family is in the tuple, every type the writer can append starts with a keep
    prefix and with no product prefix, and the prefix reaches the SQL that decides which rows stay
    (the real-rows half is ``test_a_purge_keeps_each_of_the_six_access_event_types``). The tool's
    ``event-types-classified`` guard stops on a type nobody classified, so an unclassified seventh
    type would be a refusal on the stand; this is the early way.
    """
    assert "access." in tool.KEEP_EVENT_PREFIXES
    assert len(access_audit.ACCESS_EVENT_TYPES) == 6
    for event_type in access_audit.ACCESS_EVENT_TYPES:
        assert event_type.startswith(tool.KEEP_EVENT_PREFIXES), event_type
        assert not event_type.startswith(tool.PRODUCT_EVENT_PREFIXES), event_type
    keep, delete = tool._predicates([])["audit_event"]
    assert "starts_with(t.event_type, 'access.')" in keep and delete == f"NOT {keep}"


def test_a_purge_keeps_each_of_the_six_access_event_types(stand: Stand, tmp_path: Path) -> None:
    """One event of each of the six types, written by the real writer, survives the whole purge.

    Beside them a product event (``audit_run.created``) that must go, so the keep is shown to be
    a classification and not "nothing was deleted". The surviving rows are compared with the
    test's own digest, before and after, by identity.
    """
    with stand.engine.connect() as connection:
        subject = connection.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one()
        actor = connection.execute(text(
            "SELECT user_uid FROM app_user WHERE login <> 'admin' ORDER BY login LIMIT 1")).scalar_one()
    with create_session_factory(stand.engine).begin() as session:
        access_audit.record_sign_in_succeeded(session, subject_uid=subject, default_credential=False)
        access_audit.record_sign_in_blocked(session, subject_uid=subject, failures=5)
        access_audit.record_role_granted(
            session, subject_uid=subject, role="expert", actor_uid=None, source=access_audit.SOURCE_HOST_CLI)
        access_audit.record_role_revoked(session, subject_uid=subject, role="expert", actor_uid=actor)
        access_audit.record_password_changed(session, subject_uid=subject)
        access_audit.record_password_reset(session, subject_uid=subject, actor_uid=actor)
        session.execute(text(
            "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
            "VALUES (:e, 'audit_run.created', 'AuditRun', :a, CAST('{}' AS jsonb))"),
            {"e": str(AuditEventId.new()), "a": str(RunId.new())})
    where = "starts_with(event_type, 'access.')"
    with stand.engine.connect() as connection:
        types_before = set(connection.execute(text(
            f"SELECT DISTINCT event_type FROM audit_event WHERE {where}")).scalars())
    assert types_before == set(access_audit.ACCESS_EVENT_TYPES)
    before = digest_of(stand.engine, "audit_event", where)
    assert before[0] == 4 + 6  # the seed's four, and ours

    steps = full_purge(tool, stand, tmp_path / "dump")

    assert steps["apply"][0] == 0 and steps["delete"][0] == 0, steps
    assert digest_of(stand.engine, "audit_event", where) == before
    with stand.engine.connect() as connection:
        assert set(connection.execute(text(
            f"SELECT DISTINCT event_type FROM audit_event WHERE {where}")).scalars()) == types_before
        assert connection.execute(text(
            "SELECT count(*) FROM audit_event WHERE event_type = 'audit_run.created'")).scalar_one() == 0


def test_the_runner_tokens_are_kept_and_the_tasks_are_purged_with_the_product() -> None:
    """`EXEC-PULL-01`: a runner token is configuration, like an account; a task carries the
    stand's documents and the model's answers and references runs, Attempts and calls, so it is
    PRODUCT and is truncated in the same statement as the tables it references."""
    assert "executor_runner_token" in tool.KEEP_TABLES
    assert "executor_runner_token" not in tool.PRODUCT_TABLES
    assert "executor_task" in tool.PRODUCT_TABLES and "executor_task" not in tool.KEEP_TABLES
    commands = {"issue_runner_token", "revoke_runner_token"}
    assert commands <= tool.KEEP_COMMAND_TYPES and not commands & tool.PRODUCT_COMMAND_TYPES
    assert tool.classification_problems() == []
