"""Read one AR v3 group member's trusted pins under a current Attempt.

This preflight does not read set Blobs or grant dispatch authority on its own.
The executor must continue with custody-verified bytes and recheck its Attempt
before and after every external effect.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import BetaV3ProfileRefused, resolve_beta_v3_profile
from auditmanager.jobs.public import AttemptAuthority, JobRepository
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.shared.errors import DomainError, ErrorCode


@dataclass(frozen=True, slots=True)
class V3ExecutionBinding:
    group_id: str
    run_id: str
    scope_id: str
    project_uid: str
    version_uid: str
    norms_snapshot_id: str
    analysis_profile_id: str
    prompt_bundle_id: str
    provider_mode: str
    composition_sha256: str
    policy_sha256: str
    pack_sha256: str
    map_sha256: str
    norm_retrieval_set_id: str
    set_sha256: str
    frozen_input_digest: str


_PIN = text("""
    SELECT m.group_id, m.scope_id, m.map_sha256,
           m.norm_retrieval_set_id, m.frozen_input_digest,
           g.project_uid, g.version_uid, g.norms_snapshot_id,
           g.analysis_profile_id, g.prompt_bundle_id, g.provider_mode,
           g.composition_sha256, g.policy_sha256, g.pack_sha256,
           r.state AS run_state, r.project_uid AS run_project_uid,
           r.version_uid AS run_version_uid,
           r.norms_snapshot_id AS run_snapshot_id,
           r.analysis_profile_id AS run_profile_id,
           r.prompt_bundle_id AS run_bundle_id,
           r.provider_mode AS run_provider_mode,
           r.norm_retrieval_set_id AS run_set_id,
           r.frozen_input_digest AS run_input_digest,
           r.command_id AS run_command_id,
           g.command_id AS group_command_id,
           s.state AS set_state, s.norms_snapshot_id AS set_snapshot_id,
           s.map_sha256 AS set_map_sha256,
           s.observed_set_sha256 AS observed_set_sha256,
           s.expected_set_sha256 AS expected_set_sha256
      FROM ar_v3_run_group_member m
      JOIN ar_v3_run_group g ON g.group_id = m.group_id
      JOIN audit_run r ON r.run_id = m.run_id
      JOIN norm_retrieval_set s
        ON s.norm_retrieval_set_id = m.norm_retrieval_set_id
     WHERE m.run_id = :run_id
""")


def _unavailable(kind: str = "norm_retrieval_set") -> DomainError:
    return DomainError(ErrorCode.REQUIRED_NORM_UNAVAILABLE, reference_kind=kind)


def resolve_v3_execution_binding(
    session: Session,
    *,
    authority: AttemptAuthority,
    registry: TrustedPackRegistry,
    jobs: JobRepository | None = None,
) -> V3ExecutionBinding:
    """Resolve immutable group and pack pins while this Attempt is current.

    The DB read and both authority checks belong to the caller's transaction.
    Do not cache the return across Attempts or treat it as set Blob custody.
    """
    if not isinstance(authority, AttemptAuthority):
        raise _unavailable("analysis_profile")
    job_repo = jobs or JobRepository()
    job_repo.require_current(session, authority)
    if not isinstance(registry, TrustedPackRegistry):
        raise _unavailable("analysis_profile")
    pack = registry.select_beta()
    if pack is None:
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="ar_v3_trusted_pack")
    try:
        profile = resolve_beta_v3_profile(pack.analysis_profile_id, pack.prompt_bundle_id)
    except BetaV3ProfileRefused as exc:
        raise _unavailable("analysis_profile") from exc
    rows = session.execute(_PIN, {"run_id": authority.run_id}).mappings().all()
    if len(rows) != 1:
        raise _unavailable("analysis_profile")
    row = rows[0]
    scope = next((item for item in pack.scopes if item.scope_id == row["scope_id"]), None)
    if scope is None or (
        row["run_state"] != "running"
        or row["pack_sha256"] != pack.sha256
        or row["analysis_profile_id"] != str(profile.analysis_profile_id)
        or row["prompt_bundle_id"] != str(profile.prompt_bundle_id)
        or row["norms_snapshot_id"] != profile.snapshot_id
        or row["composition_sha256"] != profile.composition_sha256
        or row["policy_sha256"] != profile.policy_sha256
        or row["map_sha256"] != scope.identity.map_sha256
        or row["norm_retrieval_set_id"] != scope.set_id
        or row["set_state"] != "verified"
        or row["set_snapshot_id"] != profile.snapshot_id
        or row["set_map_sha256"] != scope.identity.map_sha256
        or row["observed_set_sha256"] != scope.set_sha256
        or row["expected_set_sha256"] != scope.set_sha256
        or row["run_project_uid"] != row["project_uid"]
        or row["run_version_uid"] != row["version_uid"]
        or row["run_snapshot_id"] != row["norms_snapshot_id"]
        or row["run_profile_id"] != row["analysis_profile_id"]
        or row["run_bundle_id"] != row["prompt_bundle_id"]
        or row["run_provider_mode"] != row["provider_mode"]
        or row["run_set_id"] != row["norm_retrieval_set_id"]
        or row["run_input_digest"] != row["frozen_input_digest"]
        or row["run_command_id"] != row["group_command_id"]
    ):
        raise _unavailable()
    job_repo.require_current(session, authority)
    return V3ExecutionBinding(
        group_id=row["group_id"], run_id=authority.run_id,
        scope_id=row["scope_id"], project_uid=row["project_uid"],
        version_uid=row["version_uid"],
        norms_snapshot_id=row["norms_snapshot_id"],
        analysis_profile_id=row["analysis_profile_id"],
        prompt_bundle_id=row["prompt_bundle_id"],
        provider_mode=row["provider_mode"],
        composition_sha256=row["composition_sha256"],
        policy_sha256=row["policy_sha256"],
        pack_sha256=row["pack_sha256"],
        map_sha256=row["map_sha256"],
        norm_retrieval_set_id=row["norm_retrieval_set_id"],
        set_sha256=scope.set_sha256,
        frozen_input_digest=row["frozen_input_digest"],
    )


__all__ = ["V3ExecutionBinding", "resolve_v3_execution_binding"]
