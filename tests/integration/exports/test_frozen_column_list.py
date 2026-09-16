"""The seventeen columns, and the constants nothing was checking.

The `W10-FND` mutation sweep swapped columns 7 and 8 of
``auditmanager.exports.serializer.COLUMNS`` and **all 302 tests stayed green**. The reason
is the wave-9 mistake, sitting in the export contract test:

    assert header == list(COLUMNS)

Both sides move together. Worse, ``_parse`` builds each row dict by zipping the file's own
header against its cells, so every later assertion — ``row["finding_uid"]``,
``row["evidence_quote"]`` — follows the mutated header and keeps passing. The 17 frozen
column names of ``OD-11`` had no literal pin anywhere in the Python tree.

Two more constants reddened nothing:

* **the header is written even when there are no rows.** ``render_csv``'s docstring says an
  empty file with no header would be indistinguishable from a failure to produce one.
  Suppressing the header for an empty row list reddened nothing.
* **``SORT_KEY``** — declared, exported from ``auditmanager.exports``, and read by nothing
  in ``src/``, ``tests/`` or ``web/``. Replacing it with ``("finding_observation_id",)``
  reddened nothing.

Authorities used here, none of them the module under test:

* ``docs/program/P02_SEAMS.md`` §6 — the frozen column table and the sort key;
* ``web/src/shared/api/csv-columns.ts`` — the frontend's independent copy of the same list,
  which exists so "a contract test can prove the frontend's idea of the column list has not
  drifted from the seam document" and which, until this file, nothing compared with Python.
"""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.orm import Session

from auditmanager.exports import BOM, COLUMNS, SORT_KEY, export_run_csv
from auditmanager.exports.query import export_rows

_REPO = Path(__file__).resolve().parents[3]
_SEAMS = _REPO / "docs" / "program" / "P02_SEAMS.md"
_WEB_COLUMNS = _REPO / "web" / "src" / "shared" / "api" / "csv-columns.ts"

#: The frozen list, written out. `OD-11` / `P02_SEAMS.md` §6, columns 1 to 17 in order.
#: Deliberately **not** `list(COLUMNS)`: the assertion this replaces was phrased against the
#: module's own constant and survived columns 7 and 8 being swapped.
FROZEN_COLUMNS = (
    "project_uid",
    "document_uid",
    "version_uid",
    "run_id",
    "run_state",
    "provider_mode",
    "finding_uid",
    "finding_observation_id",
    "category",
    "finding_text",
    "recommendation_text",
    "evidence_page",
    "evidence_quote",
    "current_verdict",
    "latest_comment",
    "latest_decision_id",
    "decision_recorded_at",
)

#: The exact first line of the file, after the BOM and before the first CRLF. No column
#: name needs RFC 4180 quoting, so the header is the names joined by commas.
FROZEN_HEADER_LINE = (
    "project_uid,document_uid,version_uid,run_id,run_state,provider_mode,"
    "finding_uid,finding_observation_id,category,finding_text,recommendation_text,"
    "evidence_page,evidence_quote,current_verdict,latest_comment,latest_decision_id,"
    "decision_recorded_at"
)

#: `P02_SEAMS.md` §6, "Sort key".
FROZEN_SORT_KEY = ("finding_uid", "finding_observation_id", "evidence_ordinal")


def _seam_columns() -> tuple[str, ...]:
    """Columns 1-17 of the table in `P02_SEAMS.md` §6, in the order it lists them."""
    section = _SEAMS.read_text(encoding="utf-8").split("## 6. The CSV column contract")[1]
    found = re.findall(r"^\|\s*(\d+)\s*\|\s*`([a-z_]+)`\s*\|", section, re.M)
    return tuple(name for _, name in sorted(found, key=lambda pair: int(pair[0])))


def _web_columns() -> tuple[str, ...]:
    body = _WEB_COLUMNS.read_text(encoding="utf-8")
    block = re.search(r"export const CSV_COLUMNS = \[(.*?)\]", body, re.S)
    assert block is not None, "web/src/shared/api/csv-columns.ts no longer declares CSV_COLUMNS"
    return tuple(re.findall(r"'([a-z_]+)'", block.group(1)))


