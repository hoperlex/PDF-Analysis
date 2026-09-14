"""PC-02's negative-envelope documents: one fixture per envelope rule it violates.

These are **counted separately** from the measurable corpus and excluded from every
finding denominator (task `P4-QA-01`, deliverables; `PROTOTYPE_PROFILE.md` section 9).
They exist for one observation only: that the product refuses them explicitly, naming the
rule, rather than degrading into OCR or a silent partial read.

Attributable failure is the design constraint, inherited from session A4: a fixture that
violated two rules at once would prove nothing about which rule fired, and a regression
in one rule could hide behind another. `build_pc02_corpus.py` asserts against
`ar_corpus.envelope` that each violates exactly the rule it is named for, and that the
rule was genuinely *evaluated* rather than skipped.

PC-02 covers the four rules that a real submission actually trips: a scan, a password, a
document over 30 pages, and a file over 25 MiB. `ENV-PDF` - a text file or a ZIP - is
already covered by the PC-01 negative corpus and is not duplicated here.

These are PC-02's own bytes, not copies of PC-01's: the text, the metadata and the
document ids are PC-02's, so a fixture found in a log is attributable to one corpus.
"""

from __future__ import annotations

from dataclasses import dataclass

from ar_corpus import envelope, pdfwrite
from ar_corpus.negatives import _scan_bitmap
from ar_corpus.pdfwrite import Name

from . import content, layout

_BODY_SIZE = 11.0
_X = layout.MARGIN_LEFT
_TOP = layout.PAGE_HEIGHT - layout.MARGIN_TOP

# One page over the envelope, and comfortably past the size limit. Restated here so the
# fixtures overshoot the real numbers; `ar_corpus.envelope` owns the rules themselves.
_PAGES_OVER_LIMIT = envelope.MAX_PAGES + 1
_OVERSIZE_TARGET_BYTES = 26 * 1024 * 1024


@dataclass(frozen=True)
class NegativeFixture:
    label: str
    filename: str
    violates: str
    description: str
    why_it_matters: str
    data: bytes


def _lines(*texts: str) -> list[tuple[str, float, float, float]]:
    out: list[tuple[str, float, float, float]] = []
    y = _TOP
    for text in texts:
        out.append((text, _BODY_SIZE, _X, y))
        y -= _BODY_SIZE * 1.5
    return out


def _info(label: str, subject: str) -> dict[str, object]:
    return {
        "Title": pdfwrite.EncryptableString(f"PC-02 негативная фикстура {label}"),
        "Author": pdfwrite.EncryptableString(content.AUTHOR),
        "Subject": pdfwrite.EncryptableString(subject),
        "Keywords": pdfwrite.EncryptableString(
            f"synthetic; fixture; PC-02; negative-envelope; {label}"
        ),
        "Creator": pdfwrite.EncryptableString(layout.PRODUCER),
        "Producer": pdfwrite.EncryptableString(layout.PRODUCER),
        "CreationDate": pdfwrite.RawBytes(pdfwrite.pdf_literal(layout.CREATION_DATE)),
        "ModDate": pdfwrite.RawBytes(pdfwrite.pdf_literal(layout.CREATION_DATE)),
    }


def _simple_text_pdf(
    font: pdfwrite.EmbeddedFont,
    label: str,
    subject: str,
    pages: list[list[tuple[str, float, float, float]]],
    *,
    security: pdfwrite.StandardSecurity | None = None,
    extra_objects=None,
) -> bytes:
    """Build a PDF from explicit (text, size, x, y) placements per page."""
    pdf = pdfwrite.Pdf()
    catalog_ref = pdf.reserve()
    pages_ref = pdf.reserve()
    font_ref = pdfwrite.add_font(pdf, font)

    page_refs = []
    for placements in pages:
        stream = "".join(
            pdfwrite.show_text(font, layout.FONT_RESOURCE, text, size, x, y)
            for text, size, x, y in placements
        ).encode("ascii")
        content_ref = pdf.add_stream({}, stream)
        page_refs.append(pdf.add({
            "Type": Name("Page"),
            "Parent": pages_ref,
            "MediaBox": [0, 0, layout.PAGE_WIDTH, layout.PAGE_HEIGHT],
            "Resources": {"Font": {layout.FONT_RESOURCE: font_ref}},
            "Contents": content_ref,
        }))

    if extra_objects is not None:
        extra_objects(pdf)

    pdf.put(pages_ref, {
        "Type": Name("Pages"), "Kids": page_refs, "Count": len(page_refs),
    })
    pdf.put(catalog_ref, {
        "Type": Name("Catalog"),
        "Pages": pages_ref,
        "Lang": pdfwrite.RawBytes(pdfwrite.pdf_literal("ru-RU")),
    })
    return pdf.serialize(
        catalog_ref, _info(label, subject), layout.document_id(label), security=security
    )


