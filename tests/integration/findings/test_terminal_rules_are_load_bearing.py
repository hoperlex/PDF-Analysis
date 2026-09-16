"""Two rules in ``findings/terminal.py`` that the `W10-FND` mutation sweep could not redden.

* **`TERMINALS_FROM_VALIDATING` has no consumer.** It is defined in ``terminal.py``,
  re-exported from ``auditmanager.findings``, and read by nothing in ``src/``, ``tests/``
  or ``web/``. Replacing it with ``{"published", "cancelled"}`` left all 302 tests of the
  integration battery green, because no behaviour depends on it. A constant nothing reads
  can only be guarded by pinning it against an authority outside the module and against
  what ``select_terminal`` can actually return — both of which this file does.

* **`codes.discard(None)` in `_reason_for`.** Deleting it left all 302 green. Its own
  docstring says the correction exists so that an operator can tell "a model that answered
  badly" (``analysis_failed``, not retryable) from "a provider that never answered"
  (``dependency_unavailable``, retryable). Every case in ``TestTheReasonNamesTheCause``
  supplies a code for **every** failing stage, so ``None`` never enters the set and
  ``discard`` never does anything. A run where one failing stage reported a code and
  another reported none is the case the line was written for.

Expected values here are literals or come from the frozen contract. Nothing imports
``TERMINALS_FROM_VALIDATING`` and then builds its expectation from it.
"""

from __future__ import annotations

import json
from pathlib import Path

from auditmanager.findings import TERMINALS_FROM_VALIDATING, select_terminal

#: The tests' own route to the contract, resolved from this file and not from the module
#: under test — so a module whose ``CONTRACT_PATH`` drifted would not drag the expectation
#: with it.
_CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "contracts"
    / "domain"
    / "v1"
    / "state-machines.json"
)

REQUIRED = ("source_preparation", "document_context_build", "text_analysis")


class TestTerminalsFromValidatingAgreeWithTheContract:
    def test_it_is_exactly_the_three_terminals_pc01_can_reach(self) -> None:
        # Literals. `cancelled` is a declared terminal of `audit_run` and is deliberately
        # absent: PC-01 has no cancel command, so `validating` cannot reach it.
        assert TERMINALS_FROM_VALIDATING == {"published", "partial", "failed"}

    def test_every_member_is_a_declared_terminal_of_audit_run(self) -> None:
        semantics = json.loads(_CONTRACT.read_text(encoding="utf-8"))["machines"][
            "audit_run"
        ]["terminal_semantics"]
        declared = set(semantics)
        assert declared == {"published", "partial", "failed", "cancelled"}
        assert TERMINALS_FROM_VALIDATING <= declared, (
            "the constant names a state the contract does not declare terminal"
        )
        assert declared - TERMINALS_FROM_VALIDATING == {"cancelled"}

    def test_select_terminal_never_returns_a_state_outside_it(self) -> None:
        """The behavioural half: whatever the constant says, the function must agree.

        Every combination of the four declared stage statuses over the three required
        stages, with the gate having run and having not run.
        """
        statuses = ("succeeded", "partial", "failed", "skipped")
        reached = set()
        for a in statuses:
            for b in statuses:
                for c in statuses:
                    for gate_ran in (True, False):
                        selection = select_terminal(
                            dict(zip(REQUIRED, (a, b, c))),
                            required_stages=REQUIRED,
                            gate_ran=gate_ran,
                        )
                        reached.add(selection.state)
        assert reached == {"published", "partial", "failed"}
        assert reached == set(TERMINALS_FROM_VALIDATING)


class TestAStageWithNoCodeDoesNotVetoASharedOne:
    """``codes.discard(None)``, the line the reason-naming correction turns on."""

    def test_one_reported_code_and_one_silent_stage_keeps_the_reported_code(self) -> None:
        selection = select_terminal(
            {
                "source_preparation": "failed",
                "document_context_build": "failed",
                "text_analysis": "succeeded",
            },
            required_stages=REQUIRED,
            stage_errors={
                "source_preparation": "dependency_unavailable",
                # document_context_build reported no code at all.
            },
        )
        assert selection.state == "failed"
        # The literal, not `ErrorCode.DEPENDENCY_UNAVAILABLE.value`: the catalog marks this
        # code retryable and `analysis_failed` not retryable, and that difference is the
        # whole reason the line exists.
        assert selection.terminal_reason == "dependency_unavailable", (
            "a stage that reported no code vetoed the code the other stage did report"
        )

    def test_an_explicit_none_is_treated_the_same_as_an_absent_entry(self) -> None:
        selection = select_terminal(
            {
                "source_preparation": "failed",
                "document_context_build": "skipped",
                "text_analysis": "succeeded",
            },
            required_stages=REQUIRED,
            stage_errors={
                "source_preparation": "dependency_unavailable",
                "document_context_build": None,
            },
        )
        assert selection.terminal_reason == "dependency_unavailable"

    def test_two_different_reported_codes_still_keep_the_generic_reason(self) -> None:
        """The control. Discarding ``None`` must not collapse two *real* disagreements."""
        selection = select_terminal(
            {
                "source_preparation": "failed",
                "document_context_build": "failed",
                "text_analysis": "succeeded",
            },
            required_stages=REQUIRED,
            stage_errors={
                "source_preparation": "dependency_unavailable",
                "document_context_build": "analysis_failed",
            },
        )
        assert selection.terminal_reason == "analysis_failed"

    def test_every_failing_stage_silent_keeps_the_generic_reason(self) -> None:
        """The other control: discarding ``None`` must not leave an empty set naming
        something. No code at all is still ``analysis_failed``."""
        selection = select_terminal(
            {
                "source_preparation": "failed",
                "document_context_build": "failed",
                "text_analysis": "succeeded",
            },
            required_stages=REQUIRED,
            stage_errors={"source_preparation": None, "document_context_build": None},
        )
        assert selection.terminal_reason == "analysis_failed"
