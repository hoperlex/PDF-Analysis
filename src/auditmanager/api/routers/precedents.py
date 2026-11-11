"""The «Прецеденты» surface (`CRIT-SEAL-50`, contract 1.51.0, plan-v5 section 3.2): six routes of the user's; the seventh, ``getExecutorTaskContext``, is the
runner's and lives in ``api/routers/runner.py`` (`CTX-STAND`).

====================================  =================================================================================================
``getRunPrecedents``                  ``expert`` or ``admin``; the labels of the findings of a run and the queue «Рекомендовано снять»
``getFindingPrecedents``              ``expert`` or ``admin``; the card of a finding: label, hints, similar cases, possible norms
``getVectorControl``                  ``expert`` or ``admin``; whether the vectors are paused and the state of the night window
``setVectorPaused``                   ``admin``, keyed; pause the vectors or resume them, journalled with the actor
``listPrecedentSettings``             ``admin``; the switches and settings of the programme and their journal
``appendPrecedentSetting``            ``admin``, keyed; a new revision of a setting
====================================  =================================================================================================

The viewer («Наблюдатель», `R-150w`) is denied the six user routes: the authorization seam (``api/security.py``) decides it before any handler
runs, and a router decides nothing about roles. The context route is reached with a runner token only (``RUNNER_OPERATIONS``).

**Sealed, and asleep until a port stands behind it.** With no port a body reads and writes nothing: it refuses with ``503 dependency_unavailable``
(``details.dependency`` the stable class name of the lane that owns it) until that lane's adapter is wired. **`PREC-PASS` filled the precedents**:
``getRunPrecedents`` and ``getFindingPrecedents`` answer through ``PrecedentsPort`` when the composition root hands ``build_router`` one, and keep the
sleeping answer when it does not. **`EMBED-01` filled
the vector control**: ``getVectorControl`` and ``setVectorPaused`` answer through ``VectorControlPort`` when the composition root hands
``build_router`` one, and keep the sleeping answer when it does not (`api/routers/precedents_ports.py`). **`PREC-SETTINGS-01` filled the settings**
the same way: ``listPrecedentSettings`` and ``appendPrecedentSetting`` answer through ``PrecedentSettingsPort``. **`CTX-STAND` moved the context** to the
runner's module and the composition root wired it (`CRIT-CAPTURE-01` part D). The contract's error catalogue is closed and has no ``501``; ``503`` is what
every earlier seal's stubs answer (``CMP-SEAL-C0`` onwards), and there is no fallback: a caller is told that the surface is not served, never given an
empty answer.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Final, NoReturn

from fastapi import APIRouter, Path

from auditmanager.api.routers.declarations import STATE_CONFLICT_DESCRIPTION, envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.precedents_ports import PrecedentsPort, PrecedentSettingsPort, VectorControlPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentSubject
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "APPEND_PRECEDENT_SETTING_COMMAND_TYPE", "DEPENDENCIES", "SET_VECTOR_PAUSED_COMMAND_TYPE", "build_precedent_routes",
]

#: The command types of the two keyed writes, as ``command_record.command_type`` will hold them: the lane that fills a body writes them. Both
#: are classified in ``scripts/recovery/product_purge.py`` (kept configuration, like the executor commands), and the guard that reads the source
#: for command constants (`test_every_event_type_and_command_type_the_source_writes_is_classified`) sees them here.
APPEND_PRECEDENT_SETTING_COMMAND_TYPE: Final[str] = "append_precedent_setting"
SET_VECTOR_PAUSED_COMMAND_TYPE: Final[str] = "set_vector_paused"

#: The stable class names a sleeping route refuses with, one per owning lane.
DEPENDENCIES = {
    "precedents": "precedents",
    "vector_control": "vector_control",
    "precedent_settings": "precedent_settings",
}

_TAGS = ["execution"]
_FINDING_TAGS = ["findings"]

RunIdPath = Annotated[models.RunId, Path()]
FindingUidPath = Annotated[models.FindingUid, Path()]


def _asleep(dependency: str) -> NoReturn:
    raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=dependency)


def _vector_control_body(view: Mapping[str, Any]) -> bytes:
    """The contract's ``VectorControl``: an optional member with no value is absent on the wire, never null."""
    return encode_json(models.VectorControl.model_validate(dict(view)).model_dump(mode="json", exclude_unset=True))


def _precedents_body(view: Mapping[str, Any], model: type[models.RunPrecedents] | type[models.FindingPrecedents]) -> bytes:
    """The contract's ``RunPrecedents`` or ``FindingPrecedents``: a member that is optional and has no value (``pass_state`` and ``revision`` before a pass
    has started, ``label`` while the finding has no answer) is absent on the wire, never null."""
    return encode_json(model.model_validate(dict(view)).model_dump(mode="json", exclude_unset=True))


def _settings_body(view: Mapping[str, Any], model: type[models.PrecedentSetting] | type[models.PrecedentSettingList]) -> bytes:
    """The contract's ``PrecedentSetting`` or ``PrecedentSettingList``: every member is required, so nothing is left out and nothing is null."""
    return encode_json(model.model_validate(dict(view)).model_dump(mode="json"))


