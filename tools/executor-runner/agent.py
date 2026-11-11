#!/usr/bin/env python3
"""Unattended pull agent for the PDF Analysis executor channel (RUNNER_API.md).

Claims tasks from the stand over HTTPS, answers each with a local command or a local
OpenAI-compatible model, and submits the answer. It works from behind NAT: the stand never
connects to it. Standard library only (Python 3.11+, ``tomllib``).

    PDF_ANALYSIS_RUNNER_TOKEN=... python3 agent.py --config agent.toml [--max-tasks N]

Exit codes: 0 normal stop (signal or ``--max-tasks`` reached), 2 configuration error,
3 the stand rejected the token or the one-time enrollment secret (restarting will not help),
75 the stand could not be reached while enrolling (the same secret may be tried again).

``EXEC2-AGENT-01``: besides claiming, the process tells the stand what it is (``POST /runner/health``: version,
detected CLIs with their official auth state, concurrency, profile, features) at start, every ten minutes and
whenever detection changes; and ``--enroll-only --env-file F`` (what ``install.sh`` runs, as root) exchanges the
one-time secret in ``AUDITMANAGER_ENROLLMENT_SECRET`` for a runner token, stores the token in ``F`` and removes
the secret from ``F``.

``HOSTS-AGENT-01``: ``[executor] mode = "host"`` is the **host mode** (``RUNNER_API.md`` section 10): one process and one
host token serve every model this host can reach (the ``claude`` and ``codex`` CLIs, and the API keys in the service's key
file), with no model at install.  The stand's catalogue says which models matter; the agent checks each with a minimal call,
reports what it verified with every heartbeat (60 s), and refuses a task whose model it does not currently report as
verified.  ``HostAgent`` and ``HostHealthReporter`` below are that mode; the single-model agent (a token bound to one
connection, ``mode = "command"`` or ``"endpoint"``) is unchanged.

Rules kept here:

* the token (and an endpoint key) come from environment variables named in the config, never
  from the command line or the config file, and are removed from every log line;
* the task payload (document text) is never logged; command stdin uses a private
  temporary file held only for the child process's lifetime;
* a model other than the one declared in the config is never claimed to have answered: a task
  that pins another model is failed with ``model_mismatch`` before any work starts;
* a schema-invalid answer is failed with a typed reason, never retried silently;
* the enrollment secret comes from the environment only, is removed from this process's environment at
  once and is never logged, written or sent anywhere but as the bearer of the one exchange;
* one process serves one token (v1): it names itself in every claim (``runner_instance_id``, random per
  process), claims only when a local slot is free, and never starts a task id it is already working on.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import detect
import host_mode
from runner_client import (
    AGENT_VERSION_RE,
    Backoff,
    RunnerAuthError,
    RunnerClient,
    RunnerConflict,
    RunnerError,
    RunnerNotFound,
    RunnerRejected,
    RunnerThrottled,
    RunnerUnavailable,
    serves_images,
    throttle_delay,
)

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_AUTH = 3
EXIT_TEMPFAIL = 75  # sysexits EX_TEMPFAIL: enrolling failed for a reason a retry may cure

DEFAULT_TOKEN_ENV = "PDF_ANALYSIS_RUNNER_TOKEN"
#: `EXEC2-AGENT-01`: the one-time enrollment secret, in the environment of `install.sh` and of `--enroll-only`.
ENROLLMENT_SECRET_ENV = "AUDITMANAGER_ENROLLMENT_SECRET"
#: The report is repeated this often, and sooner when detection changes; detection itself runs this often (cheap:
#: CLI presence, version, login, key file; no model is called).  A host agent repeats its report every
#: ``host_mode.REPORT_SECONDS`` (60 s): the stand reads the report as the host's pulse.
HEALTH_REPORT_SECONDS = 600.0
HEALTH_DETECT_SECONDS = 60.0
UNVERSIONED = "unversioned"
DEADLINE_MARGIN_SECONDS = 5.0
#: After the stand hands back a task this process is still working on (a token whose limit is one is
#: given its held task again), wait this long before claiming again: RUNNER_API.md 2.1's floor between
#: claims that do not wait.
DUPLICATE_DELIVERY_PAUSE_SECONDS = 5.0
FORBIDDEN_KEY_EXACT = {"token", "secret", "password", "api_key", "apikey", "key", "bearer", "authorization"}
FORBIDDEN_KEY_SUFFIXES = ("_token", "_secret", "_password", "_key")

KNOWN_KEYS = {
    "runner": {"origin", "token_env", "wait_seconds", "ca_file", "allow_insecure_http", "concurrency", "drain_seconds", "extend_floor_seconds", "backoff_min_seconds", "backoff_max_seconds"},
    "model": {"declared"},
    "executor": {"mode"},
    "host": host_mode.HOST_KEYS,
    "slots": host_mode.SLOT_KEYS,
    "api": host_mode.API_KEYS,
    "command": {"argv", "timeout_seconds", "cwd", "accept_images", "max_images"},
    "endpoint": {"url", "model", "api_key_env", "timeout_seconds", "response_format", "temperature", "max_tokens", "accept_images", "max_images"},
}


class ConfigError(Exception):
    pass


def new_instance_id() -> str:
    """The name of this agent process in every claim (RUNNER_API.md 2.1): 22 url-safe characters,
    random per process, so a restarted agent is a different instance and is not handed the claim its
    predecessor held (that lapses and the task follows the stand's re-open rule)."""
    return secrets.token_urlsafe(16)


@dataclass
class Config:
    origin: str
    token_env: str = DEFAULT_TOKEN_ENV
    wait_seconds: int = 25
    ca_file: Optional[str] = None
    allow_insecure_http: bool = False
    concurrency: int = 1
    drain_seconds: float = 60.0
    extend_floor_seconds: float = 1.0
    backoff_min_seconds: float = 1.0
    backoff_max_seconds: float = 60.0
    declared_model: str = ""
    mode: str = "command"
    command_argv: list[str] = field(default_factory=list)
    command_timeout: float = 540.0
    command_cwd: Optional[str] = None
    command_accept_images: bool = False
    command_max_images: int = 1
    endpoint_url: str = ""
    endpoint_model: str = ""
    endpoint_api_key_env: str = ""
    endpoint_timeout: float = 540.0
    response_format: str = "none"
    temperature: float = 0.0
    max_tokens: int = 0
    endpoint_accept_images: bool = False
    endpoint_max_images: int = 1
    host: Optional[host_mode.HostConfig] = None  # `HOSTS-AGENT-01`: set exactly when mode == "host"

    @property
    def accept_images(self) -> bool:
        if self.mode == "host":
            return bool(self.host and self.host.accept_images)
        return self.command_accept_images if self.mode == "command" else self.endpoint_accept_images

    @property
    def declared_max_images(self) -> int:
        """What the agent tells the stand it serves in one task: the configured count when it
        accepts images at all, otherwise 1 (the stand's default for a claim that says nothing).
        A task the agent cannot serve is still refused by :meth:`Agent._worker`."""
        if not self.accept_images:
            return 1
        if self.mode == "host":
            return self.host.max_images
        return self.command_max_images if self.mode == "command" else self.endpoint_max_images


def _reject_secret_keys(document: dict, where: str = "") -> None:
    for key, value in document.items():
        lowered = key.lower().replace("-", "_")
        if lowered.endswith("_env"):
            pass  # the NAME of an environment variable is fine
        elif lowered in FORBIDDEN_KEY_EXACT or lowered.endswith(FORBIDDEN_KEY_SUFFIXES):
            raise ConfigError(
                f"config key {where}{key!r} looks like a secret: secrets belong in environment variables "
                "(name the variable with token_env / api_key_env), never in the config file"
            )
        if isinstance(value, dict):
            _reject_secret_keys(value, f"{where}{key}.")


def load_config(path: str) -> Config:
    try:
        with open(path, "rb") as handle:
            document = tomllib.load(handle)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except (tomllib.TOMLDecodeError, OSError) as error:
        raise ConfigError(f"cannot read config {path}: {error}") from None
    _reject_secret_keys(document)
    for section, body in document.items():
        if section not in KNOWN_KEYS or not isinstance(body, dict):
            raise ConfigError(f"unknown config section [{section}]")
        unknown = set(body) - KNOWN_KEYS[section]
        if unknown:
            raise ConfigError(f"unknown key(s) in [{section}]: {', '.join(sorted(unknown))}")
    runner, model, executor = document.get("runner", {}), document.get("model", {}), document.get("executor", {})
    command, endpoint = document.get("command", {}), document.get("endpoint", {})
    cfg = Config(origin=str(runner.get("origin", "")))
    cfg.token_env = str(runner.get("token_env", DEFAULT_TOKEN_ENV))
    cfg.wait_seconds = runner.get("wait_seconds", cfg.wait_seconds)
    cfg.ca_file = runner.get("ca_file") or None
    cfg.allow_insecure_http = bool(runner.get("allow_insecure_http", False))
    cfg.concurrency = runner.get("concurrency", cfg.concurrency)
    cfg.drain_seconds = float(runner.get("drain_seconds", cfg.drain_seconds))
    cfg.extend_floor_seconds = float(runner.get("extend_floor_seconds", cfg.extend_floor_seconds))
    cfg.backoff_min_seconds = float(runner.get("backoff_min_seconds", cfg.backoff_min_seconds))
    cfg.backoff_max_seconds = float(runner.get("backoff_max_seconds", cfg.backoff_max_seconds))
    cfg.declared_model = str(model.get("declared", ""))
    cfg.mode = str(executor.get("mode", ""))
    cfg.command_argv = command.get("argv", [])
    cfg.command_timeout = float(command.get("timeout_seconds", cfg.command_timeout))
    cfg.command_cwd = command.get("cwd") or None
    cfg.command_accept_images = command.get("accept_images", False)
    cfg.command_max_images = command.get("max_images", cfg.command_max_images)
    cfg.endpoint_url = str(endpoint.get("url", ""))
    cfg.endpoint_model = str(endpoint.get("model", ""))
    cfg.endpoint_api_key_env = str(endpoint.get("api_key_env", ""))
    cfg.endpoint_timeout = float(endpoint.get("timeout_seconds", cfg.endpoint_timeout))
    cfg.response_format = str(endpoint.get("response_format", cfg.response_format))
    cfg.temperature = float(endpoint.get("temperature", cfg.temperature))
    cfg.max_tokens = int(endpoint.get("max_tokens", cfg.max_tokens))
    cfg.endpoint_accept_images = endpoint.get("accept_images", False)
    cfg.endpoint_max_images = endpoint.get("max_images", cfg.endpoint_max_images)
    if cfg.mode == "host":
        try:
            cfg.host = host_mode.parse_host_config(document.get("host", {}), document.get("slots", {}), document.get("api", {}))
        except ValueError as error:
            raise ConfigError(str(error)) from None
    elif any(name in document for name in ("host", "slots", "api")):
        raise ConfigError('[host], [slots] and [api] belong to [executor] mode = "host"')
    validate_config(cfg)
    return cfg


def _validate_max_images(section: str, value: Any, accept_images: bool) -> None:
    if type(value) is not int or not 1 <= value <= 8:
        raise ConfigError(f"{section} max_images must be an integer in 1..8")
    if value > 1 and not accept_images:
        raise ConfigError(f"{section} max_images above 1 needs accept_images = true: an agent that "
                          "does not take images serves none")


def validate_config(cfg: Config) -> None:
    if not cfg.origin:
        raise ConfigError("[runner] origin is required")
    if not isinstance(cfg.wait_seconds, int) or isinstance(cfg.wait_seconds, bool) or not 0 <= cfg.wait_seconds <= 25:
        raise ConfigError("[runner] wait_seconds must be an integer in 0..25")
    if not isinstance(cfg.concurrency, int) or isinstance(cfg.concurrency, bool) or not 1 <= cfg.concurrency <= 8:
        raise ConfigError("[runner] concurrency must be an integer in 1..8")
    if cfg.mode == "host":
        return  # no model is declared: the catalogue says which models matter and the agent verifies each (section 10)
    if not cfg.declared_model:
        raise ConfigError("[model] declared is required: the exact pinned model id this agent answers as")
    if cfg.mode not in ("command", "endpoint"):
        raise ConfigError('[executor] mode must be "command", "endpoint" or "host"')
    if cfg.mode == "command":
        if not math.isfinite(cfg.command_timeout) or cfg.command_timeout < 0:
            raise ConfigError("[command] timeout_seconds must be finite and non-negative (0 uses the task deadline)")
        argv = cfg.command_argv
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
            raise ConfigError("[command] argv must be a non-empty list of strings")
        if type(cfg.command_accept_images) is not bool:
            raise ConfigError("[command] accept_images must be a boolean")
        _validate_max_images("[command]", cfg.command_max_images, cfg.command_accept_images)
    else:
        if type(cfg.endpoint_accept_images) is not bool:
            raise ConfigError("[endpoint] accept_images must be a boolean")
        _validate_max_images("[endpoint]", cfg.endpoint_max_images, cfg.endpoint_accept_images)
        if not cfg.endpoint_url.startswith(("http://", "https://")):
            raise ConfigError("[endpoint] url must be an http(s) URL of a /v1/chat/completions endpoint")
        if not cfg.endpoint_model:
            raise ConfigError("[endpoint] model (the local model name sent to the endpoint) is required")
        if cfg.response_format not in ("none", "json_object", "json_schema"):
            raise ConfigError('[endpoint] response_format must be "none", "json_object" or "json_schema"')


# ---------------------------------------------------------------------------- executors


class ExecutorFailure(Exception):
    """The local work failed. ``code`` becomes the start of the ``fail`` reason."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass
class Answer:
    output_text: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    reported_model: Optional[str] = None  # host mode: the exact string the CLI or API reported
    context_sha256: Optional[str] = None  # host mode (`CTX-RUNNER`): the stand's digest of the reference data the prompt carried


class Interrupted(Exception):
    """The work was abandoned because the claim was lost, the deadline passed or the agent is stopping."""


def run_command(cfg: Config, task: dict, budget: float, should_stop: Any) -> Answer:
    """Task JSON to the command's stdin; its stdout is the answer document."""
    payload = json.dumps(task, ensure_ascii=False).encode("utf-8")
    allowance = min(cfg.command_timeout, budget) if cfg.command_timeout > 0 else budget
    if allowance <= 0:
        raise ExecutorFailure("timeout", "no command time remains before the task deadline")
    deadline = time.monotonic() + allowance
    environment = os.environ.copy()
    # Both processes use the same monotonic clock. Leave time to report the typed failure
    # before the supervisor expires; never replace the stand's clock-adjusted budget.
    environment["PDF_ANALYSIS_COMMAND_DEADLINE_MONOTONIC"] = str(
        deadline - min(1.0, allowance / 10.0))
    with tempfile.TemporaryFile(mode="w+b") as command_input:
        # All bytes and EOF are available before polling begins. A partially
        # written stdin pipe must not depend on a later communicate(input=None),
        # which can stop registering that pipe after its first timeout.
        command_input.write(payload)
        command_input.seek(0)
        try:
            process = subprocess.Popen(
                cfg.command_argv,
                stdin=command_input,
                stdout=subprocess.PIPE,
                cwd=cfg.command_cwd,
                env=environment,
                start_new_session=True,  # so that only this command's own process group is ever signalled
            )
        except OSError as error:
            raise ExecutorFailure("command_failed", f"cannot start: {type(error).__name__}") from None
        stdout: bytes = b""
        try:
            while True:
                try:
                    stdout, _ = process.communicate(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    pass
                except (BrokenPipeError, OSError):
                    # Collect any answer already produced if the output pipe closed.
                    try:
                        stdout, _ = process.communicate(timeout=1.0)
                        break
                    except subprocess.TimeoutExpired:
                        pass
                reason = should_stop()
                if reason:
                    raise Interrupted(reason)
                if time.monotonic() >= deadline:
                    raise ExecutorFailure("timeout", "the command did not finish within its time budget")
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)  # our own child's group, by its confirmed PID
                except (ProcessLookupError, PermissionError, OSError):
                    process.kill()
                process.wait()
    if process.returncode == 124:
        raise ExecutorFailure("codex_timeout", "the CLI exhausted its task time budget; see the runner's safe diagnostics")
    if process.returncode != 0:
        raise ExecutorFailure("command_failed", f"exit status {process.returncode}")
    try:
        text = stdout.decode("utf-8").strip()
    except UnicodeDecodeError:
        raise ExecutorFailure("command_bad_output", "stdout is not UTF-8") from None
    if not text:
        raise ExecutorFailure("command_bad_output", "the command printed nothing")
    return Answer(text)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def run_endpoint(cfg: Config, task: dict, budget: float, should_stop: Any, api_key: str,
                 images: Sequence[bytes] = ()) -> Answer:
    """One non-streaming chat completion against a local OpenAI-compatible endpoint.

    ``images`` are the task's verified PNGs, **all of them and in the task's order**; each is one
    ``image_url`` block after the text. An endpoint that does not accept images refuses the
    task rather than being sent the text alone."""
    body: dict[str, Any] = {
        "model": cfg.endpoint_model,
        "messages": [{"role": "system", "content": task["system"]}, {"role": "user", "content": task["user_text"]}],
        "temperature": cfg.temperature,
        "stream": False,
    }
    if images:
        if not cfg.endpoint_accept_images:
            raise ExecutorFailure("image_input_unsupported")
        body["messages"][1]["content"] = [
            {"type": "text", "text": task["user_text"]},
            *({"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(raw).decode("ascii")}}
              for raw in images),
        ]
    if cfg.response_format == "json_object":
        body["response_format"] = {"type": "json_object"}
    elif cfg.response_format == "json_schema":
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": task["output_schema"], "strict": True}}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    request = urllib.request.Request(cfg.endpoint_url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers=headers, method="POST")
    timeout = max(1.0, min(cfg.endpoint_timeout, budget))
    # The HTTP call cannot be interrupted from outside; check the stop conditions before and after it.
    reason = should_stop()
    if reason:
        raise Interrupted(reason)
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        raise ExecutorFailure("endpoint_failed", f"HTTP {error.code}") from None
    except Exception as error:  # noqa: BLE001 - timeouts, refused connections, TLS
        raise ExecutorFailure("endpoint_failed", type(getattr(error, "reason", error)).__name__) from None
    reason = should_stop()
    if reason:
        raise Interrupted(reason)
    try:
        document = json.loads(raw.decode("utf-8"))
        choice = document["choices"][0]
        content = choice["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError, UnicodeDecodeError):
        raise ExecutorFailure("endpoint_failed", "the response is not an OpenAI chat completion") from None
    if choice.get("finish_reason") == "length":
        raise ExecutorFailure("output_truncated", "the model stopped at its length limit")
    if not isinstance(content, str) or not content.strip():
        raise ExecutorFailure("endpoint_failed", "the completion has no text")
    usage = document.get("usage") if isinstance(document.get("usage"), dict) else {}
    tokens = {name: usage.get(key) for name, key in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens"))}
    return Answer(
        content.strip(),
        tokens["input_tokens"] if isinstance(tokens["input_tokens"], int) and not isinstance(tokens["input_tokens"], bool) and tokens["input_tokens"] >= 0 else None,
        tokens["output_tokens"] if isinstance(tokens["output_tokens"], int) and not isinstance(tokens["output_tokens"], bool) and tokens["output_tokens"] >= 0 else None,
    )


# ------------------------------------------------------------------------------ agent


class Agent:
    def __init__(self, cfg: Config, client: RunnerClient, api_key: str, err: Any, instance_id: Optional[str] = None) -> None:
        self.cfg = cfg
        self.client = client
        self.api_key = api_key
        self._err = err
        self.instance_id = instance_id or new_instance_id()
        self.stop = threading.Event()
        self.abort = threading.Event()
        self.auth_failed = threading.Event()
        self._workers: list[threading.Thread] = []
        self._log_lock = threading.Lock()
        # The ids of the tasks a worker of this process is working on, guarded by its own lock: the
        # claim loop adds an id before the worker starts and the worker removes it when it ends.
        self._work_lock = threading.Lock()
        self._in_work: set[str] = set()
        self.activity_window = host_mode.ACTIVITY_WINDOW_SECONDS

    def _enter_work(self, task_id: str) -> bool:
        """Register a task as in work. ``False`` when it already is: the stand handed this process a
        task it is still working on, which must not be started a second time."""
        with self._work_lock:
            if task_id in self._in_work:
                return False
            self._in_work.add(task_id)
            return True

    def _leave_work(self, task_id: str) -> None:
        with self._work_lock:
            self._in_work.discard(task_id)

    def in_work(self) -> frozenset[str]:
        with self._work_lock:
            return frozenset(self._in_work)

    def log(self, message: str) -> None:
        text = self.client.scrub(message)
        if self.api_key:
            text = text.replace(self.api_key, "***")
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._log_lock:
            try:
                self._err.write(f"{stamp} agent: {text.replace(chr(10), ' ')}\n")
                self._err.flush()
            except (OSError, ValueError):
                pass

    # -------------------------------------------------------------------- main loop

    def run(self, max_tasks: Optional[int]) -> int:
        slots = self._claim_slots()
        backoff = Backoff(self.cfg.backoff_min_seconds, self.cfg.backoff_max_seconds)
        claimed = 0
        self.log(f"started: origin={self.client.origin} {self._start_note()} instance={self.instance_id} "
                 f"max_tasks={max_tasks if max_tasks else 'unlimited'}")
        while not self.stop.is_set() and not self.auth_failed.is_set() and (not max_tasks or claimed < max_tasks):
            if not slots.acquire(timeout=0.5):  # claim only with a free local slot
                continue
            try:
                task = self.client.claim(
                    self.cfg.wait_seconds, self.cfg.declared_max_images, runner_instance_id=self.instance_id)
            except RunnerAuthError:
                slots.release()
                self.auth_failed.set()
                break
            except RunnerThrottled as error:
                slots.release()
                pause = throttle_delay(error)
                self.log(f"throttled by the stand (HTTP 429); waiting {pause:.1f}s")
                self.stop.wait(pause)
                continue
            except RunnerError as error:  # unavailable, or a request the stand refused
                slots.release()
                pause = backoff.next_delay()
                self.log(f"claim failed ({error.message}); retrying in {pause:.1f}s")
                self.stop.wait(pause)
                continue
            backoff.reset()
            if task is None:
                slots.release()
                if self.cfg.wait_seconds == 0:
                    self.stop.wait(5.0)  # RUNNER_API.md 2.1: never poll faster than every 5 s without a wait
                continue
            if not self._enter_work(task["task_id"]):
                # A token whose limit is one is given its held task again; this process is still
                # working on it. Starting it twice would answer it twice.
                slots.release()
                self.log(f"{task['task_id']}: delivered again while still in work; not started a second time")
                self.stop.wait(DUPLICATE_DELIVERY_PAUSE_SECONDS)
                continue
            claimed += 1
            worker = threading.Thread(target=self._worker, args=(task, slots), name=task["task_id"], daemon=True)
            self._workers.append(worker)
            worker.start()
        return self._finish()

    def _claim_slots(self) -> Any:
        """What the claim loop acquires before it claims and the worker releases: the local task slots."""
        return threading.Semaphore(self.cfg.concurrency)

    def _start_note(self) -> str:
        return f"mode={self.cfg.mode} declared_model={self.cfg.declared_model} concurrency={self.cfg.concurrency}"

    def _finish(self) -> int:
        end = time.monotonic() + (0.0 if self.auth_failed.is_set() else self.cfg.drain_seconds)
        for worker in self._workers:
            worker.join(timeout=max(0.0, end - time.monotonic()))
        if any(worker.is_alive() for worker in self._workers):
            self.log("drain time over: abandoning tasks still in flight")
            self.abort.set()
            for worker in self._workers:
                worker.join(timeout=10.0)
        if self.auth_failed.is_set():
            print(
                "error: the stand rejected the runner token (HTTP 401): it is wrong, expired or revoked. Issue a new "
                "token in the stand UI, update the environment file, and restart the agent.",
                file=sys.stderr,
            )
            return EXIT_AUTH
        self.log("stopped")
        return EXIT_OK

    # ------------------------------------------------------------------------ one task

    def _worker(self, task: dict, slots: threading.Semaphore) -> None:
        task_id = task["task_id"]
        done = threading.Event()
        state = {"lost": ""}  # "", "claim_lost", "deadline"
        extender = threading.Thread(target=self._extend_loop, args=(task, done, state), daemon=True)
        try:
            self.log(f"claimed {task_id} model={task['model']}")
            if task["model"] != self.cfg.declared_model:
                self._fail(task_id, f"model_mismatch: this agent answers as {self.cfg.declared_model}, the task pins {task['model']}")
                return
            budget = self.client.seconds_until(task["deadline_at"]) - DEADLINE_MARGIN_SECONDS
            if budget <= 0:
                self._fail(task_id, "deadline_exceeded: too little time left to start")
                return
            # Refuse rather than answer on part of the evidence: a task whose images this agent
            # does not take, or more of them than it declared, is given back whole.
            if task.get("images") and not (
                self.cfg.accept_images and serves_images(task, self.cfg.declared_max_images)
            ):
                self._fail(task_id, "image_input_unsupported")
                return
            extender.start()

            def should_stop() -> str:
                if state["lost"]:
                    return state["lost"]
                if self.abort.is_set():
                    return "agent_shutdown"
                return ""

            started = time.monotonic()
            try:
                if self.cfg.mode == "command":
                    with tempfile.TemporaryDirectory(prefix="pdfa-runner-images-") as directory:
                        local_images = []
                        for image, raw in self._fetch_images(task, budget, should_stop):
                            path = Path(directory) / f"{image['blob_id']}.png"
                            path.write_bytes(raw)
                            path.chmod(0o600)
                            local_images.append({**image, "path": str(path)})
                        command_task = {**task, "local_images": local_images}
                        remaining = self.client.seconds_until(task["deadline_at"]) - DEADLINE_MARGIN_SECONDS
                        answer = run_command(self.cfg, command_task, remaining, should_stop)
                else:
                    images = [raw for _, raw in self._fetch_images(task, budget, should_stop)]
                    remaining = self.client.seconds_until(task["deadline_at"]) - DEADLINE_MARGIN_SECONDS
                    answer = run_endpoint(self.cfg, task, remaining, should_stop, self.api_key, images)
            except Interrupted as stop:
                self._interrupted(task_id, str(stop))
                return
            except RunnerAuthError:
                self.auth_failed.set()
                self.stop.set()
                return
            except (RunnerConflict, RunnerNotFound):
                self._interrupted(task_id, "claim_lost")
                return
            except RunnerError as failure:
                self.log(f"{task_id}: image delivery failed ({failure.error_code or failure.status or 'network'})")
                self._fail(task_id, "image_delivery_failed")
                return
            except ExecutorFailure as failure:
                self.log(f"{task_id}: local work failed ({failure})")
                self._fail(task_id, str(failure))
                return
            try:
                json.loads(answer.output_text)
            except ValueError:
                self._fail(task_id, "answer_not_json: the local answer is not a JSON document")
                return
            if state["lost"]:
                self._interrupted(task_id, state["lost"])
                return
            self.log(f"{task_id}: answer ready in {time.monotonic() - started:.1f}s ({len(answer.output_text)} chars)")
            self._submit(task, answer, should_stop)
        except Exception as error:  # noqa: BLE001 - one task must not take the agent down
            self.log(f"{task_id}: internal error {type(error).__name__}")
            self._fail(task_id, f"agent_error: {type(error).__name__}")
        finally:
            done.set()
            self._leave_work(task_id)  # before the slot: a task handed back later is a new piece of work
            slots.release()

    def _fetch_images(self, task: dict, budget: float, should_stop: Any) -> list[tuple[dict, bytes]]:
        """Every image of the task, in its order, each verified against its digest and size. A
        blob that two entries share (two crops with the same bytes) is fetched once. Any failure
        raises: the task is then failed whole, never worked on with some of its images."""
        fetched: dict[str, bytes] = {}
        result: list[tuple[dict, bytes]] = []
        for image in task.get("images", []):
            if should_stop():
                raise Interrupted(should_stop())
            if image["blob_id"] not in fetched:
                fetched[image["blob_id"]] = self.client.image(
                    task["task_id"], image, timeout=max(1.0, min(30.0, budget)))
            result.append((image, fetched[image["blob_id"]]))
        return result

    def _interrupted(self, task_id: str, reason: str) -> None:
        if reason == "deadline":
            self.log(f"{task_id}: deadline reached, abandoning")
            self._fail(task_id, "deadline_exceeded: the answer window closed")
        elif reason == "agent_shutdown":
            self._fail(task_id, "agent_shutdown: the agent was stopped before the answer was ready")
        elif reason == "stalled":
            self.log(f"{task_id}: no output from the call for {self.activity_window:.0f}s; it was stopped and the "
                     "claim is left to lapse (nothing is submitted)")
        else:
            self.log(f"{task_id}: claim lost, abandoning (nothing is submitted)")

    def _extend_loop(self, task: dict, done: threading.Event, state: dict, activity: Any = None) -> None:
        """Extend the claim while the task is worked on.  A host agent passes ``activity``: the claim is extended
        only while the call has produced output in the last ``activity_window`` seconds, so a hung CLI or API call
        lets its claim lapse (and is stopped); a single-model agent extends for as long as the task is in work."""
        task_id = task["task_id"]
        try:
            interval = self._interval(task["claim_expires_at"])
        except ValueError:
            interval = 10.0
        while not done.wait(interval):
            if self.client.seconds_until(task["deadline_at"]) <= 0:
                state["lost"] = "deadline"
                return
            if activity is not None and activity.idle() > self.activity_window:
                state["lost"] = "stalled"
                return
            try:
                reply = self.client.extend(task_id)
                interval = self._interval(reply["claim_expires_at"])
            except (RunnerConflict, RunnerNotFound) as error:
                state["lost"] = "claim_lost"
                self.log(f"{task_id}: claim lost while extending ({error.message})")
                return
            except RunnerAuthError:
                state["lost"] = "claim_lost"
                self.auth_failed.set()
                self.stop.set()
                return
            except RunnerThrottled as error:
                interval = max(self.cfg.extend_floor_seconds, error.retry_after or 0.0)
            except (RunnerError, ValueError, KeyError):
                interval = 2.0

    def _interval(self, claim_expires_at: str) -> float:
        return max(self.cfg.extend_floor_seconds, self.client.seconds_until(claim_expires_at) / 3.0)

    def _submit(self, task: dict, answer: Answer, should_stop: Any) -> None:
        """Deliver the same answer while its claim and server deadline allow it.

        Keep the worker's answer, slot and claim extender alive across temporary
        delivery failures. Re-sending this answer is idempotent on the stand and
        must never turn into another model invocation after a local retry cap.
        """
        task_id = task["task_id"]
        backoff = Backoff(self.cfg.backoff_min_seconds, self.cfg.backoff_max_seconds)
        while True:
            reason = should_stop()
            if reason:
                self.log(f"{task_id}: answer delivery stopped ({reason})")
                return
            if self.client.seconds_until(task["deadline_at"]) <= 0:
                self.log(f"{task_id}: answer delivery stopped (deadline)")
                return
            try:
                reply = self._deliver(task, answer)
                self.log(f"{task_id}: answer accepted (state={reply.get('state')})")
                return
            except RunnerAuthError:
                self.auth_failed.set()
                self.stop.set()
                return
            except (RunnerConflict, RunnerNotFound) as error:
                self.log(f"{task_id}: the stand no longer accepts this task (HTTP {error.status}: {error.message}); dropped")
                return
            except RunnerRejected as error:
                code = error.error_code or "rejected"
                if code == "model_identity_mismatch":
                    kind = "model_identity_mismatch"
                elif error.status == 422:
                    kind = "schema_invalid_answer"
                else:
                    kind = "answer_rejected"
                self.log(f"{task_id}: the stand refused the answer (HTTP {error.status} {code}): {error.message}")
                self._fail(task_id, f"{kind}: {error.message}")
                return
            except (RunnerThrottled, RunnerUnavailable) as error:
                pause = throttle_delay(error) if isinstance(error, RunnerThrottled) else backoff.next_delay()
                remaining = self.client.seconds_until(task["deadline_at"])
                if remaining <= 0:
                    self.log(f"{task_id}: answer delivery stopped (deadline)")
                    return
                pause = min(pause, remaining)
                self.log(f"{task_id}: submit will retry in {pause:.1f}s ({error.message})")
                self.abort.wait(pause)

    def _deliver(self, task: dict, answer: Answer) -> dict:
        """One submission of the answer (submitExecutorTaskAnswer)."""
        return self.client.answer(task["task_id"], answer.output_text, self.cfg.declared_model,
                                  answer.input_tokens, answer.output_tokens)

    def _fail(self, task_id: str, reason: str) -> None:
        try:
            self.client.fail(task_id, reason)
            self.log(f"{task_id}: failed ({reason.split(':')[0]})")
        except RunnerAuthError:
            self.auth_failed.set()
            self.stop.set()
        except RunnerError as error:
            self.log(f"{task_id}: could not report the failure ({error.message})")


# --------------------------------------------------------------------------- host mode (HOSTS-AGENT-01)


class _ClaimGate:
    """Stands in for the semaphore of the single-model claim loop: the loop may claim only when the host mode says a
    task could be served (some model verified and a free slot behind it).  ``release`` is a no-op: the number of
    tasks in work, not a count held here, is what the gate reads."""

    def __init__(self, agent: "HostAgent") -> None:
        self._agent = agent

    def acquire(self, timeout: float = 0.5) -> bool:
        if self._agent.runtime.can_claim(len(self._agent.in_work())):
            return True
        self._agent.stop.wait(min(timeout, 0.5))
        return False

    def release(self) -> None:
        return None


class HostAgent(Agent):
    """The claim loop of host mode (``RUNNER_API.md`` section 10).  It claims with the host token only while a
    model is verified and a slot is free, refuses a task for a model it does not hold as verified
    (``model_not_available``), runs the rest through the answerer of the task's provider inside that provider's
    slot, extends the claim only while the call produces output, and submits the answer with the provider, the
    access and the model the provider itself reported."""

    def __init__(self, cfg: Config, client: RunnerClient, err: Any, instance_id: Optional[str] = None) -> None:
        super().__init__(cfg, client, "", err, instance_id)
        self.runtime = host_mode.HostRuntime(cfg.host, self.log, self.stop)
        self.activity_window = cfg.host.activity_window_seconds

    def _claim_slots(self) -> Any:
        return _ClaimGate(self)

    def _start_note(self) -> str:
        return f"mode=host key_file={self.cfg.host.key_file} activity_window={self.activity_window:.0f}s"

    def _deliver(self, task: dict, answer: Answer) -> dict:
        return self.client.answer(task["task_id"], answer.output_text, task["model_id"], answer.input_tokens,
                                  answer.output_tokens, provider=task["provider"], access=task["access"],
                                  reported_model=answer.reported_model, context_sha256=answer.context_sha256)

    def _reference_for(self, task: dict, should_stop: Any) -> "Optional[host_mode.Reference]":
        """The section to put after the task's JSON (`CTX-RUNNER`, RUNNER_API.md section 11), or ``None`` when the task is not offered reference data.

        Only a task whose claim carries a well-formed ``context_request`` is asked, once, for ``host_mode.CONTEXT_KIND``, with the 8 s of
        ``runner_client.CONTEXT_TIMEOUT_SECONDS`` and no retry.  Whatever goes wrong (a refusal, a 429 whatever its ``Retry-After``, a 5xx, a
        timeout, an answer that is not the contract's, a bug here) gives the notice «Справочные данные недоступны: <причина>» instead: nothing
        is waited for and the task is never failed, never dropped and never stopped because of reference data.  A claim already lost or an agent
        stopping asks nothing: the call that follows is stopped by its own check, as it always was."""
        input_ids = host_mode.context_inputs(task)
        if input_ids is None or should_stop():
            return None
        task_id = task["task_id"]
        try:
            reference = host_mode.reference_from_answer(self.client.context(task_id, host_mode.CONTEXT_KIND), input_ids)
        except host_mode.ReferenceRefused as refused:
            reference = host_mode.unavailable_reference(refused.code)
        except RunnerError as error:
            reference = host_mode.unavailable_reference(context_refusal(error))
        except Exception as error:  # noqa: BLE001 - reference data must not take the task down
            self.log(f"{task_id}: reference data failed inside the agent ({type(error).__name__})")
            reference = host_mode.unavailable_reference("agent_error")
        if reference.context_sha256 is None:
            self.log(f"{task_id}: called without reference data ({reference.section.rsplit(': ', 1)[-1]})")
        else:
            self.log(f"{task_id}: reference data attached ({len(reference.section)} chars)")
        return reference

    def _worker(self, task: dict, slots: Any) -> None:  # noqa: C901 - one task, start to end
        task_id = task["task_id"]
        done = threading.Event()
        state = {"lost": ""}  # "", "claim_lost", "deadline", "stalled"
        activity = host_mode.Activity()
        extender = threading.Thread(target=self._extend_loop, args=(task, done, state, activity), daemon=True)
        provider_slot: Optional[str] = None
        try:
            self.log(f"claimed {task_id} provider={task.get('provider')} access={task.get('access')} "
                     f"model={task.get('model_id')} cell={task.get('cell_key')}")
            try:
                model, facts = self.runtime.check_task(task)
            except host_mode.HostFailure as failure:
                self.log(f"{task_id}: refused ({failure.code})")
                self._fail(task_id, str(failure))
                return
            budget = self.client.seconds_until(task["deadline_at"]) - DEADLINE_MARGIN_SECONDS
            if budget <= 0:
                self._fail(task_id, "deadline_exceeded: too little time left to start")
                return
            if task.get("images") and not (self.cfg.accept_images and serves_images(task, self.cfg.declared_max_images)
                                            and model.provider != detect.PROVIDER_CLAUDE_CODE):
                self._fail(task_id, "image_input_unsupported")
                return
            extender.start()

            def should_stop() -> str:
                if state["lost"]:
                    return state["lost"]
                if self.abort.is_set():
                    return "agent_shutdown"
                return ""

            try:
                while not self.runtime.slots.try_acquire(model.provider):  # never more calls than the provider's slots
                    reason = should_stop()
                    if reason:
                        raise host_mode.Stopped(reason)
                    self.abort.wait(0.2)
                provider_slot = model.provider
                activity.touch()
                started = time.monotonic()
                with tempfile.TemporaryDirectory(prefix="pdfa-runner-images-") as directory:
                    local_images = []
                    for image, raw in self._fetch_images(task, budget, should_stop):
                        path = Path(directory) / f"{image['blob_id']}.png"
                        path.write_bytes(raw)
                        path.chmod(0o600)
                        local_images.append({**image, "path": str(path)})
                    reference = self._reference_for(task, should_stop)
                    remaining = self.client.seconds_until(task["deadline_at"]) - DEADLINE_MARGIN_SECONDS
                    reply = self.runtime.execute(task, model, facts, budget=remaining, activity=activity,
                                                 should_stop=should_stop, local_images=tuple(local_images),
                                                 reference=reference)
            except host_mode.Stopped as stop:
                self._interrupted(task_id, str(stop))
                return
            except Interrupted as stop:
                self._interrupted(task_id, str(stop))
                return
            except RunnerAuthError:
                self.auth_failed.set()
                self.stop.set()
                return
            except (RunnerConflict, RunnerNotFound):
                self._interrupted(task_id, "claim_lost")
                return
            except RunnerError as failure:
                self.log(f"{task_id}: image delivery failed ({failure.error_code or failure.status or 'network'})")
                self._fail(task_id, "image_delivery_failed")
                return
            except host_mode.HostFailure as failure:
                self.log(f"{task_id}: the call failed ({failure.code})")
                self._fail(task_id, str(failure))
                return
            finally:
                if provider_slot is not None:
                    self.runtime.slots.release(provider_slot)
            if state["lost"]:
                self._interrupted(task_id, state["lost"])
                return
            self.log(f"{task_id}: answer ready in {time.monotonic() - started:.1f}s ({len(reply['output_text'])} chars, "
                     f"reported {reply['reported_model']})")
            self._submit(task, Answer(reply["output_text"], reply.get("input_tokens"), reply.get("output_tokens"),
                                      reply["reported_model"], reference.context_sha256 if reference else None), should_stop)
        except Exception as error:  # noqa: BLE001 - one task must not take the agent down
            self.log(f"{task_id}: internal error {type(error).__name__}")
            self._fail(task_id, f"agent_error: {type(error).__name__}")
        finally:
            done.set()
            self._leave_work(task_id)


def context_refusal(error: RunnerError) -> str:
    """The reason the model is told when a context request ended in an error: ``http_<status>`` for a refusal of the stand (``http_401``,
    ``http_404``, ``http_409``, ``http_429``, ``http_503`` ...), ``malformed_answer`` for a 2xx that was not JSON, ``timeout`` or ``network``
    when the stand did not answer at all."""
    if error.status is not None and 200 <= error.status < 300:
        return "malformed_answer"
    if error.status is not None:
        return f"http_{error.status}"
    return "timeout" if re.search(r"timed out|timeout", error.message, re.IGNORECASE) else "network"


# ------------------------------------------------------------- health report and enrollment
# `EXEC2-AGENT-01` (ADR-0026 decisions 4, 5, 8). The stand calls are ``RunnerClient.report_health`` and
# ``RunnerClient.redeem_enrollment`` (RUNNER_API.md section 9).


def agent_version(directory: Optional[Path] = None) -> str:
    """The package version: the ``VERSION`` file ``install.sh`` puts beside this file. A checkout has
    none and says so, in the contract's pattern, instead of inventing a number."""
    try:
        text = ((directory or Path(__file__).resolve().parent) / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return UNVERSIONED
    return text if AGENT_VERSION_RE.fullmatch(text) else UNVERSIONED


def build_health_report(cfg: Config, instance_id: str, clis: list[dict], version: str) -> dict:
    """``ReportRunnerHealthRequest`` of contract 1.15.0: enumerations and bounded strings, nothing else.

    The stand refuses an incoherent report, so one is never built: a client named twice, or a client that is
    not installed yet carries a version or a known authentication state."""
    names = [item["cli"] for item in clis]
    if len(set(names)) != len(names):
        raise ValueError("a client is named twice in one health report")
    if any(not item["installed"] and ("version" in item or item["auth_state"] != detect.AUTH_UNKNOWN) for item in clis):
        raise ValueError("a client that is not installed has a version or an authentication state")
    return {
        "agent_version": version,
        "clis": clis,
        "concurrency": cfg.concurrency,
        "execution_profile": "command" if cfg.mode == "host" else cfg.mode,
        "features": ["images"] if cfg.accept_images else [],
        "runner_instance_id": instance_id,
    }


def build_host_health_report(cfg: Config, instance_id: str, clis: list[dict], version: str, providers: list[dict],
                             slots: dict) -> dict:
    """The host agent's report (``RUNNER_API.md`` section 10.3): the report of any agent, with ``providers`` (what
    detection found, with the state of each catalogue model) and ``slots`` (concurrent calls per provider).
    ``concurrency`` is the sum of the slots, at most 16."""
    report = build_health_report(cfg, instance_id, clis, version)
    report["concurrency"] = max(1, min(host_mode.MAX_REPORTED_CONCURRENCY, sum(slots.values())))
    report["providers"] = providers
    report["slots"] = dict(slots)
    return report


def _describe(clis: list[dict]) -> str:
    return ", ".join(f"{item['cli']}:{'installed' if item['installed'] else 'absent'}/{item['auth_state']}" for item in clis)


class HealthReporter:
    """Tells the stand what this agent is: once at start, every ``report_seconds``, and at once when what
    detection finds changes. Runs beside the claim loop and never blocks it.

    A refusal of the token (401) ends the reporter and nothing else: the claim loop meets the same 401 and owns
    the exit code. A stand without the route (404) or one that refuses the report (422) is logged and tried again
    only at the next interval; a throttled or unreachable stand is tried again after the wait it asks for or
    after a growing pause."""

    def __init__(
        self,
        cfg: Config,
        client: RunnerClient,
        instance_id: str,
        log: Any,
        stop: threading.Event,
        *,
        detector: Any = None,
        version: Optional[str] = None,
        report_seconds: float = HEALTH_REPORT_SECONDS,
        detect_seconds: float = HEALTH_DETECT_SECONDS,
    ) -> None:
        self.cfg = cfg
        self.client = client
        self.instance_id = instance_id
        self.log = log
        self.stop = stop
        self.detector = detector or detect.detect_all
        self.version = version if version is not None else agent_version()
        self.report_seconds = report_seconds
        self.detect_seconds = detect_seconds
        self.sent: list[dict] = []  # the last reports the stand accepted, oldest first (the tests read it)

    def report(self) -> dict:
        return build_health_report(self.cfg, self.instance_id, self.detector(), self.version)

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.run, name="health-reporter", daemon=True)
        thread.start()
        return thread

    def run(self) -> None:
        backoff = Backoff(1.0, 60.0)
        last: Optional[dict] = None
        last_at = 0.0
        pending: Optional[dict] = None
        while not self.stop.is_set():
            if pending is None:
                try:
                    report = self.report()
                except Exception as error:  # noqa: BLE001 - detection must not take the agent down
                    self.log(f"health: detection failed ({type(error).__name__}); trying again later")
                    self._pause(self.detect_seconds)
                    continue
                if last is None or report != last or time.monotonic() - last_at >= self.report_seconds:
                    pending = report
            if pending is not None:
                outcome, wait = self._send(pending)
                if outcome == "token":
                    return
                if outcome == "retry":  # the same report again; detection is not repeated meanwhile
                    self.stop.wait(wait if wait > 0 else backoff.next_delay())
                    continue
                backoff.reset()
                if outcome == "accepted" and (last is None or pending["clis"] != last["clis"]):
                    self.log(f"health: reported {_describe(pending['clis'])}")
                last, last_at, pending = pending, time.monotonic(), None
            self._pause(self.detect_seconds)

    def _pause(self, seconds: float) -> None:
        self.stop.wait(seconds)

    def _on_ack(self, acknowledgement: dict) -> None:
        """The stand's answer to an accepted report (a host agent reads the catalogue and the switch from it)."""

    def _send(self, report: dict) -> tuple[str, float]:
        """``("accepted" | "deferred" | "token" | "retry", seconds)``. ``deferred``: the stand will not take
        this report now, so the next try is the next interval's. ``token``: the stand refused the token.
        ``retry``: try the same report again after ``seconds`` (0 means the backoff's pause)."""
        try:
            acknowledgement = self.client.report_health(report)
        except RunnerAuthError:
            self.log("health: the stand rejected the runner token; the claim loop will stop the agent")
            return "token", 0.0
        except RunnerThrottled as error:
            return "retry", throttle_delay(error)
        except RunnerUnavailable as error:
            self.log(f"health: the stand is not reachable ({error.message}); trying again")
            return "retry", 0.0
        except RunnerError as error:
            if error.status in (404, 405):
                self.log(f"health: this stand does not take health reports (HTTP {error.status}); trying again in "
                         f"{int(self.report_seconds)}s")
            else:
                self.log(f"health: the stand refused the report (HTTP {error.status} {error.error_code or ''}): {error.message}")
            return "deferred", 0.0
        self.sent.append(report)
        del self.sent[:-16]
        self._on_ack(acknowledgement)
        return "accepted", 0.0


class HostHealthReporter(HealthReporter):
    """The health reporter of host mode: the same loop (detect, report on change, repeat at the interval), with
    ``runtime`` doing the detecting and holding the snapshot.  A heartbeat repeats the snapshot as it is; a new one
    is built only when detection, a minimal call or the stand's catalogue changed something in it.  The stand's
    answer carries the current catalogue and the host's «Использовать» switch, which the runtime takes.  A pause is
    cut short when the runtime has something to say (a model verified or failed)."""

    def __init__(self, cfg: Config, client: RunnerClient, instance_id: str, log: Any, stop: threading.Event,
                 runtime: "host_mode.HostRuntime", *, version: Optional[str] = None) -> None:
        super().__init__(cfg, client, instance_id, log, stop, version=version,
                         report_seconds=cfg.host.report_seconds, detect_seconds=cfg.host.detect_seconds)
        self.runtime = runtime

    def report(self) -> dict:
        self.runtime.refresh()
        providers, slots = self.runtime.health_extras()
        return build_host_health_report(self.cfg, self.instance_id, list(self.runtime.clis()), self.version, providers, slots)

    def _on_ack(self, acknowledgement: dict) -> None:
        self.runtime.accept_ack(acknowledgement)

    def _pause(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while not self.stop.is_set() and not self.runtime.urgent.is_set():
            left = end - time.monotonic()
            if left <= 0:
                return
            self.stop.wait(min(0.5, left))
        self.runtime.urgent.clear()


class EnrollmentRefused(Exception):
    """The stand will not exchange this secret (unknown, expired, revoked, redeemed): retrying cannot help."""


class EnrollmentUnavailable(Exception):
    """The stand could not be reached or did not answer: the same secret may be tried again in its window."""


INSTANCE_FILE_NAME = "enroll-instance"
_INSTANCE_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def enrollment_instance_id(env_file: Path) -> str:
    """The ``runner_instance_id`` of the exchange, persisted beside the environment file (mode 0600): one per
    install, new on a host that never enrolled. A rerun on the same install -- the answer was lost, install.sh ran
    again inside the 15-minute window -- sends the same id and so gets the stand's idempotent repeat (a fresh
    token; the one minted before is revoked, and only the newest is stored). Another host has another id and is
    refused with 409 ``enrollment_redeemed``, so a command pasted on two hosts enrolls only the first. The id
    names the exchange and is not a credential; it is not the per-process id of the claims."""
    path = env_file.with_name(INSTANCE_FILE_NAME)
    for _ in range(3):
        try:
            existing, present = path.read_text(encoding="ascii").strip(), True
        except FileNotFoundError:
            existing, present = "", False
        except UnicodeDecodeError:
            existing, present = "", True
        if _INSTANCE_RE.fullmatch(existing):
            return existing
        if present:  # an empty or damaged file (a crash between create and write): replace it
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue  # another process created it between our read and our create; read it again
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            handle.write(secrets.token_urlsafe(16) + "\n")
    raise OSError("the enrollment instance file could not be created")


def store_runner_token(env_file: Path, token_env: str, token: str, drop: tuple[str, ...] = ()) -> None:
    """Write ``token_env=token`` into the environment file (mode 0600, replaced atomically) and remove every
    line that sets ``token_env`` or a name in ``drop`` (the spent enrollment secret). Other lines stay."""
    names = {token_env, *drop}
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
        status: Optional[os.stat_result] = env_file.stat()
    except FileNotFoundError:
        lines, status = [], None
    kept = [line for line in lines if line.partition("=")[0].strip() not in names]
    kept.append(f"{token_env}={token}")
    temporary = env_file.with_name(f".{env_file.name}.{secrets.token_hex(4)}.part")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write("\n".join(kept) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if status is not None and os.geteuid() == 0:
            os.chown(temporary, status.st_uid, status.st_gid)
        os.replace(temporary, env_file)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def enroll_with_grant(cfg: Config, secret: str, env_file: Optional[str], outcome: Optional[dict] = None) -> str:
    """Exchange the one-time secret for a runner token and store the token. Returns the token.

    ``outcome``, when given, is filled with what the stand said besides the token that is safe to show: ``host_id``
    (a host enrollment, ``RUNNER_API.md`` section 10.1) and ``catalogue_models`` (how many models its catalogue names).

    Nothing is sent unless the token can be stored: a spent secret with the token lost would leave the host
    needing a new enrollment. Raises ``ConfigError`` (cannot store, bad origin), ``EnrollmentRefused`` or
    ``EnrollmentUnavailable``."""
    if not env_file:
        raise ConfigError("an enrollment secret needs --env-file PATH: the runner token it yields is stored there")
    path = Path(env_file)
    if not os.access(path.parent, os.W_OK) or (path.exists() and not os.access(path, os.W_OK)):
        raise ConfigError(f"cannot store the runner token in {env_file} from this process (run the enrollment as root, "
                          "for example with install.sh); the secret was not used")
    client = RunnerClient(cfg.origin, secret, allow_insecure_http=cfg.allow_insecure_http, ca_file=cfg.ca_file)
    try:
        issued = client.redeem_enrollment(secret, enrollment_instance_id(path), agent_version())
    except RunnerAuthError:
        raise EnrollmentRefused(
            "the stand refused the enrollment secret (HTTP 401): it is unknown, expired (a secret lasts 15 minutes), "
            "revoked, or belongs to another stand. Issue a new enrollment in the stand UI.") from None
    except RunnerNotFound:
        raise EnrollmentRefused("the stand has no enrollment route (HTTP 404): is the origin right, and is the stand up to date?") from None
    except RunnerConflict:
        raise EnrollmentRefused(
            "the stand refused the enrollment secret (HTTP 409): it was already redeemed, or the connection is archived. "
            "Issue a new enrollment in the stand UI.") from None
    except OSError as error:
        raise ConfigError(f"cannot keep the enrollment instance file beside {env_file} ({type(error).__name__}); "
                          "the secret was not used") from None
    except (RunnerThrottled, RunnerUnavailable) as error:
        raise EnrollmentUnavailable(
            f"the stand did not take the enrollment ({error.message}); run the installer again within the "
            "15-minute window: the same secret is accepted again from this host.") from None
    except RunnerError as error:
        raise EnrollmentRefused(f"the stand refused the enrollment (HTTP {error.status}): {error.message}") from None
    token = issued["token"]
    if outcome is not None and isinstance(issued.get("host_id"), str):
        outcome["host_id"] = issued["host_id"]
        outcome["catalogue_models"] = len(host_mode.parse_catalogue(issued.get("catalogue", []))[0])
    try:
        store_runner_token(path, cfg.token_env, token, drop=(ENROLLMENT_SECRET_ENV,))
    except OSError as error:
        raise ConfigError(f"the stand issued the runner token but it could not be stored in {env_file} "
                          f"({type(error).__name__}); run the installer again within 15 minutes") from None
    return token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent.py", description="Unattended pull agent for the PDF Analysis executor channel.")
    parser.add_argument("--config", required=True, help="path to the TOML configuration (see agent.example.toml)")
    parser.add_argument("--origin", help="override [runner] origin")
    parser.add_argument("--max-tasks", type=int, default=0, help="stop after claiming this many tasks (0 = run until stopped)")
    parser.add_argument("--env-file", help=f"the environment file the runner token is stored in; with {ENROLLMENT_SECRET_ENV} in the "
                                           "environment the secret is exchanged for a token first (install.sh does this as root)")
    parser.add_argument("--enroll-only", action="store_true",
                        help=f"exchange {ENROLLMENT_SECRET_ENV} for a runner token, store it in --env-file and exit")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    # The one-time secret leaves this process's environment at once: the answer command and everything it
    # starts inherit the environment, and none of them has any use for it.
    grant = os.environ.pop(ENROLLMENT_SECRET_ENV, "")
    enrolled: dict = {}
    try:
        cfg = load_config(args.config)
        if args.origin:
            cfg.origin = args.origin
        if args.enroll_only and not grant:
            raise ConfigError(f"environment variable {ENROLLMENT_SECRET_ENV} is not set (it holds the one-time enrollment secret)")
        if args.enroll_only and not args.env_file:
            raise ConfigError("--enroll-only needs --env-file PATH")
        if grant:
            token = enroll_with_grant(cfg, grant, args.env_file, enrolled)
        else:
            token = os.environ.get(cfg.token_env, "")
    except EnrollmentRefused as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_AUTH
    except EnrollmentUnavailable as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_TEMPFAIL
    except (ConfigError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_CONFIG
    if args.enroll_only:
        if "host_id" in enrolled:
            print(f"enrolled: host {enrolled['host_id']}, the runner token is stored in {args.env_file}; "
                  "the enrollment secret is spent")
        else:
            print(f"enrolled: the runner token is stored in {args.env_file}; the enrollment secret is spent")
        return EXIT_OK
    try:
        if not token:
            raise ConfigError(f"environment variable {cfg.token_env} is not set (it holds the runner token)")
        api_key = os.environ.get(cfg.endpoint_api_key_env, "") if cfg.mode == "endpoint" and cfg.endpoint_api_key_env else ""
        client = RunnerClient(cfg.origin, token, allow_insecure_http=cfg.allow_insecure_http, ca_file=cfg.ca_file)
    except (ConfigError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_CONFIG
    if args.max_tasks < 0:
        print("error: --max-tasks must be 0 or more", file=sys.stderr)
        return EXIT_CONFIG
    if cfg.mode == "host":
        agent = HostAgent(cfg, client, sys.stderr)
        HostHealthReporter(cfg, client, agent.instance_id, agent.log, agent.stop, agent.runtime).start()
        agent.runtime.start_probes()
    else:
        agent = Agent(cfg, client, api_key, sys.stderr)
        HealthReporter(cfg, client, agent.instance_id, agent.log, agent.stop).start()

    def on_signal(signum: int, _frame: Any) -> None:
        agent.log(f"signal {signum}: stopping after the tasks in flight")
        agent.stop.set()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    try:
        return agent.run(args.max_tasks or None)
    finally:
        agent.stop.set()  # the health reporter ends with the claim loop


if __name__ == "__main__":
    sys.exit(main())
