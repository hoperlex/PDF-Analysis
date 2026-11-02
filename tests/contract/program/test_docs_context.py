"""Focused checks for the documentation crop reader."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.docs_context import MAX_LINES, crop_lines, load_crops  # noqa: E402


class DocumentationCropTests(unittest.TestCase):
    def test_headings_inside_code_fences_do_not_create_crops(self) -> None:
        lines = [
            "# Real title\n", "Before\n", "```md\n", "## Fake title\n",
            "```\n", "## Actual section\n", "After\n",
        ]
        crops = crop_lines("docs/example.md", lines)
        self.assertEqual([(c.start, c.end) for c in crops], [(1, 5), (6, 7)])
        self.assertEqual(crops[-1].title, "Real title / Actual section")

    def test_long_unbroken_section_is_bounded_and_lossless(self) -> None:
        lines = ["# Title\n"] + [f"line {i}\n" for i in range(250)]
        crops = crop_lines("docs/example.md", lines)
        self.assertTrue(all(c.end - c.start + 1 <= MAX_LINES for c in crops))
        self.assertEqual([n for c in crops for n in range(c.start, c.end + 1)],
                         list(range(1, len(lines) + 1)))

    def test_current_state_updates_are_separate_crops(self) -> None:
        lines = [
            "# Current state\n", "\n",
            "**Updated 2026-10-30 by `A-01`.** First update.\n", "\n",
            "**Updated 2026-10-29 by `B-02`.** Second update.\n",
        ]
        crops = crop_lines("docs/program/CURRENT_STATE.md", lines)
        self.assertEqual([(c.start, c.end) for c in crops], [(1, 2), (3, 4), (5, 5)])
        self.assertIn("A-01", crops[1].title)
        self.assertIn("B-02", crops[2].title)

    def test_real_index_covers_current_state_once(self) -> None:
        crops, documents = load_crops("docs/program/CURRENT_STATE.md")
        lines = documents["docs/program/CURRENT_STATE.md"]
        self.assertEqual([n for c in crops for n in range(c.start, c.end + 1)],
                         list(range(1, len(lines) + 1)))
        self.assertTrue(any("BLOCK16-INT-1030" in c.title for c in crops))


if __name__ == "__main__":
    unittest.main()
