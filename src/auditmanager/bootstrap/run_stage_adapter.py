"""``RunStagePort``: the stages of a run, plan and fact (`RUN-STAGES-01`, contract 1.46.0).

The runs context owns the rule (``runs/stage_facts.py``: the three places the facts come from, the chips, the plan); this adapter owns the
two things the rule must not know -- the caller's role set, read in its own transaction as every adapter does, and the mapping into the
contract's ``RunStages``. The viewer («Наблюдатель», `R-150w`) reads the stages but not the server or the access of a cell, so the flag
``include_server`` is true only for a caller who holds ``expert`` or ``admin``: an account with no role, and the viewer, get neither
(fail closed). A new file beside ``adapters.py`` on purpose: ``adapters.py`` is the integrator's hotspot, and the integrator wires this
class as ``run_stages=RunStageAdapter(session_factory, blob_store=blob_store)`` in the composition root.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import ROLE_ADMIN, ROLE_EXPERT, AccountRepository
from auditmanager.api.schemas import models
from auditmanager.runs.stage_facts import read_run_stage_facts

__all__ = ["RunStageAdapter"]


class RunStageAdapter:
    def __init__(self, session_factory: sessionmaker[Session], *, blob_store: Any) -> None:
        self._sessions = session_factory
        self._blob_store = blob_store

    def get_run_stages(self, *, run_id: str, user_uid: str) -> models.RunStages:
        with self._sessions() as session:
            roles = AccountRepository().roles_of(session, user_uid)
        facts = read_run_stage_facts(
            self._sessions, self._blob_store, run_id=run_id, include_server=bool(roles & {ROLE_EXPERT, ROLE_ADMIN}),
        )
        return models.RunStages.model_validate(facts)
