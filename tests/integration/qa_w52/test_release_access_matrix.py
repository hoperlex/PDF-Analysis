"""W52 release operations follow the W49 standing register for every account state."""

from __future__ import annotations

import json
import secrets

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas.models import ProductVersion, ReleaseList
from tests.integration.api.identity_surface import credential_for, identity_surface, make_account


class RecordingReleases:
    def __init__(self) -> None:
        self.version_reads = 0
        self.list_users: list[str] = []
        self.marks: list[tuple[str, str]] = []

    def get_product_version(self) -> ProductVersion:
        self.version_reads += 1
        return ProductVersion(
            product_version="0.3.0", build_id="b0123456789abcdef",
            contract_version="1.0.0-draft.1",
        )

    def list_releases(self, *, user_uid: str) -> ReleaseList:
        self.list_users.append(user_uid)
        return ReleaseList(items=[], whats_new=[])

    def mark_read(self, *, user_uid: str, read_through: str) -> None:
        self.marks.append((user_uid, read_through))


def _call_three(surface, credential: str | None):
    return (
        surface.send("GET", "/system/version", credential=credential),
        surface.send("GET", "/releases", credential=credential),
        surface.send(
            "PUT", "/me/release-notes", credential=credential,
            headers={"Content-Type": "application/json"},
            body=b'{"read_through":"0.3.0"}',
        ),
    )


def test_every_complete_role_set_can_read_releases_and_mark_only_its_own_account(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    releases = RecordingReleases()
    surface = identity_surface(session_factory, releases=releases)
    users = []
    for roles in ((), ("expert",), ("admin",), ("expert", "admin")):
        user_uid = make_account(
            session, login=f"qa52-{secrets.token_hex(4)}@suite.invalid",
            names=("Читателева", "Анна", None), roles=roles,
        )
        users.append(user_uid)
        version, listed, marked = _call_three(surface, credential_for(session, user_uid))
        assert (version.status, listed.status, marked.status) == (200, 200, 204), roles
        assert json.loads(version.body)["product_version"] == "0.3.0"
        assert json.loads(listed.body) == {"items": [], "whats_new": []}
        assert marked.body == b""
    assert releases.version_reads == len(users)
    assert releases.list_users == users
    assert releases.marks == [(user_uid, "0.3.0") for user_uid in users]


def test_guest_default_credential_and_incomplete_profile_never_reach_release_port(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    releases = RecordingReleases()
    surface = identity_surface(session_factory, releases=releases)
    default = make_account(
        session, login=f"qa52-default-{secrets.token_hex(4)}@suite.invalid",
        names=("Паролева", "Анна", None), roles=("admin",), default=True,
    )
    incomplete = make_account(
        session, login=f"qa52-legacy-{secrets.token_hex(4)}", names=None,
        roles=("expert",),
    )
    for credential, status, capability in (
        (None, 401, None),
        (credential_for(session, default), 403, "password_changed"),
        (credential_for(session, incomplete), 403, "profile_completed"),
    ):
        for answer in _call_three(surface, credential):
            body = json.loads(answer.body)
            assert answer.status == status, body
            assert body["error_code"] == (
                "authentication_required" if capability is None else "permission_denied"
            )
            if capability is not None:
                assert body["details"] == {"required_capability": capability}
    assert releases.version_reads == 0
    assert releases.list_users == []
    assert releases.marks == []
