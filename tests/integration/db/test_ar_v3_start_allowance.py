"""`AR-V3-OPT-IN` on real PostgreSQL: AR v3 is an opt-in analysis, and the default start path never produces it.

* **Switch off = today's behaviour.** While the pack is installed and the deployment has not allowed starts, a group
  start is `409 conflict` / `ar_v3_start_not_enabled` and not one row of any table changes (no command, run, group or
  job). The command's own default is closed, so a caller that forgets the allowance starts nothing. An accepted key
  still replays its group, and a NEW key is refused again.
* **Switch on.** Six runs of the sealed pair, each recording who started it (`R-151v`), each reading back as
  `ar_v3_beta` with its group and scope.
* **Default never v3.** `startRun`'s path (`start_audit_run`) and `reauditRun`'s route a classified АР version to the
  registry's АР profile, with the pack and the allowance on or off, and `reauditRun` of a member of a group is refused
  before its key is claimed.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.analysis.public import AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.api.schemas.runs import run_status_body
from auditmanager.bootstrap.adapters import _run_status_view
from auditmanager.runs.analysis_kind import analysis_kind
from auditmanager.runs.commands import reaudit_run, start_audit_run
from auditmanager.runs.preflight import RunCostPreflight
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.v3_group import start_ar_v3_group
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)
from tests.integration.db.test_ar_v3_run_group import _seed  # type: ignore[import-not-found]

V3 = (str(AR_V3_BETA_PROFILE_ID), str(AR_V3_BETA_BUNDLE_ID))
NOT_ENABLED = "ar_v3_start_not_enabled"
NOT_REPEATABLE = "ar_v3_member_not_repeatable"


def _table_counts(session: Session) -> dict[str, int]:
    """Every base table with its row count: «nothing was written», literally."""
    names = session.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
        "ORDER BY table_name"
    )).scalars().all()
    assert len(names) > 30, "this is not the migrated schema"
    return {name: int(session.execute(text(f'SELECT count(*) FROM "{name}"')).scalar_one()) for name in names}


def _group(session: Session, pack, version: str, key: str, **changes):
    return start_ar_v3_group(
        session, version_uid=version, idempotency_key=key, provider_mode="recorded", pack=pack,
        input_budget_characters=1000, **changes,
    )


def _refused(call, reason: str) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    assert caught.value.code is ErrorCode.CONFLICT, (caught.value.code, caught.value.detail_fields)
    assert caught.value.detail_fields["conflict_reason"] == reason
    return caught.value


def test_with_the_allowance_off_a_pack_alone_starts_nothing_and_writes_nothing(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session, session.begin():
        version, pack = _seed(session)
    with Session(migrated_engine) as session:
        before = _table_counts(session)
        _refused(lambda: _group(session, pack, version, "off-1", start_allowed=False), NOT_ENABLED)
        session.rollback()
        assert _table_counts(session) == before, "the refusal wrote a command, a group, a run or a job"
        assert before["audit_run"] == before["ar_v3_run_group"] == before["job"] == 0


def test_the_command_is_closed_unless_the_caller_opens_it(migrated_engine: Engine) -> None:
    """A call that says nothing about the allowance is a call that does not have it."""
    with Session(migrated_engine) as session, session.begin():
        version, pack = _seed(session)
    with Session(migrated_engine) as session:
        before = _table_counts(session)
        _refused(lambda: _group(session, pack, version, "default-closed"), NOT_ENABLED)
        session.rollback()
        assert _table_counts(session) == before


def test_with_the_allowance_on_six_runs_of_the_sealed_pair_are_created_with_their_starter(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session, session.begin():
        version, pack = _seed(session)
        starter = session.execute(text("SELECT user_uid FROM app_user LIMIT 1")).scalar_one()
        started = _group(session, pack, version, "on-1", start_allowed=True, started_by_user_uid=starter)
        assert started.replayed is False
        members = started.group.members
        assert [m.scope_id for m in members] == ["F1", "F2", "A1", "A2", "S1", "S2"]
        rows = session.execute(text(
            "SELECT run_id, analysis_profile_id, prompt_bundle_id, started_by_user_uid FROM audit_run ORDER BY run_id"
        )).all()
        assert len(rows) == 6
        assert {(r[1], r[2]) for r in rows} == {V3}
        assert {r[3] for r in rows} == {starter}, "each member records who started it (R-151v)"
        member = members[2]
        view = _run_status_view(session, member.run_id)
        assert (view.analysis_kind, view.ar_v3_group_id, view.ar_v3_scope_id) == (
            "ar_v3_beta", started.group.group_id, "A1",
        )
        body = run_status_body(view)
        assert body["analysis_kind"] == "ar_v3_beta" and body["ar_v3_scope_id"] == "A1"
        assert body["started_by_user_uid"] == starter


def test_an_accepted_key_replays_with_the_allowance_off_and_a_new_key_is_refused(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session, session.begin():
        version, pack = _seed(session)
        first = _group(session, pack, version, "replay-1", start_allowed=True)
    with Session(migrated_engine) as session:
        before = _table_counts(session)
        again = _group(session, pack, version, "replay-1", start_allowed=False)
        assert again.replayed is True and again.group.group_id == first.group.group_id
        assert _table_counts(session) == before, "a replay wrote something"
        _refused(lambda: _group(session, pack, version, "replay-2", start_allowed=False), NOT_ENABLED)
        session.rollback()
        assert _table_counts(session) == before


def test_a_member_is_not_repeatable_and_nothing_is_written(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session, session.begin():
        version, pack = _seed(session)
        started = _group(session, pack, version, "repeat-1", start_allowed=True)
    member = started.group.members[0].run_id
    with Session(migrated_engine) as session:
        before = _table_counts(session)
        for roles in (frozenset({"expert"}), frozenset({"admin"})):
            _refused(lambda: reaudit_run(
                session, source_run_id=member, roles=roles, idempotency_key="repeat-v3", provider_mode="recorded",
                analysis_profile_id="ap_01M5M28ZCDD8VPSP1BTAEW92YF", prompt_bundle_id="pb_01M5M28ZCDVCR37BX1884JGSPN",
                input_budget_characters=1000,
            ), NOT_REPEATABLE)
            session.rollback()
        # The estimate of the same repeat is the same refusal, not a price.
        _refused(lambda: RunCostPreflight.estimate_reaudit(None, session, run_id=member), NOT_REPEATABLE)
        session.rollback()
        assert _table_counts(session) == before, "the refusal claimed a key or wrote a run"


def test_the_default_start_and_the_repeat_route_an_ar_version_to_the_registry_profile_never_to_v3(
    migrated_engine: Engine,
) -> None:
    """The pack is installed in the world of this test and the allowance is on; neither is consulted by the default path."""
    table = load_text_profile_registry().section_profiles()
    assert table["AR"] != V3 and V3 not in set(table.values())
    with Session(migrated_engine) as session, session.begin():
        version, pack = _seed(session)
        started = start_audit_run(
            session, version_uid=version, provider_mode="recorded", idempotency_key="default-start",
            section_profiles=table, input_budget_characters=1_000_000,
        )
        run = RunRepository().get(session, started.run_id)
        assert (run.analysis_profile_id, run.prompt_bundle_id) == table["AR"]
        assert analysis_kind(run.analysis_profile_id, run.prompt_bundle_id) == "standard"
        view = _run_status_view(session, started.run_id)
        assert (view.analysis_kind, view.ar_v3_group_id, view.ar_v3_scope_id) == ("standard", None, None)
        assert "ar_v3_group_id" not in run_status_body(view) and run_status_body(view)["analysis_kind"] == "standard"
        # Terminal, then repeated: the repeat routes by the section now, to the same registry profile.
        runs = RunRepository()
        runs.advance(session, run_id=started.run_id, from_state="created", to_state="queued")
        runs.advance(session, run_id=started.run_id, from_state="queued", to_state="running")
        runs.terminate(session, run_id=started.run_id, from_state="running", to_state="failed",
                       terminal_reason=ErrorCode.ANALYSIS_FAILED.value)
        repeat = reaudit_run(
            session, source_run_id=started.run_id, roles=frozenset({"expert"}), idempotency_key="default-repeat",
            provider_mode="recorded", section_profiles=table, input_budget_characters=1_000_000,
        )
        repeated = runs.get(session, repeat.run_id)
        assert (repeated.analysis_profile_id, repeated.prompt_bundle_id) == table["AR"]
        # And a group started beside it does not change what the default path does with the same version.
        _group(session, pack, version, "group-beside", start_allowed=True)
        again = start_audit_run(
            session, version_uid=version, provider_mode="recorded", idempotency_key="default-start-2",
            section_profiles=table, input_budget_characters=1_000_000,
        )
        assert (runs.get(session, again.run_id).analysis_profile_id,) == (table["AR"][0],)
        assert session.execute(text(
            "SELECT count(*) FROM ar_v3_run_group_member WHERE run_id IN (:a, :b, :c)"
        ), {"a": started.run_id, "b": repeat.run_id, "c": again.run_id}).scalar_one() == 0
        assert RunId.parse(started.run_id)
