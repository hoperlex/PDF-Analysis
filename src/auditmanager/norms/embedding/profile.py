"""The frozen embedding profile ``bge-m3-dense-v1`` as constants.

The values are the bake-off's (``docs/program/NORM_EMBEDDING_BAKEOFF.md``) and the
``0013_norm_embeddings`` profile row's; ``infra/norms-worker/self_check.py`` holds the same
literals for the image, and the image-contract test keeps the three equal. Changing any of them
is a new profile and a complete rebuild, never an edit here.
"""

from __future__ import annotations

import re
from typing import Final

EMBEDDING_PROFILE: Final = "bge-m3-dense-v1"
MODEL_REPOSITORY: Final = "BAAI/bge-m3"
MODEL_REVISION: Final = "5617a9f61b028005a4858fdac845db406aefb181"
DIMENSIONS: Final = 1024
#: Total inference tokens per window, the two special tokens included.
MAX_TOKENS: Final = 512
#: Content tokens shared by consecutive windows of one over-limit text.
OVERLAP_TOKENS: Final = 64
SPECIAL_TOKENS: Final = 2
#: Plain passage and query text: the profile has no instruction prefix.
PASSAGE_PREFIX: Final = ""
#: The bake-off's encode batch size and thread count.
ENCODE_BATCH_SIZE: Final = 16
THREADS: Final = 8
#: Accepted distance between a stored vector's L2 norm and 1 (the ``0013`` CHECK's bound).
UNIT_NORM_TOLERANCE: Final = 0.0001

#: Opaque snapshot identity, as the ``0012`` CHECK spells it. The in-image entry points
#: validate it with this pattern so they import nothing outside the norms context.
SNAPSHOT_ID_PATTERN: Final = re.compile(r"^ns_[0-9A-HJKMNP-TV-Z]{26}$")


def require_snapshot_id(value: str) -> str:
    # `fullmatch`: the pattern ends in `$`, which also matches before one trailing newline.
    if not SNAPSHOT_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{value!r} is not a norms snapshot id (ns_<ULID>)")
    return value
