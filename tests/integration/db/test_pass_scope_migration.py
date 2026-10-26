"""`OPT-PROJECT-ALL-SECTIONS-01`: ``0034_pass_scope_all_sections`` on a populated ``0033`` database.

``am_check_optimisation_pass_scope`` (``0027``, replaced in ``0028``) was the database half of an
AR-only rule: the version's current classification had to be ``AR`` and so did the pinned vendor
list. ``0034`` replaces that one function so that the vendor list the pass pins is the list **of the
section the version is classified in**. Against real PostgreSQL rows, written through plain INSERTs
at ``0033``:

* **the control**: at ``0033`` an ``AR`` version with an ``AR`` list takes a pass and a ``PB``
  version with a ``PB`` list does not (``AM001``), so the migration, and nothing else, is what
  admits the second;
* **after the step each section takes its own list**: ``PB``/``PB``, ``AR``/``AR`` are accepted;
* **a mismatched pair is still refused**: a ``PB`` version with the ``AR`` list, an ``AR`` version
  with the ``PB`` list, a ``KJ`` version with either, a version nobody classified, whatever list;
* **every other condition of ``0028`` still holds**, shown on a ``PB`` version: another project's
  document, price list or list, an ``inherit`` marker, a wrong recorded source, a run of another
  version;
* **the current classification decides** (a correction moves the version to another section's
  list), as it did at ``0028``;
* **the upgrade changes no stored row** and the function is the only thing that differs;
* **the downgrade is refused while a pass pins a vendor list of a section other than ``AR``, and
  only then**; with only ``AR`` passes it restores ``0028``'s function byte for byte and the
  upgrade runs again.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from auditmanager.access.public import UserUid
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from auditmanager.storage.models import derive_blob_id
from tests.support.expected_facts import FACTS

HEAD = FACTS.migration_head  # the tree's head: this revision or a later one
THIS = "0034_pass_scope_all_sections"
PREVIOUS = "0033_ar_v3_cite_stage_id"
FUNCTION = "am_check_optimisation_pass_scope"

SHA = "d" * 64
PRICE_LIST = "prl_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_PRICE_LIST = "prl_01ARZ3NDEKTSV4RRFFQ69G5FAW"
POSITION = "prp_01ARZ3NDEKTSV4RRFFQ69G5FA1"
OTHER_POSITION = "prp_01ARZ3NDEKTSV4RRFFQ69G5FA2"
LIST_AR = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FA1"
LIST_PB = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FB1"
LIST_OV = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FC1"
LIST_KJ = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FD1"
LIST_PB_PROJECT = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FB2"
LIST_PB_INHERIT = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FB3"
LIST_PB_OTHER_PROJECT = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FB4"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


def _user(connection: Any) -> str:
    user = str(UserUid.new())
    connection.execute(
        text(
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
            "password_salt, password_hash) VALUES (:u, :login, 'pbkdf2_sha256', 100000, :salt, :hash)"
        ),
        {"u": user, "login": user.lower(), "salt": "0" * 32, "hash": "0" * 64},
    )
    return user


def _scope(connection: Any, ids: dict[str, Any], key: str, project: str, section: str | None) -> None:
    """A document with one version and one run in ``project``; classified in ``section`` unless None."""
    scope = {"document": str(DocumentUid.new()), "version": str(VersionUid.new()), "run": str(RunId.new())}
    connection.execute(
        text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, :t)"),
        {"d": scope["document"], "p": project, "t": key},
    )
    connection.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
            "byte_size, sha256, page_count) VALUES (:v, :d, 1, 'application/pdf', 1024, :sha, 1)"
        ),
        {"v": scope["version"], "d": scope["document"], "sha": "c" * 64},
    )
    if section is not None:
        connection.execute(
            text(
                "INSERT INTO document_version_classification (version_uid, project_stage, "
                "section_code, confirmed_by_user_uid) VALUES (:v, 'R', :section, :u)"
            ),
            {"v": scope["version"], "section": section, "u": ids["expert"]},
        )
    connection.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, "
            "prompt_bundle_id, provider_mode, frozen_input_digest) "
            "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"
        ),
        {"r": scope["run"], "p": project, "v": scope["version"],
         "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new()), "s": "a" * 64},
    )
    ids[key] = scope


def _price_list(connection: Any, ids: dict[str, Any], uid: str, project: str, position: str) -> None:
    connection.execute(
        text(
            "INSERT INTO price_list_revision (price_list_id, project_uid, revision_number, "
            "uploaded_by_user_uid, blob_id, sha256, size_bytes, media_type, source_format, "
            "source_filename, default_currency, parse_report, data_row_count, accepted_row_count, "
            "skipped_row_count) VALUES (:id, :project, 1, :user, :blob, :sha, 2048, "
            "'text/csv', 'csv', 'прайс.csv', 'RUB', CAST('{}' AS jsonb), 1, 1, 0)"
        ),
        {"id": uid, "project": project, "user": ids["expert"], "blob": ids["blob"], "sha": SHA},
    )
    connection.execute(
        text(
            "INSERT INTO price_list_position (price_list_position_id, price_list_id, row_number, "
            "name, unit, unit_price, currency, vendor) VALUES (:id, :list, 2, "
            "'Дверь противопожарная', 'шт', CAST('25000' AS numeric), 'RUB', 'Промет')"
        ),
        {"id": position, "list": uid},
    )


def _vendor_list(connection: Any, ids: dict[str, Any], uid: str, section: str, *, scope: str = "global",
                 project: str | None = None, mode: str = "list", number: int = 1) -> None:
    entries = 0 if mode == "inherit" else 1
    connection.execute(
        text(
            "INSERT INTO vendor_list_revision (vendor_list_id, scope, project_uid, section_code, mode, "
            "revision_number, entry_count, set_by_user_uid) VALUES (:id, :scope, :project, :section, "
            ":mode, :number, :count, :user)"
        ),
        {"id": uid, "scope": scope, "project": project, "section": section, "mode": mode,
         "number": number, "count": entries, "user": ids["admin"]},
    )
    if entries:
        connection.execute(
            text("INSERT INTO vendor_list_entry (vendor_list_id, ordinal, vendor) VALUES (:id, 1, 'Кнауф')"),
            {"id": uid},
        )


def _seed_0033(connection: Any) -> dict[str, Any]:
    """Two projects; in the first one a version of every kind a pass can meet; every vendor list."""
    ids: dict[str, Any] = {"project": str(ProjectUid.new()), "other_project": str(ProjectUid.new())}
    ids["expert"], ids["other_expert"], ids["admin"] = _user(connection), _user(connection), _user(connection)
    for key in ("project", "other_project"):
        connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Школа')"), {"p": ids[key]})
    for key, section in (("ar", "AR"), ("pb", "PB"), ("pb_second", "PB"), ("kj", "KJ"), ("moved", "PB"),
                         ("bare", None)):
        _scope(connection, ids, key, ids["project"], section)
    blob = str(derive_blob_id(sha256=SHA, size=2048))
    connection.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob})
    connection.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :b"), {"b": blob})
    connection.execute(
        text("UPDATE blob SET state = 'available', sha256 = :sha, size_bytes = 2048, "
             "media_type = 'text/csv' WHERE blob_id = :b"),
        {"b": blob, "sha": SHA},
    )
    ids["blob"] = blob
    _price_list(connection, ids, PRICE_LIST, ids["project"], POSITION)
    _price_list(connection, ids, OTHER_PRICE_LIST, ids["other_project"], OTHER_POSITION)
    for uid, section in ((LIST_AR, "AR"), (LIST_PB, "PB"), (LIST_OV, "OV"), (LIST_KJ, "KJ")):
        _vendor_list(connection, ids, uid, section)
    _vendor_list(connection, ids, LIST_PB_PROJECT, "PB", scope="project", project=ids["project"])
    _vendor_list(connection, ids, LIST_PB_INHERIT, "PB", scope="project", project=ids["project"],
                 mode="inherit", number=2)
    _vendor_list(connection, ids, LIST_PB_OTHER_PROJECT, "PB", scope="project", project=ids["other_project"])
    return ids


_counter = iter(range(10, 100))


def _pass(connection: Any, ids: dict[str, Any], key: str, vendor_list: str, **overrides: Any) -> str:
    """A pass with no proposals -- the smallest the schema admits -- over the scope ``ids[key]``."""
    scope = ids[key]
    values: dict[str, Any] = {
        "id": f"opp_01ARZ3NDEKTSV4RRFFQ69G5F{next(_counter):02d}",
        "project": ids["project"],
        "document": scope["document"],
        "version": scope["version"],
        "run": scope["run"],
        "layer": "e" * 64,
        "price_list": PRICE_LIST,
        "vendor_list": vendor_list,
        "source": "global",
        "user": ids["expert"],
    }
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO optimisation_pass (optimisation_pass_id, project_uid, document_uid, "
            "version_uid, run_id, text_layer_sha256, price_list_id, vendor_list_id, "
            "vendor_list_source, extraction_algorithm, match_algorithm, generator_version, "
            "specification_row_count, matched_row_count, proposed_row_count, proposal_count, "
            "started_by_user_uid) VALUES (:id, :project, :document, :version, :run, :layer, "
            ":price_list, :vendor_list, :source, 'specification-text-v1', 'price-match-v1', "
            "'cheaper-analog-v1', 3, 2, 0, 0, :user)"
        ),
        values,
    )
    return str(values["id"])


def _correct(connection: Any, version: str, revision: int, section: str, user: str) -> None:
    connection.execute(
        text(
            "INSERT INTO document_version_classification_correction (version_uid, revision, "
            "project_stage, section_code, corrected_by_user_uid, reason) "
            "VALUES (:v, :rev, 'R', :section, :u, 'Раздел определён неверно')"
        ),
        {"v": version, "rev": revision, "section": section, "u": user},
    )


def _refused(engine: Engine, write: Any, sqlstate: str = "AM001") -> None:
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    assert _sqlstate(caught.value) == sqlstate, caught.value


def _passes(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        return list(connection.execute(
            text("SELECT optimisation_pass_id FROM optimisation_pass ORDER BY optimisation_pass_id")
        ).scalars())


def _definition(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text(f"SELECT pg_get_functiondef('{FUNCTION}'::regproc)")).scalar_one())


def _version(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())


def _upgrade(foundation_command: Any, url: str, revision: str) -> None:
    done = foundation_command(_alembic("upgrade", revision), url)
    assert done.returncode == 0, done.describe()


@pytest.fixture
def at_previous(empty_database: Any, foundation_command: Any) -> Iterator[tuple[Engine, str, dict[str, Any]]]:
    url = empty_database.url.render_as_string(hide_password=False)
    _upgrade(foundation_command, url, PREVIOUS)
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = _seed_0033(connection)
        yield engine, url, ids
    finally:
        engine.dispose()


@pytest.fixture
def at_this(
    at_previous: tuple[Engine, str, dict[str, Any]], foundation_command: Any
) -> tuple[Engine, str, dict[str, Any]]:
    engine, url, ids = at_previous
    _upgrade(foundation_command, url, THIS)
    return engine, url, ids


# -- the control and the step ----------------------------------------------------------------


def test_at_0033_only_an_ar_pass_is_accepted(at_previous: tuple[Engine, str, dict[str, Any]]) -> None:
    engine, _, ids = at_previous
    assert _version(engine) == PREVIOUS
    with engine.begin() as connection:
        _pass(connection, ids, "ar", LIST_AR)
    _refused(engine, lambda c: _pass(c, ids, "pb", LIST_PB))
    _refused(engine, lambda c: _pass(c, ids, "pb", LIST_AR))
    assert len(_passes(engine)) == 1


def test_after_the_step_every_section_takes_a_pass_with_its_own_list(
    at_this: tuple[Engine, str, dict[str, Any]],
) -> None:
    engine, _, ids = at_this
    assert _version(engine) == THIS
    with engine.begin() as connection:
        written = [
            _pass(connection, ids, "ar", LIST_AR),
            _pass(connection, ids, "pb", LIST_PB),
            _pass(connection, ids, "kj", LIST_KJ),
            _pass(connection, ids, "pb_second", LIST_PB_PROJECT, source="project"),
        ]
    assert _passes(engine) == sorted(written)


@pytest.mark.parametrize(
    ("key", "vendor_list", "why"),
    [
        ("pb", LIST_AR, "a PB version with the AR list"),
        ("ar", LIST_PB, "an AR version with the PB list"),
        ("kj", LIST_PB, "a KJ version with the PB list"),
        ("kj", LIST_AR, "a KJ version with the AR list"),
        ("pb", LIST_OV, "a PB version with the OV list"),
        ("bare", LIST_AR, "a version nobody classified, with the AR list"),
        ("bare", LIST_PB, "a version nobody classified, with the PB list"),
    ],
)
def test_a_vendor_list_of_another_section_than_the_versions_is_refused(
    at_this: tuple[Engine, str, dict[str, Any]], key: str, vendor_list: str, why: str
) -> None:
    engine, _, ids = at_this
    _refused(engine, lambda c: _pass(c, ids, key, vendor_list))
    assert _passes(engine) == [], why


@pytest.mark.parametrize(
    ("overrides", "why"),
    [
        ({"project": "other_project"}, "the document is not in that project"),
        ({"price_list": OTHER_PRICE_LIST}, "another project's price list"),
        ({"vendor_list": LIST_PB_INHERIT, "source": "project"}, "an inherit marker is not a list"),
        ({"vendor_list": LIST_PB_OTHER_PROJECT, "source": "project"}, "another project's list"),
        ({"vendor_list": LIST_PB_PROJECT, "source": "global"}, "a project list recorded as global"),
        ({"source": "project"}, "the global list recorded as the project's"),
        ({"run": "RUN_OTHER"}, "a run of another version"),
        ({"version": "VERSION_OTHER"}, "a version of another document"),
    ],
)
def test_every_other_condition_of_0028_still_holds_for_a_pb_version(
    at_this: tuple[Engine, str, dict[str, Any]], overrides: dict[str, str], why: str
) -> None:
    engine, _, ids = at_this
    resolved = dict(overrides)
    if resolved.get("project") == "other_project":
        resolved["project"] = ids["other_project"]
    if resolved.get("run") == "RUN_OTHER":
        resolved["run"] = ids["pb_second"]["run"]
    if resolved.get("version") == "VERSION_OTHER":
        resolved["version"] = ids["pb_second"]["version"]
    resolved.setdefault("vendor_list", LIST_PB)
    vendor_list = resolved.pop("vendor_list")
    _refused(engine, lambda c: _pass(c, ids, "pb", vendor_list, **resolved))
    assert _passes(engine) == [], why


def test_the_current_classification_decides_which_list_the_pass_may_pin(
    at_this: tuple[Engine, str, dict[str, Any]],
) -> None:
    engine, _, ids = at_this
    version = ids["moved"]["version"]
    with engine.begin() as connection:  # classified PB: the PB list is the one
        first = _pass(connection, ids, "moved", LIST_PB)
    with engine.begin() as connection:  # corrected into OV: the OV list, no longer the PB one
        _correct(connection, version, 2, "OV", ids["other_expert"])
    _refused(engine, lambda c: _pass(c, ids, "moved", LIST_PB))
    with engine.begin() as connection:
        second = _pass(connection, ids, "moved", LIST_OV)
    assert _passes(engine) == sorted([first, second])  # the pass written before the correction stays


def test_a_pb_pass_is_accepted_at_the_head(migrated_engine: Engine) -> None:
    assert _version(migrated_engine) == HEAD
    with migrated_engine.begin() as connection:
        ids = _seed_0033(connection)
        _pass(connection, ids, "pb", LIST_PB)
        _pass(connection, ids, "ar", LIST_AR)
    _refused(migrated_engine, lambda c: _pass(c, ids, "pb_second", LIST_AR))
    assert len(_passes(migrated_engine)) == 2


# -- what the step touches --------------------------------------------------------------------

_SNAPSHOT = (
    "SELECT (SELECT count(*) FROM project), (SELECT count(*) FROM document), "
    "(SELECT count(*) FROM document_version), (SELECT count(*) FROM audit_run), "
    "(SELECT count(*) FROM price_list_position), (SELECT count(*) FROM vendor_list_revision), "
    "(SELECT count(*) FROM vendor_list_entry), (SELECT count(*) FROM document_version_classification), "
    "(SELECT count(*) FROM optimisation_pass), "
    "(SELECT string_agg(optimisation_pass_id || vendor_list_id, ',' ORDER BY optimisation_pass_id) "
    " FROM optimisation_pass)"
)


def test_a_populated_0033_database_upgrades_without_a_row_changing_and_only_the_function_differs(
    at_previous: tuple[Engine, str, dict[str, Any]], foundation_command: Any
) -> None:
    engine, url, ids = at_previous
    with engine.begin() as connection:
        written = _pass(connection, ids, "ar", LIST_AR)
    with engine.connect() as connection:
        before = tuple(connection.execute(text(_SNAPSHOT)).one())
        triggers = connection.execute(text(
            "SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger "
            "WHERE tgrelid = 'optimisation_pass'::regclass AND NOT tgisinternal ORDER BY tgname"
        )).all()
    definition = _definition(engine)

    _upgrade(foundation_command, url, THIS)

    assert _version(engine) == THIS
    with engine.connect() as connection:
        assert tuple(connection.execute(text(_SNAPSHOT)).one()) == before
        assert connection.execute(text(
            "SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger "
            "WHERE tgrelid = 'optimisation_pass'::regclass AND NOT tgisinternal ORDER BY tgname"
        )).all() == triggers  # the trigger is untouched; it calls the same function by name
    assert before[8] == 1 and before[9] == f"{written}{LIST_AR}"
    assert _definition(engine) != definition
    assert "c.section_code = 'AR'" not in _definition(engine)
    assert "l.section_code = c.section_code" in _definition(engine)
    assert "AND l.section_code = 'AR'" not in _definition(engine)


def test_the_columns_the_equality_compares_cannot_be_null(
    at_this: tuple[Engine, str, dict[str, Any]],
) -> None:
    """``l.section_code = c.section_code`` is never unknown: both sides are NOT NULL in the base tables."""
    engine, _, _ = at_this
    with engine.connect() as connection:
        nullable = connection.execute(text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE column_name = 'section_code' AND is_nullable = 'YES' AND table_name IN "
            "('vendor_list_revision', 'document_version_classification', "
            "'document_version_classification_correction') ORDER BY table_name"
        )).all()
    assert nullable == []


# -- the downgrade ---------------------------------------------------------------------------


def test_the_downgrade_is_refused_while_a_pass_pins_a_non_ar_list_and_only_then(
    at_this: tuple[Engine, str, dict[str, Any]], foundation_command: Any
) -> None:
    engine, url, ids = at_this
    with engine.begin() as connection:
        _pass(connection, ids, "ar", LIST_AR)
        _pass(connection, ids, "pb", LIST_PB)
    definition, passes = _definition(engine), _passes(engine)

    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "0034 downgrade refused: 1 optimisation pass(es)" in refused.stderr, refused.stderr
    assert _version(engine) == THIS  # a refusal changes nothing
    assert _definition(engine) == definition and _passes(engine) == passes


def test_with_only_ar_passes_the_downgrade_restores_the_0028_function_exactly_and_the_upgrade_runs_again(
    at_previous: tuple[Engine, str, dict[str, Any]], foundation_command: Any
) -> None:
    engine, url, ids = at_previous
    original = _definition(engine)  # 0028's function as 0033 carries it
    _upgrade(foundation_command, url, THIS)
    installed = _definition(engine)
    assert installed != original
    with engine.begin() as connection:
        _pass(connection, ids, "ar", LIST_AR)
    passes = _passes(engine)

    down = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert down.returncode == 0, down.describe()
    assert _version(engine) == PREVIOUS
    assert _definition(engine) == original  # byte for byte, whitespace included
    assert _passes(engine) == passes  # the AR passes are kept
    _refused(engine, lambda c: _pass(c, ids, "pb", LIST_PB))  # 0028's rule is back

    _upgrade(foundation_command, url, THIS)
    assert _definition(engine) == installed
    with engine.begin() as connection:
        _pass(connection, ids, "pb", LIST_PB)
    assert len(_passes(engine)) == 2
