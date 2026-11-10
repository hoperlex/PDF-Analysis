"""Host mode of the agent: one process, one host token, every model the host can serve (``HOSTS-AGENT-01``).

The stand's plan v3 (section 5) and ``RUNNER_API.md`` section 10 are the contract.  This module holds the parts
of host mode that are not the claim loop (``agent.py`` has that):

* the **catalogue** the stand sends (``provider``, ``model_id``, ``efforts``, ``accepted_reported`` per model);
* the **model book**: for every catalogue model of every provider detected on this host, whether it is
  ``verified`` (a minimal call succeeded and the model that answered is an accepted one), ``not_verified`` (not
  checked yet, or the provider cannot be used now) or ``failed`` (a call failed, with a fixed ``failure_code``);
* the **recount**: cheap detection every 60 s (CLI present, version, login, key file; no model is called), and a
  minimal model call per catalogue model of a provider whose login, key, version or access changed, when a model
  is new, every six hours for a verified one and every 15 minutes for a failed one;
* the **snapshot** reported to the stand, rebuilt only when something in it changed;
* the **slots** per provider, and the **activity** clock that decides whether a claim may be extended;
* the **dispatch** of one task to the answerer of its provider (``claude_answer``, ``codex_answer`` or
  ``api_answer``), never to a model the book does not hold as verified.

API keys are read by ``detect.read_api_key`` and handed to ``api_answer`` as an argument; they are not in any
environment, report, log line or answer.  A key's presence is all the book knows of it.
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Mapping, Optional

import api_answer
import claude_answer
import codex_answer
import detect

PROVIDERS = detect.PROVIDERS
ACCESSES = (detect.ACCESS_SUBSCRIPTION, detect.ACCESS_API)
API_PROVIDERS = api_answer.API_PROVIDERS

STATE_VERIFIED = "verified"
STATE_NOT_VERIFIED = "not_verified"
STATE_FAILED = "failed"

#: Cheap detection and the heartbeat, in seconds (plan section 5, point 4; the stand takes a heartbeat older than
#: 120 s as no pulse).
DETECT_SECONDS = 60.0
REPORT_SECONDS = 60.0
#: A minimal call per catalogue model: every six hours for a verified one, every 15 minutes for one that failed.
PROBE_INTERVAL_SECONDS = 6 * 3600.0
FAILED_RETRY_SECONDS = 900.0
PROBE_TIMEOUT_SECONDS = 180.0
PROBE_MAX_OUTPUT_TOKENS = 4096  # a ceiling, not a target: the check answers in a few tokens, thinking included
#: A claim is extended only while the call has produced output in this many seconds.
ACTIVITY_WINDOW_SECONDS = 120.0
#: Concurrent calls per provider: one on a subscription, two on an API (plan section 5, point 8).
DEFAULT_SLOTS = {detect.ACCESS_SUBSCRIPTION: 1, detect.ACCESS_API: 2}
MAX_SLOTS = 8
MAX_REPORTED_CONCURRENCY = 16

MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")
#: A string an answer may report for a model (``RunnerCatalogueEntry.accepted_reported``: 1 to 200 characters, no pattern). It is
#: only compared with what the client reported, never put on a command line, so it is held to the contract's bound and no tighter:
#: the stand's own catalogue names ``claude-opus-5-5[1m]``, which ``MODEL_ID_RE`` (the id the agent passes as ``--model``) refused,
#: and the whole entry went unserved. Control characters stay out.
REPORTED_ID_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,200}$")
EFFORT_RE = re.compile(r"^[a-z]{3,16}$")
FAILURE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
#: What a failed call says about the host's access: the model leaves service until the next successful check.
ACCESS_KINDS = ("quota_exceeded", "auth_failed", "model_not_found")

_PROBE_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"],
                 "additionalProperties": False}
_PROBE_SYSTEM = "You answer a connectivity check for a document-analysis service. Return the JSON object requested."
_PROBE_USER = 'Reply with the JSON object {"ok": true} and nothing else.'


def timestamp(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def failure_code(text: object) -> str:
    """A fixed-vocabulary ``failure_code`` from any short word: lower case, ``[a-z0-9_]``, at most 64 characters."""
    code = re.sub(r"[^a-z0-9_]+", "_", str(text).lower()).strip("_")[:64]
    return code if FAILURE_CODE_RE.fullmatch(code) else "failed"


class HostFailure(Exception):
    """The task cannot be answered; ``code`` starts the ``fail`` reason (``model_not_available``, ``quota_exceeded``,
    ``claude_turn_failed`` ...) and ``detail`` is a short payload-free note."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail
        self.reported_model: Optional[str] = None


