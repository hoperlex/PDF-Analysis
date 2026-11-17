"""`RUN-RESTART-01`: the executor of a restart, on the real services (PostgreSQL, MinIO, the recorded provider).

A source run of the extended review v2 is executed for real: the preparation stages on the corpus PDF, the text stage on the recorded provider, then
the block, cross-check and norm calls of a scripted provider that answers them (the extended review has no recording of its own). The source ends
``partial`` -- by a failure injected at one call, or by a norm reply the parser refused -- and a restart run of it is executed. What is measured:

* from **each of the eight chips** the restart makes **no model call for a chip before its own** (the replies are the source's, found in the chain, and a
  replay writes no ``model_call`` row), makes new calls for the chip and the later ones, publishes findings, and replaces its source: the tombstone is
  written in the transaction that moved the run to ``published`` (or ``partial``) and names the restart's own command;
* the text observations are taken **byte for byte**: the same artifact reference, no new ``analysis.text_observations`` blob, and the reply keys reproduce
  (a key that moved would be a refusal, not a call);
* a replay that cannot be made fails the new run with the named reason and chip **before any call**: nothing is published, the source is not
  tombstoned and its decisions are not carried;
* a restart of a restart walks the chain to the run that made a call, and the publication leaves one run of the lineage listed.

The restart runs are written directly (the command refuses a source that did not run the stage layout, and a source here runs without a plan, since a
planned run needs a host and a binding per cell): what is under test is the executor, the replay and the tombstone; the command is
``test_restart_command.py``.
"""

from __future__ import annotations

import json
from hashlib import sha256
from types import SimpleNamespace as NS
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

import auditmanager.decisions.public as decisions_public
import auditmanager.runs.extended_review as extended_review
from auditmanager.access.public import UserRepository
from auditmanager.analysis.public import ProviderMode, model_rate_sha256, pinned_models
from auditmanager.findings import published_finding_count
from auditmanager.ingest.public import CommandRepository, payload_fingerprint
from auditmanager.jobs.public import JobRepository
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.runs.preflight import FORMAT, RunCostEstimateValue
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.restart import RESTART_POINTS, lineage_of, replaced_by, restart_chain
from auditmanager.runs.stage_reuse import REUSED_FROM_METRIC
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey, RunId
from tests.support.v1_reference_profile import resolve_reference_profile

POLICY = {"enabled": True, "max_blocks": "all", "plan_version": "extended-review-v2", "original_review": "deterministic-v1"}
MODEL = "claude-opus-5"
#: What the extended review of the corpus PDF asks of the scripted provider: one batch of eight page images, one cross-check, one norm review.
EXTENDED = ("v2:blocks:0", "v2:comprehensive:0", "v2:norm_verification:0")
ROW_OF = {"v2:blocks:0": "blocks", "v2:comprehensive:0": "cross_check", "v2:norm_verification:0": "norms"}
TEXT_ROLE = "analysis.text_observations"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class V2Preflight:
    """The cost preflight of a run of the extended review v2 on the environment source: the estimate, and the consent it binds."""

    def estimate_run(self, session, *, version_uid, **_kwargs):  # type: ignore[no-untyped-def]
        pin = next(row for row in pinned_models() if row.model_id == MODEL)
        authority = {"format": FORMAT, "source_sha256": sha256(str(version_uid).encode()).hexdigest(), "window_characters": 400_000,
                     "max_windows": 12, "relaxed_limits": False, "scope": "run", "windows": 1, "calls": 4, "input_tokens": 1000,
                     "output_tokens": 1000, "billing": "metered", "model_id": MODEL, "rate_sha256": model_rate_sha256(pin),
                     "provider_mode": "recorded", "connection_revision_id": None, "preset_revision_id": None, "extended_review": POLICY}
        digest = sha256(_json(authority).encode()).hexdigest()
        public = {"estimate_digest": digest, "scope": "run", "version_uid": str(version_uid), "estimated_cost_micros": 1000,
                  "recommended_ceiling_micros": 1200, "currency": "USD"}
        return RunCostEstimateValue(_json(public), _json(authority))


