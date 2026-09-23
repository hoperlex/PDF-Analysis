"""The single externally visible failure shape.

Three things are structural here rather than reviewed, because a rule a caller must
remember is a rule that eventually is not remembered:

* ``retryable`` is read from the catalog for the reported code. It is not a parameter,
  so no call site can disagree with the catalog or infer it from an HTTP status.
* ``details`` accepts only the ``safe_detail_keys`` the catalog declares for that code.
  Anything else raises rather than being dropped, so a caller learns at once instead of
  shipping a redaction that silently did nothing.
* ``message`` defaults to the catalog summary. A custom message is screened for the
  shapes the catalog's safety rules forbid. There are **six**, and they are the six
  entries of ``_FORBIDDEN`` below, in its order: a URL, a filesystem path, an S3-style
  object key, a credential, SQL, a stack frame. The screen is a floor, not a proof: it
  cannot read intent, only shape.

  Since ``B6``, **string ``details`` values are screened by those same six patterns**,
  raising :class:`UnsafeDetailValue`. A key being declared safe says nothing about what
  a call site puts under it, so the value screen is not optional and is not weaker than
  the message screen. Any comment elsewhere in the tree claiming details are unscreened
  is stale; ``tests/integration/api/test_envelope_screen_rules.py`` holds both counts
  and the enumeration above to this docstring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Final, Mapping

from auditmanager.shared.errors.catalog import CONTRACT_VERSION
from auditmanager.shared.errors.codes import ErrorCode

_MAX_MESSAGE = 512
_MAX_DETAILS = 16
_MAX_DETAIL_VALUE = 256

#: Shapes the catalog's safety rules forbid in a caller-visible message.
_FORBIDDEN: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("a URL", re.compile(r"\b[a-z][a-z0-9+.-]*://", re.I)),
    ("a filesystem path", re.compile(r"(^|\s)[/~]\S*/|\b[A-Za-z]:\\")),
    ("an S3-style object key", re.compile(r"\bs3://|\b[\w.-]+/[\w.-]+/[\w.-]+\.\w+")),
    ("a credential", re.compile(r"(?i)\b(password|secret|token|api[_-]?key|bearer)\b\s*[:=]")),
    # A verb and a clause keyword within the same sentence, not adjacent: the first
    # version of this pattern required SELECT to touch FROM and so let
    # "SELECT id FROM blob" straight through. Its own test caught that.
    (
        "SQL",
        re.compile(
            r"(?i)\b(select|insert|update|delete|drop|alter)\b[\s\S]{0,60}?"
            r"\b(from|into|table|set|where|values)\b"
        ),
    ),
    ("a stack frame", re.compile(r'File "|Traceback \(most recent')),
)


class UnsafeMessage(ValueError):
    """Raised when a caller-visible message carries a shape the catalog forbids."""


class UnsafeDetailKey(ValueError):
    """Raised when ``details`` carries a key the catalog does not declare safe."""


class UnsafeDetailValue(ValueError):
    """Raised when a ``details`` value carries a shape the catalog forbids.

    Distinct from :class:`UnsafeDetailKey` because the remedies differ: a bad key means
    the call site chose a field the catalog does not declare, while a bad value means a
    declared field was filled with raw input instead of a classifier.
    """


def screen_message(message: str) -> str:
    if not message or len(message) > _MAX_MESSAGE:
        raise UnsafeMessage(f"message must be 1..{_MAX_MESSAGE} characters")
    for what, pattern in _FORBIDDEN:
        if pattern.search(message):
            raise UnsafeMessage(
                f"message appears to contain {what}; the catalog's safety rules forbid it"
            )
    return message


@dataclass(frozen=True, slots=True)
class ErrorEnvelope:
    """``urn:auditmanager:domain:error-envelope:v1``."""

    error_code: ErrorCode
    correlation_id: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)
    contract_version: str = CONTRACT_VERSION

    @property
    def retryable(self) -> bool:
        """Pinned to the catalog value for the reported code."""
        return self.error_code.retryable

    @property
    def http_status(self) -> int:
        return self.error_code.http_status

    def as_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contract_version": self.contract_version,
            "error_code": self.error_code.value,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "retryable": self.retryable,
        }
        if self.details:
            body["details"] = dict(self.details)
        return body


def screen_details(
    code: ErrorCode, details: Mapping[str, Any] | None
) -> dict[str, Any]:
    """The catalog's detail rules for ``code``, applied to ``details``.

    Four rules, and each raises rather than dropping, so a caller learns at once instead of
    shipping a redaction that silently did nothing:

    * the key is one of ``code.safe_detail_keys``;
    * the value is a scalar;
    * a string value is at most :data:`_MAX_DETAIL_VALUE` characters;
    * a string value carries none of the six shapes :data:`_FORBIDDEN` describes -- the
      same screen a message gets, because a key being declared safe says nothing about
      what a call site put under it. `B6` found that the hard way: its
      ``additionalProperties`` refusal echoed the caller's own property name into
      ``details.field``, so a property named ``/etc/passwd`` came back inside the envelope.

    **It is a function rather than four lines inside :func:`build`, and `D-46` is why.**
    ``RunStatus.terminal_detail`` is a **200** body -- not an error envelope -- carrying
    classifiers the catalog declares safe for the code in ``terminal_reason``, so it is
    bound by exactly these rules and by nothing else. A second implementation of them,
    beside this one, would be two spellings of one fact in a codebase that has been caught
    by that shape before (``OPERATING_CONSTRAINTS.md`` §12). So there is one screen, and
    the restriction holds by construction wherever it is called rather than by a second
    author remembering it.
    """
    checked: dict[str, Any] = {}
    if not details:
        return checked
    allowed = code.safe_detail_keys
    for key, value in details.items():
        if key not in allowed:
            raise UnsafeDetailKey(
                f"{code.value} declares safe_detail_keys {sorted(allowed)}; "
                f"{key!r} is not one of them"
            )
        if not isinstance(value, (str, int, float, bool, type(None))):
            raise UnsafeDetailKey(
                f"detail {key!r} must be a scalar, got {type(value).__name__}"
            )
        if isinstance(value, str):
            if len(value) > _MAX_DETAIL_VALUE:
                raise UnsafeDetailKey(
                    f"detail {key!r} exceeds {_MAX_DETAIL_VALUE} characters"
                )
            for what, pattern in _FORBIDDEN:
                if pattern.search(value):
                    raise UnsafeDetailValue(
                        f"detail {key!r} appears to contain {what}; the catalog's "
                        "safety rules forbid it. Details carry classifiers, not "
                        "raw input - map the input to a classifier first."
                    )
        checked[key] = value
    if len(checked) > _MAX_DETAILS:
        raise UnsafeDetailKey(f"details carries more than {_MAX_DETAILS} keys")
    return checked


def build(
    code: ErrorCode,
    correlation_id: str,
    *,
    message: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> ErrorEnvelope:
    """Construct an envelope. ``retryable`` is never an argument."""
    text = screen_message(message) if message is not None else code.summary
    return ErrorEnvelope(
        error_code=code,
        correlation_id=correlation_id,
        message=text,
        details=screen_details(code, details),
    )