class Stopped(Exception):
    """The call was stopped because the claim is lost, the call stalled or the agent is stopping."""


class Activity:
    """The clock of a call's signs of life: its answerer calls :meth:`touch` for every byte or chunk it gets."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._last = clock()

    def touch(self) -> None:
        self._last = self._clock()

    def idle(self) -> float:
        return self._clock() - self._last


# -------------------------------------------------------------------------------------- catalogue


@dataclass(frozen=True)
class CatalogueModel:
    provider: str
    model_id: str
    efforts: tuple
    accepted_reported: tuple

    @property
    def key(self) -> tuple:
        return (self.provider, self.model_id)

    @property
    def accepted(self) -> tuple:
        """The strings the provider may report for this model: its id and the catalogue's extra ones."""
        return tuple(dict.fromkeys((self.model_id, *self.accepted_reported)))


def parse_catalogue(raw: object) -> "tuple[tuple, list]":
    """``(models, problems)`` from the stand's ``catalogue`` array.  An entry that is not well formed is left out
    and named in ``problems`` (a short word and its position, never its content): that model is simply not served."""
    models: list = []
    problems: list = []
    if not isinstance(raw, list):
        return (), ["catalogue is not an array"]
    seen: set = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            problems.append(f"entry {index} is not an object")
            continue
        provider, model_id = item.get("provider"), item.get("model_id")
        efforts, reported = item.get("efforts"), item.get("accepted_reported", [])
        if provider not in PROVIDERS:
            problems.append(f"entry {index} has an unknown provider")
        elif not isinstance(model_id, str) or MODEL_ID_RE.fullmatch(model_id) is None:
            problems.append(f"entry {index} has a bad model_id")
        elif not isinstance(efforts, list) or not efforts or not all(isinstance(e, str) and EFFORT_RE.fullmatch(e) for e in efforts):
            problems.append(f"entry {index} has bad efforts")
        elif not isinstance(reported, list) or not all(isinstance(r, str) and REPORTED_ID_RE.fullmatch(r) for r in reported):
            problems.append(f"entry {index} has bad accepted_reported")
        elif (provider, model_id) in seen:
            problems.append(f"entry {index} repeats a model")
        else:
            seen.add((provider, model_id))
            models.append(CatalogueModel(provider, model_id, tuple(dict.fromkeys(efforts)), tuple(dict.fromkeys(reported))))
    return tuple(models), problems


def probe_effort(efforts: tuple) -> str:
    """The cheapest effort of a model for its minimal call: ``low`` when it has it, else the first one."""
    for preferred in ("low", "minimal"):
        if preferred in efforts:
            return preferred
    return efforts[0]


# ------------------------------------------------------------------------------------ the config


@dataclass
class HostConfig:
    key_file: str = detect.DEFAULT_KEY_FILE
    slots: dict = field(default_factory=dict)  # provider -> int, overrides of DEFAULT_SLOTS
    base_urls: dict = field(default_factory=dict)  # provider -> URL, for a proxy or a test
    detect_seconds: float = DETECT_SECONDS
    report_seconds: float = REPORT_SECONDS
    probe_interval_seconds: float = PROBE_INTERVAL_SECONDS
    failed_retry_seconds: float = FAILED_RETRY_SECONDS
    probe_timeout_seconds: float = PROBE_TIMEOUT_SECONDS
    activity_window_seconds: float = ACTIVITY_WINDOW_SECONDS
    report_cli_path: bool = False
    accept_images: bool = False
    max_images: int = 1
    expected_uid: Optional[int] = None  # the key file's owner; None = the user running this process


