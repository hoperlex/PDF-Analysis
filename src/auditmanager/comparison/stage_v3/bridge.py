"""Original procedures over existing durable units, consent and saved C3 evidence."""
from __future__ import annotations

from types import SimpleNamespace
from sqlalchemy import text

from auditmanager.comparison.ai_jobs.model import AiCallGroup, AiCounts, AiMode
from auditmanager.comparison.stage_ai.planning import StageAiMethod
from auditmanager.comparison.stage_ai.validation import digest, StageAiValidationError
from auditmanager.comparison.stage_text.fragments import extract_fragments
from auditmanager.shared.errors import DomainError, ErrorCode
from . import procedures as p
from .mode import ENGINE, ORIGINAL_SHA
from .report import source_report


class V3Method(StageAiMethod):
    @property
    def bundle_version(self):
        return p.BUNDLE

    def counts(self, session, request):
        revision = request.scope.stage_link_revision_id
        if not revision:
            revision = self._repo.run(session, request.scope.stage_chain_run_id)["revision_id"]
        snapshot = self._repo.revision(session, revision)
        facts, characters, count = [], 0, 0
        for row in snapshot["all_profiles"]:
            profile = self._profiles().read_page_profile(row["profile_id"])
            if (profile.row.profile_blob_id is None or profile.row.content_key != row["content_key"]
                    or profile.row.version_uid != row["version_uid"]):
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_ai_profile_changed")
            fragments = extract_fragments(profile, side=row["side"])
            if not fragments:
                raise StageAiValidationError("v3_native_page_without_text")
            characters += sum(len(f.normalised_text) for f in fragments)
            count += len(fragments)
            facts.append({"profile_id": row["profile_id"], "version_uid": row["version_uid"],
                          "content_key": row["content_key"], "fragment_keys": [f.content_key for f in fragments]})
        if not 2 <= len(facts) <= p.MAX_PAGES or characters > p.MAX_CHARACTERS or count > p.MAX_FRAGMENTS:
            raise StageAiValidationError("v3_native_source_budget")
        self.source_profiles = facts
        self.source_signature = digest({"engine": ENGINE, "bundle": p.BUNDLE, "revision": revision, "profiles": facts})
        # Explicit one-call consent window. Resume estimates the exact next
        # known request rather than charging every possible region in advance.
        selected = None
        run_id = request.scope.stage_chain_run_id
        remaining = request.mode is AiMode.LEFT and run_id and snapshot["fragments"]
        if remaining:
            saved = results(session, run_id)
            for phase in ("review", "classify", "synthesize"):
                plans = p.plans_for(phase, snapshot, saved, request.route.pinned_model if hasattr(request, "route") else "estimate")
                pending = [plan for plan in plans if plan.group_id not in saved]
                if pending:
                    selected = pending[0]
                    break
        groups = () if remaining and selected is None else (
            AiCallGroup(calls=1,
                prompt_chars=selected.prompt_chars if selected is not None else
                    characters + count * 500 + len(p.PROMPTS["MAPPER"]) + len(str(p.schemas.MAP_SCHEMA)) + 5000,
                output_tokens=selected.max_output_tokens if selected is not None else 4000),)
        return AiCounts(groups=groups, units=len(groups), reused=0, sheets=len(facts),
                        pairs=len(snapshot["links"]), versions=len({r["version_uid"] for r in facts}))


def results(session, run_id):
    rows = session.execute(text(
        "SELECT group_id,progress FROM stage_ai_unit WHERE stage_chain_run_id=:run "
        "AND group_id LIKE 'v3:%' AND state='completed' ORDER BY generation,created_at,stage_ai_unit_id"
    ), {"run": run_id}).mappings()
    return {r["group_id"]: r["progress"]["v3_result"] for r in rows
            if r["progress"].get("prompt_bundle_version") == p.BUNDLE and "v3_result" in r["progress"]}


