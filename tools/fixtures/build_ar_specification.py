#!/usr/bin/env python3
"""Build the synthetic AR bundle that carries a Form-7 specification table (`SPEC-TABLE-RECORDING-01`).

    python3 tools/fixtures/build_ar_specification.py           # write the fixtures
    python3 tools/fixtures/build_ar_specification.py --check   # verify, write nothing

The baseline AR corpus (`build_ar_corpus.py`) has no specification table, so a project holding
only that document reaches «Спецификация и цены» with nothing to read and an optimisation pass
holds no proposals. This builder writes a second, **synthetic** AR set beside it, in
`fixtures/synthetic/ar_specification/`:

* `ar_specification.pdf` -- four pages: a title sheet, general data (one seeded `уточнить`), and a
  Form-7 specification of seven positions over two sheets. The first sheet has the header
  (split over two lines, as the print has it), a row whose name wraps *above* its anchor line, a
  manufacturer written with its legal form; the second sheet continues the table **without** a
  repeated header, as the numbering and the group heading show;
* `ar_specification.zip` -- the portal bundle around that PDF (all five members);
* `ar_specification_prices.csv` -- a price list for it: positions of the same normalised units,
  cheaper analogs from a vendor, one unit mismatch (`п.м` against `м`), one row without a
  price, one row without a numeric quantity;
* `expected_specification.json` -- the oracle: the rows the extractor must read, how each one
  matches, the totals, and the proposals an optimisation pass must hold -- every figure computed
  here from the authored numbers, never read from the product;
* `SHA256SUMS` -- the digest of every file above.

Everything is invented: no customer, production or real project bytes, and no real
organisation, address or person (owner decision OD-17). The vendors `Промет`, `Завод Север`
and `Нева-Строй` are fictional.

Like the corpus builder it is pure standard library and byte-deterministic (fixed dates, fixed
document id, a committed font subset, no PRNG), and `--check` re-derives every file and
compares it with the committed bytes, then reads the committed PDF back with the independent
extractor and checks every authored line is in its text layer, in order.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ar_corpus  # noqa: E402
from ar_corpus import content, document, envelope, pdfextract, pdfwrite  # noqa: E402
from ar_corpus.pdfwrite import Name, Pdf, Ref  # noqa: E402
from portal_bundle import portal_format as fmt  # noqa: E402
from portal_bundle.blocklist import Block  # noqa: E402
from portal_bundle.bundle import STAMP_CONTEXT, build_bundle, make_files  # noqa: E402

REPO_ROOT = build_ar_corpus.REPO_ROOT
OUT_DIR = REPO_ROOT / "fixtures" / "synthetic" / "ar_specification"
RELATIVE_DIR = "fixtures/synthetic/ar_specification"

STEM = "ar_specification"
PDF_NAME = f"{STEM}.pdf"
BUNDLE_NAME = f"{STEM}.zip"
PRICES_NAME = f"{STEM}_prices.csv"
ORACLE_NAME = "expected_specification.json"
CHECKSUM_NAME = "SHA256SUMS"
ORACLE_SCHEMA = "ar-specification-expected/1"

#: What the expert confirms when classifying the uploaded version.
PROJECT_STAGE = "P"
SECTION_CODE = "AR"
#: The AR vendor list the journey sets (a project override): the one vendor the analogs come from.
VENDOR_LIST = ("Завод Север",)
DEFAULT_CURRENCY = "RUB"

TITLE = "СП-7-АР-С. Раздел 3. Спецификация (синтетический документ)"
AUTHOR = "СИНТЕТИКПРОЕКТ (вымышленная организация)"
SUBJECT = "Синтетическая фикстура: AR с таблицей спецификации формы 7. Не проектная документация."
PRODUCER = "PDF-Analysis synthetic AR specification generator (tools/fixtures)"
DOC_ID = hashlib.sha256(b"ar_specification").digest()[:16]

H1, H2, BODY, TABLE, SMALL = 13.0, 11.5, 10.5, 8.5, 8.0
FOOTER_SIZE = 8.0
STAMP_TOP_Y = 150.0  # the title block sits above the footer, below the table
STAMP_STEP = 11.0

#: The one seeded issue: an explicit placeholder on page 2 (the recorded model answer names it).
PLACEHOLDER_PAGE = 2
PLACEHOLDER_QUOTE = "1.3. Тип светопрозрачного заполнения — уточнить."


@dataclass(frozen=True)
class Page:
    lines: tuple[content.Line, ...]
    stamp: tuple[str, ...] = ()


def _stamp(sheet: int) -> tuple[str, ...]:
    return (
        "Изм. Кол.уч. Лист №док. Подпись Дата",
        "Разработал Образцов 01.26",
        "Стадия Лист Листов",
        f"П {sheet} 4",
    )


def _lines(*texts: str, size: float = TABLE) -> tuple[content.Line, ...]:
    return tuple(content.Line(text, size) for text in texts)


HEADER = (
    "Поз. Наименование и техническая характеристика Тип, марка Код Завод- Ед. Кол. Масса Примечание",
    "изготовитель изм. 1 ед., кг",
    "1 2 3 4 5 6 7 8 9",
)

#: The Form-7 rows exactly as the sheets print them. A name that wraps above its anchor line
#: is printed as the line above the anchored one.
SHEET_3 = (
    "Изделия",
    "1 Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет» шт. 4 45,5",
    "Окно ПВХ двухкамерное",
    "2 ОП В2 1460х1460 шт 12",
    "3 Анкер химический ООО «Промет» шт 200 0,05",
)
SHEET_4 = (
    "Материалы",
    "4 Профиль направляющий ПН 50х40 п. м 120",
    "5 Решётка вентиляционная РВ-200 шт 6",
    "6 Монтажная пена компл. - по месту",
    "7 Гидроизоляционная мембрана Техноэласт ЭПП м² 340,8",
)

PAGES = (
    Page(
        (
            content.Line("ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «СИНТЕТИКПРОЕКТ»", H2, center=True),
            content.Line("вымышленная организация; реальному юридическому лицу не соответствует",
                         SMALL, center=True),
            content.Line("", BODY, space_before=48.0),
            content.Line("Объект: административное здание (синтетический объект)", BODY, center=True),
            content.Line("Условная площадка № 2, квартал СП-7", BODY, center=True),
            content.Line("", BODY, space_before=40.0),
            content.Line("ПРОЕКТНАЯ ДОКУМЕНТАЦИЯ", H1, center=True),
            content.Line("Раздел 3. Архитектурные решения. Спецификация", H2, space_before=8.0,
                         center=True),
            content.Line("Шифр СП-7-АР-С", BODY, space_before=8.0, center=True),
            content.Line("", BODY, space_before=40.0),
            content.Line("Стадия: П", BODY, center=True),
            content.Line("Том 3", BODY, center=True),
            content.Line("", BODY, space_before=60.0),
            content.Line("СИНТЕТИЧЕСКИЙ ДОКУМЕНТ.", SMALL, center=True),
            content.Line("Создан генератором tools/fixtures/build_ar_specification.py для проверки",
                         SMALL, center=True),
            content.Line("спецификации и цен. Проектной документацией не является и для",
                         SMALL, center=True),
            content.Line("строительства не применяется.", SMALL, center=True),
        ),
    ),
    Page(
        (
            content.Line("1. ОБЩИЕ ДАННЫЕ", H1),
            content.Line("1.1. Спецификация оборудования, изделий и материалов приведена на листах 3 и 4.",
                         BODY, space_before=14.0),
            content.Line("1.2. Цены в спецификацию не включаются: сопоставление с прайс-листом", BODY,
                         space_before=4.0),
            content.Line("выполняется отдельно и не меняет проектных решений.", BODY, indent=18.0),
            content.Line(PLACEHOLDER_QUOTE, BODY, space_before=4.0),
            content.Line("1.4. Замена изделий на равноценные допускается по согласованию", BODY,
                         space_before=4.0),
            content.Line("с проектировщиком.", BODY, indent=18.0),
        ),
    ),
    Page(
        (
            content.Line("Спецификация оборудования, изделий и материалов", H2),
            content.Line("", TABLE, space_before=6.0),
            *_lines(*HEADER, *SHEET_3),
        ),
        _stamp(3),
    ),
    Page(_lines(*SHEET_4), _stamp(4)),
)

FOOTER = "СП-7-АР-С    Лист {page}    Синтетический документ"

# --------------------------------------------------------------------------------------
# The price list, and what each specification row is expected to do against it
# --------------------------------------------------------------------------------------

PRICE_HEADER = "Код;Наименование;Марка;Ед. изм.;Цена;Валюта;Поставщик"
#: (name, mark, unit, price, vendor) -- the price column is printed with a decimal comma.
PRICE_POSITIONS = (
    ("Дверь противопожарная", "ДПМ-01/60", "шт", "25000", "ООО «Промет»"),
    ("Дверь противопожарная", "ДПМ-02/60", "шт", "21000", "Завод Север"),
    ("Окно ПВХ двухкамерное ОП В2 1460х1460", "", "шт", "18500", "Нева-Строй"),
    ("Окно ПВХ двухкамерное ОП В2 1560х1460", "", "шт", "17200", "Завод Север"),
    ("Анкер химический", "", "шт", "12.75", "Промет"),
    ("Анкер химический усиленный", "", "шт", "9.5", "Завод Север"),
    ("Профиль направляющий ПН 50х40", "", "м", "310", "Завод Север"),
    ("Монтажная пена", "", "компл", "450", "ООО «Промет»"),
    ("Монтажная пена армированная", "", "компл", "300", "Завод Север"),
    ("Гидроизоляционная мембрана Техноэласт ЭПП", "", "м2", "410", "ООО «Промет»"),
)


@dataclass(frozen=True)
class ExpectedRow:
    """One specification row, the way the extractor must read it, and how it prices."""

    position: str
    page: int
    name: str
    unit: str
    quantity: str | None  # None: the printed quantity is not a plain number
    quantity_text: str
    manufacturer: str | None
    #: matched / unmatched, with the reason of an unmatched row.
    status: str
    reason: str | None
    basis: str | None
    price: str | None  # the matched position's unit price
    analog_price: str | None  # the cheaper analog's unit price, when a proposal exists
    analog_basis: str | None
    analog_vendor: str | None


EXPECTED_ROWS = (
    ExpectedRow("1", 3, "Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет»", "шт", "4", "4",
                "ООО «Промет»", "matched", None, "mark", "25000", "21000", "code_family", "Завод Север"),
    ExpectedRow("2", 3, "Окно ПВХ двухкамерное ОП В2 1460х1460", "шт", "12", "12", None,
                "matched", None, "name", "18500", "17200", "name_similarity", "Завод Север"),
    ExpectedRow("3", 3, "Анкер химический ООО «Промет»", "шт", "200", "200", "ООО «Промет»",
                "matched", None, "name", "12.75", "9.5", "name_similarity", "Завод Север"),
    ExpectedRow("4", 4, "Профиль направляющий ПН 50х40", "п.м", "120", "120", None,
                "unmatched", "unit_mismatch", None, None, None, None, None),
    ExpectedRow("5", 4, "Решётка вентиляционная РВ-200", "шт", "6", "6", None,
                "unmatched", "no_position", None, None, None, None, None),
    ExpectedRow("6", 4, "Монтажная пена", "компл", None, "-", None,
                "matched", None, "name", "450", "300", "name_similarity", "Завод Север"),
    ExpectedRow("7", 4, "Гидроизоляционная мембрана Техноэласт ЭПП", "м2", "340.8", "340,8", None,
                "matched", None, "name", "410", None, None, None),
)
SHEET_LABELS = {3: "3", 4: "4"}


def price_list_csv() -> bytes:
    lines = [PRICE_HEADER]
    for name, mark, unit, price, vendor in PRICE_POSITIONS:
        lines.append(f";{name};{mark};{unit};{price.replace('.', ',')};{DEFAULT_CURRENCY};{vendor}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _plain(value: Decimal) -> str:
    """An exact decimal as plain text without trailing zeros (the API's money form)."""
    text = format(value.normalize(), "f")
    return text


def oracle(pdf: bytes, bundle: bytes, prices: bytes) -> dict[str, object]:
    """The expected extraction, matching, totals and proposals, computed from the authored numbers."""
    rows: list[dict[str, object]] = []
    proposals: list[dict[str, object]] = []
    total = Decimal(0)
    counted = 0
    excluded = {"no_position": 0, "unit_mismatch": 0, "row_unit_missing": 0, "ambiguous": 0,
                "quantity_not_numeric": 0}
    for expected in EXPECTED_ROWS:
        quantity = None if expected.quantity is None else Decimal(expected.quantity)
        price = None if expected.price is None else Decimal(expected.price)
        amount = None
        reason = expected.reason
        if expected.status == "matched" and quantity is not None and price is not None:
            amount = quantity * price
            total += amount
            counted += 1
        elif expected.status == "matched":
            reason = "quantity_not_numeric"
        if amount is None and reason is not None:
            excluded[reason] += 1
        rows.append({
            "position": expected.position,
            "page": expected.page,
            "sheet_label": SHEET_LABELS[expected.page],
            "name": expected.name,
            "unit": expected.unit,
            "quantity_text": expected.quantity_text,
            "quantity": expected.quantity,
            "manufacturer": expected.manufacturer,
            "status": expected.status,
            "reason": expected.reason,
            "basis": expected.basis,
            "unit_price": expected.price,
            "amount": None if amount is None else _plain(amount),
            "excluded_reason": None if amount is not None else reason,
        })
        if expected.analog_price is not None:
            assert price is not None
            analog = Decimal(expected.analog_price)
            saving = None if quantity is None else (price - analog) * quantity
            proposals.append({
                "ordinal": len(proposals) + 1,
                "row_position": expected.position,
                "proposal_type": "cheaper_analog",
                "analog_basis": expected.analog_basis,
                "proposed_vendor": expected.analog_vendor,
                "unit": expected.unit,
                "currency": DEFAULT_CURRENCY,
                "quantity": expected.quantity,
                "current_unit_price": expected.price,
                "proposed_unit_price": expected.analog_price,
                "saving": None if saving is None else _plain(saving),
            })
    return {
        "schema": ORACLE_SCHEMA,
        "synthetic": True,
        "notice": (
            "Synthetic. Every figure is computed by tools/fixtures/build_ar_specification.py from "
            "the authored numbers, not read from the product. The vendors are fictional; no "
            "customer, production or real project bytes (owner decision OD-17)."
        ),
        "generated_by": "tools/fixtures/build_ar_specification.py",
        "regenerate": "python3 tools/fixtures/build_ar_specification.py",
        "verify": "python3 tools/fixtures/build_ar_specification.py --check",
        "files": {
            "pdf": _file_entry(PDF_NAME, pdf),
            "bundle": _file_entry(BUNDLE_NAME, bundle),
            "price_list": _file_entry(PRICES_NAME, prices),
        },
        "journey": {
            "classification": {"project_stage": PROJECT_STAGE, "section_code": SECTION_CODE},
            "price_list_default_currency": DEFAULT_CURRENCY,
            "project_vendor_list": [{"vendor": vendor} for vendor in VENDOR_LIST],
            "recorded_response": "fixtures/recorded/sections/ar_specification/",
        },
        "price_list_positions": len(PRICE_POSITIONS),
        "specification": {
            "algorithm": "specification-text-v1",
            "pages": [3, 4],
            "table_count": 1,
            "continued_on": [4],
            "row_count": len(EXPECTED_ROWS),
            "rows": rows,
        },
        "matching": {
            "algorithm": "price-match-v1",
            "counts": {
                "matched": sum(1 for row in EXPECTED_ROWS if row.status == "matched"),
                "ambiguous": 0,
                "unmatched": sum(1 for row in EXPECTED_ROWS if row.status == "unmatched"),
            },
            "totals": [{"currency": DEFAULT_CURRENCY, "amount": _plain(total), "row_count": counted}],
            "excluded": excluded,
        },
        "proposals": {
            "generator": "cheaper-analog-v1",
            "count": len(proposals),
            "items": proposals,
            "total_saving": {
                "currency": DEFAULT_CURRENCY,
                "amount": _plain(sum((Decimal(str(p["saving"])) for p in proposals if p["saving"] is not None),
                                     Decimal(0))),
            },
        },
        "seeded_observation": {"page": PLACEHOLDER_PAGE, "quote": PLACEHOLDER_QUOTE,
                               "category": "explicit_placeholder"},
    }


def _file_entry(name: str, data: bytes) -> dict[str, object]:
    return {"path": f"{RELATIVE_DIR}/{name}", "sha256": sha256(data), "bytes": len(data)}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------------------
# The PDF
# --------------------------------------------------------------------------------------


def _all_texts() -> list[str]:
    texts = [line.text for page in PAGES for line in page.lines if line.text]
    for page in PAGES:
        texts.extend(page.stamp)
    return texts


def check_repertoire(font: pdfwrite.EmbeddedFont) -> None:
    footer = "".join(FOOTER.format(page=n) for n in range(1, len(PAGES) + 1))
    missing = sorted(set("".join(_all_texts()) + footer) - set(font.char_to_gid))
    if missing:
        raise build_ar_corpus.BuildError(
            f"the committed font subset has no glyph for {''.join(missing)!r}; the text of "
            "tools/fixtures/build_ar_specification.py drifted outside the declared repertoire"
        )


def place(font: pdfwrite.EmbeddedFont, index: int) -> list[tuple[str, float, float, float]]:
    """The absolute placement of every line of one page, top to bottom, then its stamp."""
    page = PAGES[index]
    placed: list[tuple[str, float, float, float]] = []
    y = document.PAGE_HEIGHT - document.MARGIN_TOP
    for line in page.lines:
        y -= line.space_before + line.size * document.LINE_HEIGHT_FACTOR
        if not line.text:
            continue
        if line.center:
            x = document.MARGIN_LEFT + (document.TEXT_WIDTH - font.text_width(line.text, line.size)) / 2.0
        else:
            x = document.MARGIN_LEFT + line.indent
        placed.append((line.text, line.size, round(x, 3), round(y, 3)))
    for step, text in enumerate(page.stamp):
        placed.append((text, TABLE, document.MARGIN_LEFT, round(STAMP_TOP_Y - step * STAMP_STEP, 3)))
    footer = FOOTER.format(page=index + 1)
    placed.append((footer, FOOTER_SIZE, document.MARGIN_LEFT, document.FOOTER_BASELINE))
    return placed


def too_wide(font: pdfwrite.EmbeddedFont) -> list[str]:
    out = []
    for index in range(len(PAGES)):
        for text, size, x, _y in place(font, index):
            if x + font.text_width(text, size) > document.PAGE_WIDTH - document.MARGIN_RIGHT + 0.01:
                out.append(f"page {index + 1}: {text!r}")
    return out


def build_pdf(font: pdfwrite.EmbeddedFont) -> bytes:
    check_repertoire(font)
    overflow = too_wide(font)
    if overflow:
        raise build_ar_corpus.BuildError("lines would overflow the text box:\n  " + "\n  ".join(overflow))
    pdf = Pdf()
    catalog_ref = pdf.reserve()
    pages_ref = pdf.reserve()
    font_ref = pdfwrite.add_font(pdf, font)
    page_refs: list[Ref] = []
    for index in range(len(PAGES)):
        stream = "".join(
            pdfwrite.show_text(font, document.FONT_RESOURCE, text, size, x, y)
            for text, size, x, y in place(font, index)
        ).encode("ascii")
        content_ref = pdf.add_stream({}, stream)
        page_refs.append(pdf.add({
            "Type": Name("Page"),
            "Parent": pages_ref,
            "MediaBox": [0, 0, document.PAGE_WIDTH, document.PAGE_HEIGHT],
            "Resources": {"Font": {document.FONT_RESOURCE: font_ref}},
            "Contents": content_ref,
        }))
    pdf.put(pages_ref, {"Type": Name("Pages"), "Kids": page_refs, "Count": len(page_refs)})
    pdf.put(catalog_ref, {
        "Type": Name("Catalog"),
        "Pages": pages_ref,
        "Lang": pdfwrite.RawBytes(pdfwrite.pdf_literal("ru-RU")),
    })
    info = {
        "Title": pdfwrite.EncryptableString(TITLE),
        "Author": pdfwrite.EncryptableString(AUTHOR),
        "Subject": pdfwrite.EncryptableString(SUBJECT),
        "Keywords": pdfwrite.EncryptableString("synthetic; fixture; АР; спецификация; форма 7"),
        "Creator": pdfwrite.EncryptableString(PRODUCER),
        "Producer": pdfwrite.EncryptableString(PRODUCER),
        "CreationDate": pdfwrite.RawBytes(pdfwrite.pdf_literal(document.CREATION_DATE)),
        "ModDate": pdfwrite.RawBytes(pdfwrite.pdf_literal(document.CREATION_DATE)),
    }
    return pdf.serialize(catalog_ref, info, DOC_ID)


def expected_page_lines(font: pdfwrite.EmbeddedFont) -> list[list[str]]:
    """Every page's lines in the order a reader returns them: top to bottom by baseline."""
    result = []
    for index in range(len(PAGES)):
        result.append([text for text, _s, _x, _y in sorted(place(font, index), key=lambda item: -item[3])])
    return result


def verify_text_layer(font: pdfwrite.EmbeddedFont, pdf: bytes) -> list[str]:
    """The text layer read back from the bytes equals the authored lines, page by page."""
    problems = []
    extracted = pdfextract.extract_pages(pdf)
    wanted = expected_page_lines(font)
    if len(extracted) != len(wanted):
        return [f"extracted {len(extracted)} pages, authored {len(wanted)}"]
    for number, (text, lines) in enumerate(zip(extracted, wanted), start=1):
        if text.split("\n") != lines:
            problems.append(f"page {number}: the extracted lines differ from the authored ones")
    placeholder_pages = [n for n, text in enumerate(extracted, start=1) if PLACEHOLDER_QUOTE in text]
    if placeholder_pages != [PLACEHOLDER_PAGE]:
        problems.append(f"the placeholder is on pages {placeholder_pages}, expected [{PLACEHOLDER_PAGE}]")
    return problems


# --------------------------------------------------------------------------------------
# The bundle
# --------------------------------------------------------------------------------------


def _stamp_block(page_index: int) -> Block:
    return Block(
        fmt.KIND_STAMP, page_index, (0.50, 0.86, 0.905, 0.945),
        fields=(("code", STAMP_CONTEXT.code), ("stage", STAMP_CONTEXT.stage),
                ("sheet", "" if page_index == 0 else str(page_index + 1)),
                ("object", STAMP_CONTEXT.obj), ("organization", STAMP_CONTEXT.organization)),
    )


def build_zip(pdf: bytes) -> bytes:
    files = make_files(
        pdf, STEM, extra_blocks=[_stamp_block(2), _stamp_block(3)], stamp=STAMP_CONTEXT,
        html=True, stamp_audit=True,
    )
    return build_bundle(files).data


# --------------------------------------------------------------------------------------
# Build and check
# --------------------------------------------------------------------------------------


def build_all() -> list[tuple[Path, bytes]]:
    font = build_ar_corpus.load_font()
    pdf = build_pdf(font)
    problems = verify_text_layer(font, pdf)
    if problems:
        raise build_ar_corpus.BuildError("the text layer:\n  " + "\n  ".join(problems))
    report = envelope.check(pdf)
    if not report.accepted:
        raise build_ar_corpus.BuildError(f"the PDF violates the envelope: {report.violations}")
    bundle = build_zip(pdf)
    prices = price_list_csv()
    oracle_bytes = (json.dumps(oracle(pdf, bundle, prices), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    artefacts = [
        (OUT_DIR / PDF_NAME, pdf),
        (OUT_DIR / BUNDLE_NAME, bundle),
        (OUT_DIR / PRICES_NAME, prices),
        (OUT_DIR / ORACLE_NAME, oracle_bytes),
    ]
    sums = "\n".join(f"{sha256(data)}  {path.name}" for path, data in artefacts) + "\n"
    artefacts.append((OUT_DIR / CHECKSUM_NAME, sums.encode("utf-8")))
    return artefacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the synthetic AR specification fixtures.")
    parser.add_argument("--check", action="store_true",
                        help="verify the committed files against a fresh build; write nothing")
    args = parser.parse_args(argv)
    try:
        artefacts = build_all()
    except (build_ar_corpus.BuildError, ValueError, KeyError, AssertionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.check:
        failures: list[str] = []
        for path, data in artefacts:
            relative = path.relative_to(REPO_ROOT)
            if not path.is_file():
                failures.append(f"{relative}: missing")
            elif path.read_bytes() != data:
                failures.append(f"{relative}: committed sha256 {sha256(path.read_bytes())} != rebuilt {sha256(data)}")
        committed = OUT_DIR / PDF_NAME
        if committed.is_file():
            try:
                font = build_ar_corpus.load_font()
                failures += [f"committed PDF: {problem}"
                             for problem in verify_text_layer(font, committed.read_bytes())]
            except pdfextract.PdfParseError as exc:
                failures.append(f"committed PDF is not readable: {exc}")
        if failures:
            print("FAIL: the committed fixtures do not match a fresh build:", file=sys.stderr)
            for failure in failures:
                print(f"  {failure}", file=sys.stderr)
            return 1
        for path, data in artefacts:
            print(f"OK  {path.relative_to(REPO_ROOT)}  {sha256(data)}  {len(data)} bytes")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, data in artefacts:
        path.write_bytes(data)
        print(f"wrote {path.relative_to(REPO_ROOT)}  {sha256(data)}  {len(data)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