HOST_KEYS = {"key_file", "detect_seconds", "report_seconds", "probe_interval_seconds", "failed_retry_seconds",
             "probe_timeout_seconds", "activity_window_seconds", "report_cli_path", "accept_images", "max_images"}
SLOT_KEYS = set(PROVIDERS)
API_KEYS = {"anthropic_base_url", "openai_base_url", "openrouter_base_url"}
_BASE_URL_PROVIDER = {"anthropic_base_url": api_answer.PROVIDER_ANTHROPIC, "openai_base_url": api_answer.PROVIDER_OPENAI,
                      "openrouter_base_url": api_answer.PROVIDER_OPENROUTER}


def parse_host_config(host: Mapping, slots: Mapping, api: Mapping) -> HostConfig:
    """The ``[host]``, ``[slots]`` and ``[api]`` sections of ``agent.toml``; raises ``ValueError`` with a message
    for the operator."""
    unknown = set(host) - HOST_KEYS
    if unknown:
        raise ValueError(f"unknown key(s) in [host]: {', '.join(sorted(unknown))}")
    unknown = set(slots) - SLOT_KEYS
    if unknown:
        raise ValueError(f"unknown provider(s) in [slots]: {', '.join(sorted(unknown))}")
    unknown = set(api) - API_KEYS
    if unknown:
        raise ValueError(f"unknown key(s) in [api]: {', '.join(sorted(unknown))}")
    cfg = HostConfig()
    key_file = host.get("key_file", cfg.key_file)
    if not isinstance(key_file, str) or not key_file.startswith("/"):
        raise ValueError("[host] key_file must be an absolute path")
    cfg.key_file = key_file
    for name in ("detect_seconds", "report_seconds", "probe_interval_seconds", "failed_retry_seconds",
                 "probe_timeout_seconds", "activity_window_seconds"):
        value = host.get(name, getattr(cfg, name))
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value < 1e7:
            raise ValueError(f"[host] {name} must be a positive number of seconds")
        setattr(cfg, name, float(value))
    for name in ("report_cli_path", "accept_images"):
        value = host.get(name, getattr(cfg, name))
        if type(value) is not bool:
            raise ValueError(f"[host] {name} must be a boolean")
        setattr(cfg, name, value)
    cfg.max_images = host.get("max_images", cfg.max_images)
    if type(cfg.max_images) is not int or not 1 <= cfg.max_images <= 8:
        raise ValueError("[host] max_images must be an integer in 1..8")
    if cfg.max_images > 1 and not cfg.accept_images:
        raise ValueError("[host] max_images above 1 needs accept_images = true")
    for provider, count in slots.items():
        if type(count) is not int or not 1 <= count <= MAX_SLOTS:
            raise ValueError(f"[slots] {provider} must be an integer in 1..{MAX_SLOTS}")
        cfg.slots[provider] = count
    for name, url in api.items():
        provider = _BASE_URL_PROVIDER[name]
        try:
            cfg.base_urls[provider] = api_answer.normalize_base_url(provider, url if isinstance(url, str) else "")
        except ValueError as error:
            raise ValueError(f"[api] {name}: {error}") from None
    return cfg


# ------------------------------------------------------------------------------------ slots


