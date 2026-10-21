"""Bind an exportable run to its verified XLSX page-label source.

This is a read preflight, not an authorization decision. The guarded API caller
must still establish the principal's role, verify finding citations and supply
one consistent read transaction before composing an XLSX package.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.exports.policy import assert_exportable
from auditmanager.exports.xlsx.source_labels import (
    VerifiedPageLabels,
    read_verified_page_labels,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId, VersionUid


_RUN = text("""
    SELECT run_id, state, version_uid
      FROM audit_run
     WHERE run_id = :run_id
""")


@dataclass(frozen=True, slots=True)
class VerifiedXlsxRunSource:
    run_id: str
    version_uid: str
    state: str
    page_labels: VerifiedPageLabels


def read_xlsx_run_source_preflight(
    session: Session,
    run_id: RunId | str,
    *,
    read_blob: Callable[[str], bytes],
) -> VerifiedXlsxRunSource:
    """Read an exportable run and labels for its exact immutable version.

    The caller owns the session's consistent transaction and the Blob reader.
    Neither an authenticated role nor citation custody is inferred here.
    """
    resolved = run_id if isinstance(run_id, RunId) else RunId.parse(run_id)
    if not callable(read_blob):
        raise ValueError("xlsx_run_blob_reader_invalid")
    identity = str(resolved)
    row = session.execute(_RUN, {"run_id": identity}).mappings().first()
    if row is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
    if row["run_id"] != identity:
        raise ValueError("xlsx_run_identity_mismatch")

    state = row["state"]
    assert_exportable(state, run_id=identity)

    version_uid = str(VersionUid.parse(row["version_uid"]))
    labels = read_verified_page_labels(session, version_uid, read_blob=read_blob)
    if labels is None:
        raise ValueError("xlsx_run_page_source_missing")
    if labels.version_uid != version_uid:
        raise ValueError("xlsx_run_page_source_mismatch")
    return VerifiedXlsxRunSource(
        run_id=identity,
        version_uid=version_uid,
        state=state,
        page_labels=labels,
    )


__all__ = ["VerifiedXlsxRunSource", "read_xlsx_run_source_preflight"]
