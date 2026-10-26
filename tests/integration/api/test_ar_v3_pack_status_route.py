"""`AR-V3-BETA-PACK-STATUS-API-01`: the installed-pack read says what the manifest said, and no more.

Container-free: the adapter is built bare (its session factory is never used, because the read
touches neither the database nor a provider) and the route function is called directly, as
``test_ar_v3_group_review_route.py`` does. The response key sets are asserted exactly, so a key
added to the model later is a red test here rather than a quiet disclosure.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import APIRouter
from pydantic import ValidationError

from auditmanager.analysis.public import resolve_beta_v3_profile
from auditmanager.api.routers.ar_v3_groups import build_ar_v3_group_routes
from auditmanager.api.schemas import models
from auditmanager.api.security import OPERATION_ROLES, ROLE_ADMIN, ROLE_EXPERT
from auditmanager.bootstrap.adapters import RunAdapter
from auditmanager.norms.public import SET_BUILDER_VERSION, SetIdentity
from auditmanager.runs.public import ParsedPackManifest, ReviewAttestation, parse_manifest, seal_manifest
from auditmanager.runs.v3_group import SCOPES, ReviewedScope, TrustedPack
from auditmanager.shared.identity import NormRetrievalSetId

PROFILE = resolve_beta_v3_profile("ap_01M5M28ZCDD8VPSP1BTAEW92YE", "pb_01M5M28ZCDVCR37BX1884JGSPM")
REVIEW = ReviewAttestation(
    reviewer="Test Reviewer", capacity="expert", reviewed_at="2026-10-26",
    decision_ref="TEST-RULING-1", scope_statement="six synthetic scopes, test only",
)
INSTALLED_KEYS = {
    "state", "analysis_profile_id", "prompt_bundle_id", "pack_sha256", "scope_ids", "review",
}
REVIEW_KEYS = {"reviewer", "capacity", "reviewed_at", "decision_ref", "scope_statement"}


def _installed() -> ParsedPackManifest:
    pack = TrustedPack(
        str(PROFILE.analysis_profile_id), str(PROFILE.prompt_bundle_id),
        tuple(
            ReviewedScope(
                scope_id=scope_id,
                identity=SetIdentity(
                    map_sha256=f"{index:x}" * 64, snapshot_id=PROFILE.snapshot_id,
                    reviewed_content_key="ar-v3-beta-synthetic-key",
                    embedding_build="bge-m3-dense-v1:characters-v2:1200",
                    builder_version=SET_BUILDER_VERSION,  # the loader refuses any other builder
                ),
                chunking_profile="characters-v2:1200",
                set_id=str(NormRetrievalSetId.new()), set_sha256=f"{index + 8:x}" * 64,
            )
            for index, scope_id in enumerate(SCOPES, 1)
        ),
    )
    return parse_manifest(seal_manifest(pack, REVIEW))


def _adapter(installed: ParsedPackManifest | None) -> RunAdapter:
    return RunAdapter(
        None,  # type: ignore[arg-type]
        blob_store=None, adapter=None, provider_config=None, provider_mode="recorded",
        analysis_profile_id=str(PROFILE.analysis_profile_id),
        prompt_bundle_id=str(PROFILE.prompt_bundle_id), carrier=None,
        ar_v3_pack_registry=None if installed is None else installed.registry,
        ar_v3_installed_pack=installed,
    )


def _served(adapter: Any) -> tuple[int, bytes]:
    router = APIRouter()
    build_ar_v3_group_routes(router, adapter)
    route = next(route for route in router.routes if route.operation_id == "getArV3BetaPackStatus")
    response = route.endpoint()
    return response.status_code, response.body


def test_without_a_pack_the_answer_is_exactly_not_installed() -> None:
    status, body = _served(_adapter(None))
    assert status == 200
    assert json.loads(body) == {"state": "not_installed"}


def test_an_installed_pack_answers_its_ids_digest_scopes_and_attestation() -> None:
    installed = _installed()
    status, body = _served(_adapter(installed))
    assert status == 200
    answer = json.loads(body)
    assert set(answer) == INSTALLED_KEYS
    assert set(answer["review"]) == REVIEW_KEYS
    assert answer == {
        "state": "installed",
        "analysis_profile_id": str(PROFILE.analysis_profile_id),
        "prompt_bundle_id": str(PROFILE.prompt_bundle_id),
        "pack_sha256": installed.pack.sha256,
        "scope_ids": ["F1", "F2", "A1", "A2", "S1", "S2"],
        "review": {
            "reviewer": "Test Reviewer", "capacity": "expert", "reviewed_at": "2026-10-26",
            "decision_ref": "TEST-RULING-1", "scope_statement": "six synthetic scopes, test only",
        },
    }


def test_the_digest_is_the_one_a_group_start_would_pin() -> None:
    installed = _installed()
    pack = installed.registry.select_beta()
    assert pack is not None
    _status, body = _served(_adapter(installed))
    assert json.loads(body)["pack_sha256"] == pack.sha256


def test_no_map_set_snapshot_or_scope_digest_is_ever_served() -> None:
    installed = _installed()
    _status, body = _served(_adapter(installed))
    text = body.decode("utf-8")
    secrets = {"snapshot_id": installed.pack.scopes[0].identity.snapshot_id}
    for scope in installed.pack.scopes:
        secrets[f"{scope.scope_id} map_sha256"] = scope.identity.map_sha256
        secrets[f"{scope.scope_id} set_id"] = scope.set_id
        secrets[f"{scope.scope_id} set_sha256"] = scope.set_sha256
    secrets["reviewed_content_key"] = "ar-v3-beta-synthetic-key"
    secrets["builder_version"] = SET_BUILDER_VERSION
    secrets["embedding_build"] = "bge-m3-dense-v1"
    for what, value in secrets.items():
        assert value not in text, f"{what} reached the response"
    for key in ("map_sha256", "set_id", "set_sha256", "snapshot", "blob", "path", "manifest", "env"):
        assert key not in text, key


def test_the_transport_model_is_closed_and_optional_fields_are_absent_not_null() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        models.ArV3BetaPackStatus.model_validate({"state": "not_installed", "map_sha256": "a" * 64})
    unset = models.ArV3BetaPackStatus(state="not_installed")
    assert unset.model_dump(mode="json", exclude_unset=True) == {"state": "not_installed"}


def test_any_authenticated_role_may_read_it() -> None:
    assert OPERATION_ROLES["getArV3BetaPackStatus"] == frozenset({ROLE_EXPERT, ROLE_ADMIN})
    assert OPERATION_ROLES["getArV3BetaPackStatus"] == OPERATION_ROLES["getArV3BetaGroup"]


def test_the_route_is_a_bodyless_get_with_the_sealed_responses() -> None:
    router = APIRouter()
    build_ar_v3_group_routes(router, _adapter(None))
    route = next(route for route in router.routes if route.operation_id == "getArV3BetaPackStatus")
    assert (route.path, sorted(route.methods), route.status_code) == ("/ar-v3-beta/pack", ["GET"], 200)
    assert sorted(route.responses) == [200, 401, 403, 500, 503]
