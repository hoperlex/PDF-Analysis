"""Priced consent for a Run started through the composed application (`REVIEW-FIX-TESTS-1102`, S6-02).

The composition root sets ``require_cost_consent=True`` (``bootstrap/composition.py``), so the served
``startRun``, ``reauditRun`` and ``startArV3BetaGroup`` refuse a start that carries no confirmed consent
(``422 validation_failed``, ``constraint=confirmation_required``). A suite that drives the composed
application therefore does what the web client does: it asks ``POST /runs/cost-estimate`` for the price of
*this* version, then starts with a ``cost_consent`` built from that estimate -- the estimate's digest, its
own recommended ceiling, ``confirmed: true``. Nothing here invents a digest or a cap, and the consent is
read from a fresh estimate at the call site, so a classification or source change between two starts is
priced again instead of replaying a stale digest.

Container-free to import; the calls it makes need whatever client the suite already has (anything with
``post(url, headers=..., json=...)`` returning a response with ``status_code``, ``json()`` and ``text``).

An exact replay of a start (same idempotency key, same body) must repeat the *same* consent: the consent is
part of the command fingerprint, so a replay builds its body once, with :func:`consented_body`, and sends it
twice.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any, Protocol

import pytest

__all__ = [
    "ESTIMATE_GROUP_PATH",
    "ESTIMATE_RUN_PATH",
    "consented_body",
    "estimate_run_cost",
    "plain_analysis_pricing",
    "run_consent",
]

ESTIMATE_RUN_PATH = "/runs/cost-estimate"
ESTIMATE_GROUP_PATH = "/ar-v3-beta/groups/cost-estimate"

#: Headers that belong to the start, not to the estimate: the estimate is a read and carries no key.
_START_ONLY_HEADERS = frozenset({"idempotency-key", "content-type", "content-length"})


class _Client(Protocol):
    def post(self, url: str, **kwargs: Any) -> Any: ...


def run_consent(estimate: Mapping[str, Any]) -> dict[str, Any]:
    """The ``cost_consent`` an expert gives to exactly this estimate, at the ceiling it recommends."""
    ceiling = estimate["recommended_ceiling_micros"]
    assert type(ceiling) is int and ceiling >= 0, estimate
    return {
        "estimate_digest": estimate["estimate_digest"],
        "ceiling_micros": ceiling,
        "confirmed": True,
    }


def estimate_run_cost(
    client: _Client,
    headers: Mapping[str, str],
    body: Mapping[str, Any],
    *,
    path: str = ESTIMATE_RUN_PATH,
) -> dict[str, Any]:
    """``POST /runs/cost-estimate`` (or the group estimate) for ``body``; the answer must be a ``200``."""
    sent = {name: value for name, value in headers.items() if name.lower() not in _START_ONLY_HEADERS}
    answer = client.post(path, headers=sent, json=dict(body))
    assert answer.status_code == 200, f"{path} answered {answer.status_code}: {answer.text}"
    return answer.json()


def consented_body(
    client: _Client,
    headers: Mapping[str, str],
    body: Mapping[str, Any],
    *,
    path: str = ESTIMATE_RUN_PATH,
) -> dict[str, Any]:
    """``body`` plus a ``cost_consent`` taken from a fresh estimate of it."""
    return {**body, "cost_consent": run_consent(estimate_run_cost(client, headers, body, path=path))}


@contextmanager
def plain_analysis_pricing() -> Iterator[None]:
    """Price the plain recorded analysis, without the extended review, for the starts made inside it.

    The shipped default plan is the extended review (`AUDITMANAGER_EXTENDED_ANALYSIS`, v2 since `V3-OPTIN-01`; v3 is
    opt-in by `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN`): a consent for either approves dozens of further model calls
    (per window for v3, per page and image batch for v2), none of which exists in the committed recordings, so a
    recorded run under that consent cannot finish as the corpus run did. The suites that use this helper test
    what is read *after* a run (reports, findings, comparisons, specifications), and before consent became
    mandatory they ran exactly the plain analysis; this keeps them on it. The switch is read where the cost is
    estimated (``runs/preflight.py``), by the estimate request and again by the start that recomputes it, so both
    must be made inside the block. A suite about the extended review itself does not use this.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS", "0")
        yield
