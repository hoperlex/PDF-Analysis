"""`REVIEW-FIX-TESTS-1102` (S6-02): the one literal the money guarantee hangs on is pinned.

"No served Run starts without a confirmed priced consent" is carried by a single keyword of the
composition root: ``RunAdapter(..., require_cost_consent=True)`` (``bootstrap/composition.py``), read by
``bootstrap/adapters.py`` to hand the cost preflight to ``start_audit_run`` / ``reaudit_run``. Before this module nothing in the tree read that keyword, so flipping it to
``False`` broke no test. The behavioural proof over HTTP needs a database
(``tests/integration/composition/test_the_served_start_requires_a_priced_consent.py``); this is the
container-free half and runs everywhere: it reads the composition source as syntax, not as text, and a
control shows the reader goes red on the mutated source.
"""

from __future__ import annotations

import ast
from pathlib import Path

COMPOSITION = Path(__file__).resolve().parents[3] / "src" / "auditmanager" / "bootstrap" / "composition.py"


def _consent_keywords(source: str) -> list[tuple[str, ast.expr]]:
    """``(callee, value)`` of every ``require_cost_consent=...`` keyword in a call, however it is spelled."""
    found: list[tuple[str, ast.expr]] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        callee = ast.unparse(node.func)
        for keyword in node.keywords:
            if keyword.arg == "require_cost_consent":
                found.append((callee, keyword.value))
    return found


def _gate_is_pinned(source: str) -> bool:
    """Exactly one call passes the keyword, it is the run adapter, and the value is the constant ``True``."""
    found = _consent_keywords(source)
    if len(found) != 1:
        return False
    callee, value = found[0]
    return (
        callee.rsplit(".", 1)[-1] == "RunAdapter"
        and isinstance(value, ast.Constant)
        and value.value is True
    )


def test_the_composition_root_builds_the_run_adapter_with_the_consent_gate_closed() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    assert _gate_is_pinned(source), _consent_keywords(source)


def test_the_reader_goes_red_when_the_literal_is_flipped_removed_or_duplicated() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    assert _gate_is_pinned(source)
    assert source.count("require_cost_consent=True") == 1
    flipped = source.replace("require_cost_consent=True", "require_cost_consent=False")
    assert not _gate_is_pinned(flipped)
    removed = source.replace("        require_cost_consent=True,\n", "")
    assert removed != source and not _gate_is_pinned(removed)
    computed = source.replace("require_cost_consent=True", "require_cost_consent=bool(1)")
    assert not _gate_is_pinned(computed)
    duplicated = source + "\n_second = RunAdapter(require_cost_consent=True)\n"
    assert not _gate_is_pinned(duplicated)
