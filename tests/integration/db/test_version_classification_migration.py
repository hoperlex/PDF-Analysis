"""`W59-SECTION-SEAL-01`: ``0024_version_classification`` on a populated ``0023`` database.

What the decision's test 2 asks of the forward path, against real PostgreSQL rows written at
``0023`` -- a project, a document carrying the legacy ``section`` ``AR``, a published version
and a run pinned to a profile:

* the upgrade leaves every version unclassified: no row is fabricated from the legacy
  ``document.section``, the file name or the current head;
* the version's bytes record (``sha256``), the document's ``section`` and the run's pinned
  profile, bundle and ``frozen_input_digest`` are unchanged;
* the classification is append-only (``AM003`` on UPDATE and DELETE), one row per version,
  checked against the fifteen sections and ``P``/``R``, and its confirmer is a RESTRICT
  reference to ``app_user``;
* ``document.section`` now admits ``PS``, which ``0011``'s CHECK refused;
* the downgrade drops only the new table and restores the fourteen-code CHECK, ``NOT VALID``
  while a ``PS`` document exists, so no document row is deleted or rewritten.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

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

HEAD = "0024_version_classification"  # this revision, not the tree's head: every upgrade here targets it
PREVIOUS = "0023_norm_citations"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _seed_0023(connection: Any) -> dict[str, str]:
    """One legacy-classified document with a version and a pinned run, written at 0023."""
    ids = {
        "project": str(ProjectUid.new()),
        "document": str(DocumentUid.new()),
        "version": str(VersionUid.new()),
        "run": str(RunId.new()),
        "profile": str(AnalysisProfileId.new()),
        "bundle": str(PromptBundleId.new()),
    }
    connection.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'legacy')"), ids
    )
    connection.execute(
        text(
            "INSERT INTO document (document_uid, project_uid, display_title, section) "
            "VALUES (:document, :project, 'СП-7-АР', 'AR')"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
            "source_filename, media_type, byte_size, sha256, page_count) "
            "VALUES (:version, :document, 1, 'СП-7-АР.pdf', 'application/pdf', 1024, :sha, 1)"
        ),
        {**ids, "sha": "a" * 64},
    )
    connection.execute(
        text(
            "UPDATE document SET current_version_uid = :version WHERE document_uid = :document"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, "
            "prompt_bundle_id, provider_mode, frozen_input_digest) "
            "VALUES (:run, :project, :version, :profile, :bundle, 'recorded', :digest)"
        ),
        {**ids, "digest": "b" * 64},
    )
    return ids


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


def _classify(connection: Any, version: str, user: str, *, stage: str = "R", code: str = "KJ") -> None:
    connection.execute(
        text(
            "INSERT INTO document_version_classification "
            "(version_uid, project_stage, section_code, confirmed_by_user_uid) "
            "VALUES (:v, :stage, :code, :u)"
        ),
        {"v": version, "stage": stage, "code": code, "u": user},
    )


def _sqlstate(error: DBAPIError) -> str:
    return str(getattr(error.orig, "sqlstate", "") or "")


@pytest.fixture
def at_previous(empty_database: Any, foundation_command: Any) -> Iterator[tuple[Engine, str, dict[str, str]]]:
    url = empty_database.url.render_as_string(hide_password=False)
    upgraded = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert upgraded.returncode == 0, upgraded.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            ids = _seed_0023(connection)
        yield engine, url, ids
    finally:
        engine.dispose()


def test_populated_0023_upgrades_without_fabricating_a_classification(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, ids = at_previous
    with engine.begin() as connection:
        refused = connection.execute(
            text("SELECT to_regclass('document_version_classification')")
        ).scalar_one()
        assert refused is None, "0023 must not have the table yet"
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text("UPDATE document SET section = 'PS' WHERE document_uid = :document"),
                    ids,
                )

    upgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert upgraded.returncode == 0, upgraded.describe()

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        assert connection.execute(
            text("SELECT count(*) FROM document_version_classification")
        ).scalar_one() == 0
        version = connection.execute(
            text("SELECT sha256, source_filename FROM document_version WHERE version_uid = :version"),
            ids,
        ).one()
        assert tuple(version) == ("a" * 64, "СП-7-АР.pdf")
        assert connection.execute(
            text("SELECT section FROM document WHERE document_uid = :document"), ids
        ).scalar_one() == "AR"
        run = connection.execute(
            text(
                "SELECT analysis_profile_id, prompt_bundle_id, frozen_input_digest "
                "FROM audit_run WHERE run_id = :run"
            ),
            ids,
        ).one()
        assert tuple(run) == (ids["profile"], ids["bundle"], "b" * 64)


def test_the_classification_is_append_only_and_checked(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, ids = at_previous
    assert foundation_command(_alembic("upgrade", HEAD), url).returncode == 0
    with engine.begin() as connection:
        user = _user(connection)
        _classify(connection, ids["version"], user)
        connection.execute(
            text("UPDATE document SET section = 'PS' WHERE document_uid = :document"), ids
        )

    with engine.connect() as connection:
        for statement in (
            "UPDATE document_version_classification SET section_code = 'AR' WHERE version_uid = :version",
            "DELETE FROM document_version_classification WHERE version_uid = :version",
        ):
            with pytest.raises(DBAPIError) as refused:
                with connection.begin():
                    connection.execute(text(statement), ids)
            assert _sqlstate(refused.value) == "AM003", statement
        with pytest.raises(IntegrityError) as duplicate:
            with connection.begin():
                _classify(connection, ids["version"], user, code="AR")
        assert _sqlstate(duplicate.value) == "23505"
        for stage, code in (("X", "KJ"), ("P", "ZZ"), ("P", "ar")):
            with pytest.raises(IntegrityError) as checked:
                with connection.begin():
                    other = _seed_0023(connection)
                    _classify(connection, other["version"], user, stage=stage, code=code)
            assert _sqlstate(checked.value) == "23514", (stage, code)
        with pytest.raises(IntegrityError) as unknown_user:
            with connection.begin():
                _classify(connection, _seed_0023(connection)["version"], str(UserUid.new()))
        assert _sqlstate(unknown_user.value) == "23503"
        with pytest.raises(IntegrityError) as referenced:
            with connection.begin():
                connection.execute(text("DELETE FROM app_user WHERE user_uid = :u"), {"u": user})
        assert _sqlstate(referenced.value) == "23503"
        stored = connection.execute(
            text(
                "SELECT project_stage, section_code, confirmed_by_user_uid "
                "FROM document_version_classification WHERE version_uid = :version"
            ),
            ids,
        ).one()
        assert tuple(stored) == ("R", "KJ", user)


def test_every_current_section_is_admitted_and_ps_is_not_pb(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, _ = at_previous
    assert foundation_command(_alembic("upgrade", HEAD), url).returncode == 0
    current = ("AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS", "PS")
    with engine.begin() as connection:
        user = _user(connection)
        for index, code in enumerate(current):
            seeded = _seed_0023(connection)
            _classify(connection, seeded["version"], user, stage="PR"[index % 2], code=code)
        stored = connection.execute(
            text("SELECT section_code FROM document_version_classification")
        ).scalars().all()
    assert sorted(stored) == sorted(current) and len(set(stored)) == 15


def test_the_downgrade_drops_only_the_table_and_keeps_a_ps_document(
    at_previous: tuple[Engine, str, dict[str, str]], foundation_command: Any
) -> None:
    engine, url, ids = at_previous
    assert foundation_command(_alembic("upgrade", HEAD), url).returncode == 0
    with engine.begin() as connection:
        _classify(connection, ids["version"], _user(connection))
        connection.execute(
            text("UPDATE document SET section = 'PS' WHERE document_uid = :document"), ids
        )
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        assert connection.execute(
            text("SELECT to_regclass('document_version_classification')")
        ).scalar_one() is None
        assert connection.execute(
            text("SELECT section FROM document WHERE document_uid = :document"), ids
        ).scalar_one() == "PS"
        validated = connection.execute(
            text("SELECT convalidated FROM pg_constraint WHERE conname = 'ck_document_section'")
        ).scalar_one()
        assert validated is False
        assert connection.execute(
            text("SELECT count(*) FROM audit_run WHERE run_id = :run"), ids
        ).scalar_one() == 1
    # NOT VALID still holds every new write to the fourteen: re-writing the PS row is refused.
    with engine.connect() as connection:
        with pytest.raises(IntegrityError):
            with connection.begin():
                connection.execute(
                    text("UPDATE document SET section = 'PS', updated_at = now() WHERE document_uid = :document"),
                    ids,
                )
    reupgraded = foundation_command(_alembic("upgrade", HEAD), url)
    assert reupgraded.returncode == 0, reupgraded.describe()
