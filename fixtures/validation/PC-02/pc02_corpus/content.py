"""The PC-02 corpus text and its ground truth.

This module is the single source of truth for both the PDFs and `corpus_manifest.json`.
The manifest is generated from the same `Line` objects the PDFs are drawn from, so a
quotation cannot drift away from the page it is declared on.

Three invariants make the ground truth trustworthy, and `build_pc02_corpus.py` enforces
all three before writing anything:

1.  Every seeded and control quotation is a substring of exactly one `Line` on exactly
    the pages it declares, inside its own document, and every quotation string is unique
    across the whole corpus. Nothing is reflowed across a line boundary, so no extractor
    has to guess where a soft wrap was.
2.  Filler prose carries **no digit and no placeholder token at all**. This is what stops
    the corpus seeding an issue by accident: an unnoticed number in boilerplate is a
    contradiction nobody declared, and it would be scored as a false positive against a
    model that was right.
3.  Every quotation survives the round trip through the written PDF bytes, verified by an
    extractor that shares no code with the writer.

Everything here is invented. Owner decision OD-17 rules the corpus synthetic-only: no
customer, production or real project bytes, and no real organisation, address, person or
project is named. `СИНТЕТИКПРОЕКТ` and `Квартал СИНТЕЗ` are deliberately not names that
could belong to anyone.

## Why these seeded issues

PC-01's three seeded issues - fire-resistance degree, evacuation-exit count and the
literal `уточнить` - were found by a live model run on 2026-09-14. Reusing them would
make PC-02 a re-measurement of a result already in hand, and the task's own non-goals
forbid a corpus reverse-engineered from findings the current prompt already produces. So
none of PC-02's nine seeded issues repeats a PC-01 attribute. They were chosen instead
for the property that makes a contradiction *professionally* interesting: each is a
statement a reviewer would have to reconcile, not a statement a string comparator would
trip over.
"""

from __future__ import annotations

from dataclasses import dataclass

# Categories fixed by PROTOTYPE_PROFILE.md section 7.1. There are exactly two.
CATEGORY_CONTRADICTION = "internal_contradiction"
CATEGORY_PLACEHOLDER = "explicit_placeholder"

AUTHOR = "СИНТЕТИКПРОЕКТ (вымышленная организация)"
PROJECT = "Квартал СИНТЕЗ (вымышленный объект)"

H1 = 13.0
H2 = 11.5
BODY = 10.5

# Tokens that make a statement an explicit placeholder. Filler may not contain any of
# them; this list is also what the seeded placeholders are built from.
PLACEHOLDER_TOKENS = ("уточн", "TBD", "ТБД", "не определено", "___", "XXX")


@dataclass(frozen=True)
class Line:
    """One rendered line of text: one text-showing operator at one position."""

    text: str
    size: float = BODY
    indent: float = 0.0
    space_before: float = 0.0
    center: bool = False
    role: str = "filler"


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
    """An issue deliberately planted in a document. PC-02 recall is measured against
    these, and only against these."""

    id: str
    category: str
    attribute: str
    summary: str
    why_seeded: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Control:
    """A statement a correct analyzer must NOT report. PC-02 precision is measured
    against these.

    `why_not_an_issue` is not decoration. A control whose rationale cannot be written in
    one sentence is a control whose ground truth is in doubt, and it does not belong in
    the corpus.
    """

    id: str
    pages: tuple[int, ...]
    quotation: str
    archetype: str
    would_be_false_positive_as: str
    why_not_an_issue: str


@dataclass(frozen=True)
class Doc:
    label: str
    role: str  # "seeded" or "control"
    title: str
    subject: str
    footer: str
    summary: str
    pages: tuple[Page, ...]
    seeded: tuple[SeededIssue, ...]
    controls: tuple[Control, ...]

    @property
    def filename(self) -> str:
        return f"{self.label}.pdf"


# --------------------------------------------------------------------------------------
# Control archetypes
#
# Session A4 found the hard way that a corpus of trivial negatives measures nothing: a
# control only bounds precision if a reasonable analyzer could actually trip on it. Each
# control below declares which archetype it belongs to, so the corpus can be audited for
# breadth rather than merely for count.
# --------------------------------------------------------------------------------------

ARCHETYPES = {
    "other_object": (
        "the same attribute stated for a different, explicitly named object - a "
        "gatehouse, a substation, a neighbouring block"
    ),
    "scope_dependent": (
        "values that legitimately differ because they describe different scopes - a "
        "ground floor against a typical floor, an above-ground part against a basement"
    ),
    "identical_repeat": (
        "the same value restated identically on another page; two mentions of one "
        "attribute are not two values"
    ),
    "excluded_by_text": (
        "a value the surrounding text explicitly excludes from the comparison it would "
        "otherwise contradict"
    ),
    "superseded": (
        "a value the document explicitly withdraws, so it is history rather than a "
        "competing claim"
    ),
    "notation_variant": (
        "one value written two ways - thin space against none, м² against кв. м - "
        "identical to a reader, different to a string comparator"
    ),
    "placeholder_stem": (
        "prose carrying the stem of a placeholder word while recording a decision that "
        "has actually been made"
    ),
    "absence_by_scope": (
        "something genuinely absent from this document because another document owns "
        "it, which is not an unfilled field"
    ),
    "decided_alternative": (
        "an alternative mentioned and then explicitly rejected in favour of a stated "
        "choice"
    ),
    "sibling_filled": (
        "a filled value for a sibling of an attribute that is genuinely blank nearby, "
        "so the blank has to be distinguished from its neighbour"
    ),
    "tolerance_or_rounding": (
        "text that legitimises a small numeric divergence, so the divergence is "
        "declared rather than accidental"
    ),
    "class_notation": (
        "several class-like tokens that belong to different classification systems and "
        "are easy to conflate"
    ),
}


# --------------------------------------------------------------------------------------
# Filler prose
#
# Every sentence here is digit-free and placeholder-free, and the build refuses to run if
# that ever stops being true. That is the single property keeping the corpus honest: any
# number in boilerplate is a project attribute nobody declared, and a model that noticed
# it would be marked wrong for being right.
# --------------------------------------------------------------------------------------

