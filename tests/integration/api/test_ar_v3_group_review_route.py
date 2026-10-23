"""The public group read exposes only the reviewed six-scope projection."""

from dataclasses import asdict

import json

from fastapi import APIRouter

from auditmanager.api.routers.ar_v3_groups import build_ar_v3_group_routes
from auditmanager.api.schemas import models
from auditmanager.api.security import OPERATION_ROLES, ROLE_ADMIN, ROLE_EXPERT
from auditmanager.runs.v3_group_review import (
    V3GroupReview, V3ScopeOutcome, V3VisibleCitation, V3VisibleEvidence,
    V3VisibleProposal, V3VisibleReview, V3VisibleTopic,
)


GROUP_ID = "arg_01M2545JSD15ETSNNV904X991K"
VERSION_ID = "ver_01M2545JSD15ETSNNV904X991J"
SCOPES = ("F1", "F2", "A1", "A2", "S1", "S2")


def test_group_review_route_returns_six_safe_outcomes() -> None:
    visible = V3VisibleReview(
        topics=(V3VisibleTopic(
            "C01", "provisional_citation", "edition to review", ("D1_LOCAL",),
            "requires_expert_review", 1,
        ),),
        provisional_citations=(V3VisibleProposal(
            0, (V3VisibleEvidence(3, "door width"),),
            (V3VisibleCitation(
                "C01", "N1", "ndoc_example", "npar_example",
                "approved wording", "grounded",
            ),),
        ),),
        withheld_proposal_count=1,
        rejected_proposal_count=0,
    )
    states = ("published", "failed", "partial", "queued", "running", "created")
    reviews = ("available", "failed", "verification_refused", "pending", "pending", "pending")
    group = V3GroupReview(
        GROUP_ID, VERSION_ID,
        tuple(V3ScopeOutcome(
            scope, f"run_01M2545JSD15ETSNNV904X991{suffix}", state, review_state,
            terminal_reason="provider_unavailable" if scope == "F2" else None,
            refusal_code="storage_integrity_error" if scope == "A1" else None,
            review=visible if scope == "F1" else None,
        ) for scope, suffix, state, review_state in zip(
            SCOPES, "KMNPQR", states, reviews,
        )),
    )

    class Groups:
        def get_ar_v3_group_review(self, *, group_id: str) -> models.ArV3BetaGroupReview:
            assert group_id == GROUP_ID
            return models.ArV3BetaGroupReview.model_validate(asdict(group))

    router = APIRouter()
    build_ar_v3_group_routes(router, Groups())  # type: ignore[arg-type]
    route = next(route for route in router.routes if route.operation_id == "getArV3BetaGroupReview")
    response = route.endpoint(group_id=GROUP_ID)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["group_id"] == GROUP_ID
    assert [member["scope_id"] for member in body["members"]] == list(SCOPES)
    assert [member["review_state"] for member in body["members"]] == list(reviews)
    assert body["members"][0]["review"]["provisional_citations"][0]["proposal_ordinal"] == 0
    assert body["members"][1]["terminal_reason"] == "provider_unavailable"
    assert body["members"][2]["refusal_code"] == "storage_integrity_error"
    assert all(member["review"] is None for member in body["members"][1:])
    assert set(body["members"][0]["review"]) == {
        "topics", "provisional_citations", "withheld_proposal_count", "rejected_proposal_count",
    }
    assert b"blob_id" not in response.body
    assert b"sha256" not in response.body
    assert OPERATION_ROLES["getArV3BetaGroupReview"] == frozenset({ROLE_EXPERT, ROLE_ADMIN})
