"""The stage-upload limits shared by declaration and first-use admission."""

from __future__ import annotations

from typing import Final

from auditmanager.ingest.public import quota

#: Intake quotas (ADR-0025 decision 12); a relaxed deployment (``AUDITMANAGER_INTAKE_RELAXED=1``)
#: lifts them. The free-disk reservation of ``intake`` does not move with the flag.
RAW_BATCH_BYTES: Final[int] = quota(2 * 1024 * 1024 * 1024, 2**63 - 1)
PART_BYTES: Final[int] = 16 * 1024 * 1024
MAX_FILES: Final[int] = quota(1000, 2**31 - 1)
MAX_ACTIVE_INSTALLATION: Final[int] = 2
MAX_ACTIVE_ACCOUNT: Final[int] = 1
