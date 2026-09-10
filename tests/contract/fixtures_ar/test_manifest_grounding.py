"""The load-bearing test: every manifest quotation is really in the committed text layer.

In Gate B a grounding gate rejects any model finding whose quotation does not resolve at
its declared anchor, and PC-01 acceptance requires a live model run to find at least two
seeded issues. If a seeded quotation were not recoverable character-for-character from
the extracted text, every downstream measurement would be contaminated and nothing would
report it. So this is asserted against the **committed** PDF, by extracting text from its
bytes, and never inferred from the generator's own data structures.

`test_the_check_can_fail` exists because an assertion that cannot fail proves nothing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

# `tools/fixtures` is on no import path. The root `pyproject.toml` puts only `src` on
# `pythonpath` and is a single-owner hotspot this session does not own, so each test
# module adds the tools directory itself. Deliberately inlined rather than shared through
# a sibling helper or a `conftest.py`: under pytest's `--import-mode=importlib`, which the
# root configuration sets, a sibling import would not resolve, and that configuration
# calls conftest-level path juggling a workaround rather than an extension of its
# contract. A few duplicated lines buy a module that runs identically under
# `python3 -m unittest` and under pytest.
REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "fixtures"
CORPUS_DIR = REPO_ROOT / "fixtures" / "synthetic" / "ar"
BASELINE = CORPUS_DIR / "ar_baseline.pdf"
MANIFEST = CORPUS_DIR / "expected_issues.json"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from ar_corpus import pdfextract  # noqa: E402

ALLOWED_CATEGORIES = {"internal_contradiction", "explicit_placeholder"}


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def extracted_pages() -> list[str]:
    """Extract the committed baseline's text layer from its bytes."""
    return pdfextract.extract_pages(BASELINE.read_bytes())


class ManifestShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()

    def test_schema_and_synthetic_marking(self) -> None:
        self.assertEqual(self.manifest["schema"], "ar-expected-issues/1")
        self.assertIs(self.manifest["synthetic"], True)
        self.assertIn("OD-17", self.manifest["notice"])

    def test_seeded_issue_population(self) -> None:
        issues = self.manifest["seeded_issues"]
        self.assertEqual(len(issues), self.manifest["seeded_issue_count"])

        contradictions = [i for i in issues if i["category"] == "internal_contradiction"]
        placeholders = [i for i in issues if i["category"] == "explicit_placeholder"]
        self.assertEqual(len(contradictions), 2, "the brief seeds two contradictions")
        self.assertEqual(len(placeholders), 1, "the brief seeds one explicit placeholder")

        for issue in issues:
            self.assertIn(issue["category"], ALLOWED_CATEGORIES)

    def test_each_contradiction_spans_two_distinct_pages(self) -> None:
        for issue in self.manifest["seeded_issues"]:
            if issue["category"] != "internal_contradiction":
                continue
            pages = {ev["page"] for ev in issue["evidence"]}
            self.assertEqual(
                len(pages), 2,
                f"{issue['id']} must be a *cross-page* contradiction, got pages {pages}",
            )

    def test_the_placeholder_is_a_literal_marker(self) -> None:
        placeholder = next(
            i for i in self.manifest["seeded_issues"]
            if i["category"] == "explicit_placeholder"
        )
        quotations = [ev["quotation"] for ev in placeholder["evidence"]]
        self.assertTrue(
            any("уточнить" in q or "TBD" in q for q in quotations),
            f"expected a literal TBD/уточнить marker, got {quotations}",
        )

    def test_controls_are_present_and_categorised(self) -> None:
        controls = self.manifest["controls"]
        self.assertGreaterEqual(len(controls), 4, "precision needs real controls")
        for control in controls:
            self.assertIn(control["would_be_false_positive_as"], ALLOWED_CATEGORIES)
            self.assertTrue(control["why_not_an_issue_ru"].strip())

    def test_no_control_overlaps_a_seeded_quotation(self) -> None:
        """A control that contained (or sat inside) a seeded quotation would make the
        precision measurement meaningless: reporting it would be both right and wrong."""
        seeded = {
            ev["quotation"]
            for issue in self.manifest["seeded_issues"] for ev in issue["evidence"]
        }
        for control in self.manifest["controls"]:
            quotation = control["quotation"]
            for seed in seeded:
                self.assertNotIn(quotation, seed, f"{control['id']} sits inside a seeded quotation")
                self.assertNotIn(seed, quotation, f"{control['id']} contains a seeded quotation")