def build_encrypted(font: pdfwrite.EmbeddedFont) -> bytes:
    """A password-protected PDF. Violates ENV-ENCRYPTED and nothing else.

    Two pages, both with a real text layer, well inside the size and page limits, so the
    only thing wrong with it is the password. The user password is not empty, so it
    cannot be opened by a reader that only tries the default one.
    """
    security = pdfwrite.StandardSecurity(
        user_password="synthetic-user-pw", owner_password="synthetic-owner-pw"
    )
    return _simple_text_pdf(
        font, "PC02-N01",
        "Негативная фикстура PC-02: документ защищён паролем.",
        [
            _lines(
                "Синтетическая негативная фикстура PC-02: зашифрованный документ.",
                "Файл защищён паролем и должен быть отклонён явно.",
                "Пароль пользователя: synthetic-user-pw",
                "Нарушено единственное правило: ENV-ENCRYPTED.",
            ),
            _lines(
                "Страница 2. Текстовый слой присутствует на обеих страницах.",
                "Все прочие правила конверта соблюдены.",
            ),
        ],
        security=security,
    )


def build_image_only(font: pdfwrite.EmbeddedFont) -> bytes:
    """A scanned-looking PDF with no text operators. Violates ENV-TEXT and nothing else.

    The `font` argument is deliberately unused for drawing: the point of this fixture is
    that OCR must never be silently substituted, so there is no text layer to fall back
    on and nothing for an extractor to find.
    """
    width, height = 827, 1170  # A4 at roughly 100 dpi
    pdf = pdfwrite.Pdf()
    catalog_ref = pdf.reserve()
    pages_ref = pdf.reserve()

    page_refs = []
    for index in range(2):
        image = _scan_bitmap(width, height, seed=2_000_003 + index)
        image_ref = pdf.add_stream({
            "Type": Name("XObject"),
            "Subtype": Name("Image"),
            "Width": width,
            "Height": height,
            "ColorSpace": Name("DeviceGray"),
            "BitsPerComponent": 1,
        }, image)
        stream = (
            f"q {pdfwrite.num(layout.PAGE_WIDTH)} 0 0 "
            f"{pdfwrite.num(layout.PAGE_HEIGHT)} 0 0 cm /Im1 Do Q\n"
        ).encode("ascii")
        content_ref = pdf.add_stream({}, stream)
        page_refs.append(pdf.add({
            "Type": Name("Page"),
            "Parent": pages_ref,
            "MediaBox": [0, 0, layout.PAGE_WIDTH, layout.PAGE_HEIGHT],
            "Resources": {"XObject": {"Im1": image_ref}},
            "Contents": content_ref,
        }))

    pdf.put(pages_ref, {
        "Type": Name("Pages"), "Kids": page_refs, "Count": len(page_refs),
    })
    pdf.put(catalog_ref, {"Type": Name("Catalog"), "Pages": pages_ref})
    return pdf.serialize(
        catalog_ref,
        _info("PC02-N02", "Негативная фикстура PC-02: страницы без текстового слоя."),
        layout.document_id("PC02-N02"),
    )


_PADDING_LINE = (
    b"%% synthetic PC-02 padding: this object exists only to carry the file past the "
    b"25 MiB envelope limit. It is unreferenced and holds no document content.\n"
)


