"""Every member of a result that has a schema in the contract is checked before a row is written.

`CMP-ENGINE-01`, wave brief section 4 item 3: ``canvas``, ``differences``, ``text_changes``, ``service_notes``,
``how_compared`` and the channels are validated by a model of the contract's schema, with the caps of the schemas
(2000 differences, 2000 text changes, 500 service notes). A result that does not fit is a defect of the engine: it is
refused here and never stored.

**The models are restated here, not imported from ``api/schemas/models.py``.** Those are the models the API serialises
with, generated from ``contracts/api/v1/openapi.json``, but ``api`` is another context and ``api.schemas.models`` is not
a public module (``tests/contract/architecture/test_alr05_boundaries.py`` refuses the import, as ``runs`` and
``dashboard`` restate theirs for the same reason). The restatement is held to the generated models by
``tests/unit/comparison/engine/test_restated_models.py``: the JSON schema of each class equals the generated class's
(titles and descriptions apart), and a set of valid and invalid members is accepted or refused by both alike, so a change
of the contract turns that test red and this file is the side that has to move.
"""

from __future__ import annotations

import enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

__all__ = ["ResultInvalid", "validate_outcome"]


class ResultInvalid(ValueError):
    """The engine produced something the contract does not allow."""


class _Object(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ComparisonChannelState(str, enum.Enum):
    CHECKED = "checked"
    UNCHECKED = "unchecked"
    NOT_APPLICABLE = "not_applicable"


class ComparisonChannel(_Object):
    state: ComparisonChannelState
    diffs: Annotated[int, Field(ge=0)] = Field(default=None)  # type: ignore[assignment]
    reason: Annotated[str, Field(min_length=1, max_length=128)] = Field(default=None)  # type: ignore[assignment]


class ComparisonChannels(_Object):
    geometry: ComparisonChannel = Field(default=None)  # type: ignore[assignment]
    color: ComparisonChannel = Field(default=None)  # type: ignore[assignment]
    text: ComparisonChannel = Field(default=None)  # type: ignore[assignment]
    text_coverage: ComparisonChannel = Field(default=None)  # type: ignore[assignment]
    zones: ComparisonChannel = Field(default=None)  # type: ignore[assignment]
    annotations: ComparisonChannel = Field(default=None)  # type: ignore[assignment]
    warnings: ComparisonChannel = Field(default=None)  # type: ignore[assignment]
    spec_positions: ComparisonChannel = Field(default=None)  # type: ignore[assignment]


class ComparisonLayer(str, enum.Enum):
    MAIN = "main"
    LIGHT_ELEMENTS = "light_elements"
    COLOR_CHANGE = "color_change"
    LINE_STYLE = "line_style"
    MOVED = "moved"
    WITHIN_TOLERANCE = "within_tolerance"
    NOISE = "noise"
    SERVICE_ZONES = "service_zones"


class ComparisonBox(_Object):
    x: float
    y: float
    width: Annotated[float, Field(ge=0)]
    height: Annotated[float, Field(ge=0)]


class ComparisonDifference(_Object):
    region_class: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")]
    layer: ComparisonLayer
    box: ComparisonBox
    before_text: Annotated[str, Field(min_length=1, max_length=2000)] = Field(default=None)  # type: ignore[assignment]
    after_text: Annotated[str, Field(min_length=1, max_length=2000)] = Field(default=None)  # type: ignore[assignment]


class ComparisonNumberChange(_Object):
    before: Annotated[str, Field(min_length=1, max_length=64)]
    after: Annotated[str, Field(min_length=1, max_length=64)]


class ComparisonTextChange(_Object):
    kind: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")]
    before: Annotated[str, Field(min_length=1, max_length=2000)] = Field(default=None)  # type: ignore[assignment]
    after: Annotated[str, Field(min_length=1, max_length=2000)] = Field(default=None)  # type: ignore[assignment]
    numbers: list[ComparisonNumberChange] = Field(default=None)  # type: ignore[assignment]
    box: ComparisonBox = Field(default=None)  # type: ignore[assignment]


class ComparisonNoteChange(str, enum.Enum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


class ComparisonServiceNote(_Object):
    kind: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")]
    change: ComparisonNoteChange
    zone: Annotated[str, Field(min_length=1, max_length=64)] = Field(default=None)  # type: ignore[assignment]
    field: Annotated[str, Field(min_length=1, max_length=64)] = Field(default=None)  # type: ignore[assignment]
    before: Annotated[str, Field(min_length=1, max_length=2000)] = Field(default=None)  # type: ignore[assignment]
    after: Annotated[str, Field(min_length=1, max_length=2000)] = Field(default=None)  # type: ignore[assignment]


class ComparisonHowCompared(_Object):
    algo_version: Annotated[str, Field(min_length=1, max_length=64)]
    dpi: Annotated[int, Field(ge=1)]
    tolerance_pt: Annotated[float, Field(ge=0)]
    transform: Annotated[list[float], Field(min_length=6, max_length=6)] = Field(default=None)  # type: ignore[assignment]
    within_tolerance_count: Annotated[int, Field(ge=0)] = Field(default=None)  # type: ignore[assignment]
    noise_count: Annotated[int, Field(ge=0)] = Field(default=None)  # type: ignore[assignment]
    separated_objects: Annotated[int, Field(ge=0)] = Field(default=None)  # type: ignore[assignment]
    aligned_blocks: Annotated[int, Field(ge=0)] = Field(default=None)  # type: ignore[assignment]


class ComparisonCanvas(_Object):
    width_pt: Annotated[float, Field(gt=0)]
    height_pt: Annotated[float, Field(gt=0)]


#: The restated classes, by the name of the contract's schema (the parity test walks this).
MODELS: dict[str, type[BaseModel]] = {
    cls.__name__: cls
    for cls in (
        ComparisonChannel, ComparisonChannels, ComparisonBox, ComparisonDifference, ComparisonNumberChange,
        ComparisonTextChange, ComparisonServiceNote, ComparisonHowCompared, ComparisonCanvas,
    )
}
CAPS = {"differences": 2000, "text_changes": 2000, "service_notes": 500}


def validate_outcome(channels: dict[str, Any], result: dict[str, Any]) -> None:
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
    for name, cap in CAPS.items():
        if len(result[name]) > cap:
            raise ResultInvalid(f"{name} passes the cap of its schema")
    if result.get("format") != 1:
        raise ResultInvalid("the format of the result is not 1")
