"""A four-page PDF whose text lines cross the places a portal would cut its blocks (D-353). Not product code.

The synthetic «Пояснительная записка» and the АР baseline keep each line inside one block. A drawing set's specification
tables, a stamp's label/value rows and two-column text do not: the extractor joins words that stand side by side at one height
into ONE line with one space for any gap, so the line spans the gap and every block that stands on either side of it. This PDF
has exactly those, in volume, with real text and a real text layer (reportlab, deterministic):

* page 1: a schedule of 40 rows, three columns at x 56, 150 and 430 pt;
* page 2: running text in two columns (x 56 and x 310 pt), 40 lines each on the same baselines;
* page 3: 40 label/value rows, the label at x 56 pt, the value at x 360 pt;
* page 4: 40 rows of a wide left column (a long sentence on the odd rows, a short «Итого n» label on the even ones, so the
  column's block is wide) next to a phrase at x 330 pt: the judge's label / gap / phrase line (J3 F1), in volume.

The leading (13 pt for 10 pt text) is that of running text: the rows are not separated by white bands, so a raster XY-cut finds
the COLUMNS as blocks, as a portal does for a page of columns. Every phrase is unique on its page, so a quotation of any part of it
resolves to one place.
"""

from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)
ROWS = 40
TOP = 800.0
LEADING = 13.0
SIZE = 10.0

_WORDS = ("плита", "балка", "колонна", "перемычка", "ригель", "панель", "стойка", "связь", "опора", "анкер")
_MATERIALS = ("бетон B25", "сталь С255", "кирпич М100", "пенобетон D600", "дерево сосна", "алюминий АД31")


def font_path() -> str:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError("no Cyrillic TrueType font on this host: " + ", ".join(FONT_CANDIDATES))


def build() -> bytes:
    pdfmetrics.registerFont(TTFont("StressSans", font_path()))
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4, invariant=True)
    page.setFont("StressSans", SIZE)

    def row(index: int, texts: tuple[tuple[float, str], ...]) -> None:
        y = TOP - index * LEADING
        for x, text in texts:
            page.drawString(x, y, text)

    # Page 1: a schedule.
    page.setFont("StressSans", 14)
    page.drawString(56, 820, "Ведомость элементов конструкций")
    page.setFont("StressSans", SIZE)
    for n in range(1, ROWS + 1):
        row(n, (
            (56, f"Поз. {n}"),
            (150, f"{_WORDS[n % len(_WORDS)]} {n}-{_MATERIALS[n % len(_MATERIALS)]}, марка К{n:02d}"),
            (430, f"{n * 7 + 3} шт."),
        ))
    page.showPage()
    page.setFont("StressSans", SIZE)

    # Page 2: two columns of running text on shared baselines.
    for n in range(1, ROWS + 1):
        row(n, (
            (56, f"Левая колонка, строка {n}: узел {n * 3} крепят болтами."),
            (310, f"Правая колонка, строка {n}: зазор {n + 11} мм не менее."),
        ))
    page.showPage()
    page.setFont("StressSans", SIZE)

    # Page 3: label / value rows.
    for n in range(1, ROWS + 1):
        row(n, (
            (56, f"Показатель {n}: {_WORDS[(n * 3) % len(_WORDS)]} типа {n}"),
            (360, f"{n * 113 + 17},{n % 10} {('м²', 'м³', 'кг', 'шт.')[n % 4]}"),
        ))
    page.showPage()
    page.setFont("StressSans", SIZE)

    # Page 4: a wide left column with short labels on every other row, and a phrase far to the right.
    for n in range(1, ROWS + 1):
        left = f"Пояснение {n}: {_WORDS[n % len(_WORDS)]} воспринимает нагрузку {n * 2} кН." if n % 2 else f"Итого {n}"
        row(n, ((56, left), (330, f"Огнестойкость узла {n} — не менее R{30 + n}.")))
    page.showPage()
    page.save()
    return buffer.getvalue()
