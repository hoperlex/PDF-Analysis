"""The pull channel's adapter (`EXEC-PULL-01`, `R-143`): thin, like every adapter here.

The rules, the hashing and the task lifecycle live in ``auditmanager.executors``; this opens the
session, reads the administrator's role set inside it and maps the records into the frozen
shapes. It is also what the authorization seam asks to authenticate a runner token
(``api.security.RunnerTokens``): the ``api`` writes the rows on the runner's behalf, and the
remote party only ever calls HTTP.

No method returns a token's value except :meth:`RunnerAdapter.issue_token`, once, and no view
built here carries a hash, a payload or an answer.
"""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.routers.runner import ModelNotTheTasks
from auditmanager.api.schemas import models
from auditmanager.api.security import RunnerIdentity
from auditmanager.bootstrap.adapters import _SessionHolder
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore, StorageError, parse_blob_id

__all__ = ["RunnerAdapter", "runner_token_view"]


def runner_token_view(record: Any) -> dict[str, Any]:
    """A token's metadata. Optional properties are absent when they have no value, never null."""
    fields = {
        "token_id": record.token_id, "connection_id": record.connection_id,
        "token_prefix": record.token_prefix, "created_at": record.created_at,
        "created_by": record.created_by, "expires_at": record.expires_at,
        "revoked_at": record.revoked_at, "revoked_by": record.revoked_by,
        "last_seen_at": record.last_seen_at, "last_seen_address": record.last_seen_address,
    }
    return {name: value for name, value in fields.items() if value is not None}


