"""`EXEC-SEAL-01`: the executors commands over real PostgreSQL, one rolled-back transaction each.

Every guard here is shown to be able to fail: the refusal tests assert what was *not* written,
the destination-binding test revises the address and expects ``secret_unreadable`` for the old
secret, and the late-worker test shows a finished probe is not overwritten.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from auditmanager.executors.public import (
    PrivateRing,
    RevisionSettings,
    SecretUnreadableError,
    archive_connection,
    connection_detail,
    create_connection,
    current_revision,
    destination_for,
    generate_ssh_key,
    open_secret,
    pinned_models,
    record_probe_result,
    record_probe_started,
    request_probe,
    resolve_route,
    revise_connection,
    set_route,
    set_secret,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorProbeId
from tests.integration.executors.conftest import ADMIN, make_rings

ADMIN_ROLES = frozenset({"admin"})
PINS = {pin.model_id for pin in pinned_models()}
SENTINEL = "sk-sentinel-ZX81-do-not-leak-0123456789"

HTTP = RevisionSettings(
    pin_id="claude-opus-5", gateway_model="anthropic/claude-opus-5", billing="metered",
    allow_client_documents=False, timeout_seconds=60, api_flavour="openai_chat",
    base_url="https://proxy.test/agent/v1", transport="direct",
)
SSH = RevisionSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="metered",
    allow_client_documents=False, timeout_seconds=120, ssh_host="gpu.test", ssh_port=22,
    ssh_user="am", ssh_profile="claude_code_headless",
)
PULL = RevisionSettings(
    pin_id="claude-sonnet-5", gateway_model="claude-sonnet-5", billing="not_metered",
    allow_client_documents=False, timeout_seconds=600, pull_client="claude_code_session",
    answer_deadline_seconds=600, max_claimed_tasks=1,
)


def key() -> str:
    return f"exec-{uuid4().hex}"


def connection(session, kind: str = "http_api", *, name: str = "proxy") -> str:
    return create_connection(
        session, kind=kind, display_name=name, roles=ADMIN_ROLES, idempotency_key=key(),
        actor_uid=ADMIN,
    ).connection_id


def revise(session, connection_id: str, settings: RevisionSettings = HTTP):
    return revise_connection(
        session, connection_id=connection_id, settings=settings, pinned_model_ids=PINS,
        roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN,
    )


def secret(session, connection_id: str, ring, value: str = SENTINEL, purpose: str = "api_key"):
    return set_secret(
        session, connection_id=connection_id, purpose=purpose, value=value, ring=ring,
        roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN,
    )


def pass_probe(session, connection_id: str) -> None:
    """The worker's act, which `EXEC-HTTP-01` requires before a route: a finished ``ok`` probe
    of the connection's current revision on its current key."""
    probe = request_probe(session, connection_id=connection_id, roles=ADMIN_ROLES,
                          idempotency_key=key(), actor_uid=ADMIN)
    assert record_probe_started(session, probe.probe_id)
    assert record_probe_result(
        session, probe.probe_id, outcome="ok", reported_model="anthropic/claude-opus-5",
        identity_basis="reported", rate_check="not_reported")


def make_routable(session, rings, connection_id: str) -> None:
    """A key on the current revision and an ``ok`` probe of it: what a route to it requires."""
    secret(session, connection_id, rings.public)
    pass_probe(session, connection_id)


def count(session, table: str) -> int:
    return session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def stored(session, table: str, connection_id: str) -> int:
    """Rows of one connection. Counts are per connection, never per table: the sentinel suite
    commits rows on purpose (``pg_dump`` reads its own snapshot) and they are append-only."""
    return session.execute(text(f"SELECT count(*) FROM {table} WHERE connection_id = :c"),
                           {"c": connection_id}).scalar_one()


def refusal(call) -> DomainError:
    with pytest.raises(DomainError) as refused:
        call()
    return refused.value


# --- who may ----------------------------------------------------------------------------------


