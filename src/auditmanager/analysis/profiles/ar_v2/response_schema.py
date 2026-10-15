"""Pure AR v2 provider response shape, pending profile and stage wiring.

The two enums are sealed by W56A-SEAL-01. This schema describes only model
proposals. It carries no finding identity, anchor offset or expert verdict.
"""

from __future__ import annotations

from typing import Any, Final


CATEGORIES: Final[tuple[str, ...]] = (
    "internal_contradiction",
    "explicit_placeholder",
    "dimensions",
    "layout",
    "facade",
    "roof",
    "documentation",
)

SEVERITIES: Final[tuple[str, ...]] = (
    "critical",
    "economic",
    "operational",
    "recommendation",
    "check_adjacent",
)


def response_schema() -> dict[str, Any]:
    """Build an independent JSON Schema tree for one v2 prompt bundle."""
    return {
        "type": "object",
        "properties": {
            "observations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": list(CATEGORIES)},
                        "finding_text": {"type": "string", "minLength": 1, "maxLength": 4000},
                        "recommendation_text": {
                            "type": "string", "minLength": 1, "maxLength": 4000
                        },
                        "proposed_severity": {"type": "string", "enum": list(SEVERITIES)},
                        "evidence": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "page_number": {"type": "integer", "minimum": 1},
                                    "quote": {"type": "string", "minLength": 1},
                                },
                                "required": ["page_number", "quote"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": [
                        "category", "finding_text", "recommendation_text",
                        "proposed_severity", "evidence",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["observations"],
        "additionalProperties": False,
    }
