"""The similarity thresholds, «unavailable» without a vector, the order independence of the whole advice and the core's isolation."""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

import auditmanager.precedents as package
from auditmanager.precedents.similarity import BAND_ANALOGOUS, BAND_BELOW, BAND_SIMILAR, Thresholds, band
from tests.unit.precedents.builders import REJECTED, advise, case, corpus, critic, scored


def test_the_default_thresholds_are_085_075_092_and_the_edges_are_inclusive():
    th = Thresholds()
    assert (th.analogous, th.similar, th.history) == (0.85, 0.75, 0.92)
    assert [band(value, th) for value in (0.85, 0.8499, 0.75, 0.7499, 1.0, -0.2)] == [
        BAND_ANALOGOUS,
        BAND_SIMILAR,
        BAND_SIMILAR,
        BAND_BELOW,
        BAND_ANALOGOUS,
        BAND_BELOW,
    ]


def test_the_thresholds_are_parameters():
    strict = Thresholds(analogous=0.9, similar=0.8, history=0.95)
    items = corpus(6, cosine=0.88)
    assert advise(items, [critic("reject")]).label.code == "cancel_suggested"
    assert advise(items, [critic("reject")], thresholds=strict).label.code == "none"
    for bad in (dict(analogous=0.7), dict(history=0.8), dict(similar=-0.1), dict(history=1.2)):
        with pytest.raises(ValueError):
            Thresholds(**bad)


def test_no_vector_means_unavailable_and_nothing_else_is_computed():
    advice = advise(None, [critic("reject")])
    assert (advice.status, advice.unavailable_reason) == ("unavailable", "no_vector")
    assert advice.label is None and advice.vote_set is None and advice.hints == () and advice.stop_words_found == ()


def test_a_vector_with_no_neighbours_is_not_unavailable():
    advice = advise([])
    assert advice.status == "ok" and advice.label.code == "none"


@pytest.mark.parametrize("bad", [math.nan, math.inf, 1.5, -1.5])
def test_a_cosine_that_is_not_a_cosine_is_refused(bad):
    with pytest.raises(ValueError):
        scored(case("a"), bad)


def test_the_advice_does_not_depend_on_the_order_of_the_scored_cases():
    items = [*corpus(6), scored(case("odd", REJECTED, days_ago=3, project="p1"), 0.97)]
    forward = advise(items, [critic("reject")])
    backward = advise(list(reversed(items)), [critic("reject")])
    assert forward == backward


def test_the_core_imports_no_other_bounded_context():
    root = Path(package.__file__).parent
    offenders = []
    for path in sorted(root.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            offenders += [f"{path.name}: {name}" for name in names if name.startswith("auditmanager.") and not name.startswith("auditmanager.precedents")]
    assert offenders == []