def build_precedent_routes(
    router: APIRouter, vector_control: VectorControlPort | None = None, precedent_settings: PrecedentSettingsPort | None = None,
    precedents: PrecedentsPort | None = None,
) -> None:
    @router.get(
        "/runs/{run_id}/precedents", operation_id="getRunPrecedents", tags=_FINDING_TAGS,
        response_model=models.RunPrecedents,
        responses={**success(200, "The labels of the findings of the run, and `available: false` while the pass has no result."),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
        description=(
            "`CRIT-SEAL-50` (plan-v5 sections 2.3 and 6): what the «Прецеденты» pass gave the findings of a run -- the neutral label of "
            "each, and the items with `label: cancel_suggested` are the queue «Рекомендовано снять». `404 not_found` for an unknown run. "
            "`role:admin|expert`; the viewer («Наблюдатель») is denied."
        ),
    )
    def get_run_precedents(subject: CurrentSubject, run_id: RunIdPath) -> WireResponse:
        if precedents is None:
            _asleep(DEPENDENCIES["precedents"])
        return json_response(200, _precedents_body(precedents.get_run_precedents(run_id=run_id, user_uid=subject.user_uid), models.RunPrecedents))

    @router.get(
        "/findings/{finding_uid}/precedents", operation_id="getFindingPrecedents", tags=_FINDING_TAGS,
        response_model=models.FindingPrecedents,
        responses={**success(200, "The card of the finding."), **envelope_responses(401, 403, 404, 422, 500, 503)},
        description=(
            "`CRIT-SEAL-50` (plan-v5 sections 2.5 and 3.4): the card of a finding -- its label, at most two hints, the similar cases and the "
            "possible norms (paragraphs the run already holds). `404 not_found` for an unknown finding. `role:admin|expert`; the viewer is "
            "denied."
        ),
    )
    def get_finding_precedents(subject: CurrentSubject, finding_uid: FindingUidPath) -> WireResponse:
        if precedents is None:
            _asleep(DEPENDENCIES["precedents"])
        return json_response(
            200, _precedents_body(precedents.get_finding_precedents(finding_uid=finding_uid, user_uid=subject.user_uid), models.FindingPrecedents))

    @router.get(
        "/vector-control", operation_id="getVectorControl", tags=_TAGS,
        response_model=models.VectorControl,
        responses={**success(200, "Whether the vectors are paused, the state of the night window and the window."),
                   **envelope_responses(401, 403, 500, 503)},
        description=(
            "`CRIT-SEAL-50` (plan-v5 section 5): the pause of the vectors and the state of the night window. The queued and poisoned jobs "
            "are shown to an administrator only. `role:admin|expert`; the viewer is denied."
        ),
    )
    def get_vector_control(subject: CurrentSubject) -> WireResponse:
        if vector_control is None:
            _asleep(DEPENDENCIES["vector_control"])
        return json_response(200, _vector_control_body(vector_control.get_vector_control(user_uid=subject.user_uid)))

    @router.put(
        "/vector-control/paused", operation_id="setVectorPaused", tags=_TAGS,
        response_model=models.VectorControl,
        responses={**success(200, "The control with the pause as it now stands."),
                   **envelope_responses(401, 403, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`CRIT-SEAL-50` (plan-v5 section 5): pause the vectors or resume them. On a pause the night window does not start and the queue "
            "keeps filling. Each change is an append-only event with its actor and time; setting the value already in force answers the "
            "control as it stands. `role:admin`, `Idempotency-Key` required."
        ),
    )
    def set_vector_paused(
        subject: CurrentSubject, body: models.SetVectorPausedRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        if vector_control is None:
            _asleep(DEPENDENCIES["vector_control"])
        view = vector_control.set_vector_paused(paused=body.paused, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(200, _vector_control_body(view))

    @router.get(
        "/precedent-settings", operation_id="listPrecedentSettings", tags=_TAGS,
        response_model=models.PrecedentSettingList,
        responses={**success(200, "The revision in force of each setting and the journal."), **envelope_responses(401, 403, 500, 503)},
        description=(
            "`CRIT-SEAL-50` (plan-v5 sections 3.1 and 3.6): the switches (`one_list`, `critic_context`, `section_labels`; every one is off "
            "while nothing is journalled), the stop words, the night window and the thresholds, and the journal of their changes. "
            "`role:admin`."
        ),
    )
    def list_precedent_settings(subject: CurrentSubject) -> WireResponse:
        if precedent_settings is None:
            _asleep(DEPENDENCIES["precedent_settings"])
        view = precedent_settings.list_precedent_settings(user_uid=subject.user_uid)
        return json_response(200, _settings_body(view, models.PrecedentSettingList))

    @router.post(
        "/precedent-settings", operation_id="appendPrecedentSetting", tags=_TAGS, status_code=201,
        response_model=models.PrecedentSetting,
        responses={**success(201, "The new revision of the setting, or the recorded outcome of an identical earlier request."),
                   **envelope_responses(401, 403, 409, 422, 500, 503, descriptions={409: STATE_CONFLICT_DESCRIPTION})},
        description=(
            "`CRIT-SEAL-50` (plan-v5 sections 3.1 and 3.6): a new revision of a setting, journalled with the administrator who made it. "
            "`422 validation_failed` for a value that is not the shape of its setting. A switch changes the behaviour of runs started "
            "after it; a run's publication mode is frozen at its start. `role:admin`, `Idempotency-Key` required."
        ),
    )
    def append_precedent_setting(
        subject: CurrentSubject, body: models.AppendPrecedentSettingRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        if precedent_settings is None:
            _asleep(DEPENDENCIES["precedent_settings"])
        view = precedent_settings.append_precedent_setting(
            setting_name=body.setting_name.value, value=body.value, user_uid=subject.user_uid, idempotency_key=idempotency_key)
        return json_response(201, _settings_body(view, models.PrecedentSetting))