class GroundingTest(unittest.TestCase):
    """Quotations resolve, character-for-character, at their declared anchors."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()
        cls.pages = extracted_pages()

    def _anchors(self):
        for issue in self.manifest["seeded_issues"]:
            for evidence in issue["evidence"]:
                yield issue["id"], evidence
        for control in self.manifest["controls"]:
            for anchor in control["anchors"]:
                yield control["id"], anchor

    def test_page_count_matches_the_manifest(self) -> None:
        self.assertEqual(len(self.pages), self.manifest["baseline"]["pages"])

    def test_every_quotation_resolves_at_its_declared_offset(self) -> None:
        checked = 0
        for owner, anchor in self._anchors():
            page_text = self.pages[anchor["page"] - 1]
            offset = anchor["char_offset_in_page_text"]
            quotation = anchor["quotation"]
            self.assertEqual(
                page_text[offset:offset + len(quotation)],
                quotation,
                f"{owner}: page {anchor['page']} offset {offset} does not hold the "
                f"declared quotation character-for-character",
            )
            checked += 1
        self.assertGreaterEqual(checked, 12, "the oracle should not have shrunk silently")

    def test_every_quotation_lies_within_one_extracted_line(self) -> None:
        for owner, anchor in self._anchors():
            self.assertNotIn(
                "\n", anchor["quotation"],
                f"{owner}: a quotation spanning a line break cannot be matched reliably",
            )
            line = self.pages[anchor["page"] - 1].split("\n")[
                anchor["line_index_in_page_text"]
            ]
            self.assertEqual(line, anchor["line_text"], f"{owner}: line_text has drifted")
            self.assertIn(anchor["quotation"], line, f"{owner}: quotation not on its line")

    def test_each_quotation_occurs_on_exactly_its_declared_pages(self) -> None:
        """An unadvertised second occurrence would make the anchor ambiguous, and a
        finding could be 'grounded' against a page nobody meant."""
        declared: dict[str, set[int]] = {}
        for _owner, anchor in self._anchors():
            declared.setdefault(anchor["quotation"], set()).add(anchor["page"])
        for quotation, pages in declared.items():
            found = {n for n, text in enumerate(self.pages, start=1) if quotation in text}
            self.assertEqual(
                found, pages,
                f"{quotation!r} declared on {sorted(pages)} but found on {sorted(found)}",
            )

    def test_recorded_page_text_digests_match(self) -> None:
        import hashlib

        recorded = self.manifest["baseline"]["page_text_sha256"]
        actual = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in self.pages]
        self.assertEqual(actual, recorded)

    def test_the_check_can_fail(self) -> None:
        """Prove the grounding assertion discriminates.

        A quotation with one character changed must NOT be found. Without this, a test
        that always passed would look identical to a test that works.
        """
        issue = self.manifest["seeded_issues"][0]
        anchor = issue["evidence"][0]
        quotation = anchor["quotation"]
        page_text = self.pages[anchor["page"] - 1]

        self.assertIn(quotation, page_text)

        mutated = quotation[:-2] + ("Z" if quotation[-2] != "Z" else "Q") + quotation[-1]
        self.assertNotEqual(mutated, quotation)
        self.assertNotIn(
            mutated, page_text,
            "a one-character mutation was still found; the grounding check is vacuous",
        )

        offset = anchor["char_offset_in_page_text"]
        self.assertNotEqual(
            page_text[offset + 1:offset + 1 + len(quotation)], quotation,
            "the quotation matches at a shifted offset too; the anchor is not precise",
        )


@unittest.skipIf(shutil.which("pdftotext") is None, "poppler pdftotext is not installed")
class PopplerCrossCheckTest(unittest.TestCase):
    """Cross-check with an extractor that shares no code with this repository.

    The generator and `pdfextract.py` were written together, so a matching bug in both
    would cancel out and go unseen. Poppler cannot share that bug. Skipped rather than
    failed where poppler is absent: it is corroboration, not the primary gate.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()
        cls.pages: dict[int, str] = {}
        for number in range(1, cls.manifest["baseline"]["pages"] + 1):
            completed = subprocess.run(
                ["pdftotext", "-f", str(number), "-l", str(number),
                 "-raw", "-enc", "UTF-8", str(BASELINE), "-"],
                capture_output=True, text=True, check=True,
                env={**os.environ, "LC_ALL": "C.UTF-8"},
            )
            cls.pages[number] = completed.stdout

    def test_every_quotation_is_found_by_poppler(self) -> None:
        missing: list[str] = []
        for issue in self.manifest["seeded_issues"]:
            for evidence in issue["evidence"]:
                if evidence["quotation"] not in self.pages[evidence["page"]]:
                    missing.append(f"{issue['id']} p{evidence['page']}")
        for control in self.manifest["controls"]:
            for anchor in control["anchors"]:
                if anchor["quotation"] not in self.pages[anchor["page"]]:
                    missing.append(f"{control['id']} p{anchor['page']}")
        self.assertEqual(missing, [], "poppler could not find these quotations")


if __name__ == "__main__":
    unittest.main()
