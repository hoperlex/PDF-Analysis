"""What the segmenter keeps and what it throws away.

`R-16`: ConsultantPlus running heads are noise and are discarded at segmentation, confirmed
by the owner. The rules below are the ones that can be wrong in a way no count would show:
a rule too broad eats normative text, a rule too narrow embeds a page footer 28 000 times.
"""

from __future__ import annotations

from auditmanager.norms import ParagraphKind, segment
from auditmanager.norms.running_heads import is_publisher_noise, repeated_offcuts


def _texts(markdown: str, slug: str = "example") -> list[str]:
    paragraphs, _report = segment(slug, markdown)
    return [paragraph.text for paragraph in paragraphs]


def test_every_consultant_plus_stamp_is_gone(consultant_plus_markdown: str) -> None:
    surviving = "\n".join(_texts(consultant_plus_markdown))
    for stamp in (
        "КонсультантПлюс",
        "www.consultant.ru",
        "Дата сохранения",
        "надежная правовая поддержка",
    ):
        assert stamp not in surviving, f"{stamp!r} survived segmentation"
    assert "Страница 2 из 2" not in surviving


def test_the_repeated_truncated_title_is_gone_and_a_one_off_ellipsis_survives(
    consultant_plus_markdown: str,
) -> None:
    surviving = _texts(consultant_plus_markdown)
    assert not any(text.startswith('"ГОСТ 00000-2026.') for text in surviving), (
        "the truncated title is reprinted on both pages and is a running head"
    )
    assert any(text.startswith("Рисунок Л.6") for text in surviving), (
        "an ellipsis-terminated paragraph occurring once is body text, not an offcut; "
        "110 such paragraphs exist in the real corpus"
    )


def test_the_page_footer_rule_is_anchored_and_spares_another_publisher(
    unattributed_markdown: str,
) -> None:
    """`Страница ` alone is body text elsewhere in the corpus.

    `ГОСТ_Р_72509-2026` carries no ConsultantPlus marker at all and prints
    `Страница документа - https://GostExpert.ru/...` 49 times. An unanchored rule would
    discard all 49 as though they were ConsultantPlus footers, and the document would lose
    part of its text to a publisher it does not come from.
    """
    surviving = _texts(unattributed_markdown)
    assert any(text.startswith("Страница документа") for text in surviving)
    assert is_publisher_noise("Страница 2 из 14")
    assert not is_publisher_noise("Страница документа - https://GostExpert.ru/gost/gost-00001-2026")


def test_a_paragraph_mixing_a_stamp_with_body_text_is_kept_whole() -> None:
    mixed = "Документ предоставлен **КонсультантПлюс**\n1.9. Требования к приёмке изложены ниже."
    assert not is_publisher_noise(mixed), "dropping this would lose clause 1.9 with the stamp"


def test_repeated_offcuts_need_more_than_one_occurrence() -> None:
    assert repeated_offcuts(("на отм. ...",)) == frozenset()
    assert repeated_offcuts(("на отм. ...", "на отм. ...")) == frozenset({"на отм. ..."})


def test_headings_tables_and_clauses_are_kept_and_told_apart(
    consultant_plus_markdown: str,
) -> None:
    paragraphs, report = segment("example", consultant_plus_markdown)
    kinds = {paragraph.kind for paragraph in paragraphs}
    assert ParagraphKind.HEADING in kinds
    assert ParagraphKind.TABLE_ROW in kinds
    assert ParagraphKind.BODY in kinds
    clauses = [paragraph.clause_number for paragraph in paragraphs if paragraph.is_numbered_clause]
    assert "1.1" in clauses and "1" in clauses
    assert report.substantive == len(paragraphs)
    assert report.candidates == report.substantive + report.discarded


def test_a_table_cell_that_is_only_a_number_is_not_read_as_a_clause(
    consultant_plus_markdown: str,
) -> None:
    """`2000` appears alone as a table cell in the corpus. It is not clause 2000."""
    paragraphs, _report = segment(
        "example",
        consultant_plus_markdown.replace("1.1. Настоящий", "2000\n\n1.1. Настоящий"),
    )
    bare = [paragraph for paragraph in paragraphs if paragraph.text == "2000"]
    assert bare and bare[0].clause_number is None


def test_page_labels_are_the_pdf_page_numbers_and_do_not_renumber_over_a_gap(
    gapped_pages_markdown: str,
) -> None:
    """`ГОСТ_Р_50030_2-2010` has two pages with no block, and `results.md` omits them.

    The corpus has 28 249 `## Page` headings over 28 251 PDF pages for this reason. What
    matters downstream is that the surviving labels are still the true page numbers, because
    the label is what fetches the page crop the expert is shown.
    """
    paragraphs, report = segment("example", gapped_pages_markdown)
    assert [paragraph.page_label for paragraph in paragraphs] == [1, 3]
    assert report.page_headings == 2


def test_an_offset_points_at_the_paragraph_in_the_recognised_text(
    consultant_plus_markdown: str,
) -> None:
    """An anchor that does not resolve is worse than no anchor: nothing reveals it later."""
    from auditmanager.norms import recognised_text

    text = recognised_text(consultant_plus_markdown)
    paragraphs, _report = segment("example", consultant_plus_markdown)
    assert paragraphs
    for paragraph in paragraphs:
        window = text[paragraph.char_offset : paragraph.char_offset + paragraph.char_length]
        assert window == paragraph.text, f"offset {paragraph.char_offset} does not resolve"


def test_two_identical_paragraphs_in_one_block_get_two_different_offsets() -> None:
    """An anchor shared by two chunks is an anchor that cannot be checked.

    Added because the mutation sweep found this guard weak: rewriting the offset search to
    start from zero every time reddened nothing, since no fixture repeated a line inside one
    block. The corpus does — a table's units row, a repeated `Примечание` — and the effect
    would have been two chunks claiming one position, with nothing downstream able to notice.
    """
    markdown = (
        "# Document: X.pdf\n\n## Page 1\n\n### BLOCK #1 [TEXT]: blk_1\n\n"
        "> **Created:** 2026-08-25 09:22:54 UTC\n"
        "> **Crop:** [Crop](https://example.invalid/a)\n\n"
        "Примечание - Значение уточняют по таблице.\n\n"
        "3.1. Между двумя одинаковыми абзацами стоит текст пункта.\n\n"
        "Примечание - Значение уточняют по таблице.\n"
    )
    paragraphs, _report = segment("example", markdown)
    repeated = [p for p in paragraphs if p.text.startswith("Примечание")]
    assert len(repeated) == 2
    assert repeated[0].char_offset != repeated[1].char_offset

    from auditmanager.norms import recognised_text

    text = recognised_text(markdown)
    for paragraph in paragraphs:
        assert text[paragraph.char_offset : paragraph.char_offset + paragraph.char_length] == paragraph.text
