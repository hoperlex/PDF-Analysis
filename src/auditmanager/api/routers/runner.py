"""The pull channel (`EXEC-PULL-01`, `R-143`): runner tokens, and the four operations a runner calls.

The wire is ``tools/executor-runner/RUNNER_API.md``; this module is the server side of it. A
runner is a Claude Code session behind the stdio bridge, or an unattended agent, and it
authenticates with a **runner token** -- a principal of its own, resolved by the authorization
seam (``api/security.py``) and never a user session. Errors are the repository's
``ErrorEnvelope`` throughout.

Three statuses are the runner contract's rather than the catalog's default for their code, and
each is stated where it is produced:

* ``claimExecutorTask`` answers ``204`` with an empty body when nothing arrived within
  ``wait_seconds``;
* ``submitExecutorTaskAnswer`` answers a declared model that is not the task's with
  ``422`` and ``error_code: model_identity_mismatch``. The catalog's status for that code is 502
  (a provider's reply named the wrong model); here the *caller* declared it, which is a refusal
  of the request, and a runner treats a 5xx as transient and retries it. The claim is kept;
* every refusal of an answer (this one, a schema violation) leaves the claim as it was.

The long poll is a synchronous handler, so it runs on a worker thread and holds no database
connection while it sleeps (``executors.runner.claim_task``).
"""

from __future__ import annotations

from typing import Annotated, Protocol

from fastapi import APIRouter, Path

from auditmanager.api.routers.correlation import current_correlation_id
from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.idempotency import RequiredIdempotencyKey
from auditmanager.api.routers.ports import RunnerPort
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response
from auditmanager.api.schemas import models
from auditmanager.api.security import CurrentRunner, CurrentSubject, RunnerIdentity
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["ExecutorTaskContextPort", "ModelNotTheTasks", "build_runner_routes", "build_task_context_route"]

_TAGS = ["execution"]
_DEFAULT_WAIT_SECONDS = 25
_RUNNER_STATE_CONFLICT = (
    "The task is no longer this runner's to answer: `conflict` with `details.conflict_reason` "
    "`claim_lost`, `task_expired`, `task_terminal` or `answer_differs`, or "
    "`state_transition_not_allowed`. The runner drops the task and does not submit again."
)
_RUNNER_422 = (
    "The request was refused. `validation_failed` when `wait_seconds` is outside 0 to 25 or "
    "the answer is not the bare JSON document the task's `output_schema` describes (the "
    "message names the first violated location, never the text); the claim is kept and the "
    "runner may correct and submit again. `model_identity_mismatch` when the declared model is "
    "not the one the connection pins; the claim is kept."
)


class ExecutorTaskContextPort(Protocol):
    """`CTX-STAND` (contract 1.51.0): what answers ``getExecutorTaskContext``. The shipped implementation is the runner adapter's method over
    ``executors.public.get_task_context``; the composition root hands it to :func:`build_task_context_route`. With none the route sleeps as sealed."""

    def get_task_context(self, *, runner: RunnerIdentity, task_id: str, kind: str) -> models.ExecutorTaskContext: ...


class ModelNotTheTasks(Exception):
    """The declared model is not the task's. Raised by the port's ``submit_answer`` through the
    ``on_mismatch`` it is given; the router turns it into the 422 below."""


