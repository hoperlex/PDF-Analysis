"""A response schema that needs the provider-safe wire form: ``oneOf`` and every value constraint a strict provider refuses.

A stand-in for the sealed schemas the wire-form tests used to take from a profile that is no longer in the product. It
carries ``oneOf``, ``minLength``, ``maxLength``, ``minimum``, ``maxItems`` and ``pattern``, keeps ``minItems`` of one in three
places, and names its closed categories in ``enum``, so the wire-form tests have something that really changes.
"""

from __future__ import annotations

from typing import Any

PLAIN_CATEGORIES = ("dimensions", "layout", "facade")
NORMATIVE_CATEGORIES = ("evacuation", "fire_safety")


def _evidence() -> dict[str, Any]:
    return {
        "type": "array", "minItems": 1,
        "items": {
            "type": "object", "additionalProperties": False, "required": ["page_number", "quote"],
            "properties": {
                "page_number": {"type": "integer", "minimum": 1},
                "quote": {"type": "string", "minLength": 1, "maxLength": 2000},
            },
        },
    }


def _proposal(categories: tuple[str, ...], extra: dict[str, Any]) -> dict[str, Any]:
    """Every property is required, as the strict providers want it."""
    properties = {
        "category": {"type": "string", "enum": list(categories)},
        "finding_text": {"type": "string", "minLength": 1, "maxLength": 4000},
        "recommendation_text": {"type": "string", "minLength": 1, "maxLength": 4000},
        "proposed_severity": {"type": "string", "enum": ["critical", "operational", "economic"]},
        "evidence": _evidence(),
        **extra,
    }
    return {"type": "object", "additionalProperties": False, "required": list(properties), "properties": properties}


def one_of_response_schema() -> dict[str, Any]:
    """A fresh tree every call: a test may mutate its copy."""
    citations = {
        "type": "array", "minItems": 1, "maxItems": 5,
        "items": {
            "type": "object", "additionalProperties": False, "required": ["label", "quote"],
            "properties": {
                "label": {"type": "string", "pattern": "^N[1-9][0-9]?$"},
                "quote": {"type": "string", "minLength": 20, "maxLength": 4000},
            },
        },
    }
    return {
        "type": "object", "additionalProperties": False, "required": ["observations"],
        "properties": {
            "observations": {
                "type": "array",
                "items": {"oneOf": [
                    _proposal(PLAIN_CATEGORIES, {}),
                    _proposal(
                        NORMATIVE_CATEGORIES,
                        {
                            "norm_citations": citations,
                            "required_value": {"type": "string", "minLength": 1, "maxLength": 200},
                            "stated_value": {"type": "string", "minLength": 1, "maxLength": 200},
                        },
                    ),
                ]},
            },
        },
    }
