"""The stage layout: the six rows, the sets, the validation and the plan a run freezes (`HOSTS-LAYOUT-01`, ADR-0028 decisions 5, 10-12).

This module is pure: no database, no clock, no environment. It is the single definition of

* the closed tuple of **rows** an administrator sees (:data:`STAGE_ROWS`) and the **phase dictionary** that maps every code phase to
  one of them (:data:`PHASE_ROWS`, :data:`PHASE_LABELS`; the web takes its labels from the same place);
* the **sets** « Только Claude » and « Только Codex », model · effort exactly as ADR-0028 decision 12 and plan section 4.3 print them,
  and the rule that anything else an administrator saves is « Свой набор »;
* the **block schemes**, a closed list: the legs and the judge of an ensemble are never edited one by one, and the block row is one of
  the listed schemes or nothing. The list is the two ensembles of the sets (legs and a judge, ``HOSTS-ENSEMBLE-01``) and a single
  Astra, which the original allows; a single Claude is never on it;
* the **validation** of a layout against the catalogue (``contracts/analysis/v1/model-catalogue.json``): only a pair the file offers,
  never a Haiku, an effort above ``high`` or ``low`` for Opus;
* the **plan** (:class:`FrozenStagePlan`): the cells of a layout revision with the access chosen for each model when a run starts, its
  JSON form (what ``audit_run.stage_plan`` stores) and its digest;
* the **comparison cells** (`HOSTS-CMP-01`, ADR-0028 decision 19): one cell ``<kind>:main`` for each of the four kinds of the version
  comparison that call a model (:data:`COMPARISON_KINDS`), with the same two settings as a row. They are part of a layout revision and
  of no run: a run's plan holds the six rows only (:func:`rows_in_use`), and a comparison job freezes its cell when it starts.

A cell is a **model and an effort** (and, in a plan, an access). Since `LIMITS-01` (`R-153n`, `R-153o`) it has no answer limit and no
timeout of its own: no answer cap reaches a model, and a call's timeout is the code constant of its row or kind
(``analysis.text.cell_settings``). A layout revision stored before that carries the two old numbers per cell; they are **not read**.

Nothing here decides a model from a model's output (``AGENTS.md`` section 4): a model and an effort come from the stored layout, the
access from the availability the stand reads at the start.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Final, Iterable, Mapping, Sequence

from auditmanager.analysis.public import CellSettings, COMPARISON_TIMEOUT_SECONDS, ModelCatalogue, model_catalogue
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "BLOCK_SCHEMES", "BLOCKS_ENSEMBLE_LANDED", "BlockScheme", "CELL_ROLES", "COMPARISON_KINDS", "COMPARISON_LABELS", "COMPARISON_PRESET_CELLS", "ENSEMBLE_ROLES",
    "ENSEMBLE_ROW", "FrozenStagePlan", "ROLE_ORDER", "KITS", "KIT_CLAUDE_ONLY",
    "KIT_CODEX_ONLY", "KIT_CUSTOM", "KIT_LABELS", "MODELLESS_PHASES", "PHASE_ALIASES", "PHASE_LABELS", "PHASE_ROWS", "PLAN_FORMAT", "PRESET_CELLS",
    "ROW_LABELS", "ROW_PHASES", "STAGE_ROWS", "cell_key", "cells_to_wire", "kit_of", "parse_plan", "preset_cells", "require_valid_layout",
    "comparison_cell_key", "comparison_cells_in_force", "comparison_cells_to_wire", "comparison_preset_cells", "require_valid_comparison_cells",
    "role_of_phase", "row_of_phase", "rows_in_use", "validate_cells", "validate_comparison_cells",
]

#: The six rows, in the order the owner sees them. ``git grep -n "STAGE_ROWS" -- src`` is the totality query of this set.
STAGE_ROWS: Final[tuple[str, ...]] = ("text", "blocks", "cross_check", "norms", "review", "correction")

ROW_LABELS: Final[Mapping[str, str]] = {
    "text": "Анализ текста", "blocks": "Анализ блоков", "cross_check": "Комплексная сверка", "norms": "Нормы",
    "review": "Критик", "correction": "Уточнение",
}

#: The roles of a cell: the single answer of a row, and the two legs and the judge of the blocks ensemble (ADR-0028 decision 11).
CELL_ROLES: Final[tuple[str, ...]] = ("main", "leg1", "leg2", "judge")
#: The order a row's cells are kept in: ``main``, the legs, the judge.
ROLE_ORDER: Final[Mapping[str, int]] = {role: position for position, role in enumerate(CELL_ROLES)}
#: Every row has one ``main`` cell, except the blocks row, which is one of the :data:`BLOCK_SCHEMES` (an ensemble has no ``main``).
ENSEMBLE_ROW: Final[str] = "blocks"
ENSEMBLE_ROLES: Final[tuple[str, ...]] = ("leg1", "leg2", "judge")

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


def role_of_phase(phase: str) -> str:
    """The role of the cell a call identity runs on: ``leg1``, ``leg2`` or ``judge`` for ``blocks:3:leg1`` (and for its semantic repair
    ``blocks:3:leg1:repair:1``, which runs on the cell it repairs), else ``main``. Only the blocks identities of an ensemble carry a role."""
    parts = phase.split(":")
    if len(parts) >= 3 and PHASE_ALIASES.get(parts[0], parts[0]) == "block_analysis" and parts[2] in ENSEMBLE_ROLES:
        return parts[2]
    return "main"


def cell_key(row: str, role: str = "main") -> str:
    return f"{row}:{role}"


# --- the sets -----------------------------------------------------------------------------------------------------------------

KIT_CLAUDE_ONLY: Final[str] = "claude_only"
KIT_CODEX_ONLY: Final[str] = "codex_only"
KIT_CUSTOM: Final[str] = "custom"
KITS: Final[tuple[str, ...]] = (KIT_CLAUDE_ONLY, KIT_CODEX_ONLY, KIT_CUSTOM)

#: ``True`` once ``HOSTS-ENSEMBLE-01`` has landed: the blocks row is then two legs and a judge (one leg and a judge for the Claude set).
#: Before it the Claude set ran blocks on one model and said so in its name (plan sections 4.3 and 4.6); production waited for the ensemble.
BLOCKS_ENSEMBLE_LANDED: Final[bool] = True

KIT_LABELS: Final[Mapping[str, str]] = {
    KIT_CLAUDE_ONLY: "Только Claude" if BLOCKS_ENSEMBLE_LANDED else "Только Claude (блоки без судьи)",
    KIT_CODEX_ONLY: "Только Codex",
    KIT_CUSTOM: "Свой набор",
}

_OPUS, _SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
_SOL61, _SOL, _ASTRA, _LUNA = "gpt-6.1-sol", "gpt-6-sol", "gpt-6-astra", "gpt-6-luna"


@dataclass(frozen=True, slots=True)
class BlockScheme:
    """One entry of the closed list a blocks row is chosen from: the (role, model, effort) triples that make it up, in role order.

    A scheme with a ``judge`` is an ensemble: each leg reads the block batch alone, then the judge reads the batch again with the legs'
    observations, reconciles the legs (one leg has nothing to compare with) and searches for what they missed (``gap_search``).
    """

    scheme_id: str
    label: str
    cells: tuple[tuple[str, str, str], ...]

    @property
    def roles(self) -> tuple[str, ...]:
        return tuple(role for role, _, _ in self.cells)

    @property
    def legs(self) -> tuple[str, ...]:
        """The roles that read the batch alone: ``leg1`` and ``leg2``, or ``main`` for a single model."""
        return tuple(role for role in self.roles if role != "judge")

    @property
    def is_ensemble(self) -> bool:
        return "judge" in self.roles


#: The closed list of block schemes (plan section 4.3, ADR-0028 decisions 11 and 12). The Claude ensemble is one leg and a judge
#: (the original's ``claude_only`` mode: a second Opus leg adds mostly medium findings); the Codex ensemble is two legs and a judge. A single
#: Astra stays: the original allows it. A single Claude is not on the list and never will be (the original forbids it, ``config.py:734-741``).
BLOCK_SCHEMES: Final[tuple[BlockScheme, ...]] = (
    BlockScheme("claude_opus_judge_sonnet", "Opus 5.5 · medium + судья Sonnet 5.5 · medium, с поиском пропусков",
                (("leg1", _OPUS, "medium"), ("judge", _SONNET, "medium"))),
    BlockScheme("codex_astra_sol_judge", "gpt-6-astra · medium + gpt-6-sol · medium, судья gpt-6.1-sol · medium, с поиском пропусков",
                (("leg1", _ASTRA, "medium"), ("leg2", _SOL, "medium"), ("judge", _SOL61, "medium"))),
    BlockScheme("codex_astra_single", "gpt-6-astra · medium", (("main", _ASTRA, "medium"),)),
)

#: Model · effort of every row of each set, exactly the table of ADR-0028 decision 12 / plan section 4.3: row -> the (role, model, effort)
#: of its cells. A row has one ``main`` cell; the blocks row is the scheme of the set.
PRESET_CELLS: Final[Mapping[str, Mapping[str, tuple[tuple[str, str, str], ...]]]] = {
    KIT_CLAUDE_ONLY: {
        "text": (("main", _SONNET, "medium"),), "blocks": BLOCK_SCHEMES[0].cells, "cross_check": (("main", _SONNET, "medium"),),
        "norms": (("main", _SONNET, "medium"),), "review": (("main", _SONNET, "medium"),), "correction": (("main", _SONNET, "medium"),),
    },
    KIT_CODEX_ONLY: {
        "text": (("main", _SOL61, "medium"),), "blocks": BLOCK_SCHEMES[1].cells, "cross_check": (("main", _SOL, "medium"),),
        "norms": (("main", _ASTRA, "medium"),), "review": (("main", _SOL, "medium"),), "correction": (("main", _SOL61, "medium"),),
    },
}
if any(table["blocks"] not in {scheme.cells for scheme in BLOCK_SCHEMES} for table in PRESET_CELLS.values()):  # pragma: no cover
    raise AssertionError("the blocks row of a set is a listed scheme")


def preset_cells(kit: str) -> tuple[CellSettings, ...]:
    """The cells of a set, in row order and, inside a row, in role order (``main``, the legs, the judge). ``custom`` has no table: it is
    whatever was saved."""
    table = PRESET_CELLS.get(kit)
    if table is None:
        raise ValueError("only the two sets have a table of cells")
    return tuple(
        CellSettings(cell_key=cell_key(row, role), model_id=model, effort=effort)
        for row in STAGE_ROWS for role, model, effort in table[row]
    )


def _position(cell: CellSettings) -> tuple[int, int]:
    """Where a cell stands in a layout: its row, then its role."""
    return (STAGE_ROWS.index(cell.row) if cell.row in STAGE_ROWS else len(STAGE_ROWS), ROLE_ORDER.get(cell.role, len(ROLE_ORDER)))


def _model_effort(cells: Iterable[CellSettings]) -> tuple[tuple[str, str, str], ...]:
    return tuple((cell.cell_key, cell.model_id, cell.effort) for cell in cells)


def kit_of(cells: Sequence[CellSettings]) -> str:
    """The set whose model · effort table the cells follow exactly, else « Свой набор »."""
    mine = _model_effort(sorted(cells, key=_position))
    for kit in (KIT_CLAUDE_ONLY, KIT_CODEX_ONLY):
        if mine == _model_effort(preset_cells(kit)):
            return kit
    return KIT_CUSTOM


# --- validation ---------------------------------------------------------------------------------------------------------------

def _invalid(constraint: str, field: str = "cells") -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint)


def validate_cells(cells: Sequence[CellSettings], *, catalogue: ModelCatalogue | None = None) -> tuple[CellSettings, ...]:
    """Check a layout and return its cells in row order (and, inside a row, in role order), or raise ``validation_failed`` naming the first
    thing wrong.

    * every cell key is ``row:role`` of a known row and an offered role, none repeated: a row has a ``main`` cell, and only the blocks row
      may hold ``leg1``, ``leg2`` and ``judge`` instead;
    * every row has its cells: ``row:main`` for each row but blocks, and the cells of one scheme for blocks;
    * every (model, effort) pair is one the catalogue offers (so never a Haiku, ``xhigh``, ``max`` or Opus ``low``);
    * the blocks row is one scheme of the closed list, whole, and its roles are the scheme's: the legs and the judge are not edited
      one by one;
    A cell is a model and an effort: it has no limit or timeout to range-check (`LIMITS-01`).
    """
    catalogue = catalogue or model_catalogue()
    by_key: dict[str, CellSettings] = {}
    for cell in cells:
        row, separator, role = cell.cell_key.partition(":")
        if not separator or row not in STAGE_ROWS or role not in CELL_ROLES:
            raise _invalid("unknown_cell")
        if row != ENSEMBLE_ROW and role != "main":
            raise _invalid("role_not_offered")
        if cell.cell_key in by_key:
            raise _invalid("cell_repeated")
        by_key[cell.cell_key] = cell
    if any(cell_key(row) not in by_key for row in STAGE_ROWS if row != ENSEMBLE_ROW) or not any(
            cell.row == ENSEMBLE_ROW for cell in by_key.values()):
        raise _invalid("cell_missing")
    ordered = tuple(sorted(by_key.values(), key=_position))
    for cell in ordered:
        catalogue.require_pair(cell.model_id, cell.effort)
    if tuple((cell.role, cell.model_id, cell.effort) for cell in ordered if cell.row == ENSEMBLE_ROW) not in {
            scheme.cells for scheme in BLOCK_SCHEMES}:
        raise _invalid("block_scheme_not_listed")
    return ordered


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
    """The JSON of a layout cell (``StageLayoutCell``): what the revision stores and the API returns -- the key, the row and role it names,
    the model and the effort. A revision stored before `LIMITS-01` holds two more members per cell; they are never written again."""
    return [
        {"cell_key": cell.cell_key, "row": cell.row, "role": cell.role, "model_id": cell.model_id, "effort": cell.effort}
        for cell in cells
    ]


# --- the comparison cells -----------------------------------------------------------------------------------------------------
# `HOSTS-CMP-01` (ADR-0028 decision 19). The four kinds of work of the version comparison that call a model are served by the same
# system groups as the analysis. A kind has one cell ``<kind>:main`` (model, effort), kept in the layout revision
# beside the six rows and never in a run's plan. ``comparison_stage_review`` is not here: it is an enum value with no handler (`CMP-SEAL-C4`).

#: The kinds of comparison work a cell is chosen for, in the order the owner sees them. ``git grep -n "COMPARISON_KINDS" -- src`` is the
#: totality query of this set; the work kinds are ``executors.model.WORK_KINDS``.
COMPARISON_KINDS: Final[tuple[str, ...]] = (
    "comparison_pair_check", "comparison_sheet_changes", "comparison_spec", "comparison_report",
)
COMPARISON_LABELS: Final[Mapping[str, str]] = {
    "comparison_pair_check": "Проверка пар листов", "comparison_sheet_changes": "Описание изменений листов",
    "comparison_spec": "Сравнение спецификаций", "comparison_report": "Отчёт по сравнению версий",
}
# The call window of each kind is a code constant, ``analysis.text.cell_settings.COMPARISON_TIMEOUT_SECONDS`` (the original's values), and a
# comparison call has no answer limit: the estimate counts the figure of the module that makes the call (`LIMITS-01`, `R-153n`).
#: Model · effort of every kind of each set (the original's models mapped onto the catalogue: its ``sheet_match`` and its whole-specification
#: comparison run on ``gpt-6-luna``, a pin since `R-153m` / `D-667`). The Claude set serves all four on Sonnet.
COMPARISON_PRESET_CELLS: Final[Mapping[str, Mapping[str, tuple[str, str]]]] = {
    KIT_CLAUDE_ONLY: {kind: (_SONNET, "high") for kind in COMPARISON_KINDS},
    KIT_CODEX_ONLY: {
        "comparison_pair_check": (_LUNA, "high"), "comparison_sheet_changes": (_SOL61, "high"),
        "comparison_spec": (_LUNA, "high"), "comparison_report": (_SOL61, "high"),
    },
}
if any(set(table) != set(COMPARISON_KINDS) for table in COMPARISON_PRESET_CELLS.values()) or any(
        set(table) != set(COMPARISON_KINDS) for table in (COMPARISON_LABELS, COMPARISON_TIMEOUT_SECONDS)):  # pragma: no cover
    raise AssertionError("every comparison kind has a label, a timeout and a cell in each set")


def comparison_cell_key(kind: str) -> str:
    return cell_key(kind)


def comparison_preset_cells(kit: str) -> tuple[CellSettings, ...]:
    """The comparison cells of a set, in the order of :data:`COMPARISON_KINDS`."""
    table = COMPARISON_PRESET_CELLS.get(kit)
    if table is None:
        raise ValueError("only the two sets have a table of comparison cells")
    return tuple(
        CellSettings(cell_key=comparison_cell_key(kind), model_id=table[kind][0], effort=table[kind][1])
        for kind in COMPARISON_KINDS
    )


def comparison_cells_in_force(kit: str, stored: Sequence[CellSettings] | None) -> tuple[CellSettings, ...] | None:
    """The comparison cells a revision of ``kit`` that stored ``stored`` serves with. A revision with no stored list (made before the cells
    existed, or saved without them) follows the table of its set; « Свой набор » has no table, so its comparison kinds have **no cell** and
    a comparison is then refused rather than served by a model nobody chose (``None``)."""
    if stored:
        return tuple(sorted(stored, key=lambda cell: COMPARISON_KINDS.index(cell.row) if cell.row in COMPARISON_KINDS else len(COMPARISON_KINDS)))
    return comparison_preset_cells(kit) if kit in PRESET_CELLS else None


def validate_comparison_cells(
    cells: Sequence[CellSettings], *, catalogue: ModelCatalogue | None = None,
) -> tuple[CellSettings, ...]:
    """Check the comparison cells of a layout and return them in the order of :data:`COMPARISON_KINDS`, or raise ``validation_failed``
    (field ``comparison_cells``): a cell is ``<kind>:main`` of a known kind and appears once; every kind has its cell; every (model, effort)
    pair is one the catalogue offers."""
    catalogue = catalogue or model_catalogue()
    by_key: dict[str, CellSettings] = {}
    for cell in cells:
        kind, separator, role = cell.cell_key.partition(":")
        if not separator or kind not in COMPARISON_KINDS:
            raise _invalid("unknown_cell", "comparison_cells")
        if role != "main":
            raise _invalid("role_not_offered", "comparison_cells")
        if cell.cell_key in by_key:
            raise _invalid("cell_repeated", "comparison_cells")
        by_key[cell.cell_key] = cell
    if any(comparison_cell_key(kind) not in by_key for kind in COMPARISON_KINDS):
        raise _invalid("cell_missing", "comparison_cells")
    ordered = tuple(by_key[comparison_cell_key(kind)] for kind in COMPARISON_KINDS)
    for cell in ordered:
        catalogue.require_pair(cell.model_id, cell.effort, field="comparison_cells")
    return ordered


def require_valid_comparison_cells(
    kit: str, cells: Sequence[CellSettings], *, catalogue: ModelCatalogue | None = None,
) -> tuple[CellSettings, ...]:
    """:func:`validate_comparison_cells` plus the rule that a named set is that set: the models and efforts of the comparison cells of
    « Только Codex » are its table's. ``kit`` itself is judged by
    :func:`require_valid_layout`."""
    ordered = validate_comparison_cells(cells, catalogue=catalogue)
    if kit in PRESET_CELLS and _model_effort(ordered) != _model_effort(comparison_preset_cells(kit)):
        raise _invalid("kit_does_not_match_cells", "kit")
    return ordered


def comparison_cells_to_wire(cells: Iterable[CellSettings]) -> list[dict[str, Any]]:
    """The JSON of a comparison cell (``StageComparisonCell``): what the API returns. The kind is the cell key's row."""
    return [{"work_kind": cell.row, "model_id": cell.model_id, "effort": cell.effort} for cell in cells]