@pytest.mark.parametrize("roles", [frozenset(), frozenset({"expert"})])
def test_only_an_administrator_writes_and_nothing_is_written_otherwise(session, rings, roles) -> None:
    before = (count(session, "executor_connection"), count(session, "command_record"))
    refused = refusal(lambda: create_connection(
        session, kind="http_api", display_name="x", roles=roles, idempotency_key=key(),
        actor_uid=ADMIN))
    assert refused.code is ErrorCode.PERMISSION_DENIED
    assert (count(session, "executor_connection"), count(session, "command_record")) == before
    cid = connection(session)
    revise(session, cid)
    for call in (
        lambda: revise_connection(session, connection_id=cid, settings=HTTP, pinned_model_ids=PINS,
                                  roles=roles, idempotency_key=key(), actor_uid=ADMIN),
        lambda: archive_connection(session, connection_id=cid, roles=roles,
                                   idempotency_key=key(), actor_uid=ADMIN),
        lambda: set_secret(session, connection_id=cid, purpose="api_key", value=SENTINEL,
                           ring=rings.public, roles=roles, idempotency_key=key(), actor_uid=ADMIN),
        lambda: request_probe(session, connection_id=cid, roles=roles, idempotency_key=key(),
                              actor_uid=ADMIN),
        lambda: set_route(session, work_kind="text_analysis", primary_connection_id=cid,
                          standby_connection_id=None, roles=roles, idempotency_key=key(),
                          actor_uid=ADMIN),
    ):
        assert refusal(call).code is ErrorCode.PERMISSION_DENIED
    assert stored(session, "executor_secret", cid) == 0 == stored(session, "executor_probe", cid)


# --- connections and revisions ----------------------------------------------------------------


def test_a_replay_answers_the_same_connection_and_a_changed_payload_is_a_key_reuse(session) -> None:
    same_key = key()
    first = create_connection(session, kind="http_api", display_name="a", roles=ADMIN_ROLES,
                              idempotency_key=same_key, actor_uid=ADMIN)
    again = create_connection(session, kind="http_api", display_name="a", roles=ADMIN_ROLES,
                              idempotency_key=same_key, actor_uid=ADMIN)
    assert again.connection_id == first.connection_id
    refused = refusal(lambda: create_connection(
        session, kind="http_api", display_name="other", roles=ADMIN_ROLES,
        idempotency_key=same_key, actor_uid=ADMIN))
    assert refused.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_revisions_are_numbered_immutable_and_the_highest_is_current(session) -> None:
    cid = connection(session)
    first = revise(session, cid)
    second = revise(session, cid, replace(HTTP, base_url="https://proxy2.test"))
    assert (first.revision_no, second.revision_no) == (1, 2)
    assert current_revision(session, cid).revision_id == second.revision_id
    stored = session.execute(text(
        "SELECT base_url FROM executor_connection_revision WHERE revision_id = :id"
    ), {"id": first.revision_id}).scalar_one()
    assert stored == "https://proxy.test/agent/v1"  # the first revision is untouched


@pytest.mark.parametrize(("settings", "field", "constraint"), [
    (replace(HTTP, pin_id="not-a-pin"), "pin_id", "model_not_pinned"),
    (replace(HTTP, base_url="https://proxy.test/v1?x=1"), "base_url", "base_url_invalid"),
    (replace(HTTP, base_url="https://proxy.test/v1#f"), "base_url", "base_url_invalid"),
    (replace(HTTP, ssh_profile="custom_command"), "ssh_profile", "field_not_for_kind"),
])
def test_a_refused_revision_writes_nothing(session, settings, field, constraint) -> None:
    cid = connection(session)
    refused = refusal(lambda: revise(session, cid, settings))
    assert refused.code is ErrorCode.VALIDATION_FAILED
    assert refused.detail_fields == {"field": field, "constraint": constraint}
    assert current_revision(session, cid) is None


def test_an_unknown_connection_is_not_found(session) -> None:
    assert refusal(lambda: revise(session, f"exc_{'0' * 26}")).code is ErrorCode.NOT_FOUND


# --- sealed secrets ---------------------------------------------------------------------------


