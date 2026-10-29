"""The document a PDF is written from (`CMP-VC-REPORT-01`): the client view or the analytic ``report_v2`` with the label, the recall line and the
cipher. It is plain JSON, stored as the report's ``report_text`` artifact: «Пересобрать PDF» reads it back and writes the same PDF again with no
model call.

The **recall line** (ADR-0025 decision 20, plan ``R3-02``) is «изменённых листов N, описано K, отброшено проверкой D»: N the sheets the summary
lists (the changed ones), K those with a description (a sheet whose only line is the engine's own status is not described), D what the program's
checks dropped (the points of the client report; the rejected claims and the dropped references of the analytic one).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.comparison.report import analytic, client
from auditmanager.comparison.report.model import RECORDED_LABEL, UNCONFIRMED_LABEL

__all__ = ["analytic_document", "client_document", "document_facts", "recall_line", "sheet_counts"]

_ENGINE_LINE: Final = re.compile(r"^Сравнение:")


def recall_line(sheets: int, described: int, dropped: int) -> str:
    return f"изменённых листов {sheets}, описано {described}, отброшено проверкой {dropped}"


def sheet_counts(manifest: Mapping[str, Any], registry: Mapping[str, Any]) -> tuple[int, int]:
    """``(N, K)``: the sheets the summary lists, and those of them that carry a description (a fact other than a gap and the engine's own line)."""
    listed = sum(len(t["sheets"]) for t in manifest["transitions"])
    described = {
        f["sheet_id"] for f in registry["facts"]
        if f.get("sheet_id") and f["kind"] != "gap" and not _ENGINE_LINE.match(f["text"])
    }
    return listed, len(described)


def _period(manifest: Mapping[str, Any]) -> str:
    first, last = manifest["transitions"][0], manifest["transitions"][-1]
    return "–".join(x for x in (_date(first.get("from_date")), _date(last.get("to_date"))) if x)


def _date(iso: str | None) -> str:
    if not iso:
        return ""
    year, month, day = iso.split("-")
    return f"{day}.{month}.{year}"


def _base(kind: str, code: str, recall: str, recorded: bool) -> dict[str, Any]:
    return {
        "kind": kind, "label": UNCONFIRMED_LABEL, "recall": recall, "recorded_label": RECORDED_LABEL if recorded else None, "code": code,
    }


def client_document(
    *, manifest: Mapping[str, Any], registry: Mapping[str, Any], stored: Mapping[str, Mapping[str, Any] | None], code: str, object_name: str,
    dropped: int, recorded: bool, incomplete: Sequence[str] = (),
) -> dict[str, Any]:
    """The customer's table: one row per transition in the order of the file; ``stored`` is each transition's stored result by identity
    (``None`` for the confirmed absence of changes)."""
    rows = [client.row_of(t, stored.get(t["transition_id"])) for t in manifest["transitions"]]
    first, last = manifest["transitions"][0], manifest["transitions"][-1]
    sheets, described = sheet_counts(manifest, registry)
    document = _base("client", code, recall_line(sheets, described, dropped), recorded)
    document["view"] = {
        "title": "Изменения проектных решений", "object": object_name, "code": code, "section": "",
        "versions": f"{first['from_version']}–{last['to_version']}", "period": _period(manifest), "rows": rows,
    }
    if incomplete:
        document["incomplete"] = list(incomplete)
    return document


def analytic_document(
    *, manifest: Mapping[str, Any], registry: Mapping[str, Any], report: Mapping[str, Any], code: str, dropped: int, recorded: bool,
    analysed_at: str, sha256: str,
) -> dict[str, Any]:
    sheets, described = sheet_counts(manifest, registry)
    document = _base("analytic", code, recall_line(sheets, described, dropped), recorded)
    document.update({
        "report": dict(report), "distribution": analytic.distribution(dict(report)), "analysed_at": analysed_at, "sha256": sha256,
    })
    return document


def document_facts(document: Mapping[str, Any]) -> tuple[list[str], bool]:
    """The transition labels the PDF must show and whether it is the client kind (what ``check_pdf`` is asked)."""
    if document["kind"] == "client":
        return [r["label"] for r in document["view"]["rows"]], True
    return [f"{t['from_version']}→{t['to_version']}" for t in document["report"]["transitions"]], False
