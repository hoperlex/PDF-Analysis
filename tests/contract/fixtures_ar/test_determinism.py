"""The generator reproduces the committed corpus byte for byte.

A drifting generator has to fail its own check before any lane consumes the fixtures. If
the corpus could quietly change from run to run, the recorded SHA-256 values would be
decoration and nobody could tell a regenerated fixture from an edited one.

Two independent claims, and both are needed:

*   in-process, building twice returns identical bytes — this catches a PRNG, a clock or
    a set iteration order leaking into the output;
*   in a fresh interpreter, `build_ar_corpus.py --check` exits 0 — this catches anything
    that is stable only within one process, such as `PYTHONHASHSEED` affecting a hash
    ordering, since each subprocess gets a different seed by default.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

# See the note in test_manifest_grounding.py: `tools/fixtures` is on no import path and
# the root pyproject is a single-owner hotspot, so each module adds it itself.
REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "fixtures"
CORPUS_DIR = REPO_ROOT / "fixtures" / "synthetic" / "ar"
BASELINE = CORPUS_DIR / "ar_baseline.pdf"
CHECKSUMS = CORPUS_DIR / "SHA256SUMS"
GENERATOR = TOOLS_DIR / "build_ar_corpus.py"
FONT_ASSET = TOOLS_DIR / "assets" / "ARCorpusSans.ttf"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


class InProcessDeterminismTest(unittest.TestCase):
    def test_building_the_baseline_twice_gives_identical_bytes(self) -> None:
        import build_ar_corpus
        from ar_corpus import document

        font = build_ar_corpus.load_font()
        first = document.build_baseline(font)
        second = document.build_baseline(font)
        self.assertEqual(first, second)

    def test_the_rebuilt_baseline_matches_the_committed_one(self) -> None:
        import build_ar_corpus
        from ar_corpus import document

        rebuilt = document.build_baseline(build_ar_corpus.load_font())
        self.assertEqual(
            hashlib.sha256(rebuilt).hexdigest(),
            hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
        )

    def test_no_output_carries_a_wall_clock_timestamp(self) -> None:
        """The creation date is a fixed literal, not today."""
        from ar_corpus import document

        data = BASELINE.read_bytes()
        self.assertIn(document.CREATION_DATE.encode("ascii"), data)


class SubprocessCheckTest(unittest.TestCase):
    def test_generator_check_mode_exits_zero(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(GENERATOR), "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        self.assertEqual(
            completed.returncode, 0,
            f"generator --check failed\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}",
        )

    def test_two_fresh_interpreters_agree(self) -> None:
        """Different `PYTHONHASHSEED` values must not change a single byte."""
        digests = []
        for seed in ("0", "12345"):
            completed = subprocess.run(
                [sys.executable, "-c",
                 "import hashlib, sys;"
                 f"sys.path.insert(0, {str(TOOLS_DIR)!r});"
                 "import build_ar_corpus;"
                 "from ar_corpus import document;"
                 "d = document.build_baseline(build_ar_corpus.load_font());"
                 "print(hashlib.sha256(d).hexdigest())"],
                capture_output=True, text=True, cwd=str(REPO_ROOT),
                env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": seed},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            digests.append(completed.stdout.strip())
        self.assertEqual(digests[0], digests[1])
        self.assertEqual(
            digests[0], hashlib.sha256(BASELINE.read_bytes()).hexdigest()
        )


class ChecksumFileTest(unittest.TestCase):
    def test_sha256sums_covers_every_generated_artefact(self) -> None:
        """Every generated file is digested, and nothing undigested has crept in.

        The second half is the one that matters: an artefact nobody records is an
        artefact nobody notices changing.
        """
        recorded: dict[str, str] = {}
        for line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, name = line.split("  ", 1)
            recorded[name] = digest

        # Hand-maintained files, deliberately not generator output and so deliberately
        # not in SHA256SUMS. Listed explicitly so adding one is a conscious act.
        HAND_WRITTEN = {"README.md", ".gitattributes", "SHA256SUMS"}

        on_disk = {
            str(path.relative_to(CORPUS_DIR))
            for path in CORPUS_DIR.rglob("*")
            if path.is_file() and str(path.relative_to(CORPUS_DIR)) not in HAND_WRITTEN
        }
        self.assertEqual(
            set(recorded) - {"SHA256SUMS"}, on_disk,
            "SHA256SUMS and the corpus directory disagree about what exists",
        )

    def test_every_recorded_digest_is_correct(self) -> None:
        for line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, name = line.split("  ", 1)
            if name == "SHA256SUMS":
                continue
            with self.subTest(artefact=name):
                actual = hashlib.sha256((CORPUS_DIR / name).read_bytes()).hexdigest()
                self.assertEqual(actual, digest)


class FontSubsetTest(unittest.TestCase):
    def test_the_committed_subset_covers_every_character_the_document_draws(self) -> None:
        from ar_corpus import content, ttfsubset

        metrics = ttfsubset.read(FONT_ASSET.read_bytes())
        missing = sorted(set(content.document_characters()) - set(metrics.char_to_gid))
        self.assertEqual(missing, [], "the committed font subset is missing glyphs")

    def test_the_font_is_actually_embedded_in_the_baseline(self) -> None:
        """A non-embedded font would render through whatever the viewer substitutes,
        which is not reproducible across machines."""
        data = BASELINE.read_bytes()
        self.assertIn(b"/FontFile2", data)
        self.assertIn(b"ARCorpusSans", data)

    def test_no_two_characters_share_a_glyph(self) -> None:
        """Identity-H addresses glyphs, so a shared glyph would make two characters
        indistinguishable in the text layer and the oracle silently wrong."""
        from ar_corpus import ttfsubset

        metrics = ttfsubset.read(FONT_ASSET.read_bytes())
        seen: dict[int, str] = {}
        for char, gid in sorted(metrics.char_to_gid.items()):
            if gid in seen:
                self.fail(
                    f"U+{ord(seen[gid]):04X} and U+{ord(char):04X} share glyph {gid}"
                )
            seen[gid] = char


if __name__ == "__main__":
    unittest.main()
