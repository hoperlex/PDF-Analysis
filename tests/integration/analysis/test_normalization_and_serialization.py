"""``analysis.stages.extraction`` and ``analysis.engine.serialization``: the two pins that
make an offset mean the same thing twice.

`W10-ANL` mutation sweep, rows EX-06, EX-08, EX-09, EX-10 and the `SZ-*` serialization rows.
Green across `tests/integration/analysis_engine`, `tests/integration/analysis_text`,
`tests/replay` and the guards written earlier in this wave.

`EX-08` is the sharp one: changing the declared normalization from **NFC to NFKC** changed no
test anywhere. NFKC is a *compatibility* normalization — it rewrites ligatures, superscripts,
non-breaking spaces and full-width forms — so it changes the code-point length of text that
NFC leaves alone. Every offset in the system indexes the sequence this function produces, and
`B4` compares "after that one declared normalization and nothing else", so swapping it
silently moves anchors while `normalization.id` still reads `nfc_v1`.

The corpus does not happen to contain a character where NFC and NFKC differ, which is exactly
why an end-to-end run over it cannot detect the change. The strings here are built in the
test and chosen to separate the two.

Authorities: `docs/program/P02_SEAMS.md` §4.3 for `nfc_v1` and its description,
`docs/program/P02_LOCK.json` → `pins.pdfplumber` for the extractor identity.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from auditmanager.analysis.engine.serialization import (
    ARTIFACT_MEDIA_TYPE,
    canonical_bytes,
    sha256_hex,
)
from auditmanager.analysis.stages.extraction import (
    EXTRACTION_OPTIONS,
    EXTRACTOR_NAME,
    NORMALIZATION_ID,
    normalize,
    options_sha256,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SEAMS = REPO_ROOT / "docs" / "program" / "P02_SEAMS.md"
LOCK = REPO_ROOT / "docs" / "program" / "P02_LOCK.json"


# --- the authorities ----------------------------------------------------------------


def test_the_seams_document_declares_the_normalization_this_module_uses() -> None:
    assert NORMALIZATION_ID == "nfc_v1"
    assert '"id": "nfc_v1"' in SEAMS.read_text(encoding="utf-8")


def test_the_lock_pins_the_extractor_this_module_names() -> None:
    assert EXTRACTOR_NAME == "pdfplumber"
    assert "pdfplumber" in json.loads(LOCK.read_text(encoding="utf-8"))["pins"]


# --- EX-08: the declared normalization is NFC and not a compatibility form ------------


@pytest.mark.parametrize(
    ("label", "text"),
    [
        ("ligature_fi", "ﬁnal"),          # NFKC -> "final", NFC leaves it alone
        ("superscript_two", "²"),          # NFKC -> "2"
        ("non_breaking_space", "a b"),     # NFKC -> "a b"
        ("roman_numeral_two", "Ⅱ"),        # NFKC -> "II"
        ("fullwidth_a", "Ａ"),              # NFKC -> "A"
    ],
)
def test_the_declared_normalization_is_nfc_and_leaves_compatibility_forms_alone(
    label: str, text: str
) -> None:
    """EX-08. NFC preserves these; NFKC rewrites every one of them.

    The expected value is `unicodedata.normalize("NFC", text)` — the standard's own
    answer, not this module's — so the two cannot agree by moving together.
    """
    assert normalize(text) == unicodedata.normalize("NFC", text)
    assert normalize(text) != unicodedata.normalize("NFKC", text), label
    assert normalize(text) == text, f"{label}: NFC must not rewrite this at all"


def test_nfc_still_composes_a_decomposed_sequence() -> None:
    """The negative half: NFC is applied, not skipped.

    "й" written as и + combining breve is two code points; NFC composes it to one.
    Both lengths are literals.
    """
    decomposed = "й"
    assert len(decomposed) == 2
    assert normalize(decomposed) == "й"
    assert len(normalize(decomposed)) == 1


def test_normalization_does_not_case_fold_or_collapse_whitespace() -> None:
    """The description `P02_SEAMS` §4.3 declares, asserted as behaviour."""
    assert normalize("Отчёт  ЗА  год") == "Отчёт  ЗА  год"
    assert normalize("  ведущий пробел ") == "  ведущий пробел "


# --- EX-09: the extraction options are what `options_sha256` fixes --------------------


def test_the_extraction_options_declare_no_page_separator() -> None:
    """EX-09. `P02_SEAMS` §4.1: no separator between pages."""
    assert EXTRACTION_OPTIONS["page_separator"] == ""
    assert EXTRACTION_OPTIONS["line_separator"] == "\n"
    assert EXTRACTION_OPTIONS["line_source"] == "extract_text_lines"
    assert EXTRACTION_OPTIONS["normalization"] == "nfc_v1"


def test_the_options_checksum_is_a_function_of_the_options_alone() -> None:
    """Pinned as a literal: same options, same digest, on every machine and every run."""
    assert options_sha256() == sha256_hex(
        canonical_bytes(
            {
                "line_source": "extract_text_lines",
                "page_separator": "",
                "line_separator": "\n",
                "normalization": "nfc_v1",
            }
        )
    )
    assert len(options_sha256()) == 64


# --- the serializer is pinned as tightly as the extractor ----------------------------


def test_canonical_bytes_sorts_keys_so_insertion_order_cannot_move_a_byte() -> None:
    """SZ-01. The expected bytes are written out, not produced by the module."""
    assert canonical_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    assert canonical_bytes({"a": 2, "b": 1}) == b'{"a":2,"b":1}'


def test_canonical_bytes_leaves_cyrillic_unescaped() -> None:
    """SZ-02. `ensure_ascii=True` would quadruple every text artifact and hide the text."""
    assert canonical_bytes({"t": "Отчёт"}) == '{"t":"Отчёт"}'.encode("utf-8")
    assert b"\\u" not in canonical_bytes({"t": "Отчёт"})


def test_canonical_bytes_carries_no_insignificant_whitespace() -> None:
    """SZ-03. Indentation style must not be part of a checksum."""
    assert canonical_bytes({"a": 1, "b": [1, 2]}) == b'{"a":1,"b":[1,2]}'
    assert b", " not in canonical_bytes({"a": 1, "b": 2})
    assert b": " not in canonical_bytes({"a": 1, "b": 2})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_canonical_bytes_refuses_a_value_json_cannot_represent(value: float) -> None:
    """SZ-04. `allow_nan=True` emits `NaN`, which is not JSON and no consumer can read."""
    with pytest.raises(ValueError):
        canonical_bytes({"metric": value})


def test_the_artifact_media_type_is_the_pinned_literal() -> None:
    """SZ-05."""
    assert ARTIFACT_MEDIA_TYPE == "application/json"


def test_two_serializations_of_equal_documents_are_byte_identical() -> None:
    """`P2-ENG-01`: two runs over identical inputs publish byte-identical artifacts."""
    first = {"artifact_role": "prepared.text_layer", "pages": [{"n": 1, "t": "Отчёт"}]}
    second = {"pages": [{"t": "Отчёт", "n": 1}], "artifact_role": "prepared.text_layer"}
    assert canonical_bytes(first) == canonical_bytes(second)
    assert sha256_hex(canonical_bytes(first)) == sha256_hex(canonical_bytes(second))
