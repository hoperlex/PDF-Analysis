"""Offline, isolated LibreOffice import probe for W57b rendered XLSX bytes.

This is a rehearsal tool. A successful import says nothing about corpus custody,
run qualification, API authorization or deployment readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import posixpath
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable


MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
EXPECTED_SHEETS = ("Сводка", "Замечания")
CELL_ADDRESS = re.compile(r"[A-Z]+[1-9][0-9]*\Z")
MAX_WORKBOOK_BYTES = 32 * 1024 * 1024
TIMEOUT_SECONDS = 45


class ProbeRefused(ValueError):
    """The independent import or semantic cell comparison failed."""


@dataclass(frozen=True, slots=True)
class ProbeResult:
    source_sha256: str
    imported_sha256: str
    sheet_names: tuple[str, ...]
    compared_cell_count: int


def _xml(archive: zipfile.ZipFile, part: str) -> ET.Element:
    try:
        return ET.fromstring(archive.read(part))
    except (KeyError, ET.ParseError, ValueError) as error:
        raise ProbeRefused(f"xlsx_invalid_xml:{part}") from error


def _shared_strings(archive: zipfile.ZipFile) -> tuple[str, ...]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return ()
    root = _xml(archive, "xl/sharedStrings.xml")
    return tuple(
        "".join(node.text or "" for node in item.iter(f"{{{MAIN}}}t"))
        for item in root.findall(f"{{{MAIN}}}si")
    )


def _cell(cell: ET.Element, shared_strings: tuple[str, ...]) -> tuple[str, str | Decimal] | None:
    if cell.find(f"{{{MAIN}}}f") is not None:
        raise ProbeRefused("xlsx_formula_present")
    cell_type = cell.get("t", "n")
    if cell_type == "inlineStr":
        inline = cell.find(f"{{{MAIN}}}is")
        if inline is None:
            raise ProbeRefused("xlsx_inline_string_missing")
        value = "".join(node.text or "" for node in inline.iter(f"{{{MAIN}}}t"))
        return ("text", value) if value else None
    raw = cell.findtext(f"{{{MAIN}}}v")
    if raw is None or raw == "":
        return None
    if cell_type == "s":
        try:
            index = int(raw)
            if index < 0:
                raise IndexError(index)
            value = shared_strings[index]
        except (ValueError, IndexError) as error:
            raise ProbeRefused("xlsx_shared_string_invalid") from error
        return ("text", value) if value else None
    if cell_type == "str":
        return ("text", raw)
    if cell_type == "n":
        try:
            number = Decimal(raw)
        except InvalidOperation as error:
            raise ProbeRefused("xlsx_number_invalid") from error
        if not number.is_finite():
            raise ProbeRefused("xlsx_number_invalid")
        return ("number", number)
    if cell_type == "b" and raw in ("0", "1"):
        return ("boolean", raw)
    raise ProbeRefused(f"xlsx_cell_type_unsupported:{cell_type}")


def _workbook_cells(content: bytes) -> tuple[tuple[str, ...], dict[tuple[str, str], tuple[str, str | Decimal]]]:
    if not isinstance(content, bytes) or not content or len(content) > MAX_WORKBOOK_BYTES:
        raise ProbeRefused("xlsx_size_invalid")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            book = _xml(archive, "xl/workbook.xml")
            rels = _xml(archive, "xl/_rels/workbook.xml.rels")
            targets = {
                rel.get("Id"): rel.get("Target")
                for rel in rels.findall(f"{{{PKG_REL}}}Relationship")
            }
            strings = _shared_strings(archive)
            names: list[str] = []
            cells: dict[tuple[str, str], tuple[str, str | Decimal]] = {}
            for sheet in book.findall(f"{{{MAIN}}}sheets/{{{MAIN}}}sheet"):
                name = sheet.get("name")
                target = targets.get(sheet.get(f"{{{DOC_REL}}}id"))
                if not name or not target or name in names:
                    raise ProbeRefused("xlsx_sheet_reference_invalid")
                names.append(name)
                part = posixpath.normpath(
                    target.lstrip("/") if target.startswith("/") else posixpath.join("xl", target)
                )
                if not part.startswith("xl/worksheets/") or ".." in part.split("/"):
                    raise ProbeRefused("xlsx_sheet_target_invalid")
                root = _xml(archive, part)
                for cell in root.findall(f".//{{{MAIN}}}sheetData/{{{MAIN}}}row/{{{MAIN}}}c"):
                    address = cell.get("r")
                    if not address or not CELL_ADDRESS.fullmatch(address):
                        raise ProbeRefused("xlsx_cell_address_invalid")
                    value = _cell(cell, strings)
                    if value is not None:
                        key = (name, address)
                        if key in cells:
                            raise ProbeRefused("xlsx_duplicate_cell")
                        cells[key] = value
            return tuple(names), cells
    except (zipfile.BadZipFile, OSError, RuntimeError) as error:
        raise ProbeRefused("xlsx_archive_invalid") from error


def probe_xlsx(
    content: bytes,
    *,
    soffice: str = "soffice",
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ProbeResult:
    """Roundtrip rendered bytes via a private LibreOffice profile and compare cells."""
    source_sheets, source_cells = _workbook_cells(content)
    if source_sheets != EXPECTED_SHEETS:
        raise ProbeRefused("xlsx_sheet_names_mismatch")
    with tempfile.TemporaryDirectory(prefix="w57b-soffice-") as scratch:
        root = Path(scratch)
        source = root / "source" / "input.xlsx"
        output = root / "output"
        profile = root / "profile"
        runtime = root / "xdg-runtime"
        config = root / "xdg-config"
        cache = root / "xdg-cache"
        probe_home = root / "home"
        source.parent.mkdir()
        output.mkdir()
        profile.mkdir()
        for private_dir in (runtime, config, cache, probe_home):
            private_dir.mkdir(mode=0o700)
        environment = os.environ.copy()
        environment.update({
            "XDG_RUNTIME_DIR": str(runtime),
            "XDG_CONFIG_HOME": str(config),
            "XDG_CACHE_HOME": str(cache),
            "HOME": str(probe_home),
            "SAL_USE_VCLPLUGIN": "svp",
        })
        source.write_bytes(content)
        command = [
            soffice,
            f"-env:UserInstallation={profile.as_uri()}",
            "--headless",
            "--convert-to",
            "xlsx:Calc MS Excel 2007 XML",
            "--outdir",
            str(output),
            str(source),
        ]
        try:
            process = runner(
                command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
                env=environment,
            )
        except FileNotFoundError as error:
            raise ProbeRefused("soffice_missing") from error
        except subprocess.TimeoutExpired as error:
            raise ProbeRefused("soffice_timeout") from error
        if process.returncode != 0:
            detail = " ".join((process.stdout or "", process.stderr or "")).strip()
            detail = " ".join(detail.split())[:240]
            raise ProbeRefused(f"soffice_failed:{process.returncode}:{detail}")
        converted = output / "input.xlsx"
        if not converted.is_file():
            raise ProbeRefused("soffice_output_missing")
        imported = converted.read_bytes()
        imported_sheets, imported_cells = _workbook_cells(imported)
        if imported_sheets != source_sheets:
            raise ProbeRefused("xlsx_sheet_names_mismatch")
        if imported_cells != source_cells:
            for key in sorted(source_cells.keys() | imported_cells.keys()):
                if source_cells.get(key) != imported_cells.get(key):
                    raise ProbeRefused(f"xlsx_cell_mismatch:{key[0]}!{key[1]}")
        return ProbeResult(
            hashlib.sha256(content).hexdigest(),
            hashlib.sha256(imported).hexdigest(),
            source_sheets,
            len(source_cells),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", type=Path, help="local rendered XLSX for offline import rehearsal")
    args = parser.parse_args()
    try:
        result = probe_xlsx(args.xlsx.read_bytes())
    except (OSError, ProbeRefused) as error:
        parser.exit(1, f"probe refused: {error}\n")
    print(json.dumps({
        "source_sha256": result.source_sha256,
        "imported_sha256": result.imported_sha256,
        "sheet_names": result.sheet_names,
        "compared_cell_count": result.compared_cell_count,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
