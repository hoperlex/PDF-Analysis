"""`W11-FIX`. Which name does the system actually serve for the CSV download?

Before this, the tree gave three answers and only one of them was true.

* ``exports/service.py`` defined ``_FILENAME_TEMPLATE = "audit_run_{run_id}.csv"`` and a
  ``CsvExport.filename`` property over it. **Nothing read either.** Not the router, not
  the frontend, not a test. It was dead, and it was the first answer a reader looking
  for the download name would find, because it is the one that sits on the value object
  the export produces.
* ``api/routers/export.py:_disposition`` emits ``attachment; filename="{run_id}.csv"``.
  This is the real one: it is the bytes that reach the browser.
* ``web/src/shared/api/csv-columns.ts:csvFileName`` suggests ``{runId}-findings.csv``
  and says in its own docstring that the server's header wins if it sends one.

The last two differing is **permitted and is not a defect**. The frozen
``web/openapi/openapi.json`` declares the ``Content-Disposition`` on ``exportRunCsv``'s
200 as "presentation only and is never an identity" and pins no value -- no ``enum``, no
``pattern``, no ``example``. Reconciling them would be inventing a contract nobody wrote.
The defect was only the dead property reading as the source of truth, so only that was
removed.

These tests are the guard against it coming back, and against a fourth spelling being
added somewhere new. The bytes on the wire are asserted separately and against a real
run, by ``tests/integration/api/test_no_internal_identifiers.py``'s
``test_an_export_disposition_names_only_the_opaque_run_identity``; this file asserts that
that assertion is about the *only* place a download name is spelled.

No database is needed here: every assertion is about the shape of the source tree and of
a value object, which is precisely the kind of claim that otherwise lives in a comment.
"""

from __future__ import annotations

from pathlib import Path

from auditmanager.exports import CsvExport

SRC = Path(__file__).resolve().parents[3] / "src/auditmanager"

#: The template the dead property used, as a literal. Not imported -- it no longer
#: exists, and a test that imported it could not fail by it coming back.
DEAD_TEMPLATE = "audit_run_{run_id}.csv"

#: The name the system serves, as a literal, in the form the router writes it.
SERVED_DISPOSITION = 'attachment; filename="{run_id}.csv"'


class TestTheExportValueObjectNamesNoFile:
    """A value computed from canonical data has no business naming a download."""

    def test_csv_export_exposes_no_download_name(self) -> None:
        """Restoring the property reddens this. That is the whole guard.

        Every plausible spelling is checked, not just the one that was there: the defect
        is "the value object answers the filename question", and it would be the same
        defect under ``file_name`` or ``download_name``.
        """
        for spelling in ("filename", "file_name", "download_name", "attachment_name"):
            assert not hasattr(CsvExport, spelling), (
                f"CsvExport exposes {spelling!r}. The download name is served by "
                "`api/routers/export.py:_disposition` and by nothing else; a name on "
                "the value object reads as the source of truth while being unread."
            )

    def test_the_sibling_property_that_is_read_is_still_there(self) -> None:
        """Otherwise the test above would pass on a class stripped by accident.

        ``byte_size`` sits on the same class and *is* read --
        ``tests/integration/runs/test_corpus_measurement.py`` prints and asserts it --
        which is exactly why the dead one beside it was easy to miss.
        """
        export = CsvExport(run_id="run_x", run_state="published", content=b"abcde")
        assert export.byte_size == 5


class TestOnlyOnePlaceInTheSourceSpellsADownloadName:
    def test_the_dead_template_is_gone_from_the_whole_source_tree(self) -> None:
        offenders = [
            str(path.relative_to(SRC.parents[1]))
            for path in sorted(SRC.rglob("*.py"))
            if DEAD_TEMPLATE in path.read_text(encoding="utf-8")
        ]
        assert not offenders, (
            f"{offenders!r} spell {DEAD_TEMPLATE!r}, a download name the system has "
            "never served. It was dead when it was removed; a reader who finds it "
            "again will reasonably believe it is what the browser receives."
        )

    def test_the_router_is_the_only_source_file_that_builds_an_attachment_name(
        self,
    ) -> None:
        """Pins the answer to "which name does the system serve" to one file.

        ``attachment;`` is the token that makes a string a download name. If a second
        file starts emitting one, this reddens and the next reader is told where to
        look rather than having to find out which of two is live.
        """
        spellers = sorted(
            str(path.relative_to(SRC.parents[1]))
            for path in SRC.rglob("*.py")
            if "attachment;" in path.read_text(encoding="utf-8")
        )
        assert spellers == ["src/auditmanager/api/routers/export.py"], (
            f"{spellers!r} build an attachment name. Exactly one should: the download "
            "name is a transport concern and the transport is the router."
        )

    def test_that_one_file_serves_the_run_identity_and_a_suffix(self) -> None:
        """The literal, read out of the router's own bytes.

        Asserted as text rather than by calling ``_disposition`` so that this file can
        state the served name without a database, and stated as a literal so that it
        cannot move with the code it describes. The behaviour over a real run is
        asserted by `tests/integration/api/test_no_internal_identifiers.py`.
        """
        router = (SRC / "api/routers/export.py").read_text(encoding="utf-8")
        assert SERVED_DISPOSITION in router, (
            f"`api/routers/export.py` no longer builds {SERVED_DISPOSITION!r}; the one "
            "place that names the download has changed what it names"
        )