class Provider:
    """The recorded provider for the text stage and a scripted one for the calls of the extended review.

    ``fail`` names the kinds of call that fail (a provider that did not answer); ``bad_norm`` makes the norm reviewer cite a quote the corpus does
    not hold, which the parser refuses -- the norm procedure ends ``partial`` and the run with it, with every call answered and saved."""

    provider_mode = ProviderMode.RECORDED

    def __init__(self, recorded, *, fail: frozenset[str] = frozenset(), bad_norm: bool = False) -> None:
        self.recorded, self.fail, self.bad_norm = recorded, fail, bad_norm
        self.log: list[str] = []

    def complete(self, request):  # type: ignore[no-untyped-def]
        if self.recorded.path_for(request.request_sha256).exists():
            self.log.append("text")
            return self.recorded.complete(request)
        payload = json.loads(request.body["messages"][0]["content"])
        if request.images_bytes:
            kind = "blocks"
        elif payload.get("procedure") == "comprehensive_analysis":
            kind = "comprehensive"
        else:
            kind = "norms"
        self.log.append(kind)
        if kind in self.fail:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="scripted_provider")
        item = {"title": "Сверка", "description": "Уточнить обозначение аппарата", "norm_queries": ["СП 256"]}
        if kind == "blocks":
            values = [{**item, "source_ids": [payload["sources"][0]["source_id"]]}]
        elif kind == "comprehensive":
            values = [{**item, "title": "Комплексная сверка", "source_ids": [payload["native_context"][0]["source_id"]]}]
        else:
            quotes = {c["paragraph_id"]: c["quote"] for c in payload["norm_context"]}
            values = []
            for original in payload["observations"]:
                refs = original["norm_candidate_ids"]
                assessment = None if not refs else {"relation": "insufficient", "explanation": "Требует экспертной сверки",
                    "citations": [{"paragraph_id": refs[0], "quote": "forged" if self.bad_norm else quotes[refs[0]]}]}
                values.append({k: original[k] for k in ("title", "description", "source_ids")}
                              | {"norm_queries": [], "input_ids": [original["input_id"]], "norm_assessment": assessment})
        from auditmanager.analysis.public import ModelResponse

        return ModelResponse(json.dumps({"observations": values}), "end_turn", 100, 100, 1)


@pytest.fixture
def lab(session, seeded, blob_store, provider_config, recorded_adapter, monkeypatch):  # type: ignore[no-untyped-def]
    return Lab(session, seeded, blob_store, provider_config, recorded_adapter, monkeypatch)


