"""`PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01`: the operator-run model identity probe (`R-146e`, `AD-13`).

For each model pinned in ``docs/program/P02_LOCK.json`` it sends **one** minimal chat-completions
request through the adapter the product uses (``auditmanager.executors.http_adapter``, flavour
``openai_chat``, the pinned destination layer included) and writes one report block per model:
``requested_slug:``, ``reported_model:`` (the ``model`` string the gateway answered with), the
``R-133`` verdict, usage and cost. The verdict is the product's own comparison
(``auditmanager.executors.identity.assess_identity``): exact string, no prefix, no case folding,
no alias list (``AD-13``). The tool decides nothing else: it **never writes the lock**. The
integrator writes ``P02_LOCK.json`` from the live run's report, and only if the strings and the
rates match.

Run it from the repository root, with the credential in the process environment only::

    PYTHONPATH=src python3 -m scripts.model_probe.probe --confirm-paid \\
        --slug claude-opus-5=anthropic/claude-opus-5 --slug claude-sonnet-5=anthropic/claude-sonnet-5 \\
        --slug gpt-6-sol=<slug> --report /path/outside/the/repo/probe.txt

What stands between this tool and money (each is a refusal *before the first call*, exit 2):

* ``--confirm-paid`` is mandatory; nothing is read from the environment without it;
* ``PROXY_LLM_BASE_URL`` and ``PROXY_LLM_TOKEN`` must be in the process environment. No file is
  read for a credential: the only file this tool reads is the lock;
* ``--max-usd`` is the total ceiling (default 0.50, refused above 5.00, the ``R-29`` wave stop);
* every probed model has an explicit, non-placeholder ``--slug`` (the tool never guesses a
  gateway name) and the report path does not exist yet (it is created exclusively, mode 0600).

Cost control: before each call the worst case of that call (its prompt and ``max_tokens`` at the
lock's rates) is added to what is already counted; a call that would pass the ceiling is not made.
After each call the cost the gateway reported (else the lock's rate over the reported tokens, else
the worst case) is counted; a total over the ceiling stops the run. Either stop is exit 3. There
is no retry: a model is called at most once.

Exit status: 0 every probed model answered with exactly the requested name; 1 a model answered
with another name, no usable name, or its call failed; 2 refused before any call; 3 stopped at
the ceiling; 5 the credential value appeared in what was about to be written (it was redacted).
The report holds no answer text and no credential: the credential is scanned for in everything
that is written or printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Final, TextIO
from urllib.parse import urlsplit

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.analysis.text.lock import ModelPin, load_provider_lock
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.http_adapter import build_http_adapter
from auditmanager.executors.identity import MODEL_NAME, PROMPT, assess_identity, is_placeholder, rate_check
from auditmanager.shared.errors import DomainError

__all__ = ["BASE_URL_ENV", "TOKEN_ENV", "main", "product_adapter"]

#: The names of the process environment the product reads its OpenRouter connection from
#: (`bootstrap/settings.py`; a test holds these equal to its constants).
BASE_URL_ENV: Final[str] = "PROXY_LLM_BASE_URL"
TOKEN_ENV: Final[str] = "PROXY_LLM_TOKEN"

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
LOCK_PATH: Final[Path] = REPO_ROOT / "docs/program/P02_LOCK.json"

DEFAULT_MAX_USD: Final[Decimal] = Decimal("0.50")
#: The `R-29` stop: spending above roughly this in a wave stops for the owner. Not overridable.
HARD_CAP_USD: Final[Decimal] = Decimal("5.00")
MAX_OUTPUT_TOKENS: Final[int] = 16
#: A generous upper bound on the prompt's tokens (it is ~12), for the worst case of one call.
INPUT_TOKEN_BOUND: Final[int] = 256
CALL_TIMEOUT_SECONDS: Final[int] = 60
REDACTED: Final[str] = "[credential-redacted]"

EXIT_OK, EXIT_NOT_MATCHED, EXIT_REFUSED, EXIT_CEILING, EXIT_LEAK = 0, 1, 2, 3, 5

_FINISH_REASON = re.compile(r"[A-Za-z_]{1,32}")
_ONE_USD_MICRO = Decimal(1_000_000)


class Refused(Exception):
    """A refusal before any call. The message is a fixed phrase: no URL, no credential."""


AdapterFactory = Callable[..., Any]


def product_adapter(*, base_url: str, token: str, slug: str) -> Any:
    """The adapter one ``openai_chat`` connection revision gets in the product, for ``slug``."""
    return build_http_adapter(
        api_flavour="openai_chat", base_url=base_url, api_key=token, gateway_model=slug,
        timeout_seconds=CALL_TIMEOUT_SECONDS, transport="direct", policy=DestinationPolicy(),
    )


# -- the transport seam: what the gateway answered, kept apart from what the adapter returns ------

class _Capture:
    """The last 200 answer body that came back through the adapter's opener (never an error body:
    those can carry the prompt or a credential)."""

    def __init__(self) -> None:
        self.body: bytes | None = None
        self._chunks: list[bytes] = []

    def reset(self) -> None:
        self.body, self._chunks = None, []

    def document(self) -> Mapping[str, Any] | None:
        if self.body is None:
            return None
        try:
            document = json.loads(self.body)
        except (ValueError, UnicodeError):
            return None
        return document if isinstance(document, Mapping) else None


class _TeeResponse:
    def __init__(self, inner: Any, capture: _Capture) -> None:
        self._inner = inner
        self._capture = capture

    def __enter__(self) -> _TeeResponse:
        self._inner.__enter__()
        return self

    def __exit__(self, *exc: Any) -> Any:
        if getattr(self._inner, "status", None) == 200 and self._capture._chunks:
            self._capture.body = b"".join(self._capture._chunks)
        return self._inner.__exit__(*exc)

    def read(self, *args: Any) -> bytes:
        data = self._inner.read(*args)
        if getattr(self._inner, "status", None) == 200:
            self._capture._chunks.append(data)
        return data

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _Tee:
    def __init__(self, inner: Callable[..., Any], capture: _Capture) -> None:
        self._inner = inner
        self._capture = capture

    def __call__(self, request: Any, timeout: float | None = None) -> _TeeResponse:
        return _TeeResponse(self._inner(request, timeout=timeout), self._capture)


def _scrubbing_factory(token: str, previous: Callable[..., logging.LogRecord]) -> Callable[..., logging.LogRecord]:
    """A log-record factory that removes the credential from every record made during the run.
    The product adapter logs the reply's ``model`` string on an identity mismatch, and a hostile
    gateway could put the credential there; nothing the adapter logs may carry it to a console."""
    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous(*args, **kwargs)
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - a record that cannot be formatted is dropped to its text
            message = str(record.msg)
        if token in message:
            record.msg, record.args = message.replace(token, REDACTED), None
        return record
    return factory


def _install_tee(adapter: Any, capture: _Capture) -> None:
    """Wrap the adapter's opener so the probe sees the reply's own ``model``, which the adapter's
    typed identity refusal does not carry. Fail closed if the adapter has no such seam."""
    inner = getattr(adapter, "_opener", None)
    if not callable(inner):
        raise Refused("the product adapter has no opener seam this tool can observe")
    adapter._opener = _Tee(inner, capture)


# -- results ---------------------------------------------------------------------------------------

@dataclass
class ModelResult:
    pin_id: str
    requested_slug: str
    verdict: str = "not_called"  # match | mismatch | no_verdict | not_called
    reason: str = "not_called"
    adapter_outcome: str = "not_called"
    reported_model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None
    reported_cost: Decimal | None = None
    expected_cost: Decimal | None = None
    rate_check: str = "not_reported"
    counted_cost: Decimal = Decimal(0)
    cost_basis: str = "none"


@dataclass
class _Planned:
    pin: ModelPin
    slug: str
    adapter: Any
    capture: _Capture
    worst_case: Decimal


def _usd(value: Decimal | None) -> str:
    return "not_reported" if value is None else format(value.normalize(), "f")


def worst_case_usd(pin: ModelPin) -> Decimal:
    """The most one call can cost: the prompt bound and ``max_tokens`` at the lock's rates."""
    return (
        Decimal(INPUT_TOKEN_BOUND) * Decimal(str(pin.input_per_mtok_usd))
        + Decimal(MAX_OUTPUT_TOKENS) * Decimal(str(pin.output_per_mtok_usd))
    ) / _ONE_USD_MICRO


