"""Each negative fixture is rejected by the specific envelope rule it violates.

"Rejected" is not enough on its own. If a fixture failed for the wrong reason, a lane
would still see red and would still believe it had tested the rule it meant to test. So
every assertion here is about *which* rule fired, and about the rules that deliberately
did not.

The `not_evaluated` assertions carry the other half of the point. An encrypted file's page
count is unknown, not acceptable. A checker that recorded "unreadable" as "within the
envelope" would let a document through on a claim nobody ever checked, so the encrypted
fixture asserts that the page and text rules report `not_evaluated` and never `pass`.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

# See the note in test_manifest_grounding.py: `tools/fixtures` is on no import path and
# the root pyproject is a single-owner hotspot, so each module adds it itself.
REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "fixtures"
CORPUS_DIR = REPO_ROOT / "fixtures" / "synthetic" / "ar"
NEGATIVE_DIR = CORPUS_DIR / "negative"
BASELINE = CORPUS_DIR / "ar_baseline.pdf"
MANIFEST = CORPUS_DIR / "expected_issues.json"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from ar_corpus import envelope  # noqa: E402


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


class BaselineEnvelopeTest(unittest.TestCase):
    """The positive case. If the baseline did not pass cleanly, no negative means anything."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.data = BASELINE.read_bytes()
        cls.report = envelope.check(cls.data)
        cls.manifest = load_manifest()

    def test_baseline_is_accepted(self) -> None:
        self.assertTrue(
            self.report.accepted,
            "baseline is outside the envelope: "
            + "; ".join(f"{r.rule}={r.status.value} ({r.detail})" for r in self.report.results),
        )

    def test_every_rule_was_actually_evaluated(self) -> None:
        self.assertEqual(self.report.not_evaluated, ())
        self.assertEqual(
            {r.rule for r in self.report.results}, set(envelope.RULES),
            "a rule was silently dropped from the report",
        )

    def test_baseline_is_inside_the_size_and_page_limits(self) -> None:
        self.assertLessEqual(len(self.data), envelope.MAX_BYTES)
        self.assertLessEqual(self.manifest["baseline"]["pages"], envelope.MAX_PAGES)
        self.assertEqual(self.manifest["baseline"]["bytes"], len(self.data))

    def test_every_page_carries_extractable_text(self) -> None:
        from ar_corpus import pdfextract

        pages = pdfextract.extract_pages(self.data)
        self.assertEqual(len(pages), 8)
        for number, text in enumerate(pages, start=1):
            self.assertTrue(text.strip(), f"page {number} has no extractable text")


class NegativeFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()

    def _report(self, filename: str) -> envelope.EnvelopeReport:
        path = NEGATIVE_DIR / filename
        self.assertTrue(path.is_file(), f"missing negative fixture {path}")
        return envelope.check(path.read_bytes())

    def test_manifest_lists_every_committed_negative(self) -> None:
        listed = {Path(f["path"]).name for f in self.manifest["negative_fixtures"]}
        on_disk = {p.name for p in NEGATIVE_DIR.iterdir() if p.is_file()}
        self.assertEqual(listed, on_disk)

    def test_every_negative_violates_exactly_its_declared_rule(self) -> None:
        for fixture in self.manifest["negative_fixtures"]:
            with self.subTest(fixture=fixture["name"]):
                report = self._report(Path(fixture["path"]).name)
                self.assertEqual(
                    list(report.violations), [fixture["violates_rule"]],
                    f"{fixture['name']} should violate only {fixture['violates_rule']}; "
                    + "; ".join(
                        f"{r.rule}={r.status.value} ({r.detail})" for r in report.results
                    ),
                )
                self.assertFalse(report.accepted)

    def test_the_four_briefed_negatives_are_present(self) -> None:
        wanted = {
            "encrypted.pdf": envelope.RULE_NOT_ENCRYPTED,
            "image_only.pdf": envelope.RULE_TEXT_LAYER,
            "oversize.pdf": envelope.RULE_MAX_BYTES,
            "too_many_pages.pdf": envelope.RULE_MAX_PAGES,
        }
        for filename, rule in wanted.items():
            with self.subTest(fixture=filename):
                self.assertEqual(list(self._report(filename).violations), [rule])

    def test_encrypted_fixture_does_not_claim_unreadable_rules_passed(self) -> None:
        report = self._report("encrypted.pdf")
        self.assertEqual(list(report.violations), [envelope.RULE_NOT_ENCRYPTED])
        for rule in (envelope.RULE_MAX_PAGES, envelope.RULE_TEXT_LAYER):
            with self.subTest(rule=rule):
                self.assertIs(
                    report.by_rule(rule).status, envelope.Status.NOT_EVALUATED,
                    f"{rule} must be reported as not evaluated for an encrypted file, "
                    "never as passing",
                )

    def test_encrypted_fixture_really_needs_a_password(self) -> None:
        from ar_corpus import pdfextract

        data = (NEGATIVE_DIR / "encrypted.pdf").read_bytes()
        self.assertIn(b"/Encrypt", data)
        with self.assertRaises(pdfextract.EncryptedPdfError):
            pdfextract.extract_pages(data)

    def test_image_only_fixture_has_no_text_operator_at_all(self) -> None:
        """Not merely blank text: there must be no text-showing operator to find, so no
        reader can be tempted to treat a stray fragment as a text layer."""
        from ar_corpus import pdfextract

        data = (NEGATIVE_DIR / "image_only.pdf").read_bytes()
        doc = pdfextract.Document.load(data)
        pages = doc.pages()
        self.assertEqual(len(pages), 2)
        for number, page in enumerate(pages, start=1):
            with self.subTest(page=number):
                self.assertEqual(pdfextract.page_runs(doc, page), [])
                self.assertEqual(pdfextract.page_text(doc, page), "")

    def test_oversize_fixture_is_genuinely_over_the_limit(self) -> None:
        size = (NEGATIVE_DIR / "oversize.pdf").stat().st_size
        self.assertGreater(size, envelope.MAX_BYTES)

    def test_too_many_pages_fixture_is_one_page_over(self) -> None:
        from ar_corpus import pdfextract

        data = (NEGATIVE_DIR / "too_many_pages.pdf").read_bytes()
        self.assertEqual(pdfextract.page_count(data), envelope.MAX_PAGES + 1)


