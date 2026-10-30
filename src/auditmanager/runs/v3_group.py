"""Atomic AR v3 beta group creation and readback.

Only a server-installed reviewed pack can select sets. The request supplies a
version and idempotency key; it never supplies map, snapshot or set authority.
The caller owns the transaction. No Job or provider call is made here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import BetaV3ProfileRefused, resolve_beta_v3_profile
from auditmanager.documents.public import DocumentRepository, MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.norms.public import (
    PromotionRefused,
    SetIdentity,
    current_snapshot,
    qualification,
    select_verified_retrieval_set,
)
from auditmanager.runs.commands import (
    _checked_budget,
    _refuse_over_budget,
    frozen_input_digest,
    refuse_comparison_only_version,
)
from auditmanager.runs.provider import RouteFreezer
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    ArV3RunGroupId,
    IdempotencyKey,
    NormRetrievalSetId,
    RunId,
    VersionUid,
)

COMMAND_TYPE = "start_ar_v3_beta_group"
SCOPES = ("F1", "F2", "A1", "A2", "S1", "S2")


@dataclass(frozen=True, slots=True)
class ReviewedScope:
    scope_id: str
    identity: SetIdentity
    chunking_profile: str
    set_id: str
    set_sha256: str


@dataclass(frozen=True, slots=True)
class TrustedPack:
    """Installed by the server after review, never hydrated from an API request."""

    analysis_profile_id: str
    prompt_bundle_id: str
    scopes: tuple[ReviewedScope, ...]

    @property
    def sha256(self) -> str:
        data = {
            "format": "ar-v3-beta-reviewed-pack/1",
            "analysis_profile_id": self.analysis_profile_id,
            "prompt_bundle_id": self.prompt_bundle_id,
            "scopes": [
                {
                    "scope_id": scope.scope_id,
                    "map_sha256": scope.identity.map_sha256,
                    "snapshot_id": scope.identity.snapshot_id,
                    "reviewed_content_key": scope.identity.reviewed_content_key,
                    "embedding_build": scope.identity.embedding_build,
                    "builder_version": scope.identity.builder_version,
                    "chunking_profile": scope.chunking_profile,
                    "set_id": scope.set_id,
                    "set_sha256": scope.set_sha256,
                }
                for scope in self.scopes
            ],
        }
        return hashlib.sha256(json.dumps(
            data, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TrustedPackRegistry:
    """Versioned server registry; the API cannot add a candidate or choose its SHA."""

    registry_version: str
    installed: tuple[TrustedPack, ...]

    @classmethod
    def empty(cls) -> TrustedPackRegistry:
        return cls("ar-v3-beta-reviewed-pack-registry/1", ())

    def select_beta(self) -> TrustedPack | None:
        if self.registry_version != "ar-v3-beta-reviewed-pack-registry/1":
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE,
                              dependency="ar_v3_trusted_pack")
        if not self.installed:
            return None
        if len(self.installed) != 1:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE,
                              dependency="ar_v3_trusted_pack")
        _validate_pack(self.installed[0])
        return self.installed[0]


@dataclass(frozen=True, slots=True)
class GroupMember:
    scope_id: str
    run_id: str
    state: str
    map_sha256: str
    norm_retrieval_set_id: str


@dataclass(frozen=True, slots=True)
class GroupView:
    group_id: str
    project_uid: str
    version_uid: str
    norms_snapshot_id: str
    analysis_profile_id: str
    prompt_bundle_id: str
    pack_sha256: str
    provider_mode: str
    members: tuple[GroupMember, ...]


@dataclass(frozen=True, slots=True)
class StartedGroup:
    group: GroupView
    replayed: bool


def _unavailable(reference_kind: str = "norm_retrieval_set") -> DomainError:
    return DomainError(ErrorCode.REQUIRED_NORM_UNAVAILABLE, reference_kind=reference_kind)


def _validate_pack(pack: TrustedPack) -> object:
    if not isinstance(pack, TrustedPack):
        raise _unavailable()
    try:
        profile = resolve_beta_v3_profile(pack.analysis_profile_id, pack.prompt_bundle_id)
    except (ValueError, BetaV3ProfileRefused) as exc:
        raise _unavailable("analysis_profile") from exc
    if tuple(scope.scope_id for scope in pack.scopes) != SCOPES:
        raise _unavailable()
    if len({scope.set_id for scope in pack.scopes}) != 6:
        raise _unavailable()
    if any(
        not isinstance(scope.identity, SetIdentity)
        or scope.identity.snapshot_id != profile.snapshot_id
        or not scope.chunking_profile
        or len(scope.set_sha256) != 64
        or any(c not in "0123456789abcdef" for c in scope.set_sha256)
        for scope in pack.scopes
    ):
        raise _unavailable()
    for scope in pack.scopes:
        NormRetrievalSetId.parse(scope.set_id)
    return profile


def _fingerprint(version_uid: str, provider_mode: str, pack_sha256: str, relaxed_limits: bool = False, cost_consent=None):
    payload = {
        "version_uid": version_uid,
        "provider_mode": provider_mode,
        "pack_sha256": pack_sha256,
    }
    # Preserve the fingerprint of groups accepted before this temporary option existed.
    if relaxed_limits:
        payload["relaxed_limits"] = True
    if cost_consent is not None:
        payload["cost_consent"] = dict(cost_consent)
    return payload_fingerprint(payload)


def get_ar_v3_group(session: Session, group_id: str) -> GroupView:
    ArV3RunGroupId.parse(group_id)
    row = session.execute(text("""
        SELECT group_id, project_uid, version_uid, norms_snapshot_id,
               analysis_profile_id, prompt_bundle_id, pack_sha256, provider_mode
          FROM ar_v3_run_group WHERE group_id = :group_id
    """), {"group_id": group_id}).mappings().one_or_none()
    if row is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ArV3RunGroup")
    members = session.execute(text("""
        SELECT m.scope_id, m.run_id, r.state, m.map_sha256, m.norm_retrieval_set_id
          FROM ar_v3_run_group_member m
          JOIN audit_run r ON r.run_id = m.run_id
         WHERE m.group_id = :group_id ORDER BY m.ordinal
    """), {"group_id": group_id}).mappings().all()
    if tuple(member.scope_id for member in members) != SCOPES:
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="AR v3 group membership is incomplete")
    return GroupView(
        group_id=row["group_id"], project_uid=row["project_uid"],
        version_uid=row["version_uid"], norms_snapshot_id=row["norms_snapshot_id"],
        analysis_profile_id=row["analysis_profile_id"],
        prompt_bundle_id=row["prompt_bundle_id"], pack_sha256=row["pack_sha256"],
        provider_mode=row["provider_mode"],
        members=tuple(GroupMember(**dict(member)) for member in members),
    )


def start_ar_v3_group(
    session: Session,
    *,
    version_uid: str,
    idempotency_key: str,
    provider_mode: str,
    pack: TrustedPack | None,
    input_budget_characters: int | None,
    connection_route: RouteFreezer | None = None,
    relaxed_limits: bool = False,
    cost_preflight: Any = None,
    cost_consent: Mapping[str, Any] | None = None,
    cost_actor_uid: str | None = None,
) -> StartedGroup:
    if type(relaxed_limits) is not bool:
        raise ValueError("relaxed_limits must be a boolean")
    version_id = str(VersionUid.parse(version_uid))
    key = IdempotencyKey(idempotency_key)
    commands = CommandRepository()
    known = commands.find(session, command_type=COMMAND_TYPE, idempotency_key=key)
    # An accepted key remains replayable after the reviewed pack is withdrawn.
    if known is not None and pack is None:
        previous_id = (known.outcome or {}).get("group_id")
        if not isinstance(previous_id, str):
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_TYPE)
        previous = get_ar_v3_group(session, previous_id)
        claimed = commands.begin(
            session, command_type=COMMAND_TYPE, idempotency_key=key,
            fingerprint=_fingerprint(version_id, provider_mode, previous.pack_sha256, relaxed_limits, cost_consent),
        )
        assert isinstance(claimed, CommandReplay)
        return StartedGroup(previous, True)
    if pack is None:
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="ar_v3_trusted_pack")
    profile = _validate_pack(pack)
    pack_digest = pack.sha256
    claimed = commands.begin(
        session, command_type=COMMAND_TYPE, idempotency_key=key,
        fingerprint=_fingerprint(version_id, provider_mode, pack_digest, relaxed_limits, cost_consent),
    ) if known is not None else None
    if isinstance(claimed, CommandReplay):
        previous_id = claimed.outcome.get("group_id")
        if not isinstance(previous_id, str):
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_TYPE)
        return StartedGroup(get_ar_v3_group(session, previous_id), True)

    version = DocumentRepository().get_version(session, VersionUid.parse(version_id))
    # `CMP-C0-FIX-01`. By kind, first: a version admitted for comparison only is refused with
    # ``comparison_only_version`` (what the screen renders in Russian), not with the fault the
    # classification or manifest checks below would name.
    refuse_comparison_only_version(version)
    if version.classification is None:
        raise DomainError(ErrorCode.VERSION_CLASSIFICATION_REQUIRED)
    if version.classification.section_code != "AR":
        raise DomainError(ErrorCode.SECTION_PROFILE_UNAVAILABLE)
    blob_ids = {entry.role: str(entry.blob_id) for entry in version.manifest}
    if MANIFEST_ROLE_SOURCE_DOCUMENT not in blob_ids:
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason="missing_required_input")
    approved_cost = None
    if cost_preflight is not None:
        estimate = cost_preflight.estimate_group(session, version_uid=version_id, relaxed_limits=relaxed_limits,
            version_record=version)
        approved_cost = estimate.approve(None if cost_consent is None else dict(cost_consent), actor_user_uid=cost_actor_uid)
        frozen_route = estimate.frozen_route
    elif cost_consent is not None:
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_preflight")
    else:
        frozen_route = None if connection_route is None else connection_route(session)
    budget = _checked_budget(
        input_budget_characters if frozen_route is None else frozen_route.input_budget_characters
    )
    # This preflight is derived from the dollar ceiling, so the temporary mode
    # disables it together with the worker's dollar halt. Provider context limits
    # remain provider refusals; they are never silently truncated here.
    if not relaxed_limits and approved_cost is None:
        _refuse_over_budget(version.text_character_count, budget)
    current = current_snapshot(session)
    if current is None or current.norms_snapshot_id != profile.snapshot_id:
        raise _unavailable("norms_snapshot")
    qualified = qualification(session, profile.snapshot_id)
    if qualified is None or not qualified.build_complete or not qualified.sources_confirmed:
        raise _unavailable("norms_snapshot")
    selected = []
    try:
        for scope in pack.scopes:
            ref = select_verified_retrieval_set(
                session, identity=scope.identity, chunking_profile=scope.chunking_profile,
            )
            if (ref.set_id != scope.set_id or ref.set_sha256 != scope.set_sha256
                    or ref.map_sha256 != scope.identity.map_sha256
                    or ref.snapshot_id != profile.snapshot_id):
                raise _unavailable()
            selected.append(ref)
    except PromotionRefused as exc:
        raise _unavailable() from exc
    if len({ref.set_id for ref in selected}) != 6:
        raise _unavailable()

    # Claim only after every mutable environmental precondition has passed.
    claimed = commands.begin(
        session, command_type=COMMAND_TYPE, idempotency_key=key,
        fingerprint=_fingerprint(version_id, provider_mode, pack_digest, relaxed_limits, cost_consent),
    )
    if isinstance(claimed, CommandReplay):
        previous_id = claimed.outcome.get("group_id")
        if not isinstance(previous_id, str):
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_TYPE)
        return StartedGroup(get_ar_v3_group(session, previous_id), True)

    group_id = str(ArV3RunGroupId.new())
    session.execute(text("""
        INSERT INTO ar_v3_run_group
            (group_id, project_uid, version_uid, command_id, norms_snapshot_id,
             analysis_profile_id, prompt_bundle_id, pack_sha256, composition_sha256,
             policy_sha256, provider_mode)
        VALUES (:group_id, :project_uid, :version_uid, :command_id, :snapshot_id,
                :profile_id, :bundle_id, :pack_sha256, :composition_sha256,
                :policy_sha256, :provider_mode)
    """), {
        "group_id": group_id, "project_uid": str(version.project_uid),
        "version_uid": version_id, "command_id": str(claimed.command_id),
        "snapshot_id": profile.snapshot_id, "profile_id": str(profile.analysis_profile_id),
        "bundle_id": str(profile.prompt_bundle_id), "pack_sha256": pack_digest,
        "composition_sha256": profile.composition_sha256,
        "policy_sha256": profile.policy_sha256, "provider_mode": provider_mode,
    })
    runs = RunRepository()
    run_limits = {}
    scope_costs = {} if approved_cost is None else approved_cost.get("scope_costs_micros", {})
    if approved_cost is not None and (set(scope_costs) != {scope.scope_id for scope in pack.scopes}
            or any(type(value) is not int or value < 0 for value in scope_costs.values())
            or approved_cost["billing"] == "metered" and any(value == 0 for value in scope_costs.values())):
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="AR v3 cost scope authority is invalid")
    scope_total = sum(scope_costs.values())
    left_cap = 0 if approved_cost is None else approved_cost["ceiling_micros"]
    for ordinal, (scope, ref) in enumerate(zip(pack.scopes, selected, strict=True), 1):
        run_id = str(RunId.new())
        if approved_cost is not None:
            share = 0 if scope_total == 0 else (approved_cost["ceiling_micros"] * scope_costs[scope.scope_id] // scope_total)
            if ordinal == 6 and scope_total:
                share = left_cap
            run_limits[run_id] = share
            left_cap -= share
        digest = frozen_input_digest(
            version_uid=version_id, blob_ids=blob_ids,
            analysis_profile_id=str(profile.analysis_profile_id),
            prompt_bundle_id=str(profile.prompt_bundle_id),
            norms_snapshot_id=profile.snapshot_id,
            norm_retrieval_set_sha256=ref.set_sha256,
            ar_v3_group_id=group_id, ar_v3_scope_id=scope.scope_id,
            ar_v3_map_sha256=scope.identity.map_sha256, ar_v3_set_id=ref.set_id,
        )
        runs.create(
            session, run_id=run_id, project_uid=str(version.project_uid),
            version_uid=version_id, analysis_profile_id=str(profile.analysis_profile_id),
            prompt_bundle_id=str(profile.prompt_bundle_id), provider_mode=provider_mode,
            frozen_input_digest=digest, command_id=str(claimed.command_id),
            norms_snapshot_id=profile.snapshot_id, norm_retrieval_set_id=ref.set_id,
            connection_revision_id=None if frozen_route is None else frozen_route.revision_id,
        )
        session.execute(text("""
            INSERT INTO ar_v3_run_group_member
                (group_id, ordinal, scope_id, run_id, map_sha256,
                 norm_retrieval_set_id, frozen_input_digest)
            VALUES (:group_id, :ordinal, :scope_id, :run_id, :map_sha256,
                    :set_id, :digest)
        """), {
            "group_id": group_id, "ordinal": ordinal, "scope_id": scope.scope_id,
            "run_id": run_id, "map_sha256": scope.identity.map_sha256,
            "set_id": ref.set_id, "digest": digest,
        })
    commands.succeed(session, claimed.command_id, {
        "group_id": group_id,
        "relaxed_limits": relaxed_limits,
        **({"cost_consent": dict(approved_cost, run_limits_micros=run_limits)} if approved_cost is not None else {}),
    })
    return StartedGroup(get_ar_v3_group(session, group_id), False)