# --- the plan -----------------------------------------------------------------------------------------------------------------

PLAN_FORMAT: Final[str] = "stage-plan/1"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True, slots=True)
class FrozenStagePlan:
    """The cells a run froze at its start: model, effort and access, from one layout revision.

    ``access`` is a property of the **model** in the plan, not of a cell: one model is bought one way for the whole run, so the consent
    (a map model -> rate digest and access) and the plan agree by construction.
    """

    layout_revision_id: str
    kit: str
    cells: tuple[CellSettings, ...]
    #: The digest of the document a plan was read back from when that document is the one a run froze **before** `LIMITS-01`: it carried
    #: an answer limit and a timeout per cell, so its canonical form -- the form the owner's consent approved -- is not :meth:`to_json`'s
    #: any more. ``None`` for every plan written since (its digest is computed from :meth:`to_json`).
    frozen_digest: str | None = field(default=None, compare=False)

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
        """The document ``audit_run.stage_plan`` stores. Each cell carries exactly ``cell_key`` (``<row>:<role>``), ``model_id``, ``effort`` and
        ``access``: the row and the role are the key's, and the readers (the database trigger of the cell binding, ``getRunStages``) take them
        from it. The database requires only the key and the model of a cell (migration ``0062``), so the answer limit and the timeout a plan
        carried before `LIMITS-01` need no migration to go."""
        return {
            "format": PLAN_FORMAT, "layout_revision_id": self.layout_revision_id, "kit": self.kit,
            "cells": [
                {"cell_key": cell.cell_key, "model_id": cell.model_id, "effort": cell.effort, "access": cell.access}
                for cell in self.cells
            ],
        }

    @property
    def digest(self) -> str:
        """What the consent approved: the digest of this plan's document -- of the document it was read from, for a plan frozen before
        `LIMITS-01` (:attr:`frozen_digest`), so a run in flight at the upgrade is not refused as « changed »."""
        if self.frozen_digest is not None:
            return self.frozen_digest
        return hashlib.sha256(_canonical(self.to_json()).encode("utf-8")).hexdigest()

    def cell(self, key: str) -> CellSettings:
        for cell in self.cells:
            if cell.cell_key == key:
                return cell
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="cell_not_in_plan")

    def has_cell(self, key: str) -> bool:
        return any(cell.cell_key == key for cell in self.cells)

    def cells_of_row(self, row: str) -> tuple[CellSettings, ...]:
        """The cells of one row in role order: one ``main`` cell, or the legs and the judge of the blocks ensemble."""
        return tuple(sorted((cell for cell in self.cells if cell.row == row), key=_position))

    def roles_of_row(self, row: str) -> tuple[str, ...]:
        return tuple(cell.role for cell in self.cells_of_row(row))

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


