"""The run's Excel export: one finished run in, workbook bytes out. Nothing is created.

`W57B-NORMS-CATALOGUE-XLSX-01`. This is the use case ``exportRunXlsx`` serves. It composes
the certified W57b chain -- the run/page preflight, the certified-source adapter, the
package's read and projection, the deterministic writer -- and adds two things only: the
refusals ``exportRunCsv`` makes, in the same order, and which citation source a run has.

**Refusals, before anything is read.** An unknown run is ``not_found`` (``AuditRun``); a run
whose terminal does not publish a result is ``state_transition_not_allowed``
(:func:`auditmanager.exports.policy.assert_exportable`, the CSV's discriminator). Both are
decided on the run row alone, before any finding, label or citation is read.

**Page labels.** «Лист/стр.» comes only from the version's verified portal companion
(:mod:`.source_labels`): a version without one, or whose companion does not verify, is
``storage_integrity_error`` with ``role: source.structured_companion`` -- the catalog's
"a required manifest role is missing" -- never a page number passed off as a label. A
storage failure the Blob reader raises as a domain error is answered as that error.

**Norm columns.** A run that pinned a retrieval set, or any of whose observations carries a
certified citation partition (``norm_citation_count``) or a citation row, is read through
the certified chain (:func:`.certified_package.prepare_certified_xlsx_package`) with the
caller's verified citation reader; any refusal there is ``required_norm_unavailable`` with
``reference_kind: norm_retrieval_set``, never an export with the citations dropped. A run
with none of the three cannot carry a citation (``0023``), so every finding's citations are
the explicit empty tuple and the two norm columns stay empty; the package records
``<run_id>:no-citation-partitions`` as that source.

**No download name.** As with :class:`auditmanager.exports.CsvExport`, the name the system
serves is built at the transport (``api/routers/export.py``) and nowhere else
(``tests/integration/exports/test_the_download_name_has_one_source.py``).

The caller owns one consistent read transaction, the role decision it states in
``authorization`` and the Blob and citation readers. Two exports of an unchanged run are
byte-identical: every read is ordered and the writer reads no clock.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.documents.public import MANIFEST_ROLE_STRUCTURED_COMPANION
from auditmanager.exports.policy import assert_exportable
from auditmanager.exports.xlsx.certified_package import (
    CertifiedXlsxPackageRefused,
    prepare_certified_xlsx_package,
)
from auditmanager.exports.xlsx.certified_sources import XlsxCertifiedSourcesRefused
from auditmanager.exports.xlsx.package import (
    ExportAuthorization,
    ExportSources,
    prepare_xlsx_package,
)
from auditmanager.exports.xlsx.preflight import read_xlsx_run_source_preflight
from auditmanager.exports.xlsx.writer import CONTENT_TYPE
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import RunId

__all__ = ["OPERATION", "XlsxExport", "export_run_xlsx"]

#: The operation an ``authorization`` must name.
OPERATION: Final[str] = "exportRunXlsx"

#: «Атрибуция» on «Сводка»: how the run's model answers were obtained, in the UI's words
#: (``run-state-badge.tsx``), with the contract value.
_ATTRIBUTION: Final[dict[str, str]] = {
    "live": "ответы модели получены живым вызовом (live)",
    "recorded": "ответы модели воспроизведены из записи (recorded)",
}

_RUN = text(
    """
    SELECT r.run_id, r.state, r.provider_mode, r.analysis_profile_id,
           r.norms_snapshot_id, r.norm_retrieval_set_id,
           EXISTS (SELECT 1 FROM finding_observation o
                    WHERE o.run_id = r.run_id
                      AND o.norm_citation_count IS NOT NULL) AS has_partitions,
           EXISTS (SELECT 1 FROM finding_observation_norm_citation c
                    WHERE c.run_id = r.run_id) AS has_citations
      FROM audit_run r
     WHERE r.run_id = :run_id
    """
)

_FINDINGS = text(
    """
    SELECT f.finding_uid
      FROM finding f
     WHERE f.allocated_by_run_id = :run_id
     ORDER BY f.finding_uid COLLATE "C"
    """
)

#: The certified chain's page-source refusals (``source_labels``, ``preflight``).
_PAGE_SOURCE_PREFIXES: Final[tuple[str, ...]] = ("xlsx_page_source_", "xlsx_run_page_source_")
#: The certified chain's run-pin and citation refusals.
_CITATION_REFUSALS: Final[frozenset[str]] = frozenset({
    "xlsx_run_pin_missing",
    "xlsx_run_pin_mismatch",
    "xlsx_citation_pin_mismatch",
    "xlsx_run_pin_changed",
})


class _CitationReaderRefused(ValueError):
    """The injected citation reader refused the run's persisted citation proof."""


@dataclass(frozen=True, slots=True)
class XlsxExport:
    """The rendered workbook. A value, not a record of anything, and it names no file."""

    run_id: str
    run_state: str
    content: bytes
    content_type: str
    #: XML-forbidden characters the writer replaced with U+FFFD.
    replacement_count: int
    page_label_source_ref: str
    citation_source_ref: str

    @property
    def byte_size(self) -> int:
        return len(self.content)


@dataclass(frozen=True, slots=True)
class _RunFacts:
    run_id: str
    state: str
    provider_mode: str
    analysis_profile_id: str
    norms_snapshot_id: str | None
    norm_retrieval_set_id: str | None
    cites: bool