FILLER: tuple[str, ...] = (
    "Настоящий раздел разработан на основании задания на проектирование.",
    "Архитектурные решения приняты с учётом градостроительного контекста.",
    "Планировочная структура здания подчинена функциональному зонированию.",
    "Входные группы организованы со стороны внутриквартального проезда.",
    "Отделочные материалы приняты из числа разрешённых к применению.",
    "Наружные ограждающие конструкции выполнены по многослойной схеме.",
    "Внутренние перегородки приняты из мелкоштучных блоков на растворе.",
    "Полы помещений общего пользования выполняются по бетонному основанию.",
    "Витражное остекление лестнично-лифтовых узлов принято по типовой схеме.",
    "Кровельное покрытие выполняется с уклоном к водоприёмным устройствам.",
    "Помещения хранения уборочного инвентаря размещены на каждом этаже.",
    "Доступность для маломобильных групп обеспечена без перепадов уровней.",
    "Зоны безопасности размещены в лифтовых холлах и обозначены знаками.",
    "Естественное освещение жилых помещений обеспечено оконными проёмами.",
    "Шумозащита обеспечена конструктивными решениями ограждающих элементов.",
    "Конструкции лестниц приняты сборными с площадками заводской готовности.",
    "Мусороудаление организовано через камеру с отдельным входом снаружи.",
    "Технические помещения отделены от жилой части противопожарными преградами.",
    "Инженерные коммуникации прокладываются в выделенных вертикальных шахтах.",
    "Фасадная система крепится к несущим конструкциям через кронштейны.",
    "Цоколь облицован плитами повышенной стойкости к механическим нагрузкам.",
    "Козырьки над входами выполнены из металлоконструкций заводской поставки.",
    "Оконные блоки комплектуются приточными клапанами с ручной регулировкой.",
    "Ограждения балконов приняты со сплошным стеклянным заполнением.",
    "Кладовые и колясочные размещены на первом этаже у входной группы.",
    "Планировка квартир допускает вариантную расстановку санитарных приборов.",
    "Двери эвакуационных выходов открываются по направлению выхода наружу.",
    "Отделка стен лестничных клеток выполняется негорючими материалами.",
    "Помещения без естественного освещения оборудованы вытяжной вентиляцией.",
    "Решения согласованы со смежными разделами проектной документации.",
    "Примыкание кровли к парапету выполнено с механическим креплением.",
    "Материалы отделки приняты с учётом условий эксплуатации помещений.",
    "Приямки световых карманов закрыты решётками заводского изготовления.",
    "Ограждение кровли выполнено по периметру с креплением к парапету.",
    "Система водоотвода защищена от обледенения греющим кабелем.",
    "Лифтовые шахты отделены от смежных помещений глухими стенами.",
    "Перечень применяемых материалов приведён в ведомости отделки помещений.",
    "Входные двери приняты со встроенными доводчиками и уплотнением притвора.",
    "Внутриквартирные перегородки допускают перепланировку без нагрузок.",
    "Освещение мест общего пользования обеспечено светильниками с датчиками.",
    "Поверхности стен под отделку подготавливаются шпатлеванием и грунтованием.",
    "Дверные блоки в технические помещения приняты металлическими глухими.",
    "Лестничные марши оборудованы поручнями с обеих сторон по всей длине.",
    "Помещения консьержа оборудованы окном обзора и отдельным входом.",
    "Наружные площадки входных групп выполнены с противоскользящим покрытием.",
    "Фасадные швы герметизируются составами, стойкими к ультрафиолету.",
)


# --------------------------------------------------------------------------------------
# Page specification
# --------------------------------------------------------------------------------------


class _Filler:
    """Marker for a line the builder fills from the pool."""


F = _Filler()


@dataclass(frozen=True)
class Q:
    """An authored line whose exact text is ground truth."""

    text: str


@dataclass(frozen=True)
class PageSpec:
    heading: str
    body: tuple[object, ...]


def _page(heading: str, *body: object) -> PageSpec:
    return PageSpec(heading=heading, body=tuple(body))


def _title_lines(doc_title: str, label: str) -> tuple[Line, ...]:
    return (
        Line(AUTHOR.split(" (")[0], size=H2, center=True, space_before=90.0,
             role="title"),
        Line(PROJECT.split(" (")[0], size=H1, center=True, space_before=26.0,
             role="title"),
        Line("Раздел АР. Архитектурные решения", size=H2, center=True,
             space_before=20.0, role="title"),
        Line(doc_title, size=H2, center=True, space_before=34.0, role="title"),
        Line("Синтетический документ. Не проектная документация.", size=BODY,
             center=True, space_before=48.0, role="title"),
        Line("Приёмочная фикстура PC-02, метка " + label, size=BODY, center=True,
             space_before=12.0, role="title"),
    )


class _FillerCursor:
    """Deterministic walk over the filler pool: no PRNG, no clock, stable across runs."""

    def __init__(self) -> None:
        self._index = 0

    def next(self) -> str:
        text = FILLER[self._index % len(FILLER)]
        self._index += 1
        return text


def _build_pages(doc_title: str, label: str, specs: tuple[PageSpec, ...],
                 cursor: _FillerCursor) -> tuple[Page, ...]:
    pages: list[Page] = [Page(number=1, lines=_title_lines(doc_title, label))]
    for offset, spec in enumerate(specs, start=2):
        lines: list[Line] = [
            Line(spec.heading, size=H2, space_before=16.0, role="head")
        ]
        for item in spec.body:
            if isinstance(item, Q):
                lines.append(Line(item.text, size=BODY, space_before=6.0, role="quote"))
            else:
                lines.append(Line(cursor.next(), size=BODY, space_before=6.0))
        pages.append(Page(number=offset, lines=tuple(lines)))
    return tuple(pages)


# --------------------------------------------------------------------------------------
# The five seeded documents
# --------------------------------------------------------------------------------------

_SPECS: dict[str, tuple[PageSpec, ...]] = {}
_DOC_DEFS: list[dict] = []


def _define(label: str, role: str, title: str, subject: str, summary: str,
            specs: tuple[PageSpec, ...],
            seeded: tuple[SeededIssue, ...] = (),
            controls: tuple[Control, ...] = ()) -> None:
    _DOC_DEFS.append({
        "label": label, "role": role, "title": title, "subject": subject,
        "summary": summary, "specs": specs, "seeded": seeded, "controls": controls,
    })


# --- PC02-S01 -------------------------------------------------------------------------

S01_I1_A = "Класс конструктивной пожарной опасности корпуса 1 — С0."
S01_I1_B = "Класс конструктивной пожарной опасности корпуса 1 — С1."
S01_I2 = "Марка фасадных кассет корпуса 1 — TBD."
S01_C1 = "Класс конструктивной пожарной опасности отдельно стоящей ТП — С1."
S01_C2 = "Уточнённые размеры проёмов приведены в ведомости заполнений корпуса 1."
S01_C3 = "Класс функциональной пожарной опасности корпуса 1 — Ф1.3."
S01_C4 = "Цвет фасадных кассет корпуса 1 принят RAL 7040 и не изменяется."

