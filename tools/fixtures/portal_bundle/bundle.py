"""Assemble a portal bundle: the portal's files for one PDF, then the archive that carries them.

Two steps, kept apart because the negatives need the first without the second:

*   `make_files` builds the five members' bytes for a PDF -- one TEXT block per page that
    has a text layer, the block list, the matching markdown, optionally IMAGE and STAMP
    blocks, the HTML and the stamp audit;
*   `pack` turns those into archive members, in the name encoding asked for, and
    `build_bundle` writes the archive and then asks the validator whether it is what the
    caller said it would be.

That last check is the generator's own guard: it refuses to hand back a bundle that the
validator rejects, unless the caller named the rule the bundle is meant to break.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ar_corpus import document

from . import blocklist, results, stampaudit, validate, zipwrite
from . import portal_format as fmt
from .blocklist import Block
from .pdffacts import PageFacts, read_pages

DISPLAY_PATH = "Синтетический набор / [АР] Архитектурные решения / {stem}"

# The generator's own validation runs under permissive bounds. They are not INGEST's.
GENERATOR_LIMITS = validate.Limits(member_bytes=fmt.MAX_UPLOAD_BYTES,
                                   stamp_audit_bytes=fmt.MiB)

# Where the text sits on the corpus' pages, as a share of the page, from the layout's own
# margins. A TEXT block covers it; an IMAGE or STAMP block is placed against it.
TEXT_REGION = (
    round(document.MARGIN_LEFT / document.PAGE_WIDTH, 4),
    round(document.MARGIN_TOP / document.PAGE_HEIGHT, 4),
    round(1 - document.MARGIN_RIGHT / document.PAGE_WIDTH, 4),
    round(1 - (document.FOOTER_BASELINE - 8) / document.PAGE_HEIGHT, 4),
)

NAME_ENCODINGS = ("utf8_flag", "infozip_unicode", "utf8_plain", "cp866")

STAMP_CONTEXT = results.StampContext(
    code="СП-7-АР", stage="П",
    obj="многоквартирный жилой дом на 64 квартиры (синтетический объект)",
    organization="СИНТЕТИКПРОЕКТ (вымышленная организация)",
)


class BundleError(RuntimeError):
    """A bundle that is not what it was asked to be."""


@dataclass(frozen=True)
class SeededDefect:
    """A deliberate flaw in a block's recognised text, for the lanes that flag such flaws."""

    page_index: int
    kind: str
    original: str
    recognised: str
    flaggable: bool
    block_id: str = ""


@dataclass(frozen=True)
class PortalFiles:
    """The members of one bundle, as bytes, and the facts they were built from."""

    stem: str
    pdf: bytes
    blocks_json: bytes
    results_md: bytes
    results_html: bytes | None
    stamp_audit: bytes | None
    page_count: int
    blocks: tuple[Block, ...]
    defects: tuple[SeededDefect, ...] = ()

    def member_bytes(self) -> dict[str, bytes]:
        present = {
            fmt.ROLE_PDF: self.pdf, fmt.ROLE_BLOCKS: self.blocks_json,
            fmt.ROLE_RESULTS_MD: self.results_md, fmt.ROLE_RESULTS_HTML: self.results_html,
            fmt.ROLE_STAMP_AUDIT: self.stamp_audit,
        }
        return {role: data for role, data in present.items() if data is not None}


def text_blocks(
    pages: Sequence[PageFacts], *, only: Sequence[int] | None = None,
    bodies: Mapping[int, str] | None = None,
) -> list[Block]:
    """One TEXT block per page, carrying the page's text layer unless told otherwise.

    `only` names the pages that get a block (default: those with a text layer);
    `bodies` replaces a page's text, which is how a recognised text comes to differ from
    the layer it was read from.
    """
    chosen = [i for i, p in enumerate(pages) if p.has_text] if only is None else list(only)
    return [
        Block(fmt.KIND_TEXT, i, TEXT_REGION,
              text=(bodies or {}).get(i, pages[i].text))
        for i in chosen
    ]


def make_files(
    pdf: bytes, stem: str, *,
    pages: Sequence[PageFacts] | None = None,
    blocks: Sequence[Block] | None = None,
    extra_blocks: Sequence[Block] = (),
    stamp: results.StampContext | None = None,
    html: bool = False,
    stamp_audit: bool = False,
    defects: Sequence[SeededDefect] = (),
) -> PortalFiles:
    """Build the portal's files for `pdf`.

    `pages` defaults to what the independent extractor reads from the PDF; an encrypted
    PDF cannot be read, so its caller passes the facts. `blocks` defaults to one TEXT
    block per page with a text layer; `extra_blocks` adds to either.
    """
    facts = tuple(pages) if pages is not None else read_pages(pdf)
    chosen = text_blocks(facts) if blocks is None else list(blocks)
    placed = blocklist.assign(stem, [*chosen, *extra_blocks])
    display = DISPLAY_PATH.format(stem=stem)
    document_json = blocklist.blocks_document(stem, facts, placed, display_path=display)
    markdown = results.render_markdown(stem, display, len(facts), placed, stamp=stamp)
    by_page_kind = {(b.page_index, b.kind): b.block_id for b in placed}
    located = tuple(dataclasses.replace(d, block_id=by_page_kind.get((d.page_index, fmt.KIND_TEXT), ""))
                    for d in defects)
    stamps = [b for b in placed if b.kind == fmt.KIND_STAMP]
    return PortalFiles(
        stem=stem, pdf=pdf, blocks_json=blocklist.dump(document_json),
        results_md=markdown.encode("utf-8"),
        results_html=(results.render_html(stem, display, len(facts), placed).encode("utf-8")
                      if html else None),
        stamp_audit=stampaudit.build(stem, len(facts), stamps) if stamp_audit else None,
        page_count=len(facts), blocks=placed, defects=located,
    )


