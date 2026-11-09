"""The stage layout: the six rows, the sets, the validation and the plan a run freezes (`HOSTS-LAYOUT-01`, ADR-0028 decisions 5, 10-12).

This module is pure: no database, no clock, no environment. It is the single definition of

* the closed tuple of **rows** an administrator sees (:data:`STAGE_ROWS`) and the **phase dictionary** that maps every code phase to
  one of them (:data:`PHASE_ROWS`, :data:`PHASE_LABELS`; the web takes its labels from the same place);
* the **sets** « Только Claude » and « Только Codex », model · effort exactly as ADR-0028 decision 12 and plan section 4.3 print them,
  and the rule that anything else an administrator saves is « Свой набор »;
* the **block schemes**, a closed list: the legs and the judge of an ensemble are never edited one by one, and the block row is one of
  the listed schemes or nothing. Until the ensemble lands (``HOSTS-ENSEMBLE-01``) the only schemes are the two temporary single
  models the two sets carry;
* the **validation** of a layout against the catalogue (``contracts/analysis/v1/model-catalogue.json``): only a pair the file offers,
  never a Haiku, an effort above ``high`` or ``low`` for Opus;
* the **plan** (:class:`FrozenStagePlan`): the cells of a layout revision with the access chosen for each model when a run starts, its
  JSON form (what ``audit_run.stage_plan`` stores) and its digest.

Nothing here decides a model from a model's output (``AGENTS.md`` section 4): a model, an effort and a limit come from the stored
layout, the access from the availability the stand reads at the start.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Final, Iterable, Mapping, Sequence

from auditmanager.analysis.public import (
    CellSettings, DEFAULT_TIMEOUT_SECONDS, ModelCatalogue, ROW_DEFAULT_MAX_OUTPUT_TOKENS, model_catalogue,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "BLOCK_SCHEMES", "BLOCKS_ENSEMBLE_LANDED", "BlockScheme", "CELL_ROLES", "FrozenStagePlan", "KITS", "KIT_CLAUDE_ONLY",
    "KIT_CODEX_ONLY", "KIT_CUSTOM", "KIT_LABELS", "MODELLESS_PHASES", "PHASE_ALIASES", "PHASE_LABELS", "PHASE_ROWS", "PLAN_FORMAT", "PRESET_CELLS",
    "ROW_LABELS", "ROW_PHASES", "STAGE_ROWS", "cell_key", "cells_to_wire", "kit_of", "parse_plan", "preset_cells", "require_valid_layout",
    "row_of_phase", "rows_in_use", "validate_cells",
]

#: The six rows, in the order the owner sees them. ``git grep -n "STAGE_ROWS" -- src`` is the totality query of this set.
STAGE_ROWS: Final[tuple[str, ...]] = ("text", "blocks", "cross_check", "norms", "review", "correction")

ROW_LABELS: Final[Mapping[str, str]] = {
    "text": "Анализ текста", "blocks": "Анализ блоков", "cross_check": "Комплексная сверка", "norms": "Нормы",
    "review": "Критик", "correction": "Уточнение",
}

#: The roles of a cell. This wave offers ``main`` only: the legs and the judge of an ensemble belong to ``HOSTS-ENSEMBLE-01``.
CELL_ROLES: Final[tuple[str, ...]] = ("main", "leg1", "leg2", "judge")
_OFFERED_ROLES: Final[tuple[str, ...]] = ("main",)

#: Code phase -> row. A phase is what the code runs; a row is what the owner sees. ``text_analysis`` is the PC-01 stage; the others
#: are the procedures of the extended review (``phase_call_limits`` of the coverage policy) and the parameter passport.
PHASE_ROWS: Final[Mapping[str, str]] = {
    "text_analysis": "text",
    "block_analysis": "blocks",
    "comprehensive_analysis": "cross_check",
    "project_parameters": "cross_check",
    "norm_verification": "norms",
    "finding_review": "review",
    "finding_correction": "correction",
}
#: The inverse, row -> its phases in the order of ``PHASE_ROWS``.
ROW_PHASES: Final[Mapping[str, tuple[str, ...]]] = {
    row: tuple(phase for phase, owner in PHASE_ROWS.items() if owner == row) for row in STAGE_ROWS
}
#: Phases that run no model; their tiles on the rail show none (ADR-0028 decision 10).
MODELLESS_PHASES: Final[tuple[str, ...]] = (
    "source_preparation", "page_geometry_extraction", "document_context_build", "merge", "norm_citation_check", "report",
)
#: The one label of every phase, for the whole application.
PHASE_LABELS: Final[Mapping[str, str]] = {
    "text_analysis": "Анализ текста", "block_analysis": "Анализ блоков", "comprehensive_analysis": "Комплексная сверка",
    "project_parameters": "Паспорт параметров", "norm_verification": "Нормы", "finding_review": "Критик",
    "finding_correction": "Уточнение", "source_preparation": "Подготовка источника",
    "page_geometry_extraction": "Геометрия страниц", "document_context_build": "Контекст документа", "merge": "Свод",
    "norm_citation_check": "Сверка цитат норм", "report": "Отчёт",
}
if set(PHASE_ROWS) & set(MODELLESS_PHASES) or set(PHASE_ROWS) | set(MODELLESS_PHASES) != set(PHASE_LABELS):  # pragma: no cover
    raise AssertionError("every phase has one label and a phase is either with a model or without")


#: The names the call identities of the extended review use for the phases above (``blocks:3``, ``comprehensive``, ``critic``,
#: ``corrector``): the same phase, spelled as the workflow spells its calls.
PHASE_ALIASES: Final[Mapping[str, str]] = {
    "blocks": "block_analysis", "comprehensive": "comprehensive_analysis", "critic": "finding_review",
    "corrector": "finding_correction",
}


def row_of_phase(phase: str) -> str | None:
    """The row a phase belongs to. An identity like ``blocks:3`` or ``norm_verification:b002`` is read by the name before the colon (and the
    workflow's own aliases are resolved); a phase without a model, like ``merge``, has none."""
    name = phase.partition(":")[0]
    return PHASE_ROWS.get(PHASE_ALIASES.get(name, name))


def cell_key(row: str, role: str = "main") -> str:
    return f"{row}:{role}"


# --- the sets -----------------------------------------------------------------------------------------------------------------

KIT_CLAUDE_ONLY: Final[str] = "claude_only"
KIT_CODEX_ONLY: Final[str] = "codex_only"
KIT_CUSTOM: Final[str] = "custom"
KITS: Final[tuple[str, ...]] = (KIT_CLAUDE_ONLY, KIT_CODEX_ONLY, KIT_CUSTOM)

#: ``True`` once ``HOSTS-ENSEMBLE-01`` has landed: the blocks row is then two legs and a judge. Until then the Claude set runs blocks on
#: one model and says so in its name (plan sections 4.3 and 4.6).
BLOCKS_ENSEMBLE_LANDED: Final[bool] = False

KIT_LABELS: Final[Mapping[str, str]] = {
    KIT_CLAUDE_ONLY: "Только Claude" if BLOCKS_ENSEMBLE_LANDED else "Только Claude (блоки без судьи)",
    KIT_CODEX_ONLY: "Только Codex",
    KIT_CUSTOM: "Свой набор",
}

_OPUS, _SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
_SOL61, _SOL, _ASTRA = "gpt-6.1-sol", "gpt-6-sol", "gpt-6-astra"

#: Model · effort of every row of each set, exactly the table of ADR-0028 decision 12 / plan section 4.3. The blocks entry is the
#: temporary single model of this wave (the original allows it; the Claude set's leg is Opus 5.5 · medium, the Codex set's is Astra).
PRESET_CELLS: Final[Mapping[str, Mapping[str, tuple[str, str]]]] = {
    KIT_CLAUDE_ONLY: {
        "text": (_SONNET, "medium"), "blocks": (_OPUS, "medium"), "cross_check": (_SONNET, "medium"),
        "norms": (_SONNET, "medium"), "review": (_SONNET, "medium"), "correction": (_SONNET, "medium"),
    },
    KIT_CODEX_ONLY: {
        "text": (_SOL61, "medium"), "blocks": (_ASTRA, "medium"), "cross_check": (_SOL, "medium"),
        "norms": (_ASTRA, "medium"), "review": (_SOL, "medium"), "correction": (_SOL61, "medium"),
    },
}


@dataclass(frozen=True, slots=True)
class BlockScheme:
    """One entry of the closed list a blocks row is chosen from: the (role, model, effort) triples that make it up."""

    scheme_id: str
    label: str
    cells: tuple[tuple[str, str, str], ...]


#: The closed list of block schemes of this wave: the temporary single model of each set. The ensembles (leg + leg + judge) join it in
#: ``HOSTS-ENSEMBLE-01``; a single Claude Sonnet is not on it and never will be (the original forbids it, ``config.py:734-741``).
BLOCK_SCHEMES: Final[tuple[BlockScheme, ...]] = (
    BlockScheme("claude_opus_single", "Opus 5.5 · medium (без судьи)", (("main", _OPUS, "medium"),)),
    BlockScheme("codex_astra_single", "gpt-6-astra · medium", (("main", _ASTRA, "medium"),)),
)


def preset_cells(kit: str) -> tuple[CellSettings, ...]:
    """The cells of a set with the default answer limits and timeout. ``custom`` has no table: it is whatever was saved."""
    table = PRESET_CELLS.get(kit)
    if table is None:
        raise ValueError("only the two sets have a table of cells")
    return tuple(
        CellSettings(cell_key=cell_key(row), model_id=table[row][0], effort=table[row][1],
                     max_output_tokens=ROW_DEFAULT_MAX_OUTPUT_TOKENS[row], timeout_seconds=DEFAULT_TIMEOUT_SECONDS)
        for row in STAGE_ROWS
    )


def _model_effort(cells: Iterable[CellSettings]) -> tuple[tuple[str, str, str], ...]:
    return tuple((cell.cell_key, cell.model_id, cell.effort) for cell in cells)


def kit_of(cells: Sequence[CellSettings]) -> str:
    """The set whose model · effort table the cells follow exactly, else « Свой набор ». Limits and timeouts are not part of a set: an
    administrator who only lengthens a timeout still has the set's models, and the kit says so."""
    ordered = sorted(cells, key=lambda cell: STAGE_ROWS.index(cell.row) if cell.row in STAGE_ROWS else len(STAGE_ROWS))
    mine = _model_effort(ordered)
    for kit in (KIT_CLAUDE_ONLY, KIT_CODEX_ONLY):
        if mine == _model_effort(preset_cells(kit)):
            return kit
    return KIT_CUSTOM


# --- validation ---------------------------------------------------------------------------------------------------------------

def _invalid(constraint: str, field: str = "cells") -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint)