_define(
    "PC02-S01", "seeded",
    "Корпус 1. Архитектурные решения",
    "Синтетическая фикстура PC-02. Заложены расхождение по классу "
    "конструктивной пожарной опасности и незаполненное поле.",
    "Семь страниц. Класс конструктивной пожарной опасности корпуса 1 назван дважды "
    "по-разному, и марка фасадных кассет оставлена незаполненной.",
    (
        _page("Общие данные", F, F, Q(S01_I1_A), F, F),
        _page("Прочие строения и сооружения", F, Q(S01_C1), F, Q(S01_C3), F),
        _page("Объёмно-планировочные решения", F, F, Q(S01_C2), F, F),
        _page("Противопожарные мероприятия", F, F, Q(S01_I1_B), F),
        _page("Конструктивные решения", F, Q(S01_C3), F, F),
        _page("Наружная отделка", F, Q(S01_I2), Q(S01_C4), F, F),
    ),
    seeded=(
        SeededIssue(
            id="PC02-S01-I1",
            category=CATEGORY_CONTRADICTION,
            attribute="класс конструктивной пожарной опасности корпуса 1",
            summary="Класс конструктивной пожарной опасности одного и того же корпуса 1 "
                    "указан как С0 на странице 2 и как С1 на странице 5.",
            why_seeded="Two sections of a real AR volume are often written by different "
                       "people weeks apart, and the structural fire-hazard class is "
                       "exactly the kind of attribute each restates independently. The "
                       "wording is identical apart from the value, so the contradiction "
                       "is unambiguous, while the same page range also carries the same "
                       "class for a different object and a different class system for "
                       "the same object - so finding it requires reading the subject of "
                       "the sentence, not matching a pattern.",
            evidence=(Evidence(2, S01_I1_A), Evidence(5, S01_I1_B)),
        ),
        SeededIssue(
            id="PC02-S01-I2",
            category=CATEGORY_PLACEHOLDER,
            attribute="марка фасадных кассет корпуса 1",
            summary="Марка фасадных кассет оставлена как литерал TBD на странице 7.",
            why_seeded="PROTOTYPE_PROFILE.md section 7.1 names TBD explicitly, and it "
                       "is the placeholder PC-01 did not use. It is planted two lines "
                       "above a *decided* value for the colour of the same product, so "
                       "a detector that fires on the phrase 'фасадные кассеты' rather "
                       "than on the incompleteness scores a false positive next to it.",
            evidence=(Evidence(7, S01_I2),),
        ),
    ),
    controls=(
        Control("PC02-S01-K1", (3,), S01_C1, "other_object",
                "a second structural fire-hazard class, read as contradicting С0",
                "Класс относится к отдельно стоящей трансформаторной подстанции, а не "
                "к корпусу 1; объект назван в самой строке."),
        Control("PC02-S01-K2", (4,), S01_C2, "placeholder_stem",
                "the stem 'уточн', read as an unfilled field",
                "Размеры уже уточнены и приведены в ведомости; строка фиксирует "
                "принятое решение, а не пробел."),
        Control("PC02-S01-K3", (3, 6), S01_C3, "identical_repeat",
                "one attribute mentioned twice, read as two competing values",
                "Значение Ф1.3 повторено дословно; это класс функциональной, а не "
                "конструктивной пожарной опасности."),
        Control("PC02-S01-K4", (7,), S01_C4, "sibling_filled",
                "a fasade-cassette line beside a TBD, read as part of the same gap",
                "Цвет кассет определён и зафиксирован; незаполнена только марка."),
    ),
)

# --- PC02-S02 -------------------------------------------------------------------------

S02_I1_A = "Общая площадь здания корпуса 2 — 4 812,5 м²."
S02_I1_B = "Общая площадь здания корпуса 2 — 4 218,5 м²."
S02_C1 = "Площадь застройки корпуса 2 — 1 204,0 м²."
S02_C2 = "Полезная площадь корпуса 2 — 4 312,0 м²."
S02_C3 = "Высота первого этажа корпуса 2 от пола до пола — 3,60 м."
S02_C4 = "Высота типового этажа корпуса 2 от пола до пола — 3,00 м."
S02_C5 = "Показатели приведены с округлением до 0,1; итоги могут расходиться."
S02_C6 = "Общая площадь здания корпуса 2 составляет 4812,5 кв. м."

_define(
    "PC02-S02", "seeded",
    "Корпус 2. Объёмно-планировочные решения",
    "Синтетическая фикстура PC-02. Заложено расхождение по общей площади здания.",
    "Шесть страниц. Общая площадь здания названа двумя разными числами, и рядом "
    "стоит то же самое число в другой записи, которое расхождением не является.",
    (
        _page("Технико-экономические показатели", F, Q(S02_I1_A), Q(S02_C1), F, F),
        _page("Объёмно-планировочные решения", F, Q(S02_C2), F, Q(S02_C3), F),
        _page("Высоты помещений и этажей", F, Q(S02_C4), F, Q(S02_C6), F),
        _page("Уточнение показателей", F, F, Q(S02_I1_B), F),
        _page("Порядок подсчёта показателей", F, Q(S02_C5), F, F),
    ),
    seeded=(
        SeededIssue(
            id="PC02-S02-I1",
            category=CATEGORY_CONTRADICTION,
            attribute="общая площадь здания корпуса 2",
            summary="Общая площадь здания корпуса 2 указана как 4 812,5 м² на "
                    "странице 2 и как 4 218,5 м² на странице 5.",
            why_seeded="A transposed pair of digits (812 against 218) is the most "
                       "common way a real area disagrees with itself, and it is the "
                       "hardest kind for a reader skimming a table to catch. The same "
                       "document restates the correct value in a different notation and "
                       "carries two other areas of the building, so the model has to "
                       "decide which pair of numbers describes one attribute.",
            evidence=(Evidence(2, S02_I1_A), Evidence(5, S02_I1_B)),
        ),
    ),
    controls=(
        Control("PC02-S02-K1", (2,), S02_C1, "other_object",
                "a second area figure, read as contradicting the total",
                "Площадь застройки — иной показатель, чем общая площадь здания."),
        Control("PC02-S02-K2", (3,), S02_C2, "other_object",
                "a third area figure close to the total, read as a contradiction",
                "Полезная площадь — самостоятельный показатель и по определению "
                "меньше общей."),
        Control("PC02-S02-K3", (3,), S02_C3, "scope_dependent",
                "a storey height differing from the one on the next page",
                "Высота первого этажа законно отличается от высоты типового этажа."),
        Control("PC02-S02-K4", (4,), S02_C4, "scope_dependent",
                "a second storey height, read as contradicting the first",
                "Относится к типовому этажу, а не к первому; область действия названа."),
        Control("PC02-S02-K5", (6,), S02_C5, "tolerance_or_rounding",
                "a statement that sums may diverge, read as an admission of error",
                "Округление объявлено в самом документе, расхождение итогов "
                "предусмотрено и ограничено."),
        Control("PC02-S02-K6", (4,), S02_C6, "notation_variant",
                "the same total written without a thin space and as кв. м",
                "Число совпадает со страницей 2 посимвольно по значению; различается "
                "только запись."),
    ),
)

