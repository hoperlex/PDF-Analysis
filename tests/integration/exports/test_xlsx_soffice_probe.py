"""W57b independent import probe: runner failures and an opt-in real roundtrip."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from auditmanager.exports.xlsx import Citation, FindingMember, FindingRow, WorkbookInput, render_xlsx
from scripts.rehearsal.w57b.xlsx_soffice_probe import ProbeRefused, probe_xlsx


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
