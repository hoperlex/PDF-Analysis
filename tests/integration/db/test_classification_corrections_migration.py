"""`CLASSIFICATION-CORRECTION-01`: ``0028_classification_corrections`` on a populated ``0027`` database.

Against real PostgreSQL rows written at ``0027``:

* the upgrade fabricates nothing: no correction row, every existing version's **current**
  classification equals its original (revision 1), and the original rows are byte-identical;
* a correction is revision 2, 3, ... with the full corrected pair, the expert and the reason;
  the current view follows the latest, the revision view lists all of them oldest first, and
  the original row is never touched;
* the chain is a property of the table: a gap, a no-op, a correction of an unclassified
  version, revision 1 and a duplicate revision are refused by the database (``AM001``,
  ``23514``, ``23505``); the reason, the stage, the section and the expert are checked; the
  table refuses UPDATE and DELETE (``AM003``) and the corrector is a RESTRICT reference;
* ``am_check_optimisation_pass_scope`` asks "is the version AR" of the **current**
  classification: a correction into ``AR`` admits a pass, a correction out of ``AR`` refuses a
  new one, and a pass already written stays;
* the downgrade restores ``0027``'s function, drops only its own objects, keeps every original
  classification, names the corrections it drops, and the revision upgrades again.
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

HEAD = "0028_classification_corrections"
PREVIOUS = "0027_optimisation_proposals"
SHA = "d" * 64
PRICE_LIST = "prl_01ARZ3NDEKTSV4RRFFQ69G5FAV"
VENDOR_LIST = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FAV"
POSITION = "prp_01ARZ3NDEKTSV4RRFFQ69G5FA1"
NEW_OBJECTS = (
    "document_version_classification_correction",
    "version_classification_revision",
    "version_classification_current",
)


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


def _version(connection: Any, project: str, user: str, *, stage: str, section: str | None,
             run: bool = False) -> dict[str, str]:
    ids = {"document": str(DocumentUid.new()), "version": str(VersionUid.new())}
    connection.execute(
        text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Комплект')"),
        {"d": ids["document"], "p": project},
    )
    connection.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
            "byte_size, sha256, page_count) VALUES (:v, :d, 1, 'application/pdf', 1024, :sha, 1)"
        ),
        {"v": ids["version"], "d": ids["document"], "sha": "c" * 64},
    )
    if section is not None:
        connection.execute(
            text(
                "INSERT INTO document_version_classification (version_uid, project_stage, "
                "section_code, confirmed_by_user_uid) VALUES (:v, :stage, :section, :u)"
            ),
            {"v": ids["version"], "stage": stage, "section": section, "u": user},
        )
    if run:
        ids["run"] = str(RunId.new())
        connection.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, "
                "prompt_bundle_id, provider_mode, frozen_input_digest) "
                "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"
            ),
            {"r": ids["run"], "p": project, "v": ids["version"],
             "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new()), "s": "a" * 64},
        )
    return ids


def _seed_0027(connection: Any) -> dict[str, Any]:
    """A project with an unclassified, a KJ, an AR (with a run) and a KJ (with a run) version,
    a project price list and a global AR vendor list: everything a pass needs."""
    project = str(ProjectUid.new())
    connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Школа')"), {"p": project})
    expert, other_expert, admin = _user(connection), _user(connection), _user(connection)
    seeded: dict[str, Any] = {
        "project": project, "expert": expert, "other_expert": other_expert, "admin": admin,
        "bare": _version(connection, project, expert, stage="P", section=None),
        "kj": _version(connection, project, expert, stage="P", section="KJ"),
        "ar": _version(connection, project, expert, stage="R", section="AR", run=True),
        "kj_run": _version(connection, project, expert, stage="R", section="KJ", run=True),
    }
    blob = str(derive_blob_id(sha256=SHA, size=2048))
    connection.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob})
    connection.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :b"), {"b": blob})
    connection.execute(
        text("UPDATE blob SET state = 'available', sha256 = :sha, size_bytes = 2048, "
             "media_type = 'text/csv' WHERE blob_id = :b"),
        {"b": blob, "sha": SHA},
    )
    connection.execute(
        text(
            "INSERT INTO price_list_revision (price_list_id, project_uid, revision_number, "
            "uploaded_by_user_uid, blob_id, sha256, size_bytes, media_type, source_format, "
            "source_filename, default_currency, parse_report, data_row_count, accepted_row_count, "
            "skipped_row_count) VALUES (:id, :project, 1, :user, :blob, :sha, 2048, 'text/csv', "
            "'csv', 'прайс.csv', 'RUB', CAST('{}' AS jsonb), 1, 1, 0)"
        ),
        {"id": PRICE_LIST, "project": project, "user": expert, "blob": blob, "sha": SHA},
    )
    connection.execute(
        text(
            "INSERT INTO price_list_position (price_list_position_id, price_list_id, row_number, "
            "name, unit, unit_price, currency, vendor) VALUES (:id, :list, 2, "
            "'Дверь противопожарная', 'шт', CAST('25000' AS numeric), 'RUB', 'Промет')"
        ),
        {"id": POSITION, "list": PRICE_LIST},
    )
    connection.execute(
        text(
            "INSERT INTO vendor_list_revision (vendor_list_id, scope, project_uid, section_code, mode, "
            "revision_number, entry_count, set_by_user_uid) VALUES (:id, 'global', NULL, 'AR', 'list', "
            "1, 1, :user)"
        ),
        {"id": VENDOR_LIST, "user": admin},
    )
    connection.execute(
        text("INSERT INTO vendor_list_entry (vendor_list_id, ordinal, vendor) VALUES (:id, 1, 'Кнауф')"),
        {"id": VENDOR_LIST},
    )
    return seeded


def _pass(connection: Any, seeded: dict[str, Any], key: str, pass_id: str) -> None:
    """A pass with no proposals: the smallest one the schema admits."""
    ids = seeded[key]
    connection.execute(
        text(
            "INSERT INTO optimisation_pass (optimisation_pass_id, project_uid, document_uid, "
            "version_uid, run_id, text_layer_sha256, price_list_id, vendor_list_id, "
            "vendor_list_source, extraction_algorithm, match_algorithm, generator_version, "
            "specification_row_count, matched_row_count, proposed_row_count, proposal_count, "
            "started_by_user_uid) VALUES (:id, :project, :document, :version, :run, :layer, "
            ":price_list, :vendor_list, 'global', 'specification-text-v1', 'price-match-v1', "
            "'cheaper-analog-v1', 3, 2, 0, 0, :user)"
        ),
        {"id": pass_id, "project": seeded["project"], "document": ids["document"],
         "version": ids["version"], "run": ids["run"], "layer": "e" * 64,
         "price_list": PRICE_LIST, "vendor_list": VENDOR_LIST, "user": seeded["expert"]},
    )


def _correct(connection: Any, version: str, revision: int, stage: str, section: str, user: str,
             reason: str = "Раздел определён неверно") -> None:
    connection.execute(
        text(
            "INSERT INTO document_version_classification_correction (version_uid, revision, "
            "project_stage, section_code, corrected_by_user_uid, reason) "
            "VALUES (:v, :rev, :stage, :section, :u, :reason)"
        ),
        {"v": version, "rev": revision, "stage": stage, "section": section, "u": user, "reason": reason},
    )


def _refused(engine: Engine, write: Any, sqlstate: str | set[str]) -> None:
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    expected = {sqlstate} if isinstance(sqlstate, str) else sqlstate
    assert _sqlstate(caught.value) in expected, caught.value


@pytest.fixture
def at_previous(empty_database: Any, foundation_command: Any) -> Iterator[tuple[Engine, str, dict[str, Any]]]:
    url = empty_database.url.render_as_string(hide_password=False)
    upgraded = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert upgraded.returncode == 0, upgraded.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            seeded = _seed_0027(connection)
        yield engine, url, seeded
    finally:
        engine.dispose()


@pytest.fixture
def at_head(
    at_previous: tuple[Engine, str, dict[str, Any]], foundation_command: Any
) -> tuple[Engine, str, dict[str, Any]]:
    engine, url, seeded = at_previous
    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()
    return engine, url, seeded


_ORIGINALS = (
    "SELECT version_uid, project_stage, section_code, confirmed_by_user_uid, confirmed_at "
    "FROM document_version_classification ORDER BY version_uid"
)


def test_populated_0027_upgrades_and_every_current_classification_is_its_original(
    at_previous: tuple[Engine, str, dict[str, Any]], foundation_command: Any
) -> None:
    engine, url, seeded = at_previous
    with engine.connect() as connection:
        for name in NEW_OBJECTS:
            assert connection.execute(text(f"SELECT to_regclass('{name}')")).scalar_one() is None
        before = [tuple(row) for row in connection.execute(text(_ORIGINALS)).all()]
    assert len(before) == 3

    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        assert connection.execute(
            text("SELECT count(*) FROM document_version_classification_correction")
        ).scalar_one() == 0
        assert [tuple(row) for row in connection.execute(text(_ORIGINALS)).all()] == before
        current = [
            tuple(row) for row in connection.execute(
                text("SELECT version_uid, project_stage, section_code, confirmed_by_user_uid, "
                     "confirmed_at, revision FROM version_classification_current ORDER BY version_uid")
            ).all()
        ]
        assert [row[:5] for row in current] == before and {row[5] for row in current} == {1}
        history = connection.execute(
            text("SELECT version_uid, revision, reason FROM version_classification_revision")
        ).all()
        assert len(history) == 3 and {row[1] for row in history} == {1} and {row[2] for row in history} == {None}
        # the unclassified version has no current classification: the view never invents one
        assert connection.execute(
            text("SELECT count(*) FROM version_classification_current WHERE version_uid = :v"),
            {"v": seeded["bare"]["version"]},
        ).scalar_one() == 0
        definition = connection.execute(
            text("SELECT pg_get_functiondef('am_check_optimisation_pass_scope'::regproc)")
        ).scalar_one()
        assert "version_classification_current" in definition
        assert "document_version_classification" not in definition.replace("version_classification_current", "")


def test_a_correction_is_a_new_revision_and_the_current_view_follows_it(
    at_head: tuple[Engine, str, dict[str, Any]],
) -> None:
    engine, _, seeded = at_head
    version, first, second = seeded["kj"]["version"], seeded["expert"], seeded["other_expert"]
    with engine.begin() as connection:
        original = connection.execute(text(_ORIGINALS)).all()
        _correct(connection, version, 2, "R", "KJ", second, "Это рабочая документация")
        _correct(connection, version, 3, "R", "AR", first, "Раздел указан неверно\nещё раз")
    with engine.connect() as connection:
        current = connection.execute(
            text("SELECT project_stage, section_code, confirmed_by_user_uid, revision "
                 "FROM version_classification_current WHERE version_uid = :v"),
            {"v": version},
        ).one()
        assert tuple(current) == ("R", "AR", first, 3)
        history = connection.execute(
            text("SELECT revision, project_stage, section_code, actor_user_uid, reason "
                 "FROM version_classification_revision WHERE version_uid = :v ORDER BY revision"),
            {"v": version},
        ).all()
        assert [tuple(row) for row in history] == [
            (1, "P", "KJ", first, None),
            (2, "R", "KJ", second, "Это рабочая документация"),
            (3, "R", "AR", first, "Раздел указан неверно\nещё раз"),
        ]
        # the other versions are untouched, and the original row never moves
        assert connection.execute(text(_ORIGINALS)).all() == original
        others = connection.execute(
            text("SELECT revision FROM version_classification_current WHERE version_uid <> :v"),
            {"v": version},
        ).scalars().all()
        assert others == [1, 1]
        stamps = connection.execute(
            text("SELECT corrected_at FROM document_version_classification_correction "
                 "WHERE version_uid = :v ORDER BY revision"),
            {"v": version},
        ).scalars().all()
        assert stamps[0] <= stamps[1]


def test_the_chain_is_a_property_of_the_table(at_head: tuple[Engine, str, dict[str, Any]]) -> None:
    engine, _, seeded = at_head
    kj, bare, user = seeded["kj"]["version"], seeded["bare"]["version"], seeded["other_expert"]
    # no revision 2 yet, so 3 has nothing before it
    _refused(engine, lambda c: _correct(c, kj, 3, "R", "AR", user), "AM001")
    # a correction that changes nothing (the original is P/KJ)
    _refused(engine, lambda c: _correct(c, kj, 2, "P", "KJ", user), "AM001")
    # a version nobody classified has nothing to correct
    _refused(engine, lambda c: _correct(c, bare, 2, "R", "AR", user), "AM001")
    # revision 1 is the original, never a correction (the chain trigger answers before the CHECK)
    _refused(engine, lambda c: _correct(c, kj, 1, "R", "AR", user), {"AM001", "23514"})
    with engine.begin() as connection:
        _correct(connection, kj, 2, "R", "KJ", user)
    # the same revision twice, with a different pair so the chain check passes
    _refused(engine, lambda c: _correct(c, kj, 2, "R", "AR", user), "23505")
    # revision 3 may not repeat revision 2's pair, though it differs from the original's
    _refused(engine, lambda c: _correct(c, kj, 3, "R", "KJ", user), "AM001")
    # going back to the original's values is a legitimate revision
    with engine.begin() as connection:
        _correct(connection, kj, 3, "P", "KJ", user)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT revision FROM version_classification_current WHERE version_uid = :v"), {"v": kj}
        ).scalar_one() == 3


def test_the_values_the_reason_and_the_expert_are_checked(
    at_head: tuple[Engine, str, dict[str, Any]],
) -> None:
    engine, _, seeded = at_head
    kj, user = seeded["kj"]["version"], seeded["other_expert"]
    for stage, section in (("X", "AR"), ("R", "ZZ"), ("R", "ar"), ("", "AR")):
        _refused(engine, lambda c, stage=stage, section=section: _correct(c, kj, 2, stage, section, user), "23514")
    for reason in ("", " ", " ведущий пробел", "хвост\n", "а" * 2001):
        _refused(engine, lambda c, reason=reason: _correct(c, kj, 2, "R", "AR", user, reason), "23514")
    _refused(engine, lambda c: _correct(c, kj, 2, "R", "AR", str(UserUid.new())), "23503")
    _refused(engine, lambda c: _correct(c, "ver_not-a-ulid", 2, "R", "AR", user), {"23514", "AM001"})
    with engine.begin() as connection:
        _correct(connection, kj, 2, "R", "AR", user, "а" * 2000)  # exactly the bound
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT char_length(reason) FROM document_version_classification_correction")
        ).scalar_one() == 2000


def test_every_current_section_is_a_valid_correction_target(
    at_head: tuple[Engine, str, dict[str, Any]],
) -> None:
    engine, _, seeded = at_head
    kj, user = seeded["kj"]["version"], seeded["other_expert"]
    sections = ("AR", "AI", "KM", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS", "PS", "KJ")
    with engine.begin() as connection:
        for revision, section in enumerate(sections, start=2):
            _correct(connection, kj, revision, "P", section, user)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT section_code, revision FROM version_classification_current WHERE version_uid = :v"),
            {"v": kj},
        ).one() == ("KJ", 16)


def test_the_table_is_append_only_and_the_corrector_is_referenced(
    at_head: tuple[Engine, str, dict[str, Any]],
) -> None:
    engine, _, seeded = at_head
    kj, user = seeded["kj"]["version"], seeded["other_expert"]
    with engine.begin() as connection:
        _correct(connection, kj, 2, "R", "KJ", user)
    for statement in (
        "UPDATE document_version_classification_correction SET reason = 'иначе' WHERE version_uid = :v",
        "DELETE FROM document_version_classification_correction WHERE version_uid = :v",
        "UPDATE document_version_classification SET section_code = 'AR' WHERE version_uid = :v",
        "DELETE FROM document_version_classification WHERE version_uid = :v",
    ):
        _refused(engine, lambda c, statement=statement: c.execute(text(statement), {"v": kj}), "AM003")
    _refused(engine, lambda c: c.execute(text("DELETE FROM app_user WHERE user_uid = :u"), {"u": user}), "23503")


def test_a_pass_reads_the_current_classification_and_a_written_pass_stays(
    at_head: tuple[Engine, str, dict[str, Any]],
) -> None:
    engine, _, seeded = at_head
    pass_a, pass_b, pass_c = (f"opp_01ARZ3NDEKTSV4RRFFQ69G5F{suffix}" for suffix in ("A1", "A2", "A3"))
    # a KJ version cannot take a pass; an AR one can
    _refused(engine, lambda c: _pass(c, seeded, "kj_run", pass_a), "AM001")
    with engine.begin() as connection:
        _pass(connection, seeded, "ar", pass_a)
    # corrected into AR, the KJ version takes one ...
    with engine.begin() as connection:
        _correct(connection, seeded["kj_run"]["version"], 2, "R", "AR", seeded["other_expert"])
        _pass(connection, seeded, "kj_run", pass_b)
    # ... and the AR version, corrected out of AR, takes no new one while its old pass stays
    with engine.begin() as connection:
        _correct(connection, seeded["ar"]["version"], 2, "R", "KJ", seeded["other_expert"])
    _refused(engine, lambda c: _pass(c, seeded, "ar", pass_c), "AM001")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT optimisation_pass_id FROM optimisation_pass ORDER BY optimisation_pass_id")
        ).scalars().all() == [pass_a, pass_b]
    # corrected back into AR, the scope check admits it again: what refuses the repeat is the
    # natural key of the pass already written for these inputs (23505), not the scope (AM001)
    with engine.begin() as connection:
        _correct(connection, seeded["ar"]["version"], 3, "R", "AR", seeded["other_expert"])
    _refused(engine, lambda c: _pass(c, seeded, "ar", pass_c), "23505")


def test_the_downgrade_restores_0027_and_drops_only_its_own_objects(
    at_head: tuple[Engine, str, dict[str, Any]], foundation_command: Any
) -> None:
    engine, url, seeded = at_head
    kj = seeded["kj"]["version"]
    with engine.begin() as connection:
        before = connection.execute(text(_ORIGINALS)).all()
        _correct(connection, kj, 2, "R", "AR", seeded["other_expert"])
        _correct(connection, kj, 3, "P", "PS", seeded["other_expert"])
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    assert "2 correction(s) of 1 version(s)" in downgraded.stdout + downgraded.stderr
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        for name in NEW_OBJECTS:
            assert connection.execute(text(f"SELECT to_regclass('{name}')")).scalar_one() is None
        assert connection.execute(
            text("SELECT count(*) FROM pg_proc WHERE proname = 'am_check_classification_correction_chain'")
        ).scalar_one() == 0
        assert connection.execute(text(_ORIGINALS)).all() == before
        definition = connection.execute(
            text("SELECT pg_get_functiondef('am_check_optimisation_pass_scope'::regproc)")
        ).scalar_one()
        assert "JOIN document_version_classification c" in definition
        assert "version_classification_current" not in definition
    # 0027's own rule is back: the original classification decides, so a KJ version takes no pass
    _refused(engine, lambda c: _pass(c, seeded, "kj_run", "opp_01ARZ3NDEKTSV4RRFFQ69G5FB1"), "AM001")
    reupgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert reupgraded.returncode == 0, reupgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM document_version_classification_correction")
        ).scalar_one() == 0
        assert connection.execute(text(_ORIGINALS)).all() == before