# --- PC02-S03 -------------------------------------------------------------------------

S03_I1_A = "Кровля корпуса 3 — плоская, с внутренним организованным водостоком."
S03_I1_B = "Кровля корпуса 3 — скатная, с наружным организованным водостоком."
S03_I2 = "Толщина утеплителя покрытия корпуса 3 — ___ мм."
S03_C1 = "Кровля отдельно стоящего гаража — скатная, с наружным водостоком."
S03_C2 = "Толщина утеплителя наружных стен корпуса 3 — 150 мм."
S03_C3 = "Класс энергетической эффективности корпуса 3 — А."
S03_C4 = "Водосточные воронки приняты по каталогу изготовителя, позиция 4.2."

_define(
    "PC02-S03", "seeded",
    "Корпус 3. Кровля и фасадные системы",
    "Синтетическая фикстура PC-02. Заложены расхождение по типу кровли и "
    "незаполненное поле толщины утеплителя.",
    "Семь страниц. Тип кровли одного корпуса назван и плоским, и скатным, а "
    "толщина утеплителя покрытия оставлена прочерком.",
    (
        _page("Общие данные", F, Q(S03_C3), F, F),
        _page("Кровля и водоотвод", F, F, Q(S03_I1_A), F),
        _page("Прочие строения и сооружения", F, Q(S03_C1), F, F),
        _page("Теплозащита ограждающих конструкций", F, Q(S03_I2), Q(S03_C2), F),
        _page("Организация водоотвода", F, Q(S03_I1_B), F, Q(S03_C3), F),
        _page("Материалы и изделия", F, F, Q(S03_C4), F),
    ),
    seeded=(
        SeededIssue(
            id="PC02-S03-I1",
            category=CATEGORY_CONTRADICTION,
            attribute="тип кровли корпуса 3",
            summary="Кровля корпуса 3 описана как плоская с внутренним водостоком на "
                    "странице 3 и как скатная с наружным водостоком на странице 6.",
            why_seeded="Every other seeded contradiction in this corpus is numeric. "
                       "This one is categorical, and a rate measured only on numbers "
                       "would not generalize to the half of AR prose that carries no "
                       "figures. It is also the contradiction with the largest "
                       "professional consequence here, which is what makes it worth "
                       "asking a reviewer whether the finding was useful.",
            evidence=(Evidence(3, S03_I1_A), Evidence(6, S03_I1_B)),
        ),
        SeededIssue(
            id="PC02-S03-I2",
            category=CATEGORY_PLACEHOLDER,
            attribute="толщина утеплителя покрытия корпуса 3",
            summary="Толщина утеплителя покрытия оставлена прочерком на странице 5.",
            why_seeded="A blank rule is a placeholder with no placeholder *word* in it. "
                       "A detector keyed to уточнить and TBD misses it entirely, so it "
                       "measures whether the stage understands incompleteness or only "
                       "recognises vocabulary. The filled thickness of a sibling "
                       "structure sits on the next line.",
            evidence=(Evidence(5, S03_I2),),
        ),
    ),
    controls=(
        Control("PC02-S03-K1", (4,), S03_C1, "other_object",
                "a second roof type, read as contradicting the main roof",
                "Относится к отдельно стоящему гаражу; объект назван в строке."),
        Control("PC02-S03-K2", (5,), S03_C2, "sibling_filled",
                "a filled insulation thickness beside a blank one",
                "Это утеплитель наружных стен, а не покрытия; значение задано."),
        Control("PC02-S03-K3", (2, 6), S03_C3, "identical_repeat",
                "an energy class stated twice, read as two values",
                "Значение А повторено дословно."),
        Control("PC02-S03-K4", (7,), S03_C4, "absence_by_scope",
                "a reference to an external catalogue, read as an unfilled field",
                "Позиция изделия определена ссылкой на каталог; выбор сделан."),
    ),
)

# --- PC02-S04 -------------------------------------------------------------------------

S04_I1_A = "Отметка 0,000 корпуса 4 соответствует абсолютной отметке 143,60."
S04_I1_B = "Отметка 0,000 корпуса 4 соответствует абсолютной отметке 143,80."
S04_I2_A = "В корпусе 4 предусмотрено два пассажирских лифта."
S04_I2_B = "В корпусе 4 предусмотрено три пассажирских лифта."
S04_C1 = "Отметка 0,000 корпуса 5 соответствует абсолютной отметке 144,10."
S04_C2 = "В корпусе 4 предусмотрен один грузопассажирский лифт."
S04_C3 = "Ранее принятая отметка 143,40 настоящим листом не применяется."
S04_C4 = "Количество лифтов корпуса 5 — четыре, включая один грузовой."
S04_C5 = "Отметки даны в Балтийской системе высот."