class RunnerAdapter(_SessionHolder):
    def __init__(
        self, session_factory: sessionmaker[Session], *, blob_store: BlobStore | None = None,
    ) -> None:
        super().__init__(session_factory)
        self._blob_store = blob_store

    @staticmethod
    def _roles(session: Session, user_uid: str) -> Any:
        from auditmanager.access.public import AccountRepository

        return AccountRepository().roles_of(session, user_uid)

    # -- the seam ---------------------------------------------------------------------------

    def authenticate_runner(
        self, presented: str, *, address: str | None
    ) -> RunnerIdentity | None:
        from auditmanager.executors.public import authenticate_runner

        def work(session: Session) -> RunnerIdentity | None:
            principal = authenticate_runner(session, presented, address=address)
            if principal is None:
                return None
            return RunnerIdentity(
                token_id=principal.token_id, connection_id=principal.connection_id)
        return self._write(work)

    # -- the administrator's -----------------------------------------------------------------

    def issue_token(
        self, *, connection_id: str, expires_in_days: int | None, user_uid: str,
        idempotency_key: str,
    ) -> models.IssuedRunnerToken:
        from auditmanager.executors.public import issue_runner_token

        def work(session: Session) -> models.IssuedRunnerToken:
            issued = issue_runner_token(
                session, connection_id=connection_id, expires_in_days=expires_in_days,
                roles=self._roles(session, user_uid), idempotency_key=idempotency_key,
                actor_uid=user_uid,
            )
            return models.IssuedRunnerToken.model_validate({
                "token": issued.value, "runner_token": runner_token_view(issued.record),
            })
        return self._write(work)

    def revoke_token(
        self, *, connection_id: str, token_id: str, user_uid: str, idempotency_key: str
    ) -> models.RunnerTokenMetadata:
        from auditmanager.executors.public import revoke_runner_token

        def work(session: Session) -> models.RunnerTokenMetadata:
            record = revoke_runner_token(
                session, connection_id=connection_id, token_id=token_id,
                roles=self._roles(session, user_uid), idempotency_key=idempotency_key,
                actor_uid=user_uid,
            )
            return models.RunnerTokenMetadata.model_validate(runner_token_view(record))
        return self._write(work)

    # -- the runner's ------------------------------------------------------------------------

    @staticmethod
    def _principal(runner: RunnerIdentity) -> Any:
        from auditmanager.executors.public import RunnerPrincipal

        return RunnerPrincipal(token_id=runner.token_id, connection_id=runner.connection_id)

    def claim_task(
        self, *, runner: RunnerIdentity, wait_seconds: int, max_images: int | None = None
    ) -> models.ClaimedExecutorTask | None:
        from auditmanager.executors.public import claim_task

        task = claim_task(self._sessions, self._principal(runner), wait_seconds=wait_seconds,
                          max_images=max_images)
        if task is None:
            return None
        return models.ClaimedExecutorTask.model_validate({
            "task_id": task.task_id, "claim_expires_at": task.claim_expires_at,
            "deadline_at": task.deadline_at, "model": task.model, "system": task.system,
            "user_text": task.user_text, "output_schema": dict(task.output_schema),
            **({"images": list(task.images)} if task.images else {}),
        })

    def read_image(self, *, runner: RunnerIdentity, task_id: str, blob_id: str) -> bytes:
        """Serve only a current claim's bounded PNG, never a direct Blob lookup by URL."""
        from auditmanager.executors.public import claimed_image

        if self._blob_store is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="blob_storage")

        def authorized(session: Session) -> dict[str, Any]:
            return dict(claimed_image(session, self._principal(runner), task_id, blob_id))

        image = self._read(authorized)
        try:
            identity = parse_blob_id(blob_id)
            metadata = self._blob_store.inspect(identity)
            if (metadata.size != image["size_bytes"]
                    or metadata.sha256 != image["sha256"]
                    or metadata.media_type != "image/png"):
                raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,
                                  message="runner image metadata changed")
            chunks = self._blob_store.open_stream(
                identity, expected_sha256=image["sha256"],
                expected_size=image["size_bytes"],
            )
            parts: list[bytes] = []
            total = 0
            try:
                for chunk in chunks:
                    total += len(chunk)
                    if total > image["size_bytes"]:
                        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,
                                          message="runner image exceeds its byte ceiling")
                    parts.append(chunk)
            finally:
                chunks.close()
            content = b"".join(parts)
        except StorageError:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE,
                              dependency="blob_storage") from None
        if (len(content) != image["size_bytes"]
                or hashlib.sha256(content).hexdigest() != image["sha256"]
                or not content.startswith(b"\x89PNG\r\n\x1a\n")):
            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,
                              message="runner image bytes are invalid")
        self._read(authorized)
        return content

    def extend_claim(
        self, *, runner: RunnerIdentity, task_id: str
    ) -> models.ExtendedExecutorTaskClaim:
        from auditmanager.executors.public import extend_claim

        def work(session: Session) -> models.ExtendedExecutorTaskClaim:
            lease = extend_claim(session, self._principal(runner), task_id)
            return models.ExtendedExecutorTaskClaim.model_validate({"claim_expires_at": lease})
        return self._write(work)

    def submit_answer(
        self, *, runner: RunnerIdentity, task_id: str,
        body: models.SubmitExecutorTaskAnswerRequest,
    ) -> models.ExecutorTaskAck:
        from auditmanager.executors.public import submit_answer

        def work(session: Session) -> models.ExecutorTaskAck:
            ack = submit_answer(
                session, self._principal(runner), task_id, output_text=body.output_text,
                model=body.model, input_tokens=body.input_tokens,
                output_tokens=body.output_tokens, on_mismatch=ModelNotTheTasks,
            )
            return models.ExecutorTaskAck.model_validate(
                {"task_id": ack.task_id, "state": ack.state})
        return self._write(work)

    def fail_task(
        self, *, runner: RunnerIdentity, task_id: str, reason: str
    ) -> models.ExecutorTaskAck:
        from auditmanager.executors.public import fail_task

        def work(session: Session) -> models.ExecutorTaskAck:
            ack = fail_task(session, self._principal(runner), task_id, reason=reason)
            return models.ExecutorTaskAck.model_validate(
                {"task_id": ack.task_id, "state": ack.state})
        return self._write(work)
