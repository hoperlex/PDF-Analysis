"""W57b independent import probe: runner failures and an opt-in real roundtrip."""

from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

from auditmanager.exports.xlsx import Citation, FindingMember, FindingRow, WorkbookInput, render_xlsx
from scripts.rehearsal.w57b.xlsx_soffice_probe import ProbeRefused, _workbook_cells, probe_xlsx


def _render(*, finding_text: str = "=1+1") -> bytes:
    return render_xlsx(
        WorkbookInput(
            project_uid="prj_1",
            version_uid="ver_1",
            run_id="run_1",
            profile_id="ar_v3",
            snapshot_key="ns_1",
            attribution="recorded",
            findings=(
                FindingRow(
                    finding_uid="finding_1",
                    sheet_page="АР-1 / 3",
                    category="fire_safety",
                    finding_text=finding_text,
                    recommendation="+SUM(1,2)",
                    proposed_severity="economic",
                    citations=(Citation("СП 1", "п. 2", "Первая цитата\nВторая строка"),),
                    members=(FindingMember("АР-2 / 4", "повтор"),),
                ),
            ),
        )
    ).content


def _copy_runner(
    command: list[str], *, capture_output: bool, text: bool, timeout: int,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    assert capture_output is True and text is True and timeout <= 45
    assert command[1].startswith("-env:UserInstallation=file:")
    assert command[2:5] == ["--headless", "--convert-to", "xlsx:Calc MS Excel 2007 XML"]
    assert command[5] == "--outdir"
    source = Path(command[-1])
    assert source.name == "input.xlsx"
    output = Path(command[6]) / "input.xlsx"
    assert source.parent != output.parent
    for key in ("XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "HOME"):
        assert Path(env[key]).is_dir()
        assert Path(env[key]).stat().st_mode & 0o777 == 0o700
        assert Path(env[key]).parent == source.parent.parent
    assert env["SAL_USE_VCLPLUGIN"] == "svp"
    shutil.copyfile(source, output)
    return subprocess.CompletedProcess(command, 0, "", "")


def test_probe_preserves_every_nonempty_cell_and_private_profile() -> None:
    content = _render()
    result = probe_xlsx(content, runner=_copy_runner)
    assert result.sheet_names == ("Сводка", "Замечания")
    assert result.compared_cell_count > 35
    assert result.source_sha256 == hashlib.sha256(content).hexdigest()
    assert result.imported_sha256 == result.source_sha256


def test_probe_refuses_changed_cell_even_when_import_exits_zero() -> None:
    def changed_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        result = _copy_runner(command, **kwargs)
        (Path(command[6]) / "input.xlsx").write_bytes(_render(finding_text="changed"))
        return result

    with pytest.raises(ProbeRefused, match=r"xlsx_cell_mismatch:Замечания!D2"):
        probe_xlsx(_render(), runner=changed_runner)


def test_probe_refuses_missing_output_nonzero_and_timeout() -> None:
    def no_output(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "", "")

    def failed(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 8, "", "bad filter")

    def timed_out(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout=45)

    for runner, message in (
        (no_output, "soffice_output_missing"),
        (failed, "soffice_failed:8"),
        (timed_out, "soffice_timeout"),
    ):
        with pytest.raises(ProbeRefused, match=message):
            probe_xlsx(_render(), runner=runner)


def test_probe_refuses_malformed_input_before_spawning() -> None:
    def unexpected_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("must reject before LibreOffice")

    with pytest.raises(ProbeRefused, match="xlsx_archive_invalid"):
        probe_xlsx(b"not an xlsx", runner=unexpected_runner)


@pytest.mark.skipif(os.getenv("W57B_RUN_SOFFICE") != "1", reason="manual after host gate")
def test_real_soffice_roundtrip() -> None:
    result = probe_xlsx(_render())
    assert result.sheet_names == ("Сводка", "Замечания")
    assert result.compared_cell_count > 35


_CATEGORIES = (
    "internal_contradiction", "explicit_placeholder", "dimensions", "layout", "facade", "roof",
    "documentation", "evacuation", "fire_safety", "accessibility", "insulation", "sound",
)
_SEVERITIES = ("critical", "economic", "operational", "recommendation", "check_adjacent")
_VERDICTS = ("pending", "accepted", "rejected", "needs_manual_review")


def _column_number(letters: str) -> int:
    number = 0
    for letter in letters:
        number = number * 26 + ord(letter) - 64
    return number


@pytest.mark.skipif(
    os.getenv("W57B_RUN_SOFFICE") != "1" or shutil.which("soffice") is None,
    reason="manual: needs soffice on PATH and W57B_RUN_SOFFICE=1",
)
def test_real_soffice_csv_shows_every_label_cell_by_cell(tmp_path: Path) -> None:
    """`XLSX-RU-LABELS-01`: LibreOffice reads every sheet back as the cells the XML holds.

    Every category, severity and verdict is present, so each Russian label is a cell the
    application had to open as text. The comparison is independent of the writer: the
    expected grid comes from the probe's own XML reader, the actual grid from the CSV
    LibreOffice writes for each sheet (its own profile under ``tmp_path``).
    """
    findings = tuple(
        FindingRow(
            finding_uid=f"finding_{index:02d}", sheet_page=f"АР-{index} / {index}",
            category=category, finding_text=f"Замечание {index}",
            decided_severity=_SEVERITIES[index % 5] if index % 2 else None,
            proposed_severity=_SEVERITIES[(index + 1) % 5],
            expert_decision=_VERDICTS[index % 4] if index % 2 == 0 else "accepted",
        )
        for index, category in enumerate(_CATEGORIES)
    )
    content = render_xlsx(
        WorkbookInput("prj_1", "ver_1", "run_1", "ar_v3", "ns_1", "recorded", findings)
    ).content
    source = tmp_path / "in" / "labels.xlsx"
    source.parent.mkdir()
    source.write_bytes(content)
    out, profile, runtime, home = (tmp_path / name for name in ("out", "profile", "run", "home"))
    for directory in (out, profile):
        directory.mkdir()
    for directory in (runtime, home):
        directory.mkdir(mode=0o700)
    environment = {
        **os.environ, "XDG_RUNTIME_DIR": str(runtime), "HOME": str(home),
        "SAL_USE_VCLPLUGIN": "svp",
    }
    done = subprocess.run(
        [
            "soffice", f"-env:UserInstallation={profile.as_uri()}", "--headless",
            "--convert-to", "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,-1",
            "--outdir", str(out), str(source),
        ],
        capture_output=True, text=True, timeout=120, env=environment,
    )
    assert done.returncode == 0, done.stderr
    names, expected = _workbook_cells(content)
    compared = 0
    for name in names:
        (path,) = out.glob(f"labels-{name}.csv")
        grid = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8"), newline="")))
        wanted = {}
        for (sheet, address), (kind, value) in expected.items():
            if sheet != name:
                continue
            match = re.fullmatch(r"([A-Z]+)([0-9]+)", address)
            assert match is not None
            shown = str(int(value)) if isinstance(value, Decimal) else value
            wanted[(int(match.group(2)), _column_number(match.group(1)))] = shown
        for (row, column), shown in wanted.items():
            assert grid[row - 1][column - 1] == shown, (name, row, column)
            compared += 1
        # ... and nothing else is filled: no formula result, no stray cell.
        filled = {
            (row, column) for row, cells in enumerate(grid, start=1)
            for column, value in enumerate(cells, start=1) if value != ""
        }
        assert filled == set(wanted), (name, sorted(filled ^ set(wanted))[:5])
    assert compared > 120  # 143 non-empty cells for twelve findings