def test_without_a_public_key_a_secret_is_a_typed_refusal_and_nothing_is_stored(session) -> None:
    cid = connection(session)
    revise(session, cid)
    refused = refusal(lambda: secret(session, cid, None))
    assert refused.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert refused.detail_fields == {"dependency": "secrets_public_key_missing"}
    assert stored(session, "executor_secret", cid) == 0
    assert SENTINEL not in str(refused) + repr(refused.detail_fields)


def test_a_secret_needs_a_revision_and_a_purpose_its_kind_holds(session, rings) -> None:
    cid = connection(session)
    assert refusal(lambda: secret(session, cid, rings.public)).detail_fields == {
        "conflict_reason": "no_revision"}
    revise(session, cid)
    refused = refusal(lambda: secret(session, cid, rings.public, purpose="bogus"))
    assert refused.detail_fields["constraint"] == "purpose_not_for_kind"
    pull = connection(session, "pull")
    revise(session, pull, PULL)
    assert refusal(lambda: secret(session, pull, rings.public)).detail_fields == {
        "field": "purpose", "constraint": "purpose_not_for_kind"}
    assert stored(session, "executor_secret", cid) == 0 == stored(session, "executor_secret", pull)


def test_a_secret_is_stored_as_ciphertext_with_its_last_four_and_opens_with_the_private_ring(
    session, rings,
) -> None:
    cid = connection(session)
    revision = revise(session, cid)
    record = secret(session, cid, rings.public)
    row = session.execute(text(
        "SELECT ciphertext, last4, kid, destination FROM executor_secret WHERE secret_id = :id"
    ), {"id": record.secret_id}).one()
    assert SENTINEL.encode() not in bytes(row[0]) and bytes(row[0])
    assert (row[1], row[2], row[3]) == (SENTINEL[-4:], "k1", "direct||https://proxy.test:443")
    destination = destination_for("http_api", revision.settings, "api_key")
    assert open_secret(session, rings.private, secret_id=record.secret_id,
                       destination=destination) == SENTINEL


def test_a_short_secret_shows_no_last_four(session, rings) -> None:
    cid = connection(session)
    revise(session, cid)
    assert secret(session, cid, rings.public, value="short-key").last4 == ""


def test_a_rotation_replaces_the_current_secret_and_keeps_the_revision(session, rings) -> None:
    cid = connection(session)
    revise(session, cid)
    old = secret(session, cid, rings.public)
    new = secret(session, cid, rings.public, value="another-key-9876543210")
    states = dict(session.execute(text(
        "SELECT secret_id, replaced_at IS NULL FROM executor_secret WHERE connection_id = :c"
    ), {"c": cid}).all())
    assert states == {old.secret_id: False, new.secret_id: True}
    assert len(session.execute(text("SELECT 1 FROM executor_connection_revision "
                                    "WHERE connection_id = :c"), {"c": cid}).all()) == 1


def test_a_replay_of_a_secret_answers_the_first_and_stores_one_row(session, rings) -> None:
    cid = connection(session)
    revise(session, cid)
    same_key = key()
    kwargs = dict(connection_id=cid, purpose="api_key", ring=rings.public, roles=ADMIN_ROLES,
                  idempotency_key=same_key, actor_uid=ADMIN)
    first = set_secret(session, value=SENTINEL, **kwargs)
    again = set_secret(session, value=SENTINEL, **kwargs)
    assert again.secret_id == first.secret_id
    assert stored(session, "executor_secret", cid) == 1


# --- the destination binding ------------------------------------------------------------------


