"""``listAnalysisProfiles`` (`W59-ANALYSIS-SETTINGS-01`).

The read behind «Настройки анализа»: the section-keyed text-profile registry the
composition root loaded at start-up -- the same table ``startRun`` and ``reauditRun`` route a
classified version through -- as fifteen rows in the project-structure order. A section with
a registered profile carries its identities, version, status (``draft`` or ``reviewed``),
prompt-bundle and profile hashes and, for a ported package, the legacy source; a section without
one carries ``profile: null``, which is also what run start refuses it for. АР is that section
since `PROD-11-AR-V1-V2-REMOVAL-01`: its analysis is the six-Run AR v3 group, not a text profile.

Read-only, for any one role (``role:admin|expert``): there is no operation that edits a
profile, uploads one or changes its status. No path parameter, no query and no body, so the
operation declares no ``422``.
"""

from __future__ import annotations

from fastapi import APIRouter

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import AnalysisProfilePort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models

__all__ = ["build_analysis_profile_routes"]


def build_analysis_profile_routes(router: APIRouter, profiles: AnalysisProfilePort) -> None:

    @router.get(
        "/analysis/profiles",
        operation_id="listAnalysisProfiles",
        tags=["analysis"],
        status_code=200,
        response_model=models.AnalysisProfileList,
        responses={
            **success(200, "All fifteen sections, each with its registered profile or `null`."),
            **envelope_responses(401, 403, 500, 503),
        },
        description=(
            "The analysis profiles the server routes runs through: all fifteen sections in "
            "the project-structure order, each with its registered text profile -- "
            "identities, version, status (`draft` or `reviewed`), prompt-bundle "
            "and profile hashes and the legacy source of a ported package -- or `null` when "
            "no profile is registered, which run start refuses (АР is such a section: it is "
            "analysed by the six-Run group, not by a text profile). Read-only: no operation "
            "edits a profile or its status. Any one role, `role:admin|expert`."
        ),
    )
    def list_analysis_profiles() -> WireResponse:
        listing = profiles.list_analysis_profiles()
        return json_response(200, encode_json(listing.model_dump(mode="json")))