_define(
    "PC02-S04", "seeded",
    "Корпус 4. Вертикальный транспорт и высотные отметки",
    "Синтетическая фикстура PC-02. Заложены расхождения по абсолютной отметке "
    "нуля и по количеству пассажирских лифтов.",
    "Девять страниц с двумя заложенными расхождениями и явно отменённым третьим "
    "значением отметки, которое расхождением не является.",
    (
        _page("Высотные отметки", F, F, Q(S04_I1_A), F),
        _page("Смежные корпуса", F, Q(S04_C1), Q(S04_C5), F),
        _page("Вертикальный транспорт", F, F, Q(S04_I2_A), F),
        _page("Грузовые перевозки", F, Q(S04_C2), F, F),
        _page("Изменения и дополнения", F, Q(S04_C3), F, F),
        _page("Привязка к генеральному плану", F, Q(S04_I1_B), F, Q(S04_C5), F),
        _page("Лифтовое оборудование", F, F, Q(S04_I2_B), F),
        _page("Сведения о смежных разделах", F, Q(S04_C4), F, F),
    ),
    seeded=(
        SeededIssue(
            id="PC02-S04-I1",
            category=CATEGORY_CONTRADICTION,
            attribute="абсолютная отметка нуля корпуса 4",
            summary="Абсолютная отметка нуля корпуса 4 указана как 143,60 на "
                    "странице 2 и как 143,80 на странице 7.",
            why_seeded="A 200 mm disagreement in the datum is small enough to survive "
                       "review and expensive enough to matter on site, which is exactly "
                       "the profile of a finding worth paying for. The document also "
                       "carries the datum of a neighbouring block and a third value it "
                       "explicitly withdraws, so three numbers are in play and only one "
                       "pair is a contradiction.",
            evidence=(Evidence(2, S04_I1_A), Evidence(7, S04_I1_B)),
        ),
        SeededIssue(
            id="PC02-S04-I2",
            category=CATEGORY_CONTRADICTION,
            attribute="количество пассажирских лифтов корпуса 4",
            summary="Количество пассажирских лифтов корпуса 4 указано как два на "
                    "странице 4 и как три на странице 8.",
            why_seeded="Counts of the same equipment class in one building are a "
                       "standard AR inconsistency. The wording is identical apart from "
                       "the numeral, so the claim is unambiguous, while a goods lift in "
                       "the same building offers the obvious wrong reconciliation - "
                       "two plus one - which a careless reader would accept.",
            evidence=(Evidence(4, S04_I2_A), Evidence(8, S04_I2_B)),
        ),
    ),
    controls=(
        Control("PC02-S04-K1", (3,), S04_C1, "other_object",
                "a third datum value, read as contradicting the other two",
                "Отметка относится к корпусу 5; корпус назван в строке."),
        Control("PC02-S04-K2", (5,), S04_C2, "other_object",
                "a lift count that appears to reconcile two against three",
                "Лифт грузопассажирский, а не пассажирский; классы разные."),
        Control("PC02-S04-K3", (6,), S04_C3, "superseded",
                "a third datum value, read as a live competing claim",
                "Значение прямо отменено настоящим листом и в сравнении не участвует."),
        Control("PC02-S04-K4", (9,), S04_C4, "other_object",
                "a fourth lift count, read as contradicting the building's own",
                "Относится к корпусу 5."),
        Control("PC02-S04-K5", (3, 7), S04_C5, "identical_repeat",
                "a datum system stated twice, read as two claims",
                "Строка повторена дословно и значения не содержит."),
    ),
)

# --- PC02-S05 -------------------------------------------------------------------------

S05_I1_A = "Этажность корпуса 5 — 12 этажей."
S05_I1_B = "Этажность корпуса 5 — 14 этажей."
S05_I2 = "Назначение помещения 1.12 — не определено."
S05_C1 = "Количество этажей корпуса 5, включая подземные, — 13."
S05_C2 = "Этажность корпуса 6 — 9 этажей."
S05_C3 = "Назначение помещения 1.14 — помещение уборочного инвентаря."
S05_C4 = "Перечень встроенных помещений уточнён и приведён в таблице 5.1."
S05_C5 = "Класс функциональной пожарной опасности встроенной части — Ф4.3."
S05_C6 = "Помещения подвала в этажность здания не включаются."

_define(
    "PC02-S05", "seeded",
    "Корпус 5. Этажность и встроенные помещения",
    "Синтетическая фикстура PC-02. Заложены расхождение по этажности и "
    "незаполненное назначение помещения.",
    "Десять страниц. Этажность корпуса названа дважды по-разному, а назначение "
    "одного из встроенных помещений оставлено неопределённым.",
    (
        _page("Общие данные", F, Q(S05_I1_A), Q(S05_C1), F, F),
        _page("Смежные корпуса", F, Q(S05_C2), F, F),
        _page("Пожарно-технические характеристики", F, Q(S05_C5), F, F),
        _page("Встроенные помещения", F, Q(S05_C3), F, F),
        _page("Состав встроенной части", F, F, Q(S05_I2), F),
        _page("Уточнение состава помещений", F, Q(S05_C4), F, F),
        _page("Классификация встроенной части", F, Q(S05_C5), F, F),
        _page("Технико-экономические показатели", F, F, Q(S05_I1_B), F),
        _page("Порядок подсчёта этажности", F, Q(S05_C6), F, F),
    ),
    seeded=(
        SeededIssue(
            id="PC02-S05-I1",
            category=CATEGORY_CONTRADICTION,
            attribute="этажность корпуса 5",
            summary="Этажность корпуса 5 указана как 12 этажей на странице 2 и как "
                    "14 этажей на странице 9.",
            why_seeded="Storey count is the attribute most often restated in an AR "
                       "volume and therefore most often restated wrongly. This one is "
                       "planted directly beside the legitimate Russian distinction "
                       "between этажность and количество этажей, which differ by the "
                       "basement on purpose - so a model that treats every nearby "
                       "number as the same attribute produces a false positive on the "
                       "very next line while finding the real one.",
            evidence=(Evidence(2, S05_I1_A), Evidence(9, S05_I1_B)),
        ),
        SeededIssue(
            id="PC02-S05-I2",
            category=CATEGORY_PLACEHOLDER,
            attribute="назначение помещения 1.12",
            summary="Назначение помещения 1.12 оставлено как «не определено» на "
                    "странице 6.",
            why_seeded="An explicitly undetermined field with no conventional "
                       "placeholder token. It sits two pages from a filled sibling "
                       "room and one page from a sentence carrying the уточн stem "
                       "about a list that is complete, so both the recall and the "
                       "precision sides of the placeholder category are exercised in "
                       "one document.",
            evidence=(Evidence(6, S05_I2),),
        ),
    ),
    controls=(
        Control("PC02-S05-K1", (2,), S05_C1, "scope_dependent",
                "a storey count differing from этажность on the same page",
                "Этажность и количество этажей — разные показатели; подземный этаж "
                "в этажность не входит, разница в один этаж закономерна."),
        Control("PC02-S05-K2", (3,), S05_C2, "other_object",
                "a third storey count, read as contradicting the building's own",
                "Относится к корпусу 6."),
        Control("PC02-S05-K3", (5,), S05_C3, "sibling_filled",
                "a room-purpose line beside an undetermined one",
                "Назначение помещения 1.14 определено; пробел только у 1.12."),
        Control("PC02-S05-K4", (7,), S05_C4, "placeholder_stem",
                "the stem 'уточн', read as an unfilled field",
                "Перечень уже уточнён и приведён в таблице."),
        Control("PC02-S05-K5", (4, 8), S05_C5, "identical_repeat",
                "a fire-hazard class stated twice, read as two values",
                "Значение Ф4.3 повторено дословно."),
        Control("PC02-S05-K6", (10,), S05_C6, "excluded_by_text",
                "a rule about basements, read as contradicting the storey count",
                "Строка объясняет, почему количество этажей больше этажности, и сама "
                "значения не назначает."),
    ),
)


