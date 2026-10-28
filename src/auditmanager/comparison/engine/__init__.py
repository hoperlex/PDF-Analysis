"""The per-sheet comparison engine of «Сравнение версий» (`CMP-ENGINE-01`, ADR-0025 decisions 8, 9, 15).

* :mod:`.mask_codec` -- the format of the mask blob (the wave brief ``CMP-WAVE-C1`` section 4 item 1);
* :mod:`.service` -- :func:`compare_sheet_pair`, the entry point of `CMP-SERIES-01`: the result identity of a pair of
  page profiles, from the cache or computed in a ceilinged child and written (blob first, then the row);
* :mod:`.handler`, :mod:`.enqueue` -- the ``pair_result`` work kind and the call that enqueues a pair;
* :mod:`.child` -- what runs inside the child (never imported by the worker's side except the pure modules).

Other contexts import these names only through ``comparison/public.py``.
"""

from auditmanager.comparison.engine.enqueue import enqueue_pair_result, pair_result_dedupe_key
from auditmanager.comparison.engine.handler import (
    PAIR_RESULT_KIND,
    PairResultHandler,
    pair_result_handler,
    pair_result_payload,
)
from auditmanager.comparison.engine.limits import ALGO_VERSION as ENGINE_ALGO_VERSION
from auditmanager.comparison.engine.mask_codec import (
    LAYERS,
    MASK_FORMAT,
    DecodedMask,
    MaskFormatError,
    decode_mask,
    encode_mask,
    encode_packed_planes,
)
from auditmanager.comparison.engine.repository import PairResultRepository, StoredResult
from auditmanager.comparison.engine.service import PairOutcome, compare_sheet_pair

__all__ = [
    "DecodedMask",
    "ENGINE_ALGO_VERSION",
    "LAYERS",
    "MASK_FORMAT",
    "MaskFormatError",
    "PAIR_RESULT_KIND",
    "PairOutcome",
    "PairResultHandler",
    "PairResultRepository",
    "StoredResult",
    "compare_sheet_pair",
    "decode_mask",
    "encode_mask",
    "encode_packed_planes",
    "enqueue_pair_result",
    "pair_result_dedupe_key",
    "pair_result_handler",
    "pair_result_payload",
]
