"""The result of one pair of pages: from the cache when its content key exists, else computed in the ceilinged child
and written, **blob first, then the row** (`CMP-ENGINE-01`, ADR-0025 decisions 7, 8, 9, 15; wave brief section 4 item 4).

:func:`compare_sheet_pair` is the entry point `CMP-SERIES-01` calls (or the ``pair_result`` handler does, for the queue).
For a project and two page profiles -- either may be absent, which is a sheet only in the newer version (``added``) or
only in the older (``removed``) and needs no result -- it answers a :class:`PairOutcome`.

How a result comes to exist
---------------------------
1. both profiles must belong to the project (``not_found`` otherwise);
2. the **content key** is made from the Merkle of both pages, their annotation hashes, the sorted link reasons, the split
   part, the parameters, ``ALGO_VERSION`` and the project (:mod:`.key`); if the project has a row with that key it is
   the answer and nothing is computed;
3. a page that was refused or ended without a result gives a ``needs_review`` result at once (``PAGE_TOO_LARGE``,
   ``RENDER_FAILED``), no child is started; two pages with the same Merkle give the fast path of the original
   (``engine.py:505-527``), no child either;
4. otherwise the two source PDFs are streamed (digest-checked) into private temporary files and **one child** compares
   the pair under the ceilings of decision 8 (768 MiB, 300 s CPU, 600 s wall). A child that ends without a result, for
   whatever reason, is ``needs_review`` with reason ``RENDER_FAILED`` for **this pair only**, and is stored: the key is
   the content, so the pair is not run again until ``ALGO_VERSION`` changes. A child that never started
   (:class:`~auditmanager.comparison.profile.runner.ChildStartError`) is the server's fault: nothing is stored;
5. the outcome is validated by the generated models of the contract; the mask blob (only for a pair that is not ``same``)
   is published and made ``available``; and only then the row is inserted, ``ON CONFLICT DO NOTHING``. A row never names
   a blob that was not written; a crash between the two leaves an unreferenced blob that a re-run references again (the
   id is the content's).
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from collections.abc import Callable, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.engine import inputs as inputs_module
from auditmanager.comparison.engine.child import annotations as annotations_module
from auditmanager.comparison.engine.child.result import failure_outcome, identical_outcome
from auditmanager.comparison.engine.child.words import classify_kind, make_words
from auditmanager.comparison.engine.key import content_key
from auditmanager.comparison.engine.limits import (
    ALGO_VERSION,
    CHILD_LIMITS,
    REASON_RENDER_FAILED,
    ROLE_PAIR_MASK,
)
from auditmanager.comparison.engine.repository import PairResultRepository, StoredResult
from auditmanager.comparison.engine.runner import ChildRunner, ChildStartError, engine_runner
from auditmanager.comparison.engine.validate import validate_outcome
from auditmanager.comparison.profile import limits as profile_limits
from auditmanager.comparison.profile.models import PageProfileData, PageProfileRow
from auditmanager.comparison.profile.publish import ProfileBlobPublisher
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.profile.repository import PageProfileRepository
from auditmanager.comparison.profile.source import load_source_version, materialised_source
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["MASK_MEDIA_TYPE", "Computed", "PairOutcome", "compare_sheet_pair"]

_LOG = logging.getLogger(__name__)

MASK_MEDIA_TYPE: Final[str] = "application/octet-stream"
_SIZE_TOLERANCE_PT: Final[float] = 0.5
PART_KINDS: Final[frozenset[str]] = frozenset({"split", "floors"})


@dataclass(frozen=True, slots=True)
class Computed:
    """What the child (or the fast path) gave: the outcome, the mask blob bytes if any, how the child ended
    (``ok``, ``identical`` for the fast path, ``refused``, or the class of an end without a result), and the child's
    own account of itself (time and memory as the kernel measured them) when one was started."""

    outcome: dict[str, Any]
    mask: bytes | None
    end: str
    child: Any = None


@dataclass(frozen=True, slots=True)
class PairOutcome:
    """The answer for one pair. ``result_id`` is ``None`` for a sheet that has no partner (``added``, ``removed``)."""

    status: str
    result_id: str | None
    #: This call wrote the row.
    created: bool = False
    #: The row existed (or another worker wrote it first): nothing of this call's computing is in it.
    cached: bool = False
    reasons: tuple[str, ...] = ()
    mask_blob_id: str | None = None
    #: How the child ended, when one was started (``ok``, ``overrun``, ``wall``, ...), for the operator.
    child_end: str | None = None
    timings: Any = None


def _outcome_of(stored: StoredResult, *, created: bool, cached: bool) -> PairOutcome:
    return PairOutcome(
        status=stored.status, result_id=stored.result_id, created=created, cached=cached,
        reasons=tuple(stored.reasons), mask_blob_id=stored.mask_blob_id,
    )


def _failure_reason(a: PageProfileRow, b: PageProfileRow) -> tuple[str, str]:
    """The forcing reason and the sentence for a pair one of whose pages has no profile to compare."""
    reasons = {row.reason for row in (a, b) if row.status != profile_limits.STATUS_READY and row.reason}
    for reason in (profile_limits.REASON_PAGE_TOO_LARGE, profile_limits.REASON_FRAME_MISMATCH, REASON_RENDER_FAILED):
        if reason in reasons:
            return reason, "страница не прочитана: сравнить её нельзя"
    return REASON_RENDER_FAILED, "страница не прочитана: сравнить её нельзя"


def _page_size(row: PageProfileRow) -> tuple[float, float]:
    return float(row.summary.get("width_pt") or 1.0), float(row.summary.get("height_pt") or 1.0)


def _dpi_of(row: PageProfileRow) -> int:
    raster = row.summary.get("raster") or {}
    return int(raster.get("dpi") or 72)


def compare_sheet_pair(
    session_factory: sessionmaker[Session],
    blob_store: Any,
    *,
    project_uid: str,
    page_a_profile_id: str | None,
    page_b_profile_id: str | None,
    link_reasons: Sequence[str] = (),
    part: str | None = None,
    runner: ChildRunner | None = None,
    child_limits: profile_limits.ChildLimits = CHILD_LIMITS,
    work_dir: str | None = None,
    before_publish: Callable[[], None] | None = None,
    fence: Callable[[Session], None] | None = None,
) -> PairOutcome:
    """The result identity of the pair; see the module docstring.

    ``before_publish`` is called before the mask blob is published (the queue handler proves its lease there);
    ``fence`` is called in the transaction that inserts the row (the handler locks its item there)."""
    if page_a_profile_id is None and page_b_profile_id is None:
        raise ValueError("a pair has at least one page")
    if part is not None and part not in PART_KINDS:
        raise ValueError("part is 'split' or 'floors'")
    profiles = PageProfileRepository()
    repository = PairResultRepository()
    present = [p for p in (page_a_profile_id, page_b_profile_id) if p is not None]
    with session_scope(session_factory) as session:
        owned = repository.pages_of_project(session, project_uid, present)
        if owned != set(present):
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ComparisonPageProfile")
        if page_a_profile_id is None or page_b_profile_id is None:
            return PairOutcome(status="added" if page_a_profile_id is None else "removed", result_id=None)
        row_a = profiles.get(session, page_a_profile_id)
        row_b = profiles.get(session, page_b_profile_id)
        if row_a is None or row_b is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ComparisonPageProfile")
        key = content_key(project_uid, row_a, row_b, reasons=link_reasons, part=part)
        existing = repository.find(session, project_uid, key)
    if existing is not None:
        return _outcome_of(existing, created=False, cached=True)

    child_end: str | None = None
    if row_a.status != profile_limits.STATUS_READY or row_b.status != profile_limits.STATUS_READY:
        reason, why = _failure_reason(row_a, row_b)
        width, height = _page_size(row_a)
        outcome = failure_outcome(reason, why, width_pt=width, height_pt=height, dpi=_dpi_of(row_a), extra_reasons=list(link_reasons))
        mask = None
    else:
        reader = PageProfileReader(session_factory, blob_store)
        data_a, data_b = reader.open_profile(row_a), reader.open_profile(row_b)
        computed = _compute(
            session_factory, blob_store, data_a, data_b, link_reasons, part, runner or engine_runner(), child_limits, work_dir)
        outcome, mask, child_end = computed.outcome, computed.mask, computed.end
    validate_outcome(outcome["channels"], outcome["result"])
    if outcome["status"] == "same" and mask is not None:
        raise ValueError("a same result holds no mask")
    if (outcome["result"]["mask"] is None) != (mask is None):
        raise ValueError("the mask blob and the mask member of the result disagree")

    mask_blob_id = None
    if mask is not None:
        if before_publish is not None:
            before_publish()
        mask_blob_id = ProfileBlobPublisher(session_factory, blob_store).publish(mask, role=ROLE_PAIR_MASK, media_type=MASK_MEDIA_TYPE)
    with session_scope(session_factory) as session:
        if fence is not None:
            fence(session)
        result_id = repository.insert(
            session, project_uid=project_uid, content_key=key, algo_version=ALGO_VERSION, status=outcome["status"],
            reasons=outcome["reasons"], channels=outcome["channels"], result=outcome["result"],
            page_a_profile_id=page_a_profile_id, page_b_profile_id=page_b_profile_id, mask_blob_id=mask_blob_id)
        if result_id is not None:
            return PairOutcome(
                status=outcome["status"], result_id=result_id, created=True, reasons=tuple(outcome["reasons"]),
                mask_blob_id=mask_blob_id, child_end=child_end)
        winner = repository.find(session, project_uid, key)
    if winner is None:  # pragma: no cover - a conflict on a key that then vanished
        raise RuntimeError("the pair result could not be written or found")
    return _outcome_of(winner, created=False, cached=True)


def _same_content(a: PageProfileData, b: PageProfileData) -> bool:
    return bool(
        a.content_merkle and a.content_merkle == b.content_merkle
        and abs(a.width_pt - b.width_pt) <= _SIZE_TOLERANCE_PT and abs(a.height_pt - b.height_pt) <= _SIZE_TOLERANCE_PT
        and a.rotation == b.rotation
    )


def _identical(a: PageProfileData, b: PageProfileData, link_reasons: Sequence[str], part: str | None) -> dict[str, Any]:
    """Two pages with the same Merkle: the rendered pages are the same by construction (``engine.py:505-527``)."""
    annotations_a = [{"subtype": x.subtype, "rect": None if x.rect is None else list(x.rect), "contents": x.contents, "sha256": x.sha256} for x in a.annotations]
    annotations_b = [{"subtype": x.subtype, "rect": None if x.rect is None else list(x.rect), "contents": x.contents, "sha256": x.sha256} for x in b.annotations]
    identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    compared = annotations_module.compare_annotations(
        annotations_a, annotations_b, matrix=identity, a_height=a.height_pt, a_rotation=a.rotation,
        b_height=b.height_pt, b_rotation=b.rotation, identity=True)
    words = make_words([[w.x0, w.top, w.x1, w.bottom, w.text] for w in a.words])
    is_spec = classify_kind(words, a.stamp.designation, a.height_pt) == "spec"
    return identical_outcome(
        width_pt=a.width_pt, height_pt=a.height_pt, dpi=int(a.raster[0]) if a.raster else 72, reasons=list(link_reasons),
        annotation_diffs=annotations_module.diff_count(compared), has_annotations=bool(annotations_a or annotations_b),
        service_notes=annotations_module.notes(compared), is_spec=is_spec,
        part={"kind": part, "reliable": True} if part else None)


def _compute(
    session_factory: sessionmaker[Session], blob_store: Any, a: PageProfileData, b: PageProfileData,
    link_reasons: Sequence[str], part: str | None, runner: ChildRunner, child_limits: profile_limits.ChildLimits,
    work_dir: str | None,
) -> Computed:
    """The outcome of a pair of ready pages: the fast path for the same content, else the sources are streamed to
    private temporary files and one child compares them."""
    if _same_content(a, b):
        return Computed(_identical(a, b, link_reasons, part), None, "identical")
    with session_scope(session_factory) as session:
        source_a = load_source_version(session, a.row.version_uid)
        source_b = load_source_version(session, b.row.version_uid)
    with ExitStack() as stack:
        path_a = stack.enter_context(materialised_source(blob_store, source_a))
        path_b = path_a if source_b.blob_id == source_a.blob_id else stack.enter_context(materialised_source(blob_store, source_b))
        return compute_pair(a, b, path_a=path_a, path_b=path_b, link_reasons=link_reasons, part=part, runner=runner,
                            child_limits=child_limits, work_dir=work_dir)


def compute_pair(
    a: PageProfileData, b: PageProfileData, *, path_a: str | None = None, path_b: str | None = None,
    link_reasons: Sequence[str] = (),
    part: str | None = None, runner: ChildRunner | None = None, child_limits: profile_limits.ChildLimits = CHILD_LIMITS,
    work_dir: str | None = None,
) -> Computed:
    """Run the child on two PDFs on disk. No database and no
    object store: this is what the measurement and the tests drive. A child that never started raises
    :class:`ChildStartError`; one that ended without a result gives the ``RENDER_FAILED`` outcome."""
    import json

    if _same_content(a, b):
        return Computed(_identical(a, b, link_reasons, part), None, "identical")
    if path_a is None or path_b is None:
        raise ValueError("two pages of different content need their PDFs")
    runner = runner or engine_runner()
    dpi = int(a.raster[0]) if a.raster else 72
    scratch = tempfile.mkdtemp(prefix="cmp-engine-", dir=work_dir)
    os.chmod(scratch, 0o700)
    try:
        page_a = inputs_module.page_inputs(a, pdf_path=path_a, page_index=a.row.page_number - 1, work_dir=scratch, name="a")
        page_b = inputs_module.page_inputs(b, pdf_path=path_b, page_index=b.row.page_number - 1, work_dir=scratch, name="b")
        inputs_path = os.path.join(scratch, "inputs.json")
        out_dir = os.path.join(scratch, "out")
        inputs_module.write_inputs(inputs_path, page_a, page_b, dpi=dpi, reasons=list(link_reasons), part=part)
        result = runner.run({"inputs": inputs_path, "out_dir": out_dir}, child_limits)
        _LOG.info(
            "comparison_pair end=%s stage=%s wall_s=%s cpu_s=%s max_rss_kib=%s",
            result.end if not result.ok else "ok", result.stage, result.wall_s, result.cpu_s, result.max_rss_kib,
        )
        if result.status == "refused":
            return Computed(failure_outcome(profile_limits.REASON_PAGE_TOO_LARGE, "страница больше допустимой: не сравнивалась",
                                            width_pt=a.width_pt, height_pt=a.height_pt, dpi=dpi, extra_reasons=list(link_reasons)),
                            None, "refused", result)
        if not result.ok:
            return Computed(failure_outcome(REASON_RENDER_FAILED, "расчёт пары не завершён: сравнить страницы не удалось",
                                            width_pt=a.width_pt, height_pt=a.height_pt, dpi=dpi, extra_reasons=list(link_reasons)),
                            None, result.end, result)
        with open(os.path.join(out_dir, "outcome.json"), encoding="utf-8") as handle:
            outcome = json.load(handle)
        mask_path = os.path.join(out_dir, "mask.bin")
        mask = None
        if os.path.exists(mask_path):
            with open(mask_path, "rb") as handle:
                mask = handle.read()
        return Computed(outcome, mask, "ok", result)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


__all__ += ["ChildStartError", "PART_KINDS", "compute_pair"]
