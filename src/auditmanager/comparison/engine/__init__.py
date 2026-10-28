"""The per-sheet comparison engine of «Сравнение версий» (`CMP-ENGINE-01`, ADR-0025 decisions 8, 9, 15).

``mask_codec`` is the format of the mask blob (the wave brief ``CMP-WAVE-C1`` section 4); the rest of the package is
added by the commits that follow it.
"""

from auditmanager.comparison.engine.mask_codec import (
    LAYERS,
    MASK_FORMAT,
    DecodedMask,
    MaskFormatError,
    decode_mask,
    encode_mask,
    encode_packed_planes,
)

__all__ = [
    "DecodedMask",
    "LAYERS",
    "MASK_FORMAT",
    "MaskFormatError",
    "decode_mask",
    "encode_mask",
    "encode_packed_planes",
]
