#!/usr/bin/env python3
"""Unattended pull agent for the PDF Analysis executor channel (RUNNER_API.md).

Claims tasks from the stand over HTTPS, answers each with a local command or a local
OpenAI-compatible model, and submits the answer. It works from behind NAT: the stand never
connects to it. Standard library only (Python 3.11+, ``tomllib``).

    PDF_ANALYSIS_RUNNER_TOKEN=... python3 agent.py --config agent.toml [--max-tasks N]

Exit codes: 0 normal stop (signal or ``--max-tasks`` reached), 2 configuration error,
3 the stand rejected the token (401: wrong, expired or revoked; restarting will not help).

Rules kept here:

* the token (and an endpoint key) come from environment variables named in the config, never
  from the command line or the config file, and are removed from every log line;
* the task payload (document text) is never logged and is written to disk only if the
  configured command does so;
* a model other than the one declared in the config is never claimed to have answered: a task
  that pins another model is failed with ``model_mismatch`` before any work starts;
* a schema-invalid answer is failed with a typed reason, never retried silently.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from runner_client import (
    Backoff,
    RunnerAuthError,
    RunnerClient,
    RunnerConflict,
    RunnerError,
    RunnerNotFound,
    RunnerRejected,
    RunnerThrottled,
    RunnerUnavailable,
    throttle_delay,
)

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_AUTH = 3

DEFAULT_TOKEN_ENV = "PDF_ANALYSIS_RUNNER_TOKEN"
DEADLINE_MARGIN_SECONDS = 5.0
MAX_ANSWER_BYTES = 8 << 20
SUBMIT_RETRY_BUDGET_SECONDS = 120.0
FORBIDDEN_KEY_EXACT = {"token", "secret", "password", "api_key", "apikey", "key", "bearer", "authorization"}
FORBIDDEN_KEY_SUFFIXES = ("_token", "_secret", "_password", "_key")

KNOWN_KEYS = {
    "runner": {"origin", "token_env", "wait_seconds", "ca_file", "allow_insecure_http", "concurrency", "drain_seconds", "extend_floor_seconds", "backoff_min_seconds", "backoff_max_seconds"},
    "model": {"declared"},
    "executor": {"mode"},
    "command": {"argv", "timeout_seconds", "cwd"},
    "endpoint": {"url", "model", "api_key_env", "timeout_seconds", "response_format", "temperature", "max_tokens"},
}


class ConfigError(Exception):
    pass


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
    endpoint_url: str = ""
    endpoint_model: str = ""
    endpoint_api_key_env: str = ""
    endpoint_timeout: float = 540.0
    response_format: str = "none"
    temperature: float = 0.0
    max_tokens: int = 0


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
    cfg.endpoint_url = str(endpoint.get("url", ""))
    cfg.endpoint_model = str(endpoint.get("model", ""))
    cfg.endpoint_api_key_env = str(endpoint.get("api_key_env", ""))
    cfg.endpoint_timeout = float(endpoint.get("timeout_seconds", cfg.endpoint_timeout))
    cfg.response_format = str(endpoint.get("response_format", cfg.response_format))
    cfg.temperature = float(endpoint.get("temperature", cfg.temperature))
    cfg.max_tokens = int(endpoint.get("max_tokens", cfg.max_tokens))
    validate_config(cfg)
    return cfg


def validate_config(cfg: Config) -> None:
    if not cfg.origin:
        raise ConfigError("[runner] origin is required")
    if not isinstance(cfg.wait_seconds, int) or isinstance(cfg.wait_seconds, bool) or not 0 <= cfg.wait_seconds <= 25:
        raise ConfigError("[runner] wait_seconds must be an integer in 0..25")
    if not isinstance(cfg.concurrency, int) or isinstance(cfg.concurrency, bool) or not 1 <= cfg.concurrency <= 8:
        raise ConfigError("[runner] concurrency must be an integer in 1..8")
    if not cfg.declared_model:
        raise ConfigError("[model] declared is required: the exact pinned model id this agent answers as")
    if cfg.mode not in ("command", "endpoint"):
        raise ConfigError('[executor] mode must be "command" or "endpoint"')
    if cfg.mode == "command":
        argv = cfg.command_argv
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
            raise ConfigError("[command] argv must be a non-empty list of strings")
    else:
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


class Interrupted(Exception):
    """The work was abandoned because the claim was lost, the deadline passed or the agent is stopping."""


def run_command(cfg: Config, task: dict, budget: float, should_stop: Any) -> Answer:
    """Task JSON to the command's stdin; its stdout is the answer document."""
    payload = json.dumps(task, ensure_ascii=False).encode("utf-8")
    try:
        process = subprocess.Popen(
            cfg.command_argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=cfg.command_cwd,
            start_new_session=True,  # so that only this command's own process group is ever signalled
        )
    except OSError as error:
        raise ExecutorFailure("command_failed", f"cannot start: {type(error).__name__}") from None
    deadline = time.monotonic() + min(cfg.command_timeout, budget)
    stdout: bytes = b""
    first = True
    try:
        while True:
            try:
                stdout, _ = process.communicate(input=payload if first else None, timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                first = False
            except (BrokenPipeError, OSError):
                # the command closed its stdin early; collect what it produced
                first = False
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
    if process.returncode != 0:
        raise ExecutorFailure("command_failed", f"exit status {process.returncode}")
    if len(stdout) > MAX_ANSWER_BYTES:
        raise ExecutorFailure("command_bad_output", "stdout is larger than 8 MiB")
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


def run_endpoint(cfg: Config, task: dict, budget: float, should_stop: Any, api_key: str) -> Answer:
    """One non-streaming chat completion against a local OpenAI-compatible endpoint."""
    body: dict[str, Any] = {
        "model": cfg.endpoint_model,
        "messages": [{"role": "system", "content": task["system"]}, {"role": "user", "content": task["user_text"]}],
        "temperature": cfg.temperature,
        "stream": False,
    }
    if cfg.max_tokens > 0:
        body["max_tokens"] = cfg.max_tokens
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
            raw = response.read(MAX_ANSWER_BYTES + 1)
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
    def __init__(self, cfg: Config, client: RunnerClient, api_key: str, err: Any) -> None:
        self.cfg = cfg
        self.client = client
        self.api_key = api_key
        self._err = err
        self.stop = threading.Event()
        self.abort = threading.Event()
        self.auth_failed = threading.Event()
        self._workers: list[threading.Thread] = []
        self._log_lock = threading.Lock()

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
        slots = threading.Semaphore(self.cfg.concurrency)
        backoff = Backoff(self.cfg.backoff_min_seconds, self.cfg.backoff_max_seconds)
        claimed = 0
        self.log(
            f"started: origin={self.client.origin} mode={self.cfg.mode} declared_model={self.cfg.declared_model} "
            f"concurrency={self.cfg.concurrency} max_tasks={max_tasks if max_tasks else 'unlimited'}"
        )
        while not self.stop.is_set() and not self.auth_failed.is_set() and (not max_tasks or claimed < max_tasks):
            if not slots.acquire(timeout=0.5):
                continue
            try:
                task = self.client.claim(self.cfg.wait_seconds)
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
            claimed += 1
            worker = threading.Thread(target=self._worker, args=(task, slots), name=task["task_id"], daemon=True)
            self._workers.append(worker)
            worker.start()
        return self._finish()

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
                    answer = run_command(self.cfg, task, budget, should_stop)
                else:
                    answer = run_endpoint(self.cfg, task, budget, should_stop, self.api_key)
            except Interrupted as stop:
                self._interrupted(task_id, str(stop))
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
            self._submit(task_id, answer)
        except Exception as error:  # noqa: BLE001 - one task must not take the agent down
            self.log(f"{task_id}: internal error {type(error).__name__}")
            self._fail(task_id, f"agent_error: {type(error).__name__}")
        finally:
            done.set()
            slots.release()

    def _interrupted(self, task_id: str, reason: str) -> None:
        if reason == "deadline":
            self.log(f"{task_id}: deadline reached, abandoning")
            self._fail(task_id, "deadline_exceeded: the answer window closed")
        elif reason == "agent_shutdown":
            self._fail(task_id, "agent_shutdown: the agent was stopped before the answer was ready")
        else:
            self.log(f"{task_id}: claim lost, abandoning (nothing is submitted)")

    def _extend_loop(self, task: dict, done: threading.Event, state: dict) -> None:
        task_id = task["task_id"]
        try:
            interval = self._interval(task["claim_expires_at"])
        except ValueError:
            interval = 10.0
        while not done.wait(interval):
            if self.client.seconds_until(task["deadline_at"]) <= 0:
                state["lost"] = "deadline"
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

    def _submit(self, task_id: str, answer: Answer) -> None:
        started = time.monotonic()
        backoff = Backoff(self.cfg.backoff_min_seconds, self.cfg.backoff_max_seconds)
        while True:
            try:
                reply = self.client.answer(task_id, answer.output_text, self.cfg.declared_model, answer.input_tokens, answer.output_tokens)
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
                if time.monotonic() - started + pause > SUBMIT_RETRY_BUDGET_SECONDS or self.abort.is_set():
                    self.log(f"{task_id}: could not deliver the answer ({error.message}); the claim will lapse")
                    return
                self.log(f"{task_id}: submit will retry in {pause:.1f}s ({error.message})")
                time.sleep(pause)

    def _fail(self, task_id: str, reason: str) -> None:
        try:
            self.client.fail(task_id, reason)
            self.log(f"{task_id}: failed ({reason.split(':')[0]})")
        except RunnerAuthError:
            self.auth_failed.set()
            self.stop.set()
        except RunnerError as error:
            self.log(f"{task_id}: could not report the failure ({error.message})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent.py", description="Unattended pull agent for the PDF Analysis executor channel.")
    parser.add_argument("--config", required=True, help="path to the TOML configuration (see agent.example.toml)")
    parser.add_argument("--origin", help="override [runner] origin")
    parser.add_argument("--max-tasks", type=int, default=0, help="stop after claiming this many tasks (0 = run until stopped)")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
        if args.origin:
            cfg.origin = args.origin
        token = os.environ.get(cfg.token_env, "")
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
    agent = Agent(cfg, client, api_key, sys.stderr)

    def on_signal(signum: int, _frame: Any) -> None:
        agent.log(f"signal {signum}: stopping after the tasks in flight")
        agent.stop.set()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    return agent.run(args.max_tasks or None)


if __name__ == "__main__":
    sys.exit(main())
