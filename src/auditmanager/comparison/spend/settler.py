"""The spend settler the queue's reclaim calls (`CMP-SPEND-01`, ADR-0025 decision 5).

``comparison.work`` reclaims an attempt whose lease ran out and, for each, asks every registered
settler whether the attempt left a model call that may have spent. This one answers ``True`` when there
was a call that was ``prepared`` or ``sent`` and not ended, **after** marking it ``unknown`` in the
reclaim's own transaction. The queue then ends the item ``spend_unknown`` instead of putting it back, so
the call is never sent a second time by itself; only an explicit retry of the item (``retry_spend_unknown``)
clears it.

It is the only thing between a dead worker and a double spend, so it is registered by being in
``comparison.public.SPEND_SETTLERS`` and by nothing else.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from auditmanager.comparison.spend.repository import ComparisonSpendRepository

__all__ = ["settle_lost_attempt"]

_REPOSITORY = ComparisonSpendRepository()


def settle_lost_attempt(session: Session, attempt_id: str) -> bool:
    """Mark every unfinished call of the lost attempt ``unknown``; ``True`` if there was one."""
    return _REPOSITORY.settle_attempt(session, attempt_id)
