"""Build `w28_own_document.pdf` -- a second synthetic AR document, for `W28-LIVE`.

`W28-LIVE` had to measure what a person gets when they upload **their own** PDF: a
document the recorded corpus has never seen. `fixtures/synthetic/ar/ar_baseline.pdf` is
the one document with a recording, so it is exactly the wrong instrument for that
question -- its request checksum hits `fixtures/recorded/text_analysis/` and the run
replays. Every negative fixture under `fixtures/synthetic/ar/negative/` violates one
envelope rule on purpose, so none of them is a valid upload either.

So: a valid document that is not the baseline. Same generator, same embedded font subset,
same fixed metadata, no clock and no PRNG -- the bytes are deterministic. It is shorter
than the baseline (three pages), it says different things, and it carries one deliberate
internal contradiction so that a real analysis has something true to find.

It deliberately lives here and NOT in `fixtures/synthetic/ar/`: that corpus is sealed,
enumerated by contract tests and hashed into `SHA256SUMS`, and `W28-LIVE` owns no slot in
it. This is a driver fixture for one measurement, under `tests/e2e/**`.

    python3 tests/e2e/pc01/journey/fixtures/w28-live/make_document.py

Writes `w28_own_document.pdf` beside this file and prints its size and sha256.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
sys.path.insert(0, str(REPO / "tools" / "fixtures"))

from ar_corpus import content, document, pdfwrite  # noqa: E402

sys.path.insert(0, str(REPO / "tools"))
from fixtures.build_ar_corpus import load_font  # noqa: E402

H1 = 13.0
H2 = 11.5
BODY = 10.5
SMALL = 9.0

FOOTER = "СП-9-АР    Лист {page}    Синтетический документ W28"

# (text, size, centred?) -- one tuple per drawn line; "" is a blank advance.
PAGES: tuple[tuple[tuple[str, float, bool], ...], ...] = (
    (
        ("ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «СИНТЕТИКПРОЕКТ»", H2, True),
        ("вымышленная организация; реальному юридическому лицу не соответствует", SMALL, True),
        ("", BODY, False),
        ("", BODY, False),
        ("Объект: пристроенное здание детского сада на 120 мест", BODY, True),
        ("Условная площадка № 9, квартал СП-9", BODY, True),
        ("", BODY, False),
        ("", BODY, False),
        ("ПРОЕКТНАЯ ДОКУМЕНТАЦИЯ", H1, True),
        ("Раздел 3. Архитектурные решения", H2, True),
        ("", BODY, False),
        ("Шифр СП-9-АР", BODY, True),
        ("", BODY, False),
        ("", BODY, False),
        ("Документ синтетический. Не является проектной документацией", SMALL, True),
        ("и не описывает реальный объект капитального строительства.", SMALL, True),
    ),
    (
        ("1. Общие данные", H1, False),
        ("", BODY, False),
        ("1.1. Настоящий раздел разработан на основании задания на проектирование", BODY, False),
        ("и содержит архитектурные решения пристроенного здания детского сада.", BODY, False),
        ("", BODY, False),
        ("1.2. Класс функциональной пожарной опасности здания — Ф1.1.", BODY, False),
        ("", BODY, False),
        ("1.3. Степень огнестойкости здания — II.", BODY, False),
        ("", BODY, False),
        ("1.4. Количество надземных этажей — 2. Подвал не предусмотрен.", BODY, False),
        ("", BODY, False),
        ("1.5. Высота здания от планировочной отметки земли до низа проёмов", BODY, False),
        ("верхнего этажа составляет 6,6 м.", BODY, False),
        ("", BODY, False),
        ("2. Объёмно-планировочные решения", H1, False),
        ("", BODY, False),
        ("2.1. Здание прямоугольное в плане, с размерами в осях 36,0 × 18,0 м.", BODY, False),
        ("", BODY, False),
        ("2.2. Групповые ячейки размещены на первом и втором этажах.", BODY, False),
        ("На первом этаже — четыре ячейки, на втором — четыре ячейки.", BODY, False),
        ("", BODY, False),
        ("2.3. Высота помещений групповых ячеек в чистоте — 3,0 м.", BODY, False),
    ),
    (
        ("3. Конструктивные и отделочные решения", H1, False),
        ("", BODY, False),
        ("3.1. Наружные стены — кладка из керамического кирпича с утеплением", BODY, False),
        ("минераловатными плитами и штукатурным фасадом.", BODY, False),
        ("", BODY, False),
        ("3.2. Перекрытия — сборные железобетонные плиты по серии.", BODY, False),
        ("", BODY, False),
        ("3.3. Кровля — плоская, с внутренним организованным водостоком.", BODY, False),
        ("", BODY, False),
        ("4. Противопожарные требования", H1, False),
        ("", BODY, False),
        ("4.1. Степень огнестойкости здания принята III, что учтено при назначении", BODY, False),
        ("пределов огнестойкости несущих конструкций.", BODY, False),
        ("", BODY, False),
        ("4.2. Из каждой групповой ячейки предусмотрен рассредоточенный выход", BODY, False),
        ("на лестничную клетку.", BODY, False),
        ("", BODY, False),
        ("5. Заключение", H1, False),
        ("", BODY, False),
        ("5.1. Принятые архитектурные решения обеспечивают функционирование", BODY, False),
        ("здания в соответствии с заданием на проектирование.", BODY, False),
    ),
)


def build() -> bytes:
    font = load_font()

    allowed = set(content.character_set())
    used: set[str] = set()
    for page in PAGES:
        for text, _size, _centre in page:
            used.update(text)
    for number in range(1, len(PAGES) + 1):
        used.update(FOOTER.format(page=number))
    missing = sorted(used - allowed)
    if missing:
        raise SystemExit(
            "these characters are outside the committed font subset, so the document "
            f"would draw blanks: {''.join(missing)!r}"
        )

    placements: list[list[tuple[str, float, float, float]]] = []
    for number, page in enumerate(PAGES, start=1):
        y = document.PAGE_HEIGHT - document.MARGIN_TOP
        out: list[tuple[str, float, float, float]] = []
        for text, size, centre in page:
            y -= size * document.LINE_HEIGHT_FACTOR
            if not text:
                continue
            width = font.text_width(text, size)
            if width > document.TEXT_WIDTH:
                raise SystemExit(
                    f"page {number}: {text!r} is {width:.2f} pt wide and the text box is "
                    f"{document.TEXT_WIDTH:.2f} pt. A reader could split a quotation on it."
                )
            x = (
                document.MARGIN_LEFT + (document.TEXT_WIDTH - width) / 2.0
                if centre
                else document.MARGIN_LEFT
            )
            out.append((text, size, round(x, 3), round(y, 3)))
        footer = FOOTER.format(page=number)
        out.append((footer, content.FOOTER_SIZE, document.MARGIN_LEFT, document.FOOTER_BASELINE))
        placements.append(out)

    return document.simple_text_pdf(font, placements)


def main() -> int:
    pdf = build()
    target = HERE / "w28_own_document.pdf"
    target.write_bytes(pdf)
    print(f"{target}  {len(pdf)} bytes  sha256 {hashlib.sha256(pdf).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
