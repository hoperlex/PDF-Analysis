"""The series of adjacent transitions of «Сравнение версий» (`CMP-SERIES-01`, ADR-0025 decisions 4, 15, 21).

* :mod:`.planning` -- the transitions and sheet pairs of one revision of the effective matrix; only neighbours (pure);
* :mod:`.service` -- the series operations of the contract: start, list, get, pause, resume, cancel, finish, list the sheet pairs, get one;
* :mod:`.handlers` -- the work kinds ``series_pair``, ``series_drive`` and ``series_after_preparation``;
* :mod:`.advance` -- reconcile, finalise a transition (parts coverage, permit reconciliation, counts, verdict), conclude;
* :mod:`.verdict`, :mod:`.parts`, :mod:`.permit`, :mod:`.inputs`, :mod:`.views` -- the pure rules; :mod:`.repository` -- the SQL.

Other contexts import these names only through ``comparison/public.py``.
"""

from auditmanager.comparison.series.followup import enqueue_series_after_preparation, follow_up_dedupe_key
from auditmanager.comparison.series.handlers import (
    SeriesAfterPreparationHandler,
    SeriesDriveHandler,
    SeriesPairHandler,
    series_after_preparation_handler,
    series_drive_handler,
    series_pair_handler,
)
from auditmanager.comparison.series.model import (
    SERIES_AFTER_PREPARATION_KIND,
    SERIES_DRIVE_KIND,
    SERIES_PAIR_KIND,
)
from auditmanager.comparison.series.service import ComparisonSeriesService, PairPage, SeriesPage

__all__ = [
    "ComparisonSeriesService",
    "PairPage",
    "SERIES_AFTER_PREPARATION_KIND",
    "SERIES_DRIVE_KIND",
    "SERIES_PAIR_KIND",
    "SeriesAfterPreparationHandler",
    "SeriesDriveHandler",
    "SeriesPage",
    "SeriesPairHandler",
    "enqueue_series_after_preparation",
    "follow_up_dedupe_key",
    "series_after_preparation_handler",
    "series_drive_handler",
    "series_pair_handler",
]
