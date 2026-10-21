"""Unserved W57b use case for one certified XLSX export candidate.

The caller owns one consistent read transaction, authorization, registered v3
profile identity and the findings-public citation reader. This module binds
their outputs; it does not grant a role or serve an HTTP download.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.exports.xlsx.certified_sources import sources_from_certified_reads
from auditmanager.exports.xlsx.package import (
    ExportAuthorization,
    PreparedXlsx,
    prepare_xlsx_package,
)
from auditmanager.exports.xlsx.preflight import read_xlsx_run_source_preflight
from auditmanager.shared.identity import RunId


class CertifiedXlsxPackageRefused(ValueError):
    """An export decision or certified source does not match the persisted Run."""


_RUN_PIN = text("""
    SELECT run_id, project_uid, version_uid, state, analysis_profile_id,
           norms_snapshot_id, norm_retrieval_set_id
      FROM audit_run
     WHERE run_id = :run_id
""")


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _pin(session: Session, run_id: str) -> dict[str, object]:
    row = session.execute(_RUN_PIN, {"run_id": run_id}).mappings().one_or_none()
    if row is None:
        raise CertifiedXlsxPackageRefused("xlsx_run_pin_missing")
    return dict(row)


def prepare_certified_xlsx_package(
    session: Session,
    *,
    run_id: RunId | str,
    authorization: ExportAuthorization,
    read_blob: Callable[[str], bytes],
    read_citations: Callable[..., object],
    profile_id: str,
    attribution: str,
) -> PreparedXlsx:
    """Compose verified page/citation sources and render bytes in one read.

    The injected citation reader is the future findings-public port; this
    export context never imports findings internals. Caller-provided DTOs or
    decision references alone cannot prove custody or permission.
    """
    if not isinstance(run_id, (RunId, str)):
        raise CertifiedXlsxPackageRefused("xlsx_run_identity_invalid")
    identity = str(run_id)
    if (
        not _nonblank(identity)
        or not isinstance(authorization, ExportAuthorization)
        or authorization.run_id != identity
        or authorization.operation != "exportRunXlsx"
        or authorization.decision != "allow"
        or not _nonblank(authorization.principal_id)
        or not _nonblank(authorization.decision_ref)
        or not callable(read_blob)
        or not callable(read_citations)
        or not _nonblank(profile_id)
        or not _nonblank(attribution)
    ):
        raise CertifiedXlsxPackageRefused("xlsx_export_inputs_invalid")

    run_source = read_xlsx_run_source_preflight(session, run_id, read_blob=read_blob)
    pin = _pin(session, identity)
    if (
        pin.get("run_id") != identity
        or run_source.run_id != identity
        or pin.get("version_uid") != run_source.version_uid
        or pin.get("state") != run_source.state
        or pin.get("analysis_profile_id") != profile_id
        or not _nonblank(pin.get("project_uid"))
        or not _nonblank(pin.get("norms_snapshot_id"))
        or not _nonblank(pin.get("norm_retrieval_set_id"))
    ):
        raise CertifiedXlsxPackageRefused("xlsx_run_pin_mismatch")

    citation_read = read_citations(
        session, run_id=identity, version_uid=run_source.version_uid,
        profile_id=profile_id,
    )
    if (
        getattr(citation_read, "run_id", None) != identity
        or getattr(citation_read, "project_uid", None) != pin["project_uid"]
        or getattr(citation_read, "version_uid", None) != pin["version_uid"]
        or getattr(citation_read, "run_state", None) != pin["state"]
        or getattr(citation_read, "norms_snapshot_id", None) != pin["norms_snapshot_id"]
        or getattr(citation_read, "norm_retrieval_set_id", None)
        != pin["norm_retrieval_set_id"]
    ):
        raise CertifiedXlsxPackageRefused("xlsx_citation_pin_mismatch")

    sources = sources_from_certified_reads(
        run_source, citation_read, attribution=attribution,
    )
    package = prepare_xlsx_package(
        session, authorization=authorization, sources=sources,
    )
    if package is None or _pin(session, identity) != pin:
        raise CertifiedXlsxPackageRefused("xlsx_run_pin_changed")
    return package


__all__ = ["CertifiedXlsxPackageRefused", "prepare_certified_xlsx_package"]
