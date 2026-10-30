"""Read-only source/model-bound estimates and explicit start cost authority."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import os

from auditmanager.analysis.public import count_native_text_characters, model_rate_sha256, pinned_models, relaxed_window_characters
from auditmanager.documents.public import DocumentRepository, UPLOAD_KIND_COMPARISON_PDF
from auditmanager.norms.public import PromotionRefused, current_snapshot, qualification, select_verified_retrieval_set
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import VersionUid
from auditmanager.storage.public import parse_blob_id

from .commands import _freeze_for, analysis_source_entry, route_classified_version


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
        authority = json.loads(self.authority_json)
        uncapped_stats = (authority["scope"] == "run" and authority["relaxed_limits"] is True
                          and cap == 0)
        if not uncapped_stats and cap < self.as_dict()["estimated_cost_micros"]:
            raise _invalid("ceiling_micros", "below_estimate")
        if authority["billing"] == "metered" and cap == 0 and not uncapped_stats:
            raise _invalid("ceiling_micros", "positive_metered_limit")
        result = {"estimate_digest": self.estimate_digest, "ceiling_micros": cap,
            "billing": authority["billing"], "model_id": authority["model_id"],
            "rate_sha256": authority["rate_sha256"], "connection_revision_id": authority.get("connection_revision_id"),
            "window_characters": authority.get("window_characters"), "max_windows": authority.get("max_windows"),
            "source_sha256": authority["source_sha256"], "format": FORMAT}
        if uncapped_stats:
            result["uncapped_stats"] = True
        if actor_user_uid is not None:
            result["approved_by_user_uid"] = actor_user_uid
        if "extended_review" in authority:
            result["extended_review"] = authority["extended_review"]
        if "native_page_piece_policy" in authority:
            result["native_page_piece_policy"] = authority["native_page_piece_policy"]
        if "scope_costs_micros" in authority:
            result["scope_costs_micros"] = authority["scope_costs_micros"]
        return result


class RunCostPreflight:
    """No I/O in construction; every estimate is recomputed in the start transaction."""

    def __init__(self, *, section_profiles, text_profiles, provider_config, provider_mode,
                 connection_route=None, preset_resolver=None, pack_registry=None, prices=None,
                 blob_store=None):
        self.sections, self.profiles = section_profiles, text_profiles
        self.config, self.mode = provider_config, provider_mode
        self.route, self.presets, self.packs = connection_route, preset_resolver, pack_registry
        self.prices = prices or pinned_models
        self.blob_store = blob_store

    def _image_block_count(self, version):
        member = next((item for item in version.manifest
            if str(item.role) == "source.structured_companion"), None)
        if member is None or self.blob_store is None:
            return None
        raw = self.blob_store.read(parse_blob_id(member.blob_id), verify=True)
        try:
            if (len(raw) != member.size_bytes or hashlib.sha256(raw).hexdigest() != member.sha256):
                raise ValueError()
            document = json.loads(raw)
            blocks = document["blocks"]
            # The portal contract also admits stamp blocks. They are not image
            # inputs for the model and must not make the cost estimate fail.
            if not isinstance(blocks, list) or any(not isinstance(block, dict)
                    or block.get("block_type") not in {"image", "text", "stamp"} for block in blocks):
                raise ValueError()
            return sum(block["block_type"] == "image" for block in blocks)
        except (KeyError, TypeError, ValueError):
            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis",
                reason="cost_blocks_source_invalid") from None

    def _source(self, session, version_uid, version=None):
        version = version or DocumentRepository().get_version(session, VersionUid.parse(version_uid))
        if version.classification is None:
            raise DomainError(ErrorCode.VERSION_CLASSIFICATION_REQUIRED)
        native_characters = version.text_character_count
        if native_characters is None and version.upload_kind == UPLOAD_KIND_COMPARISON_PDF:
            if self.blob_store is None:
                raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_source")
            source = analysis_source_entry(version)
            native_characters = count_native_text_characters(
                self.blob_store, parse_blob_id(str(source.blob_id)),
                expected_sha256=source.sha256, expected_page_count=version.page_count,
            )
        if type(native_characters) is not int or native_characters < 0:
            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="cost_text_count_unavailable")
        chars = native_characters + (version.recognised_character_count or 0)
        facts = {"version_uid": str(version.version_uid), "sha256": version.sha256,
            "native_characters": native_characters, "recognised_characters": version.recognised_character_count,
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
               windows, calls, input_tokens, output_tokens, window_characters=None, scope_costs=None,
               extended_review=None, native_page_piece_policy=None):
        cost = (sum(scope_costs.values()) if scope_costs is not None else
                0 if pricing["billing"] == "unmetered" else estimated_micros(pin, input_tokens, output_tokens))
        source_sha = _digest(source)
        authority = dict(pricing, format=FORMAT, source_sha256=source_sha,
            window_characters=window_characters,
            max_windows=(max(12, version.page_count) if relaxed and native_page_piece_policy is None else max(12, windows)) if scope == "run" else None,
            relaxed_limits=relaxed, scope=scope, windows=windows, calls=calls,
            input_tokens=input_tokens, output_tokens=output_tokens)
        if scope_costs is not None:
            authority["scope_costs_micros"] = scope_costs
        if extended_review is not None:
            authority["extended_review"] = extended_review
        if native_page_piece_policy is not None:
            authority["native_page_piece_policy"] = native_page_piece_policy
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

    def estimate_run(self, session, *, version_uid, executor_connection_id=None, preset_id=None, relaxed_limits=False, version_record=None,
                     allow_native_page_pieces=True):
        if type(relaxed_limits) is not bool:
            raise _invalid("relaxed_limits", "boolean")
        version, chars, source = self._source(session, version_uid, version_record)
        routed = route_classified_version(version, self.sections)
        resolve = self.profiles.resolve if hasattr(self.profiles, "resolve") else self.profiles
        profile = resolve(routed.analysis_profile_id, routed.prompt_bundle_id)
        pin, pricing, frozen, chosen = self._route(session, executor_connection_id=executor_connection_id, preset_id=preset_id)
        source["image_block_count"] = self._image_block_count(version)
        bundle = profile.prompt_bundle
        window = relaxed_window_characters(pin.model_id, bundle)
        if window <= 0:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_window_policy")
        # Ordered whole-page packing can require twice the aggregate quotient;
        # never estimate fewer than that conservative bound without parsing pages.
        windows = 1 if chars + version.page_count * 32 <= window else min(version.page_count,
            max(2, 2 * math.ceil((chars + version.page_count * 32) / window)))
        page_pieces = None
        if allow_native_page_pieces and os.environ.get("AUDITMANAGER_NATIVE_PAGE_PIECES", "1").strip().lower() not in {"0", "false", "off"}:
            from auditmanager.analysis.public import native_page_piece_policy
            page_pieces = native_page_piece_policy()
            rendered_upper = 2 * chars + version.page_count * page_pieces["page_frame_characters"]
            if rendered_upper > window:
                available = window - page_pieces["frame_characters"] - 1024
                if available <= 0:
                    raise _invalid("analysis_window_policy", "page_piece_frame_exceeds_window")
                # Native text is splittable; recognised blocks remain indivisible.
                # Next-fit packing needs at most twice the total rendered weight
                # quotient plus one. Escaped recognised text and page labels are
                # included conservatively, without a page_count call cap.
                windows = max(windows, 2 * math.ceil(rendered_upper / available) + 1)
        fixed = len(bundle.system_prompt) + len(_json(bundle.response_schema)) + 12_000
        input_characters = 2 * chars + fixed * windows
        if page_pieces is not None:
            input_characters += (version.page_count * page_pieces["page_frame_characters"]
                + windows * page_pieces["frame_characters"])
        input_tokens = math.ceil(Fraction(input_characters * 5, 7))
        output_tokens = windows * (64_000 if relaxed_limits else bundle.max_output_tokens)
        # A new plan is accepted explicitly. Previous accepted v1/v2 commands keep
        # their historical semantics and never acquire this larger call allowance.
        extended = None
        extra_calls = 0
        if os.environ.get("AUDITMANAGER_EXTENDED_ANALYSIS", "1").strip().lower() not in {"0", "false", "off"}:
            requested = os.environ.get("AUDITMANAGER_EXTENDED_ANALYSIS_PLAN", "v3").strip().lower()
            if requested in {"v3", "extended-review-v3"}:
                from auditmanager.analysis.public import estimate_extended_visual_scope, extended_review_bundle_digest
                visual = estimate_extended_visual_scope(version=version, blob_store=self.blob_store)
                section = version.classification.section_code
                extended = {"enabled": True, "plan_version": "extended-review-v3",
                    "max_blocks": visual["max_blocks"], "window_size": visual["window_size"],
                    "max_windows": visual["max_windows"], "text_page_limit": visual["text_page_limit"], "review": True,
                    "review_scope": "full_document", "rules_sha256": extended_review_bundle_digest(section), "section_code": section}
                coverage_mode = os.environ.get("AUDITMANAGER_EXTENDED_COVERAGE", "batched-v1").strip().lower()
                if coverage_mode in {"batched-v1", "batched-fixed-v1"}:
                    from auditmanager.analysis.public import extended_coverage_policy
                    extended.update(extended_coverage_policy(**({"text_characters": chars,
                        "unbounded_stats": relaxed_limits} if coverage_mode == "batched-v1" else {})))
                    limits = extended["phase_call_limits"]
                    per_window_calls = sum(limits.values())
                    per_window_output = sum(limits[phase] * tokens for phase, tokens in (
                        ("block_analysis", 6_000), ("comprehensive_analysis", 6_000),
                        ("norm_verification", 12_000), ("finding_review", 12_000),
                        ("finding_correction", 12_000)))
                    extra_calls = visual["max_windows"] * per_window_calls
                    # Conservative request envelope; the accepted monetary ceiling
                    # remains authoritative and every actual call is metered.
                    input_tokens += visual["max_windows"] * per_window_calls * 100_000
                    output_tokens += visual["max_windows"] * per_window_output
                    cross_window_mode = os.environ.get("AUDITMANAGER_EXTENDED_CROSS_WINDOW", "1").strip().lower()
                    if visual["text_page_limit"] > 16 and cross_window_mode not in {"0", "false", "off"}:
                        from auditmanager.analysis.public import extended_cross_window_policy
                        global_policy = extended_cross_window_policy()
                        extended["global_cross_window_policy"] = global_policy
                        global_limits = global_policy["call_limits"]
                        global_calls = sum(global_limits.values())
                        # One run-global allowance after local windows, reserved
                        # before consent; a reused reply does not spend it again.
                        extra_calls += global_calls
                        input_tokens += global_calls * 100_000
                        output_tokens += sum(count * (6_000 if phase == "comprehensive_analysis" else 12_000)
                            for phase, count in global_limits.items())
                    if os.environ.get("AUDITMANAGER_NORM_PARAGRAPH_CONTEXT", "1").strip().lower() not in {"0", "false", "off"}:
                        from .norm_context import policy as norm_context_policy
                        norm_context = norm_context_policy()
                        extended["norm_paragraph_context_policy"] = norm_context
                        norm_calls = visual["max_windows"] * limits["norm_verification"]
                        norm_calls += extended.get("global_cross_window_policy", {}).get("call_limits", {}).get("norm_verification", 0)
                        # Context augments input on existing calls only; citation/output
                        # schemas and logical request caps are unchanged.
                        input_tokens += norm_calls * norm_context["input_tokens_per_call"]
                elif coverage_mode in {"legacy", "0", "off", "false"}:
                    extra_calls = visual["max_windows"] * 6
                    input_tokens += visual["max_windows"] * 600_000
                    output_tokens += visual["max_windows"] * 72_000
                else:
                    raise _invalid("analysis_coverage", "unsupported_plan")
                if chars > 0 and os.environ.get("AUDITMANAGER_PROJECT_PARAMETERS", "1").strip().lower() not in {"0", "false", "off"}:
                    from auditmanager.analysis.public import project_parameters_policy
                    parameters = project_parameters_policy(section)
                    extended["project_parameters_policy"] = parameters
                    extra_calls += parameters["max_calls"]
                    input_tokens += parameters["max_calls"] * 100_000
                    output_tokens += parameters["max_calls"] * parameters["output_tokens"]
                    if os.environ.get("AUDITMANAGER_PROJECT_PARAMETER_CONTEXT", "1").strip().lower() not in {"0", "false", "off"}:
                        from auditmanager.analysis.public import project_parameter_context_policy
                        parameter_context = project_parameter_context_policy(parameters)
                        extended["project_parameter_context_policy"] = parameter_context
                        # At most two8-image requests in each16-source local window.
                        # Context adds input only; the parameter/visual call counts do not grow.
                        input_tokens += visual["max_windows"] * 2 * parameter_context["input_tokens_per_call"]
                source["visual_scope"] = visual
            elif requested in {"v2", "extended-review-v2"}:
                extended = {"enabled": True, "max_blocks": "all", "plan_version": "extended-review-v2"}
                possible_images = source["image_block_count"]
                if possible_images is None:
                    possible_images = min(1_000, version.page_count * 100)
                elif possible_images == 0:
                    possible_images = version.page_count
                image_calls = math.ceil(possible_images / 8)
                comprehensive_calls = version.page_count + math.ceil(chars / 40_000) + image_calls + windows
                # Every model call can return forty observations. Reserve one normative
                # batch per forty such results plus the base text windows.
                norm_calls = image_calls + comprehensive_calls + windows
                extra_calls = image_calls + comprehensive_calls + norm_calls
                input_tokens += image_calls * 40_000 + comprehensive_calls * 80_000 + norm_calls * 100_000
                output_tokens += (image_calls + comprehensive_calls) * 6_000 + norm_calls * 12_000
            else:
                raise _invalid("analysis_workflow", "unsupported_plan")
        source.update(profile_sha256=profile.content_sha256, preset_id=preset_id,
            executor_connection_id=executor_connection_id, relaxed_limits=relaxed_limits,
            extended_review=extended, **({"native_page_piece_policy": page_pieces} if page_pieces is not None else {}))
        return self._value(version=version, chars=chars, source=source, pricing=pricing, pin=pin,
            frozen=frozen, chosen=chosen, relaxed=relaxed_limits, scope="run", windows=windows, calls=windows+extra_calls,
            input_tokens=input_tokens, output_tokens=output_tokens, window_characters=window,
            extended_review=extended, native_page_piece_policy=page_pieces)

    def estimate_reaudit(self, session, *, run_id, version_record=None):
        from .repository import RunRepository
        runs = RunRepository()
        source_run = runs.get(session, run_id)
        executor = runs.chosen_executor_connection(session, run_id)
        from auditmanager.analysis.public import AR_V3_BETA_PROFILE_ID
        value = self.estimate_run(session, version_uid=source_run.version_uid,
            executor_connection_id=executor, version_record=version_record,
            allow_native_page_pieces=str(source_run.analysis_profile_id) != str(AR_V3_BETA_PROFILE_ID))
        authority = json.loads(value.authority_json)
        # A fresh approval is for this new re-audit, never the parent's paid work.
        authority["reaudit_of_run_id"] = run_id
        public = value.as_dict()
        public["estimate_digest"] = _digest(authority)
        return RunCostEstimateValue(_json(public), _json(authority), value.frozen_route)

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
