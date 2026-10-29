"""The overview of «Проекты и этапы» and the comparison queue summary (`CMP-VC-OVERVIEW-01`).

* :mod:`.model`, :mod:`.rules` -- the seven steps, their state words, the next-step rule, the groups, the counters (pure);
* :mod:`.repository` -- the set-based, read-only statements; :mod:`.service` -- the two reads of the contract.

Other contexts import these names only through ``comparison/public.py``.
"""

from auditmanager.comparison.overview.service import ComparisonOverviewService

__all__ = ["ComparisonOverviewService"]