def test_revising_the_address_leaves_the_old_secret_unreadable_for_it(session, rings) -> None:
    """A key opens only for the destination it was entered for (plan section 4.1, T-1, T-4)."""
    cid = connection(session)
    old_revision = revise(session, cid)
    record = secret(session, cid, rings.public)
    old_destination = destination_for("http_api", old_revision.settings, "api_key")
    assert open_secret(session, rings.private, secret_id=record.secret_id,
                       destination=old_destination) == SENTINEL

    new_revision = revise(session, cid, replace(HTTP, base_url="https://attacker.test/v1"))
    new_destination = destination_for("http_api", new_revision.settings, "api_key")
    assert new_destination != old_destination
    refused = refusal(lambda: open_secret(
        session, rings.private, secret_id=record.secret_id, destination=new_destination))
    assert isinstance(refused, SecretUnreadableError)
    assert refused.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert refused.detail_fields == {"dependency": "secret_unreadable"}
    # The stored column still names the old destination. It is informational: had the
    # associated data been built from it, the call above would have opened.
    stored = session.execute(text("SELECT destination FROM executor_secret WHERE secret_id = :id"),
                             {"id": record.secret_id}).scalar_one()
    assert stored == old_destination
    # A changed path alone is the same origin and keeps the key; a new transport does not.
    same_origin = revise(session, cid, replace(HTTP, base_url="https://proxy.test/other"))
    assert open_secret(session, rings.private, secret_id=record.secret_id,
                       destination=destination_for("http_api", same_origin.settings, "api_key")
                       ) == SENTINEL
    vpn = revise(session, cid, replace(HTTP, transport="vpn"))
    assert refusal(lambda: open_secret(
        session, rings.private, secret_id=record.secret_id,
        destination=destination_for("http_api", vpn.settings, "api_key"))).code is (
        ErrorCode.DEPENDENCY_UNAVAILABLE)


def test_a_wrong_ring_a_missing_ring_and_a_missing_secret_are_all_unreadable(session, rings) -> None:
    cid = connection(session)
    revision = revise(session, cid)
    record = secret(session, cid, rings.public)
    destination = destination_for("http_api", revision.settings, "api_key")
    stranger = make_rings("k1").private
    other_kid = make_rings("k9").private
    for ring in (stranger, other_kid, None, PrivateRing(keys={})):
        refused = refusal(lambda: open_secret(
            session, ring, secret_id=record.secret_id, destination=destination))
        assert refused.detail_fields == {"dependency": "secret_unreadable"}
        assert SENTINEL not in repr(refused.detail_fields) + str(refused)
    assert refusal(lambda: open_secret(
        session, rings.private, secret_id=f"exs_{'0' * 26}", destination=destination)
    ).detail_fields == {"dependency": "secret_unreadable"}


# --- generated SSH keys -----------------------------------------------------------------------


def test_a_generated_ssh_key_returns_only_its_public_half_and_opens_for_its_endpoint(
    session, rings,
) -> None:
    cid = connection(session, "ssh_command", name="gpu")
    revision = revise(session, cid, SSH)
    generated = generate_ssh_key(
        session, connection_id=cid, ring=rings.public, roles=ADMIN_ROLES,
        idempotency_key=key(), actor_uid=ADMIN)
    assert generated.public_key.startswith("ssh-ed25519 ")
    assert generated.authorized_keys_line == f"restrict {generated.public_key} auditmanager:{cid}"
    assert "PRIVATE" not in repr(generated)
    destination = destination_for("ssh_command", revision.settings, "ssh_private_key")
    assert destination == "ssh_command|gpu.test:22|"
    pem = open_secret(session, rings.private, secret_id=generated.secret.secret_id,
                      destination=destination)
    assert pem.startswith("-----BEGIN OPENSSH PRIVATE KEY-----")
    moved = revise(session, cid, replace(SSH, ssh_host="elsewhere.test"))
    assert refusal(lambda: open_secret(
        session, rings.private, secret_id=generated.secret.secret_id,
        destination=destination_for("ssh_command", moved.settings, "ssh_private_key"))
    ).detail_fields == {"dependency": "secret_unreadable"}


def test_an_ssh_key_needs_an_ssh_endpoint(session, rings) -> None:
    cid = connection(session)
    revise(session, cid)
    refused = refusal(lambda: generate_ssh_key(
        session, connection_id=cid, ring=rings.public, roles=ADMIN_ROLES,
        idempotency_key=key(), actor_uid=ADMIN))
    assert refused.detail_fields == {"field": "purpose", "constraint": "purpose_not_for_kind"}
    tunnel = connection(session, name="tunnel")
    revise(session, tunnel, replace(HTTP, base_url="http://localhost:11434", transport="ssh_tunnel",
                                    ssh_host="gpu.test", ssh_port=22, ssh_user="am"))
    assert generate_ssh_key(session, connection_id=tunnel, ring=rings.public, roles=ADMIN_ROLES,
                            idempotency_key=key(), actor_uid=ADMIN).public_key