def build_task_context_route(router: APIRouter, task_context: ExecutorTaskContextPort | None = None) -> None:
    """``getExecutorTaskContext`` -- `CRIT-SEAL-50` sealed it asleep in ``api/routers/precedents.py``; `CTX-STAND` serves it from here, beside the
    runner's other operations. The declaration is the seal's, word for word, so the contract's document does not move.

    **Dormant until wired.** Nothing in this tree calls the builder: the seal's sleeping route in ``precedents.py`` still declares the operation. The
    integrator's move is one step: delete that route, call this builder (as ``build_runner_routes`` is called) with the runner adapter as the port.
    With no port the route is declared and answers what the seal answered, ``503 dependency_unavailable`` with ``dependency: executor_task_context``,
    so the served document is the same whether or not a port stands behind it."""

    @router.post(
        "/runner/tasks/{task_id}/context", operation_id="getExecutorTaskContext", tags=_TAGS,
        response_model=models.ExecutorTaskContext,
        responses={**success(200, "The reference data of the task by `input_id`, or `status: unavailable` with a `reason`. A repeat of the "
                                  "same kind answers the same and spends no budget."),
                   **envelope_responses(401, 404, 409, 422, 500, 503, descriptions={
                       404: "The task is not one that may be given reference data: it is not a model call of a run, the run has no stage "
                            "plan, its cell is not `review:main`, or the consent does not carry the same `executor_context_policy`. A "
                            "task is not told apart from one that does not exist.",
                       409: "The task is no longer this runner's to ask for: `conflict` with `details.conflict_reason` `claim_lost`, "
                            "`task_expired` or `task_terminal`. The agent calls the model without reference data."})},
        description=(
            "`CRIT-SEAL-50` (plan-v5 section 3.2): the agent behind the claim of a `review:main` task asks once per kind for the decisions "
            "of experts on findings like the task's own. The stand answers by the `input_id` of the task's `context_request` and journals "
            "what it gave (no text). **Idempotent by (task, kind)**: a repeat returns the same answer and spends no budget. While the "
            "night encoder is the only one the answer is `status: unavailable, reason: until_move`. The agent appends the data to the prompt "
            "as reference, never as ground, and echoes `context_sha256` in `submitExecutorTaskAnswer`; an error here never fails the task. "
            "Runner token only; no role."
        ),
    )
    def get_executor_task_context(
        identity: CurrentRunner, task_id: Annotated[models.ExecutorTaskId, Path()], body: models.ExecutorTaskContextRequest,
    ) -> WireResponse:
        if task_context is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="executor_task_context")
        view = task_context.get_task_context(runner=identity, task_id=task_id, kind=body.kind.value)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))


