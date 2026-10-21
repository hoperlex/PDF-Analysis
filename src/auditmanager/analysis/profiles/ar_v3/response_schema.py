"""Closed, pure AR v3 model-proposal shape; independent of served API types.

The normative fields are model claims, not verified citations. A later profile
must content-bind this schema to its reviewed prompt and qualified set.
"""

from __future__ import annotations

from typing import Any, Final


NONNORMATIVE_CATEGORIES: Final[tuple[str, ...]] = (
    "internal_contradiction",
    "explicit_placeholder",
    "dimensions",
    "layout",
    "facade",
    "roof",
    "documentation",
)
NORMATIVE_CATEGORIES: Final[tuple[str, ...]] = (
    "evacuation",
    "fire_safety",
    "accessibility",
    "insulation",
    "sound",
)
CATEGORIES: Final[tuple[str, ...]] = NONNORMATIVE_CATEGORIES + NORMATIVE_CATEGORIES
SEVERITIES: Final[tuple[str, ...]] = (
    "critical",
    "economic",
    "operational",
    "recommendation",
    "check_adjacent",
)


def _observation(*, normative: bool) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "category": {
            "type": "string",
            "enum": list(NORMATIVE_CATEGORIES if normative else NONNORMATIVE_CATEGORIES),
        },
        "finding_text": {"type": "string", "minLength": 1, "maxLength": 4000},
        "recommendation_text": {"type": "string", "minLength": 1, "maxLength": 4000},
        "proposed_severity": {"type": "string", "enum": list(SEVERITIES)},
        "evidence": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "page_number": {"type": "integer", "minimum": 1},
                    "quote": {"type": "string", "minLength": 1, "maxLength": 2000},
                },
                "required": ["page_number", "quote"],
                "additionalProperties": False,
            },
        },
    }
    required = list(properties)
    if normative:
        properties.update({
            "norm_citations": {
                "type": "array",
                "minItems": 1,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "pattern": "^N[1-9][0-9]*$"},
                        "quote": {"type": "string", "minLength": 20, "maxLength": 1000},
                    },
                    "required": ["label", "quote"],
                    "additionalProperties": False,
                },
            },
            "required_value": {"type": "string", "minLength": 1, "maxLength": 200},
            "stated_value": {"type": "string", "minLength": 1, "maxLength": 200},
        })
        required.extend(("norm_citations", "required_value", "stated_value"))
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def response_schema() -> dict[str, Any]:
    """Return a fresh tree; callers cannot mutate the frozen proposal policy."""
    return {
        "type": "object",
        "properties": {
            "observations": {
                "type": "array",
                "items": {"oneOf": [_observation(normative=False), _observation(normative=True)]},
            },
        },
        "required": ["observations"],
        "additionalProperties": False,
    }
