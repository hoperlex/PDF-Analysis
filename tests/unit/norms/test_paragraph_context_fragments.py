"""`REVIEW-FIX-ANALYSIS-1102` (S3-03): a two-fragment search excerpt is literal when each fragment is.

The search stores up to two ``ts_headline`` fragments joined by ``FragmentDelimiter``. That string is
not text of the paragraph, so a whole-quote ``strpos`` is 0 for every such excerpt and the paragraph
context was marked "quote not literal". The check now looks the fragments up one by one; the stored
quote is not changed. No database: the double evaluates the two ``strpos`` expressions of the query.
"""
import pytest

from auditmanager.norms import paragraph_context as context
from auditmanager.norms.search.fragment import HEADLINE_OPTIONS
from auditmanager.shared.identity import NormDocumentId, NormParagraphId, NormsSnapshotId

DELIMITER = " … "
FIRST, SECOND = "первый фрагмент нормы", "второй фрагмент нормы"
TEXT = "А" * 3000 + " " + FIRST + " " + "Б" * 3000 + " " + SECOND + " " + "В" * 500
IDS = {"snapshot_id": str(NormsSnapshotId.new()), "document_id": str(NormDocumentId.new()),
    "paragraph_id": str(NormParagraphId.new())}


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def one_or_none(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class _Session:
    """Answers `_PRIMARY` the way its SQL does for one paragraph, and records each quote it was asked about."""

    def __init__(self, text=TEXT):
        self.text, self.quotes = text, []

    def execute(self, statement, parameters):
        if statement is not context._PRIMARY:
            return _Result([])
        quote, limit = parameters["quote"], parameters["paragraph_characters"]
        self.quotes.append(quote)
        position = self.text.find(quote) + 1  # strpos: 1-based, 0 when absent
        start = 0 if len(self.text) <= limit else max(0, position - 1 - 1000)
        return _Result([{"norm_paragraph_id": IDS["paragraph_id"], "norm_document_pk": 1, "ordinal": 1,
            "page_label": 1, "block_ref": "b", "kind": "paragraph", "clause_number": "1.1",
            "text_reliability": "reliable", "full_characters": len(self.text), "quote_position": position,
            "character_start": start, "context_text": self.text[start:start + limit],
            "source_attribution": "СП", "title": "Норма", "drawn_on": None}])


@pytest.fixture(autouse=True)
def _no_scope(monkeypatch):
    monkeypatch.setattr(context, "resolve_scope", lambda *_: None)


def _read(session, quote):
    return context.read_norm_paragraph_context(session, quote=quote, **IDS)


def test_a_literal_quote_costs_one_lookup_and_is_unchanged():
    session = _Session()
    result = _read(session, FIRST)
    assert session.quotes == [FIRST] and result["search_quote_literal_in_paragraph"] is True
    assert result["search_quote_paragraph_character_start"] == TEXT.find(FIRST)


def test_both_fragments_found_makes_the_excerpt_literal_and_centres_on_the_first():
    session = _Session()
    result = _read(session, FIRST + DELIMITER + SECOND)
    assert session.quotes == [FIRST + DELIMITER + SECOND, FIRST, SECOND]
    assert result["search_quote_literal_in_paragraph"] is True
    assert result["search_quote_paragraph_character_start"] == TEXT.find(FIRST)
    # the six-thousand-character window opens a thousand characters before the first fragment
    assert result["primary"]["paragraph_character_start"] == TEXT.find(FIRST) - 1000
    assert FIRST in result["primary"]["text"]


def test_a_missing_fragment_leaves_the_excerpt_not_literal_but_still_centres_on_a_found_one():
    result = _read(_Session(), FIRST + DELIMITER + "такого фрагмента в абзаце нет")
    assert result["search_quote_literal_in_paragraph"] is False
    assert result["search_quote_paragraph_character_start"] == TEXT.find(FIRST)
    # the window follows the first fragment found, even when it is the second of the quote
    result = _read(_Session(), "такого фрагмента в абзаце нет" + DELIMITER + SECOND)
    assert result["search_quote_literal_in_paragraph"] is False
    assert result["search_quote_paragraph_character_start"] == TEXT.find(SECOND)


def test_no_fragment_found_keeps_the_old_answer_with_the_window_at_the_paragraph_start():
    result = _read(_Session(), "нет первого" + DELIMITER + "нет второго")
    assert result["search_quote_literal_in_paragraph"] is False
    assert result["search_quote_paragraph_character_start"] is None
    assert result["primary"]["paragraph_character_start"] == 0


def test_a_whole_quote_that_contains_the_delimiter_in_the_paragraph_is_found_whole():
    text = "Начало " + FIRST + DELIMITER + SECOND + " конец"
    session = _Session(text)
    result = _read(session, FIRST + DELIMITER + SECOND)
    assert session.quotes == [FIRST + DELIMITER + SECOND] and result["search_quote_literal_in_paragraph"] is True


def test_a_repeated_or_empty_fragment_is_looked_up_once_or_not_at_all():
    session = _Session()
    whole = FIRST + DELIMITER + FIRST + DELIMITER + "   " + DELIMITER
    result = _read(session, whole)
    assert session.quotes == [whole, FIRST]  # the whole quote, then its one distinct non-empty fragment
    assert result["search_quote_literal_in_paragraph"] is True


def test_the_delimiter_is_the_one_the_search_asks_the_database_for():
    assert context.FRAGMENT_DELIMITER == DELIMITER
    assert f'FragmentDelimiter="{context.FRAGMENT_DELIMITER}"' in HEADLINE_OPTIONS


def test_unreadable_search_options_stop_the_import_instead_of_disabling_the_split(monkeypatch):
    for options in ("MaxFragments=2", 'FragmentDelimiter=""', 'FragmentDelimiter=" "'):
        monkeypatch.setattr(context, "HEADLINE_OPTIONS", options)
        with pytest.raises(RuntimeError, match="norm_search_fragment_delimiter_unreadable"):
            context._fragment_delimiter()