class SlotPool:
    """Concurrent calls per provider.  Within a provider never more than its slots are running."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._capacity: dict = {}
        self._used: dict = {}

    def set_capacity(self, capacity: Mapping[str, int]) -> None:
        with self._lock:
            self._capacity = dict(capacity)

    def capacity(self, provider: Optional[str] = None) -> int:
        with self._lock:
            return sum(self._capacity.values()) if provider is None else self._capacity.get(provider, 0)

    def try_acquire(self, provider: str) -> bool:
        with self._lock:
            if self._used.get(provider, 0) >= self._capacity.get(provider, 0):
                return False
            self._used[provider] = self._used.get(provider, 0) + 1
            return True

    def release(self, provider: str) -> None:
        with self._lock:
            self._used[provider] = max(0, self._used.get(provider, 0) - 1)

    def used(self, provider: str) -> int:
        with self._lock:
            return self._used.get(provider, 0)


# ------------------------------------------------------------------------------------ the book


@dataclass
class _Entry:
    state: str
    checked_at: float
    checked_mono: float
    failure_code: Optional[str] = None


def _facts_key(facts: detect.ProviderFacts) -> tuple:
    return (facts.access, facts.auth_state, facts.cli_version, facts.credential)


def servable(facts: detect.ProviderFacts) -> bool:
    """Whether a model call can be tried for this provider at all: a CLI with a recognised, valid login, or an API
    with a key."""
    if facts.provider in API_PROVIDERS:
        return True
    return facts.auth_state == detect.AUTH_VALID


class ModelBook:
    """What this host knows about its models.  Thread-safe; the snapshot is rebuilt only when ``version`` moves."""

    def __init__(self, *, report_cli_path: bool = False, slots: Optional[Mapping[str, int]] = None,
                 clock: Callable[[], float] = time.time, mono: Callable[[], float] = time.monotonic) -> None:
        self._lock = threading.Lock()
        self._clock, self._mono = clock, mono
        self.report_cli_path = report_cli_path
        self._slot_overrides = dict(slots or {})
        self._catalogue: tuple = ()
        self._facts: dict = {}
        self._entries: dict = {}
        self.version = 0
        self.builds = 0  # how many times the snapshot was rebuilt (a test reads it)
        self._snapshot: Optional[tuple] = None

    # ------------------------------------------------------------------ inputs

    def set_catalogue(self, catalogue: tuple) -> bool:
        with self._lock:
            if catalogue == self._catalogue:
                return False
            now, tick = self._clock(), self._mono()
            previous = {model.key: model for model in self._catalogue}
            for model in catalogue:
                if previous.get(model.key) != model or model.key not in self._entries:
                    self._entries[model.key] = _Entry(STATE_NOT_VERIFIED, now, tick)
            for key in list(self._entries):
                if key not in {model.key for model in catalogue}:
                    del self._entries[key]
            self._catalogue = catalogue
            self._changed()
            return True

    def apply_facts(self, providers: tuple) -> "list[str]":
        """The detected providers.  Returns the providers that are new or whose login, key, version or access
        changed (their models go back to ``not_verified`` until a minimal call passes) and the ones that left."""
        now, tick = self._clock(), self._mono()
        changed: list = []
        with self._lock:
            current = {facts.provider: facts for facts in providers}
            for provider, facts in current.items():
                before = self._facts.get(provider)
                if before is None or _facts_key(before) != _facts_key(facts):
                    changed.append(provider)
                    for model in self._catalogue:
                        if model.provider == provider:
                            self._entries[model.key] = _Entry(STATE_NOT_VERIFIED, now, tick)
            changed += [provider for provider in self._facts if provider not in current]
            if current != self._facts:  # a path alone changes the (opt-in) report, not the models
                self._facts = current
                self._changed()
        return changed

    def record_probe(self, provider: str, model_id: str, failure: Optional[str]) -> None:
        with self._lock:
            entry = self._entries.get((provider, model_id))
            if entry is None:
                return
            entry.state = STATE_VERIFIED if failure is None else STATE_FAILED
            entry.failure_code = None if failure is None else failure_code(failure)
            entry.checked_at, entry.checked_mono = self._clock(), self._mono()
            self._changed()

    def mark_failed(self, provider: str, model_id: str, failure: str) -> None:
        """A real call failed for a reason about the host's access: the model is out of service until a check passes."""
        self.record_probe(provider, model_id, failure)

    # ------------------------------------------------------------------ reads

    def _changed(self) -> None:
        self.version += 1
        self._snapshot = None

    def facts(self, provider: str) -> Optional[detect.ProviderFacts]:
        with self._lock:
            return self._facts.get(provider)

    def entry(self, provider: str, model_id: str) -> "Optional[tuple]":
        """``(CatalogueModel, state)`` or ``None``."""
        with self._lock:
            entry = self._entries.get((provider, model_id))
            for model in self._catalogue:
                if model.key == (provider, model_id) and entry is not None:
                    return model, entry.state
        return None

    def is_verified(self, provider: str, access: str, model_id: str) -> bool:
        with self._lock:
            facts, entry = self._facts.get(provider), self._entries.get((provider, model_id))
            return (facts is not None and facts.access == access and servable(facts)
                    and entry is not None and entry.state == STATE_VERIFIED)

    def has_catalogue(self) -> bool:
        with self._lock:
            return bool(self._catalogue)

    def verified_providers(self) -> "list[str]":
        with self._lock:
            return sorted({key[0] for key, entry in self._entries.items()
                           if entry.state == STATE_VERIFIED and key[0] in self._facts and servable(self._facts[key[0]])})

    def due(self, probe_interval: float, failed_retry: float) -> "list[tuple]":
        """The ``(provider, model)`` pairs whose minimal call is due, in catalogue order."""
        tick = self._mono()
        found: list = []
        with self._lock:
            for model in self._catalogue:
                facts, entry = self._facts.get(model.provider), self._entries.get(model.key)
                if facts is None or entry is None or not servable(facts):
                    continue
                age = tick - entry.checked_mono
                if (entry.state == STATE_NOT_VERIFIED
                        or (entry.state == STATE_VERIFIED and age >= probe_interval)
                        or (entry.state == STATE_FAILED and age >= failed_retry)):
                    found.append((model, facts))
        return found

    def slot_capacity(self) -> dict:
        with self._lock:
            return self._slots_locked()

    def _slots_locked(self) -> dict:
        return {provider: self._slot_overrides.get(provider, DEFAULT_SLOTS[facts.access])
                for provider, facts in self._facts.items()}

    def snapshot(self) -> tuple:
        """``(providers, slots)`` for the report: built only when something changed since the last build."""
        with self._lock:
            if self._snapshot is None:
                self.builds += 1
                providers = []
                for provider in PROVIDERS:
                    facts = self._facts.get(provider)
                    if facts is not None:
                        providers.append(self._provider_locked(facts))
                self._snapshot = (providers, self._slots_locked())
            return self._snapshot

    def _provider_locked(self, facts: detect.ProviderFacts) -> dict:
        models = []
        for model in self._catalogue:
            if model.provider != facts.provider:
                continue
            entry = self._entries[model.key]
            item = {"model_id": model.model_id, "state": entry.state, "checked_at": timestamp(entry.checked_at)}
            if entry.failure_code:
                item["failure_code"] = entry.failure_code
            models.append(item)
        states = [m["state"] for m in models]
        failures = [m.get("failure_code") for m in models]
        auth = facts.auth_state
        if facts.provider in API_PROVIDERS:
            if STATE_VERIFIED in states:
                auth = detect.AUTH_VALID
            elif "auth_failed" in failures:
                auth = detect.AUTH_LOGIN_REQUIRED
        elif auth == detect.AUTH_VALID and STATE_VERIFIED not in states and "auth_failed" in failures:
            auth = detect.AUTH_LOGIN_REQUIRED
        payload: dict = {"provider": facts.provider, "access": facts.access}
        if self.report_cli_path and facts.cli_path:
            payload["cli_path"] = facts.cli_path
        if facts.cli_version:
            payload["cli_version"] = facts.cli_version
        payload["auth_state"] = auth
        payload["models"] = models
        return payload


