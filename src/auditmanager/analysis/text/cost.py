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


#: The two values ``cost_basis`` takes, named once. ``model_call.cost_basis`` holds the
#: same pair (migration ``0004``) and ``RunStatus.cost_basis`` publishes it.
BASIS_MEASURED: str = "measured"
BASIS_ESTIMATED: str = "estimated"


@dataclass(slots=True)
class CostMeter:
    """Accumulated measured spend for one run, against one ceiling."""

    ceiling_usd: float
    spent_usd: float = field(default=0.0)
    call_count: int = field(default=0)
    #: Contributions to :attr:`spent_usd` the transport did not price. Not a constructor
    #: argument: a caller cannot declare the provenance of spend it is handing over, and
    #: :meth:`__post_init__` decides what an opening balance means.
    unpriced_contributions: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        # An opening balance is spend this meter did not charge and cannot vouch for.
        # `execute_run` accepts a meter already carrying spend, so this is a real state
        # and not a hypothetical. Counting it as unpriced is `D-3` applied to the absent
        # case: the flattering reading of "no provenance recorded" is `measured`, and it
        # is the one reading that can be wrong in the direction nobody notices.
        if self.spent_usd:
            self.unpriced_contributions += 1

    @property
    def remaining_usd(self) -> float:
        return self.ceiling_usd - self.spent_usd

    @property
    def cost_basis(self) -> str:
        """How :attr:`spent_usd` was arrived at, over **every** contribution to it.

        ``R-14``, which is the rule ``W18-SEAL`` already gave ``RunStatus.cost_basis``:
        ``measured`` only when every contributing call reported a cost of its own,
        ``estimated`` the moment one did not. The two places now say the same thing.

        It describes the *sum*, not the last call. One call's own record carries that
        call's own basis and can legitimately read ``measured`` while this reads
        ``estimated`` -- they are answers about different numbers.

        A meter that has charged nothing reports ``estimated`` and never ``measured``:
        there is no measurement to claim. The stage emits this only after a charge, so
        that state does not reach the metrics, but the rule is stated rather than left
        to that coincidence.
        """
        if self.unpriced_contributions or self.call_count == 0:
            return BASIS_ESTIMATED
        return BASIS_MEASURED

    def check_before_call(self) -> None:
        """Halt before spending anything more once the ceiling is reached."""
        if self.spent_usd >= self.ceiling_usd:
            raise cost_budget_exceeded()

    def charge(
        self,
        pin: ModelPin,
        *,
        input_tokens: int,
        output_tokens: int,
        reported_cost_usd: float | None = None,
    ) -> float:
        """Add one call's measured cost, then halt if the run has passed the ceiling.

        The charge is recorded before the check so the model call record and the run
        report show what was actually spent, including the call that broke the
        budget. Hiding that call would understate the spend.
        """
        # A reported figure wins over the pinned table. The table is a rate card for one
        # model; under `OD-02`'s revision the model is chosen at configuration time and may
        # not be in the table at all, in which case the estimate is not merely imprecise but
        # absent. When the transport measures the spend, the ceiling should hold against the
        # measurement.
        cost = (
            float(reported_cost_usd)
            if reported_cost_usd is not None
            else pin.cost_usd(input_tokens=input_tokens, output_tokens=output_tokens)
        )
        self.spent_usd += cost
        self.call_count += 1
        # Counted here, beside the spend it qualifies, and before the ceiling check for
        # the same reason the spend is: the call that broke the budget is in
        # `spent_usd`, so it is in the provenance of `spent_usd`. `W18-SEAL`'s rule for
        # the `model_call` rows treats a NULL `cost_micros` as unmeasured; `None` here
        # is that same absence, one layer earlier and before it can be summed away.
        if reported_cost_usd is None:
            self.unpriced_contributions += 1
        if self.spent_usd > self.ceiling_usd:
            raise cost_budget_exceeded()
        return cost
