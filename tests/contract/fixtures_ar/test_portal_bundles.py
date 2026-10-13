"""The portal-bundle fixtures: byte-stable, complete, honest about what each one means.

What is asserted, and why each assertion is worth having:

*   regeneration is byte-stable (twice in a row, across interpreters with different hash
    seeds, and equal to what is committed), because a fixture whose digest is an oracle
    must not move;
*   every synthetic PDF has a bundle carrying the committed PDF's bytes, `SHA256SUMS`
    covers them, and the manifest agrees with the bytes;
*   the validator accepts what the manifest says is accepted, and refuses each archive
    negative for exactly the constraint it was built for -- not merely "refuses" -- since
    a negative refused for the wrong reason proves nothing about its rule;
*   the generated stand-ins (a sparse file past the upload bound, 501 pages, a page with
    neither a layer nor a block) are what they claim to be;
*   the writer streams, and a zip bomb's disguise (a header that lies about a size) is
    caught by counting bytes, not by trusting the header.

`jsonschema` is not in the lock, so the validator implements the pinned block-list schema
itself, reading it from the contract; the tests do not import `src/` and need no
container, database or object store.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import stat
import struct
import subprocess
import sys
import tempfile
import tracemalloc
import unicodedata
import unittest
import zipfile
import zlib
from pathlib import Path

# See the note in test_manifest_grounding.py: `tools/fixtures` is on no import path and
# the root pyproject is a single-owner hotspot, so each module adds it itself.
REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "fixtures"
CORPUS_DIR = REPO_ROOT / "fixtures" / "synthetic" / "ar"
BUNDLE_DIR = CORPUS_DIR / "bundles"
MANIFEST = BUNDLE_DIR / "bundle_manifest.json"
CHECKSUMS = CORPUS_DIR / "SHA256SUMS"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import build_ar_corpus  # noqa: E402
import build_portal_bundles  # noqa: E402
from ar_corpus import pdfextract  # noqa: E402
from portal_bundle import (  # noqa: E402
    archive_negatives, blocklist, bundle, committed, generated, pdffacts, positives,
    results, schemacheck, stampaudit, validate, zipscan, zipwrite,
)
from portal_bundle import portal_format as fmt  # noqa: E402

MiB = 1024 * 1024
# Small bounds for the size-driven tests: the sizes are arguments precisely so a test does
# not have to write hundreds of MiB to cross them.
SMALL = validate.Limits(member_bytes=2 * MiB, stamp_audit_bytes=64 * 1024)

# The corpus generator's lines in SHA256SUMS, as they were before the bundles were added.
# They must not change: INGEST consumes the negatives until it switches them.
ORIGINAL_SUMS = (
    ("6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f", "ar_baseline.pdf"),
    ("8ed158305cc8d16114b435c60479b51601b435d25c359e605a5a84b185899276", "expected_issues.json"),
    ("9513362c5d85dec1438406ffd4e77fef6d08bb18f104a5b107afc610dde8faba", "negative/encrypted.pdf"),
    ("8917d48af68cffac071fdf75040d181a548d27d952baa05defbca48a2ca94325", "negative/image_only.pdf"),
    ("623bf92bbbf989c1d350f9c8038f9dd6379ee1538100374fd230a81812a665ef", "negative/oversize.pdf"),
    ("acb3c347dbfe4b38efbc7e56f4389e97725b529966defa2a39c21e34f74da12a", "negative/too_many_pages.pdf"),
    ("ef968094226cd1559df9e2169eac549a8160ded5787fac492900fa899da5187d", "negative/not_a_pdf.txt"),
    ("05a5bb6305d56ed44a3f64769fecaa339529adaa28fa51b693147b76d60139cb", "negative/companion_archive.zip"),
)

# The oracle, written out independently of `committed.py` so a wrong `expect` there is
# caught here: file -> (source PDF, refusal constraint or None).
EXPECTED = {
    "ar_baseline.zip": ("ar_baseline.pdf", None),
    "ar_baseline_minimal.zip": ("ar_baseline.pdf", None),
    "ar_baseline_ocr_defects.zip": ("ar_baseline.pdf", None),
    "image_only.zip": ("negative/image_only.pdf", "every_page_has_extractable_text"),
    "image_only_with_block.zip": ("negative/image_only.pdf", None),
    "encrypted.zip": ("negative/encrypted.pdf", "not_encrypted"),
    "pages_31.zip": ("negative/too_many_pages.pdf", None),
}

# The one committed PDF that has no bundle, and why: its meaning (a PDF over 25 MiB) is
# gone under the bundle rules, and `generated.oversize_sparse_file` replaces it.
UNBUNDLED_PDFS = {"negative/oversize.pdf"}

SECTION = re.compile(
    r"^### BLOCK #(\d+) \[(TEXT|IMAGE)\]: (blk_[0-9a-f]{32})\n\n((?:> [^\n]*\n)+)\n"
    r"(.*?)(?=^### BLOCK #|^## Page |\Z)", re.MULTILINE | re.DOTALL)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def read_zip(data: bytes) -> dict[str, bytes]:
    """Member name -> bytes, read by the standard library (an independent reader)."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        return {info.filename: archive.read(info) for info in archive.infolist()}


def members_by_role(data: bytes) -> dict[str, bytes]:
    out = {}
    with zipscan.Archive.from_bytes(data) as archive:
        for entry in archive.load_entries():
            out[fmt.role_of(entry.name)] = b"".join(archive.read_chunks(entry))
    return out


def text_sections(markdown: str) -> dict[str, tuple[int, str, str]]:
    """block id -> (ordinal, type, body) for every section of a recognised-text markdown."""
    return {m.group(3): (int(m.group(1)), m.group(2), m.group(5).strip("\n"))
            for m in SECTION.finditer(markdown)}


