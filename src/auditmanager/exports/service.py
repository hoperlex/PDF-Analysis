"""The export use case: a run identity in, CSV bytes out. Nothing is created.

No export aggregate, no table, no row, no ``export_id``, no ``exported_at``, no polling
and no asynchronous job. The export is *computed* from canonical data on request and is
not itself canonical data — which is exactly why it needs no idempotency command of its
own: a repeat returns byte-identical bytes because it recomputes the same read, not
because something remembered the answer.

``P2-API-01`` exposes ``GET /runs/{run_id}/export.csv`` and calls this; it adds no export
logic of its own, and ``P3-WEB-04`` only downloads the response.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.exports.policy import assert_exportable
from auditmanager.exports.query import export_rows
from auditmanager.exports.query import run_header as read_run_header
from auditmanager.exports.serializer import CONTENT_TYPE, render_csv
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId


@dataclass(frozen=True, slots=True)
class CsvExport:
    """The rendered export. A value, not a record of anything.

    **It carries no download name, deliberately.** It used to expose a ``filename``
    property over a template of its own that nothing read - not the router, not the
    frontend, not a test - while reading, from here, as though it were the name the
    system serves. It was not. A dead spelling of the name is worse than none, because
    it is the first answer a reader looking for the download name finds: it sits on the
    object the export produces.

    The name the system serves is built by ``api/routers/export.py:_disposition`` and
    nowhere else, and this docstring does not restate it - restating it here is how the
    dead one came to exist. The frontend suggests a different one
    (``web/src/shared/api/csv-columns.ts``) and says in its own docstring that the
    server's header wins. The two differing is **permitted**: the frozen
    ``openapi.json`` declares that header on ``exportRunCsv``'s 200 as "presentation
    only and is never an identity" and pins no value - no enum, no pattern, no example.
    Reconciling them is not a repair, it is inventing a contract nobody wrote.

    Serving a name is a transport concern and belongs at the transport. A value computed
    from canonical data has no business naming a download.
    ``tests/integration/exports/test_the_download_name_has_one_source.py`` holds this.
    """

    run_id: str
    run_state: str
    content: bytes
    content_type: str = CONTENT_TYPE

    @property
    def byte_size(self) -> int:
        return len(self.content)


def export_run_csv(session: Session, run_id: RunId | str) -> CsvExport:
    """Render one run's findings as the frozen seventeen-column CSV.

    Refuses with ``state_transition_not_allowed`` when the run's terminal does not
    declare ``publishes_result: true`` — a non-terminal run, and the terminal ``failed``.
    A ``partial`` run **is** exported, with its degraded state visible in the
    ``run_state`` column; PC-01 never emits ``partial_result_not_publishable`` here.

    The caller owns the transaction. This function opens no engine and writes nothing.
    """
    resolved = run_id if isinstance(run_id, RunId) else RunId.parse(run_id)
    identity = str(resolved)

    header = read_run_header(session, identity)
    if header is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")

    # The discriminator, before any row is read: a refused run produces no query and no
    # partially built file.
    assert_exportable(header.state, run_id=identity)

    rows = export_rows(session, identity)
    return CsvExport(
        run_id=identity, run_state=header.state, content=render_csv(rows)
    )


__all__ = ["CsvExport", "export_run_csv"]