# --- probes -----------------------------------------------------------------------------------


def test_a_probe_is_requested_against_the_current_revision_and_its_secret(session, rings) -> None:
    cid = connection(session)
    revision = revise(session, cid)
    record = secret(session, cid, rings.public)
    probe = request_probe(session, connection_id=cid, roles=ADMIN_ROLES, idempotency_key=key(),
                          actor_uid=ADMIN)
    assert (probe.state, probe.outcome, probe.revision_id, probe.secret_id) == (
        "requested", None, revision.revision_id, record.secret_id)
    assert probe.started_at is None and probe.finished_at is None


def test_a_probe_nobody_takes_ends_as_no_worker_and_a_late_worker_changes_nothing(session) -> None:
    cid = connection(session)
    revision = revise(session, cid)
    old = session.execute(text(
        "INSERT INTO executor_probe (probe_id, connection_id, revision_id, state, requested_by, "
        "requested_at) VALUES (:id, :c, :r, 'requested', :a, "
        "clock_timestamp() - interval '121 seconds') RETURNING probe_id"
    ), {"id": str(ExecutorProbeId.new()), "c": cid, "r": revision.revision_id,
        "a": ADMIN}).scalar_one()
    fresh = request_probe(session, connection_id=cid, roles=ADMIN_ROLES, idempotency_key=key(),
                          actor_uid=ADMIN)
    detail = connection_detail(session, cid)
    by_id = {probe.probe_id: probe for probe in detail.probes}
    assert (by_id[old].state, by_id[old].outcome) == ("finished", "no_worker")
    assert by_id[fresh.probe_id].state == "requested"  # younger than 120 s: untouched
    assert record_probe_started(session, old) is False
    assert record_probe_result(session, old, outcome="ok") is False
    assert connection_detail(session, cid).latest_probe_by_revision[revision.revision_id].probe_id == (
        fresh.probe_id)


def test_the_worker_writes_started_then_finished_once(session) -> None:
    cid = connection(session)
    revise(session, cid)
    probe = request_probe(session, connection_id=cid, roles=ADMIN_ROLES, idempotency_key=key(),
                          actor_uid=ADMIN)
    assert record_probe_started(session, probe.probe_id) is True
    assert record_probe_started(session, probe.probe_id) is False
    assert record_probe_result(
        session, probe.probe_id, outcome="model_mismatch", reported_model="some/other-model",
        identity_basis="reported", latency_ms=420, http_status=200, rate_check="checked",
        detail="x" * 900) is True
    assert record_probe_result(session, probe.probe_id, outcome="ok") is False
    finished = connection_detail(session, cid).probes[0]
    assert (finished.state, finished.outcome, finished.reported_model, finished.latency_ms,
            finished.http_status, finished.rate_check, len(finished.detail)) == (
        "finished", "model_mismatch", "some/other-model", 420, 200, "checked", 500)


def test_a_running_probe_whose_worker_vanished_ends_as_timeout(session) -> None:
    cid = connection(session)
    revision = revise(session, cid)
    probe_id = str(ExecutorProbeId.new())
    session.execute(text(
        "INSERT INTO executor_probe (probe_id, connection_id, revision_id, state, requested_by, "
        "started_at) VALUES (:id, :c, :r, 'running', :a, clock_timestamp() - interval '200 seconds')"
    ), {"id": probe_id, "c": cid, "r": revision.revision_id, "a": ADMIN})
    states = {p.probe_id: (p.state, p.outcome) for p in connection_detail(session, cid).probes}
    assert states[probe_id] == ("finished", "timeout")  # 60 s timeout + 30 s margin < 200 s


# --- routes and archive -----------------------------------------------------------------------