class ByteStabilityTest(unittest.TestCase):
    def test_building_twice_in_one_process_gives_identical_bytes(self) -> None:
        first = build_portal_bundles.build_all()
        second = build_portal_bundles.build_all()
        self.assertEqual([p.name for p, _ in first], [p.name for p, _ in second])
        for (path, one), (_, two) in zip(first, second):
            with self.subTest(artefact=path.name):
                self.assertEqual(one, two)

    def test_the_rebuild_equals_every_committed_file(self) -> None:
        for path, data in build_portal_bundles.build_all():
            with self.subTest(artefact=str(path.relative_to(REPO_ROOT))):
                self.assertTrue(path.is_file(), "not committed")
                self.assertEqual(sha256(path.read_bytes()), sha256(data))

    def test_check_mode_exits_zero_in_a_fresh_interpreter(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "build_portal_bundles.py"), "--check"],
            capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertEqual(completed.returncode, 0,
                         f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")

    def test_interpreters_with_different_hash_seeds_agree(self) -> None:
        program = (
            "import hashlib, sys; sys.path.insert(0, sys.argv[1]);"
            "import build_portal_bundles as b;"
            "print(hashlib.sha256(b''.join(d for _, d in b.build_all())).hexdigest())")
        digests = []
        for seed in ("0", "98765"):
            completed = subprocess.run(
                [sys.executable, "-c", program, str(TOOLS_DIR)], capture_output=True,
                text=True, cwd=str(REPO_ROOT),
                env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": seed, "TZ": "Pacific/Kiritimati",
                     "LC_ALL": "C"})
            self.assertEqual(completed.returncode, 0, completed.stderr)
            digests.append(completed.stdout.strip())
        self.assertEqual(digests[0], digests[1])

    def test_the_package_imports_nothing_that_could_vary_between_runs(self) -> None:
        banned = {"time", "random", "uuid", "secrets", "datetime", "locale", "os", "platform",
                  "getpass", "socket"}
        for source in sorted((TOOLS_DIR / "portal_bundle").glob("*.py")):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                with self.subTest(module=source.name, imports=names):
                    self.assertFalse(banned & set(names))

    def test_no_output_carries_a_path_a_clock_reading_or_a_host_name(self) -> None:
        forbidden = [str(REPO_ROOT).encode(), str(Path.home()).encode(), b"/tmp/", b"worktrees"]
        everything: dict[str, bytes] = {}
        for path in sorted(BUNDLE_DIR.glob("*.zip")):
            for name, data in read_zip(path.read_bytes()).items():
                everything[f"{path.name}:{name}"] = data
        everything["manifest"] = MANIFEST.read_bytes()
        for name, data in everything.items():
            for needle in forbidden:
                with self.subTest(artefact=name, needle=needle):
                    self.assertNotIn(needle, data)

    def test_every_timestamp_is_one_of_the_fixed_constants(self) -> None:
        allowed = {fmt.GENERATED_AT_JSON, fmt.GENERATED_AT_MARKDOWN, fmt.BLOCK_CREATED_AT,
                   fmt.STAMP_AUDIT_GENERATED_AT}
        pattern = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00| UTC)?")
        for path in sorted(BUNDLE_DIR.glob("*.zip")):
            for name, data in read_zip(path.read_bytes()).items():
                if name.endswith(".pdf"):
                    continue
                with self.subTest(archive=path.name, member=name):
                    self.assertLessEqual(set(pattern.findall(data.decode("utf-8"))), allowed)

    def test_the_zip_timestamps_are_the_fixed_dos_constants(self) -> None:
        for path in sorted(BUNDLE_DIR.glob("*.zip")):
            with zipscan.Archive.from_bytes(path.read_bytes()) as archive:
                for entry in archive.load_entries():
                    local = archive._read(entry.header_offset, 30)
                    _sig, _v, _f, _m, time_, date_ = struct.unpack_from("<IHHHHH", local)
                    with self.subTest(archive=path.name, entry=entry.index):
                        self.assertEqual((time_, date_), (zipwrite.DOS_TIME, zipwrite.DOS_DATE))

    def test_identifiers_are_digests_of_the_stem_the_kind_and_a_number(self) -> None:
        self.assertEqual(fmt.block_id("s", "text", 3),
                         "blk_" + sha256(b"s:text:3")[:32])
        self.assertEqual(fmt.document_id("s"), "doc_" + sha256(b"s:document")[:32])
        # And the committed list really uses them: the n-th TEXT block of the baseline.
        document = json.loads(members_by_role((BUNDLE_DIR / "ar_baseline.zip").read_bytes())
                              [fmt.ROLE_BLOCKS])
        texts = [b["block_id"] for b in document["blocks"] if b["block_type"] == "text"]
        self.assertEqual(texts, [fmt.block_id("ar_baseline", "text", n) for n in range(1, 9)])
        self.assertEqual(document["document_id"], fmt.document_id("ar_baseline"))


class CommittedBundlesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = read_manifest()
        cls.entries = {e["file"]: e for e in cls.manifest["bundles"]}

    def test_the_committed_negatives_and_baseline_are_untouched(self) -> None:
        recorded = [tuple(line.split("  ", 1)) for line in
                    CHECKSUMS.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(tuple(recorded[:len(ORIGINAL_SUMS)]), ORIGINAL_SUMS)
        for digest, name in ORIGINAL_SUMS:
            with self.subTest(file=name):
                self.assertEqual(sha256((CORPUS_DIR / name).read_bytes()), digest)

    def test_every_synthetic_pdf_has_a_bundle_carrying_its_exact_bytes(self) -> None:
        pdfs = {str(p.relative_to(CORPUS_DIR)) for p in CORPUS_DIR.rglob("*.pdf")
                if BUNDLE_DIR not in p.parents}
        bundled = {e["source_pdf"].removeprefix("fixtures/synthetic/ar/") for e in self.entries.values()}
        self.assertEqual(pdfs - bundled, UNBUNDLED_PDFS)
        self.assertLessEqual(bundled, pdfs)
        for name, entry in self.entries.items():
            source = (REPO_ROOT / entry["source_pdf"]).read_bytes()
            pdf_members = [d for n, d in read_zip((BUNDLE_DIR / name).read_bytes()).items()
                           if n.endswith(".pdf")]
            with self.subTest(bundle=name):
                self.assertEqual(pdf_members, [source])

    def test_the_bundle_directory_holds_the_seven_bundles_and_the_manifest_only(self) -> None:
        self.assertEqual({p.name for p in BUNDLE_DIR.iterdir()},
                         set(EXPECTED) | {"bundle_manifest.json"})

    def test_sha256sums_covers_every_bundle_file_and_verifies(self) -> None:
        recorded = dict(reversed(line.split("  ", 1)) for line in
                        CHECKSUMS.read_text(encoding="utf-8").splitlines())
        on_disk = {f"bundles/{p.name}" for p in BUNDLE_DIR.iterdir()}
        self.assertEqual({n for n in recorded if n.startswith("bundles/")}, on_disk)
        for name in sorted(on_disk):
            with self.subTest(file=name):
                self.assertEqual(recorded[name], sha256((CORPUS_DIR / name).read_bytes()))

    def test_sha256sum_itself_accepts_the_file(self) -> None:
        completed = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=str(CORPUS_DIR),
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_the_manifest_agrees_with_the_bytes(self) -> None:
        self.assertEqual(self.manifest["schema"], "ar-portal-bundles/1")
        self.assertEqual(set(self.entries), set(EXPECTED))
        for name, entry in self.entries.items():
            data = (BUNDLE_DIR / name).read_bytes()
            with self.subTest(bundle=name):
                self.assertEqual((entry["size"], entry["sha256"]), (len(data), sha256(data)))
                listed = [(m["name"], m["role"], m["size"], m["sha256"]) for m in entry["members"]]
                with zipscan.Archive.from_bytes(data) as archive:
                    actual = []
                    for e in archive.load_entries():
                        content = b"".join(archive.read_chunks(e))
                        actual.append((zipscan.decode_display_name(e.name, e.flags, e.extra),
                                       fmt.role_of(e.name), len(content), sha256(content)))
                self.assertEqual(listed, actual)
                roles = members_by_role(data)
                document = json.loads(roles[fmt.ROLE_BLOCKS])
                counts = {k: sum(1 for b in document["blocks"] if b["block_type"] == k)
                          for k in fmt.KINDS}
                self.assertEqual(entry["blocks"], counts)
                self.assertEqual(entry["page_count"], len(document["pages"]))
                source = (REPO_ROOT / entry["source_pdf"]).read_bytes()
                if entry["refusal"] is None or entry["refusal"]["constraint"] != "not_encrypted":
                    self.assertEqual(entry["page_count"], pdfextract.page_count(source))
                self.assertEqual(entry["stem"] + ".pdf", entry["members"][0]["name"])

    def test_the_oracle_is_the_one_the_task_states(self) -> None:
        for name, (source, constraint) in EXPECTED.items():
            entry = self.entries[name]
            with self.subTest(bundle=name):
                self.assertEqual(entry["source_pdf"], f"fixtures/synthetic/ar/{source}")
                if constraint is None:
                    self.assertEqual((entry["expected"], entry["refusal"]), ("accepted", None))
                else:
                    self.assertEqual(entry["expected"], "refused")
                    self.assertEqual(entry["refusal"]["constraint"], constraint)
                    self.assertEqual(entry["refusal"]["field"],
                                     validate.CONSTRAINT_FIELDS[constraint])

    def test_the_validator_agrees_with_the_oracle_on_the_committed_archives(self) -> None:
        for name, (_source, constraint) in EXPECTED.items():
            verdict = validate.validate((BUNDLE_DIR / name).read_bytes(), bundle.GENERATOR_LIMITS)
            with self.subTest(bundle=name):
                self.assertEqual(verdict.constraints, () if constraint is None else (constraint,))

    def test_the_complete_bundle_has_everything_the_task_asks_for(self) -> None:
        roles = members_by_role((BUNDLE_DIR / "ar_baseline.zip").read_bytes())
        self.assertEqual(set(roles), set(fmt.ROLE_ORDER))
        document = json.loads(roles[fmt.ROLE_BLOCKS])
        kinds = [b["block_type"] for b in document["blocks"]]
        self.assertEqual(kinds.count("text"), 8)
        self.assertGreaterEqual(kinds.count("image"), 2)
        self.assertGreaterEqual(kinds.count("stamp"), 1)
        polygons = [b for b in document["blocks"] if b["polygon_points"] is not None]
        self.assertGreaterEqual(len(polygons), 1)
        for block in polygons:
            self.assertEqual(block["block_type"], "image")
            self.assertEqual(block["shape_type"], "polygon")
            self.assertTrue(6 <= len(block["polygon_points"]) <= 11)
        audit = json.loads(roles[fmt.ROLE_STAMP_AUDIT])
        self.assertTrue(audit["stamps"])
        self.assertEqual({s["block_id"] for s in audit["stamps"]},
                         {b["block_id"] for b in document["blocks"] if b["block_type"] == "stamp"})
        self.assertTrue(roles[fmt.ROLE_RESULTS_HTML].startswith(b"<!DOCTYPE html>"))

    def test_the_minimal_bundle_has_the_three_required_members_and_text_blocks_only(self) -> None:
        roles = members_by_role((BUNDLE_DIR / "ar_baseline_minimal.zip").read_bytes())
        self.assertEqual(set(roles), set(fmt.REQUIRED_ROLES))
        kinds = {b["block_type"] for b in json.loads(roles[fmt.ROLE_BLOCKS])["blocks"]}
        self.assertEqual(kinds, {"text"})

    def test_recognised_text_of_the_clean_bundles_is_the_text_layer(self) -> None:
        for name in ("ar_baseline_minimal.zip", "ar_baseline.zip", "pages_31.zip"):
            roles = members_by_role((BUNDLE_DIR / name).read_bytes())
            layer = pdfextract.extract_pages(roles[fmt.ROLE_PDF])
            document = json.loads(roles[fmt.ROLE_BLOCKS])
            sections = text_sections(roles[fmt.ROLE_RESULTS_MD].decode("utf-8"))
            for block in document["blocks"]:
                if block["block_type"] != "text":
                    continue
                with self.subTest(bundle=name, page=block["page_index"] + 1):
                    self.assertEqual(sections[block["block_id"]][2], layer[block["page_index"]])

    def test_the_scanned_bundle_pair_differs_only_by_the_blocks(self) -> None:
        bare = members_by_role((BUNDLE_DIR / "image_only.zip").read_bytes())
        blocked = members_by_role((BUNDLE_DIR / "image_only_with_block.zip").read_bytes())
        self.assertEqual(bare[fmt.ROLE_PDF], blocked[fmt.ROLE_PDF])
        self.assertEqual(json.loads(bare[fmt.ROLE_BLOCKS])["blocks"], [])
        self.assertEqual(pdfextract.extract_pages(bare[fmt.ROLE_PDF]), ["", ""])
        document = json.loads(blocked[fmt.ROLE_BLOCKS])
        self.assertEqual([(b["block_type"], b["page_index"]) for b in document["blocks"]],
                         [("text", 0), ("text", 1)])
        sections = text_sections(blocked[fmt.ROLE_RESULTS_MD].decode("utf-8"))
        self.assertEqual(len(sections), 2)
        self.assertTrue(all("распознан" in body for _o, _t, body in sections.values()))

    def test_the_31_page_bundle_is_valid_under_the_new_limit(self) -> None:
        verdict = validate.validate((BUNDLE_DIR / "pages_31.zip").read_bytes(),
                                    bundle.GENERATOR_LIMITS)
        self.assertTrue(verdict.accepted)
        self.assertEqual((verdict.page_count, verdict.block_counts["text"]), (31, 31))


class FormatTest(unittest.TestCase):
    """The measured portal formats, held by the baseline bundle."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.roles = members_by_role((BUNDLE_DIR / "ar_baseline.zip").read_bytes())
        cls.document = json.loads(cls.roles[fmt.ROLE_BLOCKS])
        cls.markdown = cls.roles[fmt.ROLE_RESULTS_MD].decode("utf-8")

    def test_the_block_list_has_the_portals_keys_in_the_portals_order(self) -> None:
        self.assertEqual(list(self.document), [
            "schema_version", "document_id", "document_name", "document_path",
            "generated_at", "coordinate_space", "pages", "blocks"])
        self.assertEqual(list(self.document["pages"][0]),
                         ["page_index", "width_px", "height_px", "rotation"])
        self.assertEqual(list(self.document["blocks"][0]), [
            "block_id", "ordinal", "page_index", "page_label", "block_type", "shape_type",
            "status", "export_status", "coords_norm", "polygon_points", "crop_url"])
        self.assertEqual(self.document["coordinate_space"], "normalized_page_top_left")
        self.assertRegex(self.document["document_id"], r"^doc_[0-9a-f]{32}$")
        self.assertRegex(self.document["generated_at"], r"^\d{4}-\d\d-\d\dT[\d:.]+Z$")

    def test_ordinals_run_over_text_and_image_blocks_in_reading_order_and_stamps_have_none(self) -> None:
        counted = [b for b in self.document["blocks"] if b["block_type"] != "stamp"]
        self.assertEqual([b["ordinal"] for b in counted], list(range(1, len(counted) + 1)))
        for block in self.document["blocks"]:
            with self.subTest(block=block["block_id"]):
                self.assertEqual(block["page_label"], block["page_index"] + 1)
                if block["block_type"] == "stamp":
                    self.assertIsNone(block["ordinal"])
                    self.assertIsNone(block["crop_url"])
                else:
                    self.assertRegex(block["crop_url"],
                                     r"^https://portal\.invalid/api/crops/[A-Za-z0-9_-]{20}$")
        by_page = [b["page_index"] for b in counted]
        self.assertEqual(by_page, sorted(by_page))

    def test_page_sizes_are_the_300_dpi_render_and_match_the_pdf_aspect(self) -> None:
        pdf_pages = pdffacts.read_pages(self.roles[fmt.ROLE_PDF])
        for portal, page in zip(self.document["pages"], pdf_pages):
            with self.subTest(page=portal["page_index"] + 1):
                self.assertEqual(portal["width_px"], round(page.width_pt * 300 / 72))
                self.assertEqual(portal["height_px"], round(page.height_pt * 300 / 72))
                aspect = (portal["width_px"] / portal["height_px"]) / (page.width_pt / page.height_pt)
                self.assertLess(abs(aspect - 1), 0.005)
        self.assertEqual({(p["width_px"], p["height_px"]) for p in self.document["pages"]},
                         {(2480, 3508)})

    def test_markdown_headers_follow_the_portals_layout(self) -> None:
        lines = self.markdown.split("\n")
        self.assertEqual(lines[0], "# Document: ar_baseline.pdf")
        self.assertTrue(lines[2].startswith("Path: "))
        self.assertEqual(lines[4], "Generated: 2026-07-24 07:45:12 UTC")
        self.assertTrue(lines[6].startswith("**Stamp:** Code: "))
        self.assertEqual(lines[8], "---")
        self.assertEqual(re.findall(r"^## Page (\d+)$", self.markdown, re.M),
                         [str(n) for n in range(1, 9)])
        self.assertTrue(self.markdown.endswith("\n") and not self.markdown.endswith("\n\n"))
        first = text_sections(self.markdown)
        self.assertEqual(len(first), 10)       # 8 TEXT and 2 IMAGE; the stamps have none
        header = next(m for m in SECTION.finditer(self.markdown))
        self.assertRegex(header.group(4), r"^> \*\*Created:\*\* \d{4}-\d\d-\d\d [\d:]+ UTC\n"
                                          r"> \*\*Crop:\*\* \[Crop\]\(https://\S+\)\n"
                                          r"> \*\*Stamp:\*\* Code: .* \| Revisions: \n$")

    def test_image_blocks_carry_the_portals_description_fields(self) -> None:
        bodies = [body for _o, kind, body in text_sections(self.markdown).values()
                  if kind == "IMAGE"]
        self.assertEqual(len(bodies), 2)
        for body in bodies:
            with self.subTest(body=body[:30]):
                self.assertRegex(body, r"^\*\*\[IMAGE\]\*\* \| Type: .+ \| Axes: .+\n\n"
                                       r"\*\*Summary:\*\* .+\n\n\*\*Description:\*\* .+\n\n"
                                       r"\*\*Entities:\*\* .+$")

    def test_stamps_appear_in_the_block_list_and_never_in_the_markdown(self) -> None:
        stamp_ids = {b["block_id"] for b in self.document["blocks"] if b["block_type"] == "stamp"}
        self.assertTrue(stamp_ids)
        for identifier in stamp_ids:
            self.assertNotIn(identifier, self.markdown)
        self.assertNotIn("[STAMP]", self.markdown)

    def test_the_stamp_audit_has_the_owners_corpus_shape(self) -> None:
        audit = json.loads(self.roles[fmt.ROLE_STAMP_AUDIT])
        self.assertEqual(list(audit), ["schema_version", "document_id", "document_name",
                                       "generated_at", "enabled", "stamps", "volume", "pages"])
        self.assertEqual(audit["generated_at"], "2026-08-25T09:47:54.548970+00:00")
        self.assertEqual(list(audit["volume"]), ["fields", "origins", "conflicts", "excluded"])
        self.assertEqual([p["page_index"] for p in audit["pages"]], list(range(8)))
        self.assertEqual(list(audit["pages"][0]),
                         ["page_index", "fields", "origins", "conflicts", "excluded"])
        # With no stamp at all the audit has the empty shape the owner's bundles show.
        empty = json.loads(stampaudit.build("s", 2, []))
        self.assertEqual(empty["stamps"], [])
        self.assertEqual(empty["volume"], {"fields": {}, "origins": {}, "conflicts": {},
                                           "excluded": []})
        self.assertEqual(empty["pages"][1], {"page_index": 1, "fields": {}, "origins": {},
                                             "conflicts": {}, "excluded": []})

    def test_the_html_is_a_small_deterministic_document_without_links(self) -> None:
        html = self.roles[fmt.ROLE_RESULTS_HTML].decode("utf-8")
        self.assertNotIn("http", html)
        self.assertNotIn("<script", html)
        again = results.render_html("ar_baseline", bundle.DISPLAY_PATH.format(stem="ar_baseline"),
                                    8, committed.baseline_full(self.roles[fmt.ROLE_PDF]).blocks)
        self.assertEqual(html, again)

    def test_the_defect_variant_seeds_each_kind_and_keeps_designations_unflagged(self) -> None:
        entry = {e["file"]: e for e in read_manifest()["bundles"]}["ar_baseline_ocr_defects.zip"]
        seeded = entry["seeded_text_defects"]
        self.assertEqual(sorted({d["kind"] for d in seeded}), [
            "cjk_character", "doubled_list_marker", "engineering_designation",
            "latin_homoglyph", "mixed_script_word"])
        roles = members_by_role((BUNDLE_DIR / "ar_baseline_ocr_defects.zip").read_bytes())
        sections = text_sections(roles[fmt.ROLE_RESULTS_MD].decode("utf-8"))
        for defect in seeded:
            body = sections[defect["block_id"]][2]
            with self.subTest(kind=defect["kind"], recognised=defect["recognised"]):
                self.assertIn(defect["recognised"], body)
                self.assertEqual(defect["flaggable"], defect["kind"] != "engineering_designation")
                scripts = {unicodedata.name(c).split()[0] for c in defect["recognised"] if c.isalpha()}
                if defect["kind"] == "latin_homoglyph":
                    self.assertTrue({"LATIN", "CYRILLIC"} <= scripts)
                if defect["kind"] == "mixed_script_word":
                    self.assertTrue({"LATIN", "CYRILLIC"} <= scripts)
                if defect["kind"] == "cjk_character":
                    self.assertTrue(any("CJK UNIFIED" in unicodedata.name(c)
                                        for c in defect["recognised"]))
                if defect["kind"] == "doubled_list_marker":
                    self.assertTrue(defect["recognised"].startswith("- - "))
                if defect["kind"] == "engineering_designation":
                    self.assertNotIn("CYRILLIC", scripts)
        designations = {d["recognised"] for d in seeded if d["kind"] == "engineering_designation"}
        self.assertEqual(designations, {"B25", "A500C", "1.A", "REI 150"})
        # The PDF is the baseline's, so the layer is clean and only the recognised text differs.
        layer = pdfextract.extract_pages(roles[fmt.ROLE_PDF])
        document = json.loads(roles[fmt.ROLE_BLOCKS])
        differing = [b["page_index"] for b in document["blocks"]
                     if sections[b["block_id"]][2] != layer[b["page_index"]]]
        self.assertEqual(differing, [1, 2, 3, 4, 5])


class ValidatorTest(unittest.TestCase):
    def test_it_accepts_every_valid_but_unusual_positive(self) -> None:
        for name, build in positives.POSITIVES.items():
            data = build()
            verdict = validate.validate(data, bundle.GENERATOR_LIMITS)
            with self.subTest(positive=name):
                self.assertEqual(verdict.constraints, ())
                self.assertTrue(verdict.members)

    def test_the_standard_library_reads_every_valid_output(self) -> None:
        archives = {f"committed:{p.name}": p.read_bytes() for p in sorted(BUNDLE_DIR.glob("*.zip"))}
        archives.update({f"positive:{n}": b() for n, b in positives.POSITIVES.items()})
        for label, data in archives.items():
            with self.subTest(archive=label):
                standard = list(read_zip(data).values())
                with zipscan.Archive.from_bytes(data) as archive:
                    ours = [b"".join(archive.read_chunks(e)) for e in archive.load_entries()]
                self.assertEqual(standard, ours)

    def test_each_small_negative_is_refused_for_exactly_its_own_rule(self) -> None:
        negatives = archive_negatives.small_negatives()
        self.assertGreater(len(negatives), 50)
        for negative in negatives:
            verdict = validate.validate(negative.build(), bundle.GENERATOR_LIMITS)
            with self.subTest(rule=negative.constraint, negative=negative.name):
                self.assertEqual(
                    verdict.constraints, (negative.constraint,),
                    [(v.constraint, v.detail) for v in verdict.violations])
                self.assertEqual({v.field for v in verdict.violations},
                                 {validate.CONSTRAINT_FIELDS[negative.constraint]})

    def test_every_registered_bundle_constraint_has_a_negative_and_a_field(self) -> None:
        catalog = json.loads((REPO_ROOT / "contracts" / "domain" / "v1" / "error-codes.json")
                             .read_text(encoding="utf-8"))
        notes = " ".join(catalog["codes"]["validation_failed"]["notes"])
        registered = set(re.findall(
            r"\b(portal_bundle_required|bundle_[a-z_]+|blocks_json_invalid|blocks_page_count|"
            r"results_blocks_mismatch|stamp_audit_invalid)\b", notes))
        self.assertGreaterEqual(len(registered), 18)
        built = (set(archive_negatives.by_constraint()) | set(archive_negatives.SIZE_DRIVEN)
                 | {"max_bytes"})                  # the last one is the sparse stand-in's
        self.assertEqual(registered - built, set())
        self.assertEqual(registered - set(validate.CONSTRAINT_FIELDS), set())

    def test_the_pdf_member_keeps_its_existing_constraints_and_fields(self) -> None:
        # Records 17, 19, 20 and 21 of the characterization suite answer these fields.
        self.assertEqual(validate.CONSTRAINT_FIELDS["not_encrypted"], "content")
        self.assertEqual(validate.CONSTRAINT_FIELDS["pdf_magic_bytes"], "content")
        self.assertEqual(validate.CONSTRAINT_FIELDS["page_count"], "page_count")
        self.assertEqual(validate.CONSTRAINT_FIELDS["every_page_has_extractable_text"], "page_text")
        base = archive_negatives.base_files()
        wrong_magic = bundle.build_bundle(
            bundle.make_files(b"not a pdf", "bundle", pages=pdffacts.read_pages(base.pdf)),
            expect="pdf_magic_bytes")
        self.assertEqual(wrong_magic.verdict.violations[0].field, "content")

    def test_the_entry_count_gate_sits_between_eight_and_nine(self) -> None:
        eight = validate.validate(archive_negatives.entry_count(8), bundle.GENERATOR_LIMITS)
        nine = validate.validate(archive_negatives.entry_count(9), bundle.GENERATOR_LIMITS)
        # Eight entries get past the count and are then refused for what they hold.
        self.assertEqual(eight.constraints, ("bundle_member_set",))
        self.assertEqual(nine.constraints, ("bundle_entry_count",))

    def test_the_block_list_schema_is_read_from_the_contract_and_guarded(self) -> None:
        schema = validate.load_schema()
        contract = json.loads((REPO_ROOT / "contracts" / "analysis" / "v1" /
                               "portal-blocks.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema, contract)
        self.assertEqual(len(contract["x-envelope-rules"]), validate.IMPLEMENTED_ENVELOPE_RULES)
        with self.assertRaises(schemacheck.SchemaSubsetError):
            schemacheck.assert_supported({"type": "object", "oneOf": []})
        with self.assertRaises(schemacheck.SchemaSubsetError):
            schemacheck.assert_supported({"properties": {"a": {"allOf": []}}})

    def test_the_schema_subset_checker_can_fail(self) -> None:
        schema = validate.load_schema()
        good = json.loads(members_by_role((BUNDLE_DIR / "ar_baseline.zip").read_bytes())
                          [fmt.ROLE_BLOCKS])
        self.assertEqual(schemacheck.check(good, schema), [])
        broken = json.loads(json.dumps(good))
        broken["blocks"][0]["coords_norm"] = [0, 0, 2, 1]
        broken["blocks"][1]["ordinal"] = True
        broken["pages"][0]["rotation"] = 45
        del broken["blocks"][2]["status"]
        broken["schema_version"] = True
        errors = schemacheck.check(broken, schema)
        for fragment in ("coords_norm[2]", "ordinal", "rotation", "status", "schema_version"):
            self.assertTrue(any(fragment in e for e in errors), (fragment, errors))

    def test_names_are_compared_on_raw_bytes_across_encodings(self) -> None:
        items = archive_negatives.members(archive_negatives.CYRILLIC_STEM)
        # The same Cyrillic stem, once as UTF-8 and once as cp866: the display names agree,
        # the raw bytes do not, and the raw bytes decide.
        items[1].name = (archive_negatives.CYRILLIC_STEM + "_blocks.json").encode("cp866")
        items[1].flags = 0
        data = zipwrite.build_zip(items)
        verdict = validate.validate(data, bundle.GENERATOR_LIMITS)
        self.assertEqual(verdict.constraints, ("bundle_stem_mismatch",))
        with zipscan.Archive.from_bytes(data) as archive:
            shown = {zipscan.decode_display_name(e.name, e.flags, e.extra)[:5]
                     for e in archive.load_entries()}
        self.assertEqual(shown, {archive_negatives.CYRILLIC_STEM})

    def test_display_names_decode_in_the_ruled_order(self) -> None:
        decode = zipscan.decode_display_name
        stem = "Проект"
        utf8, cp866 = stem.encode("utf-8"), stem.encode("cp866")
        other = zipwrite.unicode_path_extra(utf8, "Другой".encode("utf-8"))
        # 1. flag 11 wins, even over an Info-ZIP field naming something else.
        self.assertEqual(decode(utf8, zipwrite.FLAG_UTF8, other), stem)
        # 2. without the flag the Info-ZIP field wins over what the header bytes decode as.
        self.assertEqual(decode(utf8, 0, other), "Другой")
        field = zipwrite.unicode_path_extra(cp866, utf8)
        self.assertEqual(decode(cp866, 0, field), stem)
        # ...but only while its CRC still matches the header name; an edited name is ignored.
        self.assertEqual(decode(utf8, 0, zipwrite.unicode_path_extra(b"edited", b"x")), stem)
        # 3. then strict UTF-8.
        self.assertEqual(decode(utf8, 0, b""), stem)
        # 4. and only if that fails, cp866 -- which cannot fail.
        self.assertEqual(decode(cp866, 0, b""), stem)
        self.assertEqual(decode(bytes(range(0x80, 0x100)), 0, b"").encode("cp866"),
                         bytes(range(0x80, 0x100)))
        # A flagged name that is not UTF-8 is shown with replacement characters, not refused.
        self.assertIn("�", decode(cp866, zipwrite.FLAG_UTF8, b""))

    def test_the_four_name_encodings_decode_to_the_same_display_name(self) -> None:
        for encoding in bundle.NAME_ENCODINGS:
            data = positives.name_encoding(encoding)
            with zipscan.Archive.from_bytes(data) as archive:
                entries = archive.load_entries()
                shown = [zipscan.decode_display_name(e.name, e.flags, e.extra) for e in entries]
                with self.subTest(encoding=encoding):
                    self.assertEqual(shown[0], "Проект_АР.pdf")
                    flagged = {bool(e.flags & zipwrite.FLAG_UTF8) for e in entries}
                    has_field = {bool(zipscan.unicode_path(e.name, e.extra)) for e in entries}
                    raw_is_utf8 = entries[0].name == "Проект_АР.pdf".encode("utf-8")
                    expected = {"utf8_flag": ({True}, {False}, True),
                                "utf8_plain": ({False}, {False}, True),
                                "infozip_unicode": ({False}, {True}, False),
                                "cp866": ({False}, {False}, False)}[encoding]
                    self.assertEqual((flagged, has_field, raw_is_utf8), expected)

    def test_a_bundle_is_judged_on_what_it_unpacks_to_not_on_what_it_says(self) -> None:
        # A member whose CRC does not match is unreadable even when every size is right.
        self.assertEqual(
            validate.validate(archive_negatives.crc_mismatch(), bundle.GENERATOR_LIMITS).constraints,
            ("bundle_unreadable",))


class ZipWriterTest(unittest.TestCase):
    def matrix(self):
        for descriptor in (False, True):
            for zip64 in (False, True):
                for method, deflate in ((0, "stored_blocks"), (8, "stored_blocks"), (8, "zlib")):
                    yield descriptor, zip64, method, deflate

    def test_standard_library_reads_every_header_combination(self) -> None:
        payloads = [b"", b"x", b"%PDF-1.7 " + bytes(range(256)) * 700, "Привет\n".encode() * 3000]
        for descriptor, zip64, method, deflate in self.matrix():
            items = [zipwrite.Member(f"m{i}.bin".encode(), p, method=method, deflate=deflate,
                                     zip64=zip64,
                                     flags=zipwrite.FLAG_DESCRIPTOR if descriptor else 0)
                     for i, p in enumerate(payloads)]
            for end64 in (False, True):
                with self.subTest(descriptor=descriptor, zip64=zip64, method=method,
                                  deflate=deflate, zip64_end=end64):
                    data = zipwrite.build_zip(items, zip64_end=end64)
                    got = read_zip(data)
                    self.assertEqual(list(got.values()), payloads)
                    with zipscan.Archive.from_bytes(data) as archive:
                        scanned = [b"".join(archive.read_chunks(e)) for e in archive.load_entries()]
                    self.assertEqual(scanned, payloads)

    def test_the_directory_reader_agrees_with_the_standard_library(self) -> None:
        data = positives.every_optional_member()
        with zipfile.ZipFile(io.BytesIO(data)) as archive, zipscan.Archive.from_bytes(data) as ours:
            for info, entry in zip(archive.infolist(), ours.load_entries()):
                self.assertEqual((info.CRC, info.file_size, info.compress_size, info.compress_type),
                                 (entry.crc, entry.size, entry.compressed_size, entry.method))
                self.assertEqual(info.header_offset, entry.header_offset)

    def test_the_same_members_always_give_the_same_bytes(self) -> None:
        def build() -> bytes:
            return zipwrite.build_zip(archive_negatives.members(), zip64_end=True)
        self.assertEqual(build(), build())
        self.assertEqual(sha256(build()), sha256(build()))

    def test_stored_block_deflate_is_a_valid_deflate_stream_whatever_the_length(self) -> None:
        for length in (0, 1, 65534, 65535, 65536, 65537, 200000):
            data = bytes((i * 7) % 251 for i in range(length))
            with self.subTest(length=length):
                self.assertEqual(zlib.decompress(zipwrite.deflate_stored_blocks(data), -15), data)

    def test_the_fields_a_negative_needs_land_where_the_standard_library_sees_them(self) -> None:
        link = zipfile.ZipFile(io.BytesIO(archive_negatives.symlink())).infolist()[2]
        self.assertTrue(stat.S_ISLNK(link.external_attr >> 16))
        flagged = zipfile.ZipFile(io.BytesIO(archive_negatives.encrypted_member())).infolist()[0]
        self.assertTrue(flagged.flag_bits & 0x1)
        directory = zipfile.ZipFile(io.BytesIO(archive_negatives.directory_entry())).infolist()[3]
        self.assertTrue(directory.is_dir())
        method = zipfile.ZipFile(io.BytesIO(archive_negatives.compression_method(99))).infolist()[1]
        self.assertEqual(method.compress_type, 99)
        descriptor = zipfile.ZipFile(io.BytesIO(positives.data_descriptors())).infolist()[1]
        self.assertTrue(descriptor.flag_bits & 0x8)
        wide = zipfile.ZipFile(io.BytesIO(positives.zip64_sizes())).infolist()[1]
        self.assertTrue(any(i == zipwrite.EXTRA_ZIP64 for i, _ in zipscan.parse_extra(wide.extra)))
        unicode_path = zipfile.ZipFile(io.BytesIO(positives.name_encoding("infozip_unicode"))).infolist()[0]
        self.assertTrue(any(i == zipwrite.EXTRA_UNICODE_PATH
                            for i, _ in zipscan.parse_extra(unicode_path.extra)))

    def test_a_large_member_streams_without_being_held_in_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "big.zip"
            tracemalloc.start()
            try:
                archive_negatives.member_size(path, member_bytes=64 * MiB - 1)
                _current, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertLess(peak, 8 * MiB, f"peak {peak} bytes while writing a 64 MiB member")
            self.assertLess(path.stat().st_size, MiB)       # zeros deflate to almost nothing
            with zipscan.Archive.from_path(path) as archive:
                self.assertEqual(archive.load_entries()[0].size, 64 * MiB)


class GeneratedFixturesTest(unittest.TestCase):
    def test_the_oversize_stand_in_is_sparse_and_past_the_upload_bound(self) -> None:
        size = fmt.MAX_UPLOAD_BYTES + 1024 * 1024
        with tempfile.TemporaryDirectory() as tmp:
            path = generated.oversize_sparse_file(Path(tmp) / "big.zip", size)
            info = path.stat()
            self.assertEqual(info.st_size, size)
            self.assertGreater(info.st_size, fmt.MAX_UPLOAD_BYTES)
            allocated = info.st_blocks * 512
            self.assertLess(allocated, MiB, f"{allocated} bytes allocated: the file is not sparse")
            with path.open("rb") as handle:
                self.assertEqual(handle.read(4), b"PK\x03\x04")
            verdict = validate.validate(path, bundle.GENERATOR_LIMITS)
            self.assertEqual(verdict.constraints, ("max_bytes",))

    def test_exactly_at_the_bound_the_size_rule_does_not_fire(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = generated.oversize_sparse_file(Path(tmp) / "edge.zip", fmt.MAX_UPLOAD_BYTES)
            verdict = validate.validate(path, bundle.GENERATOR_LIMITS)
            self.assertNotIn("max_bytes", verdict.constraints)
            self.assertEqual(verdict.constraints, ("bundle_unreadable",))

    def test_501_pages_are_501_pages_to_the_independent_reader_and_small(self) -> None:
        pdf = generated.pdf_with_n_pages(501)
        self.assertEqual(pdfextract.page_count(pdf), 501)
        self.assertLess(len(pdf), MiB)
        pages = pdfextract.extract_pages(pdf)
        self.assertTrue(all(text.strip() for text in pages))
        self.assertIn("501 из 501", pages[-1])

    def test_a_501_page_bundle_breaks_the_page_rule_and_a_500_page_one_does_not(self) -> None:
        over = validate.validate(generated.bundle_with_pages(501), bundle.GENERATOR_LIMITS)
        edge = validate.validate(generated.bundle_with_pages(500), bundle.GENERATOR_LIMITS)
        self.assertEqual(over.constraints, ("page_count",))
        self.assertEqual(edge.constraints, ())
        self.assertEqual(edge.page_count, 500)

    def test_a_page_without_a_layer_or_a_block_is_refused_and_a_block_satisfies_the_rule(self) -> None:
        pdf = generated.pdf_page_without_text_layer(page_count=3, textless_page=2)
        texts = pdfextract.extract_pages(pdf)
        self.assertEqual([bool(t.strip()) for t in texts], [True, False, True])
        self.assertEqual(
            validate.validate(generated.bundle_without_block_on_textless_page(),
                              bundle.GENERATOR_LIMITS).constraints,
            ("every_page_has_extractable_text",))
        self.assertTrue(validate.validate(generated.bundle_with_block_on_textless_page(),
                                          bundle.GENERATOR_LIMITS).accepted)
        bare = bundle.build_bundle(generated.files_without_block(),
                                   expect="every_page_has_extractable_text")
        self.assertIn("[2]", bare.verdict.violations[0].detail)
        self.assertEqual(blocklist.counts_by_kind(bare.files.blocks)["text"], 2)
        blocked = bundle.build_bundle(generated.files_with_block())
        self.assertEqual(blocklist.counts_by_kind(blocked.files.blocks)["text"], 3)
        recognised = text_sections(blocked.files.results_md.decode("utf-8"))
        second = [b for b in blocked.files.blocks if b.page_index == 1][0]
        self.assertIn("получен только из блока портала", recognised[second.block_id][2])

    def test_the_committed_negatives_are_still_what_they_were(self) -> None:
        # INGEST switches their consumers later; until then they are not to move.
        for digest, name in ORIGINAL_SUMS:
            self.assertEqual(sha256((CORPUS_DIR / name).read_bytes()), digest, name)


class SizeDrivenTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "archive.zip"

    def constraints(self, limits: validate.Limits = SMALL) -> tuple[str, ...]:
        return validate.validate(self.path, limits).constraints

    def test_one_byte_over_the_member_bound_is_refused_stored_or_deflated(self) -> None:
        for compress in ("stored", "deflate"):
            archive_negatives.member_size(self.path, member_bytes=SMALL.member_bytes,
                                          compress=compress)
            with self.subTest(compress=compress):
                self.assertEqual(self.constraints(), ("bundle_member_size",))

    def test_a_member_exactly_at_the_bound_passes_the_size_rules(self) -> None:
        archive_negatives.member_size(self.path, member_bytes=SMALL.member_bytes - 1,
                                      compress="stored")
        # The padded PDF is not a document, so a later gate refuses it -- not a size rule.
        self.assertEqual(self.constraints(), ("parseable_pdf",))

    def test_two_members_inside_the_member_bound_that_pass_the_total_are_refused(self) -> None:
        for compress in ("stored", "deflate"):
            archive_negatives.total_size(self.path, member_bytes=SMALL.member_bytes,
                                         total_bytes=3 * MiB, compress=compress)
            limits = validate.Limits(member_bytes=SMALL.member_bytes, stamp_audit_bytes=1024,
                                     total_bytes=3 * MiB)
            with self.subTest(compress=compress):
                self.assertEqual(self.constraints(limits), ("bundle_total_size",))
        with self.assertRaises(ValueError):
            archive_negatives.total_size(self.path, member_bytes=MiB, total_bytes=3 * MiB)

    def test_a_ratio_above_the_bound_is_refused_and_one_below_it_is_not(self) -> None:
        archive_negatives.compression_ratio(self.path, size=MiB)
        self.assertEqual(self.constraints(), ("bundle_compression_ratio",))
        # The same zeros, with the bound raised past their ratio, are no longer a ratio problem.
        relaxed = validate.Limits(member_bytes=SMALL.member_bytes, stamp_audit_bytes=1024,
                                  ratio=100_000)
        self.assertNotIn("bundle_compression_ratio", self.constraints(relaxed))
        with self.assertRaises(ValueError):
            archive_negatives.compression_ratio(self.path, size=MiB, ratio=1_000_000)

    def test_a_header_that_declares_less_than_the_member_holds_is_caught_by_counting(self) -> None:
        for compress in ("stored", "deflate"):
            archive_negatives.size_lie_declared_small(
                self.path, actual_bytes=SMALL.member_bytes + 1024, declared_bytes=1,
                compress=compress)
            with zipscan.Archive.from_path(self.path) as archive:
                entry = archive.load_entries()[0]
                self.assertEqual(entry.size, 1)            # the lie
                self.assertEqual(validate._declared_size_rules((entry,), SMALL), [])
            with self.subTest(compress=compress):
                self.assertEqual(self.constraints(), ("bundle_member_size",))
        with self.assertRaises(ValueError):
            archive_negatives.size_lie_declared_small(self.path, actual_bytes=10, declared_bytes=10)

    def test_a_header_that_declares_more_than_the_member_holds_is_refused_on_its_word(self) -> None:
        archive_negatives.size_lie_declared_large(
            self.path, actual_bytes=1000, declared_bytes=SMALL.member_bytes + 1)
        self.assertEqual(self.constraints(), ("bundle_member_size",))
        # Past 4 GiB the header needs ZIP64 and the lie is still caught; the total bound
        # is exceeded by the same word, so both size rules speak.
        archive_negatives.size_lie_declared_large(self.path, actual_bytes=1000,
                                                  declared_bytes=10 * 1024 * MiB)
        verdict = validate.validate(self.path, SMALL)
        self.assertEqual(verdict.constraints[0], "bundle_member_size")
        self.assertLessEqual(set(verdict.constraints), {"bundle_member_size", "bundle_total_size"})
        with self.assertRaises(ValueError):
            archive_negatives.size_lie_declared_large(self.path, actual_bytes=10, declared_bytes=10)

    def test_a_declared_size_just_past_the_upload_bound_is_refused_at_the_freeze_values(self) -> None:
        # The 250 MiB bound a stand would use: the declared size refuses the member before
        # a byte of it is read, so the archive on disk is a few hundred bytes.
        limits = validate.Limits(member_bytes=fmt.MAX_UPLOAD_BYTES, stamp_audit_bytes=1024)
        archive_negatives.size_lie_declared_large(
            self.path, actual_bytes=1000, declared_bytes=fmt.MAX_UPLOAD_BYTES + 1)
        self.assertEqual(self.constraints(limits), ("bundle_member_size",))


class AssembleToolTest(unittest.TestCase):
    TOOL = TOOLS_DIR / "assemble_portal_bundle.py"

    def export(self, directory: Path, files: bundle.PortalFiles) -> None:
        stem = files.stem
        (directory / f"{stem}.pdf").write_bytes(files.pdf)
        (directory / f"{stem}_blocks.json").write_bytes(files.blocks_json)
        (directory / f"{stem}_results.md").write_bytes(files.results_md)
        if files.results_html is not None:
            (directory / f"{stem}_results.html").write_bytes(files.results_html)
        (directory / "input_manifest.json").write_text("{}", encoding="utf-8")   # not a member

    def run_tool(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.TOOL), *args],
                              capture_output=True, text=True, cwd=str(REPO_ROOT))

    def test_it_packages_a_synthetic_export_deterministically(self) -> None:
        pdf = (CORPUS_DIR / "ar_baseline.pdf").read_bytes()
        stem = "Проект_АР"
        files = bundle.make_files(pdf, stem, html=True, stamp_audit=True)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "export"
            source.mkdir()
            self.export(source, files)
            audit = Path(tmp) / "audit.json"
            audit.write_bytes(files.stamp_audit)
            outputs = []
            for name in ("one.zip", "two.zip"):
                out = Path(tmp) / name
                done = self.run_tool(str(source), str(out), "--stamp-audit", str(audit))
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertIn("left out: input_manifest.json", done.stdout)
                outputs.append(out.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            members = read_zip(outputs[0])
            self.assertEqual(list(members), [f"{stem}.pdf", f"{stem}_blocks.json",
                                             f"{stem}_results.md", f"{stem}_results.html",
                                             f"{stem}_stamp_audit.json"])
            self.assertEqual(members[f"{stem}.pdf"], pdf)
            self.assertEqual(members[f"{stem}_results.md"], files.results_md)
            self.assertTrue(validate.validate(outputs[0], bundle.GENERATOR_LIMITS).accepted)
            self.assertEqual([p.name for p in Path(tmp).glob("*.part")], [])

    def test_it_refuses_and_leaves_nothing_when_the_validator_rejects(self) -> None:
        files = bundle.make_files((CORPUS_DIR / "ar_baseline.pdf").read_bytes(), "synthetic")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "export"
            source.mkdir()
            self.export(source, files)
            # A markdown that lost a section no longer matches the block list.
            md = source / "synthetic_results.md"
            md.write_bytes(md.read_bytes().replace(b"[TEXT]", b"[IMAGE]", 1))
            out = Path(tmp) / "out.zip"
            done = self.run_tool(str(source), str(out))
            self.assertEqual(done.returncode, 1)
            self.assertIn("results_blocks_mismatch", done.stderr)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["export"])

    def test_it_stops_on_a_directory_that_is_not_one_export(self) -> None:
        files = bundle.make_files((CORPUS_DIR / "ar_baseline.pdf").read_bytes(), "synthetic")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "export"
            source.mkdir()
            self.export(source, files)
            (source / "synthetic_results.md").unlink()
            self.assertEqual(self.run_tool(str(source), str(Path(tmp) / "a.zip")).returncode, 2)
            (source / "synthetic_results.md").write_bytes(files.results_md)
            (source / "second.pdf").write_bytes(files.pdf)
            self.assertEqual(self.run_tool(str(source), str(Path(tmp) / "b.zip")).returncode, 2)


class GeneratorGuardTest(unittest.TestCase):
    def test_the_generator_refuses_a_bundle_its_own_validator_rejects(self) -> None:
        scanned = (CORPUS_DIR / "negative" / "image_only.pdf").read_bytes()
        files = bundle.make_files(scanned, "scanned")
        with self.assertRaises(bundle.BundleError):
            bundle.build_bundle(files)                                  # refused, none expected
        with self.assertRaises(bundle.BundleError):
            bundle.build_bundle(files, expect="not_encrypted")          # refused for another rule
        self.assertEqual(
            bundle.build_bundle(files, expect="every_page_has_extractable_text").verdict.constraints,
            ("every_page_has_extractable_text",))
        clean = bundle.make_files((CORPUS_DIR / "ar_baseline.pdf").read_bytes(), "clean")
        with self.assertRaises(bundle.BundleError):
            bundle.build_bundle(clean, expect="not_encrypted")          # accepted, a refusal expected

    def test_the_corpus_script_keeps_the_lines_another_generator_appended(self) -> None:
        fresh = b"aaa  ar_baseline.pdf\nbbb  negative/x.pdf\n"
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "SHA256SUMS"
            existing.write_text("old  ar_baseline.pdf\nccc  bundles/a.zip\nddd  bundles/m.json\n",
                                encoding="utf-8")
            self.assertEqual(build_ar_corpus.keep_appended_lines(fresh, existing),
                             fresh + b"ccc  bundles/a.zip\nddd  bundles/m.json\n")
            existing.write_text("old  ar_baseline.pdf\n", encoding="utf-8")
            self.assertEqual(build_ar_corpus.keep_appended_lines(fresh, existing), fresh)
            self.assertEqual(build_ar_corpus.keep_appended_lines(fresh, Path(tmp) / "none"), fresh)

    def test_the_bundle_script_leaves_the_corpus_scripts_lines_alone(self) -> None:
        existing = CHECKSUMS.read_bytes()
        rebuilt = build_portal_bundles.checksum_bytes(existing, [("bundles/x.zip", b"x")])
        self.assertTrue(rebuilt.startswith(
            b"".join(f"{d}  {n}\n".encode() for d, n in ORIGINAL_SUMS)))
        self.assertTrue(rebuilt.endswith(f"{sha256(b'x')}  bundles/x.zip\n".encode()))
        self.assertEqual(rebuilt.count(b"bundles/"), 1)

    def test_the_freeze_values_are_the_validators_defaults(self) -> None:
        limits = validate.Limits(member_bytes=1, stamp_audit_bytes=1)
        self.assertEqual((limits.entries, limits.total_bytes, limits.ratio, limits.upload_bytes),
                         (8, 300 * MiB, 100, 250 * MiB))
        self.assertEqual((limits.min_pages, limits.max_pages), (1, 500))
        with self.assertRaises(TypeError):
            validate.Limits()                 # the member bound and the cap are INGEST's to name


if __name__ == "__main__":
    unittest.main()
