"""Parse what ``claude -p`` prints, and read the model it reports (`R-133`, plan 5, T-7).

The ``claude_code_headless`` profile runs ``claude -p --output-format json`` on the remote machine
(``tools/executor-runner/ssh-forced-command.sh``) and the stand reads that document from stdout.
This module turns it into ``(result_text, reported_model)``. It never infers a model: the identity
rule is fail-closed, so a document that does not name exactly one model is an error, not a guess.

Where the model comes from
--------------------------

* The ``--output-format json`` result document carries a **per-model breakdown** of the run, the
  key ``modelUsage`` (the TypeScript SDK spelling; the Python SDK's ``model_usage`` is accepted too),
  a map ``{model id: {inputTokens, outputTokens, costUSD, ...}}``. The model is that map's key:

  * exactly one key -> that is the reported model;
  * no key, or several (a run that also used a second, auxiliary model) -> ``ModelIdentityError``.
    The caller treats it as ``model_identity_mismatch`` and publishes nothing from the answer.
* A list of messages (``--output-format stream-json``, or the same messages already decoded) is also
  accepted. The ``system`` message with ``subtype == "init"`` carries ``model``. If the result
  message has a ``modelUsage`` map as well, the two must agree; a disagreement is an identity error.

**EXEC-SSH-01 Work 0 must confirm the key against the installed version.** The Claude Code
documentation read on 2026-10-22 does not spell out the JSON key (it mentions a per-model cost
breakdown), and no ``claude`` binary was available when this was written. Before the stand
trusts this parser, capture ``claude --version`` and
``claude -p "hi" --output-format json | python3 -c 'import json,sys; print(sorted(json.load(sys.stdin)))'``
from the installed version, keep the output in the report, and adjust ``_MODEL_USAGE_KEYS`` (or
switch the forced command to ``--output-format stream-json --verbose`` and use the ``system/init``
route) to match. Never infer the model from anything else.

The module has no dependency on the rest of the application.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, NamedTuple

__all__ = [
    "ClaudeOutputError",
    "ClaudeResult",
    "ModelIdentityError",
    "parse_claude_output",
]

#: Keys under which the per-model breakdown may appear, in order of preference.
_MODEL_USAGE_KEYS = ("modelUsage", "model_usage")


class ClaudeOutputError(ValueError):
    """The output is not a usable ``claude -p`` result document."""


class ModelIdentityError(ClaudeOutputError):
    """The document does not name exactly one model. ``candidates`` lists what it did name."""

    def __init__(self, message: str, candidates: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.candidates = candidates


class ClaudeResult(NamedTuple):
    result_text: str
    reported_model: str


def parse_claude_output(document: bytes | str | Mapping[str, Any] | list[Any]) -> ClaudeResult:
    """``(result_text, reported_model)`` from a result document or a list of stream messages.

    ``document`` is the stdout bytes/text (one JSON document, or JSON lines of stream-json), an
    already decoded result object, or an already decoded list of messages. Raises
    ``ClaudeOutputError`` for anything that is not a successful result, and
    ``ModelIdentityError`` when the model cannot be named exactly.
    """

    messages = _as_messages(document)
    results = [m for m in messages if m.get("type") == "result"]
    if len(messages) == 1 and not results and "result" in messages[0]:
        results = messages  # a bare result object without "type"
    if len(results) != 1:
        raise ClaudeOutputError(f"expected exactly one result message, found {len(results)}")
    result = results[0]
    _require_success(result)
    text = result.get("result")
    if not isinstance(text, str):
        raise ClaudeOutputError("the result message has no text in 'result'")

    usage_models = _models_from_usage(result)
    init_models = _models_from_init(messages)

    if usage_models is None and not init_models:
        raise ModelIdentityError("the output names no model (no modelUsage breakdown, no system/init message)")
    if usage_models is not None and len(usage_models) != 1:
        raise ModelIdentityError(
            f"modelUsage names {len(usage_models)} models, expected exactly one", tuple(sorted(usage_models))
        )
    if usage_models is None:
        if len(init_models) != 1:
            raise ModelIdentityError(
                f"system/init messages name {len(init_models)} models, expected exactly one", tuple(sorted(init_models))
            )
        return ClaudeResult(text, next(iter(init_models)))
    (model,) = usage_models
    if init_models and init_models != {model}:
        raise ModelIdentityError(
            "system/init and modelUsage disagree about the model", tuple(sorted(init_models | {model}))
        )
    return ClaudeResult(text, model)


def _as_messages(document: bytes | str | Mapping[str, Any] | list[Any]) -> list[Mapping[str, Any]]:
    value: Any = document
    if isinstance(document, (bytes, bytearray)):
        try:
            value = bytes(document).decode("utf-8")
        except UnicodeDecodeError as error:
            raise ClaudeOutputError("the output is not UTF-8") from error
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ClaudeOutputError("the output is empty")
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            lines = [line for line in text.splitlines() if line.strip()]
            try:
                value = [json.loads(line) for line in lines]
            except json.JSONDecodeError as error:
                raise ClaudeOutputError("the output is not JSON") from error
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, list) and value and all(isinstance(item, Mapping) for item in value):
        return list(value)
    raise ClaudeOutputError("the output is not a JSON object or a list of JSON objects")


def _require_success(result: Mapping[str, Any]) -> None:
    subtype = result.get("subtype")
    if result.get("is_error") is True or (subtype is not None and subtype != "success"):
        # Name the kind, never the content: a result text may carry document text.
        raise ClaudeOutputError(f"claude reported an unsuccessful run (subtype={subtype!r})")


def _models_from_usage(result: Mapping[str, Any]) -> set[str] | None:
    """The model ids of the per-model breakdown, or ``None`` if the document has no such map."""
    found: list[set[str]] = []
    for key in _MODEL_USAGE_KEYS:
        if key not in result:
            continue
        usage = result[key]
        if not isinstance(usage, Mapping):
            raise ClaudeOutputError(f"'{key}' is not an object")
        names = set(usage)
        if not all(isinstance(name, str) and name.strip() for name in names):
            raise ModelIdentityError(f"'{key}' has an empty model name")
        found.append(names)
    if not found:
        return None
    if len(found) > 1 and found[0] != found[1]:
        raise ModelIdentityError("modelUsage and model_usage disagree", tuple(sorted(found[0] | found[1])))
    return found[0]


def _models_from_init(messages: list[Mapping[str, Any]]) -> set[str]:
    models: set[str] = set()
    for message in messages:
        if message.get("type") == "system" and message.get("subtype") == "init":
            model = message.get("model")
            if not isinstance(model, str) or not model.strip():
                raise ModelIdentityError("a system/init message carries no model")
            models.add(model)
    return models