#: The two members a cell of a plan (and of a layout revision) carried before `LIMITS-01`. They are read from nothing now: a run's call window is
#: the row's constant whatever the plan froze.
_LEGACY_CELL_MEMBERS: Final[tuple[str, str]] = ("max_output_tokens", "timeout_seconds")


def parse_plan(document: object) -> FrozenStagePlan:
    """Read ``audit_run.stage_plan`` back. A document that is not exactly what :meth:`FrozenStagePlan.to_json` writes is refused: a
    run whose plan cannot be read calls nothing.

    The one other shape read is the plan of a run frozen before `LIMITS-01`: the same cells with an answer limit and a timeout each. A cell
    must then carry **both** members (a half-old cell is refused), they are dropped unread, and the plan keeps the digest of the document the
    consent approved (:attr:`FrozenStagePlan.frozen_digest`). A run in flight at the upgrade finishes under it; the call window it runs with
    is the row's constant, not the number the old plan froze."""
    try:
        if not isinstance(document, Mapping) or document.get("format") != PLAN_FORMAT:
            raise ValueError("format")
        raw_cells = document["cells"]
        legacy = [item for item in raw_cells if isinstance(item, Mapping) and any(name in item for name in _LEGACY_CELL_MEMBERS)]
        if legacy and (len(legacy) != len(raw_cells) or any(name not in item for item in legacy for name in _LEGACY_CELL_MEMBERS)):
            raise ValueError("legacy shape")
        cells = tuple(
            CellSettings(
                cell_key=str(item["cell_key"]), model_id=str(item["model_id"]), effort=str(item["effort"]), access=str(item["access"]),
            )
            for item in raw_cells
        )
        plan = FrozenStagePlan(
            str(document["layout_revision_id"]), str(document["kit"]), cells,
            frozen_digest=hashlib.sha256(_canonical(document).encode("utf-8")).hexdigest() if legacy else None,
        )
        current = {**document, "cells": [{k: v for k, v in item.items() if k not in _LEGACY_CELL_MEMBERS} for item in raw_cells]}
        if _canonical(plan.to_json()) != _canonical(current):
            raise ValueError("shape")
        return plan
    except (KeyError, TypeError, ValueError):
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="the run's stage plan is invalid") from None
