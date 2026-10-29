"""The stage-upload limits shared by declaration and first-use admission."""

from __future__ import annotations

from typing import Final

RAW_BATCH_BYTES: Final[int] = 2 * 1024 * 1024 * 1024
PART_BYTES: Final[int] = 16 * 1024 * 1024
MAX_FILES: Final[int] = 1000
MAX_ACTIVE_INSTALLATION: Final[int] = 2
MAX_ACTIVE_ACCOUNT: Final[int] = 1