def _count(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() and number >= 0 else None


def _display_reported(reported: Any) -> str | None:
    """What goes after ``reported_model:``. A plausible name is printed as it came; a string that
    is not one is JSON-quoted (control characters escaped) and bounded."""
    if reported is None:
        return None
    if isinstance(reported, str):
        if MODEL_NAME.fullmatch(reported) is not None:
            return reported
        return "unusable " + json.dumps(reported[:100])
    return "unusable (not text)"


def assess(
    result: ModelResult, planned: _Planned, document: Mapping[str, Any] | None,
    outcome: str, dispatch_class: str | None,
) -> None:
    """Fill ``result`` from the adapter's outcome and the gateway's own answer body."""
    result.adapter_outcome = outcome
    pin = planned.pin
    if document is None:
        result.verdict, result.reason = "no_verdict", "no_answer_body"
        paid_possible = dispatch_class not in ("not_sent", "definite_refusal", "rate_limited")
        if paid_possible:
            result.counted_cost, result.cost_basis = planned.worst_case, "bound"
        return
    reported = document.get("model")
    ident, name = assess_identity(reported, planned.slug)
    result.reported_model = _display_reported(reported)
    if ident == "ok":
        result.verdict, result.reason = "match", "exact"
    else:
        result.verdict = "mismatch"
        result.reason = "no_usable_model_named" if name is None else "other_model"
    usage = document.get("usage")
    usage = usage if isinstance(usage, Mapping) else {}
    result.input_tokens = _count(usage.get("prompt_tokens"))
    result.output_tokens = _count(usage.get("completion_tokens"))
    choices = document.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else None
    finish = choice.get("finish_reason") if isinstance(choice, Mapping) else None
    result.finish_reason = finish if isinstance(finish, str) and _FINISH_REASON.fullmatch(finish) else None
    result.reported_cost = _decimal(usage.get("cost"))
    result.rate_check = rate_check(
        usage, billing="metered", input_per_mtok_usd=pin.input_per_mtok_usd,
        output_per_mtok_usd=pin.output_per_mtok_usd,
    )
    if result.input_tokens is not None and result.output_tokens is not None:
        result.expected_cost = (
            Decimal(result.input_tokens) * Decimal(str(pin.input_per_mtok_usd))
            + Decimal(result.output_tokens) * Decimal(str(pin.output_per_mtok_usd))
        ) / _ONE_USD_MICRO
    if result.reported_cost is not None:
        result.counted_cost, result.cost_basis = result.reported_cost, "reported"
    elif result.expected_cost is not None:
        result.counted_cost, result.cost_basis = result.expected_cost, "estimated"
    else:
        result.counted_cost, result.cost_basis = planned.worst_case, "bound"


def call_once(planned: _Planned, run_id: str) -> ModelResult:
    """One call, no retry. Nothing here raises: every failure is a verdict in the result."""
    result = ModelResult(pin_id=planned.pin.model_id, requested_slug=planned.slug)
    request = ModelRequest(
        model_id=planned.slug,
        body={"messages": [{"role": "user", "content": PROMPT}], "max_tokens": MAX_OUTPUT_TOKENS},
        idempotency_scope=run_id,
    )
    planned.capture.reset()
    outcome, dispatch_class = "answered", None
    try:
        planned.adapter.complete(request)
    except ProxyDispatchError as error:
        outcome = getattr(error.code, "value", str(error.code))
        dispatch_class = error.dispatch_class
    except DomainError as error:
        outcome, dispatch_class = getattr(error.code, "value", str(error.code)), "outcome_unknown"
    except Exception as error:  # noqa: BLE001 - reported by type name only: no message can leak
        outcome, dispatch_class = "unexpected_" + type(error).__name__, "outcome_unknown"
    assess(result, planned, planned.capture.document(), outcome, dispatch_class)
    return result


# -- the run ---------------------------------------------------------------------------------------

@dataclass
class RunOutcome:
    results: list[ModelResult] = field(default_factory=list)
    spent: Decimal = Decimal(0)
    stopped: str = "none"


def run_calls(plan: Sequence[_Planned], ceiling: Decimal, run_id: str,
              on_progress: Callable[[RunOutcome], None]) -> RunOutcome:
    outcome = RunOutcome()
    for index, planned in enumerate(plan):
        if outcome.spent + planned.worst_case > ceiling:
            outcome.stopped = "projected_over_ceiling"
        else:
            result = call_once(planned, run_id)
            outcome.results.append(result)
            outcome.spent += result.counted_cost
            on_progress(outcome)
            if outcome.spent > ceiling:
                outcome.stopped = "ceiling_exceeded"
        if outcome.stopped != "none":
            for rest in plan[len(outcome.results):]:
                outcome.results.append(ModelResult(pin_id=rest.pin.model_id, requested_slug=rest.slug))
            break
    return outcome


def exit_code(outcome: RunOutcome, leaked: bool) -> int:
    if leaked:
        return EXIT_LEAK
    if outcome.stopped != "none":
        return EXIT_CEILING
    if all(result.verdict == "match" for result in outcome.results):
        return EXIT_OK
    return EXIT_NOT_MATCHED


def lock_candidate(outcome: RunOutcome, pinned: int, leaked: bool) -> bool:
    """Every model the lock pins was probed, matched exactly and had its reported cost within the
    rate tolerance. The integrator's condition for writing the lock; the tool writes nothing."""
    return (
        not leaked and outcome.stopped == "none" and len(outcome.results) == pinned
        and all(r.verdict == "match" and r.rate_check == "checked" for r in outcome.results)
    )


def render(
    outcome: RunOutcome, *, run_id: str, started: str, host: str, lock_sha: str, ceiling: Decimal,
    pinned: int, leaked: bool, final: bool,
) -> str:
    lines = [
        "# model identity probe report (PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01)",
        f"run_id: {run_id}",
        f"started_at_utc: {started}",
        f"gateway_host: {host}",
        f"lock_sha256: {lock_sha}",
        f"prompt_sha256: {hashlib.sha256(PROMPT.encode('utf-8')).hexdigest()}",
        f"max_output_tokens: {MAX_OUTPUT_TOKENS}",
        f"ceiling_usd: {_usd(ceiling)}",
        "comparison: exact string, no alias list (AD-13, R-133)",
        "",
    ]
    for result in outcome.results:
        lines += [
            f"--- model {result.pin_id} ---",
            f"pin_id: {result.pin_id}",
            f"requested_slug: {result.requested_slug}",
            f"reported_model: {result.reported_model or 'none'}",
            f"verdict: {result.verdict}",
            f"verdict_reason: {result.reason}",
            f"adapter_outcome: {result.adapter_outcome}",
            f"input_tokens: {'not_reported' if result.input_tokens is None else result.input_tokens}",
            f"output_tokens: {'not_reported' if result.output_tokens is None else result.output_tokens}",
            f"finish_reason: {result.finish_reason or 'not_reported'}",
            f"reported_cost_usd: {_usd(result.reported_cost)}",
            f"expected_cost_usd_at_lock_rates: {_usd(result.expected_cost)}",
            f"rate_check: {result.rate_check}",
            f"counted_cost_usd: {_usd(result.counted_cost)}",
            f"cost_basis: {result.cost_basis}",
            "",
        ]
    code = exit_code(outcome, leaked)
    called = sum(1 for r in outcome.results if r.adapter_outcome != "not_called")
    lines += [
        "--- summary ---",
        f"models_pinned_in_lock: {pinned}",
        f"models_probed: {len(outcome.results)}",
        f"models_called: {called}",
        f"spent_usd_counted: {_usd(outcome.spent)}",
        f"stopped: {outcome.stopped}",
        f"all_identities_match: {'yes' if all(r.verdict == 'match' for r in outcome.results) else 'no'}",
        f"lock_candidate: {'yes' if lock_candidate(outcome, pinned, leaked) else 'no'}",
        f"credential_guard: {'redacted' if leaked else 'clean'}",
        f"complete: {'yes' if final else 'no (run in progress or interrupted)'}",
        f"exit_code: {code}",
        "P02_LOCK.json: not written (the integrator writes it from this report)",
    ]
    return "\n".join(lines) + "\n"


# -- the command -----------------------------------------------------------------------------------

def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="probe", description=__doc__.split("\n\n")[0])
    parser.add_argument("--confirm-paid", action="store_true",
                        help="required: every probed model is one paid call")
    parser.add_argument("--max-usd", default=str(DEFAULT_MAX_USD),
                        help=f"total ceiling in USD (default {DEFAULT_MAX_USD}, at most {HARD_CAP_USD})")
    parser.add_argument("--slug", action="append", default=[], metavar="PIN=SLUG",
                        help="the gateway name to request for a pinned model id; one per probed model")
    parser.add_argument("--only", action="append", default=[], metavar="PIN",
                        help="probe only this pinned model id (repeatable); the default is every pin")
    parser.add_argument("--report", type=Path, default=None,
                        help="report path; must not exist; default: a new file in the temp directory")
    return parser.parse_args(list(argv) if argv is not None else None)