def validate_cells(cells: Sequence[CellSettings], *, catalogue: ModelCatalogue | None = None) -> tuple[CellSettings, ...]:
    """Check a layout and return its cells in row order, or raise ``validation_failed`` naming the first thing wrong.

    * every cell key is ``row:role`` of a known row and an offered role, none repeated, none missing: exactly the six ``row:main``;
    * every (model, effort) pair is one the catalogue offers (so never a Haiku, ``xhigh``, ``max`` or Opus ``low``);
    * the blocks row is one scheme of the closed list, whole;
    * a limit and a timeout are integers inside the wire's bounds.
    """
    catalogue = catalogue or model_catalogue()
    by_key: dict[str, CellSettings] = {}
    for cell in cells:
        row, separator, role = cell.cell_key.partition(":")
        if not separator or row not in STAGE_ROWS or role not in CELL_ROLES:
            raise _invalid("unknown_cell")
        if role not in _OFFERED_ROLES:
            raise _invalid("role_not_offered")
        if cell.cell_key in by_key:
            raise _invalid("cell_repeated")
        by_key[cell.cell_key] = cell
    if any(cell_key(row) not in by_key for row in STAGE_ROWS):
        raise _invalid("cell_missing")
    for key in (cell_key(row) for row in STAGE_ROWS):
        cell = by_key[key]
        catalogue.require_pair(cell.model_id, cell.effort)
        if (type(cell.max_output_tokens) is not int or not 1 <= cell.max_output_tokens <= 65_536
                or type(cell.timeout_seconds) is not int or not 1 <= cell.timeout_seconds <= 7_200):
            raise _invalid("limit_out_of_range")
    blocks = tuple((cell.role, cell.model_id, cell.effort) for cell in cells if cell.row == "blocks")
    if blocks not in {scheme.cells for scheme in BLOCK_SCHEMES}:
        raise _invalid("block_scheme_not_listed")
    return tuple(by_key[cell_key(row)] for row in STAGE_ROWS)