def bundles(runtime, session, *, run_id, snapshot, phase, model):
    try:
        saved = results(session, run_id)
        plans = p.plans_for(phase, snapshot, saved, model)
        if phase == "synthesize" and all(plan.group_id in saved for plan in plans):
            cards = p.canonical_cards(snapshot, saved)
            _changes, _hints, ledger, cov, records = p.reviewed(snapshot, saved)
            report = source_report(snapshot, records, cov, ledger)
            final_key = digest({"engine": ENGINE, "bundle": p.BUNDLE, "cards": cards,
                                "revision": snapshot["stage_link_revision_id"],
                                "source_report_sha256": digest(report)})
            run = runtime._repo.run(session, run_id)
            unit = runtime._repo.unit(session, run_id=run_id, kind="classify", group_id="v3:final:cards",
                source_sha256=final_key, job_id=run["comparison_ai_job_id"], payload={
                    "content_key": final_key, "engine": ENGINE, "prompt_bundle_version": p.BUNDLE,
                    "coverage": cov["summary"], "quality": ledger["summary"], "source_report": report,
                    "immutable_source": {"engine": ENGINE, "original": ORIGINAL_SHA, "bundle": p.BUNDLE,
                                         "card_keys": [digest(card) for card in cards], "source_report_sha256": digest(report)}})
            runtime._repo.save_answer(session, run_id=run_id, kind="classify", unit=unit,
                content_key=final_key, value=cards, model_identity={"engine": ENGINE, "model": model,
                                                               "original_source": ORIGINAL_SHA})
            runtime._repo.update_unit(session, unit["stage_ai_unit_id"], payload=unit["payload"],
                                      state="completed", job_id=run["comparison_ai_job_id"])
        return [(SimpleNamespace(review=SimpleNamespace(group_id=plan.group_id)), (plan,),
                 plan.source_sha256, digest({"v3_plan": plan.content_key})) for plan in plans]
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise StageAiValidationError("v3_procedure_input_invalid") from exc


def finish(phase, plans, responses, snapshot, unit):
    answer = p.parse(plans[0], responses[plans[0].content_key], snapshot)
    unit["payload"]["v3_result"] = answer
    return ([{"experimental_mapper": answer}] if phase == "review" else [] if phase == "classify"
            else {"experimental_procedure": plans[0].payload["_experimental_procedure"], "result": answer})


def public_answer(kind, item, *, group_id, source_sha256):
    """Use sealed classic reader envelopes without pretending V3 ran classic AI.

    The original procedure result stays inspectable in typed audit metadata;
    cards and progress have their own experimental fields for the product UI.
    """
    item = dict(item)
    field = {"review": "decisions", "classify": "cards", "synthesize": "result"}[kind]
    original = item[field]
    item["model_identity"] = dict(item["model_identity"], experimental={
        "engine": ENGINE, "source_version": ORIGINAL_SHA, "group_id": group_id, "result": original})
    if kind == "review":
        item[field] = []  # Mapper is not a SAME/MOVED/CHANGED fragment review.
    elif kind == "classify":
        keys = ("class_name", "category", "title", "system", "evidence_ids", "model_class",
                "policy_reasons", "materiality", "importance", "detail_increased")
        item[field] = [dict({key: card[key] for key in keys if key in card},
            card_key=digest({"class": card["class_name"], "evidence_ids": sorted(card["evidence_ids"])}),
            evidence_digest=digest({"source": card.get("experimental", {}).get("source_sha256", source_sha256),
                                    "evidence_ids": sorted(card["evidence_ids"])})) for card in original]
    else:
        procedure = original["experimental_procedure"]
        item[field] = {"group_id": group_id, "source_sha256": source_sha256, "evidence_ids": [],
            "decision": "EXPERIMENTAL_PROCEDURE", "change_type": procedure,
            "title": "Процедура V3: " + procedure,
            "reason": "Сохранён исходный результат экспериментальной процедуры. Инженерное решение требует проверки эксперта."}
    return item
