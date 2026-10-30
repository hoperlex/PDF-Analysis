"""The crop byte budget of one version (`RUN-ROBUSTNESS-01`, D-177).

`W55B-FIX` bounded the *number* of crops a version may ask for (``MAX_IMAGE_BLOCKS``, 1 000)
and each crop's *pixels* (``MAX_PIXELS``, 4 000 000), and `W55B-JUDGE-X` X-4's recheck left the
product of the two unbounded in bytes: a high-entropy crop at the pixel cap is 11.4 MiB of PNG,
so a bundle of a thousand distinct ones makes a stage publish about 11 GiB for one version and
hold it for good.

The measured volume is far below that. On `W55B-REHEARSAL-01`'s 500-sheet scanned set the 500
crops of 2.2 Mpx median were 396.6 MiB, 0.79 MiB a crop; the 1 000 crops the ceiling allows
would be 0.77 GiB. :data:`MAX_CROP_BYTES` is 2 GiB: two and a half times that, and 175 of the
worst case. A stage that would go past it is refused with ``analysis_input_invalid`` and the
``reason`` :data:`REASON_CROPS_OVER_BUDGET` -- an existing code with a classifier of the same
kind as ``portal_block_degenerate``; nothing is added to the error catalogue.

It is a decorator over the stage's publication store and not a change to the stage, so the
stage keeps publishing crops one at a time exactly as before and the budget is the run
boundary's: :class:`CropByteBudget` looks only at ``put_blob`` of a crop-image blob, counts the
bytes the caller *declares* and refuses **before** the inner store journals, stages or uploads
anything, so the blob that would cross the line is never written. Each stage execution builds
its own, so the count is per version and per attempt: crops are content-addressed, and a
resumed attempt that publishes the same bytes again is a new count of the same blobs, not a
second budget's worth of storage. The stage's crop publisher publishes each distinct PNG once,
so equal crops are counted once.
"""

from __future__ import annotations

from typing import Any, Final

from auditmanager.analysis.public import ROLE_CROP_IMAGE
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import parse_blob_role

__all__ = ["MAX_CROP_BYTES", "REASON_CROPS_OVER_BUDGET", "CropByteBudget"]

#: The most crop-image bytes one stage execution may publish for one version.
MAX_CROP_BYTES: Final[int] = 2 * 1024**3
#: The ``reason`` of the refusal (``analysis_input_invalid``).
REASON_CROPS_OVER_BUDGET: Final[str] = "portal_crops_over_budget"

#: The blob role of a crop image, as the geometry stage names it.
_CROP_ROLE: Final = parse_blob_role(ROLE_CROP_IMAGE.replace(".", "_"))


class CropByteBudget:
    """A blob store that refuses the crop that would take the stage past its byte budget.

    Everything but ``put_blob`` is the inner store's own, untouched.
    """

    __slots__ = ("_store", "_stage_id", "_budget", "_used")

    def __init__(self, store: Any, *, stage_id: str, budget: int | None = MAX_CROP_BYTES) -> None:
        if budget is not None and (type(budget) is not int or budget < 0):
            raise ValueError("crop budget must be a nonnegative integer or None")
        self._store = store
        self._stage_id = stage_id
        self._budget = budget
        self._used = 0

    @property
    def used(self) -> int:
        """The crop bytes this execution has published so far."""
        return self._used

    def put_blob(
        self,
        source: Any,
        *,
        declared_sha256: str,
        declared_size: int,
        role: Any,
        media_type: str,
    ) -> Any:
        if role == _CROP_ROLE:
            if self._budget is not None and self._used + declared_size > self._budget:
                raise DomainError(
                    ErrorCode.ANALYSIS_INPUT_INVALID,
                    message=(
                        "the crops of this version would take more storage than a version may "
                        "hold; the stage refuses rather than publishing them"
                    ),
                    stage_id=self._stage_id,
                    reason=REASON_CROPS_OVER_BUDGET,
                )
            self._used += declared_size
        return self._store.put_blob(
            source,
            declared_sha256=declared_sha256,
            declared_size=declared_size,
            role=role,
            media_type=media_type,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._store, name)
