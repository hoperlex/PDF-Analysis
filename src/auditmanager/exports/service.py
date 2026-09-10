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
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.exports.policy import assert_exportable
from auditmanager.exports.query import export_rows
from auditmanager.exports.query import run_header as read_run_header
from auditmanager.exports.serializer import CONTENT_TYPE, render_csv
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId

#: What a browser should call the downloaded file. Derived from the run identity, which
#: is opaque: no filesystem path, no bucket and no object key is involved, and none of
#: those is an identity in the first place (P02 §2.2).
_FILENAME_TEMPLATE: Final[str] = "audit_run_{run_id}.csv"


@dataclass(frozen=True, slots=True)
class CsvExport:
    """The rendered export. A value, not a record of anything."""

    run_id: str
    run_state: str
    content: bytes
    content_type: str = CONTENT_TYPE

    @property
    def filename(self) -> str:
        return _FILENAME_TEMPLATE.format(run_id=self.run_id)

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