class EnvelopeCheckerCanFailTest(unittest.TestCase):
    """Prove the checker discriminates. A guard nobody has seen fail is not a guard."""

    def test_a_non_pdf_violates_the_pdf_rule(self) -> None:
        report = envelope.check(b"this is plainly not a PDF")
        self.assertEqual(list(report.violations), [envelope.RULE_IS_PDF])

    def test_an_oversize_input_violates_the_size_rule(self) -> None:
        report = envelope.check(b"%PDF-1.7\n" + b"x" * envelope.MAX_BYTES)
        self.assertIn(envelope.RULE_MAX_BYTES, report.violations)

    def test_a_truncated_pdf_is_not_silently_accepted(self) -> None:
        truncated = BASELINE.read_bytes()[:2048]
        report = envelope.check(truncated)
        self.assertFalse(report.accepted)

    def test_a_corrupt_pdf_reports_rather_than_crashes(self) -> None:
        """`build_ar_corpus.py --check` re-reads the *committed* baseline, which can be
        corrupt in ways a fresh build never is. It relies on corruption surfacing as
        `PdfParseError` so it can name the bad artefact instead of dying with a
        traceback. This pins that contract.
        """
        from ar_corpus import pdfextract

        data = bytearray(BASELINE.read_bytes())
        data[-200] ^= 0x01
        with self.assertRaises(pdfextract.PdfParseError):
            pdfextract.extract_pages(bytes(data))
        # And the envelope checker turns that same corruption into a report, not a raise.
        self.assertFalse(envelope.check(bytes(data)).accepted)

    def test_a_baseline_stripped_of_its_tounicode_map_fails_the_text_rule(self) -> None:
        """The failure mode that would silently contaminate the oracle.

        Without a `/ToUnicode` CMap a viewer still draws the page perfectly, so the PDF
        looks fine, but the extracted characters are glyph ids rather than text. Nothing
        about the file's appearance would reveal it. `ENV-TEXT` has to be the thing that
        notices, so here it is made to.
        """
        data = BASELINE.read_bytes()
        self.assertTrue(envelope.check(data).accepted)
        self.assertIn(b"/ToUnicode", data)
        # Rename the key rather than remove it, so every byte offset in the file - and
        # therefore the cross-reference table - stays valid and only the map is lost.
        broken = data.replace(b"/ToUnicode", b"/ToUnicodX", 1)
        self.assertNotEqual(broken, data)
        report = envelope.check(broken)
        self.assertIn(
            envelope.RULE_TEXT_LAYER, report.violations,
            "a PDF whose text layer is not recoverable was reported as acceptable",
        )
        self.assertFalse(report.accepted)


if __name__ == "__main__":
    unittest.main()
