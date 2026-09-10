"""Synchronous, deterministic server-side CSV export — ``OD-11`` / P02 §6.

    from auditmanager.exports import export_run_csv

    export = export_run_csv(session, run_id)
    export.content       # bytes: UTF-8 with a BOM, CRLF, RFC 4180
    export.content_type  # "text/csv; charset=utf-8"

Seventeen frozen columns, one row per evidence item, sorted by
``(finding_uid, finding_observation_id, evidence_ordinal)``. Two exports of an unchanged
run are byte-identical.

**Nothing is created by an export.** No export aggregate, no table, no ``export_id``, no
``exported_at``, no polling. The export is computed from canonical data and is not itself
canonical data.

The refusal is stated by the contract's own ``terminal_semantics.publishes_result`` flag
rather than by a hand-written state list: ``published`` and ``partial`` export, with the
degraded state visible in column 5; a non-terminal run and the terminal ``failed`` are
refused with ``state_transition_not_allowed``. PC-01 never emits
``partial_result_not_publishable``.
"""

from auditmanager.exports.policy import (
    assert_exportable,
    exportable_states,
    publishes_result,
    publishes_result_by_state,
)
from auditmanager.exports.query import ExportRow, RunHeader, export_rows, run_header
from auditmanager.exports.serializer import (
    BOM,
    COLUMNS,
    CONTENT_TYPE,
    SORT_KEY,
    render_csv,
    row_values,
)
from auditmanager.exports.service import CsvExport, export_run_csv

__all__ = [
    "BOM",
    "COLUMNS",
    "CONTENT_TYPE",
    "SORT_KEY",
    "CsvExport",
    "ExportRow",
    "RunHeader",
    "assert_exportable",
    "export_rows",
    "export_run_csv",
    "exportable_states",
    "publishes_result",
    "publishes_result_by_state",
    "render_csv",
    "row_values",
    "run_header",
]
