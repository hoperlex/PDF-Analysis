"""`CRIT-SEAL-52` (contract 1.52.0): a block observation may have no text evidence, and a memory case may carry its comments.

Two debts of the first seal of the «Прецеденты» programme, closed by the second:

* `D-683`. ``FindingObservation.evidence`` had ``minItems: 1``. A finding of a ``one_list`` run grounded on a portal block has no text span, so its
  observation has ``evidence == []`` and its blocks are listed in the finding's ``block_evidence``. The contract now says it as a JSON Schema ``if``/``else``
  on ``grounding_kind`` (``minItems: 1`` for every observation that is not ``portal_block``, an absent kind included). It is an ``if``/``else`` and not a
  ``oneOf`` because the observation is a closed object: a ``oneOf`` branch would have to restate every member (the defect
  ``test_finding_detail_composition.py`` pins for ``allOf``), while ``else`` constrains a member that is already declared and adds none.
* `D-682`. ``DecisionMemoryCase.comments`` is an optional array of ``DecisionMemoryComment`` (``comment_id`` ``dmk``, ``decided_at``, ``comment``), with no
  author, like a decision.

Every guard here is shown to fail: the contract as it stood before is rebuilt in memory and run through the same validator, the closure is probed with a
member nobody declares, and the contract's own Pydantic models refuse what the schema refuses.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pydantic
import pytest

from auditmanager.api.schemas import models

ROOT = Path(__file__).resolve().parents[3]
BLOCK = "blk_" + "a" * 32
SHA = "b" * 64
ULID = "01M2545JSD15ETSNNV904X991M"


def _block_finding(finding: dict[str, Any], *, grounding_kind: str | None = "portal_block", evidence: list[Any] | None = None) -> dict[str, Any]:
    """The finding body of a block finding: no text evidence, its blocks in ``block_evidence``."""
    body = copy.deepcopy(finding)
    body["category"] = "drawing_discrepancy"
    body["origin"] = "drawing"
    observation = body["observation"]
    observation["category"] = "drawing_discrepancy"
    observation["evidence"] = [] if evidence is None else evidence
    if grounding_kind is None:
        observation.pop("grounding_kind", None)
    else:
        observation["grounding_kind"] = grounding_kind
    body["block_evidence"] = [{
        "ordinal": 0, "page_number": 3, "portal_block_id": BLOCK,
        "bbox_norm": {"x0": 0.1, "y0": 0.2, "x1": 0.6, "y1": 0.7}, "crop_sha256": SHA,
    }]
    return body


def _before_1_52_0(document: dict[str, Any]) -> dict[str, Any]:
    """The contract as 1.51.0 had it, rebuilt in memory: ``minItems: 1`` on the property and no ``if``/``else``. It proves the guards can fail."""
    older = copy.deepcopy(document)
    observation = older["components"]["schemas"]["FindingObservation"]
    observation["properties"]["evidence"]["minItems"] = 1
    del observation["if"]
    del observation["else"]
    return older


def _verdicts(validate: Any, document: dict[str, Any], schema: str, **payloads: Any) -> dict[str, bool]:
    results = validate(document, [{"name": name, "schema": schema, "payload": payload} for name, payload in payloads.items()])
    return {name: results[name]["valid"] for name in payloads}


# --- D-683: the evidence of a block observation ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("schema_name", ["Finding", "FindingDetail"])
def test_a_block_observation_with_no_text_evidence_validates(
    openapi_document: dict[str, Any], finding_detail_payload: dict[str, Any], finding_payload: dict[str, Any], validate: Any, schema_name: str
) -> None:
    base = finding_payload if schema_name == "Finding" else finding_detail_payload
    verdicts = _verdicts(validate, openapi_document, schema_name, block=_block_finding(base))
    assert verdicts == {"block": True}


@pytest.mark.parametrize("schema_name", ["Finding", "FindingDetail"])
def test_every_other_observation_still_needs_text_evidence(
    openapi_document: dict[str, Any], finding_detail_payload: dict[str, Any], finding_payload: dict[str, Any], validate: Any, schema_name: str
) -> None:
    base = finding_payload if schema_name == "Finding" else finding_detail_payload
    verdicts = _verdicts(
        validate, openapi_document, schema_name,
        text_span_kind=_block_finding(base, grounding_kind="text_span"),   # the kind is named and is not a block
        absent_kind=_block_finding(base, grounding_kind=None),             # absent means text_span, the only kind before 1.51.0
        plain_text_finding=_block_finding(base, grounding_kind=None, evidence=base["observation"]["evidence"]),   # control: with evidence, it is fine
    )
    assert verdicts == {"text_span_kind": False, "absent_kind": False, "plain_text_finding": True}


def test_a_merged_block_observation_is_covered_too(
    openapi_document: dict[str, Any], finding_payload: dict[str, Any], validate: Any
) -> None:
    """``merged_observations`` is a list of the same schema: the rule is the observation's, wherever it sits."""
    block = _block_finding(finding_payload)
    parent = copy.deepcopy(finding_payload)
    parent["merged_observations"] = [block["observation"]]
    broken = copy.deepcopy(parent)
    broken["merged_observations"] = [_block_finding(finding_payload, grounding_kind=None)["observation"]]
    assert _verdicts(validate, openapi_document, "Finding", merged_block=parent, merged_text_without_evidence=broken) == {
        "merged_block": True, "merged_text_without_evidence": False}


