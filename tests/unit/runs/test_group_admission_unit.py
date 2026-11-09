"""`EXEC2-GROUP-RUN-01` (ADR-0026 decisions 12 and 13): the run-start command admits a Run on a group, and only then.

Container-free, in the manner of ``test_executor_choice.py``: the ledger, the run and document repositories, the session, the
route freezer and the group admitter are fakes that record what they were handed. B3 section 11 is not in the repository, so
the numbers below are the task file's reading of it (the integrator re-maps them):

* **3 -- admission freezes intent, not an executor.** A start that names a group, or that names nothing while the routing
  mode is ``rules``, writes the run ``pending`` with the group revision (and the rule revision when a rule routed it) and
  **no connection revision**; the route freezer is never called; one ``audit_run.group_admitted`` event carries
  classifiers only;
* **4 -- the selectors are exclusive** and the refusals precede the key's claim: a group with a connection, a group with a
  preset, the ``environment`` source (no admitter), and the admitter's own typed refusals (unknown group, archived group,
  no rule) leave no run, no event and no ledger call;
* **18 -- everything else is what it was.** The routing mode ``legacy`` with no selector, an explicit connection and a
  preset are written ``frozen_at_start`` exactly as before: the fingerprint is the literal every earlier key holds, the
  admitter is not even asked about a connection or a preset, and a replayed key consults no admitter;
* **20 -- a re-audit keeps the kind of selector the original start used.** A named connection stays that connection; a
  source admitted on a named group is admitted again on that group; a source routed by a rule names nothing, so the
  re-audit follows today's mode; an archived group refuses it and writes nothing.

What PostgreSQL does with the same rows is in ``tests/integration/runs/test_group_admission.py``. Written and **not run** in
EXEC-2 (`R-149d`).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.ingest.public import CommandReplay, CommandStarted, payload_fingerprint
from auditmanager.runs.commands import (
    admit_group_for_start,
    reaudit_run,
    refuse_group_conflicts,
    start_audit_run,
    start_run_fingerprint,
)
from auditmanager.runs.provider import AdmittedGroup, FrozenRoute
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
PROFILE = "ap_01M2545JSD15ETSNNV904X991A"
BUNDLE = "pb_01M2545JSD15ETSNNV904X991P"
BLOB = "blob_sha256_" + "ab" * 32
SOURCE_RUN = "run_01M2545JSD15ETSNNV904X991K"
PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
COMMAND = "cmd_01M2545JSD15ETSNNV904X991C"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991N"
PRESET = "evt_01M2545JSD15ETSNNV904X991N"
GROUP = "exg_01M2545JSD15ETSNNV904X991G"
OTHER_GROUP = "exg_01M2545JSD15ETSNNV904X992G"
GROUP_REVISION = "exgr_01M2545JSD15ETSNNV904X991R"
RULE_GROUP_REVISION = "exgr_01M2545JSD15ETSNNV904X992R"
RULE_REVISION = "exrr_01M2545JSD15ETSNNV904X991U"
ROUTED_REVISION = "excr_ROUTED"

#: The input basis and the fingerprint of the plain request below on the base tree: what every earlier key holds
#: (the same two literals `test_executor_choice.py` captured for the same request).
BASIS = "edb5162bab84b32ec352ffa4785cc7ab02625c7b92a88c78bec5ccdca2a8c031"
BASE_FINGERPRINT = "62bde5d8d311ce2d73c60ed4c870c7ff03602ff6b540c2bf2ec2e5074fb7f061"


class Ledger:
    def __init__(self, replay_run: str | None = None) -> None:
        self.fingerprints: list[str] = []
        self.succeeded: list[dict[str, Any]] = []
        self._replay_run = replay_run

    def find(self, session: Any, *, command_type: str, idempotency_key: Any) -> Any:
        return None if self._replay_run is None else SimpleNamespace(outcome={"run_id": self._replay_run})

    def begin(self, session: Any, *, command_type: str, idempotency_key: Any, fingerprint: Any) -> Any:
        self.fingerprints.append(str(fingerprint))
        if self._replay_run is not None:
            return CommandReplay(CommandId(COMMAND), {"run_id": self._replay_run})
        return CommandStarted(CommandId(COMMAND))

    def succeed(self, session: Any, command_id: Any, outcome: dict[str, Any]) -> None:
        self.succeeded.append(dict(outcome))


class Runs:
    def __init__(self, source: Any = None, source_choice: str | None = None) -> None:
        self.created: list[dict[str, Any]] = []
        self._source = source
        self._source_choice = source_choice

    def create(self, session: Any, **row: Any) -> None:
        self.created.append(row)

    def get(self, session: Any, run_id: str) -> Any:
        assert self._source is not None and run_id == self._source.run_id
        return self._source

    def find(self, session: Any, run_id: str) -> Any:
        return None

    def chosen_executor_connection(self, session: Any, run_id: str) -> str | None:
        return self._source_choice

    def advance(self, session: Any, **_: Any) -> None:
        return None


class Documents:
    def get_version(self, session: Any, version_uid: Any) -> Any:
        return SimpleNamespace(
            project_uid=PROJECT, text_character_count=None,
            manifest=(SimpleNamespace(role="source.document", blob_id=BLOB),),
        )


class Jobs:
    def enqueue(self, session: Any, *, run_id: str) -> None:
        return None


class Session:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def execute(self, statement: Any, parameters: Any = None) -> Any:
        if str(statement).lstrip().startswith("INSERT INTO audit_event"):
            self.events.append({**parameters, "payload": json.loads(parameters["payload"])})
        return SimpleNamespace(scalar_one_or_none=lambda: None)


class Freezer:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, session: Any, **kwargs: Any) -> FrozenRoute:
        self.calls.append(dict(kwargs))
        named = kwargs.get("connection_id")
        return FrozenRoute(
            revision_id=ROUTED_REVISION if named is None else f"excr_OF_{named[-4:]}",
            input_budget_characters=10**9, chosen_connection_id=named,
        )


class Admitter:
    """The ``GroupAdmitter`` seam: ``mode`` is the routing mode it would read, ``refusal`` what it would raise."""

    def __init__(self, *, mode: str = "legacy", refusal: DomainError | None = None) -> None:
        self.calls: list[str | None] = []
        self.group_reads: list[str] = []
        self._mode = mode
        self._refusal = refusal

    def __call__(self, session: Any, *, group_id: str | None = None) -> AdmittedGroup | None:
        self.calls.append(group_id)
        if self._refusal is not None:
            raise self._refusal
        if group_id is None and self._mode != "rules":
            return None
        if group_id is None:
            return AdmittedGroup(
                group_id=OTHER_GROUP, group_revision_id=RULE_GROUP_REVISION, pin_id="claude-sonnet-5",
                gateway_model="claude-sonnet-5", billing="unmetered", input_budget_characters=10**9,
                rule_revision_id=RULE_REVISION,
            )
        return AdmittedGroup(
            group_id=group_id, group_revision_id=GROUP_REVISION, pin_id="claude-sonnet-5",
            gateway_model="claude-sonnet-5", billing="unmetered", input_budget_characters=10**9,
        )

    def group_of(self, session: Any, group_revision_id: str) -> str | None:
        self.group_reads.append(group_revision_id)
        return GROUP


def _start(ledger: Ledger, runs: Runs, session: Session, freezer: Freezer | None, admitter: Admitter | None,
           **named: Any) -> Any:
    return start_audit_run(
        session, version_uid=VERSION, analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
        provider_mode="recorded", idempotency_key="group-1", commands=ledger, runs=runs,
        documents=Documents(), norms_snapshot=lambda s: None, connection_route=freezer,
        group_admitter=admitter, **named,
    )


def _fingerprint(**named: Any) -> str:
    return str(start_run_fingerprint(
        version_uid=VERSION, analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
        provider_mode="recorded", input_basis_digest_value=BASIS, **named,
    ))


def _nothing_written(ledger: Ledger, runs: Runs, session: Session) -> None:
    assert ledger.fingerprints == [] and ledger.succeeded == []
    assert runs.created == [] and session.events == []


# --- 3: admission freezes intent, not an executor ---------------------------------------------------------------


def test_a_start_that_names_a_group_is_written_pending_with_the_group_revision_and_no_connection() -> None:
    ledger, runs, session, freezer, admitter = Ledger(), Runs(), Session(), Freezer(), Admitter()
    started = _start(ledger, runs, session, freezer, admitter, executor_group_id=GROUP)
    assert admitter.calls == [GROUP]
    assert freezer.calls == [], "no connection is chosen at admission: the route freezer is never asked"
    (row,) = runs.created
    assert row["binding_state"] == "pending"
    assert row["executor_group_revision_id"] == GROUP_REVISION
    assert row["routing_rule_revision_id"] is None, "a named group has no rule revision"
    assert row.get("connection_revision_id") is None and row.get("preset_revision_id") is None
    assert started.replayed is False


def test_a_start_that_names_nothing_is_admitted_by_the_rule_while_the_mode_is_rules() -> None:
    ledger, runs, session, freezer, admitter = Ledger(), Runs(), Session(), Freezer(), Admitter(mode="rules")
    _start(ledger, runs, session, freezer, admitter)
    assert admitter.calls == [None] and freezer.calls == []
    (row,) = runs.created
    assert (row["binding_state"], row["executor_group_revision_id"], row["routing_rule_revision_id"]) == (
        "pending", RULE_GROUP_REVISION, RULE_REVISION), "the rule's immutable group revision, and the rule revision"
    assert row.get("connection_revision_id") is None
    assert ledger.fingerprints == [BASE_FINGERPRINT], "a start that names nothing keeps the payload every earlier key holds"


def test_admission_journals_one_classifier_only_event_beside_the_run() -> None:
    session = Session()
    started = _start(Ledger(), Runs(), session, Freezer(), Admitter(), executor_group_id=GROUP)
    (event,) = session.events
    assert event["event_type"] == "audit_run.group_admitted"
    assert (event["aggregate_type"], event["aggregate_id"]) == ("AuditRun", started.run_id)
    assert event["payload"] == {
        "run_id": started.run_id, "work_kind": "text_analysis", "state": "pending", "reason": "group"}
    ruled = Session()
    _start(Ledger(), Runs(), ruled, Freezer(), Admitter(mode="rules"))
    assert ruled.events[0]["payload"]["reason"] == "rule"
    from auditmanager.jobs.events import _SAFE_KEYS

    assert set(event["payload"]) - {"run_id"} <= _SAFE_KEYS


def test_the_group_is_part_of_the_payload_the_key_is_compared_by_and_a_member_is_not() -> None:
    assert _fingerprint() == BASE_FINGERPRINT
    assert _fingerprint(executor_group_id=GROUP) != BASE_FINGERPRINT
    assert _fingerprint(executor_group_id=GROUP) != _fingerprint(executor_group_id=OTHER_GROUP)
    assert _fingerprint(executor_group_id=GROUP) == str(payload_fingerprint({
        "analysis_profile_id": PROFILE, "frozen_input_digest": BASIS, "prompt_bundle_id": BUNDLE,
        "provider_mode": "recorded", "version_uid": VERSION, "executor_group_id": GROUP}))
    ledger = Ledger()
    _start(ledger, Runs(), Session(), Freezer(), Admitter(), executor_group_id=GROUP)
    assert ledger.fingerprints == [_fingerprint(executor_group_id=GROUP)]


# --- 4: exclusivity and refusals, all before the key is claimed ---------------------------------------------------


@pytest.mark.parametrize(("other", "constraint"), [
    ({"executor_connection_id": CONNECTION}, "conflicts_with_executor_connection_id"),
    ({"preset_id": PRESET}, "conflicts_with_preset_id"),
])
def test_a_group_together_with_a_connection_or_a_preset_is_refused_and_writes_nothing(
    other: dict[str, str], constraint: str,
) -> None:
    ledger, runs, session, admitter = Ledger(), Runs(), Session(), Admitter()
    with pytest.raises(DomainError) as caught:
        _start(ledger, runs, session, Freezer(), admitter, executor_group_id=GROUP, **other)
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(caught.value.detail_fields) == {"field": "executor_group_id", "constraint": constraint}
    assert admitter.calls == [], "the exclusivity is decided before any row is read"
    _nothing_written(ledger, runs, session)


def test_the_environment_source_has_no_admitter_and_refuses_a_group() -> None:
    ledger, runs, session = Ledger(), Runs(), Session()
    with pytest.raises(DomainError) as caught:
        _start(ledger, runs, session, None, None, executor_group_id=GROUP)
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(caught.value.detail_fields) == {"field": "executor_group_id", "constraint": "environment_source"}
    _nothing_written(ledger, runs, session)


@pytest.mark.parametrize("refusal", [
    DomainError(ErrorCode.VALIDATION_FAILED, field="executor_group_id", constraint="unknown_executor_group"),
    DomainError(ErrorCode.CONFLICT, conflict_reason="group_archived"),
    DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="no_rule_for_work_kind"),
])
def test_the_admitters_typed_refusals_stop_the_start_before_the_key_is_claimed(refusal: DomainError) -> None:
    ledger, runs, session = Ledger(), Runs(), Session()
    with pytest.raises(DomainError) as caught:
        _start(ledger, runs, session, Freezer(), Admitter(refusal=refusal), executor_group_id=GROUP)
    assert caught.value is refusal
    _nothing_written(ledger, runs, session)


def test_a_start_with_no_selector_in_rules_mode_and_no_rule_is_refused_not_run_on_the_route() -> None:
    ledger, runs, session, freezer = Ledger(), Runs(), Session(), Freezer()
    refusal = DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="no_rule_for_work_kind")
    with pytest.raises(DomainError):
        _start(ledger, runs, session, freezer, Admitter(mode="rules", refusal=refusal))
    assert freezer.calls == [], "no silent fallback to the legacy route"
    _nothing_written(ledger, runs, session)


def test_the_conflict_helper_is_silent_without_a_group() -> None:
    refuse_group_conflicts(None, CONNECTION, PRESET)  # the connection/preset conflict is the older check's, not this one's


def test_admission_helper_answers_none_for_a_connection_or_a_preset_without_asking() -> None:
    admitter = Admitter(mode="rules")
    assert admit_group_for_start(
        Session(), admitter, executor_group_id=None, executor_connection_id=CONNECTION, preset_id=None) is None
    assert admit_group_for_start(
        Session(), admitter, executor_group_id=None, executor_connection_id=None, preset_id=PRESET) is None
    assert admitter.calls == []


# --- 18: everything else is what it was -------------------------------------------------------------------------


def test_mode_legacy_with_no_selector_follows_the_route_and_is_frozen_at_start() -> None:
    ledger, runs, session, freezer, admitter = Ledger(), Runs(), Session(), Freezer(), Admitter(mode="legacy")
    _start(ledger, runs, session, freezer, admitter)
    assert freezer.calls == [{}], "the route's call: no connection_id keyword"
    (row,) = runs.created
    assert row["connection_revision_id"] == ROUTED_REVISION
    assert "binding_state" not in row and "executor_group_revision_id" not in row, "the defaults are the database's"
    assert ledger.fingerprints == [BASE_FINGERPRINT] and session.events == []


def test_an_explicit_connection_stays_frozen_at_start_whatever_the_mode_says() -> None:
    ledger, runs, session, freezer, admitter = Ledger(), Runs(), Session(), Freezer(), Admitter(mode="rules")
    _start(ledger, runs, session, freezer, admitter, executor_connection_id=CONNECTION)
    assert admitter.calls == [], "a named connection is never admitted by a group"
    assert freezer.calls == [{"connection_id": CONNECTION}]
    (row,) = runs.created
    assert row["connection_revision_id"] == f"excr_OF_{CONNECTION[-4:]}" and "binding_state" not in row


def test_an_environment_start_without_a_selector_is_unchanged() -> None:
    ledger, runs, session = Ledger(), Runs(), Session()
    _start(ledger, runs, session, None, None)
    (row,) = runs.created
    assert row["connection_revision_id"] is None and "binding_state" not in row
    assert ledger.fingerprints == [BASE_FINGERPRINT]


def test_a_replayed_group_start_asks_no_admitter_and_writes_nothing() -> None:
    ledger, runs, session, admitter = Ledger(replay_run=SOURCE_RUN), Runs(), Session(), Admitter()
    started = _start(ledger, runs, session, Freezer(), admitter, executor_group_id=GROUP)
    assert started.replayed is True and started.run_id == SOURCE_RUN
    assert admitter.calls == [] and runs.created == [] and session.events == []
    assert ledger.fingerprints == [_fingerprint(executor_group_id=GROUP)]


# --- 20: a re-audit keeps the kind of selector the original start used ------------------------------------------------


def _source(**admission: Any) -> Any:
    return SimpleNamespace(
        run_id=SOURCE_RUN, project_uid=PROJECT, version_uid=VERSION, state="failed",
        frozen_input_digest="c" * 64, norms_snapshot_id=None,
        # `AR-V3-OPT-IN`: the source's pinned pair (a standard analysis), which a repeat reads.
        analysis_profile_id="ap_01M5M28ZCDD8VPSP1BTAEW92YF", prompt_bundle_id="pb_01M5M28ZCDVCR37BX1884JGSPN", **admission,
    )


def _repeat(ledger: Ledger, runs: Runs, session: Session, freezer: Freezer | None, admitter: Admitter | None) -> Any:
    return reaudit_run(
        session, source_run_id=SOURCE_RUN, roles=frozenset({"expert"}),
        idempotency_key="repeat-1", analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
        provider_mode="recorded", runs=runs, jobs=Jobs(), commands=ledger, documents=Documents(),
        norms_snapshot=lambda s: None, connection_route=freezer, group_admitter=admitter,
        input_budget_characters=10**9,
    )


def test_a_repeat_of_a_named_group_start_is_admitted_again_on_that_group() -> None:
    source = _source(binding_state="bound", executor_group_revision_id=GROUP_REVISION, routing_rule_revision_id=None)
    ledger, runs, session, freezer, admitter = Ledger(), Runs(source), Session(), Freezer(), Admitter()
    _repeat(ledger, runs, session, freezer, admitter)
    assert admitter.group_reads == [GROUP_REVISION], "the group is read back from the source's revision"
    assert admitter.calls == [GROUP], "and admitted again by id: the group's current revision"
    assert freezer.calls == []
    (row,) = runs.created
    assert (row["binding_state"], row["executor_group_revision_id"]) == ("pending", GROUP_REVISION)
    assert row["reaudit_of_run_id"] == SOURCE_RUN


def test_a_repeat_of_a_rule_start_names_nothing_so_today_s_mode_decides() -> None:
    source = _source(
        binding_state="bound", executor_group_revision_id=RULE_GROUP_REVISION, routing_rule_revision_id=RULE_REVISION)
    ledger, runs, session, freezer, admitter = Ledger(), Runs(source), Session(), Freezer(), Admitter(mode="rules")
    _repeat(ledger, runs, session, freezer, admitter)
    assert admitter.group_reads == [] and admitter.calls == [None], "the current rule, not the source's group"
    (row,) = runs.created
    assert (row["binding_state"], row["routing_rule_revision_id"]) == ("pending", RULE_REVISION)

    legacy_admitter, legacy_runs, legacy_freezer = Admitter(mode="legacy"), Runs(source), Freezer()
    _repeat(Ledger(), legacy_runs, Session(), legacy_freezer, legacy_admitter)
    (legacy_row,) = legacy_runs.created
    assert legacy_freezer.calls == [{}] and legacy_row["connection_revision_id"] == ROUTED_REVISION
    assert "binding_state" not in legacy_row, "after a return to legacy the repeat follows the route again"


def test_a_repeat_of_a_named_connection_stays_that_connection_in_rules_mode() -> None:
    source = _source(binding_state="frozen_at_start", executor_group_revision_id=None, routing_rule_revision_id=None)
    ledger, runs, session, freezer, admitter = Ledger(), Runs(source, CONNECTION), Session(), Freezer(), Admitter(mode="rules")
    _repeat(ledger, runs, session, freezer, admitter)
    assert freezer.calls == [{"connection_id": CONNECTION}] and admitter.calls == []
    (row,) = runs.created
    assert "binding_state" not in row


def test_a_repeat_of_a_group_start_whose_group_was_archived_is_refused_and_writes_nothing() -> None:
    source = _source(binding_state="bound", executor_group_revision_id=GROUP_REVISION, routing_rule_revision_id=None)
    ledger, runs, session = Ledger(), Runs(source), Session()
    archived = DomainError(ErrorCode.CONFLICT, conflict_reason="group_archived")
    with pytest.raises(DomainError) as caught:
        _repeat(ledger, runs, session, Freezer(), Admitter(refusal=archived))
    assert caught.value is archived
    _nothing_written(ledger, runs, session)


def test_a_repeat_of_a_group_start_with_no_admitter_is_refused_not_run_on_another_executor() -> None:
    source = _source(binding_state="pending", executor_group_revision_id=GROUP_REVISION, routing_rule_revision_id=None)
    ledger, runs, session = Ledger(), Runs(source), Session()
    with pytest.raises(DomainError) as caught:
        _repeat(ledger, runs, session, Freezer(), None)
    assert dict(caught.value.detail_fields) == {"field": "executor_group_id", "constraint": "environment_source"}
    _nothing_written(ledger, runs, session)


def test_a_repeat_of_an_ordinary_run_is_unchanged_with_an_admitter_wired() -> None:
    source = _source(binding_state="frozen_at_start", executor_group_revision_id=None, routing_rule_revision_id=None)
    ledger, runs, session, freezer, admitter = Ledger(), Runs(source), Session(), Freezer(), Admitter(mode="legacy")
    _repeat(ledger, runs, session, freezer, admitter)
    assert freezer.calls == [{}]
    (row,) = runs.created
    assert row["connection_revision_id"] == ROUTED_REVISION and "binding_state" not in row
    assert ledger.fingerprints == [str(payload_fingerprint(
        {"reaudit_of_run_id": SOURCE_RUN, "frozen_input_digest": "c" * 64}))]
