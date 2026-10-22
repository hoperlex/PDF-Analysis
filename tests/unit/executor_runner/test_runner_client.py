"""runner_client.py: the pieces both clients rely on."""

from __future__ import annotations

import calendar
import importlib.util
import sys
import time
from email.utils import formatdate
from pathlib import Path

import pytest

_NAME = "executor_runner_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
S = sys.modules[_NAME]

_CLIENT = "runner_client_under_test"
if _CLIENT not in sys.modules:
    _cspec = importlib.util.spec_from_file_location(_CLIENT, S.RUNNER_DIR / "runner_client.py")
    _cmod = importlib.util.module_from_spec(_cspec)
    sys.modules[_CLIENT] = _cmod
    _cspec.loader.exec_module(_cmod)
rc = sys.modules[_CLIENT]


@pytest.mark.parametrize(
    "origin, expected",
    [
        ("https://stand.example.org", "https://stand.example.org"),
        ("https://stand.example.org/", "https://stand.example.org"),
        ("https://stand.example.org:8443", "https://stand.example.org:8443"),
        ("http://127.0.0.1:8000", "http://127.0.0.1:8000"),
        ("http://localhost:8000", "http://localhost:8000"),
        ("http://[::1]:8000", "http://[::1]:8000"),
    ],
)
def test_origins_that_are_accepted(origin, expected):
    assert rc.normalize_origin(origin) == expected


@pytest.mark.parametrize(
    "origin",
    ["stand.example.org", "ftp://stand.example.org", "https://", "https://user:pw@stand.example.org", "https://stand.example.org/api", "https://stand.example.org?x=1", "https://stand.example.org#f", "http://stand.example.org", "https://stand.example.org:notaport"],
)
def test_origins_that_are_refused(origin):
    with pytest.raises(ValueError):
        rc.normalize_origin(origin)


def test_clear_text_http_needs_the_explicit_flag():
    assert rc.normalize_origin("http://stand.example.org", allow_insecure_http=True) == "http://stand.example.org"


def test_timestamps_and_retry_after():
    assert rc.parse_timestamp("2026-10-22T07:30:15Z") == calendar.timegm((2026, 10, 22, 7, 30, 15))
    assert rc.parse_timestamp("2026-10-22T12:30:15+05:00") == rc.parse_timestamp("2026-10-22T07:30:15Z")
    assert rc.parse_timestamp("2026-10-22T07:30:15.5Z") == pytest.approx(rc.parse_timestamp("2026-10-22T07:30:15Z") + 0.5)
    with pytest.raises(ValueError):
        rc.parse_timestamp("yesterday")
    assert rc.parse_retry_after("7") == 7.0
    assert rc.parse_retry_after("100000") == rc.MAX_RETRY_AFTER
    assert rc.parse_retry_after("-3") == 0.0
    assert rc.parse_retry_after(None) is None and rc.parse_retry_after("garbage") is None
    assert 8 <= rc.parse_retry_after(formatdate(time.time() + 10, usegmt=True)) <= 11


def test_backoff_doubles_to_a_cap_and_resets():
    backoff = rc.Backoff(1.0, 8.0)
    delays = [backoff.next_delay() for _ in range(6)]
    bases = [1, 2, 4, 8, 8, 8]
    assert all(base <= d <= base * 1.1 + 1e-9 for base, d in zip(bases, delays))
    backoff.reset()
    assert 1.0 <= backoff.next_delay() <= 1.1


def test_a_429_without_retry_after_waits_the_documented_default():
    error = rc.RunnerThrottled("slow", status=429, retry_after=None)
    assert 30.0 <= rc.throttle_delay(error) <= 33.0
    assert 5.0 <= rc.throttle_delay(rc.RunnerThrottled("slow", status=429, retry_after=5.0)) <= 5.5