def require_valid_layout(
    kit: str, cells: Sequence[CellSettings], *, catalogue: ModelCatalogue | None = None,
) -> tuple[CellSettings, ...]:
    """:func:`validate_cells` plus the rule that a named set is that set: a request for « Только Claude » whose models differ from the
    table is refused (``kit_does_not_match_cells``) rather than stored under a name it does not deserve."""
    ordered = validate_cells(cells, catalogue=catalogue)
    if kit not in KITS:
        raise _invalid("unknown_kit", "kit")
    if kit != KIT_CUSTOM and kit_of(ordered) != kit:
        raise _invalid("kit_does_not_match_cells", "kit")
    return ordered


def cells_to_wire(cells: Iterable[CellSettings]) -> list[dict[str, Any]]:
    """The JSON of a layout cell (``StageLayoutCell``): what the revision stores and the API returns."""
    return [
        {"cell_key": cell.cell_key, "row": cell.row, "role": cell.role, "model_id": cell.model_id, "effort": cell.effort,
         "max_output_tokens": cell.max_output_tokens, "timeout_seconds": cell.timeout_seconds}
        for cell in cells
    ]


# --- the plan -----------------------------------------------------------------------------------------------------------------

PLAN_FORMAT: Final[str] = "stage-plan/1"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True, slots=True)
class FrozenStagePlan:
    """The cells a run froze at its start: model, effort, answer limit, timeout and access, from one layout revision.

    ``access`` is a property of the **model** in the plan, not of a cell: one model is bought one way for the whole run, so the consent
    (a map model -> rate digest and access) and the plan agree by construction.
    """

    layout_revision_id: str
    kit: str
    cells: tuple[CellSettings, ...]

    def __post_init__(self) -> None:
        if not self.cells:
            raise ValueError("a plan has at least one cell")
        access: dict[str, str | None] = {}
        for cell in self.cells:
            if cell.access not in {"subscription", "api"}:
                raise ValueError("every cell of a plan carries its access")
            if access.setdefault(cell.model_id, cell.access) != cell.access:
                raise ValueError("one model is served one way in a plan")
        if len({cell.cell_key for cell in self.cells}) != len(self.cells):
            raise ValueError("a cell appears once in a plan")

    def to_json(self) -> dict[str, Any]:
        return {
            "format": PLAN_FORMAT, "layout_revision_id": self.layout_revision_id, "kit": self.kit,
            "cells": [{**wire, "access": cell.access} for wire, cell in zip(cells_to_wire(self.cells), self.cells)],
        }

    @property
    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_json()).encode("utf-8")).hexdigest()

    def cell(self, key: str) -> CellSettings:
        for cell in self.cells:
            if cell.cell_key == key:
                return cell
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="cell_not_in_plan")

    def has_cell(self, key: str) -> bool:
        return any(cell.cell_key == key for cell in self.cells)

    @property
    def rows(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(cell.row for cell in self.cells))

    @property
    def models(self) -> tuple[str, ...]:
        """The distinct models in cell order."""
        return tuple(dict.fromkeys(cell.model_id for cell in self.cells))

    def access_of(self, model_id: str) -> str:
        for cell in self.cells:
            if cell.model_id == model_id:
                return str(cell.access)
        raise KeyError(model_id)

    @property
    def access(self) -> str:
        """The total: ``subscription``, ``api`` or ``mixed``."""
        kinds = {cell.access for cell in self.cells}
        return str(kinds.pop()) if len(kinds) == 1 else "mixed"

    def restricted_to(self, rows: Iterable[str]) -> "FrozenStagePlan":
        """The same plan with only the cells of ``rows``: a run binds and pays for the cells it will call (ADR-0028 decision 5)."""
        wanted = set(rows)
        return FrozenStagePlan(self.layout_revision_id, self.kit, tuple(cell for cell in self.cells if cell.row in wanted))