# --------------------------------------------------------------------------------------
# The nine control documents
#
# None carries a seeded issue. A correct analyzer reports nothing on any of them, and
# every finding raised against one is a false positive by construction. They are where
# the precision half of the P04 measurement actually comes from: the seeded documents
# supply nine positives, and these supply the denominator that makes a precision figure
# mean anything.
# --------------------------------------------------------------------------------------

C01_K1 = "Степень огнестойкости корпуса 6 — II."
C01_K2 = "Степень огнестойкости отдельно стоящей котельной — IV."
C01_K3 = "Степень огнестойкости навеса автостоянки не нормируется."

_define(
    "PC02-C01", "control",
    "Корпус 6. Общие архитектурные решения",
    "Синтетическая фикстура PC-02. Контрольный документ без заложенных проблем.",
    "Пять страниц. Три разные степени огнестойкости, каждая — у своего названного "
    "объекта. Расхождений нет.",
    (
        _page("Общие данные", F, Q(C01_K1), F, F),
        _page("Прочие строения и сооружения", F, Q(C01_K2), F, F),
        _page("Навесы и открытые сооружения", F, Q(C01_K3), F, F),
        _page("Пожарно-технические характеристики", F, Q(C01_K1), F, F),
    ),
    controls=(
        Control("PC02-C01-K1", (2, 5), C01_K1, "identical_repeat",
                "a fire-resistance degree stated twice, read as two values",
                "Значение II повторено дословно на двух страницах."),
        Control("PC02-C01-K2", (3,), C01_K2, "other_object",
                "a second fire-resistance degree, read as a contradiction",
                "Относится к отдельно стоящей котельной."),
        Control("PC02-C01-K3", (4,), C01_K3, "other_object",
                "a third fire-resistance statement, read as a contradiction",
                "Относится к навесу автостоянки, для которого степень не нормируется."),
    ),
)

C02_K1 = "Высота первого этажа корпуса 7 от пола до пола — 4,20 м."
C02_K2 = "Высота типового этажа корпуса 7 от пола до пола — 3,00 м."
C02_K3 = "Высота технического этажа корпуса 7 от пола до пола — 2,40 м."
C02_K4 = "Высота жилых помещений корпуса 7 в чистоте — не менее 2,70 м."
C02_K5 = "Высота помещений общественного назначения в чистоте — 3,00 м."

_define(
    "PC02-C02", "control",
    "Корпус 7. Высоты помещений и этажей",
    "Синтетическая фикстура PC-02. Контрольный документ без заложенных проблем.",
    "Шесть страниц. Пять разных высот, каждая со своей областью действия. "
    "Расхождений нет.",
    (
        _page("Высоты помещений и этажей", F, Q(C02_K1), F, F),
        _page("Типовой этаж", F, Q(C02_K2), F, F),
        _page("Технический этаж", F, Q(C02_K3), F, F),
        _page("Жилые помещения", F, Q(C02_K4), F, F),
        _page("Помещения общественного назначения", F, Q(C02_K5), F, F),
    ),
    controls=(
        Control("PC02-C02-K1", (2,), C02_K1, "scope_dependent",
                "the first of five heights, read as contradicting the others",
                "Относится к первому этажу."),
        Control("PC02-C02-K2", (3,), C02_K2, "scope_dependent",
                "a second storey height, read as a contradiction",
                "Относится к типовому этажу."),
        Control("PC02-C02-K3", (4,), C02_K3, "scope_dependent",
                "a third storey height, read as a contradiction",
                "Относится к техническому этажу."),
        Control("PC02-C02-K4", (5,), C02_K4, "scope_dependent",
                "a clear height stated as a minimum, read as contradicting a "
                "floor-to-floor height",
                "Высота в чистоте и высота от пола до пола — разные величины."),
        Control("PC02-C02-K5", (6,), C02_K5, "scope_dependent",
                "a clear height equal to another floor-to-floor height",
                "Относится к общественным помещениям; совпадение значений случайно "
                "и расхождением не является."),
    ),
)

C03_K1 = "Уточнённая ведомость заполнения проёмов приведена в приложении Б."
C03_K2 = "Тип заполнения проёмов уточнён при разработке и принят ПВХ."
C03_K3 = "Ведомость уточнений по проёмам закрыта, изменений не предусмотрено."
C03_K4 = "Возможна замена на алюминиевые витражи; проектом принято ПВХ."
C03_K5 = "Цвет профиля проёмов — RAL 7016, изменению не подлежит."

_define(
    "PC02-C03", "control",
    "Корпус 8. Заполнение проёмов",
    "Синтетическая фикстура PC-02. Контрольный документ без заложенных проблем.",
    "Шесть страниц, насыщенных корнем «уточн», при том что ни одно поле не "
    "оставлено незаполненным.",
    (
        _page("Заполнение проёмов", F, Q(C03_K1), F, F),
        _page("Принятые решения", F, Q(C03_K2), F, F),
        _page("Изменения и дополнения", F, Q(C03_K3), F, F),
        _page("Рассмотренные варианты", F, Q(C03_K4), F, F),
        _page("Колористическое решение", F, Q(C03_K5), F, F),
    ),
    controls=(
        Control("PC02-C03-K1", (2,), C03_K1, "placeholder_stem",
                "the stem 'уточн', read as an unfilled field",
                "Ведомость уточнена и приложена; решение принято."),
        Control("PC02-C03-K2", (3,), C03_K2, "placeholder_stem",
                "the stem 'уточн' beside a material choice",
                "Тип заполнения назван прямо в той же строке."),
        Control("PC02-C03-K3", (4,), C03_K3, "placeholder_stem",
                "the word 'уточнений' in a heading-like sentence",
                "Ведомость закрыта; строка сообщает об отсутствии изменений."),
        Control("PC02-C03-K4", (5,), C03_K4, "decided_alternative",
                "a mentioned alternative, read as an undecided choice",
                "Вариант назван и отклонён; принятое решение указано в той же строке."),
        Control("PC02-C03-K5", (6,), C03_K5, "decided_alternative",
                "a colour code, read as provisional",
                "Цвет зафиксирован и объявлен неизменяемым."),
    ),
)

C04_K1 = "Общая площадь здания корпуса 9 — 6 340,0 м²."
C04_K2 = "Общая площадь здания корпуса 9 составляет 6340,0 кв. м."
C04_K3 = "Площадь застройки корпуса 9 — 1 015,5 м²."
C04_K4 = "Строительный объём корпуса 9 — 24 120,0 м³."
C04_K5 = "Показатели корпуса 9 округлены до 0,1; итоги могут расходиться."
C04_K6 = "Общая площадь квартир корпуса 9 — 4 980,2 м², без учёта лоджий."