def test_the_time_left_on_a_claim_is_measured_on_the_servers_clock():
    client = rc.RunnerClient("https://stand.example.org", "tok")
    assert client.clock_skew == 0.0
    expires = S.stamp(time.time() + 103)
    client.clock_skew = 100.0  # the server's clock is 100 s ahead of ours
    assert 2.0 <= client.seconds_until(expires) <= 4.0
    class Headers(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)
    client._note_date(Headers(Date=formatdate(time.time() + 40, usegmt=True)))
    assert 38.0 <= client.clock_skew <= 41.0
    client._note_date(Headers(Date="not a date"))
    assert 38.0 <= client.clock_skew <= 41.0  # an unreadable Date leaves the estimate alone


def test_token_with_whitespace_or_empty_is_refused_and_the_token_is_scrubbed():
    for bad in ("", "a b", "a\nb"):
        with pytest.raises(ValueError):
            rc.RunnerClient("https://stand.example.org", bad)
    client = rc.RunnerClient("https://stand.example.org", "amr_secret_1")
    assert client.scrub("Bearer amr_secret_1 and amr_secret_1") == "Bearer *** and ***"


def test_claim_validates_the_range_the_task_shape_and_204():
    with S.FakeRunner() as runner:
        client = rc.RunnerClient(runner.origin, S.TOKEN)
        for bad in (-1, 26, "5", True, None):
            with pytest.raises(rc.RunnerRejected):
                client.claim(bad)
        assert runner.requests == []  # refused before any request
        assert client.claim(0) is None
        runner.override("claim", S.Reply(200, {"task_id": "ext_X"}))
        with pytest.raises(rc.RunnerUnavailable, match="malformed task document"):
            client.claim(0)
        runner.override("claim", S.Reply(200, S.make_task("../evil")))
        with pytest.raises(rc.RunnerUnavailable, match="task_id"):
            client.claim(0)
        runner.override("claim", S.Reply(200, S.make_task(deadline_at="tomorrow")))
        with pytest.raises(rc.RunnerUnavailable, match="timestamp"):
            client.claim(0)
        runner.override("claim", S.Reply(200, S.make_task("ext_OK")))
        assert client.claim(0)["task_id"] == "ext_OK"


def test_status_codes_map_to_exception_classes_and_the_envelope_is_read():
    with S.FakeRunner() as runner:
        client = rc.RunnerClient(runner.origin, S.TOKEN)
        cases = [
            (401, rc.RunnerAuthError), (404, rc.RunnerNotFound), (409, rc.RunnerConflict), (422, rc.RunnerRejected),
            (400, rc.RunnerRejected), (429, rc.RunnerThrottled), (500, rc.RunnerUnavailable), (503, rc.RunnerUnavailable),
        ]
        for status, expected in cases:
            runner.override("answer", S.Reply(status, S.envelope("conflict", "words", False), {"X-Correlation-Id": "hdr-1"}))
            with pytest.raises(expected) as caught:
                client.answer("ext_T", "{}", "claude-opus-5")
            assert caught.value.status == status and caught.value.error_code == "conflict" and caught.value.message == "words"
            assert caught.value.correlation_id == "corr-1"  # the body's id wins over the header
        runner.override("answer", S.Reply(502, None))  # an HTML or empty gateway answer is not the envelope
        with pytest.raises(rc.RunnerUnavailable) as caught:
            client.answer("ext_T", "{}", "claude-opus-5")
        assert caught.value.error_code is None and caught.value.message == "HTTP 502"


def test_oversized_requests_and_bad_task_ids_never_leave_the_machine():
    with S.FakeRunner() as runner:
        client = rc.RunnerClient(runner.origin, S.TOKEN)
        with pytest.raises(rc.RunnerRejected, match="1 MiB"):
            client.answer("ext_T", "x" * (rc.MAX_REQUEST_BYTES + 1), "claude-opus-5")
        for bad in ("", "a/b", "a b", "x" * 65, "ext_T?q=1", "..", None):
            with pytest.raises(rc.RunnerRejected):
                client.extend(bad)
        assert runner.requests == []


def test_fail_reason_is_cut_to_512_characters_and_never_empty():
    with S.FakeRunner() as runner:
        client = rc.RunnerClient(runner.origin, S.TOKEN)
        client.fail("ext_T", "r" * 900)
        client.fail("ext_T", "")
        reasons = [r["body"]["reason"] for r in runner.of_kind("fail")]
        assert reasons == ["r" * 512, "unspecified"]