# ------------------------------------------------------------------------------ the runtime


Detector = Callable[[], "detect.HostDetection"]


class HostRuntime:
    """The state and the work of host mode that the claim loop and the health reporter share."""

    def __init__(self, cfg: HostConfig, log: Callable[[str], None], stop: threading.Event, *,
                 detector: Optional[Detector] = None, mono: Callable[[], float] = time.monotonic) -> None:
        self.cfg = cfg
        self.log = log
        self.stop = stop
        self._mono = mono
        self.book = ModelBook(report_cli_path=cfg.report_cli_path, slots=cfg.slots)
        self.slots = SlotPool()
        self.detector = detector or (lambda: detect.detect_host(key_file=cfg.key_file, expected_uid=cfg.expected_uid))
        self.enabled: Optional[bool] = None
        self.urgent = threading.Event()  # set when the report should go out now
        self.wake = threading.Event()  # set when a minimal call may be due
        self.probes_run = 0
        self._clis: tuple = ()
        self._detected_at: Optional[float] = None
        self._key_notice: Optional[str] = None
        self._warned_no_catalogue = False
        self._detect_lock = threading.Lock()

    # -------------------------------------------------------------------------- recount

    def refresh(self, force: bool = False) -> None:
        """Cheap detection (no model is called) and the snapshot when it changed.  Called by the health reporter
        every ``detect_seconds``; a second call inside the same second is answered from the first."""
        with self._detect_lock:
            tick = self._mono()
            if not force and self._detected_at is not None and tick - self._detected_at < 1.0:
                return
            detection = self.detector()
            self._detected_at = tick
            self._clis = detection.clis
            keys = detection.key_file
            notice = keys.describe() if keys.present and keys.reason else None
            if notice != self._key_notice:
                self._key_notice = notice
                if notice:
                    self.log(f"keys: {keys.path} is {notice}; no API key is read from it")
            for name in keys.rejected:
                self.log(f"keys: {name} in {keys.path} has an unusable value and is ignored")
            changed = self.book.apply_facts(detection.providers)
            self.slots.set_capacity(self.book.slot_capacity())
            if changed:
                self.log("host: detection changed for " + ", ".join(sorted(changed)) + "; its models are checked again")
                self.wake.set()
                self.urgent.set()

    def clis(self) -> tuple:
        return self._clis

    def health_extras(self) -> "tuple[list, dict]":
        """``(providers, slots)`` for the health report."""
        providers, slots = self.book.snapshot()
        return providers, slots

    def accept_ack(self, document: Mapping) -> None:
        """The stand's answer to a health report: the current catalogue and the host's «Использовать» switch."""
        if "catalogue" in document:
            models, problems = parse_catalogue(document["catalogue"])
            for problem in problems:
                self.log(f"catalogue: {problem}; that entry is not served")
            if self.book.set_catalogue(models):
                self.log(f"catalogue: {len(models)} model(s) from the stand")
                self.wake.set()
                self.urgent.set()
        elif not self.book.has_catalogue() and not self._warned_no_catalogue:
            self._warned_no_catalogue = True
            self.log("health: the stand's answer carries no catalogue; no model can be checked")
        enabled = document.get("enabled")
        if type(enabled) is bool and enabled != self.enabled:
            if self.enabled is not None or not enabled:
                self.log(f"host: «Использовать» is now {'on' if enabled else 'off'}; claims go on for runs already bound")
            self.enabled = enabled

    # ------------------------------------------------------------------------- claim gate

    def can_claim(self, in_work: int) -> bool:
        """Claim only when some model is verified and fewer tasks are in work than the slots of the providers that
        serve one (a task of a provider whose slots are full would only wait)."""
        verified = self.book.verified_providers()
        if not verified:
            return False
        return in_work < sum(self.slots.capacity(provider) for provider in verified)

    # ----------------------------------------------------------------------------- probes

    def probe_pass(self) -> int:
        """Run the minimal call of every model that is due, one at a time, each inside its provider's slot."""
        ran = 0
        for model, facts in self.book.due(self.cfg.probe_interval_seconds, self.cfg.failed_retry_seconds):
            if self.stop.is_set():
                break
            if not self.slots.try_acquire(model.provider):
                continue  # the provider is busy with real work: try again at the next pass
            try:
                failure = self._probe(model, facts)
            except Stopped:
                break  # the agent is stopping: nothing is recorded about a call that was cut short
            finally:
                self.slots.release(model.provider)
            self.book.record_probe(model.provider, model.model_id, failure)
            ran += 1
            self.probes_run += 1
            self.urgent.set()
            self.log(f"probe: {model.provider}/{model.model_id} "
                     + ("verified" if failure is None else f"failed ({failure_code(failure)})"))
        return ran

    def _probe(self, model: CatalogueModel, facts: detect.ProviderFacts) -> Optional[str]:
        task = {"system": _PROBE_SYSTEM, "user_text": _PROBE_USER, "output_schema": _PROBE_SCHEMA}
        try:
            reply = self.dispatch(
                facts, model, probe_effort(model.efforts), task, max_output_tokens=PROBE_MAX_OUTPUT_TOKENS,
                timeout=self.cfg.probe_timeout_seconds, activity=Activity(),
                should_stop=lambda: "agent_shutdown" if self.stop.is_set() else "")
        except HostFailure as error:
            return error.code
        try:
            document = json.loads(reply["output_text"])
        except (ValueError, TypeError):
            return "probe_bad_answer"
        return None if isinstance(document, dict) and document.get("ok") is True else "probe_bad_answer"

    def run_probes(self) -> None:
        """The probe thread: wait for something to check, check it, repeat until the agent stops."""
        while not self.stop.is_set():
            try:
                self.probe_pass()
            except Exception as error:  # noqa: BLE001 - a probe must not take the agent down
                self.log(f"probe: internal error {type(error).__name__}")
            self.wake.wait(5.0)
            self.wake.clear()

    def start_probes(self) -> threading.Thread:
        thread = threading.Thread(target=self.run_probes, name="host-probes", daemon=True)
        thread.start()
        return thread

    # --------------------------------------------------------------------------- dispatch

    def check_task(self, task: Mapping) -> "tuple[CatalogueModel, detect.ProviderFacts]":
        """The catalogue model and provider facts a claimed task is for, or :class:`HostFailure`.  A task whose model
        this host does not currently report as verified for that provider and access is refused with
        ``model_not_available`` before anything runs."""
        provider, access, model_id = task.get("provider"), task.get("access"), task.get("model_id")
        if not isinstance(provider, str) or not isinstance(access, str) or not isinstance(model_id, str):
            raise HostFailure("host_task_incomplete", "the task names no provider, access or model_id")
        found = self.book.entry(provider, model_id)
        facts = self.book.facts(provider)
        if found is None or facts is None or not self.book.is_verified(provider, access, model_id):
            raise HostFailure("model_not_available", f"{provider}/{access}/{model_id} is not reported verified by this host")
        model = found[0]
        effort = task.get("effort")
        if effort not in model.efforts:
            raise HostFailure("effort_not_allowed", f"{provider}/{model_id} has no effort {str(effort)[:20]}")
        return model, facts

    def execute(self, task: Mapping, model: CatalogueModel, facts: detect.ProviderFacts, *, budget: float,
                activity: Activity, should_stop: Callable[[], str], local_images: tuple = ()) -> dict:
        """Answer one claimed task.  ``budget`` is the seconds left before the task's deadline.  Returns the answer
        document of the answerer (``output_text``, ``reported_model``, token counts) or raises :class:`HostFailure`
        / :class:`Stopped`.  A failure about the host's access also takes the model out of service."""
        timeout = min(float(task["timeout_seconds"]), budget)
        if timeout <= 0:
            raise HostFailure("timeout", "no time remains before the task deadline")
        call = {"system": task["system"], "user_text": task["user_text"], "output_schema": task["output_schema"]}
        try:
            return self.dispatch(facts, model, task["effort"], call, max_output_tokens=task["max_output_tokens"],
                                 timeout=timeout, activity=activity, should_stop=should_stop, local_images=local_images)
        except HostFailure as error:
            if error.code in ACCESS_KINDS:
                self.book.mark_failed(model.provider, model.model_id, error.code)
                self.urgent.set()
                self.wake.set()
            raise

    def dispatch(self, facts: detect.ProviderFacts, model: CatalogueModel, effort: str, call: Mapping, *,
                 max_output_tokens: int, timeout: float, activity: Activity, should_stop: Callable[[], str],
                 local_images: tuple = ()) -> dict:
        """One call to the answerer of the provider; its errors become :class:`HostFailure` or :class:`Stopped`."""
        provider = model.provider
        if local_images and provider == detect.PROVIDER_CLAUDE_CODE:
            raise HostFailure("image_input_unsupported", "the Claude Code command takes no image")
        try:
            if provider == detect.PROVIDER_CLAUDE_CODE:
                reply = claude_answer.run_host(
                    call, model=model.model_id, effort=effort, timeout=timeout, claude=facts.cli_path,
                    accepted=model.accepted_reported, activity=activity, should_stop=should_stop,
                    max_output_tokens=max_output_tokens)
            elif provider == detect.PROVIDER_CODEX:
                extra: dict = {}
                if local_images:
                    extra = {"images": [{k: v for k, v in item.items() if k != "path"} for item in local_images],
                             "local_images": list(local_images)}
                reply = codex_answer.run_host(
                    {**call, **extra}, model=model.model_id, effort=effort, timeout=timeout, codex=facts.cli_path,
                    accepted=model.accepted_reported, activity=activity, should_stop=should_stop)
            else:
                key = detect.read_api_key(provider, self.cfg.key_file, expected_uid=self.cfg.expected_uid)
                if key is None:
                    raise HostFailure("auth_failed", f"no key for {provider} in the key file")
                strict = None
                if provider == api_answer.PROVIDER_OPENAI:
                    strict = codex_answer._codex_output_schema(call["output_schema"])
                images = [self._read_image(item) for item in local_images]
                result = api_answer.call(
                    provider, api_key=key, model=model.model_id, effort=effort, max_output_tokens=max_output_tokens,
                    timeout=timeout, idle_timeout=min(self.cfg.activity_window_seconds, timeout),
                    system=call["system"], user_text=call["user_text"], output_schema=call["output_schema"],
                    base_url=self.cfg.base_urls.get(provider), images=images, strict_schema=strict,
                    accepted=model.accepted_reported, activity=activity, should_stop=should_stop)
                reply = {"output_text": result.output_text, "reported_model": result.reported_model,
                         "input_tokens": result.input_tokens, "output_tokens": result.output_tokens}
        except (claude_answer.Interrupted, codex_answer.Interrupted, api_answer.Interrupted) as stop:
            raise Stopped(str(stop)) from None
        except HostFailure:
            raise
        except (claude_answer.TaskError, codex_answer.TaskError) as error:
            kind = getattr(error, "kind", None)
            raise HostFailure(kind or str(error), f"{provider}/{model.model_id}") from None
        except api_answer.ApiError as error:
            raise HostFailure(error.kind or error.code, f"{provider}/{model.model_id}") from None
        except (ValueError, OSError):
            raise HostFailure("answerer_error", f"{provider}/{model.model_id}") from None
        return reply

    @staticmethod
    def _read_image(item: Mapping) -> bytes:
        with open(item["path"], "rb") as handle:
            return handle.read()