_define(
    "PC02-C04", "control",
    "Корпус 9. Технико-экономические показатели",
    "Синтетическая фикстура PC-02. Контрольный документ без заложенных проблем.",
    "Семь страниц с шестью числовыми показателями. Единственный повторённый "
    "показатель записан двумя способами с одним и тем же значением.",
    (
        _page("Технико-экономические показатели", F, Q(C04_K1), F, F),
        _page("Сводка показателей", F, Q(C04_K2), F, F),
        _page("Показатели участка", F, Q(C04_K3), F, F),
        _page("Объёмные показатели", F, Q(C04_K4), F, F),
        _page("Порядок подсчёта показателей", F, Q(C04_K5), F, F),
        _page("Площади квартир", F, Q(C04_K6), F, F),
    ),
    controls=(
        Control("PC02-C04-K1", (2,), C04_K1, "notation_variant",
                "a total area restated on another page, read as two values",
                "То же значение, что на странице 3, в записи с разделителем разрядов."),
        Control("PC02-C04-K2", (3,), C04_K2, "notation_variant",
                "the same total without a separator and as кв. м",
                "Значение совпадает со страницей 2; различается только запись."),
        Control("PC02-C04-K3", (4,), C04_K3, "other_object",
                "a second area figure, read as contradicting the total",
                "Площадь застройки — иной показатель."),
        Control("PC02-C04-K4", (5,), C04_K4, "other_object",
                "a volume figure, read as an area contradiction",
                "Строительный объём измеряется в кубических метрах."),
        Control("PC02-C04-K5", (6,), C04_K5, "tolerance_or_rounding",
                "an admission that sums may diverge",
                "Округление объявлено; расхождение итогов предусмотрено."),
        Control("PC02-C04-K6", (7,), C04_K6, "other_object",
                "a fourth area figure, read as contradicting the total",
                "Площадь квартир — иной показатель, и оговорено исключение лоджий."),
    ),
)

C05_K1 = "Из надземной части корпуса 10 предусмотрено два эвакуационных выхода."
C05_K2 = "Из подземной автостоянки предусмотрен один обособленный выход."
C05_K3 = "Выход из автостоянки в число выходов надземной части не входит."
C05_K4 = "Из корпуса 11 предусмотрено три эвакуационных выхода."

_define(
    "PC02-C05", "control",
    "Корпус 10. Эвакуация",
    "Синтетическая фикстура PC-02. Контрольный документ без заложенных проблем.",
    "Шесть страниц. Три разных числа выходов, разделённые по областям действия и "
    "явно исключённые друг из друга.",
    (
        _page("Эвакуация и пути эвакуации", F, Q(C05_K1), F, F),
        _page("Подземная автостоянка", F, Q(C05_K2), F, F),
        _page("Разграничение путей эвакуации", F, Q(C05_K3), F, F),
        _page("Надземная часть", F, Q(C05_K1), F, F),
        _page("Смежные корпуса", F, Q(C05_K4), F, F),
    ),
    controls=(
        Control("PC02-C05-K1", (2, 5), C05_K1, "identical_repeat",
                "an exit count stated twice, read as two values",
                "Строка повторена дословно."),
        Control("PC02-C05-K2", (3,), C05_K2, "scope_dependent",
                "a different exit count, read as contradicting the building's own",
                "Относится к подземной автостоянке."),
        Control("PC02-C05-K3", (4,), C05_K3, "excluded_by_text",
                "a sentence about exits, read as a third count",
                "Строка прямо исключает выход автостоянки из счёта надземной части."),
        Control("PC02-C05-K4", (6,), C05_K4, "other_object",
                "a third exit count, read as a contradiction",
                "Относится к корпусу 11."),
    ),
)

C06_K1 = "Настоящим листом принята толщина утеплителя стен корпуса 11 — 200 мм."
C06_K2 = "Ранее принятая толщина утеплителя 150 мм более не применяется."
C06_K3 = "Изменение внесено в раздел целиком и учтено во всех листах."
C06_K4 = "Толщина утеплителя стен корпуса 11 — 200 мм."

_define(
    "PC02-C06", "control",
    "Корпус 11. Конструктивные и отделочные решения",
    "Синтетическая фикстура PC-02. Контрольный документ без заложенных проблем.",
    "Пять страниц. Два значения толщины утеплителя, одно из которых документ "
    "прямо отменяет.",
    (
        _page("Теплозащита ограждающих конструкций", F, Q(C06_K1), F, F),
        _page("Изменения и дополнения", F, Q(C06_K2), F, F),
        _page("Порядок внесения изменений", F, Q(C06_K3), F, F),
        _page("Конструктивные решения", F, Q(C06_K4), F, F),
    ),
    controls=(
        Control("PC02-C06-K1", (2,), C06_K1, "superseded",
                "the live insulation thickness, read as contradicting the old one",
                "Значение принято настоящим листом и действует."),
        Control("PC02-C06-K2", (3,), C06_K2, "superseded",
                "a second insulation thickness, read as a live competing claim",
                "Значение прямо отменено и в сравнении не участвует."),
        Control("PC02-C06-K3", (4,), C06_K3, "absence_by_scope",
                "a change note, read as an incomplete record",
                "Строка подтверждает, что изменение учтено во всех листах."),
        Control("PC02-C06-K4", (5,), C06_K4, "identical_repeat",
                "the live thickness restated, read as a third value",
                "Значение совпадает со страницей 2."),
    ),
)

C07_K1 = "Расчёт инсоляции выполнен в отдельном томе и здесь не приводится."
C07_K2 = "Количество машино-мест приведено в разделе ПЗУ и не дублируется."
C07_K3 = "Сведения о наружных сетях в настоящий раздел не входят."
C07_K4 = "Раздел выполнен в объёме стадии П; рабочая документация выпускается позже."