def _member_name(stem: str, role: str, encoding: str) -> tuple[bytes, int, bytes, bytes]:
    """(raw name, flags, local extra, central extra) for a member in a name encoding.

    `utf8_flag`: UTF-8 with general-purpose flag 11. `infozip_unicode`: the header holds a
    cp866 name and the Info-ZIP Unicode Path field holds the UTF-8 one. `utf8_plain`:
    UTF-8 with no flag and no field. `cp866`: cp866 with nothing to say so.
    """
    text = stem + fmt.ROLE_SUFFIX[role].decode("ascii")
    if encoding == "utf8_flag":
        return text.encode("utf-8"), zipwrite.FLAG_UTF8, b"", b""
    if encoding == "utf8_plain":
        return text.encode("utf-8"), 0, b"", b""
    if encoding == "cp866":
        return text.encode("cp866"), 0, b"", b""
    if encoding == "infozip_unicode":
        raw = text.encode("cp866")
        extra = zipwrite.unicode_path_extra(raw, text.encode("utf-8"))
        return raw, 0, extra, extra
    raise ValueError(f"unknown name encoding {encoding!r}")


def pack(
    files: PortalFiles, *, encoding: str = "utf8_flag", deflate: str = "stored_blocks",
    descriptors: bool = False, zip64: bool = False, stored: bool = False,
    roles: Sequence[str] | None = None,
) -> list[zipwrite.Member]:
    """The archive members for a bundle's files, in the fixed member order.

    The PDF is stored (it is compressed already); the others are method 8, with a
    compressor chosen by `deflate`. `stored=True` stores everything. `roles` limits the
    archive to the named members, which is how a member is left out.
    """
    members: list[zipwrite.Member] = []
    present = files.member_bytes()
    for role in fmt.ROLE_ORDER:
        if role not in present or (roles is not None and role not in roles):
            continue
        name, flags, local_extra, central_extra = _member_name(files.stem, role, encoding)
        method = zipwrite.STORED if stored or role == fmt.ROLE_PDF else zipwrite.DEFLATED
        members.append(zipwrite.Member(
            name=name, payload=present[role], method=method, deflate=deflate,
            flags=flags | (zipwrite.FLAG_DESCRIPTOR if descriptors else 0), zip64=zip64,
            local_extra=local_extra, central_extra=central_extra,
        ))
    return members


@dataclass(frozen=True)
class BuiltBundle:
    data: bytes
    files: PortalFiles
    verdict: validate.Verdict


def build_bundle(files: PortalFiles, *, expect: str | None = None, zip64_end: bool = False,
                 limits: validate.Limits = GENERATOR_LIMITS, **pack_options) -> BuiltBundle:
    """Write the archive and refuse it unless the validator agrees with `expect`.

    `expect=None` means the bundle must be accepted. A bundle that is meant to be refused
    (a scanned PDF, an encrypted one) names the rule it is meant to break, and must break
    that rule and no other.
    """
    data = zipwrite.build_zip(pack(files, **pack_options), zip64_end=zip64_end)
    verdict = validate.validate(data, limits)
    wanted = () if expect is None else (expect,)
    if verdict.constraints != wanted:
        raise BundleError(
            f"{files.stem}: expected {wanted or 'an accepted bundle'}, the validator says "
            f"{[(v.constraint, v.detail) for v in verdict.violations] or 'accepted'}"
        )
    return BuiltBundle(data, files, verdict)


# ---------------------------------------------------------------- the defect variant


def _replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise BundleError(f"expected exactly one {old!r} in the page text, found {text.count(old)}")
    return text.replace(old, new)


def seed_text_defects(pages: Sequence[PageFacts]) -> tuple[dict[int, str], list[SeededDefect]]:
    """Recognised texts with known flaws, for the lanes that flag flaws in recognised text.

    Each seeded flaw is recorded with the word as it should have been and as it was
    recognised. The engineering designations are not flaws: they are Latin tokens a
    careless detector would flag, and the record says they must not be.
    """
    # Latin letters that look like Cyrillic ones, written as escapes so no editor,
    # formatter or reviewer can quietly turn them back.
    latin_e, latin_a = "\u0065", "\u0061"
    bodies: dict[int, str] = {}
    seeded: list[SeededDefect] = []

    def edit(page: int, old: str, new: str, kind: str) -> None:
        bodies[page] = _replace_once(bodies.get(page, pages[page].text), old, new)
        seeded.append(SeededDefect(page, kind, old, new, flaggable=True))

    edit(1, "Уровень", "Уров" + latin_e + "нь", "latin_homoglyph")
    edit(1, "ответственности здания", "ответственности зд" + latin_a + "ния", "latin_homoglyph")
    edit(2, "каждый", "кажд" + chr(0x68AF) + "й", "cjk_character")   # a CJK ideograph
    edit(3, "3.2. Внутренние", "- - 3.2. Внутренние", "doubled_list_marker")
    edit(3, "3.3. Перегородки", "- - 3.3. Перегородки", "doubled_list_marker")
    edit(4, "мелкоштучных", "мелкоshтучных", "mixed_script_word")

    footer = pages[5].text.split("\n")[-1]
    designations = "5.6. Бетон B25, арматура A500C, оси 1.A, предел REI 150."
    bodies[5] = pages[5].text[: -len(footer)] + designations + "\n" + footer
    for token in ("B25", "A500C", "1.A", "REI 150"):
        seeded.append(SeededDefect(5, "engineering_designation", token, token, False))
    return bodies, seeded
