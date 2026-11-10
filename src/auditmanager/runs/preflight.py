"""Read-only source/model-bound estimates and explicit start cost authority."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import os
import threading

from auditmanager.analysis.public import (
    apply_to_bundle, count_native_text_characters, model_rate_sha256, pinned_models, relaxed_window_characters,
)
from auditmanager.documents.public import DocumentRepository, UPLOAD_KIND_COMPARISON_PDF
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import VersionUid
from auditmanager.storage.public import parse_blob_id

from .commands import (
    _freeze_for, _named_group_of, admit_group_for_start, analysis_source_entry, refuse_selectors_under_layout, route_classified_version,
)
from .provider import AdmittedGroup
from .stage_layout import PHASE_ROWS, STAGE_ROWS, FrozenStagePlan, rows_in_use

#: "The layout was not asked about": ``estimate_run`` then reads the seam the preflight was built with. ``None`` is an answer (the layout
#: is off, or the command already read it), and nothing is read again.
_UNSET = object()


FORMAT = "analysis-cost-preflight/1"
MAX_SAFE_MICROS = 9_007_199_254_740_991

#: `REVIEW-FIX-CMP-SPEC-1102` (S6-04). A comparison PDF stores no `text_character_count`, and counting it parses the whole
#: file (minutes for a drawing set). The count is a pure function of the immutable bytes and the page count, so it is kept per
#: process under ``(blob sha256, page_count)``: the estimate parses once, and the start -- which recomputes the estimate inside
#: its write transaction -- only reads this cache and never parses (see ``parse_native_text``). Integers only; bounded.
_NATIVE_COUNTS_MAX = 256
_NATIVE_COUNTS: "OrderedDict[tuple[str, int], int]" = OrderedDict()
_NATIVE_COUNTS_LOCK = threading.Lock()


def _cached_native_count(key):
    with _NATIVE_COUNTS_LOCK:
        count = _NATIVE_COUNTS.get(key)
        if count is not None:
            _NATIVE_COUNTS.move_to_end(key)
        return count


def _remember_native_count(key, count):
    with _NATIVE_COUNTS_LOCK:
        _NATIVE_COUNTS[key] = count
        _NATIVE_COUNTS.move_to_end(key)
        while len(_NATIVE_COUNTS) > _NATIVE_COUNTS_MAX:
            _NATIVE_COUNTS.popitem(last=False)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _invalid(field, constraint):
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint)


#: `V3-OPTIN-01` (R-154b). A bare name, so that the contract test of the compose forwarding reads it as the code default of the plan switch.
EXTENDED_PLAN_DEFAULT = "v2"


def _requested_extended_plan() -> str:
    """The plan name a fresh extended analysis asks for, read from the server environment in this one place.

    The stages of plan v3 (the cross-window check, the parameter passport, the critic and the correction) are opt-in:
    ``AUDITMANAGER_EXTENDED_ANALYSIS_PLAN`` unset or blank is ``v2``, and only ``v3`` (or ``extended-review-v3``) turns them on. A name that
    is neither is not repaired here; the caller refuses it as ``unsupported_plan``."""
    return os.environ.get("AUDITMANAGER_EXTENDED_ANALYSIS_PLAN", EXTENDED_PLAN_DEFAULT).strip().lower() or EXTENDED_PLAN_DEFAULT


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
    #: `EXEC2-GROUP-RUN-01`. The group admission this estimate was made on (``None`` for an estimate of a connection,
    #: a preset or the route). The start admits the run on exactly this revision, so the estimate the person consented to
    #: and the group revision the run freezes cannot differ.
    admitted_group: AdmittedGroup | None = None
    #: `HOSTS-LAYOUT-01` (ADR-0028 decision 8, consent v2). The plan this estimate priced -- the cells of the rows the run will call, with
    #: the access chosen now -- or ``None`` for an estimate of the legacy route. The start freezes exactly this plan.
    stage_plan: FrozenStagePlan | None = None

    def as_dict(self):
        return json.loads(self.public_json)

    @property
    def estimate_digest(self):
        return self.as_dict()["estimate_digest"]

    def approve(self, consent, *, actor_user_uid=None):
        if (not isinstance(consent, dict) or set(consent) != {"estimate_digest", "ceiling_micros", "confirmed"}
                or consent.get("confirmed") is not True):
            raise _invalid("cost_consent", "confirmation_required")
        authority = json.loads(self.authority_json)
        if consent["estimate_digest"] != self.estimate_digest:
            if authority.get("stage_plan_digest") is not None:
                # `HOSTS-LAYOUT-01` (ADR-0028 decision 8): the digest of a stage-plan estimate binds the plan, each model's rates and the
                # access it is bought with. Whatever moved since it was read -- an agent went off line and a subscription became an API
                # key, a rate changed -- the consent no longer binds the work: the existing refusal, and the screen reads the start again.
                raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="cost_estimate_binding_changed")
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="run_cost_estimate_stale")
        cap = consent["ceiling_micros"]
        if type(cap) is not int or not 0 <= cap <= MAX_SAFE_MICROS:
            raise _invalid("ceiling_micros", "nonnegative_integer")
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
        if authority.get("executor_group_revision_id") is not None:
            # `EXEC2-GROUP-RUN-01` (ADR-0026 decision 13): the consent envelope of work admitted on a group names the
            # group revision (and the rule revision that routed it), and **no** connection revision: the claim
            # re-checks it against the revision the run froze, and binds a member only if it holds.
            result["executor_group_revision_id"] = authority["executor_group_revision_id"]
            if authority.get("routing_rule_revision_id") is not None:
                result["routing_rule_revision_id"] = authority["routing_rule_revision_id"]
        if uncapped_stats:
            result["uncapped_stats"] = True
        if actor_user_uid is not None:
            result["approved_by_user_uid"] = actor_user_uid
        if "extended_review" in authority:
            result["extended_review"] = authority["extended_review"]
        if "native_page_piece_policy" in authority:
            result["native_page_piece_policy"] = authority["native_page_piece_policy"]
        if authority.get("stage_plan_digest") is not None:
            # Consent v2 (`HOSTS-LAYOUT-01`): the digest of the plan, and per model the rates and the access it was priced with.
            # ``require_approved_model`` holds every call to membership of this map.
            result["stage_plan_digest"] = authority["stage_plan_digest"]
            result["models"] = {line["model_id"]: {"rate_sha256": line["rate_sha256"], "access": line["access"]}
                                for line in authority["models"]}
        return result


class RunCostPreflight:
    """No I/O in construction; every estimate is recomputed in the start transaction."""

    def __init__(self, *, section_profiles, text_profiles, provider_config, provider_mode,
                 connection_route=None, preset_resolver=None, prices=None,
                 blob_store=None, group_admitter=None, stage_plans=None):
        #: `HOSTS-LAYOUT-01`: the seam that reads the stage layout (``stage_plans(session)``: ``None`` while it is off, else the draft).
        #: With it an estimate is by model while the layout is on, whoever asks; without it only an explicit ``stage_plan`` is.
        self.stage_plans = stage_plans
        self.sections, self.profiles = section_profiles, text_profiles
        self.config, self.mode = provider_config, provider_mode
        self.route, self.presets = connection_route, preset_resolver
        self.group_admitter = group_admitter
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

    def _source(self, session, version_uid, version=None, *, parse_native_text=True):
        """``parse_native_text=False`` is the start transaction: a comparison PDF whose count is not already known (cached by an
        earlier estimate of the same bytes) is refused as ``cost_text_count_unavailable`` and never parsed here."""
        version = version or DocumentRepository().get_version(session, VersionUid.parse(version_uid))
        if version.classification is None:
            raise DomainError(ErrorCode.VERSION_CLASSIFICATION_REQUIRED)
        native_characters = version.text_character_count
        if native_characters is None and version.upload_kind == UPLOAD_KIND_COMPARISON_PDF:
            if self.blob_store is None:
                raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_source")
            source = analysis_source_entry(version)
            cache_key = (str(source.sha256), int(version.page_count))
            native_characters = _cached_native_count(cache_key)
            if native_characters is None and parse_native_text:
                native_characters = count_native_text_characters(
                    self.blob_store, parse_blob_id(str(source.blob_id)),
                    expected_sha256=source.sha256, expected_page_count=version.page_count,
                )
                _remember_native_count(cache_key, native_characters)
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

    def _route(self, session, *, executor_connection_id=None, preset_id=None):
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
        billing = "metered" if frozen is None else frozen.billing
        facts = {"model_id": pin.model_id, "rate_sha256": model_rate_sha256(pin), "billing": billing,
                 "provider_mode": self.mode, "connection_revision_id": None if frozen is None else frozen.revision_id,
                 "preset_revision_id": None if chosen is None else chosen.revision_id}
        return pin, facts, frozen, chosen

    def _route_group(self, admitted: AdmittedGroup):
        """The pricing facts of an estimate admitted on a group (`EXEC2-GROUP-RUN-01`, ADR-0026 decision 13).

        A homogeneous group has one pin, one model and one billing, so the estimate follows the group revision's
        ``pin_id`` and no connection: ``connection_revision_id`` is absent and the group revision (and the rule revision
        when a rule routed it) are bound into the digest instead. The rates are the provider lock's for that pin, as for
        every other estimate."""
        pin = next((row for row in self.prices() if row.model_id == admitted.pin_id), None)
        if pin is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="model_price_pin")
        facts = {"model_id": pin.model_id, "rate_sha256": model_rate_sha256(pin), "billing": admitted.billing,
                 "provider_mode": self.mode, "connection_revision_id": None, "preset_revision_id": None,
                 "executor_group_id": admitted.group_id, "executor_group_revision_id": admitted.group_revision_id,
                 "pin_id": admitted.pin_id}
        if admitted.rule_revision_id is not None:
            facts["routing_rule_revision_id"] = admitted.rule_revision_id
        return pin, facts, None, None

    def _value(self, *, version, chars, source, pricing, pin, frozen, chosen, relaxed, scope,
               windows, calls, input_tokens, output_tokens, window_characters=None,
               extended_review=None, native_page_piece_policy=None, admitted=None):
        cost = 0 if pricing["billing"] == "unmetered" else estimated_micros(pin, input_tokens, output_tokens)
        source_sha = _digest(source)
        authority = dict(pricing, format=FORMAT, source_sha256=source_sha,
            window_characters=window_characters,
            max_windows=(max(12, version.page_count) if relaxed and native_page_piece_policy is None else max(12, windows)) if scope == "run" else None,
            relaxed_limits=relaxed, scope=scope, windows=windows, calls=calls,
            input_tokens=input_tokens, output_tokens=output_tokens)
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
        for key in ("connection_revision_id", "preset_revision_id", "executor_group_id", "executor_group_revision_id",
                    "routing_rule_revision_id", "pin_id"):
            if pricing.get(key) is not None:
                public[key] = pricing[key]
        return RunCostEstimateValue(_json(public), _json(authority), frozen, chosen, admitted)

    def _value_planned(self, *, version, chars, source, plan, ledger, relaxed, windows, window_characters, extended_review,
                       native_page_piece_policy):
        """The estimate of a run on the stage layout (consent v2, `HOSTS-LAYOUT-01`): priced **by model**.

        Each cell's calls and tokens belong to the model of that cell; a model is bought one way for the whole run (the access frozen in the
        plan), so a subscription model costs 0 and an API model costs its pinned rates. The blocks row of an ensemble has one cell per leg and
        one for the judge, and every one of them is asked once per block batch, so the row's calls are the base batches times its cells. The digest binds the plan, every model's rate
        digest and access and the source: a start that finds another plan, rate or access holds no consent. ``billing`` is ``unmetered``
        when every cell is on a subscription (pressing the button is the consent), ``metered`` when none is, else ``mixed``.
        """
        totals = {}
        for key, (calls, row_input, row_output) in ledger.items():
            entry = totals.setdefault(plan.cell(key).model_id, [0, 0, 0])
            entry[0] += calls
            entry[1] += row_input
            entry[2] += row_output
        lines = []
        for model_id, (calls, row_input, row_output) in totals.items():
            pin, access = self._pin(model_id), plan.access_of(model_id)
            lines.append({"model_id": model_id, "access": access, "rate_sha256": model_rate_sha256(pin), "calls": calls,
                          "input_tokens": row_input, "output_tokens": row_output,
                          "estimated_cost_micros": 0 if access == "subscription" else estimated_micros(pin, row_input, row_output)})
        cost = sum(line["estimated_cost_micros"] for line in lines)
        billing = {"subscription": "unmetered", "api": "metered", "mixed": "mixed"}[plan.access]
        text_pin = self._pin(plan.cell("text:main").model_id)
        calls, input_tokens, output_tokens = (sum(entry[index] for entry in ledger.values()) for index in range(3))
        pricing = {"model_id": text_pin.model_id, "rate_sha256": model_rate_sha256(text_pin), "billing": billing,
                   "provider_mode": self.mode, "connection_revision_id": None, "preset_revision_id": None}
        authority = dict(pricing, format=FORMAT, source_sha256=_digest(source), window_characters=window_characters,
            max_windows=(max(12, version.page_count) if relaxed and native_page_piece_policy is None else max(12, windows)),
            relaxed_limits=relaxed, scope="run", windows=windows, calls=calls, input_tokens=input_tokens,
            output_tokens=output_tokens, stage_plan_digest=plan.digest, models=lines)
        if extended_review is not None:
            authority["extended_review"] = extended_review
        if native_page_piece_policy is not None:
            authority["native_page_piece_policy"] = native_page_piece_policy
        digest = _digest(authority)
        public = {"estimate_digest": digest, "scope": "run", "version_uid": str(version.version_uid), "provider_mode": self.mode,
            "billing": billing, "model_id": text_pin.model_id, "text_characters": chars, "page_count": version.page_count,
            "windows": windows, "calls": calls, "input_tokens": input_tokens, "output_tokens": output_tokens,
            "estimated_cost_micros": cost, "recommended_ceiling_micros": max(1, (cost * 6 + 4) // 5) if cost else 0,
            "currency": "USD", "relaxed_limits": relaxed, "stage_plan_digest": plan.digest, "models": lines}
        return RunCostEstimateValue(_json(public), _json(authority), None, None, None, plan)

    def extended_plan(self):
        """The extended plan a run started now would be priced and frozen under: ``"v2"``, ``"v3"``, or ``None`` when the extended
        analysis is off (text only). Derived from :meth:`stage_rows_in_use`, so it is the one environment read the estimate makes
        and cannot disagree with it; an unsupported name is refused there (``unsupported_plan``)."""
        rows = self.stage_rows_in_use()
        if rows == ("text",):
            return None
        return "v3" if rows == STAGE_ROWS else "v2"

    def _pin(self, model_id):
        pin = next((row for row in self.prices() if row.model_id == model_id), None)
        if pin is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="model_price_pin")
        return pin

    def stage_rows_in_use(self):
        """The rows of the stage layout a run started now would call: the text analysis alone, or with the v2 or the v3 extended review
        (`HOSTS-LAYOUT-01`; the same environment the estimate reads). The readiness read asks before it prices anything."""
        if os.environ.get("AUDITMANAGER_EXTENDED_ANALYSIS", "1").strip().lower() in {"0", "false", "off"}:
            return ("text",)
        requested = _requested_extended_plan()
        if requested in {"v3", "extended-review-v3"}:
            return STAGE_ROWS
        if requested in {"v2", "extended-review-v2"}:
            return ("text", "blocks", "cross_check", "norms")
        raise _invalid("analysis_workflow", "unsupported_plan")

    def estimate_run(self, session, *, version_uid, executor_connection_id=None, preset_id=None, relaxed_limits=False, version_record=None,
                     allow_native_page_pieces=True, parse_native_text=True, executor_group_id=None, stage_plan=_UNSET):
        if type(relaxed_limits) is not bool:
            raise _invalid("relaxed_limits", "boolean")
        # `HOSTS-LAYOUT-01`: with the stage layout on, the estimate is by model: the plan's cells decide the model, the effort, the answer
        # limit and the access of every phase, and no executor, preset or group is named.
        if stage_plan is _UNSET:
            stage_plan = None if self.stage_plans is None else self.stage_plans(session)
        planned = stage_plan is not None
        if planned:
            refuse_selectors_under_layout(executor_connection_id=executor_connection_id, preset_id=preset_id,
                                          executor_group_id=executor_group_id)
            admitted = None
        else:
            # `EXEC2-GROUP-RUN-01`: exclusivity and the environment refusal come first, before any row is read.
            admitted = admit_group_for_start(session, self.group_admitter, executor_group_id=executor_group_id,
                executor_connection_id=executor_connection_id, preset_id=preset_id)
        version, chars, source = self._source(session, version_uid, version_record, parse_native_text=parse_native_text)
        routed = route_classified_version(version, self.sections)
        resolve = self.profiles.resolve if hasattr(self.profiles, "resolve") else self.profiles
        profile = resolve(routed.analysis_profile_id, routed.prompt_bundle_id)
        plan = text_cell = None
        if planned:
            plan = stage_plan.freeze(self.stage_rows_in_use())
            text_cell = plan.cell("text:main")
            pin, pricing, frozen, chosen = self._pin(text_cell.model_id), None, None, None
        else:
            pin, pricing, frozen, chosen = (
                self._route(session, executor_connection_id=executor_connection_id, preset_id=preset_id)
                if admitted is None else self._route_group(admitted))
        source["image_block_count"] = self._image_block_count(version)
        bundle = profile.prompt_bundle
        window = relaxed_window_characters(pin.model_id, apply_to_bundle(bundle, text_cell))
        # Per cell ledger of the plan: [calls, input tokens, output tokens]. Every addition below is made to the totals (the legacy route) and
        # to the cells of the row it belongs to; a plan prices the cells by model and the totals are their sum. A row has one cell, except
        # the blocks row of an ensemble: each of its legs and its judge is asked once per batch, so each carries the row's calls.
        ledger = {cell.cell_key: [0, 0, 0] for cell in (plan.cells if planned else ())}

        def led(row, calls, input_tokens_added, floor=0):
            """Add ``calls`` calls (and the input tokens of their requests) to every cell of ``row``, each priced at the row's estimate figure
            (at least ``floor`` tokens: a repair of a reply is asked for the larger of the two). The figure prices a call; it caps nothing."""
            if planned:
                for cell in plan.cells_of_row(row):
                    entry = ledger[cell.cell_key]
                    entry[0] += calls
                    entry[1] += input_tokens_added
                    entry[2] += calls * max(floor, cell.estimate_output_tokens)
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
        if planned:
            # The row's estimate figure wins over the relaxed limit's 64000: the layout is the explicit configuration of the call. It prices the
            # call; no answer cap reaches the model (`R-153n`).
            output_tokens = windows * text_cell.estimate_output_tokens
            led("text", windows, input_tokens)
        # A new plan is accepted explicitly. Previous accepted v1/v2 commands keep
        # their historical semantics and never acquire this larger call allowance.
        extended = None
        extra_calls = 0
        if os.environ.get("AUDITMANAGER_EXTENDED_ANALYSIS", "1").strip().lower() not in {"0", "false", "off"}:
            requested = _requested_extended_plan()
            if requested in {"v3", "extended-review-v3"}:
                from auditmanager.analysis.public import estimate_extended_visual_scope, extended_review_bundle_digest
                coverage_mode = os.environ.get("AUDITMANAGER_EXTENDED_COVERAGE", "batched-v1").strip().lower()
                # The section-run bounds (1000 sources, 500 text pages, 63 windows, 900 000 request
                # bytes) hold unless the run asked for relaxed_limits. The worker recognises such a
                # run by the `unbounded_stats` stamp of the batched coverage policy below, so only
                # that coverage mode can lift them (`REVIEW-FIX-BOUNDS-1102`).
                visual = estimate_extended_visual_scope(version=version, blob_store=self.blob_store,
                    relaxed_limits=relaxed_limits and coverage_mode == "batched-v1")
                section = version.classification.section_code
                extended = {"enabled": True, "plan_version": "extended-review-v3",
                    "max_blocks": visual["max_blocks"], "window_size": visual["window_size"],
                    "max_windows": visual["max_windows"], "text_page_limit": visual["text_page_limit"], "review": True,
                    "review_scope": "full_document", "rules_sha256": extended_review_bundle_digest(section), "section_code": section}
                if coverage_mode in {"batched-v1", "batched-fixed-v1"}:
                    from auditmanager.analysis.public import extended_coverage_policy
                    extended.update(extended_coverage_policy(**({"text_characters": chars,
                        "unbounded_stats": relaxed_limits} if coverage_mode == "batched-v1" else {})))
                    # Fresh consent names complete source-sized processing and one
                    # separate semantic repair after a received invalid answer.
                    # Historical frozen plans never acquire these permissions.
                    extended.update(completion_policy="source-complete-v1", semantic_repair_attempts=1)
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
                    for phase, count in limits.items():
                        row = PHASE_ROWS[phase]
                        led(row, visual["max_windows"] * count, visual["max_windows"] * count * 100_000)
                    cross_window_mode = os.environ.get("AUDITMANAGER_EXTENDED_CROSS_WINDOW", "1").strip().lower()
                    if visual["text_page_limit"] > 16 and cross_window_mode not in {"0", "false", "off"}:
                        from auditmanager.analysis.public import extended_cross_window_policy
                        global_policy = extended_cross_window_policy(full_coverage=True)
                        extended["global_cross_window_policy"] = global_policy
                        global_limits = global_policy["call_limits"]
                        global_calls = sum(global_limits.values())
                        # One run-global allowance after local windows, reserved
                        # before consent; a reused reply does not spend it again.
                        extra_calls += global_calls
                        input_tokens += global_calls * 100_000
                        output_tokens += sum(count * (6_000 if phase == "comprehensive_analysis" else 12_000)
                            for phase, count in global_limits.items())
                        for phase, count in global_limits.items():
                            row = PHASE_ROWS[phase]
                            led(row, count, count * 100_000)
                    if os.environ.get("AUDITMANAGER_NORM_PARAGRAPH_CONTEXT", "1").strip().lower() not in {"0", "false", "off"}:
                        from .norm_context import policy as norm_context_policy
                        norm_context = norm_context_policy()
                        extended["norm_paragraph_context_policy"] = norm_context
                        norm_calls = visual["max_windows"] * limits["norm_verification"]
                        norm_calls += extended.get("global_cross_window_policy", {}).get("call_limits", {}).get("norm_verification", 0)
                        # Context augments input on existing calls only; citation/output
                        # schemas and logical request caps are unchanged.
                        input_tokens += norm_calls * norm_context["input_tokens_per_call"]
                        led("norms", 0, norm_calls * norm_context["input_tokens_per_call"])
                elif coverage_mode in {"legacy", "0", "off", "false"}:
                    if planned:
                        # The legacy coverage has no per-phase accounting to price by model.
                        raise _invalid("analysis_coverage", "unsupported_for_stage_plan")
                    extra_calls = visual["max_windows"] * 6
                    input_tokens += visual["max_windows"] * 600_000
                    output_tokens += visual["max_windows"] * 72_000
                else:
                    raise _invalid("analysis_coverage", "unsupported_plan")
                if chars > 0 and os.environ.get("AUDITMANAGER_PROJECT_PARAMETERS", "1").strip().lower() not in {"0", "false", "off"}:
                    from auditmanager.analysis.public import project_parameters_policy
                    parameters = project_parameters_policy(section, full_coverage=True, candidate_refusals=True)
                    extended["project_parameters_policy"] = parameters
                    extra_calls += parameters["max_calls"]
                    input_tokens += parameters["max_calls"] * 100_000
                    output_tokens += parameters["max_calls"] * parameters["output_tokens"]
                    led("cross_check", parameters["max_calls"], parameters["max_calls"] * 100_000)
                    if os.environ.get("AUDITMANAGER_PROJECT_PARAMETER_CONTEXT", "1").strip().lower() not in {"0", "false", "off"}:
                        from auditmanager.analysis.public import project_parameter_context_policy
                        parameter_context = project_parameter_context_policy(parameters)
                        extended["project_parameter_context_policy"] = parameter_context
                        # At most two8-image requests in each16-source local window.
                        # Context adds input only; the parameter/visual call counts do not grow.
                        input_tokens += visual["max_windows"] * 2 * parameter_context["input_tokens_per_call"]
                        # The context rides on the block requests: two per window for each cell of the blocks row (each leg and the judge).
                        led("blocks", 0, visual["max_windows"] * 2 * parameter_context["input_tokens_per_call"])
                        if (extended.get("coverage_version") == "batched-v1"
                                and os.environ.get("AUDITMANAGER_PROJECT_PARAMETER_REVIEW_CONTEXT", "1").strip().lower() not in {"0", "false", "off"}):
                            from auditmanager.analysis.public import project_parameter_review_context_policy
                            review_context = project_parameter_review_context_policy(parameters)
                            extended["project_parameter_review_context_policy"] = review_context
                            review_calls = visual["max_windows"] * sum(extended["phase_call_limits"][phase]
                                for phase in review_context["scopes"])
                            review_calls += sum(extended.get("global_cross_window_policy", {}).get("call_limits", {}).get(phase, 0)
                                for phase in review_context["scopes"])
                            input_tokens += review_calls * review_context["input_tokens_per_call"]
                            for phase in review_context["scopes"]:
                                phase_calls = visual["max_windows"] * extended["phase_call_limits"][phase] + extended.get(
                                    "global_cross_window_policy", {}).get("call_limits", {}).get(phase, 0)
                                led(PHASE_ROWS[phase], 0, phase_calls * review_context["input_tokens_per_call"])
                if extended.get("semantic_repair_attempts") == 1:
                    # Reserve one additional received-reply repair for every
                    # initial extended call; actual source-sized work is still
                    # bounded by the accepted monetary ceiling and checkpoints.
                    input_tokens += extra_calls * 100_000
                    output_tokens += extra_calls * 12_000
                    if planned:
                        # The repair of a reply runs on the cell of the phase it repairs: its calls are that row's.
                        for row, row_calls in [(row, ledger[plan.cells_of_row(row)[0].cell_key][0]) for row in plan.rows if row != "text"]:
                            led(row, row_calls, row_calls * 100_000, floor=12_000)
                    extra_calls *= 2
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
                led("blocks", image_calls, image_calls * 40_000)
                led("cross_check", comprehensive_calls, comprehensive_calls * 80_000)
                led("norms", norm_calls, norm_calls * 100_000)
            else:
                raise _invalid("analysis_workflow", "unsupported_plan")
        source.update(profile_sha256=profile.content_sha256, preset_id=preset_id,
            executor_connection_id=executor_connection_id, relaxed_limits=relaxed_limits,
            extended_review=extended, **({"native_page_piece_policy": page_pieces} if page_pieces is not None else {}))
        if planned:
            if {key.partition(":")[0] for key in ledger} != set(rows_in_use(extended)):  # the rows the estimate priced are the rows the consent will hold
                raise _invalid("analysis_workflow", "stage_plan_rows_changed")
            return self._value_planned(version=version, chars=chars, source=source, plan=plan, ledger=ledger,
                relaxed=relaxed_limits, windows=windows, window_characters=window, extended_review=extended,
                native_page_piece_policy=page_pieces)
        return self._value(version=version, chars=chars, source=source, pricing=pricing, pin=pin,
            frozen=frozen, chosen=chosen, relaxed=relaxed_limits, scope="run", windows=windows, calls=windows+extra_calls,
            input_tokens=input_tokens, output_tokens=output_tokens, window_characters=window,
            extended_review=extended, native_page_piece_policy=page_pieces, admitted=admitted)

    def estimate_reaudit(self, session, *, run_id, version_record=None, parse_native_text=True, stage_plan=_UNSET):
        from .repository import RunRepository
        runs = RunRepository()
        source_run = runs.get(session, run_id)
        if stage_plan is _UNSET:
            stage_plan = None if self.stage_plans is None else self.stage_plans(session)
        # `HOSTS-LAYOUT-01`: with the layout on, a repeat takes today's plan whatever the source ran on; its named connection or group is
        # not carried over (the stand chooses the servers).
        executor = None if stage_plan is not None else runs.chosen_executor_connection(session, run_id)
        # `EXEC2-GROUP-RUN-01`: a re-audit keeps the kind of selector the original start used. A named connection stays
        # that connection, a named group is admitted again on its current revision, and a start that named nothing
        # (the route, or a rule) names nothing now either: today's mode decides.
        value = self.estimate_run(session, version_uid=source_run.version_uid,
            executor_connection_id=executor, version_record=version_record,
            parse_native_text=parse_native_text,
            executor_group_id=None if stage_plan is not None else _named_group_of(session, source_run, executor, self.group_admitter),
            stage_plan=stage_plan)
        authority = json.loads(value.authority_json)
        # A fresh approval is for this new re-audit, never the parent's paid work.
        authority["reaudit_of_run_id"] = run_id
        public = value.as_dict()
        public["estimate_digest"] = _digest(authority)
        return RunCostEstimateValue(_json(public), _json(authority), value.frozen_route, None, value.admitted_group, value.stage_plan)

    def estimate_from_stage(self, session, *, run_id, start_stage_id, version_record=None, parse_native_text=True, stage_plan=_UNSET):
        """`R-151i`: the price of a run started from ``start_stage_id`` of ``run_id``, for the stages it computes.

        A run that reuses the stage outputs before the chosen stage prices only the stages from it on. Every model call of
        a PC-01 run is made by ``text_analysis`` (and the extended review inside it), and a chosen stage is never after it,
        so the priced work is that stage's: what changes is which stages are *not* done again, and the answer names both
        (``reused_stage_ids``, ``computed_stage_ids``). The reuse rule is asked here, with this estimate's own extended-review
        plan, so a stage that cannot be taken is refused as a price is asked and not after it is consented to. The consent is
        bound to this source and stage: a digest from ``estimate_reaudit`` or from another stage is ``run_cost_estimate_stale``.
        """
        from .stage_reuse import plan_stage_reuse, require_startable_stage, visual_only_pages_allowed
        require_startable_stage(start_stage_id)
        value = self.estimate_reaudit(session, run_id=run_id, version_record=version_record,
            parse_native_text=parse_native_text, stage_plan=stage_plan)
        authority = json.loads(value.authority_json)
        plan = plan_stage_reuse(session, source_run_id=run_id, start_stage_id=start_stage_id,
            visual_only_pages=visual_only_pages_allowed(authority.get("extended_review")))
        # Not a repeat of the parent: a new run that continues it.
        authority.pop("reaudit_of_run_id")
        authority["started_from"] = {"run_id": run_id, "stage_id": start_stage_id,
            "reused": list(plan.reused_stage_ids)}
        public = value.as_dict()
        public.update(start_from_run_id=run_id, start_stage_id=start_stage_id,
            reused_stage_ids=list(plan.reused_stage_ids), computed_stage_ids=list(plan.computed_stage_ids))
        public["estimate_digest"] = _digest(authority)
        return RunCostEstimateValue(_json(public), _json(authority), value.frozen_route, None, value.admitted_group, value.stage_plan)