def _ceiling(raw: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise Refused("--max-usd is not a number") from None
    if not value.is_finite() or value <= 0:
        raise Refused("--max-usd must be a positive number")
    if value > HARD_CAP_USD:
        raise Refused(f"--max-usd is above the {HARD_CAP_USD} USD wave stop (R-29)")
    return value


def _slugs(pairs: Sequence[str], pins: Sequence[ModelPin], only: Sequence[str]) -> list[tuple[ModelPin, str]]:
    by_id = {pin.model_id: pin for pin in pins}
    chosen: dict[str, str] = {}
    for pair in pairs:
        pin_id, separator, slug = pair.partition("=")
        if not separator or pin_id not in by_id or pin_id in chosen:
            raise Refused("--slug must be PIN=SLUG for a pinned model id, once per model")
        if MODEL_NAME.fullmatch(slug) is None or is_placeholder(slug):
            raise Refused("a --slug is not a model name (a gateway stub or a malformed name)")
        chosen[pin_id] = slug
    if any(pin_id not in by_id for pin_id in only):
        raise Refused("--only names a model the lock does not pin")
    selected = [pin for pin in pins if not only or pin.model_id in only]
    if any(pin.model_id not in chosen for pin in selected):
        raise Refused("every probed model needs an explicit --slug; the tool does not guess a gateway name")
    if any(pin_id not in {pin.model_id for pin in selected} for pin_id in chosen):
        raise Refused("a --slug names a model that is not probed")
    return [(pin, chosen[pin.model_id]) for pin in selected]


def _credential(environ: Mapping[str, str]) -> tuple[str, str]:
    base_url, token = environ.get(BASE_URL_ENV, "").strip(), environ.get(TOKEN_ENV, "")
    if not base_url or not token.strip():
        raise Refused(f"{BASE_URL_ENV} and {TOKEN_ENV} must be in the process environment")
    return base_url, token


def default_report_path(run_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"model-probe-{run_id}.txt"


def _open_report(path: Path) -> int:
    """Create the report exclusively (never over an existing file, the lock included), 0600."""
    try:
        return os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise Refused("the report path exists; the tool never overwrites a file") from None
    except OSError:
        raise Refused("the report path cannot be created") from None


def _write(descriptor: int, text: str) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    os.ftruncate(descriptor, 0)
    os.write(descriptor, text.encode("utf-8"))
    os.fsync(descriptor)


def main(
    argv: Sequence[str] | None = None, *, environ: Mapping[str, str] | None = None,
    adapter_factory: AdapterFactory = product_adapter, out: TextIO | None = None,
    err: TextIO | None = None, run_id: str | None = None, lock_path: Path | None = None,
) -> int:
    out, err = out or sys.stdout, err or sys.stderr
    args = _parse(argv)
    run_id = run_id or uuid.uuid4().hex
    lock_file = lock_path or LOCK_PATH
    try:
        # Order matters: the confirmation is checked before the environment is touched.
        if not args.confirm_paid:
            raise Refused("--confirm-paid is required (every probed model is a paid call)")
        ceiling = _ceiling(args.max_usd)
        base_url, token = _credential(os.environ if environ is None else environ)
        try:
            lock_bytes = lock_file.read_bytes()
            lock = load_provider_lock(lock_file)
        except (OSError, ValueError, KeyError, DomainError):
            raise Refused("the lock could not be read") from None
        pins = list(lock.models.values())
        chosen = _slugs(args.slug, pins, args.only)
        plan: list[_Planned] = []
        for pin, slug in chosen:
            capture = _Capture()
            try:
                adapter = adapter_factory(base_url=base_url, token=token, slug=slug)
            except DomainError:
                raise Refused("the connection settings are not valid for the product adapter") from None
            _install_tee(adapter, capture)
            plan.append(_Planned(pin, slug, adapter, capture, worst_case_usd(pin)))
        report_path = args.report or default_report_path(run_id)
        descriptor = _open_report(report_path)
    except Refused as refusal:
        print(f"model probe refused before any call: {refusal}", file=err)
        return EXIT_REFUSED

    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    host = re.sub(r"[^A-Za-z0-9.\-:\[\]]", "?", _host_of(base_url))
    lock_sha = hashlib.sha256(lock_bytes).hexdigest()
    pinned = len(pins)

    def text_for(outcome: RunOutcome, final: bool) -> tuple[str, bool]:
        draft = render(outcome, run_id=run_id, started=started, host=host, lock_sha=lock_sha,
                       ceiling=ceiling, pinned=pinned, leaked=False, final=final)
        leaked = token in draft
        text = render(outcome, run_id=run_id, started=started, host=host, lock_sha=lock_sha,
                      ceiling=ceiling, pinned=pinned, leaked=leaked, final=final)
        return text.replace(token, REDACTED), leaked

    def progress(outcome: RunOutcome) -> None:
        assert descriptor is not None
        _write(descriptor, text_for(outcome, False)[0])

    previous_factory = logging.getLogRecordFactory()
    logging.setLogRecordFactory(_scrubbing_factory(token, previous_factory))
    try:
        outcome = run_calls(plan, ceiling, run_id, progress)
        text, leaked = text_for(outcome, True)
        _write(descriptor, text)
    finally:
        logging.setLogRecordFactory(previous_factory)
        os.close(descriptor)
    out.write(text)
    print(f"report_path: {report_path}", file=out)
    return exit_code(outcome, leaked)


def _host_of(base_url: str) -> str:
    try:
        return urlsplit(base_url).hostname or "unknown"
    except ValueError:
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
