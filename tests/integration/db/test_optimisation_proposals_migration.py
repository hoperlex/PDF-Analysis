"""`W60-OPT-PROPOSALS-01`: ``0027_optimisation_proposals`` on a populated ``0026`` database.

Against real PostgreSQL rows written at ``0026`` -- accounts, a project with a document, an
AR-classified version and a run, a price list with positions and a global AR vendor list:

* the upgrade creates three empty tables beside them and changes no existing row;
* all three tables refuse UPDATE and DELETE (``AM003``);
* a pass whose proposals are not all written is refused at COMMIT (``AM001``);
* a pass that does not pin one consistent scope -- a document of another project, a version
  of another document, a run of another version, a version not classified ``AR``, a price
  list of another project, a vendor list of another section, another project, in
  ``inherit`` mode or of the other source -- is refused at INSERT (``AM001``);
* a proposal whose prices, currency or vendor are not those of two positions of its pass's
  price list is refused at INSERT (``AM001``);
* the money rule holds as CHECKs: a saving exactly when the quantity is a number, equal to
  ``(current − proposed) × quantity``; the proposed price strictly lower;
* the identity formats (``opp_``, ``opr_``, ``opd_``, ``prp_`` included), the vocabularies and
  the bounds hold; ``revise`` needs a comment; one decision per command;
* both account columns are RESTRICT references;
* the downgrade drops exactly the three tables and the three functions, keeps every ``0026``
  row, and the revision upgrades again.
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
    CommandId,
    DocumentUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from auditmanager.storage.models import derive_blob_id

HEAD = "0027_optimisation_proposals"
PREVIOUS = "0026_price_lists"

PASS = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_PASS = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAW"
PROPOSAL = "opr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_PROPOSAL = "opr_01ARZ3NDEKTSV4RRFFQ69G5FAW"
DECISION = "opd_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_DECISION = "opd_01ARZ3NDEKTSV4RRFFQ69G5FAW"
PRICE_LIST = "prl_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_PRICE_LIST = "prl_01ARZ3NDEKTSV4RRFFQ69G5FAW"
MATCHED = "prp_01ARZ3NDEKTSV4RRFFQ69G5FA1"
CHEAPER = "prp_01ARZ3NDEKTSV4RRFFQ69G5FA2"
FOREIGN_POSITION = "prp_01ARZ3NDEKTSV4RRFFQ69G5FA3"
VENDOR_LIST = "vnl_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SHA = "d" * 64
TABLES = ("optimisation_pass", "optimisation_proposal", "optimisation_proposal_decision")
FUNCTIONS = (
    "am_check_optimisation_pass_scope",
    "am_check_optimisation_proposal_prices",
    "am_require_optimisation_proposals",
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


def _scope(connection: Any, ids: dict[str, str], *, suffix: str, section: str = "AR") -> dict[str, str]:
    """A document with a classified version and a run, in ``ids['project']``."""
    scope = {
        f"document{suffix}": str(DocumentUid.new()),
        f"version{suffix}": str(VersionUid.new()),
        f"run{suffix}": str(RunId.new()),
    }
    connection.execute(
        text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'АР')"),
        {"d": scope[f"document{suffix}"], "p": ids["project"]},
    )
    connection.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
            "byte_size, sha256, page_count) VALUES (:v, :d, 1, 'application/pdf', 1024, :sha, 1)"
        ),
        {"v": scope[f"version{suffix}"], "d": scope[f"document{suffix}"], "sha": "c" * 64},
    )
    connection.execute(
        text(
            "INSERT INTO document_version_classification (version_uid, project_stage, "
            "section_code, confirmed_by_user_uid) VALUES (:v, 'R', :section, :u)"
        ),
        {"v": scope[f"version{suffix}"], "section": section, "u": ids["expert"]},
    )
    connection.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, "
            "prompt_bundle_id, provider_mode, frozen_input_digest) "
            "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"
        ),
        {
            "r": scope[f"run{suffix}"],
            "p": ids["project"],
            "v": scope[f"version{suffix}"],
            "ap": str(AnalysisProfileId.new()),
            "pb": str(PromptBundleId.new()),
            "s": "a" * 64,
        },
    )
    return scope


def _price_list(connection: Any, ids: dict[str, str], uid: str, project: str, number: int,
                positions: tuple[tuple[str, str, str], ...]) -> None:
    connection.execute(
        text(
            "INSERT INTO price_list_revision (price_list_id, project_uid, revision_number, "
            "uploaded_by_user_uid, blob_id, sha256, size_bytes, media_type, source_format, "
            "source_filename, default_currency, parse_report, data_row_count, accepted_row_count, "
            "skipped_row_count) VALUES (:id, :project, :number, :user, :blob, :sha, 2048, "
            "'text/csv', 'csv', 'прайс.csv', 'RUB', CAST('{}' AS jsonb), :n, :n, 0)"
        ),
        {"id": uid, "project": project, "number": number, "user": ids["expert"], "blob": ids["blob"],
         "sha": SHA, "n": len(positions)},
    )
    for row, (position, price, vendor) in enumerate(positions, start=2):
        connection.execute(
            text(
                "INSERT INTO price_list_position (price_list_position_id, price_list_id, row_number, "
                "name, unit, unit_price, currency, vendor) VALUES (:id, :list, :row, "
                "'Дверь противопожарная', 'шт', CAST(:price AS numeric), 'RUB', :vendor)"
            ),
            {"id": position, "list": uid, "row": row, "price": price, "vendor": vendor},
        )


def _vendor_list(connection: Any, ids: dict[str, str], uid: str, *, scope: str = "global",
                 project: str | None = None, section: str = "AR", mode: str = "list",
                 number: int = 1) -> None:
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


def _seed_0026(connection: Any) -> dict[str, str]:
    ids = {"project": str(ProjectUid.new()), "other_project": str(ProjectUid.new())}
    ids["expert"] = _user(connection)
    ids["admin"] = _user(connection)
    for key in ("project", "other_project"):
        connection.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Школа')"),
                           {"p": ids[key]})
    ids.update(_scope(connection, ids, suffix=""))
    ids.update(_scope(connection, ids, suffix="_kj", section="KJ"))
    ids.update(_scope(connection, ids, suffix="_second"))
    blob = str(derive_blob_id(sha256=SHA, size=2048))
    connection.execute(text("INSERT INTO blob (blob_id) VALUES (:b)"), {"b": blob})
    connection.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :b"), {"b": blob})
    connection.execute(
        text("UPDATE blob SET state = 'available', sha256 = :sha, size_bytes = 2048, "
             "media_type = 'text/csv' WHERE blob_id = :b"),
        {"b": blob, "sha": SHA},
    )
    ids["blob"] = blob
    _price_list(connection, ids, PRICE_LIST, ids["project"], 1,
                ((MATCHED, "25000", "Промет"), (CHEAPER, "21000.5", "Кнауф")))
    _price_list(connection, ids, OTHER_PRICE_LIST, ids["other_project"], 1,
                ((FOREIGN_POSITION, "100", "Кнауф"),))
    _vendor_list(connection, ids, VENDOR_LIST)
    _vendor_list(connection, ids, "vnl_01ARZ3NDEKTSV4RRFFQ69G5FKJ", section="KJ")
    _vendor_list(connection, ids, "vnl_01ARZ3NDEKTSV4RRFFQ69G5FPR", scope="project",
                 project=ids["project"])
    _vendor_list(connection, ids, "vnl_01ARZ3NDEKTSV4RRFFQ69G5FNH", scope="project",
                 project=ids["project"], mode="inherit", number=2)
    _vendor_list(connection, ids, "vnl_01ARZ3NDEKTSV4RRFFQ69G5FXT", scope="project",
                 project=ids["other_project"])
    return ids


def _pass(connection: Any, ids: dict[str, str], uid: str = PASS, *, proposals: int = 1,
          **overrides: Any) -> None:
    values = {
        "id": uid,
        "project": ids["project"],
        "document": ids["document"],
        "version": ids["version"],
        "run": ids["run"],
        "layer": "e" * 64,
        "price_list": PRICE_LIST,
        "vendor_list": VENDOR_LIST,
        "source": "global",
        "extraction": "specification-text-v1",
        "match": "price-match-v1",
        "generator": "cheaper-analog-v1",
        "rows": 3,
        "matched": 2,
        "proposed": 1 if proposals else 0,
        "count": proposals,
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
            ":price_list, :vendor_list, :source, :extraction, :match, :generator, :rows, "
            ":matched, :proposed, :count, :user)"
        ),
        values,
    )


def _proposal(connection: Any, uid: str = PROPOSAL, pass_id: str = PASS, **overrides: Any) -> None:
    values = {
        "id": uid,
        "pass": pass_id,
        "ordinal": 1,
        "type": "cheaper_analog",
        "key": "sr-" + "a" * 32,
        "page": 1,
        "sheet": "10",
        "start": 3,
        "end": 3,
        "table": 1,
        "position": "1",
        "text": "Дверь противопожарная ДПМ-01/60",
        "matched": MATCHED,
        "matched_basis": "mark",
        "proposed": CHEAPER,
        "analog_basis": "code_family",
        "similarity": "1",
        "vendor": "Кнауф",
        "unit": "шт",
        "quantity": "4",
        "quantity_text": "4",
        "current": "25000",
        "price": "21000.5",
        "currency": "RUB",
        "saving": "15998",
        "rationale": "Более дешёвый аналог",
    }
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO optimisation_proposal (optimisation_proposal_id, optimisation_pass_id, "
            "ordinal, proposal_type, spec_row_key, page_number, sheet_label, line_start, line_end, "
            "table_ordinal, row_position, row_text, matched_position_id, matched_basis, "
            "proposed_position_id, analog_basis, name_similarity, proposed_vendor, unit, quantity, "
            "quantity_text, current_unit_price, proposed_unit_price, currency, saving, rationale) "
            "VALUES (:id, :pass, :ordinal, :type, :key, :page, :sheet, :start, :end, :table, "
            ":position, :text, :matched, :matched_basis, :proposed, :analog_basis, "
            "CAST(:similarity AS numeric), :vendor, :unit, CAST(:quantity AS numeric), "
            ":quantity_text, CAST(:current AS numeric), CAST(:price AS numeric), :currency, "
            "CAST(:saving AS numeric), :rationale)"
        ),
        values,
    )


def _command(connection: Any) -> str:
    command = str(CommandId.new())
    connection.execute(
        text(
            "INSERT INTO command_record (command_id, command_type, idempotency_key, "
            "payload_fingerprint) VALUES (:c, 'decide_optimisation_proposal', :k, :f)"
        ),
        {"c": command, "k": command.lower(), "f": "f" * 64},
    )
    return command


def _decision(connection: Any, uid: str = DECISION, **overrides: Any) -> None:
    values = {
        "id": uid,
        "proposal": PROPOSAL,
        "seq": 1,
        "verdict": "accept",
        "comment": None,
        "actor": None,
        "command": None,
    }
    values.update(overrides)
    if values["command"] is None:
        values["command"] = _command(connection)
    connection.execute(
        text(
            "INSERT INTO optimisation_proposal_decision (proposal_decision_id, "
            "optimisation_proposal_id, seq, verdict, comment, actor_user_uid, command_id) "
            "VALUES (:id, :proposal, :seq, :verdict, :comment, :actor, :command)"
        ),
        values,
    )


def _refused(engine: Engine, write: Any, *, sqlstate: str | set[str]) -> None:
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    expected = {sqlstate} if isinstance(sqlstate, str) else sqlstate
    assert _sqlstate(caught.value) in expected, caught.value


@pytest.fixture
def at_previous(
    empty_database: Any, foundation_command: Any
) -> Iterator[tuple[Engine, str, dict[str, str]]]:
    url = empty_database.url.render_as_string(hide_password=False)
    upgraded = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert upgraded.returncode == 0, upgraded.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = _seed_0026(connection)
        yield engine, url, ids
    finally:
        engine.dispose()


@pytest.fixture
def at_head(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> tuple[Engine, str, dict[str, str]]:
    engine, url, ids = at_previous
    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()
    return engine, url, ids


_SNAPSHOT = (
    "SELECT (SELECT count(*) FROM project), (SELECT count(*) FROM document), "
    "(SELECT count(*) FROM document_version), (SELECT count(*) FROM audit_run), "
    "(SELECT string_agg(price_list_position_id || '=' || unit_price::text, ',' "
    " ORDER BY price_list_position_id) FROM price_list_position), "
    "(SELECT count(*) FROM vendor_list_revision), (SELECT count(*) FROM vendor_list_entry), "
    "(SELECT count(*) FROM document_version_classification), (SELECT count(*) FROM command_record)"
)


def test_populated_0026_upgrades_and_no_existing_row_changes(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, _ = at_previous
    with engine.connect() as connection:
        for table in TABLES:
            assert connection.execute(text(f"SELECT to_regclass('{table}')")).scalar_one() is None
        before = tuple(connection.execute(text(_SNAPSHOT)).one())

    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        for table in TABLES:
            assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
        after = tuple(connection.execute(text(_SNAPSHOT)).one())
    assert after == before
    assert before[4] == f"{MATCHED}=25000,{CHEAPER}=21000.5,{FOREIGN_POSITION}=100"


def test_a_complete_pass_commits_and_every_table_refuses_update_and_delete(
    at_head: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        _pass(connection, ids)
        _proposal(connection)
        _decision(connection, actor=ids["expert"])
        _decision(connection, OTHER_DECISION, seq=2, verdict="revise", comment="уточнить",
                  actor=ids["admin"])
    for table, assignment in (
        ("optimisation_pass", "proposal_count = proposal_count"),
        ("optimisation_proposal", "rationale = rationale"),
        ("optimisation_proposal_decision", "verdict = verdict"),
    ):
        _refused(engine, lambda c, t=table, a=assignment: c.execute(text(f"UPDATE {t} SET {a}")),
                 sqlstate="AM003")
        _refused(engine, lambda c, t=table: c.execute(text(f"DELETE FROM {t}")), sqlstate="AM003")


def test_a_pass_without_all_its_proposals_is_refused_at_commit(
    at_head: tuple[Engine, str, dict[str, str]],
) -> None:
    engine, _, ids = at_head

    def two_declared_one_written(connection: Any) -> None:
        _pass(connection, ids, proposals=2)
        _proposal(connection)

    _refused(engine, two_declared_one_written, sqlstate="AM001")
    with engine.begin() as connection:  # an empty pass declares none and needs none
        _pass(connection, ids, proposals=0)


@pytest.mark.parametrize(
    "overrides",
    [
        {"document": "DOCUMENT_KJ"},  # another document's ... with this version
        {"version": "VERSION_SECOND"},  # a version of another document
        {"run": "RUN_SECOND"},  # a run of another version
        {"document": "DOCUMENT_KJ", "version": "VERSION_KJ", "run": "RUN_KJ"},  # classified KJ
        {"project": "OTHER_PROJECT"},  # the document is not in that project
        {"price_list": OTHER_PRICE_LIST},  # another project's price list
        {"vendor_list": "vnl_01ARZ3NDEKTSV4RRFFQ69G5FKJ"},  # another section's list
        {"vendor_list": "vnl_01ARZ3NDEKTSV4RRFFQ69G5FNH", "source": "project"},  # inherit
        {"vendor_list": "vnl_01ARZ3NDEKTSV4RRFFQ69G5FXT", "source": "project"},  # another project
        {"vendor_list": "vnl_01ARZ3NDEKTSV4RRFFQ69G5FPR", "source": "global"},  # wrong source
        {"source": "project"},  # the global list recorded as the project's
    ],
)
def test_a_pass_outside_one_consistent_scope_is_refused(
    at_head: tuple[Engine, str, dict[str, str]], overrides: dict[str, str]
) -> None:
    engine, _, ids = at_head
    resolved = {
        key: ids[value.lower()] if value.isupper() and value.lower() in ids else value
        for key, value in overrides.items()
    }

    def write(connection: Any) -> None:
        _pass(connection, ids, proposals=0, **resolved)

    _refused(engine, write, sqlstate="AM001")


def test_the_project_override_list_is_a_valid_scope(at_head: tuple[Engine, str, dict[str, str]]) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        _pass(connection, ids, proposals=0, vendor_list="vnl_01ARZ3NDEKTSV4RRFFQ69G5FPR", source="project")


@pytest.mark.parametrize(
    "overrides",
    [
        {"current": "25001", "saving": "16002"},  # not the matched position's price
        {"price": "21000", "saving": "16000"},  # not the proposed position's price
        {"vendor": "Промет"},  # not the proposed position's vendor
        {"proposed": FOREIGN_POSITION, "price": "100", "saving": "99600"},  # another price list
        {"currency": "EUR"},  # not the positions' currency
    ],
)
def test_a_proposal_must_take_its_money_from_its_positions(
    at_head: tuple[Engine, str, dict[str, str]], overrides: dict[str, str]
) -> None:
    engine, _, ids = at_head

    def write(connection: Any) -> None:
        _pass(connection, ids)
        _proposal(connection, **overrides)

    _refused(engine, write, sqlstate="AM001")


@pytest.mark.parametrize(
    ("table", "overrides"),
    [
        ("pass", {"id": "opp_short"}),
        ("pass", {"id": "opr_01ARZ3NDEKTSV4RRFFQ69G5FAV"}),
        ("pass", {"layer": "E" * 64}),
        ("pass", {"source": "team"}),
        ("pass", {"generator": "Cheaper Analog"}),
        ("pass", {"generator": ""}),
        ("pass", {"matched": 4}),  # more matched rows than rows
        ("pass", {"rows": 10001, "matched": 0, "proposed": 0, "count": 0}),
        ("pass", {"user": "usr_bad"}),
        ("proposal", {"id": "opr_bad"}),
        ("proposal", {"ordinal": 0}),
        ("proposal", {"type": "faster_install"}),
        ("proposal", {"key": "sr-xyz"}),
        ("proposal", {"page": 0}),
        ("proposal", {"start": 4, "end": 3}),
        ("proposal", {"table": 0}),
        ("proposal", {"text": ""}),
        ("proposal", {"text": "я" * 8001}),
        ("proposal", {"sheet": ""}),
        ("proposal", {"position": "x" * 101}),
        ("proposal", {"matched_basis": "fuzzy"}),
        ("proposal", {"analog_basis": "llm"}),
        ("proposal", {"similarity": "1.5"}),
        ("proposal", {"similarity": "0.12345"}),
        ("proposal", {"proposed": MATCHED, "price": "25000", "vendor": "Промет"}),  # itself
        ("proposal", {"unit": ""}),
        ("proposal", {"quantity": "-1", "saving": "-3999.5"}),
        ("proposal", {"saving": None}),  # a numeric quantity without its saving
        ("proposal", {"quantity": None, "saving": "15998"}),  # a saving without a quantity
        ("proposal", {"quantity": None, "saving": "0"}),  # absent is never 0
        ("proposal", {"saving": "15998.01"}),  # not (current - proposed) x quantity
        ("proposal", {"current": "21000.5", "saving": "0"}),  # not cheaper
        ("proposal", {"rationale": ""}),
        ("decision", {"id": "opd_bad"}),
        ("decision", {"seq": 0}),
        ("decision", {"verdict": "pending"}),
        ("decision", {"verdict": "revise", "comment": None}),
        ("decision", {"comment": ""}),
        ("decision", {"comment": "я" * 2001}),
        ("decision", {"actor": "usr_bad"}),
    ],
)
def test_the_checks_refuse_malformed_rows(
    at_head: tuple[Engine, str, dict[str, str]], table: str, overrides: dict[str, Any]
) -> None:
    engine, _, ids = at_head

    def write(connection: Any) -> None:
        if table == "pass":
            _pass(connection, ids, proposals=0, **{"proposed": 0, **overrides})
        elif table == "proposal":
            _pass(connection, ids)
            _proposal(connection, **overrides)
        else:
            _pass(connection, ids)
            _proposal(connection)
            _decision(connection, **{"actor": ids["expert"], **overrides})

    _refused(engine, write, sqlstate={"23514", "AM001", "23503"})


def test_well_formed_rows_at_their_bounds_are_admitted(at_head: tuple[Engine, str, dict[str, str]]) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        _pass(connection, ids, proposals=2)
        _proposal(connection, text="я" * 8000, sheet=None, position=None, similarity="0.6666",
                  quantity=None, quantity_text=None, saving=None, rationale="я" * 10000)
        _proposal(connection, OTHER_PROPOSAL, ordinal=2, key="sr-" + "b" * 32, quantity="0",
                  saving="0", analog_basis="name_similarity", matched_basis="name")
        _decision(connection, actor=ids["expert"], verdict="revise", comment="я" * 2000)
        _decision(connection, OTHER_DECISION, actor=ids["expert"], verdict="reject", seq=2)
    with engine.connect() as connection:
        savings = connection.execute(
            text("SELECT saving::text FROM optimisation_proposal ORDER BY ordinal")
        ).scalars().all()
    assert savings == [None, "0"]


def test_uniqueness_inputs_ordinals_seq_and_commands(at_head: tuple[Engine, str, dict[str, str]]) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        _pass(connection, ids)
        _proposal(connection)
        command = _command(connection)
        _decision(connection, actor=ids["expert"], command=command)

    _refused(engine, lambda c: _pass(c, ids, OTHER_PASS, proposals=0), sqlstate="23505")

    def same_row_and_position(connection: Any) -> None:
        _pass(connection, ids, OTHER_PASS, proposals=2, generator="cheaper-analog-v2")
        _proposal(connection, pass_id=OTHER_PASS)
        _proposal(connection, OTHER_PROPOSAL, pass_id=OTHER_PASS, ordinal=2)

    _refused(engine, same_row_and_position, sqlstate="23505")
    _refused(engine, lambda c: _decision(c, OTHER_DECISION, actor=ids["expert"]), sqlstate="23505")
    _refused(engine, lambda c: _decision(c, OTHER_DECISION, seq=2, actor=ids["expert"], command=command),
             sqlstate="23505")
    with engine.begin() as connection:  # another generator version is another pass
        _pass(connection, ids, OTHER_PASS, proposals=0, generator="cheaper-analog-v2")


@pytest.mark.parametrize("column", ["started_by_user_uid", "actor_user_uid"])
def test_each_account_column_alone_blocks_deleting_the_account(
    at_head: tuple[Engine, str, dict[str, str]], column: str
) -> None:
    engine, _, ids = at_head
    with engine.begin() as connection:
        holder = _user(connection)
        if column == "started_by_user_uid":
            _pass(connection, ids, proposals=0, user=holder)
        else:
            _pass(connection, ids)
            _proposal(connection)
            _decision(connection, actor=holder)
    _refused(
        engine,
        lambda connection: connection.execute(text("DELETE FROM app_user WHERE user_uid = :u"),
                                              {"u": holder}),
        sqlstate="23503",
    )


def test_the_downgrade_drops_only_this_revision_and_the_head_upgrades_again(
    at_head: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, ids = at_head
    with engine.begin() as connection:
        _pass(connection, ids)
        _proposal(connection)
        _decision(connection, actor=ids["expert"])
        before = tuple(connection.execute(text(_SNAPSHOT)).one())

    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    assert "exist nowhere else and are dropped" in downgraded.stderr + downgraded.stdout

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        for table in TABLES:
            assert connection.execute(text(f"SELECT to_regclass('{table}')")).scalar_one() is None
        for function in FUNCTIONS:
            assert connection.execute(
                text("SELECT count(*) FROM pg_proc WHERE proname = :f"), {"f": function}
            ).scalar_one() == 0
        assert connection.execute(
            text("SELECT count(*) FROM pg_proc WHERE proname = 'am_require_price_list_positions'")
        ).scalar_one() == 1
        # Every 0026 row stays, the decision's command record included.
        assert tuple(connection.execute(text(_SNAPSHOT)).one()) == before

    reupgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert reupgraded.returncode == 0, reupgraded.describe()
    with engine.connect() as connection:
        for table in TABLES:
            assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