def test_the_observation_stays_closed(
    openapi_document: dict[str, Any], finding_payload: dict[str, Any], unknown_property: str, validate: Any
) -> None:
    """A rule that bought the empty array by loosening the object would pass the two tests above and fail here."""
    body = _block_finding(finding_payload)
    body["observation"][unknown_property] = "x"
    assert _verdicts(validate, openapi_document, "Finding", smuggled=body) == {"smuggled": False}


def test_the_contract_before_1_52_0_refuses_the_block_observation_this_one_accepts(
    openapi_document: dict[str, Any], finding_payload: dict[str, Any], validate: Any
) -> None:
    """The guard's own proof: run the block finding through the rebuilt 1.51.0 document and it is refused, which is the defect `D-683` pinned."""
    body = _block_finding(finding_payload)
    assert _verdicts(validate, _before_1_52_0(openapi_document), "Finding", block=body) == {"block": False}
    assert _verdicts(validate, openapi_document, "Finding", block=body) == {"block": True}


def test_the_evidence_property_no_longer_carries_the_minimum_but_the_rule_does(openapi_document: dict[str, Any]) -> None:
    observation = openapi_document["components"]["schemas"]["FindingObservation"]
    assert "minItems" not in observation["properties"]["evidence"] and "evidence" in observation["required"]
    assert observation["if"] == {"properties": {"grounding_kind": {"const": "portal_block"}}, "required": ["grounding_kind"]}
    assert observation["else"] == {"properties": {"evidence": {"minItems": 1}}}
    assert observation["additionalProperties"] is False and "then" not in observation


@pytest.mark.parametrize("model_name", ["Finding", "FindingDetail"])
def test_the_contracts_own_models_accept_a_block_observation_and_refuse_the_rest(
    finding_detail_payload: dict[str, Any], finding_payload: dict[str, Any], model_name: str
) -> None:
    """The Pydantic side, which is what the served document and the adapters' tests validate with."""
    model = getattr(models, model_name)
    base = finding_payload if model_name == "Finding" else finding_detail_payload

    accepted = model.model_validate(_block_finding(base))
    assert accepted.observation.evidence == [] and accepted.observation.grounding_kind is models.FindingGroundingKind.PORTAL_BLOCK
    assert [block.portal_block_id for block in accepted.block_evidence] == [BLOCK]

    for refused in (_block_finding(base, grounding_kind="text_span"), _block_finding(base, grounding_kind=None)):
        with pytest.raises(pydantic.ValidationError, match="evidence needs at least one item unless grounding_kind is portal_block"):
            model.model_validate(refused)
    assert model.model_validate(_block_finding(base, grounding_kind=None, evidence=base["observation"]["evidence"]))   # control


# --- D-682: the comments of a memory case ---------------------------------------------------------------------------------------------------