_define(
    "PC02-C07", "control",
    "Корпус 12. Ссылки и разграничение разделов",
    "Синтетическая фикстура PC-02. Контрольный документ без заложенных проблем.",
    "Пять страниц, в которых четыре сведения отсутствуют по принадлежности к "
    "другим разделам. Незаполненных полей нет.",
    (
        _page("Сведения о смежных разделах", F, Q(C07_K1), F, F),
        _page("Разграничение с разделом ПЗУ", F, Q(C07_K2), F, F),
        _page("Наружные инженерные сети", F, Q(C07_K3), F, F),
        _page("Стадийность разработки", F, Q(C07_K4), F, F),
    ),
    controls=(
        Control("PC02-C07-K1", (2,), C07_K1, "absence_by_scope",
                "a missing calculation, read as an unfilled field",
                "Расчёт выполнен, но принадлежит другому тому."),
        Control("PC02-C07-K2", (3,), C07_K2, "absence_by_scope",
                "a missing count, read as an unfilled field",
                "Показатель определён в разделе ПЗУ и намеренно не дублируется."),
        Control("PC02-C07-K3", (4,), C07_K3, "absence_by_scope",
                "absent information, read as incompleteness",
                "Сведения не относятся к предмету раздела."),
        Control("PC02-C07-K4", (5,), C07_K4, "absence_by_scope",
                "a stage note, read as a document that is not finished",
                "Стадия П завершена в своём объёме; выпуск РД — следующая стадия, а "
                "не пробел в этом документе."),
    ),
)

C08_K1 = "Цвет фасадных кассет корпуса 13 — RAL 7040."
C08_K2 = "Цвет ограждений балконов корпуса 13 — RAL 7016."

_define(
    "PC02-C08", "control",
    "Корпус 13. Фасады и колористика",
    "Синтетическая фикстура PC-02. Контрольный документ без заложенных проблем.",
    "Восемь страниц обычного текста с двумя цветовыми кодами и без единой "
    "противоречивой пары. Самый длинный документ корпуса: он проверяет, молчит "
    "ли модель, когда находить нечего.",
    (
        _page("Колористическое решение фасадов", F, F, F, F),
        _page("Фасадные кассеты", F, Q(C08_K1), F, F),
        _page("Материалы и изделия", F, F, F, F),
        _page("Наружная отделка", F, F, F, F),
        _page("Фасадные кассеты нижних этажей", F, Q(C08_K1), F, F),
        _page("Ограждения балконов", F, Q(C08_K2), F, F),
        _page("Прочие элементы фасада", F, F, F, F),
    ),
    controls=(
        Control("PC02-C08-K1", (3, 6), C08_K1, "identical_repeat",
                "a colour code stated twice, read as two values",
                "Значение RAL 7040 повторено дословно."),
        Control("PC02-C08-K2", (7,), C08_K2, "other_object",
                "a second colour code, read as contradicting the fasade colour",
                "Относится к ограждениям балконов, а не к фасадным кассетам."),
    ),
)

C09_K1 = "Класс функциональной пожарной опасности корпуса 14 — Ф1.3."
C09_K2 = "Корпус 14 относится к классу Ф1.3 — многоквартирные жилые дома."
C09_K3 = "Встроенные помещения корпуса 14 отнесены к классу Ф4.3."
C09_K4 = "Класс конструктивной пожарной опасности корпуса 14 — С0."
C09_K5 = "Степень огнестойкости корпуса 14 — II."
C09_K6 = "Классы указаны для здания в целом; для ТП классы не нормируются."

_define(
    "PC02-C09", "control",
    "Корпус 14. Пожарно-технические характеристики",
    "Синтетическая фикстура PC-02. Контрольный документ без заложенных проблем.",
    "Семь страниц с шестью классификационными строками из трёх разных систем "
    "классификации. Ни одна пара не противоречива.",
    (
        _page("Пожарно-технические характеристики", F, Q(C09_K1), F, F),
        _page("Функциональное назначение", F, Q(C09_K2), F, F),
        _page("Встроенные помещения", F, Q(C09_K3), F, F),
        _page("Конструктивная пожарная опасность", F, Q(C09_K4), F, F),
        _page("Степень огнестойкости", F, Q(C09_K5), F, F),
        _page("Область применения классификации", F, Q(C09_K6), F, F),
    ),
    controls=(
        Control("PC02-C09-K1", (2,), C09_K1, "class_notation",
                "a class token, read as contradicting Ф4.3 or С0",
                "Класс функциональной пожарной опасности — отдельная система."),
        Control("PC02-C09-K2", (3,), C09_K2, "notation_variant",
                "the same class written in expanded form, read as a second claim",
                "Ф1.3 повторён с расшифровкой; значение то же."),
        Control("PC02-C09-K3", (4,), C09_K3, "scope_dependent",
                "a different functional class, read as a contradiction",
                "Относится к встроенным помещениям, а не к жилой части."),
        Control("PC02-C09-K4", (5,), C09_K4, "class_notation",
                "a structural class token, read as contradicting Ф1.3",
                "Конструктивная и функциональная пожарная опасность — разные системы."),
        Control("PC02-C09-K5", (6,), C09_K5, "class_notation",
                "a Roman numeral, read as contradicting С0",
                "Степень огнестойкости — третья система классификации."),
        Control("PC02-C09-K6", (7,), C09_K6, "excluded_by_text",
                "a scope sentence, read as an admission of a gap",
                "Строка ограничивает область применения классов и значений не "
                "назначает."),
    ),
)


# --------------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------------

def _assemble() -> tuple[Doc, ...]:
    cursor = _FillerCursor()
    docs: list[Doc] = []
    for definition in _DOC_DEFS:
        pages = _build_pages(
            definition["title"], definition["label"], definition["specs"], cursor
        )
        docs.append(Doc(
            label=definition["label"],
            role=definition["role"],
            title=definition["title"],
            subject=definition["subject"],
            footer=definition["label"] + "    Лист {page}    Синтетический документ",
            summary=definition["summary"],
            pages=pages,
            seeded=definition["seeded"],
            controls=definition["controls"],
        ))
    return tuple(docs)


DOCUMENTS: tuple[Doc, ...] = _assemble()


def seeded_documents() -> tuple[Doc, ...]:
    return tuple(d for d in DOCUMENTS if d.role == "seeded")


def control_documents() -> tuple[Doc, ...]:
    return tuple(d for d in DOCUMENTS if d.role == "control")


def all_quotations(doc: Doc) -> list[tuple[str, int, str]]:
    """(owner id, page, quotation) for every seeded issue and control in one document."""
    out: list[tuple[str, int, str]] = []
    for issue in doc.seeded:
        for ev in issue.evidence:
            out.append((issue.id, ev.page, ev.quotation))
    for control in doc.controls:
        for page in control.pages:
            out.append((control.id, page, control.quotation))
    return out


def document_characters() -> str:
    """Every character the corpus actually draws."""
    chars: set[str] = set()
    for doc in DOCUMENTS:
        for page in doc.pages:
            for line in page.lines:
                chars.update(line.text)
            chars.update(doc.footer.format(page=page.number))
    chars.discard("\n")
    return "".join(sorted(chars))
