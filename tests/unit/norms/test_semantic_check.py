"""`NORM-VECTOR-TEMP-01`: the quality gate's arithmetic (thresholds of the owner, 2026-11-11: 0.97 and 0.90)."""

from __future__ import annotations

import pytest

from auditmanager.norms import semantic_check as gate
from auditmanager.norms.semantic_check import WindowResult


def test_the_owner_thresholds() -> None:
    assert (gate.MIN_MEAN_INNER_PRODUCT, gate.MIN_SELF_RECALL_AT_10) == (0.97, 0.90)


def test_a_pgvector_literal_is_read_as_floats() -> None:
    assert gate.parse_vector("[0.5,-0.25,1e-3]") == [0.5, -0.25, 0.001]
    assert gate.inner_product([0.6, 0.8], [0.6, 0.8]) == pytest.approx(1.0)


def test_pass_needs_both_measures() -> None:
    good = [WindowResult(0.985, True)] * 95 + [WindowResult(0.96, False)] * 5
    assert gate.verdict(good)["verdict"] == "PASS"
    low_similarity = [WindowResult(0.95, True)] * 100
    assert gate.verdict(low_similarity)["verdict"] == "FAIL"
    low_recall = [WindowResult(0.99, True)] * 85 + [WindowResult(0.99, False)] * 15
    summary = gate.verdict(low_recall)
    assert summary["verdict"] == "FAIL" and summary["self_recall_at_10"] == 0.85


def test_no_window_is_a_fail_never_a_pass() -> None:
    assert gate.verdict([])["verdict"] == "FAIL"