class TestTheColumnListIsPinnedToSomethingOutsideTheModule:
    def test_the_seam_document_lists_these_seventeen_in_this_order(self) -> None:
        assert _seam_columns() == FROZEN_COLUMNS
        assert len(FROZEN_COLUMNS) == 17

    def test_the_module_constant_matches_the_frozen_list_in_order(self) -> None:
        assert tuple(COLUMNS) == FROZEN_COLUMNS, (
            "COLUMNS no longer matches OD-11 / P02_SEAMS.md §6, in order"
        )

    def test_the_frontend_and_the_backend_declare_the_same_list(self) -> None:
        assert _web_columns() == FROZEN_COLUMNS
        assert _web_columns() == tuple(COLUMNS)

    def test_the_exported_header_line_is_the_frozen_one_byte_for_byte(
        self, session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
    ) -> None:
        """Against a real run's real bytes, and against a literal string.

        Not `list(COLUMNS)`, and not a dict built by zipping the file's own header with
        its own cells: both of those follow a reordered column list without complaint.
        """
        from auditmanager.runs import execute_run, start_audit_run

        started = start_audit_run(
            session,
            version_uid=seeded.version_uid,
            analysis_profile_id=seeded.analysis_profile_id,
            prompt_bundle_id=seeded.prompt_bundle_id,
            provider_mode="recorded",
            idempotency_key=new_key("frozen-header"),
        )
        execute_run(
            session,
            started.run_id,
            blob_store=blob_store,
            adapter=recorded_adapter,
            provider_config=provider_config,
        )
        content = export_run_csv(session, started.run_id).content

        assert content[:3] == b"\xef\xbb\xbf"
        first_line, _, _ = content[3:].decode("utf-8").partition("\r\n")
        assert first_line == FROZEN_HEADER_LINE


class TestTheHeaderIsWrittenEvenWhenThereAreNoRows:
    """``render_csv`` on an empty row list.

    A run over a clean document publishes nothing and is still ``published``; an empty file
    with no header would be indistinguishable from a failure to produce one.
    """

    def test_an_empty_export_is_the_bom_the_header_and_one_crlf(self) -> None:
        from auditmanager.exports.serializer import render_csv

        content = render_csv(())
        assert content == b"\xef\xbb\xbf" + FROZEN_HEADER_LINE.encode("utf-8") + b"\r\n"

    def test_the_bom_constant_is_still_the_utf8_bom(self) -> None:
        assert BOM == b"\xef\xbb\xbf"


class TestTheSortKeyConstantDescribesTheOrderTheQueryActuallyProduces:
    """``SORT_KEY`` has no consumer, so only a cross-check can defend it.

    The literal comes from `P02_SEAMS.md` §6; the behavioural half asserts the rows a real
    run produces are ascending on the key the constant names, which reddens if the constant
    names a key the query does not order by.
    """

    def test_it_is_the_frozen_three_part_key(self) -> None:
        assert tuple(SORT_KEY) == FROZEN_SORT_KEY

    def test_the_rows_of_a_real_run_are_ascending_on_it(
        self, session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
    ) -> None:
        from auditmanager.runs import execute_run, start_audit_run

        started = start_audit_run(
            session,
            version_uid=seeded.version_uid,
            analysis_profile_id=seeded.analysis_profile_id,
            prompt_bundle_id=seeded.prompt_bundle_id,
            provider_mode="recorded",
            idempotency_key=new_key("sort-key"),
        )
        execute_run(
            session,
            started.run_id,
            blob_store=blob_store,
            adapter=recorded_adapter,
            provider_config=provider_config,
        )
        rows = export_rows(session, started.run_id)
        assert rows, "the run published nothing; there is no order to check"

        keys = [tuple(getattr(row, name) for name in SORT_KEY) for row in rows]
        assert keys == sorted(keys), (
            "export_rows is not ascending on the key SORT_KEY names"
        )
        assert len(set(keys)) == len(keys), "the key does not distinguish the rows"
