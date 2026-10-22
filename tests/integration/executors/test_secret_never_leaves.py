"""`EXEC-SEAL-01`, plan section 4.2: the sentinel test.

A sentinel key set through the API must occur in **none** of: any API response (success or
refusal), an ``audit_event`` payload, ``command_record``, a log line the test captures, and a
``pg_dump --data-only`` text of the lane's database. The ciphertext opens only with the private
ring. Every scan is shown to be able to find a planted sentinel, so a green result is not a
scan that looks nowhere.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from auditmanager.executors.public import (
    PrivateRing,
    SecretUnreadableError,
    destination_for,
    generate_ssh_key,
    open_secret,
)
from tests.integration.executors.conftest import ADMIN, driver, make_rings
from tests.integration.executors.test_executor_commands import (
    ADMIN_ROLES,
    HTTP,
    SSH,
    connection,
    key,
    revise,
    secret,
)
from tests.integration.executors.test_executor_surface import (
    HTTP_SETTINGS,
    call,
    made,
)

SENTINEL = f"sk-SENTINEL-{uuid4().hex}-do-not-leak"


def leaks(haystack: str, needle: str = SENTINEL) -> bool:
    """The scan under test. Case-sensitive on the value, and on its hex and base64 spellings."""
    import base64

    spellings = {needle, needle.encode().hex(), base64.b64encode(needle.encode()).decode(),
                 base64.urlsafe_b64encode(needle.encode()).decode()}
    return any(spelling in haystack for spelling in spellings)


def test_the_scan_can_find_a_planted_sentinel() -> None:
    """The guard is not vacuous: each spelling it claims to catch is caught."""
    import base64

    assert leaks(f"x {SENTINEL} y")
    assert leaks(SENTINEL.encode().hex())
    assert leaks(base64.b64encode(SENTINEL.encode()).decode())
    assert leaks(json.dumps({"payload": {"secret": SENTINEL}}))
    assert not leaks("a response with no key in it")


def test_the_sentinel_occurs_in_no_response_event_ledger_or_log(
    session, surface, rings, caplog, capsys,
) -> None:
    caplog.set_level(logging.DEBUG)
    answers = []
    cid = made(surface)
    answers.append(call(surface, "POST", f"/executor-connections/{cid}/secrets",
                        {"purpose": "api_key", "value": SENTINEL}))
    # The same value on every path that could echo it: a refused purpose, an unknown
    # connection, an archived one, a body with an extra field, and a replay.
    answers.append(call(surface, "POST", f"/executor-connections/{cid}/secrets",
                        {"purpose": "bogus", "value": SENTINEL}))
    answers.append(call(surface, "POST", f"/executor-connections/{cid}/secrets",
                        {"purpose": "api_key", "value": SENTINEL, "extra": SENTINEL}))
    answers.append(call(surface, "POST", f"/executor-connections/exc_{'0' * 26}/secrets",
                        {"purpose": "api_key", "value": SENTINEL}))
    answers.append(call(surface, "POST", f"/executor-connections/{cid}/secrets",
                        {"purpose": "ssh_private_key", "value": SENTINEL}))
    answers.append(call(surface, "POST", f"/executor-connections/{cid}/secrets",
                        {"purpose": "api_key", "value": SENTINEL[:6]}))
    bare = call(surface, "POST", "/executor-connections",
                {"kind": "http_api", "display_name": "no revision yet"}).json()["connection_id"]
    answers.append(call(surface, "POST", f"/executor-connections/{bare}/secrets",
                        {"purpose": "api_key", "value": SENTINEL}))
    for path in ("/executor-connections", f"/executor-connections/{cid}", "/executor-routes"):
        answers.append(call(surface, "GET", path, keyed=False))
    answers.append(call(surface, "POST", f"/executor-connections/{cid}/probes"))
    answers.append(call(surface, "PUT", "/executor-routes",
                        {"work_kind": "text_analysis", "primary_connection_id": cid}))
    ssh = made(surface, "ssh_command", {
        "pin_id": "claude-sonnet-5", "gateway_model": "claude-sonnet-5", "billing": "metered",
        "allow_client_documents": False, "timeout_seconds": 120, "ssh_host": "gpu.test",
        "ssh_port": 22, "ssh_user": "am", "ssh_profile": "claude_code_headless"})
    answers.append(call(surface, "POST", f"/executor-connections/{ssh}/ssh-key"))

    statuses = [answer.status for answer in answers]
    assert 201 in statuses and 422 in statuses and 404 in statuses and 409 in statuses, statuses
    for answer in answers:
        assert not leaks(answer.body.decode("utf-8", "replace")), answer.body
        assert not any(leaks(value) for _name, value in answer.headers)

    # What the journal and the ledger hold, read from the database itself.
    events = session.execute(text("SELECT payload::text FROM audit_event")).scalars().all()
    assert events and not any(leaks(event) for event in events)
    ledger = session.execute(text(
        "SELECT row_to_json(c)::text FROM command_record c")).scalars().all()
    assert ledger and not any(leaks(row) for row in ledger)
    everything = session.execute(text(
        "SELECT row_to_json(t)::text FROM executor_secret t")).scalars().all()
    assert everything and not any(leaks(row) for row in everything)

    printed = capsys.readouterr()
    assert not leaks(caplog.text + printed.out + printed.err)
    assert SENTINEL not in repr(rings.public) + repr(rings.private)


def test_the_scan_of_the_ledger_and_the_journal_can_fail(session, admin_account) -> None:
    """A sentinel planted in a payload and in a ledger outcome is found by the very queries above."""
    from auditmanager.jobs.public import append_execution_event

    cid = connection(session)
    with pytest.raises(ValueError):  # the allowlist refuses a secret-shaped key outright
        append_execution_event(session, event_type="executor.secret_set", aggregate_type="ExecutorConnection",
                               aggregate_id=cid, payload={"secret": SENTINEL})
    session.execute(text(
        "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
        "VALUES (:id, 'executor.planted', 'ExecutorConnection', :c, CAST(:p AS jsonb))"
    ), {"id": f"evt_{'0' * 25}1", "c": cid, "p": json.dumps({"connection_id": SENTINEL})})
    events = session.execute(text("SELECT payload::text FROM audit_event")).scalars().all()
    assert any(leaks(event) for event in events)


def test_the_ciphertext_opens_only_with_the_private_ring(session, rings) -> None:
    cid = connection(session)
    revision = revise(session, cid)
    record = secret(session, cid, rings.public, value=SENTINEL)
    destination = destination_for("http_api", revision.settings, "api_key")
    assert open_secret(session, rings.private, secret_id=record.secret_id,
                       destination=destination) == SENTINEL
    for stranger in (make_rings("k1").private, PrivateRing(keys={}), None):
        with pytest.raises(SecretUnreadableError):
            open_secret(session, stranger, secret_id=record.secret_id, destination=destination)
    # The public ring the api holds has no way to open: it is not even a ring of private keys.
    assert not hasattr(rings.public, "open")


def _pg_dump(server_major: int) -> str:
    for candidate in (shutil.which("pg_dump"), f"/usr/lib/postgresql/{server_major}/bin/pg_dump"):
        if candidate and os.path.exists(candidate):
            out = subprocess.run([candidate, "--version"], capture_output=True, text=True).stdout
            found = re.search(r"(\d+)(?:\.\d+)?\s*(?:\(|$)", out)
            if found and int(found.group(1)) >= server_major:
                return candidate
    pytest.fail(f"no pg_dump of major {server_major} or newer is available; this check never skips")


def test_a_database_dump_carries_ciphertext_and_no_secret_and_no_ring(engine, rings) -> None:
    """Committed on purpose: ``pg_dump`` reads its own snapshot. The rows stay (they are
    append-only and harmless: a sentinel that no key opens), so every assertion is keyed to ids
    this test created."""
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as work:
        cid = connection(work, name="dump-sentinel")
        revision = revise(work, cid)
        record = secret(work, cid, rings.public, value=SENTINEL)
        ssh = connection(work, "ssh_command", name="dump-ssh")
        revise(work, ssh, SSH)
        generated = generate_ssh_key(work, connection_id=ssh, ring=rings.public, roles=ADMIN_ROLES,
                                     idempotency_key=key(), actor_uid=ADMIN)
        ciphertext = work.execute(text(
            "SELECT encode(ciphertext, 'hex') FROM executor_secret WHERE secret_id = :id"
        ), {"id": record.secret_id}).scalar_one()
        work.commit()

    with engine.connect() as probe:
        server_major = int(probe.execute(text("SHOW server_version_num")).scalar_one()) // 10000
    url = engine.url
    environment = dict(os.environ, PGPASSWORD=url.password or "")
    dump = subprocess.run(
        [_pg_dump(server_major), "--data-only", "--no-owner", "-h", url.host or "localhost",
         "-p", str(url.port or 5432), "-U", url.username or "", "-d", url.database or "",
         "-t", "public.executor_*", "-t", "public.audit_event", "-t", "public.command_record"],
        capture_output=True, text=True, env=environment, timeout=120,
    )
    assert dump.returncode == 0, dump.stderr
    text_dump = dump.stdout
    assert cid in text_dump and record.secret_id in text_dump  # it dumped what this test wrote
    assert ciphertext in text_dump                              # ciphertext only, as bytea hex
    assert not leaks(text_dump)
    assert rings.private_text not in text_dump and "PRIVATE KEY" not in text_dump
    # What the dump holds is not enough to read it: only the private ring opens it.
    with factory() as reader:
        destination = destination_for("http_api", revision.settings, "api_key")
        assert open_secret(reader, rings.private, secret_id=record.secret_id,
                           destination=destination) == SENTINEL
        with pytest.raises(SecretUnreadableError):
            open_secret(reader, make_rings("k1").private, secret_id=record.secret_id,
                        destination=destination)
        assert generated.secret.secret_id in text_dump
