"""AR-V3-JUDGE-FIXES-01 finding 2: ``exportRunXlsx`` reads an AR v3 Run's citations through the stage
that certifies them.

The certified citation partitions of an AR v3 beta Run are certified by the succeeded
``ar_v3_citation_review`` stage; a v1/v2 Run's by ``norm_verification``. The workbook's use case
(``exports/xlsx/run_export.py``) is handed the citation reader by the composition root and calls it
with ``run_id``, ``version_uid`` and ``profile_id`` only, so the reader the adapter hands over must
choose the stage from the profile. Before this fix it handed over ``read_verified_citations``
unchanged, whose default stage is ``norm_verification``; its header query (an inner join on that
stage) found nothing for a v3 Run, the use case answered ``required_norm_unavailable`` and the export
was closed for every AR v3 beta Run.

No database: the adapter is driven with a session that only records the bind parameters.
"""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import AR_V3_BETA_PROFILE_ID
from auditmanager.bootstrap.adapters import XlsxExportAdapter
from auditmanager.findings.citation_reader import CitationReadRefused

RUN = "run_01M5B0000000000000000000R1"
VERSION = "ver_01M5B0000000000000000000V1"
V3_PROFILE = str(AR_V3_BETA_PROFILE_ID)
OTHER_PROFILE = "ap_01M5B00000000000000000AP01"


class _Nothing:
    """A result with no row: the reader refuses with ``run_or_v3_profile_unavailable``."""

    def mappings(self) -> "_Nothing":
        return self

    def one_or_none(self) -> None:
        return None


class _RecordingSession:
    def __init__(self) -> None:
        self.parameters: list[dict[str, object]] = []

    def execute(self, statement: object, parameters: dict[str, object]) -> _Nothing:
        self.parameters.append(dict(parameters))
        return _Nothing()


def _captured_reader(monkeypatch: pytest.MonkeyPatch):
    """Drive the adapter's ``export_run_xlsx`` and return the citation reader it hands the use case."""
    captured: dict[str, object] = {}

    def fake_export(session: object, run_id: str, *, authorization: object, read_blob: object,
                    read_citations: object) -> SimpleNamespace:
        captured.update(run_id=run_id, read_citations=read_citations, authorization=authorization)
        return SimpleNamespace(content=b"workbook")

    monkeypatch.setattr("auditmanager.exports.export_run_xlsx", fake_export)

    @contextmanager
    def sessions():
        yield _RecordingSession()

    adapter = XlsxExportAdapter(sessions, blob_store=object())  # type: ignore[arg-type]
    assert adapter.export_run_xlsx(run_id=RUN, principal_id="usr_1") == b"workbook"
    assert captured["run_id"] == RUN
    return captured["read_citations"]


def _stage_bound_for(reader, profile_id: str) -> object:
    session = _RecordingSession()
    with pytest.raises(CitationReadRefused, match="run_or_v3_profile_unavailable"):
        reader(session, run_id=RUN, version_uid=VERSION, profile_id=profile_id)
    (parameters,) = session.parameters
    assert parameters["run_id"] == RUN and parameters["profile_id"] == profile_id
    return parameters["cite_stage_id"]


def test_an_ar_v3_run_is_read_through_the_v3_citation_stage(monkeypatch):
    assert _stage_bound_for(_captured_reader(monkeypatch), V3_PROFILE) == "ar_v3_citation_review"


def test_any_other_profile_is_still_read_through_norm_verification(monkeypatch):
    assert _stage_bound_for(_captured_reader(monkeypatch), OTHER_PROFILE) == "norm_verification"

