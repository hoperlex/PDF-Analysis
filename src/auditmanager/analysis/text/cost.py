"""The per-run cost ceiling of ``OD-03``.

Exceeding the ceiling raises ``cost_budget_exceeded`` - the catalog code that exists
for exactly this case - and halts. It **never truncates the document and never
silently drops pages**: degrading the analysis to fit a budget would produce a result
that looks complete and is not, which is the outcome the ceiling exists to prevent.

The meter checks twice, and the two checks catch different failures:

* **before** a call, so a run already at the ceiling never issues another request and
  never spends past it;
* **after** a call, on measured usage, so a single call that turns out far more
  expensive than expected halts the run rather than being noticed in a bill.

Rates come from ``docs/program/P02_LOCK.json`` through :mod:`.lock`. No rate and no
model identifier is written down in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from auditmanager.analysis.text.lock import ModelPin
from auditmanager.shared.errors import DomainError, ErrorCode

#: The single safe detail key ``cost_budget_exceeded`` declares. It names the scope
#: the budget applies to, and carries no amount: an envelope is caller-visible, and
#: the measured spend belongs in the run record, not in an error message.
BUDGET_SCOPE_RUN: str = "run"


def cost_budget_exceeded() -> DomainError:
    """The typed halt. One construction site, so the code cannot drift."""
    return DomainError(
        ErrorCode.COST_BUDGET_EXCEEDED,
        message=(
            "the per-run model cost ceiling is exhausted; the stage halted without "
            "shortening the document"
        ),
        budget_scope=BUDGET_SCOPE_RUN,
    )


@dataclass(slots=True)
class CostMeter:
    """Accumulated measured spend for one run, against one ceiling."""

    ceiling_usd: float
    spent_usd: float = field(default=0.0)
    call_count: int = field(default=0)

    @property
    def remaining_usd(self) -> float:
        return self.ceiling_usd - self.spent_usd

    def check_before_call(self) -> None:
        """Halt before spending anything more once the ceiling is reached."""
        if self.spent_usd >= self.ceiling_usd:
            raise cost_budget_exceeded()

    def charge(self, pin: ModelPin, *, input_tokens: int, output_tokens: int) -> float:
        """Add one call's measured cost, then halt if the run has passed the ceiling.

        The charge is recorded before the check so the model call record and the run
        report show what was actually spent, including the call that broke the
        budget. Hiding that call would understate the spend.
        """
        cost = pin.cost_usd(input_tokens=input_tokens, output_tokens=output_tokens)
        self.spent_usd += cost
        self.call_count += 1
        if self.spent_usd > self.ceiling_usd:
            raise cost_budget_exceeded()
        return cost