class Carries:
    """Stands in for the carry of ``decisions`` (the lane that owns it has not merged): it records what the executor asks of it."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, str]] = []

    def __call__(self, session_factory, *, run_id: str, actor_user_uid: str):  # type: ignore[no-untyped-def]
        self.asked.append((run_id, actor_user_uid))


class Lab:
    def __init__(self, session, seeded, blob_store, provider_config, recorded, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        self.session, self.seeded, self.store, self.config, self.recorded = session, seeded, blob_store, provider_config, recorded
        self.runs, self.ledger = RunRepository(), CommandRepository()
        self.actor = str(UserRepository().create_user(session, "restart-" + uuid4().hex, "restart-test-password").user_uid)
        self.snapshot = "ns_" + uuid4().hex[:26].upper()
        # A norms corpus the lookup can find a paragraph in: a snapshot row (no foreign keys are needed of it) and a search that answers one hit.
        session.execute(text("SET LOCAL session_replication_role = replica"))
        session.execute(text(
            "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, content_digest, undated_documents, "
            "document_count, segmentation_profile, repair_count, unreliable_count) VALUES (:s, :k, :k, :d, 0, 1, 'seg', 0, 0)"),
            {"s": self.snapshot, "k": "key-" + self.snapshot, "d": sha256(self.snapshot.encode()).hexdigest()})
        session.execute(text("SET LOCAL session_replication_role = origin"))
        monkeypatch.setattr(extended_review, "search_norms", lambda _session, **kwargs: NS(items=(NS(
            norms_snapshot_id=self.snapshot, norm_document_id="doc", norm_paragraph_id="paragraph", designation="СП", clause_number="1",
            fragment=NS(text="Реальная цитата"), page_label=1),), next_cursor=None))
        self.carries = Carries()
        monkeypatch.setattr(decisions_public, "carry_restart_decisions", self.carries, raising=False)

    # -- runs ---------------------------------------------------------------------------------------------------------------------
    def provider(self, **options: Any) -> Provider:
        return Provider(self.recorded, **options)

    def execute(self, run_id: str, provider: Provider, **options: Any):  # type: ignore[no-untyped-def]
        return execute_run(self.session, run_id, blob_store=self.store, adapter=provider, provider_config=self.config,
                           text_profiles=resolve_reference_profile, **options)

    def source(self, **options: Any) -> str:
        """An executed run of the extended review v2 over the corpus PDF."""
        started = start_audit_run(
            self.session, version_uid=self.seeded.version_uid, analysis_profile_id=self.seeded.analysis_profile_id,
            prompt_bundle_id=self.seeded.prompt_bundle_id, provider_mode="recorded", idempotency_key="rr-" + uuid4().hex,
            cost_preflight=V2Preflight(), cost_consent={"estimate_digest": V2Preflight().estimate_run(
                self.session, version_uid=self.seeded.version_uid).estimate_digest, "ceiling_micros": 5_000_000, "confirmed": True},
            cost_actor_uid=self.actor, norms_snapshot=lambda _session: self.snapshot, started_by_user_uid=self.actor)
        self.source_provider = self.provider(**options)
        self.execute(str(started.run_id), self.source_provider)
        return str(started.run_id)

    def restart(self, source: str, point: str, *, digest: str | None = None) -> str:
        """A restart run of ``source`` as the command writes it: its own command record carrying the source's consent, the source's settings."""
        old = self.runs.get(self.session, source)
        consent = self.session.execute(text("SELECT outcome FROM command_record WHERE command_id = :c"), {"c": old.command_id}).scalar_one()["cost_consent"]
        claimed = self.ledger.begin(self.session, command_type="restart_run", idempotency_key=IdempotencyKey("rr-" + uuid4().hex),
                                    fingerprint=payload_fingerprint({"source": source, "point": point, "n": uuid4().hex}))
        run_id = str(RunId.new())
        self.runs.create(
            self.session, run_id=run_id, project_uid=old.project_uid, version_uid=old.version_uid, analysis_profile_id=old.analysis_profile_id,
            prompt_bundle_id=old.prompt_bundle_id, provider_mode=old.provider_mode, frozen_input_digest=digest or old.frozen_input_digest,
            command_id=str(claimed.command_id), started_from_run_id=source, restart_point=point, norms_snapshot_id=old.norms_snapshot_id,
            started_by_user_uid=self.actor)
        self.ledger.succeed(self.session, claimed.command_id, {"run_id": run_id, "restart_of_run_id": source, "restart_point": point,
                                                                "cost_consent": consent})
        self.runs.advance(self.session, run_id=run_id, from_state="created", to_state="queued")
        JobRepository().enqueue(self.session, run_id=run_id)
        return run_id

    # -- reads --------------------------------------------------------------------------------------------------------------------
    def calls(self, run_id: str) -> tuple[set[str], int]:
        """The extended-review phases the run called a model for, and how many calls were not of the extended review (the text stage's)."""
        rows = self.session.execute(text("SELECT parameters ->> 'extended_phase' FROM model_call WHERE run_id = :r"), {"r": run_id}).scalars().all()
        return {row for row in rows if row is not None}, sum(1 for row in rows if row is None)

    def rows(self, run_id: str) -> dict[str, Any]:
        return {row.stage_id: row for row in self.runs.stage_results(self.session, run_id)}

    def snapshot_of(self, run_id: str):  # type: ignore[no-untyped-def]
        return (self.session.execute(text("SELECT to_jsonb(r) FROM audit_run r WHERE run_id = :r"), {"r": run_id}).scalar_one(),
                self.session.execute(text("SELECT jsonb_agg(to_jsonb(s) ORDER BY stage_id) FROM stage_result s WHERE run_id = :r"), {"r": run_id}).scalar_one(),
                self.session.execute(text("SELECT count(*) FROM model_call WHERE run_id = :r"), {"r": run_id}).scalar_one())

    def listed(self) -> list[str]:
        return [row.run_id for row in self.runs.list_for_version(self.session, self.seeded.version_uid)]


# -- from each chip --------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("point", RESTART_POINTS)
def test_a_restart_from_each_chip_takes_what_is_before_it_computes_the_rest_and_replaces_its_source(lab, point) -> None:  # type: ignore[no-untyped-def]
    source = lab.source(bad_norm=True)
    assert lab.runs.get(lab.session, source).state == "partial"
    made, text_calls = lab.calls(source)
    assert made == set(EXTENDED) and text_calls == 1, "the source made every call once: one text call and the three of the extended review"
    before = lab.snapshot_of(source)
    source_findings = published_finding_count(lab.session, source)
    assert source_findings > 0

    restart = lab.restart(source, point)
    provider = lab.provider()  # a norm reviewer that cites a real quote
    result = lab.execute(restart, provider)

    replayed = {phase for phase in EXTENDED if ROW_OF[phase] in ("blocks", "cross_check", "norms")
                and RESTART_POINTS.index(point) > RESTART_POINTS.index(ROW_OF[phase])}
    taken_text = RESTART_POINTS.index(point) > RESTART_POINTS.index("text")
    made_now, text_now = lab.calls(restart)
    # No model call for a chip before the restart's own; new calls for the chip and every later one.
    assert made_now == set(EXTENDED) - replayed
    assert text_now == (0 if taken_text else 1)
    assert provider.log.count("text") == text_now and len(provider.log) == len(made_now) + text_now
    # The norm reply a restart from «Критик» or «Уточнение» replays is the refused one: the run ends ``partial`` and is published all the same.
    assert result.terminal_state == ("partial" if "v2:norm_verification:0" in replayed else "published")
    assert published_finding_count(lab.session, restart) == source_findings
    # The preparation stages are the source's by reference (except for a full rerun); the text is the source's byte for byte (after «Текст»).
    old, new = lab.rows(source), lab.rows(restart)
    for stage_id in ("source_preparation", "page_geometry_extraction", "document_context_build"):
        assert (REUSED_FROM_METRIC in new[stage_id].metrics) == (point != "preparation"), stage_id
        if point != "preparation":
            assert new[stage_id].artifacts == old[stage_id].artifacts and new[stage_id].metrics[REUSED_FROM_METRIC] == source
    old_text = next(a for a in old["text_analysis"].artifacts if a["role"] == TEXT_ROLE)
    new_text = next(a for a in new["text_analysis"].artifacts if a["role"] == TEXT_ROLE)
    assert (new_text == old_text) == taken_text, "the text blob is the source's own, not a copy, when it is taken"
    published_roles = set(lab.session.execute(text(
        "SELECT DISTINCT artifact_role FROM analysis_artifact_publication WHERE run_id = :r AND stage_id = 'text_analysis'"), {"r": restart}).scalars())
    assert (TEXT_ROLE in published_roles) != taken_text
    if taken_text:
        assert new["text_analysis"].metrics[REUSED_FROM_METRIC] == source
    # The source is exactly what it was (its rows are not rewritten), and it is replaced: one tombstone, written with the restart's own command.
    assert lab.snapshot_of(source) == before
    assert lab.runs.is_deleted(lab.session, source) and replaced_by(lab.session, source) == restart
    command = lab.runs.get(lab.session, restart).command_id
    assert lab.session.execute(text("SELECT command_id FROM audit_run_deletion WHERE run_id = :r"), {"r": source}).scalar_one() == command
    assert lab.listed() == [restart], "exactly one run of the lineage stays listed"
    # The views say so: the new run names its source and its chip (and no start stage), the replaced source names the run that replaced it.
    from auditmanager.bootstrap.adapters import _run_status_view

    new_view, old_view = _run_status_view(lab.session, restart), _run_status_view(lab.session, source)
    assert (new_view.started_from_run_id, new_view.restart_point, new_view.start_stage_id, new_view.replaced_by_run_id) == (source, point, None, None)
    assert (old_view.replaced_by_run_id, old_view.restart_point) == (restart, None)
    # The decisions of the lineage are carried by the step of ``decisions`` after the terminal, for the starter.
    assert lab.carries.asked == [(restart, lab.actor)]


def test_the_replayed_keys_are_the_sources_so_a_restart_makes_no_call_at_all_from_the_last_chip(lab) -> None:  # type: ignore[no-untyped-def]
    source = lab.source(bad_norm=True)
    provider = lab.provider()
    lab.execute(lab.restart(source, "correction"), provider)
    assert provider.log == [], "every reply of the source replayed: the keys reproduce, the questions are the same"


# -- a replay that cannot be made --------------------------------------------------------------------------------------------------------


def _failed_nothing_published(lab, source: str, restart: str, provider: Provider, *, reason: str, point: str, stage: str) -> None:  # type: ignore[no-untyped-def]
    run = lab.runs.get(lab.session, restart)
    assert run.state == "failed" and run.terminal_reason == "analysis_input_invalid"
    assert run.terminal_detail == {"stage_id": stage, "reason": reason, "restart_point": point}
    row = lab.rows(restart)["text_analysis"]
    assert row.status == "failed" and row.error["code"] == "analysis_input_invalid" and row.error["details"] == run.terminal_detail
    assert provider.log == [], "the refusal is before any paid call: no text call, none of the extended review"
    assert lab.calls(restart) == (set(), 0)
    assert published_finding_count(lab.session, restart) == 0, "nothing is published: the evidence gate is not asked"
    assert lab.session.execute(text("SELECT count(*) FROM finding_observation WHERE run_id = :r"), {"r": restart}).scalar_one() == 0
    # The source is neither tombstoned nor replaced, and its decisions are not carried.
    assert not lab.runs.is_deleted(lab.session, source) and replaced_by(lab.session, source) is None
    assert lab.listed() == [restart, source]
    assert lab.carries.asked == []


def test_a_reply_the_chain_does_not_hold_fails_the_new_run_before_any_call_and_publishes_nothing(lab, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import auditmanager.runs.executor as executor

    source = lab.source(fail=frozenset({"comprehensive"}))  # the cross-check never answered: the run ended partial without its reply
    assert lab.runs.get(lab.session, source).state == "partial"
    assert lab.calls(source)[0] == {"v2:blocks:0"}, "a call that did not answer leaves no reply and no model call row"
    restart = lab.restart(source, "norms")
    provider = lab.provider()
    gate_reads: list[str] = []
    original = executor._read_gate_inputs
    monkeypatch.setattr(executor, "_read_gate_inputs", lambda **kwargs: gate_reads.append(kwargs["run_id"]) or original(**kwargs))
    result = lab.execute(restart, provider)
    assert result.terminal_state == "failed"
    assert gate_reads == [], "the evidence gate's inputs are not even read for a run whose replay was refused: in the one_list mode they hold the saved candidates"
    _failed_nothing_published(lab, source, restart, provider, reason="restart_reply_missing", point="cross_check", stage="comprehensive_analysis")
    # From the chip that failed the same source restarts: the cross-check is computed again.
    again = lab.restart(source, "cross_check")
    assert lab.execute(again, lab.provider()).terminal_state in ("published", "partial")


def test_a_question_that_moved_since_the_source_is_refused_as_a_changed_request(lab) -> None:  # type: ignore[no-untyped-def]
    source = lab.source(bad_norm=True)
    restart = lab.restart(source, "cross_check", digest="0" * 64)  # the run froze other inputs: the source digest of every key moved
    provider = lab.provider()
    assert lab.execute(restart, provider).terminal_state == "failed"
    _failed_nothing_published(lab, source, restart, provider, reason="restart_request_changed", point="blocks", stage="block_analysis")


def test_a_text_that_cannot_be_taken_fails_the_new_run_before_any_call(lab) -> None:  # type: ignore[no-untyped-def]
    source = lab.source(bad_norm=True)
    lab.session.execute(text("UPDATE stage_result SET metrics = jsonb_set(metrics, '{pages_analysed}', '1') WHERE run_id = :r AND stage_id = 'text_analysis'"),
                        {"r": source})
    restart = lab.restart(source, "blocks")
    provider = lab.provider()
    assert lab.execute(restart, provider).terminal_state == "failed"
    _failed_nothing_published(lab, source, restart, provider, reason="restart_text_not_reusable", point="text", stage="text_analysis")


# -- the chain ------------------------------------------------------------------------------------------------------------------------


def test_a_restart_of_a_restart_walks_the_chain_to_the_run_that_made_the_call_and_the_publication_leaves_one_run_listed(lab) -> None:  # type: ignore[no-untyped-def]
    source = lab.source(bad_norm=True)
    first = lab.restart(source, "cross_check")
    assert lab.execute(first, lab.provider()).terminal_state == "published"
    assert lab.calls(first)[0] == {"v2:comprehensive:0", "v2:norm_verification:0"}, "the first restart replayed the blocks: its own calls are the later ones"
    assert lab.listed() == [first]
    # A restart of the restart (written directly: the command refuses a run that published) from «Нормы»: the blocks are replayed from the source, two
    # runs up the chain, the cross-check from the first restart, whose own call it is; only the norms are asked again.
    second = lab.restart(first, "norms")
    assert restart_chain(lab.session, second) == [second, first, source]
    provider = lab.provider()
    assert lab.execute(second, provider).terminal_state == "published"
    assert provider.log == ["norms"] and lab.calls(second)[0] == {"v2:norm_verification:0"}
    # One run of the lineage stands, and every other is led to it.
    assert lab.listed() == [second]
    assert {member.run_id: member.tombstoned for member in lineage_of(lab.session, source)} == {source: True, first: True, second: False}
    assert replaced_by(lab.session, source) == second, "the oldest run is led to the run that stands, not to the one in between"
    assert replaced_by(lab.session, first) == second
    assert lab.carries.asked == [(first, lab.actor), (second, lab.actor)]


def test_a_failed_restart_leaves_its_source_listed_and_a_later_restart_replaces_both(lab) -> None:  # type: ignore[no-untyped-def]
    source = lab.source(fail=frozenset({"comprehensive"}))
    refused = lab.restart(source, "norms")
    assert lab.execute(refused, lab.provider()).terminal_state == "failed"
    # A restart of the failed restart is allowed (its source is that run): the text is found in the chain, the run publishes, and the lineage goes.
    third = lab.restart(refused, "blocks")
    assert restart_chain(lab.session, third) == [third, refused, source]
    assert lab.execute(third, lab.provider()).terminal_state in ("published", "partial")
    assert lab.listed() == [third]
    assert replaced_by(lab.session, refused) == third and replaced_by(lab.session, source) == third
    command_of = {row[0]: row[1] for row in lab.session.execute(text("SELECT run_id, command_id FROM audit_run_deletion"))}
    assert command_of[refused] == lab.runs.get(lab.session, third).command_id, "the direct source goes with the restart's command"
    assert command_of[source] != command_of[refused], "every other run of the lineage with a delete command of its own"


# -- the signs of life ------------------------------------------------------------------------------------------------------------------


def test_the_restart_attempt_signals_life_at_its_claim_and_on_every_replayed_reply(lab, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The Attempt is not *live* until its first sign of life, and a replay makes no call that would be one (`R-155c`): the claim, the reused stages, every
    replayed reply and the steps of the end signal on their own."""
    from auditmanager.jobs.public import AttemptContext

    source = lab.source(bad_norm=True)
    signals: list[int] = []
    original = AttemptContext.progress

    def spy(self, now=None):  # type: ignore[no-untyped-def]
        signals.append(len(signals) + 1)
        original(self, now)

    monkeypatch.setattr(AttemptContext, "progress", spy)
    boundaries: list[tuple[str, int]] = []
    claimed: list[int] = []
    lab.execute(lab.restart(source, "correction"), lab.provider(),
                effect_checkpoint=lambda name: boundaries.append((name, len(signals))), checkpoint=lambda: claimed.append(len(signals)))
    assert claimed == [1], "the first sign of life is the claim: it is given before the first stage runs"
    replays = [(name, count) for name, count in boundaries if name == "extended_reply_replayed"]
    assert len(replays) == 3
    between = [count for _, count in boundaries]
    for position, (name, count) in enumerate(boundaries):
        if name == "extended_reply_replayed":
            assert count > between[position - 1], "a replayed reply is a sign of life of its own"
    # The end of the run signals again: the gate, the publication, the tombstones and the carry.
    assert len(signals) > replays[-1][1]
