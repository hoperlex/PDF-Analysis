"""`HOSTS-AGENT-01`: the catalogue, the model book, the snapshot, the slots and the recount rules of host mode.

Pure logic with a fake clock and a fake detector: nothing is started.  What is under test is when a model is
verified, when it stops being, when a minimal call is due, that the snapshot is rebuilt only on change, and that the
slots of a provider are never exceeded.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
from pathlib import Path

import pytest

_NAME = "executor_runner_agent_support"
if _NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_NAME, Path(__file__).with_name("_agent_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module
    _spec.loader.exec_module(_module)
A = sys.modules[_NAME]
host_mode = A.load_module("exec_host_book_under_test", A.RUNNER_DIR / "host_mode.py")
detect = sys.modules["detect"]

CATALOGUE = [
    {"provider": "claude_code", "model_id": "claude-opus-5-5", "efforts": ["medium", "high"], "accepted_reported": ["claude-opus-5-5-20261001"]},
    {"provider": "claude_code", "model_id": "claude-sonnet-5-5", "efforts": ["low", "medium"], "accepted_reported": []},
    {"provider": "anthropic_api", "model_id": "claude-opus-5-5", "efforts": ["medium"], "accepted_reported": []},
]


class Clock:
    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


def facts(provider="claude_code", access="subscription", auth="valid", version="2.1.310", credential="", path="/usr/bin/claude"):
    return detect.ProviderFacts(provider, access, auth, path, version, credential)


def api_facts(credential="aaaa", provider="anthropic_api"):
    return detect.ProviderFacts(provider, "api", "unknown", None, None, credential)


def book(clock=None, **kwargs):
    clock = clock or Clock()
    return host_mode.ModelBook(clock=clock, mono=clock, **kwargs), clock


def loaded(clock=None, providers=None, **kwargs):
    b, clock = book(clock, **kwargs)
    models, problems = host_mode.parse_catalogue(CATALOGUE)
    assert not problems
    b.set_catalogue(models)
    b.apply_facts(tuple(providers if providers is not None else [facts()]))
    return b, clock


# ---------------------------------------------------------------------------------------- the catalogue


def test_a_well_formed_catalogue_is_parsed_with_its_efforts_and_accepted_reported_strings():
    models, problems = host_mode.parse_catalogue(CATALOGUE)
    assert problems == [] and len(models) == 3
    opus = models[0]
    assert (opus.provider, opus.model_id, opus.efforts) == ("claude_code", "claude-opus-5-5", ("medium", "high"))
    assert opus.accepted == ("claude-opus-5-5", "claude-opus-5-5-20261001")  # the id itself is always accepted
    assert models[1].accepted == ("claude-sonnet-5-5",)


def test_the_catalogue_the_stand_sends_is_served_whole():
    """The stand's own catalogue, exactly as ``reportRunnerHealth`` hands it out, loses no entry on the agent.

    Its ``accepted_reported`` names strings such as ``claude-opus-5-5[1m]``; the agent once held them to the ``--model`` rule, so
    both Claude subscription models went unserved on every host (adm1, 2026-11-10) while the fixtures above stayed green.
    """
    from auditmanager.executors.catalogue import catalogue

    sent = catalogue().for_agent()
    models, problems = host_mode.parse_catalogue(sent)
    assert problems == []
    assert [(m.provider, m.model_id) for m in models] == [(e["provider"], e["model_id"]) for e in sent]
    for model, entry in zip(models, sent):
        assert set(model.accepted) == {entry["model_id"], *entry["accepted_reported"]}


def test_a_reported_string_is_held_to_the_contract_not_to_the_model_id_rule():
    entry = {"provider": "claude_code", "model_id": "claude-opus-5-5", "efforts": ["low"],
             "accepted_reported": ["claude-opus-5-5[1m]", "Claude Opus 5.5"]}
    models, problems = host_mode.parse_catalogue([entry])
    assert problems == [] and models[0].accepted == ("claude-opus-5-5", "claude-opus-5-5[1m]", "Claude Opus 5.5")
    # the id itself is what reaches --model: it keeps the strict rule
    models, problems = host_mode.parse_catalogue([{**entry, "model_id": "claude-opus-5-5[1m]"}])
    assert models == () and "bad model_id" in problems[0]


@pytest.mark.parametrize("entry,needle", [
    ({"provider": "gemini", "model_id": "x", "efforts": ["low"]}, "unknown provider"),
    ({"provider": "codex", "model_id": "has space", "efforts": ["low"]}, "bad model_id"),
    ({"provider": "codex", "model_id": "gpt-6", "efforts": ["low"], "accepted_reported": ["gpt\n6"]}, "bad accepted_reported"),
    ({"provider": "codex", "model_id": "gpt-6", "efforts": ["low"], "accepted_reported": [""]}, "bad accepted_reported"),
    ({"provider": "codex", "model_id": "gpt-6", "efforts": ["low"], "accepted_reported": ["g" * 201]}, "bad accepted_reported"),
    ({"provider": "codex", "model_id": "gpt-6", "efforts": []}, "bad efforts"),
    ({"provider": "codex", "model_id": "gpt-6", "efforts": ["LOW"]}, "bad efforts"),
    ({"provider": "codex", "model_id": "gpt-6", "efforts": ["low"], "accepted_reported": "gpt"}, "bad accepted_reported"),
    ("a string", "not an object"),
])
def test_a_malformed_entry_is_left_out_and_named_without_its_content(entry, needle):
    models, problems = host_mode.parse_catalogue([entry, CATALOGUE[0]])
    assert [m.model_id for m in models] == ["claude-opus-5-5"]
    assert len(problems) == 1 and needle in problems[0] and "has space" not in problems[0]


def test_a_repeated_model_and_a_catalogue_that_is_not_an_array_are_refused():
    models, problems = host_mode.parse_catalogue([CATALOGUE[0], CATALOGUE[0]])
    assert len(models) == 1 and "repeats" in problems[0]
    assert host_mode.parse_catalogue({"provider": "codex"}) == ((), ["catalogue is not an array"])


def test_the_probe_uses_the_cheapest_effort_the_model_has():
    assert host_mode.probe_effort(("medium", "low", "high")) == "low"
    assert host_mode.probe_effort(("medium", "high")) == "medium"
    assert host_mode.probe_effort(("minimal", "medium")) == "minimal"


# ------------------------------------------------------------------------------------ states and recount


def test_a_new_catalogue_model_is_not_verified_until_a_minimal_call_passes():
    b, clock = loaded()
    assert not b.is_verified("claude_code", "subscription", "claude-opus-5-5")
    assert [(m.model_id, f.provider) for m, f in b.due(21600, 900)] == [("claude-opus-5-5", "claude_code"), ("claude-sonnet-5-5", "claude_code")]
    b.record_probe("claude_code", "claude-opus-5-5", None)
    assert b.is_verified("claude_code", "subscription", "claude-opus-5-5")
    assert not b.is_verified("claude_code", "api", "claude-opus-5-5"), "verified for the access it was checked under only"
    assert not b.is_verified("claude_code", "subscription", "claude-sonnet-5-5")
    assert not b.is_verified("codex", "subscription", "claude-opus-5-5")
    assert b.verified_providers() == ["claude_code"]


def test_the_snapshot_names_each_model_with_its_state_checked_at_and_failure_code():
    b, clock = loaded()
    b.record_probe("claude_code", "claude-opus-5-5", None)
    clock.now += 5
    b.record_probe("claude_code", "claude-sonnet-5-5", "Quota Exceeded!")
    providers, slots = b.snapshot()
    [entry] = providers
    assert entry["provider"] == "claude_code" and entry["access"] == "subscription" and entry["auth_state"] == "valid"
    assert entry["cli_version"] == "2.1.310" and "cli_path" not in entry, "the path stays local unless the operator opts in"
    opus, sonnet = entry["models"]
    assert opus == {"model_id": "claude-opus-5-5", "state": "verified", "checked_at": "2027-01-15T08:00:00Z"}
    assert sonnet == {"model_id": "claude-sonnet-5-5", "state": "failed", "checked_at": "2027-01-15T08:00:05Z",
                      "failure_code": "quota_exceeded"}
    assert slots == {"claude_code": 1}


def test_cli_path_is_reported_only_when_the_operator_asked_for_it():
    b, _ = loaded(report_cli_path=True)
    [entry] = b.snapshot()[0]
    assert entry["cli_path"] == "/usr/bin/claude"


def test_a_change_of_login_key_version_or_access_sends_the_models_of_that_provider_back_to_not_verified():
    b, clock = loaded(providers=[facts(), api_facts("aaaa")])
    for provider, model in (("claude_code", "claude-opus-5-5"), ("claude_code", "claude-sonnet-5-5"), ("anthropic_api", "claude-opus-5-5")):
        b.record_probe(provider, model, None)
    assert b.verified_providers() == ["anthropic_api", "claude_code"]
    clock.now += 60
    assert b.apply_facts((facts(), api_facts("aaaa"))) == []  # nothing changed
    assert b.verified_providers() == ["anthropic_api", "claude_code"]
    assert b.apply_facts((facts(version="2.1.311"), api_facts("aaaa"))) == ["claude_code"]
    assert b.verified_providers() == ["anthropic_api"], "a new CLI version is checked again"
    assert b.apply_facts((facts(version="2.1.311"), api_facts("bbbb"))) == ["anthropic_api"]
    assert b.verified_providers() == [], "a rotated key is checked again"
    b.record_probe("claude_code", "claude-opus-5-5", None)
    assert sorted(b.apply_facts((facts(version="2.1.311", auth="login_required"),))) == ["anthropic_api", "claude_code"]
    assert b.verified_providers() == [], "a login that went away makes nothing servable"
    assert b.due(21600, 900) == [], "and nothing is called for a provider that cannot be used"


def test_a_provider_that_left_and_came_back_is_checked_again_and_the_report_stops_naming_it_meanwhile():
    b, _ = loaded()
    b.record_probe("claude_code", "claude-opus-5-5", None)
    assert b.apply_facts(()) == ["claude_code"]
    assert b.snapshot() == ([], {})
    assert not b.is_verified("claude_code", "subscription", "claude-opus-5-5")
    b.apply_facts((facts(),))
    assert not b.is_verified("claude_code", "subscription", "claude-opus-5-5")


def test_a_verified_model_is_due_after_the_interval_and_a_failed_one_after_the_shorter_retry():
    b, clock = loaded()
    b.record_probe("claude_code", "claude-opus-5-5", None)
    b.record_probe("claude_code", "claude-sonnet-5-5", "model_not_found")
    assert b.due(21600, 900) == []
    clock.now += 899
    assert b.due(21600, 900) == []
    clock.now += 2
    assert [m.model_id for m, _ in b.due(21600, 900)] == ["claude-sonnet-5-5"]
    clock.now += 21600
    assert [m.model_id for m, _ in b.due(21600, 900)] == ["claude-opus-5-5", "claude-sonnet-5-5"]


def test_a_changed_catalogue_keeps_what_is_unchanged_and_resets_what_is_new_or_different():
    b, _ = loaded()
    b.record_probe("claude_code", "claude-opus-5-5", None)
    b.record_probe("claude_code", "claude-sonnet-5-5", None)
    models, _ = host_mode.parse_catalogue([CATALOGUE[0], {**CATALOGUE[1], "efforts": ["low"]}, CATALOGUE[2]])
    assert b.set_catalogue(models) is True
    assert b.is_verified("claude_code", "subscription", "claude-opus-5-5")
    assert not b.is_verified("claude_code", "subscription", "claude-sonnet-5-5")
    assert b.set_catalogue(models) is False
    b.set_catalogue(models[:1])
    assert b.entry("anthropic_api", "claude-opus-5-5") is None and b.entry("claude_code", "claude-sonnet-5-5") is None


def test_an_api_provider_is_valid_once_a_model_verified_and_login_required_when_its_key_was_refused():
    b, _ = loaded(providers=[api_facts("aaaa")])
    assert b.snapshot()[0][0]["auth_state"] == "unknown"
    b.record_probe("anthropic_api", "claude-opus-5-5", "auth_failed")
    assert b.snapshot()[0][0]["auth_state"] == "login_required"
    b.record_probe("anthropic_api", "claude-opus-5-5", None)
    assert b.snapshot()[0][0]["auth_state"] == "valid"


def test_a_cli_that_says_valid_but_refuses_every_call_is_reported_login_required():
    b, _ = loaded()
    b.record_probe("claude_code", "claude-opus-5-5", "auth_failed")
    b.record_probe("claude_code", "claude-sonnet-5-5", "auth_failed")
    assert b.snapshot()[0][0]["auth_state"] == "login_required"


def test_an_unrecognised_login_has_no_servable_provider_and_no_call_is_due():
    b, _ = loaded(providers=[facts(auth="unknown", access="api")])
    assert b.due(21600, 900) == [] and b.verified_providers() == []
    assert b.snapshot()[0][0]["auth_state"] == "unknown"


# ---------------------------------------------------------------------------------- snapshot only on change


def test_the_snapshot_is_rebuilt_only_when_something_in_it_changed():
    b, clock = loaded()
    first = b.snapshot()
    builds = b.builds
    for _ in range(25):
        clock.now += 60
        b.apply_facts((facts(),))  # a heartbeat: detection found the same thing
        assert b.snapshot() is first
    assert b.builds == builds
    b.record_probe("claude_code", "claude-opus-5-5", None)
    second = b.snapshot()
    assert second is not first and b.builds == builds + 1
    assert b.snapshot() is second and b.builds == builds + 1
    b.apply_facts((facts(), api_facts("k")))
    assert b.builds == builds + 1, "built when asked for, not when the input changed"
    b.snapshot()
    assert b.builds == builds + 2


# ---------------------------------------------------------------------------------------------- slots


def test_default_slots_are_one_on_a_subscription_two_on_an_api_and_the_config_overrides_them():
    b, _ = loaded(providers=[facts(), facts("codex", "api", path="/usr/bin/codex"), api_facts("k")])
    assert b.slot_capacity() == {"claude_code": 1, "codex": 2, "anthropic_api": 2}
    over, _ = loaded(providers=[facts(), api_facts("k")],
                     slots={"claude_code": 3, "anthropic_api": 1})
    assert over.slot_capacity() == {"claude_code": 3, "anthropic_api": 1}


def test_a_provider_never_runs_more_calls_than_its_slots_even_under_contention():
    pool = host_mode.SlotPool()
    pool.set_capacity({"claude_code": 1, "anthropic_api": 2})
    assert pool.capacity() == 3 and pool.capacity("anthropic_api") == 2 and pool.capacity("codex") == 0
    assert pool.try_acquire("claude_code") and not pool.try_acquire("claude_code")
    assert pool.try_acquire("anthropic_api") and pool.try_acquire("anthropic_api") and not pool.try_acquire("anthropic_api")
    assert not pool.try_acquire("codex"), "a provider without capacity has no slot"
    pool.release("claude_code")
    assert pool.try_acquire("claude_code")
    pool.release("codex")  # an unmatched release never goes below zero
    assert pool.used("codex") == 0

    wide = host_mode.SlotPool()
    wide.set_capacity({"claude_code": 2})
    inside, peak, lock = [0], [0], threading.Lock()

    def worker() -> None:
        for _ in range(200):
            if wide.try_acquire("claude_code"):
                with lock:
                    inside[0] += 1
                    peak[0] = max(peak[0], inside[0])
                with lock:
                    inside[0] -= 1
                wide.release("claude_code")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert 1 <= peak[0] <= 2


# --------------------------------------------------------------------------------------------- config


def test_the_agents_silence_window_is_600_seconds_and_equals_the_stands_stall_window():
    """`R-153p`: a claim is extended only while the call produced output in the last 600 s (it was 120).  The window is deliberately the stand's own
    stall window (``ATTEMPT_STALL_SECONDS``), so a silent call is stopped by the agent and fenced by the stand together."""
    from auditmanager.jobs.lease import ATTEMPT_STALL_SECONDS

    assert host_mode.ACTIVITY_WINDOW_SECONDS == 600.0
    assert host_mode.ACTIVITY_WINDOW_SECONDS == float(ATTEMPT_STALL_SECONDS)
    assert host_mode.parse_host_config({}, {}, {}).activity_window_seconds == 600.0
    assert host_mode.parse_host_config({"activity_window_seconds": 90}, {}, {}).activity_window_seconds == 90.0, "an explicit setting still wins"


def test_the_host_config_defaults_and_its_checks():
    cfg = host_mode.parse_host_config({}, {}, {})
    assert cfg.key_file == "/etc/pdf-analysis-agent/keys.env" and cfg.slots == {} and cfg.report_cli_path is False
    assert (cfg.detect_seconds, cfg.report_seconds, cfg.probe_interval_seconds) == (60.0, 60.0, 21600.0)
    assert (cfg.failed_retry_seconds, cfg.activity_window_seconds, cfg.accept_images) == (900.0, 600.0, False)
    custom = host_mode.parse_host_config({"key_file": "/srv/keys.env", "probe_interval_seconds": 3600, "report_cli_path": True},
                                         {"codex": 2}, {"anthropic_base_url": "http://127.0.0.1:9999"})
    assert custom.key_file == "/srv/keys.env" and custom.probe_interval_seconds == 3600.0 and custom.report_cli_path is True
    assert custom.slots == {"codex": 2} and custom.base_urls == {"anthropic_api": "http://127.0.0.1:9999"}


@pytest.mark.parametrize("host,slots,api,needle", [
    ({"key_file": "relative.env"}, {}, {}, "absolute path"),
    ({"surprise": 1}, {}, {}, "unknown key"),
    ({"probe_interval_seconds": -5}, {}, {}, "positive number"),
    ({"report_cli_path": "yes"}, {}, {}, "boolean"),
    ({"max_images": 2}, {}, {}, "accept_images"),
    ({}, {"gemini": 1}, {}, "unknown provider"),
    ({}, {"codex": 0}, {}, "1..8"),
    ({}, {"codex": 99}, {}, "1..8"),
    ({}, {}, {"anthropic_base_url": "http://example.org"}, "https://"),
    ({}, {}, {"nope": "x"}, "unknown key"),
])
def test_a_bad_host_config_is_refused_with_a_message_for_the_operator(host, slots, api, needle):
    with pytest.raises(ValueError, match=needle):
        host_mode.parse_host_config(host, slots, api)


def test_failure_codes_are_fixed_words_in_the_contracts_alphabet():
    assert host_mode.failure_code("Quota Exceeded!") == "quota_exceeded"
    assert host_mode.failure_code("claude_turn_failed") == "claude_turn_failed"
    assert host_mode.failure_code("") == "failed" and host_mode.failure_code("***") == "failed"
    assert len(host_mode.failure_code("x" * 300)) == 64
    assert host_mode.FAILURE_CODE_RE.fullmatch(host_mode.failure_code("9 lives"))
