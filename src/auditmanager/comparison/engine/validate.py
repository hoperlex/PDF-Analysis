"""Every member of a result that has a schema in the contract is checked by the generated model before a row is written.

`CMP-ENGINE-01`, wave brief section 4 item 3: ``canvas``, ``differences``, ``text_changes``, ``service_notes``,
``how_compared`` and the channels. The models are those the API serialises with (``api/schemas/models.py``, generated
from ``contracts/api/v1/openapi.json``); a result that does not fit them is a defect of the engine, and it is refused
here and never stored (the caps of the schemas hold: 2000 differences, 2000 text changes, 500 service notes).
"""

from __future__ import annotations

from typing import Any

__all__ = ["ResultInvalid", "validate_outcome"]


class ResultInvalid(ValueError):
    """The engine produced something the contract does not allow."""


def validate_outcome(channels: dict[str, Any], result: dict[str, Any]) -> None:
    from pydantic import ValidationError

    from auditmanager.api.schemas.models import (
        ComparisonCanvas,
        ComparisonChannels,
        ComparisonDifference,
        ComparisonHowCompared,
        ComparisonServiceNote,
        ComparisonTextChange,
    )

    try:
        ComparisonChannels(**channels)
        ComparisonCanvas(**result["canvas"])
        ComparisonHowCompared(**result["how_compared"])
        for item in result["differences"]:
            ComparisonDifference(**item)
        for item in result["text_changes"]:
            ComparisonTextChange(**item)
        for item in result["service_notes"]:
            ComparisonServiceNote(**item)
    except ValidationError as failure:
        raise ResultInvalid(str(failure)[:400]) from failure
    if len(result["differences"]) > 2000 or len(result["text_changes"]) > 2000 or len(result["service_notes"]) > 500:
        raise ResultInvalid("a list of the result passes the cap of its schema")
    if result.get("format") != 1:
        raise ResultInvalid("the format of the result is not 1")
