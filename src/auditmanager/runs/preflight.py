"""Read-only source/model-bound estimates and explicit start cost authority."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math

from auditmanager.analysis.public import model_rate_sha256, pinned_models, relaxed_window_characters
from auditmanager.documents.public import DocumentRepository
from auditmanager.norms.public import PromotionRefused, current_snapshot, qualification, select_verified_retrieval_set
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import VersionUid

from .commands import _freeze_for, refuse_comparison_only_version, route_classified_version


FORMAT = "analysis-cost-preflight/1"
MAX_SAFE_MICROS = 9_007_199_254_740_991


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _invalid(field, constraint):
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint)


def estimated_micros(pin, input_tokens: int, output_tokens: int) -> int:
    # USD per million tokens × micro-USD per USD cancels the million exactly.
    return math.ceil(input_tokens * Fraction(str(pin.input_per_mtok_usd))
                     + output_tokens * Fraction(str(pin.output_per_mtok_usd)))


@dataclass(frozen=True, slots=True)
class RunCostEstimateValue:
    public_json: str
    authority_json: str
    frozen_route: object | None = None
    chosen_preset: object | None = None

    def as_dict(self):
        return json.loads(self.public_json)

    @property
    def estimate_digest(self):
        return self.as_dict()["estimate_digest"]

    def approve(self, consent, *, actor_user_uid=None):
        if (not isinstance(consent, dict) or set(consent) != {"estimate_digest", "ceiling_micros", "confirmed"}
                or consent.get("confirmed") is not True):
            raise _invalid("cost_consent", "confirmation_required")
        if consent["estimate_digest"] != self.estimate_digest:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="run_cost_estimate_stale")
        cap = consent["ceiling_micros"]
        if type(cap) is not int or not 0 <= cap <= MAX_SAFE_MICROS:
            raise _invalid("ceiling_micros", "nonnegative_integer")
        if cap < self.as_dict()["estimated_cost_micros"]:
            raise _invalid("ceiling_micros", "below_estimate")
        authority = json.loads(self.authority_json)
        if authority["billing"] == "metered" and cap == 0:
            raise _invalid("ceiling_micros", "positive_metered_limit")
        result = {"estimate_digest": self.estimate_digest, "ceiling_micros": cap,
            "billing": authority["billing"], "model_id": authority["model_id"],
            "rate_sha256": authority["rate_sha256"], "connection_revision_id": authority.get("connection_revision_id"),
            "window_characters": authority.get("window_characters"), "max_windows": authority.get("max_windows"),
            "source_sha256": authority["source_sha256"], "format": FORMAT}
        if actor_user_uid is not None:
            result["approved_by_user_uid"] = actor_user_uid
        if "scope_costs_micros" in authority:
            result["scope_costs_micros"] = authority["scope_costs_micros"]
        return result


class RunCostPreflight:
    """No I/O in construction; every estimate is recomputed in the start transaction."""

    def __init__(self, *, section_profiles, text_profiles, provider_config, provider_mode,
                 connection_route=None, preset_resolver=None, pack_registry=None, prices=None):
        self.sections, self.profiles = section_profiles, text_profiles
        self.config, self.mode = provider_config, provider_mode
        self.route, self.presets, self.packs = connection_route, preset_resolver, pack_registry
        self.prices = prices or pinned_models

    def _source(self, session, version_uid, version=None):
        version = version or DocumentRepository().get_version(session, VersionUid.parse(version_uid))
        refuse_comparison_only_version(version)
        if version.classification is None:
            raise DomainError(ErrorCode.VERSION_CLASSIFICATION_REQUIRED)
        if type(version.text_character_count) is not int or version.text_character_count < 0:
            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="cost_text_count_unavailable")
        chars = version.text_character_count + (version.recognised_character_count or 0)
        facts = {"version_uid": str(version.version_uid), "sha256": version.sha256,
            "native_characters": version.text_character_count, "recognised_characters": version.recognised_character_count,
            "page_count": version.page_count,
            "classification": {"section": version.classification.section_code,
                "stage": version.classification.project_stage, "revision": version.classification.revision},
            "manifest": sorted((str(row.role), str(row.blob_id)) for row in version.manifest)}
        return version, chars, facts

    def _route(self, session, *, executor_connection_id=None, preset_id=None, group=False):
        if executor_connection_id is not None and preset_id is not None:
            raise _invalid("preset_id", "conflicts_with_executor_connection_id")
        chosen = None
        if preset_id is not None:
            if self.presets is None:
                raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_preset")
            chosen = self.presets(session, preset_id)
            executor_connection_id = chosen.executor_connection_id
        if executor_connection_id is not None and self.route is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="executor_connection")
        frozen = None if self.route is None else _freeze_for(session, self.route, executor_connection_id)
        model = self.config.model_id if frozen is None else frozen.model_id
        pin = next((row for row in self.prices() if row.model_id == model), None)
        if pin is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="model_price_pin")
        billing = ("unmetered" if group and frozen is None and self.mode == "recorded" else "metered") if frozen is None else frozen.billing
        facts = {"model_id": pin.model_id, "rate_sha256": model_rate_sha256(pin), "billing": billing,
                 "provider_mode": self.mode, "connection_revision_id": None if frozen is None else frozen.revision_id,
                 "preset_revision_id": None if chosen is None else chosen.revision_id}
        return pin, facts, frozen, chosen

    def _value(self, *, version, chars, source, pricing, pin, frozen, chosen, relaxed, scope,
               windows, calls, input_tokens, output_tokens, window_characters=None, scope_costs=None):
        cost = (sum(scope_costs.values()) if scope_costs is not None else
                0 if pricing["billing"] == "unmetered" else estimated_micros(pin, input_tokens, output_tokens))
        source_sha = _digest(source)
        authority = dict(pricing, format=FORMAT, source_sha256=source_sha,
            window_characters=window_characters, max_windows=max(12, windows) if scope == "run" else None,
            relaxed_limits=relaxed, scope=scope, windows=windows, calls=calls,
            input_tokens=input_tokens, output_tokens=output_tokens)
        if scope_costs is not None:
            authority["scope_costs_micros"] = scope_costs
        digest = _digest(authority)
        public = {"estimate_digest": digest, "scope": scope, "version_uid": str(version.version_uid),
            "provider_mode": self.mode, "billing": pricing["billing"], "model_id": pin.model_id,
            "text_characters": chars, "page_count": version.page_count, "windows": windows, "calls": calls,
            "input_tokens": input_tokens, "output_tokens": output_tokens, "estimated_cost_micros": cost,
            "recommended_ceiling_micros": max(1, (cost * 6 + 4) // 5) if pricing["billing"] == "metered" else 0,
            "currency": "USD", "relaxed_limits": relaxed}
        for key in ("connection_revision_id", "preset_revision_id"):
            if pricing.get(key) is not None:
                public[key] = pricing[key]
        return RunCostEstimateValue(_json(public), _json(authority), frozen, chosen)

    def estimate_run(self, session, *, version_uid, executor_connection_id=None, preset_id=None, relaxed_limits=False, version_record=None):
        if type(relaxed_limits) is not bool:
            raise _invalid("relaxed_limits", "boolean")
        version, chars, source = self._source(session, version_uid, version_record)
        routed = route_classified_version(version, self.sections)
        resolve = self.profiles.resolve if hasattr(self.profiles, "resolve") else self.profiles
        profile = resolve(routed.analysis_profile_id, routed.prompt_bundle_id)
        pin, pricing, frozen, chosen = self._route(session, executor_connection_id=executor_connection_id, preset_id=preset_id)
        bundle = profile.prompt_bundle
        window = relaxed_window_characters(pin.model_id, bundle)
        if window <= 0:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_window_policy")
        # Ordered whole-page packing can require twice the aggregate quotient;
        # never estimate fewer than that conservative bound without parsing pages.
        windows = 1 if chars + version.page_count * 32 <= window else min(version.page_count,
            max(2, 2 * math.ceil((chars + version.page_count * 32) / window)))
        fixed = len(bundle.system_prompt) + len(_json(bundle.response_schema)) + 12_000
        input_tokens = math.ceil(Fraction((2 * chars + fixed * windows) * 5, 7))
        output_tokens = windows * (64_000 if relaxed_limits else bundle.max_output_tokens)
        source.update(profile_sha256=profile.content_sha256, preset_id=preset_id,
            executor_connection_id=executor_connection_id, relaxed_limits=relaxed_limits)
        return self._value(version=version, chars=chars, source=source, pricing=pricing, pin=pin,
            frozen=frozen, chosen=chosen, relaxed=relaxed_limits, scope="run", windows=windows, calls=windows,
            input_tokens=input_tokens, output_tokens=output_tokens, window_characters=window)

    def estimate_group(self, session, *, version_uid, relaxed_limits=False, version_record=None):
        from .v3_group import _validate_pack
        if type(relaxed_limits) is not bool:
            raise _invalid("relaxed_limits", "boolean")
        version, chars, source = self._source(session, version_uid, version_record)
        if version.classification.section_code != "AR":
            raise DomainError(ErrorCode.SECTION_PROFILE_UNAVAILABLE)
        pack = None if self.packs is None else self.packs.select_beta()
        if pack is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="ar_v3_trusted_pack")
        profile = _validate_pack(pack)
        current, qualified = current_snapshot(session), qualification(session, profile.snapshot_id)
        if current is None or current.norms_snapshot_id != profile.snapshot_id or qualified is None or not qualified.build_complete or not qualified.sources_confirmed:
            raise DomainError(ErrorCode.REQUIRED_NORM_UNAVAILABLE, reference_kind="norms_snapshot")
        pin, pricing, frozen, chosen = self._route(session, group=True)
        sets, input_tokens, scope_costs = [], 0, {}
        try:
            for scope in pack.scopes:
                ref = select_verified_retrieval_set(session, identity=scope.identity, chunking_profile=scope.chunking_profile)
                if ref.set_id != scope.set_id or ref.set_sha256 != scope.set_sha256:
                    raise ValueError()
                sets.append({"scope": scope.scope_id, "set_id": ref.set_id, "sha256": ref.set_sha256,
                             "bytes": ref.set_size_bytes})
                # The verified artifact's byte size bounds its rendered normative
                # part; JSON quoting of document text is reserved independently.
                characters = chars * 2 + ref.set_size_bytes + len(profile.system_prompt) + len(profile.response_schema_json) + 16_000 + version.page_count * 40
                scope_tokens = math.ceil(Fraction(characters * 5, 7))
                input_tokens += scope_tokens
                scope_costs[scope.scope_id] = 0 if pricing["billing"] == "unmetered" else estimated_micros(
                    pin, scope_tokens, 64_000 if relaxed_limits else 16_000)
        except (PromotionRefused, ValueError):
            raise DomainError(ErrorCode.REQUIRED_NORM_UNAVAILABLE, reference_kind="norm_retrieval_set") from None
        source.update(pack_sha256=pack.sha256, profile_sha256=profile.content_sha256, sets=sets, relaxed_limits=relaxed_limits)
        return self._value(version=version, chars=chars, source=source, pricing=pricing, pin=pin,
            frozen=frozen, chosen=chosen, relaxed=relaxed_limits, scope="ar_v3_group", windows=6, calls=6,
            input_tokens=input_tokens, output_tokens=6 * (64_000 if relaxed_limits else 16_000), scope_costs=scope_costs)