def rows_in_use(extended_review: Mapping[str, Any] | None) -> tuple[str, ...]:
    """The rows a run will call, from the extended-review plan its consent holds (``None``: the text analysis alone).

    The ``extended-review-v2`` plan has no critic and no refinement (ADR-0028 decision 10, column « План »); v3 has all six.
    """
    if not isinstance(extended_review, Mapping) or extended_review.get("enabled") is not True:
        return ("text",)
    if extended_review.get("plan_version") == "extended-review-v3":
        return STAGE_ROWS
    return ("text", "blocks", "cross_check", "norms")


def parse_plan(document: object) -> FrozenStagePlan:
    """Read ``audit_run.stage_plan`` back. A document that is not exactly what :meth:`FrozenStagePlan.to_json` writes is refused: a
    run whose plan cannot be read calls nothing."""
    try:
        if not isinstance(document, Mapping) or document.get("format") != PLAN_FORMAT:
            raise ValueError("format")
        cells = tuple(
            CellSettings(
                cell_key=str(item["cell_key"]), model_id=str(item["model_id"]), effort=str(item["effort"]),
                max_output_tokens=int(item["max_output_tokens"]), timeout_seconds=int(item["timeout_seconds"]),
                access=str(item["access"]),
            )
            for item in document["cells"]
        )
        plan = FrozenStagePlan(str(document["layout_revision_id"]), str(document["kit"]), cells)
        if _canonical(plan.to_json()) != _canonical(document):
            raise ValueError("shape")
        return plan
    except (KeyError, TypeError, ValueError):
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="the run's stage plan is invalid") from None
