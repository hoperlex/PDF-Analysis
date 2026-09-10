"""The export discriminator: ``terminal_semantics.publishes_result``, read from the contract.

``OD-11`` says which runs export, and it says it through a **flag the domain contract
already carries** rather than through a list of state names somebody types out. The
difference matters: a hand-written list is a second place for the policy to live, and
the first place for it to drift. ``contracts/domain/v1/state-machines.json`` declares,
for each terminal of ``audit_run``, whether that terminal publishes a result. This
module reads exactly that.

So the policy is not "``published`` or ``partial``". The policy is "``publishes_result``
is true", and ``published`` and ``partial`` are simply the two terminals for which it
currently is. If the contract ever changed, this module would follow it without an edit,
which is the property a hand-written list cannot have.

Everything else is refused with the typed ``state_transition_not_allowed``: a
non-terminal run, and the terminal ``failed``. ``cancelled`` is likewise false and is
unreachable in PC-01, there being no cancel command.

**PC-01 never emits ``partial_result_not_publishable`` from here.** The frozen contract
raises that code for "an operation that requires a complete run"; under ``OD-11`` this
export is explicitly not one — a ``partial`` run exports, with its degraded state visible
in the ``run_state`` column rather than as a silent empty file. P02 §6 says so in as many
words.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Final, Mapping

from auditmanager.shared.errors import DomainError, ErrorCode

#: ``src/auditmanager/exports/policy.py`` -> repository root.
CONTRACT_PATH: Final[Path] = (
    Path(__file__).resolve().parents[3]
    / "contracts"
    / "domain"
    / "v1"
    / "state-machines.json"
)

#: The machine whose terminals this policy reads.
MACHINE: Final[str] = "audit_run"


@lru_cache(maxsize=1)
def publishes_result_by_state() -> Mapping[str, bool]:
    """``{terminal_state: publishes_result}`` for ``audit_run``, from the contract.

    Only terminal states appear. A state absent from the mapping is either non-terminal
    or not declared at all, and neither exports.
    """
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    semantics = document["machines"][MACHINE]["terminal_semantics"]
    return {
        state: bool(body.get("publishes_result", False))
        for state, body in semantics.items()
    }


def publishes_result(state: str) -> bool:
    """Does a run in this state publish a result a reader may download?"""
    return publishes_result_by_state().get(state, False)


def exportable_states() -> frozenset[str]:
    """The states that export. Derived, never typed out."""
    return frozenset(
        state for state, flag in publishes_result_by_state().items() if flag
    )


def assert_exportable(state: str, *, run_id: str) -> None:
    """Refuse a run whose terminal does not publish a result.

    The refusal is ``state_transition_not_allowed`` — the code the frozen contract
    assigns — and carries the run identity and the state, both of which the catalog
    admits as safe detail keys. It does **not** carry
    ``partial_result_not_publishable``: see the module docstring.
    """
    if publishes_result(state):
        return
    raise DomainError(
        ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
        message=(
            "this run's state does not publish a result, so there is nothing to "
            "export; the contract's terminal_semantics.publishes_result is false for it"
        ),
        machine=MACHINE,
        current_state=state,
    )


__all__ = [
    "CONTRACT_PATH",
    "MACHINE",
    "assert_exportable",
    "exportable_states",
    "publishes_result",
    "publishes_result_by_state",
]