def _facts(session: Session, run_id: str) -> _RunFacts | None:
    row = session.execute(_RUN, {"run_id": run_id}).mappings().first()
    if row is None:
        return None
    if row["run_id"] != run_id:
        raise ValueError("xlsx_run_identity_mismatch")
    return _RunFacts(
        run_id=row["run_id"],
        state=row["state"],
        provider_mode=row["provider_mode"],
        analysis_profile_id=row["analysis_profile_id"],
        norms_snapshot_id=row["norms_snapshot_id"],
        norm_retrieval_set_id=row["norm_retrieval_set_id"],
        cites=(
            row["norm_retrieval_set_id"] is not None
            or bool(row["has_partitions"])
            or bool(row["has_citations"])
        ),
    )


def _attribution(provider_mode: str) -> str:
    try:
        return _ATTRIBUTION[provider_mode]
    except KeyError:
        raise ValueError("xlsx_run_provider_mode_invalid") from None


def _citation_unavailable(facts: _RunFacts) -> DomainError:
    details: dict[str, str] = {
        "reference_kind": "norm_retrieval_set",
        "analysis_profile_id": facts.analysis_profile_id,
    }
    if facts.norms_snapshot_id is not None:
        details["norms_snapshot_id"] = facts.norms_snapshot_id
    return DomainError(
        ErrorCode.REQUIRED_NORM_UNAVAILABLE,
        message=(
            "this run's norm citations do not verify against its pinned retrieval set, so "
            "the workbook is not produced rather than produced without them"
        ),
        **details,
    )


def _page_source_unavailable() -> DomainError:
    return DomainError(
        ErrorCode.STORAGE_INTEGRITY_ERROR,
        message=(
            "the version has no verifiable portal companion to label its sheets and pages "
            "from, and a page number is never passed off as a sheet label"
        ),
        role=MANIFEST_ROLE_STRUCTURED_COMPANION,
    )


def _domain_cause(exc: BaseException) -> DomainError | None:
    seen: set[int] = set()
    cause = exc.__cause__
    while cause is not None and id(cause) not in seen:
        if isinstance(cause, DomainError):
            return cause
        seen.add(id(cause))
        cause = cause.__cause__
    return None


def _refusal(exc: ValueError, facts: _RunFacts) -> DomainError | None:
    """The domain answer for one of the certified chain's refusals, or ``None`` for a
    failure that is not a refusal of this run's sources (it stays an internal error)."""
    code = str(exc.args[0]) if exc.args else ""
    if code.startswith(_PAGE_SOURCE_PREFIXES):
        return _domain_cause(exc) or _page_source_unavailable()
    if isinstance(exc, (_CitationReaderRefused, XlsxCertifiedSourcesRefused)):
        return _domain_cause(exc) or _citation_unavailable(facts)
    if isinstance(exc, CertifiedXlsxPackageRefused) and code in _CITATION_REFUSALS:
        return _citation_unavailable(facts)
    return None


def _guarded(read_citations: Callable[..., object]) -> Callable[..., object]:
    def read(session: Session, **arguments: Any) -> object:
        try:
            return read_citations(session, **arguments)
        except DomainError:
            raise
        except ValueError as exc:
            raise _CitationReaderRefused(str(exc)) from exc

    return read


def export_run_xlsx(
    session: Session,
    run_id: RunId | str,
    *,
    authorization: ExportAuthorization,
    read_blob: Callable[[str], bytes],
    read_citations: Callable[..., object] | None,
) -> XlsxExport:
    """Render one run's findings as the W57b workbook; see the module docstring."""
    resolved = run_id if isinstance(run_id, RunId) else RunId.parse(run_id)
    identity = str(resolved)

    facts = _facts(session, identity)
    if facts is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
    # The discriminator, before any other row is read: a refused run produces no query
    # and no partially built workbook.
    assert_exportable(facts.state, run_id=identity)

    if (
        not isinstance(authorization, ExportAuthorization)
        or authorization.run_id != identity
        or authorization.operation != OPERATION
        or authorization.decision != "allow"
    ):
        raise ValueError("xlsx_export_authorization_invalid")
    attribution = _attribution(facts.provider_mode)

    try:
        if facts.cites:
            if read_citations is None:
                raise _citation_unavailable(facts)
            package = prepare_certified_xlsx_package(
                session,
                run_id=identity,
                authorization=authorization,
                read_blob=read_blob,
                read_citations=_guarded(read_citations),
                profile_id=facts.analysis_profile_id,
                attribution=attribution,
            )
        else:
            run_source = read_xlsx_run_source_preflight(session, identity, read_blob=read_blob)
            findings = session.execute(_FINDINGS, {"run_id": identity}).scalars().all()
            sources = ExportSources(
                page_labels=run_source.page_labels.page_labels,
                page_label_source_ref=run_source.page_labels.source_ref,
                citations_by_finding=MappingProxyType({str(uid): () for uid in findings}),
                citation_source_ref=f"{identity}:no-citation-partitions",
                attribution=attribution,
            )
            package = prepare_xlsx_package(session, authorization=authorization, sources=sources)
            if package is None:  # pragma: no cover - the run row was read above
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
    except ValueError as exc:
        refusal = _refusal(exc, facts)
        if refusal is None:
            raise
        raise refusal from exc

    if package.content_type != CONTENT_TYPE:  # pragma: no cover - the writer's constant
        raise ValueError("xlsx_content_type_invalid")
    return XlsxExport(
        run_id=identity,
        run_state=facts.state,
        content=package.content,
        content_type=package.content_type,
        replacement_count=package.replacement_count,
        page_label_source_ref=package.page_label_source_ref,
        citation_source_ref=package.citation_source_ref,
    )
