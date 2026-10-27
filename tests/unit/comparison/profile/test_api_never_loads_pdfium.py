"""The API process never loads PDFium for a tile (`CMP-PROFILE-01`, ADR-0025 decision 9 and its addendum).

Two proofs, one static and one dynamic, so that either can fail alone:

* **static**: no module of ``comparison/profile`` outside its ``child/`` directory imports ``pypdfium2``,
  ``pdfplumber`` or ``pypdf`` (a function-level import is an import);
* **dynamic**: in a fresh interpreter that imports what the API imports (the composition root and the router),
  builds the tile renderer and serves a real tile of the A1 plan of VS-1 -- the child renders it -- none of
  ``pypdfium2``, ``pdfplumber``, ``pypdf`` is in ``sys.modules`` afterwards, and the tile is a PNG.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROFILE = ROOT / "src" / "auditmanager" / "comparison" / "profile"
FORBIDDEN = {"pypdfium2", "pdfplumber", "pypdf"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_no_module_of_the_api_side_imports_a_pdf_library() -> None:
    api_side = sorted(path for path in PROFILE.glob("*.py"))
    assert {path.name for path in api_side} >= {"tiles.py", "reader.py", "runner.py", "source.py", "builder.py"}
    offenders = {path.name: sorted(_imports(path) & FORBIDDEN) for path in api_side if _imports(path) & FORBIDDEN}
    assert offenders == {}
    # The scan sees what it should: the child programs are where the libraries are used.
    assert any(_imports(path) & FORBIDDEN for path in (PROFILE / "child").glob("*.py"))


def test_a_tile_served_by_the_api_side_code_loads_no_pdf_library_into_the_process(fixtures_dir: Path, tmp_path: Path) -> None:
    pdf = fixtures_dir / "vs1" / "v1.pdf"
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    script = tmp_path / "serve_a_tile.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import json, sys
            sys.path.insert(0, {str(ROOT / "src")!r})
            import auditmanager.bootstrap.adapters, auditmanager.bootstrap.composition, auditmanager.api.routers
            from auditmanager.comparison.public import TileRenderer
            from auditmanager.comparison.profile.source import SourceVersion
            from auditmanager.storage.public import derive_blob_id

            PDF = {str(pdf)!r}
            DIGEST = {digest!r}
            SIZE = {pdf.stat().st_size}

            class Store:
                def open_stream(self, blob_id, *, expected_sha256, expected_size, **_):
                    assert expected_sha256 == DIGEST and expected_size == SIZE
                    with open(PDF, "rb") as handle:
                        yield handle.read()

            source = SourceVersion("ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", 6, DIGEST, SIZE,
                                   str(derive_blob_id(sha256=DIGEST, size=SIZE)))
            png = TileRenderer().render(Store(), source, page_number=5, level=1, column=2, row=1)
            print(json.dumps({{"png": png[:8].hex(), "size": len(png),
                              "loaded": sorted(m for m in ("pypdfium2", "pdfplumber", "pypdf") if m in sys.modules)}}))
            """
        ),
        encoding="utf-8",
    )
    done = subprocess.run([sys.executable, "-I", str(script)], capture_output=True, text=True, cwd="/", timeout=120)
    assert done.returncode == 0, done.stderr[-2000:]
    answer = json.loads(done.stdout.strip().splitlines()[-1])
    assert answer["png"] == "89504e470d0a1a0a" and answer["size"] > 500
    assert answer["loaded"] == []
