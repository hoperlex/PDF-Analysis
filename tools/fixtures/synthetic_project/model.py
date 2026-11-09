"""What a section document is made of: pages with drawing operations, block regions, and an answer key.

A section module (`sec_<code>.py`) exposes `build() -> SectionDoc`. The renderer adds the frame and
the title block to every page, writes the PDF, derives the portal blocks (TEXT from the text anchored
inside each text region, IMAGE from the declared drawing regions) and checks every answer-key quote
against the PDF's own text layer (pypdfium2, as the product reads it).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from comparison import scene

from .kit import Ops

A4 = scene.A4
A3L = scene.landscape(scene.A3)
A2L = scene.landscape(scene.A2)

# The area free for content on a page: inside the frame, above the title block (points).
def content_box(size: tuple[float, float]) -> tuple[float, float, float, float]:
    w, h = size
    return (scene.FRAME_LEFT + 6, scene.FRAME_OTHER + scene.STAMP_H + 6, w - scene.FRAME_OTHER - 6, h - scene.FRAME_OTHER - 6)


Box = tuple[float, float, float, float]  # x0, y0, x1, y1 in points, lower-left origin


@dataclass(frozen=True)
class ImageRegion:
    """A drawing region the portal recognised as IMAGE; the product crops it from the PDF page."""

    box: Box
    drawing_type: str                 # «План», «Схема», «Разрез», «Аксонометрия», «Генплан», «Узел»...
    axes: tuple[str, ...]             # axis labels visible in it, e.g. ("1", "7", "А", "Г"); () if none
    summary: str                      # one sentence
    description: str                  # two or three sentences: what is drawn
    entities: tuple[str, ...]         # labels a reader sees in it (equipment marks, room numbers)


@dataclass
class Page:
    title: str                        # the sheet title in the title block («Общие данные», «План ... »)
    size: tuple[float, float]
    ops: Ops
    text_regions: list[Box] = field(default_factory=list)
    images: list[ImageRegion] = field(default_factory=list)


@dataclass(frozen=True)
class Quote:
    page: int                         # 1-based page number
    text: str                         # an exact substring of ONE text line on that page


@dataclass(frozen=True)
class Expected:
    """A finding a correct analysis of the section should report."""

    id: str
    category: str                     # internal_contradiction | explicit_placeholder | documentation
    summary: str                      # Russian, one sentence: what disagrees with what
    quotes: tuple[Quote, ...]


@dataclass(frozen=True)
class Trap:
    """A place that looks like a finding and is not one (the profile's no-finding conditions)."""

    id: str
    why: str                          # Russian: which no-finding condition applies
    quotes: tuple[Quote, ...]


@dataclass
class SectionDoc:
    code: str                         # contract section code: AR, AI, KM, KJ, OV, EOM, VK, PT, PB, SS, ITP, GP, TX, POS, PS
    abbr: str                         # Russian abbreviation: АР, АИ, КМ, КЖ, ОВ, ЭОМ, ВК, ПТ, ПБ, СС, ИТП, ГП, ТХ, ПОС, ПЗ
    name: str                         # the section name as the product shows it
    pages: list[Page]
    expected: list[Expected]
    traps: list[Trap] = field(default_factory=list)
    stage: str = "Р"
    date: str = "15.10.2026"
    revision: str = "Изм.0"

    @property
    def designation(self) -> str:
        return f"СИНТ-02-{self.abbr}"