def route(session, primary, standby=None, **kwargs):
    return set_route(session, work_kind="text_analysis", primary_connection_id=primary,
                     standby_connection_id=standby, roles=ADMIN_ROLES, idempotency_key=key(),
                     actor_uid=ADMIN, **kwargs)


def test_a_route_resolves_to_the_current_revision_of_each_side_and_is_journaled(
    session, rings
) -> None:
    # `EXEC-HTTP-01`: both sides are served kinds with a key and an ok probe of their current
    # revision (an `ssh_command` side is refused at route time until `EXEC-SSH-01` serves it).
    primary, standby = connection(session, name="p"), connection(session, name="s")
    revise(session, primary)
    revision = revise(session, primary, replace(HTTP, base_url="https://proxy3.test"))
    standby_revision = revise(session, standby, HTTP)
    make_routable(session, rings, primary)
    make_routable(session, rings, standby)
    first = route(session, primary)
    assert first.route_no >= 1
    second = route(session, primary, standby)
    assert second.route_no == first.route_no + 1
    resolved = resolve_route(session, "text_analysis")
    assert resolved.route.route_event_id == second.route_event_id
    assert resolved.primary.revision_id == revision.revision_id
    assert resolved.standby.revision_id == standby_revision.revision_id
    events = session.execute(text(
        "SELECT payload FROM audit_event WHERE event_type = 'executor.route_set' "
        "AND aggregate_id = :id"), {"id": second.route_event_id}).scalars().all()
    assert events == [{"work_kind": "text_analysis", "primary_connection_id": primary,
                       "standby_connection_id": standby, "actor_uid": ADMIN}]


def test_a_route_refuses_what_cannot_serve_and_never_falls_back(session, rings) -> None:
    ready, bare, archived = (connection(session, name=n) for n in ("ready", "bare", "gone"))
    revise(session, ready)
    make_routable(session, rings, ready)
    revise(session, archived)
    archive_connection(session, connection_id=archived, roles=ADMIN_ROLES, idempotency_key=key(),
                       actor_uid=ADMIN)
    assert refusal(lambda: route(session, ready, ready)).detail_fields == {
        "field": "standby_connection_id", "constraint": "standby_equals_primary"}
    assert refusal(lambda: route(session, bare)).detail_fields == {"conflict_reason": "no_revision"}
    assert refusal(lambda: route(session, archived)).detail_fields == {
        "conflict_reason": "connection_archived"}
    assert refusal(lambda: route(session, ready, f"exc_{'0' * 26}")).code is ErrorCode.NOT_FOUND
    assert refusal(lambda: route(session, f"exc_{'0' * 26}")).code is ErrorCode.NOT_FOUND


def test_archiving_a_routed_connection_is_a_conflict_and_archiving_is_one_way(
    session, rings
) -> None:
    primary, spare = connection(session, name="p"), connection(session, name="q")
    revise(session, primary)
    revise(session, spare)
    make_routable(session, rings, primary)
    make_routable(session, rings, spare)
    route(session, primary, spare)
    for routed in (primary, spare):
        assert refusal(lambda: archive_connection(
            session, connection_id=routed, roles=ADMIN_ROLES, idempotency_key=key(),
            actor_uid=ADMIN)).detail_fields == {"conflict_reason": "connection_routed"}
    route(session, spare)  # the standby is dropped: nothing names `primary` any more
    archived = archive_connection(session, connection_id=primary, roles=ADMIN_ROLES,
                                  idempotency_key=key(), actor_uid=ADMIN)
    assert archived.archived_at is not None
    assert refusal(lambda: archive_connection(
        session, connection_id=primary, roles=ADMIN_ROLES, idempotency_key=key(), actor_uid=ADMIN)
    ).detail_fields == {"conflict_reason": "connection_archived"}
    assert refusal(lambda: revise(session, primary)).detail_fields == {
        "conflict_reason": "connection_archived"}
    assert connection_detail(session, spare).summary.routed_work_kinds == ("text_analysis",)
    assert connection_detail(session, primary).summary.routed_work_kinds == ()
