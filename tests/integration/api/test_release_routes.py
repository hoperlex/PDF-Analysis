"""The Stage-B release router passes verified identity to its narrow port."""

from __future__ import annotations

import json
import secrets

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas.models import ProductVersion, ReleaseList
from auditmanager.bootstrap.adapters import ReleasesAdapter
from auditmanager.releases.public import ReleaseRepository

from .identity_surface import credential_for, identity_surface, make_account


class _RecordingReleases:
    def __init__(self) -> None:
        self.read_user: str | None = None
        self.mark: tuple[str, str] | None = None

    def get_product_version(self) -> ProductVersion:
        return ProductVersion(
            product_version="0.3.0", build_id="b0123456789abcdef", contract_version="1.0.0-draft.1"
        )

    def list_releases(self, *, user_uid: str) -> ReleaseList:
        self.read_user = user_uid
        return ReleaseList(items=[], whats_new=[])

    def mark_read(self, *, user_uid: str, read_through: str) -> None:
        self.mark = (user_uid, read_through)


def test_admin_without_expert_reads_release_surface_and_marks_only_itself(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    admin = make_account(
        session,
        login=f"release-admin-{secrets.token_hex(4)}@suite.invalid",
        names=("Админова", "Ольга", None),
        roles=("admin",),
    )
    releases = _RecordingReleases()
    surface = identity_surface(session_factory, releases=releases)
    credential = credential_for(session, admin)

    version = surface.send("GET", "/system/version", credential=credential)
    assert version.status == 200
    assert json.loads(version.body) == {
        "product_version": "0.3.0",
        "build_id": "b0123456789abcdef",
        "contract_version": "1.0.0-draft.1",
    }
    listed = surface.send("GET", "/releases", credential=credential)
    assert listed.status == 200
    assert json.loads(listed.body) == {"items": [], "whats_new": []}
    assert releases.read_user == admin

    marked = surface.send(
        "PUT", "/me/release-notes", credential=credential,
        headers={"Content-Type": "application/json"},
        body=b'{"read_through":"0.3.0"}',
    )
    assert marked.status == 204
    assert marked.body == b""
    assert releases.mark == (admin, "0.3.0")


def test_stage_c_adapter_serves_the_running_version_and_visible_history(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    account = make_account(
        session,
        login=f"release-reader-{secrets.token_hex(4)}@suite.invalid",
        names=("Читателева", "Анна", None),
        roles=(),
    )
    adapter = ReleasesAdapter(
        ReleaseRepository(session_factory, product_version="0.3.0"),
        product_version="0.3.0",
        build_id="b0123456789abcdef",
    )
    surface = identity_surface(session_factory, releases=adapter)
    credential = credential_for(session, account)
    version = surface.send("GET", "/system/version", credential=credential)
    assert version.status == 200
    assert json.loads(version.body)["product_version"] == "0.3.0"
    answer = surface.send("GET", "/releases", credential=credential)
    assert answer.status == 200
    body = json.loads(answer.body)
    assert body["whats_new"] == [], "a newly created account has no historical What's New"
    assert [item["version"] for item in body["items"]] in (
        [], ["0.3.0", "0.2.0"]
    ), "the lane DB may be before or after the one-shot loader"
    if body["items"]:
        assert body["items"][-1]["is_archive"] is True
        assert body["items"][0]["range_label"] is None
