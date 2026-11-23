"""`LOCAL-AGENT-01` on PostgreSQL: ``python -m auditmanager.bootstrap.local_host`` issues the deploy server's grant as «Подключить сервер» does.

The module is what ``infra/deploy/local-agent.sh`` runs inside the ``api`` container. Here it runs against a migrated database with a real
agent package built by ``tools/executor-runner/package.py`` (the directory the image would hold), so the grant, the host, its «Использовать»
event and the actor are the database's own. The script's half (the download, ``install.sh --login-user``) is covered by the unit tests of the
installer and of ``local_agent_clis.py``; nothing here installs anything.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.bootstrap import local_host
from auditmanager.executors import public as ex
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.errors import DomainError

ROOT = Path(__file__).resolve().parents[3]
ORIGIN = "http://127.0.0.1:18088"
_RUN = uuid.uuid4().hex[:10]


@pytest.fixture(scope="module")
def local_engine() -> Iterator[Engine]:
    """Its own engine from ``DATABASE_URL`` (the suite's harness needs the whole application importable; this module does not)."""
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set: this suite runs against a migrated PostgreSQL and never skips.")
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    try:
        yield built
    finally:
        built.dispose()


@pytest.fixture
def sessions(local_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=local_engine, expire_on_commit=False, future=True)


@pytest.fixture(scope="module")
def package_dir(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("agent-package")
    version = (ROOT / "VERSION").read_text().strip()
    built = subprocess.run([sys.executable, str(ROOT / "tools/executor-runner/package.py"), "--version", version, "--out", str(out)],
                           capture_output=True, text=True, timeout=60)
    assert built.returncode == 0, built.stderr
    return out


@pytest.fixture
def admin(sessions: sessionmaker[Session]) -> str:
    login = f"local-agent-{_RUN}-{uuid.uuid4().hex[:6]}"
    with sessions() as s:
        uid = str(UserRepository().create_user(s, login, "local-agent-test-password").user_uid)
        AccountRepository().grant_role(s, user_uid=uid, role="admin", granted_by=None)
        s.commit()
    return login


@pytest.fixture
def name() -> str:
    return f"Этот сервер {_RUN}-{uuid.uuid4().hex[:4]}"


@pytest.fixture(autouse=True)
def _package_and_cleanup(monkeypatch, package_dir: Path, sessions: sessionmaker[Session]) -> Iterator[None]:
    monkeypatch.setenv("AUDITMANAGER_AGENT_PACKAGE_DIR", str(package_dir))
    yield
    with sessions() as s:
        actor = s.execute(text(
            "SELECT u.user_uid FROM app_user u JOIN app_user_role r ON r.user_uid = u.user_uid AND r.role = 'admin' "
            "WHERE u.archived_at IS NULL ORDER BY u.created_at LIMIT 1")).scalar_one()
        for host in ex.read_hosts(s):
            if host.record.display_name.startswith(f"Этот сервер {_RUN}"):
                ex.archive_host(s, host_id=host.record.host_id, roles=("admin",), idempotency_key=f"local-cleanup-{uuid.uuid4().hex}",
                                actor_uid=str(actor))
        s.commit()


def _run(sessions: sessionmaker[Session], *argv: str) -> dict:
    return local_host.run(list(argv), session_factory=lambda: sessions)


def test_enroll_creates_the_card_enabled_and_issues_a_grant_the_database_holds_only_as_a_hash(
    sessions: sessionmaker[Session], admin: str, name: str,
) -> None:
    line = _run(sessions, "enroll", "--name", name, "--origin", ORIGIN, "--actor", admin)
    assert line["actor_login"] == admin and line["secret"].startswith("ame_")
    assert line["package_version"] == (ROOT / "VERSION").read_text().strip() and len(line["package_sha256"]) == 64
    with sessions() as s:
        stored = s.execute(text("SELECT secret_hash, host_id, created_by FROM executor_enrollment WHERE host_id = :h"),
                           {"h": line["host_id"]}).one()
        actor_uid = s.execute(text("SELECT user_uid FROM app_user WHERE login = :l"), {"l": admin}).scalar_one()
    assert line["secret"] not in str(stored.secret_hash) and stored.created_by == actor_uid
    card = _run(sessions, "show", "--name", name)["host"]
    assert card["host_id"] == line["host_id"] and card["enabled"] is True, "owner 2026-11-20: the card is on at once"
    assert card["state"] == "offline" and card.get("models", []) == [], "no agent has reported yet"


def test_a_second_enroll_of_the_same_name_is_a_new_grant_for_the_same_card(sessions: sessionmaker[Session], admin: str, name: str) -> None:
    first = _run(sessions, "enroll", "--name", name, "--origin", ORIGIN, "--actor", admin)
    second = _run(sessions, "enroll", "--name", name.upper(), "--origin", ORIGIN, "--actor", admin)
    assert second["host_id"] == first["host_id"] and second["secret"] != first["secret"]
    with sessions() as s:
        states = s.execute(text("SELECT revoked_at IS NULL FROM executor_enrollment WHERE host_id = :h ORDER BY created_at"),
                           {"h": first["host_id"]}).scalars().all()
    assert states == [False, True], "the earlier unredeemed grant is revoked: only the newest one can be redeemed"


def test_an_archived_card_is_not_shown_and_a_new_enroll_makes_a_new_card(sessions: sessionmaker[Session], admin: str, name: str) -> None:
    first = _run(sessions, "enroll", "--name", name, "--origin", ORIGIN, "--actor", admin)
    with sessions() as s:
        uid = s.execute(text("SELECT user_uid FROM app_user WHERE login = :l"), {"l": admin}).scalar_one()
        ex.archive_host(s, host_id=first["host_id"], roles=("admin",), idempotency_key=f"local-archive-{uuid.uuid4().hex}", actor_uid=str(uid))
        s.commit()
    assert _run(sessions, "show", "--name", name) == {"host": None}
    again = _run(sessions, "enroll", "--name", name, "--origin", ORIGIN, "--actor", admin)
    assert again["host_id"] != first["host_id"]


def test_an_actor_who_is_not_an_administrator_is_refused_and_nothing_is_written(sessions: sessionmaker[Session], name: str) -> None:
    login = f"local-agent-expert-{uuid.uuid4().hex[:6]}"
    with sessions() as s:
        UserRepository().create_user(s, login, "local-agent-test-password")
        s.commit()
    with pytest.raises(local_host.Refused):
        _run(sessions, "enroll", "--name", name, "--origin", ORIGIN, "--actor", login)
    assert _run(sessions, "show", "--name", name) == {"host": None}


def test_without_an_actor_the_first_created_active_administrator_is_used(sessions: sessionmaker[Session], admin: str, name: str) -> None:
    line = _run(sessions, "enroll", "--name", name, "--origin", ORIGIN)
    with sessions() as s:
        first = s.execute(text(
            "SELECT u.login FROM app_user u JOIN app_user_role r ON r.user_uid = u.user_uid AND r.role = 'admin' "
            "WHERE u.archived_at IS NULL ORDER BY u.created_at, u.user_uid LIMIT 1")).scalar_one()
    assert line["actor_login"] == first


def test_an_origin_that_is_not_one_is_refused_before_a_card_is_made(sessions: sessionmaker[Session], admin: str, name: str) -> None:
    with pytest.raises(DomainError):
        _run(sessions, "enroll", "--name", name, "--origin", "http://127.0.0.1:1/x", "--actor", admin)
    assert _run(sessions, "show", "--name", name) == {"host": None}