def _case(**extra: Any) -> dict[str, Any]:
    """A case as a forgotten one is answered (no content, empty lists): the shortest valid body."""
    summary = {
        "case_id": f"dmc_{ULID}", "category": "dimensions", "section_code": None, "data_class": "test", "crop_state": "none_available",
        "origin_project_uid": f"prj_{ULID}", "captured_at": "2026-11-11T09:00:00Z", "status": "active", "status_reason_code": None,
        "status_changed_at": None, "current_verdict": "accepted", "current_severity": None, "current_origin_kind": "direct",
        "current_decided_at": "2026-11-11T09:00:00Z", "decision_count": 1,
    }
    return {"summary": summary, "content": None, "decisions": [], "evidence": [], "norm_refs": [], "crops": [], "status_events": [], **extra}


def _comment(**changes: Any) -> dict[str, Any]:
    return {"comment_id": f"dmk_{ULID}", "decided_at": "2026-11-11T09:05:00Z", "comment": "Согласовано с автором проекта.", **changes}


def test_a_case_may_carry_comments_and_may_not() -> None:
    assert models.DecisionMemoryCase.model_validate(_case()).comments is None                       # absent: the server does not report them
    assert models.DecisionMemoryCase.model_validate(_case(comments=[])).comments == []              # present and empty: none
    case = models.DecisionMemoryCase.model_validate(_case(comments=[_comment(), _comment(comment_id=f"dmk_{ULID[:-1]}N")]))
    assert [item.comment_id for item in case.comments] == [f"dmk_{ULID}", f"dmk_{ULID[:-1]}N"]


def test_the_comments_are_optional_in_the_contract_and_the_comment_has_no_author(openapi_document: dict[str, Any]) -> None:
    schemas = openapi_document["components"]["schemas"]
    case = schemas["DecisionMemoryCase"]
    assert "comments" in case["properties"] and "comments" not in case["required"]
    assert case["properties"]["comments"]["items"] == {"$ref": "#/components/schemas/DecisionMemoryComment"}
    comment = schemas["DecisionMemoryComment"]
    assert set(comment["properties"]) == {"comment_id", "decided_at", "comment"} == set(comment["required"])
    assert comment["additionalProperties"] is False and "author_user_uid" not in comment["properties"]
    assert comment["properties"]["comment_id"]["pattern"] == "^dmk_[0-9A-HJKMNP-TV-Z]{26}$"


def test_a_comment_names_no_author_and_keeps_its_identity_and_length(openapi_document: dict[str, Any], validate: Any) -> None:
    verdicts = _verdicts(
        validate, openapi_document, "DecisionMemoryCase",
        with_comments=_case(comments=[_comment()]),
        without_comments=_case(),
        with_author=_case(comments=[_comment(author_user_uid=f"usr_{ULID}")]),            # the memory names nobody
        decision_identity=_case(comments=[_comment(comment_id=f"dmd_{ULID}")]),           # a comment is a ``dmk``, not a decision
        empty_text=_case(comments=[_comment(comment="")]),
        too_long=_case(comments=[_comment(comment="x" * 4001)]),
        longest=_case(comments=[_comment(comment="x" * 4000)]),                           # the database's own bound, 1 to 4000
        missing_time=_case(comments=[{key: value for key, value in _comment().items() if key != "decided_at"}]),
    )
    assert verdicts == {
        "with_comments": True, "without_comments": True, "with_author": False, "decision_identity": False, "empty_text": False,
        "too_long": False, "longest": True, "missing_time": False,
    }


def test_the_models_refuse_what_the_schema_refuses() -> None:
    for refused in (_comment(author_user_uid=f"usr_{ULID}"), _comment(comment_id=f"dmd_{ULID}"), _comment(comment=""), _comment(comment="x" * 4001)):
        with pytest.raises(pydantic.ValidationError):
            models.DecisionMemoryComment.model_validate(refused)
    with pytest.raises(pydantic.ValidationError):
        models.DecisionMemoryCase.model_validate(_case(comments=[_comment(author_user_uid=f"usr_{ULID}")]))


def test_the_db_bound_of_a_comment_is_the_contracts() -> None:
    """The table's CHECK (``char_length(comment) BETWEEN 1 AND 4000``, migration ``0064``) and the schema's bound are one number."""
    migration = (ROOT / "db/migrations/versions/20261110_0064_precedents_seal.py").read_text(encoding="utf-8")
    assert "CHECK (char_length(comment) BETWEEN 1 AND 4000)" in migration
    schema = models.DecisionMemoryComment.model_json_schema()["properties"]["comment"]
    assert (schema["minLength"], schema["maxLength"]) == (1, 4000)
