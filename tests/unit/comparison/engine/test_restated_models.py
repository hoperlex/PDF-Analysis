"""The models of `engine/validate.py` are held to the generated models of the contract (`CMP-ENGINE-01`).

The engine restates them because ``api.schemas.models`` is not a public module of its context (the boundary guard
``test_alr05_boundaries`` refuses the import). The contract is the authority: the JSON schema of every restated class
equals the generated class's, and valid and invalid members are accepted or refused by both alike.
"""

from __future__ import annotations

import copy

import pytest

from auditmanager.api.schemas import models as generated
from auditmanager.comparison.engine import validate

CAPS = {"differences": 2000, "text_changes": 2000, "service_notes": 500}


def _strip(node):
    """The schema without titles and descriptions, which prose changes, and without defaults the generated models hide."""
    if isinstance(node, dict):
        return {k: _strip(v) for k, v in node.items() if k not in ("title", "description", "default")}
    if isinstance(node, list):
        return [_strip(v) for v in node]
    return node


@pytest.mark.parametrize("name", sorted(validate.MODELS))
def test_the_json_schema_of_a_restated_model_is_that_of_the_generated_one(name: str) -> None:
    ours = _strip(validate.MODELS[name].model_json_schema())
    theirs = _strip(getattr(generated, name).model_json_schema())
    assert ours == theirs


def test_the_caps_are_those_of_the_contract_document() -> None:
    import json
    from pathlib import Path

    document = json.loads((Path(__file__).resolve().parents[4] / "contracts/api/v1/openapi.json").read_text(encoding="utf-8"))
    sheet_pair = document["components"]["schemas"]
    # The caps live on the members of ComparisonSheetPair; the engine's list is the same.
    members = sheet_pair["ComparisonSheetPair"]["properties"]
    found = {name: members[name].get("maxItems") for name in ("differences", "text_changes", "service_notes") if name in members}
    assert found == {name: CAPS[name] for name in found} and validate.CAPS == CAPS


VALID = {
    "ComparisonChannels": [{}, {"geometry": {"state": "checked", "diffs": 0}}, {"text": {"state": "unchecked", "reason": "x"}}],
    "ComparisonChannel": [{"state": "not_applicable", "reason": "r"}],
    "ComparisonBox": [{"x": 0, "y": -1, "width": 0, "height": 2.5}],
    "ComparisonDifference": [{"region_class": "text", "layer": "main", "box": {"x": 0, "y": 0, "width": 1, "height": 1}, "before_text": "а"}],
    "ComparisonTextChange": [{"kind": "added"}, {"kind": "changed", "numbers": [{"before": "1", "after": "2"}], "box": {"x": 0, "y": 0, "width": 1, "height": 1}}],
    "ComparisonServiceNote": [{"kind": "field", "change": "changed", "zone": "stamp", "field": "designation", "before": "а", "after": "б"}],
    "ComparisonHowCompared": [{"algo_version": "a", "dpi": 200, "tolerance_pt": 0.5, "transform": [1, 0, 0, 1, 0, 0], "aligned_blocks": 0}],
    "ComparisonCanvas": [{"width_pt": 1, "height_pt": 2}],
}
INVALID = {
    "ComparisonChannels": [{"geometry": {"state": "weird"}}, {"extra": {}}, {"geometry": None}],
    "ComparisonChannel": [{}, {"state": "checked", "diffs": -1}, {"state": "checked", "reason": ""}, {"state": "checked", "reason": "x" * 129}],
    "ComparisonBox": [{"x": 0, "y": 0, "width": -1, "height": 1}, {"x": 0}],
    "ComparisonDifference": [{"region_class": "Bad", "layer": "main", "box": {"x": 0, "y": 0, "width": 1, "height": 1}},
                             {"region_class": "text", "layer": "nope", "box": {"x": 0, "y": 0, "width": 1, "height": 1}},
                             {"region_class": "text", "layer": "main", "box": {"x": 0, "y": 0, "width": 1, "height": 1}, "before_text": ""}],
    "ComparisonTextChange": [{"kind": "A"}, {"kind": "added", "numbers": [{"before": "", "after": "1"}]}, {"kind": "added", "before": "x" * 2001}],
    "ComparisonServiceNote": [{"kind": "field"}, {"kind": "field", "change": "gone"}, {"kind": "field", "change": "added", "zone": ""}],
    "ComparisonHowCompared": [{"algo_version": "a", "dpi": 0, "tolerance_pt": 0.5}, {"algo_version": "a", "dpi": 1, "tolerance_pt": 0.5, "transform": [1, 2, 3]}],
    "ComparisonCanvas": [{"width_pt": 0, "height_pt": 2}, {"width_pt": 1}],
}


def _accepts(model, payload) -> bool:
    try:
        model(**copy.deepcopy(payload))
    except Exception:  # noqa: BLE001 - any refusal
        return False
    return True


@pytest.mark.parametrize("name", sorted(VALID))
def test_valid_and_invalid_members_are_accepted_and_refused_by_both_alike(name: str) -> None:
    ours, theirs = validate.MODELS[name], getattr(generated, name)
    for payload in VALID[name]:
        assert _accepts(theirs, payload) and _accepts(ours, payload), payload
    for payload in INVALID[name]:
        assert not _accepts(theirs, payload) and not _accepts(ours, payload), payload
