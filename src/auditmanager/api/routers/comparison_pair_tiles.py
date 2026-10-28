"""One tile of a sheet pair's overlay or of one of its pages, sealed as a stub (`CMP-SEAL-C1`,
ADR-0025 decision 9).

``streamComparisonPairTile`` answers a PNG addressed by ``mode`` (``overlay``, ``a`` or ``b``),
``level``, ``column`` and ``row``; ``layers`` (a comma-separated list of layer names) chooses the difference layers of an
overlay and ``align_blocks`` aligns the recognised blocks of the newer page onto the older one
without changing the PDF. The API never loads PDFium: it reduces what the worker stored. Any one
role. Answers ``503 dependency_unavailable`` until `CMP-VIEWER-01` wires the port.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Path, Query

from auditmanager.api.routers.declarations import envelope_responses, success
from auditmanager.api.routers.ports import ComparisonPairTilePort
from auditmanager.api.routers.version_pages import MAX_TILE_INDEX, MAX_TILE_LEVEL
from auditmanager.api.routers.wire import WireResponse
from auditmanager.api.schemas import models

__all__ = ["build_comparison_pair_tile_routes"]

_PNG: Final[str] = "image/png"
_TAGS: Final[list[str]] = ["comparison"]
_PNG_CONTENT = {_PNG: {"schema": {"type": "string", "format": "binary"}}}
#: The layers of an overlay as one query value: layer names from :class:`models.ComparisonLayer`, separated by commas
#: (the generated client carries a query value as a scalar, so the list is one string).
_LAYER_NAMES = "|".join(layer.value for layer in models.ComparisonLayer)
_LAYERS_PATTERN = rf"^({_LAYER_NAMES})(,({_LAYER_NAMES})){{0,7}}$"


def _parse_layers(value: str | None) -> tuple[models.ComparisonLayer, ...]:
    """The distinct layers the query names, in the order named; the pattern has already refused any other word."""
    if not value:
        return ()
    return tuple(dict.fromkeys(models.ComparisonLayer(name) for name in value.split(",")))


def build_comparison_pair_tile_routes(router: APIRouter, tiles: ComparisonPairTilePort) -> None:
    @router.get(
        "/comparison-sheet-pairs/{comparison_sheet_pair_id}/tile",
        operation_id="streamComparisonPairTile", tags=_TAGS, status_code=200,
        response_class=WireResponse,
        responses={**success(200, "One tile PNG of the pair.", content=_PNG_CONTENT),
                   **envelope_responses(401, 403, 404, 422, 500, 503)},
    )
    def stream_comparison_pair_tile(
        comparison_sheet_pair_id: Annotated[models.ComparisonSheetPairId, Path()],
        mode: Annotated[models.ComparisonPairTileMode, Query()],
        level: Annotated[int, Query(ge=0, le=MAX_TILE_LEVEL)],
        column: Annotated[int, Query(ge=0, le=MAX_TILE_INDEX)],
        row: Annotated[int, Query(ge=0, le=MAX_TILE_INDEX)],
        layers: Annotated[str, Query(pattern=_LAYERS_PATTERN, max_length=160)] = None,  # type: ignore[assignment]
        align_blocks: Annotated[bool, Query()] = False,
    ) -> WireResponse:
        content = tiles.read_tile(
            sheet_pair_id=comparison_sheet_pair_id, mode=mode, level=level, column=column,
            row=row, layers=_parse_layers(layers), align_blocks=align_blocks,
        )
        return WireResponse(
            200, (("Content-Type", _PNG), ("Content-Length", str(len(content)))), content
        )