def build_runner_routes(router: APIRouter, runner: RunnerPort) -> None:
    @router.post(
        "/executor-connections/{connection_id}/runner-tokens",
        operation_id="issueRunnerToken", tags=_TAGS, status_code=201,
        response_model=models.IssuedRunnerToken,
        responses={**success(201, "The token's value, shown once, and its metadata. The value "
                                  "is stored only as a one-way hash and no operation returns "
                                  "it again."),
                   **envelope_responses(
                       401, 403, 404, 409, 422, 500, 503,
                       descriptions={409: "`conflict`: the connection is archived, or this "
                                          "request was already answered once (`token_shown_once`: "
                                          "the value cannot be shown again; revoke the token "
                                          "and issue another)."})},
    )
    def issue_runner_token(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
        body: models.IssueRunnerTokenRequest, idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = runner.issue_token(
            connection_id=connection_id, expires_in_days=body.expires_in_days,
            user_uid=subject.user_uid, idempotency_key=idempotency_key,
        )
        return json_response(201, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/executor-connections/{connection_id}/runner-tokens/{token_id}/revoke",
        operation_id="revokeRunnerToken", tags=_TAGS, response_model=models.RunnerTokenMetadata,
        responses={**success(200, "The token's metadata after revocation. Revoking a token "
                                  "already revoked answers it as it stands."),
                   **envelope_responses(401, 403, 404, 409, 422, 500, 503)},
    )
    def revoke_runner_token(
        subject: CurrentSubject, connection_id: Annotated[models.ExecutorConnectionId, Path()],
        token_id: Annotated[models.ExecutorRunnerTokenId, Path()],
        idempotency_key: RequiredIdempotencyKey,
    ) -> WireResponse:
        view = runner.revoke_token(
            connection_id=connection_id, token_id=token_id, user_uid=subject.user_uid,
            idempotency_key=idempotency_key,
        )
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/runner/tasks/claim", operation_id="claimExecutorTask", tags=_TAGS,
        response_model=models.ClaimedExecutorTask,
        responses={**success(200, "A task, now claimed by the calling runner token."),
                   **success(204, "Nothing arrived within `wait_seconds`; the body is empty "
                                  "and the runner claims again."),
                   **envelope_responses(401, 422, 500, 503)},
    )
    def claim_executor_task(
        identity: CurrentRunner, body: models.ClaimExecutorTaskRequest,
    ) -> WireResponse:
        wait_seconds = _DEFAULT_WAIT_SECONDS if body.wait_seconds is None else body.wait_seconds
        if body.runner_instance_id is None:
            # `EXEC2-PULL-01`: a claim that names no instance reaches the port with the arguments it
            # had before the field existed (ADR-0026 decision 3).
            task = runner.claim_task(
                runner=identity, wait_seconds=wait_seconds, max_images=body.max_images)
        else:
            task = runner.claim_task(
                runner=identity, wait_seconds=wait_seconds, max_images=body.max_images,
                runner_instance_id=body.runner_instance_id)
        if task is None:
            return WireResponse(204, ())
        return json_response(200, encode_json(task.model_dump(mode="json", exclude_unset=True)))

    @router.get(
        "/runner/tasks/{task_id}/images/{blob_id}",
        operation_id="getExecutorTaskImage", tags=_TAGS,
        status_code=200,
        response_class=WireResponse,
        responses={
            **success(200, "Verified PNG of this runner's current claim.",
                      content={"image/png": {"schema": {"type": "string", "format": "binary"}}}),
            **envelope_responses(401, 404, 409, 422, 500, 503,
                                 descriptions={409: _RUNNER_STATE_CONFLICT}),
        },
    )
    def get_executor_task_image(
        identity: CurrentRunner, task_id: Annotated[models.ExecutorTaskId, Path()],
        blob_id: Annotated[models.RunnerImageBlobId, Path()],
    ) -> WireResponse:
        content = runner.read_image(runner=identity, task_id=task_id, blob_id=blob_id)
        return WireResponse(200, (("Content-Type", "image/png"),
                                  ("Content-Length", str(len(content))),
                                  ("Cache-Control", "no-store")), content)

    @router.post(
        "/runner/tasks/{task_id}/extend", operation_id="extendExecutorTaskClaim", tags=_TAGS,
        response_model=models.ExtendedExecutorTaskClaim,
        responses={**success(200, "The claim's new lease end, never beyond the task's deadline."),
                   **envelope_responses(401, 404, 409, 422, 500, 503,
                                        descriptions={409: _RUNNER_STATE_CONFLICT})},
    )
    def extend_executor_task_claim(
        identity: CurrentRunner, task_id: Annotated[models.ExecutorTaskId, Path()],
    ) -> WireResponse:
        view = runner.extend_claim(runner=identity, task_id=task_id)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/runner/tasks/{task_id}/answer", operation_id="submitExecutorTaskAnswer",
        tags=_TAGS, response_model=models.ExecutorTaskAck,
        responses={**success(200, "The answer was accepted, or this exact answer already was."),
                   **envelope_responses(401, 404, 409, 422, 500, 503,
                                        descriptions={409: _RUNNER_STATE_CONFLICT,
                                                      422: _RUNNER_422})},
    )
    def submit_executor_task_answer(
        identity: CurrentRunner, task_id: Annotated[models.ExecutorTaskId, Path()],
        body: models.SubmitExecutorTaskAnswerRequest,
    ) -> WireResponse:
        try:
            view = runner.submit_answer(runner=identity, task_id=task_id, body=body)
        except ModelNotTheTasks:
            envelope = DomainError(
                ErrorCode.MODEL_IDENTITY_MISMATCH,
                message="the declared model is not the one this connection pins",
            ).envelope(current_correlation_id())
            return json_response(422, encode_json(envelope.as_dict()))
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))

    @router.post(
        "/runner/tasks/{task_id}/fail", operation_id="failExecutorTask", tags=_TAGS,
        response_model=models.ExecutorTaskAck,
        responses={**success(200, "The task is failed, or already was."),
                   **envelope_responses(401, 404, 409, 422, 500, 503,
                                        descriptions={409: _RUNNER_STATE_CONFLICT})},
    )
    def fail_executor_task(
        identity: CurrentRunner, task_id: Annotated[models.ExecutorTaskId, Path()],
        body: models.FailExecutorTaskRequest,
    ) -> WireResponse:
        view = runner.fail_task(runner=identity, task_id=task_id, reason=body.reason)
        return json_response(200, encode_json(view.model_dump(mode="json", exclude_unset=True)))
