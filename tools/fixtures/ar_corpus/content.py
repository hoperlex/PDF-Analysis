"""The synthetic AR document text and the seeded-issue oracle it is built around.

This module is the single source of truth for both the PDF and the expected-issues
manifest. The manifest is generated from the same `Line` objects the PDF is drawn from,
so a quotation cannot drift away from the page it is declared on.

Two invariants make the quotations recoverable character-for-character, and
`build_ar_corpus.py` enforces both before writing anything:

1.  Every seeded and control quotation is a substring of exactly one `Line`. Nothing is
    ever reflowed across a line boundary, so no extractor has to guess where a soft wrap
    was and no quotation can acquire an interior newline.
2.  Each `Line` is drawn with a single text-showing operator at a single position, so an
    extractor reproduces it verbatim rather than reassembling it from fragments.

Everything here is invented. There is no customer, production or real project content,
and no real organisation, address or person is named (owner decision OD-17).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Categories fixed by PROTOTYPE_PROFILE.md section 7.1.
CATEGORY_CONTRADICTION = "internal_contradiction"
CATEGORY_PLACEHOLDER = "explicit_placeholder"


@dataclass(frozen=True)
class Line:
    """One rendered line of text: one text-showing operator at one position."""

    text: str
    size: float = 10.5
    indent: float = 0.0
    space_before: float = 0.0
    center: bool = False


@dataclass(frozen=True)
class Page:
    number: int
    lines: tuple[Line, ...]


@dataclass(frozen=True)
class Evidence:
    page: int
    quotation: str


@dataclass(frozen=True)
class SeededIssue:
    """An issue deliberately planted in the document. PC-01 acceptance measures recall
    against these."""

    id: str
    category: str
    attribute: str
    summary: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Control:
    """A statement a correct analyzer must NOT report. PC-01 precision is measured
    against these."""

    id: str
    pages: tuple[int, ...]
    quotation: str
    would_be_false_positive_as: str
    why_not_an_issue: str


def _p(number: int, lines: list[Line]) -> Page:
    return Page(number=number, lines=tuple(lines))


H1 = 13.0
H2 = 11.5
BODY = 10.5
SMALL = 9.0

# --------------------------------------------------------------------------------------
# Page 1 - title
# --------------------------------------------------------------------------------------
_PAGE_1 = _p(1, [  # every line centred; see _centre_title_page below
    Line("ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «СИНТЕТИКПРОЕКТ»", H2),
    Line("вымышленная организация; реальному юридическому лицу не соответствует", SMALL),
    Line("", BODY, space_before=48.0),
    Line("Объект: многоквартирный жилой дом на 64 квартиры", BODY),
    Line("Условная площадка № 1, квартал СП-7", BODY),
    Line("", BODY, space_before=40.0),
    Line("ПРОЕКТНАЯ ДОКУМЕНТАЦИЯ", H1),
    Line("Раздел 3. Архитектурные решения", H2, space_before=8.0),
    Line("Шифр СП-7-АР", BODY, space_before=8.0),
    Line("", BODY, space_before=40.0),
    Line("Стадия: П", BODY),
    Line("Том 3", BODY),
    Line("", BODY, space_before=60.0),
    Line("СИНТЕТИЧЕСКИЙ ДОКУМЕНТ.", SMALL),
    Line("Создан генератором tools/fixtures/build_ar_corpus.py для приёмочных", SMALL),
    Line("испытаний. Проектной документацией не является и для строительства", SMALL),
    Line("не применяется.", SMALL),
])

# --------------------------------------------------------------------------------------
# Page 2 - general data. Carries the first half of SI-01 and of CTL-05.
# --------------------------------------------------------------------------------------
_PAGE_2 = _p(2, [
    Line("1. ОБЩИЕ ДАННЫЕ", H1),
    Line("1.1. Раздел разработан на основании задания на проектирование и содержит",
         BODY, space_before=14.0),
    Line("архитектурные решения надземной и подземной частей здания."),
    Line("1.2. Уровень ответственности здания — нормальный.", BODY, space_before=10.0),
    Line("1.3. Степень огнестойкости здания — II.", BODY, space_before=10.0),
    Line("1.4. Класс конструктивной пожарной опасности здания — С0.",
         BODY, space_before=10.0),
    Line("1.5. Класс функциональной пожарной опасности — Ф1.3.", BODY, space_before=10.0),
    Line("1.6. Количество надземных этажей — 9, подземных этажей — 1.",
         BODY, space_before=10.0),
    Line("1.7. Общая площадь здания — 4 812,0 кв. м.", BODY, space_before=10.0),
    Line("1.8. Строительный объём здания — 17 640,0 куб. м.", BODY, space_before=10.0),
])

# --------------------------------------------------------------------------------------
# Page 3 - planning. Carries the first half of SI-02 and CTL-03.
# --------------------------------------------------------------------------------------
_PAGE_3 = _p(3, [
    Line("2. ОБЪЁМНО-ПЛАНИРОВОЧНЫЕ РЕШЕНИЯ", H1),
    Line("2.1. Здание односекционное, прямоугольной формы в плане, с размерами",
         BODY, space_before=14.0),
    Line("в осях 36,0 х 18,0 м."),
    Line("2.2. Высота этажа в чистоте на первом этаже — 3,3 м.", BODY, space_before=10.0),
    Line("2.3. Входная группа оборудована тамбуром глубиной 1,8 м.",
         BODY, space_before=10.0),
    Line("2.4. Из надземной части здания предусмотрено два эвакуационных выхода.",
         BODY, space_before=10.0),
    Line("2.5. Выходы ведут непосредственно наружу через тамбуры.",
         BODY, space_before=10.0),
    Line("2.6. Лифтовой узел включает два пассажирских лифта грузоподъёмностью",
         BODY, space_before=10.0),
    Line("630 кг каждый."),
])

# --------------------------------------------------------------------------------------
# Page 4 - construction and finishes. Carries CTL-04 and CTL-02.
# --------------------------------------------------------------------------------------
_PAGE_4 = _p(4, [
    Line("3. КОНСТРУКТИВНЫЕ РЕШЕНИЯ", H1),
    Line("3.1. Наружные стены — трёхслойные, с эффективным утеплителем и облицовкой",
         BODY, space_before=14.0),
    Line("лицевым кирпичом."),
    Line("3.2. Внутренние несущие стены — монолитный железобетон толщиной 200 мм.",
         BODY, space_before=10.0),
    Line("3.3. Перегородки — из керамического кирпича толщиной 120 мм.",
         BODY, space_before=10.0),
    Line("3.4. Высота этажа в чистоте на типовых этажах — 3,0 м.",
         BODY, space_before=10.0),
    Line("3.5. Уточнённые отметки чистого пола приведены в таблице 4.2.",
         BODY, space_before=10.0),
    Line("3.6. Кровля — плоская, с внутренним организованным водостоком.",
         BODY, space_before=10.0),
])

# --------------------------------------------------------------------------------------
# Page 5 - the separate gatehouse. Carries CTL-01, the strongest precision control.
# --------------------------------------------------------------------------------------
_PAGE_5 = _p(5, [
    Line("4. ОТДЕЛЬНО СТОЯЩИЕ ЗДАНИЯ ПЛОЩАДКИ", H1),
    Line("4.1. На площадке размещается отдельно стоящее одноэтажное здание",
         BODY, space_before=14.0),
    Line("контрольно-пропускного пункта (далее — КПП) площадью 24,0 кв. м."),
    Line("4.2. Степень огнестойкости здания КПП — IV.", BODY, space_before=10.0),
    Line("4.3. Здание КПП не связано с жилым домом ни конструктивно, ни",
         BODY, space_before=10.0),
    Line("функционально и рассматривается как самостоятельный объект."),
    Line("4.4. Наружные стены здания КПП — из мелкоштучных блоков толщиной 300 мм.",
         BODY, space_before=10.0),
])

# --------------------------------------------------------------------------------------
# Page 6 - fire measures. Carries the second half of SI-01 and of CTL-05.
# --------------------------------------------------------------------------------------
_PAGE_6 = _p(6, [
    Line("5. АРХИТЕКТУРНО-СТРОИТЕЛЬНЫЕ ПРОТИВОПОЖАРНЫЕ МЕРОПРИЯТИЯ", H2),
    Line("5.1. Проектные решения приняты с учётом требований пожарной безопасности,",
         BODY, space_before=14.0),
    Line("предъявляемых к многоквартирным жилым зданиям."),
    Line("5.2. Степень огнестойкости здания — III.", BODY, space_before=10.0),
    Line("5.3. Класс конструктивной пожарной опасности здания — С0.",
         BODY, space_before=10.0),
    Line("5.4. Предел огнестойкости несущих стен принят не менее R 90.",
         BODY, space_before=10.0),
    Line("5.5. Заполнение проёмов в противопожарных преградах принято по типу",
         BODY, space_before=10.0),
    Line("соответствующей преграды."),
])

# --------------------------------------------------------------------------------------
# Page 7 - evacuation. Carries the second half of SI-02 and CTL-06.
# --------------------------------------------------------------------------------------
_PAGE_7 = _p(7, [
    Line("6. ЭВАКУАЦИОННЫЕ ПУТИ И ВЫХОДЫ", H1),
    Line("6.1. Ширина эвакуационных путей принята не менее 1,2 м, высота — не менее",
         BODY, space_before=14.0),
    Line("2,0 м."),
    Line("6.2. Из надземной части здания предусмотрено три эвакуационных выхода.",
         BODY, space_before=10.0),
    Line("6.3. Из подвала предусмотрен один обособленный эвакуационный выход.",
         BODY, space_before=10.0),
    Line("Он не учитывается в числе выходов из надземной части здания."),
    Line("6.4. Двери эвакуационных выходов открываются по направлению выхода",
         BODY, space_before=10.0),
    Line("из здания."),
])

# --------------------------------------------------------------------------------------
# Page 8 - finishes schedule. Carries SI-03, the explicit placeholder.
# --------------------------------------------------------------------------------------
_PAGE_8 = _p(8, [
    Line("7. ВЕДОМОСТЬ ЗАПОЛНЕНИЯ ПРОЁМОВ И ОТДЕЛКИ", H2),
    Line("7.1. Отделка помещений общего пользования выполняется материалами",
         BODY, space_before=14.0),
    Line("группы горючести Г1."),
    Line("7.2. Тип заполнения оконных проёмов — уточнить.", BODY, space_before=10.0),
    Line("7.3. Тип заполнения дверных проёмов — двупольные двери с остеклением.",
         BODY, space_before=10.0),
    Line("7.4. Полы в помещениях общего пользования — керамогранит.",
         BODY, space_before=10.0),
    Line("7.5. Настоящий раздел подлежит рассмотрению в составе тома 3.",
         BODY, space_before=10.0),
])

PAGES: tuple[Page, ...] = (
    _PAGE_1, _PAGE_2, _PAGE_3, _PAGE_4, _PAGE_5, _PAGE_6, _PAGE_7, _PAGE_8,
)

FOOTER_TEMPLATE = "СП-7-АР    Лист {page}    Синтетический документ"
FOOTER_SIZE = 8.0

# --------------------------------------------------------------------------------------
# The oracle
# --------------------------------------------------------------------------------------

SEEDED_ISSUES: tuple[SeededIssue, ...] = (
    SeededIssue(
        id="SI-01",
        category=CATEGORY_CONTRADICTION,
        attribute="степень огнестойкости здания",
        summary=(
            "Степень огнестойкости одного и того же здания указана как II в разделе "
            "общих данных и как III в разделе противопожарных мероприятий."
        ),
        evidence=(
            Evidence(page=2, quotation="Степень огнестойкости здания — II."),
            Evidence(page=6, quotation="Степень огнестойкости здания — III."),
        ),
    ),
    SeededIssue(
        id="SI-02",
        category=CATEGORY_CONTRADICTION,
        attribute="количество эвакуационных выходов из надземной части",
        summary=(
            "Количество эвакуационных выходов из надземной части здания указано "
            "как два в объёмно-планировочных решениях и как три в разделе эвакуации."
        ),
        evidence=(
            Evidence(
                page=3,
                quotation="Из надземной части здания предусмотрено два эвакуационных выхода.",
            ),
            Evidence(
                page=7,
                quotation="Из надземной части здания предусмотрено три эвакуационных выхода.",
            ),
        ),
    ),
    SeededIssue(
        id="SI-03",
        category=CATEGORY_PLACEHOLDER,
        attribute="тип заполнения оконных проёмов",
        summary=(
            "Тип заполнения оконных проёмов не определён: вместо решения оставлено "
            "буквальное указание «уточнить»."
        ),
        evidence=(
            Evidence(page=8, quotation="Тип заполнения оконных проёмов — уточнить."),
        ),
    ),
)

CONTROLS: tuple[Control, ...] = (
    Control(
        id="CTL-01",
        pages=(5,),
        quotation="Степень огнестойкости здания КПП — IV.",
        would_be_false_positive_as=CATEGORY_CONTRADICTION,
        why_not_an_issue=(
            "Третье значение той же характеристики, но у другого объекта: отдельно "
            "стоящего здания КПП, а не жилого дома. Раздел 4 прямо указывает, что КПП "
            "рассматривается как самостоятельный объект."
        ),
    ),
    Control(
        id="CTL-02",
        pages=(4,),
        quotation="Уточнённые отметки чистого пола приведены в таблице 4.2.",
        would_be_false_positive_as=CATEGORY_PLACEHOLDER,
        why_not_an_issue=(
            "Содержит основу «уточн», но описывает уже принятое решение со ссылкой на "
            "таблицу, а не пропуск. Поиск по подстроке даст здесь ложное срабатывание."
        ),
    ),
    Control(
        id="CTL-03",
        pages=(3,),
        quotation="Высота этажа в чистоте на первом этаже — 3,3 м.",
        would_be_false_positive_as=CATEGORY_CONTRADICTION,
        why_not_an_issue=(
            "Значение относится к первому этажу и согласовано с CTL-04, который "
            "относится к типовым этажам. Разные объекты описания, а не противоречие."
        ),
    ),
    Control(
        id="CTL-04",
        pages=(4,),
        quotation="Высота этажа в чистоте на типовых этажах — 3,0 м.",
        would_be_false_positive_as=CATEGORY_CONTRADICTION,
        why_not_an_issue=(
            "Парная к CTL-03. Различие значений объясняется различием этажей, прямо "
            "названным в обеих формулировках."
        ),
    ),
    Control(
        id="CTL-05",
        pages=(2, 6),
        quotation="Класс конструктивной пожарной опасности здания — С0.",
        would_be_false_positive_as=CATEGORY_CONTRADICTION,
        why_not_an_issue=(
            "Одна и та же характеристика с одним и тем же значением на двух страницах: "
            "повтор, а не расхождение. Это другая характеристика, чем степень "
            "огнестойкости из SI-01, и смешивать их нельзя."
        ),
    ),
    Control(
        id="CTL-06",
        pages=(7,),
        quotation="Из подвала предусмотрен один обособленный эвакуационный выход.",
        would_be_false_positive_as=CATEGORY_CONTRADICTION,
        why_not_an_issue=(
            "Относится к подвалу, а не к надземной части, и следующая строка прямо "
            "исключает этот выход из их числа. С SI-02 не связано."
        ),
    ),
)


def all_quotations() -> list[tuple[str, int, str]]:
    """Return (owner id, page, quotation) for every seeded issue and every control."""
    out: list[tuple[str, int, str]] = []
    for issue in SEEDED_ISSUES:
        for ev in issue.evidence:
            out.append((issue.id, ev.page, ev.quotation))
    for control in CONTROLS:
        for page in control.pages:
            out.append((control.id, page, control.quotation))
    return out


# The font subset covers a declared repertoire rather than only the characters the
# baseline happens to use today. Two reasons: the negative fixtures carry ASCII rule ids
# and passwords, and a one-word edit to the document should not silently need a font
# rebuild. `character_set` asserts the document stays inside the repertoire, so a
# genuinely new character is still a loud failure rather than a dropped glyph.
REPERTOIRE = "".join(sorted(set(
    # Printable ASCII.
    "".join(chr(c) for c in range(0x20, 0x7F))
    # Russian alphabet, both cases, including Ё/ё.
    + "".join(chr(c) for c in range(0x0410, 0x0450))
    + "\u0401\u0451"
    # Typography the document uses: guillemets, en/em dash, numero, non-breaking hyphen
    # substitutes, ellipsis, curly quotes.
    + "\u00ab\u00bb\u2013\u2014\u2018\u2019\u201c\u201d\u201e\u2026\u2116\u00a0\u00b0\u00b2\u00b3\u00d7\u2212"
)))


def document_characters() -> str:
    """Every character the baseline document actually draws."""
    chars: set[str] = set()
    for page in PAGES:
        for line in page.lines:
            chars.update(line.text)
        chars.update(FOOTER_TEMPLATE.format(page=page.number))
    chars.discard("\n")
    return "".join(sorted(chars))


def character_set() -> str:
    """The repertoire the font subset must cover.

    Raises if the document has drifted outside the declared repertoire, which is the
    case where a font rebuild is genuinely required.
    """
    outside = sorted(set(document_characters()) - set(REPERTOIRE))
    if outside:
        raise ValueError(
            "the baseline text uses characters outside REPERTOIRE: "
            + " ".join(f"U+{ord(c):04X} {c!r}" for c in outside)
        )
    return REPERTOIRE
