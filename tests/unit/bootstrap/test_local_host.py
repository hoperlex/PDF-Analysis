"""`LOCAL-AGENT-01`: ``python -m auditmanager.bootstrap.local_host`` -- the stand's half of ``infra/deploy/local-agent.sh``.

The database is not needed here: the session factory and the hosts service are replaced by recording fakes; what is checked is the
actor rule, the one-line JSON shape the script reads, and the exit codes. The real issue path (``issue_host_enrollment``) has its own
database tests.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from auditmanager.bootstrap import local_host
from auditmanager.shared.errors import DomainError, ErrorCode


@dataclass(frozen=True)
class _Record:
    user_uid: str
    login: str
    created_at: datetime
    archived_at: datetime | None = None


def _account(uid: str, login: str, day: int, roles=("admin",), archived=None):
    return SimpleNamespace(record=_Record(uid, login, datetime(2026, 11, day, tzinfo=timezone.utc), archived), roles=frozenset(roles))


ACCOUNTS = [
    _account("usr_03", "late-admin", 9),
    _account("usr_01", "expert", 1, roles=("expert",)),
    _account("usr_02", "first-admin", 2),
    _account("usr_00", "gone-admin", 1, archived=datetime(2026, 11, 3, tzinfo=timezone.utc)),
]


def test_the_actor_is_the_named_active_administrator_or_else_the_one_created_first():
    assert local_host.choose_actor(ACCOUNTS, None).login == "first-admin"
    assert local_host.choose_actor(ACCOUNTS, "late-admin").login == "late-admin"
    with pytest.raises(local_host.Refused, match="no active administrator with the login 'expert'"):
        local_host.choose_actor(ACCOUNTS, "expert")
    with pytest.raises(local_host.Refused, match="no active administrator with the login 'gone-admin'"):
        local_host.choose_actor(ACCOUNTS, "gone-admin")
    with pytest.raises(local_host.Refused, match="has no active administrator"):
        local_host.choose_actor([ACCOUNTS[1]], None)


class _FakeService:
    calls: list = []
    listing: dict = {"items": []}

    def __init__(self, *, session_factory, public_origin=None, ring=None):
        _FakeService.calls.append(("init", public_origin))

    def list_hosts(self):
        return _FakeService.listing

    def issue_enrollment(self, *, display_name, user_uid, idempotency_key):
        _FakeService.calls.append(("issue", display_name, user_uid, idempotency_key))
        return {"secret": "ame_abcdefgh_" + "x" * 43, "package_version": "0.33.0", "package_sha256": "a" * 64,
                "command": "not used", "enrollment": {"host_id": "exh_01", "state": "issued"}}


@pytest.fixture
def fakes(monkeypatch):
    _FakeService.calls = []
    _FakeService.listing = {"items": []}
    import auditmanager.access.public as access_public
    import auditmanager.bootstrap.hosts_service as hosts_service

    monkeypatch.setattr(hosts_service, "HostsService", _FakeService)

    class _Accounts:
        def list_accounts(self, session, include_archived=False):
            assert include_archived is False
            return ACCOUNTS

    monkeypatch.setattr(access_public, "AccountRepository", _Accounts)

    @contextmanager
    def session():
        yield object()

    return lambda: session


def test_enroll_issues_the_grant_in_the_name_of_the_first_administrator_and_returns_the_secret_once(fakes):
    line = local_host.run(["enroll", "--origin", "http://127.0.0.1:8088"], session_factory=fakes)
    assert line == {"secret": "ame_abcdefgh_" + "x" * 43, "host_id": "exh_01", "package_version": "0.33.0",
                    "package_sha256": "a" * 64, "actor_login": "first-admin"}
    init, issue = _FakeService.calls
    assert init == ("init", "http://127.0.0.1:8088"), "the grant's command names the loopback origin the agent uses"
    assert issue[1] == local_host.DEFAULT_NAME == "Этот сервер" and issue[2] == "usr_02"
    assert issue[3].startswith("local-agent-") and len(issue[3]) <= 128


def test_enroll_takes_the_name_and_the_actor_given(fakes):
    local_host.run(["enroll", "--origin", "http://127.0.0.1:8088", "--name", "kz deploy", "--actor", "late-admin"], session_factory=fakes)
    assert _FakeService.calls[-1][1:3] == ("kz deploy", "usr_03")


def test_show_finds_the_live_card_by_name_case_blind_and_ignores_an_archived_one(fakes):
    seen = datetime(2026, 11, 20, 1, 0, tzinfo=timezone.utc)
    _FakeService.listing = {"items": [
        {"host_id": "exh_old", "display_name": "Этот сервер", "archived_at": seen},
        {"host_id": "exh_01", "display_name": "ЭТОТ СЕРВЕР", "enabled": True, "state": "online", "last_seen_at": seen,
         "models": [{"provider": "codex", "model_id": "gpt-6-sol", "access": "subscription", "state": "available"}]},
    ]}
    line = local_host.run(["show"], session_factory=fakes)
    assert line["host"]["host_id"] == "exh_01" and line["host"]["last_seen_at"] == seen.isoformat()
    json.dumps(line)  # the line is JSON as it is
    _FakeService.listing = {"items": []}
    assert local_host.run(["show", "--name", "other"], session_factory=fakes) == {"host": None}


def test_main_prints_one_json_line_and_maps_refusals_to_exit_3(fakes, monkeypatch, capsys):
    monkeypatch.setattr(local_host, "_default_factory", fakes)
    assert local_host.main(["enroll", "--origin", "http://127.0.0.1:8088"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1 and json.loads(out)["actor_login"] == "first-admin"

    def refuse(self, **kwargs):
        raise DomainError(ErrorCode.CONFLICT, message="m", conflict_reason="upgrade_blocked_by_use")

    monkeypatch.setattr(_FakeService, "issue_enrollment", refuse)
    assert local_host.main(["enroll", "--origin", "http://127.0.0.1:8088"]) == 3
    captured = capsys.readouterr()
    assert captured.out == "" and "refused: conflict upgrade_blocked_by_use" in captured.err
    assert local_host.main(["enroll", "--origin", "http://127.0.0.1:8088", "--actor", "expert"]) == 3
    assert local_host.main(["nonsense"]) == 2
    assert local_host.main(["enroll"]) == 2, "the origin is required"


def test_package_reads_the_package_the_stand_serves(monkeypatch):
    package = SimpleNamespace(version="0.33.0", sha256="b" * 64)
    import auditmanager.executors.public as executors_public

    monkeypatch.setattr(executors_public, "latest_package", lambda: package)
    assert local_host.run(["package"], session_factory=lambda: None) == {"package_version": "0.33.0", "package_sha256": "b" * 64}
