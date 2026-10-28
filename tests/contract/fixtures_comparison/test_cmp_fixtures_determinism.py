"""The comparison corpus is reproduced byte for byte, and the writer change leaves the AR corpus alone.

Three independent claims, each of which can fail on its own:

*   in one process, building twice gives the same bytes (no clock, no PRNG, no set order);
*   in fresh interpreters with different `PYTHONHASHSEED`, the digests agree with each other and with
    the committed `SHA256SUMS` (what is stable only inside one process would show here);
*   the committed files are exactly what a fresh build writes, and nothing else sits beside them.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pypdf
import pytest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
TOOLS_DIR = REPO_ROOT / "tools" / "fixtures"
CORPUS = REPO_ROOT / "fixtures" / "comparison"
BUILD = TOOLS_DIR / "comparison" / "build.py"
for path in (str(TOOLS_DIR), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import cmp_fixtures_support as support  # noqa: E402
from comparison import build  # noqa: E402

#: Hand-written files in the corpus directory; everything else is generator output and is digested.
HAND_WRITTEN = {"README.md", ".gitattributes"}


@pytest.fixture(scope="module")
def fresh() -> dict[str, bytes]:
    return build.build_all()


def test_building_twice_in_one_process_gives_identical_bytes(fresh) -> None:
    assert build.build_all() == fresh


def test_the_committed_corpus_is_what_a_fresh_build_writes(fresh) -> None:
    committed = support.load_files()
    assert set(committed) - HAND_WRITTEN == set(fresh), "a generated file is missing, or an unknown file sits in the corpus"
    for name, data in fresh.items():
        assert committed[name] == data, f"{name} differs from a fresh build"


def test_sha256sums_digests_every_generated_file_and_nothing_else(fresh) -> None:
    recorded = {}
    for line in fresh["SHA256SUMS"].decode("utf-8").splitlines():
        digest, name = line.split("  ", 1)
        recorded[name] = digest
    assert set(recorded) == set(fresh) - {"SHA256SUMS"}
    import hashlib

    for name, digest in recorded.items():
        assert hashlib.sha256(fresh[name]).hexdigest() == digest


def test_fresh_interpreters_with_different_hash_seeds_agree_with_the_committed_sums() -> None:
    committed = (CORPUS / "SHA256SUMS").read_text(encoding="utf-8")
    for seed in ("0", "12345"):
        completed = subprocess.run(
            [sys.executable, "-c",
             "import sys;"
             f"sys.path.insert(0, {str(TOOLS_DIR)!r});"
             "from comparison import build;"
             "sys.stdout.write(build.build_all()['SHA256SUMS'].decode('utf-8'))"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
            env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": seed},
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout == committed, f"PYTHONHASHSEED={seed} changed a byte"


def test_the_generator_check_mode_exits_zero() -> None:
    completed = subprocess.run([sys.executable, str(BUILD), "--check"], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_the_check_mode_fails_when_a_committed_file_is_altered(tmp_path: Path, monkeypatch) -> None:
    """The guard on the previous test can fail: point the check at a corrupted copy."""
    import shutil

    copy = tmp_path / "comparison"
    shutil.copytree(CORPUS, copy)
    victim = copy / "sp1" / "new_r2.pdf"
    victim.write_bytes(victim.read_bytes()[:-8] + b"tampered")
    monkeypatch.setattr(build, "OUT_DIR", copy)
    assert build.main(["--check"]) == 1


def test_the_pdfs_stay_under_two_megabytes_in_total() -> None:
    total = sum(p.stat().st_size for p in CORPUS.rglob("*.pdf"))
    assert 0 < total < 2_000_000, total


def test_the_size_budget_is_enforced_by_the_build(monkeypatch) -> None:
    monkeypatch.setattr(build, "PDF_BUDGET_BYTES", 1000)
    with pytest.raises(build.BuildError, match="budget"):
        build.build_all()


def test_every_pdf_carries_only_its_authored_creation_date() -> None:
    """No wall clock: the creation date is derived from the authored revision date."""
    for name, data in support.load_files().items():
        if not name.endswith(".pdf"):
            continue
        metadata = pypdf.PdfReader(__import__("io").BytesIO(data)).metadata
        match = re.fullmatch(r"D:(2026)(\d\d)(\d\d)000000Z", str(metadata["/CreationDate"]))
        assert match, f"{name}: {metadata['/CreationDate']!r}"
        assert str(metadata["/ModDate"]) == str(metadata["/CreationDate"])


def test_the_readme_names_the_one_regeneration_command() -> None:
    text = (CORPUS / "README.md").read_text(encoding="utf-8")
    assert "python3 tools/fixtures/comparison/build.py" in text
    assert "--check" in text
    assert "realistic_a1.py" in text


# -- the writer extension is additive ---------------------------------------------------


def test_the_default_page_dictionary_is_the_one_the_ar_builders_write() -> None:
    from ar_corpus import document, pdfwrite
    from ar_corpus.pdfwrite import Name, Ref

    old = {
        "Type": Name("Page"),
        "Parent": Ref(2),
        "MediaBox": [0, 0, document.PAGE_WIDTH, document.PAGE_HEIGHT],
        "Resources": {"Font": {document.FONT_RESOURCE: Ref(3)}},
        "Contents": Ref(9),
    }
    new = pdfwrite.page_dictionary(
        Ref(2), [0, 0, document.PAGE_WIDTH, document.PAGE_HEIGHT],
        {"Font": {document.FONT_RESOURCE: Ref(3)}}, Ref(9),
    )
    assert pdfwrite.serialize_value(new) == pdfwrite.serialize_value(old)


def test_each_extension_is_off_unless_asked_for() -> None:
    from ar_corpus import pdfwrite
    from ar_corpus.pdfwrite import Ref

    plain = pdfwrite.page_dictionary(Ref(2), [0, 0, 100, 100], {}, Ref(4))
    assert not {"CropBox", "Rotate", "Annots"} & set(plain)
    with_all = pdfwrite.page_dictionary(
        Ref(2), [0, 0, 100, 100], {}, Ref(4), crop_box=[1, 1, 99, 99], rotate=90, annots=[Ref(5)])
    assert {"CropBox", "Rotate", "Annots"} <= set(with_all)
    with pytest.raises(ValueError):
        pdfwrite.page_dictionary(Ref(2), [0, 0, 100, 100], {}, Ref(4), rotate=45)


def test_the_ar_builders_do_not_call_the_new_writer_functions() -> None:
    """The new functions cannot change AR bytes if nothing in the AR path calls them."""
    from ar_corpus import pdfwrite

    new_names = {
        "page_dictionary", "add_text_annotation", "add_square_annotation", "add_ocg", "ocg_properties",
        "layer_begin", "layer_end", "stroke_line_op", "stroke_rect_op", "stroke_circle_op",
        "add_hatch_pattern", "pattern_fill_op", "hatch_segments", "hatch_lines", "clip_rect_op", "stroke_text_op",
    }
    assert all(hasattr(pdfwrite, name) for name in new_names)
    for module in ("document", "negatives", "content", "envelope"):
        source = (TOOLS_DIR / "ar_corpus" / f"{module}.py").read_text(encoding="utf-8")
        for name in new_names:
            assert f"pdfwrite.{name}" not in source, f"{module}.py calls pdfwrite.{name}"
    for script in ("build_ar_corpus.py", "build_ar_specification.py"):
        source = (TOOLS_DIR / script).read_text(encoding="utf-8")
        for name in new_names:
            assert f"pdfwrite.{name}" not in source, f"{script} calls pdfwrite.{name}"


def test_the_ar_corpus_check_still_passes_with_the_extended_writer() -> None:
    completed = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "build_ar_corpus.py"), "--check"],
        capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_key_json_is_stable_text() -> None:
    for name in ("vs1/answer_key.json", "sp1/answer_key.json"):
        raw = (CORPUS / name).read_text(encoding="utf-8")
        assert raw.endswith("\n")
        assert json.dumps(json.loads(raw), ensure_ascii=False, indent=2) + "\n" == raw