def build_oversize(font: pdfwrite.EmbeddedFont) -> bytes:
    """A valid two-page text PDF carried past 25 MiB. Violates ENV-SIZE and nothing else.

    The bulk is one unreferenced, uncompressed stream of a repeating ASCII line. That
    keeps the fixture honest - it really is over the limit on disk, which is the only
    thing it has to prove - while staying cheap in Git, because the repository's own
    zlib compresses a repeating pattern to almost nothing.
    """
    repeats = _OVERSIZE_TARGET_BYTES // len(_PADDING_LINE) + 1
    padding = _PADDING_LINE * repeats

    def add_padding(pdf: pdfwrite.Pdf) -> None:
        pdf.add_stream({"Type": Name("SyntheticPadding")}, padding)

    return _simple_text_pdf(
        font, "PC02-N03",
        "Негативная фикстура PC-02: файл больше 25 МиБ.",
        [
            _lines(
                "Синтетическая негативная фикстура PC-02: превышение размера файла.",
                "Документ корректен во всём, кроме объёма: он больше 25 МиБ.",
                "Нарушено единственное правило: ENV-SIZE.",
            ),
            _lines(
                "Страница 2. Текстовый слой присутствует на каждой странице.",
                "Число страниц и отсутствие шифрования соответствуют конверту.",
            ),
        ],
        extra_objects=add_padding,
    )


def build_too_many_pages(font: pdfwrite.EmbeddedFont) -> bytes:
    """A 31-page text PDF. Violates ENV-PAGES and nothing else.

    Every page carries real text, so ENV-TEXT genuinely passes rather than being skipped:
    the fixture is one page over the limit and correct in every other respect. One page
    over, not fifty, because the interesting failure is the boundary.
    """
    pages = [
        _lines(
            f"Синтетическая негативная фикстура PC-02: страница {n} из "
            f"{_PAGES_OVER_LIMIT}.",
            "Документ превышает предел в 30 страниц ровно на одну страницу.",
            "Нарушено единственное правило: ENV-PAGES.",
        )
        for n in range(1, _PAGES_OVER_LIMIT + 1)
    ]
    return _simple_text_pdf(
        font, "PC02-N04",
        "Негативная фикстура PC-02: документ длиннее 30 страниц.",
        pages,
    )


def build_all(font: pdfwrite.EmbeddedFont) -> list[NegativeFixture]:
    return [
        NegativeFixture(
            label="PC02-N01",
            filename="PC02-N01-encrypted.pdf",
            violates=envelope.RULE_NOT_ENCRYPTED,
            description="Двухстраничный PDF, защищённый паролем пользователя "
                        "synthetic-user-pw и паролем владельца synthetic-owner-pw.",
            why_it_matters="A password-protected submission is the most common "
                           "over-the-wall failure in practice. The observation is that "
                           "the product says so, and does not report a page count it "
                           "cannot have read.",
            data=build_encrypted(font),
        ),
        NegativeFixture(
            label="PC02-N02",
            filename="PC02-N02-image-only.pdf",
            violates=envelope.RULE_TEXT_LAYER,
            description="Двухстраничный PDF, каждая страница — растровое изображение "
                        "без единого текстового оператора.",
            why_it_matters="The scanned-drawing case. PROTOTYPE_PROFILE.md section 7.1 "
                           "forbids silently substituting OCR, so the only acceptable "
                           "behaviour is an explicit refusal naming ENV-TEXT.",
            data=build_image_only(font),
        ),
        NegativeFixture(
            label="PC02-N03",
            filename="PC02-N03-oversize.pdf",
            violates=envelope.RULE_MAX_BYTES,
            description="Корректный двухстраничный PDF, доведённый до размера свыше "
                        "25 МиБ одним несвязанным потоком-заполнителем.",
            why_it_matters="Size is the rule most likely to be checked late, after the "
                           "bytes have already been read into memory. The fixture is "
                           "genuinely oversized on disk rather than merely declared so.",
            data=build_oversize(font),
        ),
        NegativeFixture(
            label="PC02-N04",
            filename="PC02-N04-too-many-pages.pdf",
            violates=envelope.RULE_MAX_PAGES,
            description="PDF из 31 страницы, каждая с текстовым слоем: ровно на одну "
                        "страницу больше предела.",
            why_it_matters="One page over the limit, because the interesting failure is "
                           "the boundary rather than an obvious excess.",
            data=build_too_many_pages(font),
        ),
    ]
