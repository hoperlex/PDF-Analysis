"""The SSH transport reads signs of life from the command's stderr (`AR-V3-LIVENESS-01`, lane B).

A call used to be bounded by one wall-clock ``timeout_s``: a model that was thinking could not be
told from one that hung. Now a command that writes a **heartbeat line** to stderr
(``pdf-analysis-forced-command: hb <elapsed> <events> <output_tokens>``) makes the call *live*:
``timeout_s`` stops applying, the call may run to ``live_hard_cap_s``, and it is cut after
``live_stall_s`` without another heartbeat.

The fake ``ssh`` below is a script that plays a **plan** (sleep, write stderr, beat, write stdout,
exit) and records its PID, so a test can show that a cut call's child is gone. No server, no
network, no container. Numbers are fractions of a second; nothing here sleeps a minute.

What is held, one test each where it can fail on its own:

* a heartbeating command outlives ``timeout_s`` and returns its answer;
* silence after a heartbeat is a ``stalled`` failure (sent, the child killed, no key left behind);
* a command that keeps signalling is cut at ``live_hard_cap_s`` as ``hard_cap``;
* **only** the exact line is a sign of life: lookalikes, a partial line, a longer line that ends
  with the text, and plain stderr are not -- a command that shows nothing else is cut at
  ``timeout_s`` exactly as before, with or without the live parameters;
* ``on_signal`` is called for the heartbeats, at most once a second, and a callback that raises
  does not end the call;
* a call made **without** ``live_hard_cap_s`` is what it was: heartbeats are ordinary stderr.
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from auditmanager.executors import ssh_transport as transport
from auditmanager.executors.ssh_transport import HEARTBEAT_LINE, OUTCOMES, SshEndpoint, SshFailure, run_command

PEM = "-----BEGIN OPENSSH PRIVATE KEY-----\nSENTINELBODYLINE0123456789abcdefSENTINEL\n-----END OPENSSH PRIVATE KEY-----\n"
ENDPOINT = SshEndpoint("remote.example.test", 2222, "runner")
HEARTBEAT = "pdf-analysis-forced-command: hb {} {} {}\n"

FAKE_SSH = textwrap.dedent(
    """\
    #!{python}
    import json, os, sys, time

    here = os.path.dirname(os.path.abspath(__file__))
    plan = json.load(open(os.path.join(here, "plan.json")))
    open(os.path.join(here, "pid"), "w").write(str(os.getpid()))
    sys.stdin.buffer.read()  # a real command reads its task first

    def err(text):
        sys.stderr.write(text)
        sys.stderr.flush()

    for step in plan:
        kind = step[0]
        if kind == "sleep":
            time.sleep(step[1])
        elif kind == "err":
            err(step[1])
        elif kind == "beat":
            err("pdf-analysis-forced-command: hb %d %d %d\\n" % (step[1], step[2], step[3]))
        elif kind == "beats":  # [count, period]: a heartbeat, then the period, count times
            for number in range(step[1]):
                err("pdf-analysis-forced-command: hb %d %d 0\\n" % (number, number))
                time.sleep(step[2])
        elif kind == "out":
            sys.stdout.write(step[1])
            sys.stdout.flush()
        elif kind == "exit":
            sys.exit(step[1])
    """
)


class Plan:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def set(self, *steps: list) -> None:
        (self.directory / "plan.json").write_text(json.dumps(list(steps)))

    def pid(self) -> int:
        return int((self.directory / "pid").read_text())

    def assert_child_gone(self) -> None:
        with pytest.raises(ProcessLookupError):
            os.kill(self.pid(), 0)  # our own child was killed and reaped by the transport


@pytest.fixture
def key_area(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    area = tmp_path / "shm"
    area.mkdir()
    monkeypatch.setattr(transport, "TMPFS_DIR", area)
    return area


@pytest.fixture
def plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key_area: Path) -> Iterator[Plan]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "ssh"
    script.write_text(FAKE_SSH.format(python=sys.executable))
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    fake = Plan(bin_dir)
    fake.set(["out", "{}"], ["exit", 0])
    yield fake
    try:  # a failing test must not leave its sleeping fake behind: only the PID it recorded
        pid = fake.pid()
        if str(bin_dir).encode() in Path(f"/proc/{pid}/cmdline").read_bytes():
            os.kill(pid, 9)
    except (OSError, ValueError):
        pass


class Signals:
    """An ``on_signal`` that counts, and remembers when."""

    def __init__(self) -> None:
        self.times: list[float] = []

    def __call__(self) -> None:
        self.times.append(time.monotonic())


def call(*, timeout_s: float = 10, **live):
    return run_command(ENDPOINT, PEM, "ssh-ed25519 " + _blob(), b'{"task":1}', timeout_s, 1_000_000, **live)


def _blob() -> str:
    import base64
    import struct

    name = b"ssh-ed25519"
    return base64.b64encode(struct.pack(">I", len(name)) + name + struct.pack(">I", 32) + b"k" * 32).decode()


# --------------------------------------------------------------------------------------------
# The frozen line and the vocabulary
# --------------------------------------------------------------------------------------------


def test_the_heartbeat_line_is_the_frozen_regular_expression() -> None:
    assert HEARTBEAT_LINE.pattern == rb"^pdf-analysis-forced-command: hb [0-9]+ [0-9]+ [0-9]+$"
    for line in (b"pdf-analysis-forced-command: hb 0 0 0", b"pdf-analysis-forced-command: hb 30 1234 98765"):
        assert HEARTBEAT_LINE.fullmatch(line)
    for line in (
        b"", b"pdf-analysis-forced-command: hb 1 2", b"pdf-analysis-forced-command: hb 1 2 3 4",
        b"pdf-analysis-forced-command: hb 1 2 x", b"pdf-analysis-forced-command: hb -1 2 3",
        b"pdf-analysis-forced-command: hb 1  2 3", b" pdf-analysis-forced-command: hb 1 2 3",
        b"pdf-analysis-forced-command: hb 1 2 3 ", b"pdf-analysis-forced-command: hb 1 2 3\r",
        b"pdf-analysis-forced-command:hb 1 2 3", b"PDF-ANALYSIS-FORCED-COMMAND: hb 1 2 3",
        b"x pdf-analysis-forced-command: hb 1 2 3", b"pdf-analysis-forced-command: error hb 1 2 3",
        b"pdf-analysis-forced-command: hb \xd9\xa1 2 3",
    ):
        assert not HEARTBEAT_LINE.fullmatch(line), line


def test_the_two_new_outcomes_are_in_the_vocabulary_and_are_sent() -> None:
    assert {"stalled", "hard_cap"} <= set(OUTCOMES)
    for outcome in ("stalled", "hard_cap"):
        failure = SshFailure(outcome, "detail", sent=True)
        assert failure.outcome == outcome and failure.sent is True
    with pytest.raises(ValueError):
        SshFailure("unheard_of", "x", sent=True)


# --------------------------------------------------------------------------------------------
# Live: the call outlives timeout_s while it signals
# --------------------------------------------------------------------------------------------


def test_a_command_that_keeps_signalling_outlives_the_timeout_and_returns_its_answer(plan: Plan) -> None:
    plan.set(["beats", 8, 0.25], ["out", '{"answer": 1}'], ["exit", 0])  # about 2 s
    signals = Signals()
    started = time.monotonic()
    stdout, stderr = call(timeout_s=1, live_hard_cap_s=30, live_stall_s=1.0, on_signal=signals)
    assert time.monotonic() - started > 1.5, "the call went past its 1 s timeout"
    assert stdout == b'{"answer": 1}'
    assert stderr == "", "heartbeat lines are not kept in the returned stderr"
    assert signals.times, "on_signal was called"


def test_heartbeat_lines_are_dropped_from_the_returned_text_and_other_stderr_is_kept(plan: Plan) -> None:
    plan.set(
        ["beat", 0, 0, 0], ["err", "warning: something real\n"], ["beat", 1, 2, 3],
        ["err", "last words"], ["out", "ok"], ["exit", 0],
    )
    _, stderr = call(live_hard_cap_s=30, live_stall_s=5)
    assert stderr == "warning: something real\nlast words"
    assert "pdf-analysis-forced-command" not in stderr


def test_a_heartbeat_split_across_two_writes_is_one_line_and_a_sign_of_life(plan: Plan) -> None:
    plan.set(
        ["sleep", 0.2], ["err", "pdf-analysis-forced-command: hb 1"], ["sleep", 0.3],
        ["err", " 2 3\n"], ["sleep", 30],
    )
    started = time.monotonic()
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=1.5, live_hard_cap_s=30, live_stall_s=0.6)
    assert raised.value.outcome == "stalled", "live from the completed line, so not the 1.5 s timeout"
    assert time.monotonic() - started < 1.5 + 5


# --------------------------------------------------------------------------------------------
# Stall and hard cap
# --------------------------------------------------------------------------------------------


def test_silence_after_a_heartbeat_is_a_stall_and_the_command_may_have_run(plan: Plan, key_area: Path) -> None:
    plan.set(["beat", 0, 0, 0], ["sleep", 60])
    signals = Signals()
    started = time.monotonic()
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=30, live_hard_cap_s=30, live_stall_s=0.8, on_signal=signals)
    took = time.monotonic() - started
    assert 0.7 <= took < 6, f"cut at the stall window, not at the 30 s timeout ({took:.2f} s)"
    assert raised.value.outcome == "stalled"
    assert raised.value.sent is True  # outcome unknown: the model may have run and spent
    assert "no sign of life" in raised.value.detail
    assert len(signals.times) == 1
    plan.assert_child_gone()
    assert list(key_area.iterdir()) == [], "the key file is gone"


def test_a_command_that_keeps_signalling_is_cut_at_the_hard_cap_not_the_timeout(plan: Plan, key_area: Path) -> None:
    plan.set(["beats", 1000, 0.15])  # signals for a minute
    started = time.monotonic()
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=0.4, live_hard_cap_s=1.5, live_stall_s=0.6)
    took = time.monotonic() - started
    assert 1.4 <= took < 6, f"past the 0.4 s timeout, cut at the 1.5 s ceiling ({took:.2f} s)"
    assert raised.value.outcome == "hard_cap"
    assert raised.value.sent is True
    assert "ceiling" in raised.value.detail
    plan.assert_child_gone()
    assert list(key_area.iterdir()) == []


def test_a_ceiling_of_nothing_cuts_a_live_call_at_its_first_sign(plan: Plan) -> None:
    plan.set(["beats", 1000, 0.15])
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=30, live_hard_cap_s=0, live_stall_s=5)
    assert raised.value.outcome == "hard_cap"


def test_without_a_stall_window_only_the_ceiling_applies(plan: Plan) -> None:
    plan.set(["beat", 0, 0, 0], ["sleep", 1.0], ["out", "late"], ["exit", 0])
    stdout, _ = call(timeout_s=0.3, live_hard_cap_s=30)
    assert stdout == b"late"


# --------------------------------------------------------------------------------------------
# Only the exact line is a sign of life
# --------------------------------------------------------------------------------------------

LOOKALIKES = (
    "pdf-analysis-forced-command: hb 1 2\n",
    "pdf-analysis-forced-command: hb 1 2 3 4\n",
    "pdf-analysis-forced-command: hb 1 2 x\n",
    "pdf-analysis-forced-command: hb -1 2 3\n",
    " pdf-analysis-forced-command: hb 1 2 3\n",
    "pdf-analysis-forced-command: hb 1 2 3 \n",
    "pdf-analysis-forced-command: hb 1 2 3\r\n",
    "ssh: connection alive\n",
    "Warning: Permanently added a host\n",
    "\n",
)


def test_lines_that_are_not_the_exact_heartbeat_are_not_signs_of_life(plan: Plan) -> None:
    """A command that shows only lookalikes for three seconds, then answers, is a call that never
    signalled: it is cut at ``timeout_s`` as it always was -- ``timeout``, not ``stalled`` or
    ``hard_cap``, and ``on_signal`` is never called."""
    steps: list[list] = []
    for _ in range(6):
        steps += [["err", line] for line in LOOKALIKES] + [["sleep", 0.5]]
    plan.set(*steps, ["out", "answer"], ["exit", 0])
    signals = Signals()
    started = time.monotonic()
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=1, live_hard_cap_s=60, live_stall_s=0.5, on_signal=signals)
    assert time.monotonic() - started < 3, "cut at the 1 s timeout"
    assert raised.value.outcome == "timeout" and raised.value.sent is True
    assert signals.times == []
    plan.assert_child_gone()


def test_text_after_a_very_long_line_is_not_a_whole_line(plan: Plan) -> None:
    """A line longer than the buffer the reader keeps is never a heartbeat, and neither is the rest
    of it: the text that ends it is not a line of its own."""
    plan.set(
        ["err", "A" * 3000], ["sleep", 0.2], ["err", "pdf-analysis-forced-command: hb 1 2 3\n"],
        ["sleep", 3], ["out", "answer"], ["exit", 0],
    )
    signals = Signals()
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=1, live_hard_cap_s=60, live_stall_s=0.5, on_signal=signals)
    assert raised.value.outcome == "timeout"
    assert signals.times == []


def test_a_heartbeat_without_its_line_end_is_not_whole(plan: Plan) -> None:
    plan.set(["err", "pdf-analysis-forced-command: hb 1 2 3"], ["sleep", 3], ["out", "answer"], ["exit", 0])
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=1, live_hard_cap_s=60, live_stall_s=0.5)
    assert raised.value.outcome == "timeout"


def test_a_command_that_never_signals_is_cut_at_the_timeout_as_today_with_live_parameters(plan: Plan) -> None:
    plan.set(["sleep", 60])
    started = time.monotonic()
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=1, live_hard_cap_s=30, live_stall_s=0.5)
    took = time.monotonic() - started
    assert 0.9 <= took < 5, f"at timeout_s, not earlier and not later ({took:.2f} s)"
    assert raised.value.outcome == "timeout" and raised.value.sent is True
    assert "no answer within 1 s" in raised.value.detail
    plan.assert_child_gone()


def test_the_timeout_applies_until_the_first_heartbeat_then_stops(plan: Plan) -> None:
    """The first sign arrives after 0.5 s, 0.3 s before the 0.8 s timeout: the call is live."""
    plan.set(["sleep", 0.5], ["beat", 0, 0, 0], ["sleep", 1.2], ["out", "late"], ["exit", 0])
    stdout, _ = call(timeout_s=0.8, live_hard_cap_s=30, live_stall_s=3)
    assert stdout == b"late"
    # The same plan, one heartbeat later than the timeout, is a plain timeout.
    plan.set(["sleep", 1.2], ["beat", 0, 0, 0], ["sleep", 1.2], ["out", "late"], ["exit", 0])
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=0.8, live_hard_cap_s=30, live_stall_s=3)
    assert raised.value.outcome == "timeout"


# --------------------------------------------------------------------------------------------
# Without the live parameters the call is what it was
# --------------------------------------------------------------------------------------------


def test_a_call_without_the_live_parameters_does_not_read_heartbeats(plan: Plan) -> None:
    plan.set(["beats", 1000, 0.15])
    signals = Signals()
    started = time.monotonic()
    with pytest.raises(SshFailure) as raised:
        call(timeout_s=1, live_stall_s=0.5, on_signal=signals)  # no live_hard_cap_s: not live
    assert time.monotonic() - started < 4, "cut at timeout_s whatever it prints"
    assert raised.value.outcome == "timeout"
    assert signals.times == []
    assert "pdf-analysis-forced-command: hb" in raised.value.detail, "ordinary stderr, kept as before"


def test_a_call_without_the_live_parameters_keeps_the_heartbeat_text_in_its_stderr(plan: Plan) -> None:
    plan.set(["beat", 1, 2, 3], ["out", "ok"], ["exit", 0])
    stdout, stderr = call()
    assert stdout == b"ok" and stderr == "pdf-analysis-forced-command: hb 1 2 3"


# --------------------------------------------------------------------------------------------
# on_signal
# --------------------------------------------------------------------------------------------


def test_on_signal_is_called_at_most_once_a_second(plan: Plan) -> None:
    plan.set(
        *([["beat", 1, 1, 1]] * 6), ["sleep", 1.3], ["beat", 9, 9, 9], ["out", "ok"], ["exit", 0],
    )
    signals = Signals()
    call(live_hard_cap_s=30, live_stall_s=5, on_signal=signals)
    assert len(signals.times) == 2, "six beats in a burst are one call; the beat 1.3 s later is another"
    assert signals.times[1] - signals.times[0] >= 1.0


def test_a_callback_that_raises_does_not_end_the_call(plan: Plan, caplog: pytest.LogCaptureFixture) -> None:
    plan.set(["beat", 0, 0, 0], ["sleep", 0.2], ["out", "ok"], ["exit", 0])

    def broken() -> None:
        raise RuntimeError("the context is gone")

    with caplog.at_level("ERROR", logger=transport.LOGGER.name):
        stdout, _ = call(live_hard_cap_s=30, live_stall_s=5, on_signal=broken)
    assert stdout == b"ok"
    assert any("sign-of-life callback failed" in record.getMessage() for record in caplog.records)


def test_a_failed_call_that_was_live_keeps_its_ordinary_classification(plan: Plan) -> None:
    plan.set(["beat", 0, 0, 0], ["err", "boom\n"], ["exit", 2])
    with pytest.raises(SshFailure) as raised:
        call(live_hard_cap_s=30, live_stall_s=5)
    assert raised.value.outcome == "protocol_error" and raised.value.exit_status == 2
    assert "boom" in raised.value.detail and "pdf-analysis-forced-command" not in raised.value.detail


def test_the_stderr_of_a_live_call_stays_bounded(plan: Plan) -> None:
    plan.set(["beat", 0, 0, 0], ["err", ("e" * 99 + "\n") * 2000], ["beat", 1, 1, 1], ["out", "x"], ["exit", 0])
    _, stderr = call(live_hard_cap_s=30, live_stall_s=5)
    assert len(stderr) == 500


def test_the_live_limits_are_validated(plan: Plan) -> None:
    with pytest.raises(ValueError):
        call(live_hard_cap_s=-1, live_stall_s=5)
    with pytest.raises(ValueError):
        call(live_hard_cap_s=10, live_stall_s=0)
    with pytest.raises(ValueError):
        call(live_hard_cap_s=10, live_stall_s=-3)


# --------------------------------------------------------------------------------------------
# The adapter, the transport and the Attempt context together
# --------------------------------------------------------------------------------------------


def test_a_heartbeating_command_makes_the_attempt_live_and_outlives_the_revisions_timeout(plan: Plan) -> None:
    """The whole path: the adapter hands the transport the Attempt's ``progress``; the command's
    heartbeat lines call it; the call outlives the revision's 1 s timeout and the answer is read.
    Without the signal wiring the Attempt would stay silent and be fenced at 900 s."""
    from datetime import datetime, timezone

    from auditmanager.analysis.public import ModelRequest
    from auditmanager.executors.destinations import DestinationPolicy
    from auditmanager.executors.model import RevisionRecord, RevisionSettings
    from auditmanager.executors.ssh_adapter import SshCommandAdapter
    from auditmanager.jobs.lease import AttemptContext

    revision = RevisionRecord(
        revision_id="excr_1", connection_id="exc_1", revision_no=1,
        created_at=datetime.now(timezone.utc), created_by="usr_1",
        settings=RevisionSettings(
            pin_id="claude-opus-5", gateway_model="claude-opus-5", billing="metered",
            allow_client_documents=True, timeout_seconds=1, ssh_host="example.com", ssh_port=22,
            ssh_user="runner", host_key="ssh-ed25519 " + _blob(), ssh_profile="custom_command",
        ),
    )
    answer = json.dumps({"model": "claude-opus-5", "output_text": "ok", "stop_reason": "end_turn",
                         "input_tokens": 3, "output_tokens": 1})
    plan.set(["beats", 8, 0.25], ["out", answer], ["exit", 0])  # about 2 s: twice the timeout
    context = AttemptContext(run_id="run_1", attempt_id="att_1", started_monotonic=time.monotonic())
    policy = DestinationPolicy(resolver=lambda host, port: ["8.8.8.8"], networks=lambda: ())
    request = ModelRequest(
        model_id="claude-opus-5",
        body={"system": "system", "messages": [{"role": "user", "content": "describe"}], "max_tokens": 64},
    )
    assert context.live is False
    started = time.monotonic()
    response = SshCommandAdapter(revision, PEM, policy, context).complete(request)
    assert time.monotonic() - started > 1.5
    assert response.output_text == "ok"
    assert context.live is True, "the heartbeat reached the Attempt"
    assert context.remaining_seconds() > 590, "and its watchdog is now the 600 s silence window"
