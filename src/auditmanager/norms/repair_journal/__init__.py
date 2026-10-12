"""The paid repair journal (`R-106`): a local fsynced file, the ``norm_repair_call`` rows, and
the runner that puts every provider try through both before it is dispatched.

See :mod:`.runner` for the rules and :mod:`.file_journal` for the file. Nothing here knows a
provider: :mod:`auditmanager.norms.__main__` composes the proxy behind :class:`RepairTransport`.
"""

from .file_journal import LocalJournal
from .model import (
    CEILING_USD,
    MAX_CONSECUTIVE_UNKNOWN,
    MAX_PROVIDER_TRIES,
    RETRY_AFTER_CAP_SECONDS,
    RETRY_DELAYS_SECONDS,
    SAMPLE_MARGIN,
    SAMPLE_SIZE,
    AnswerReader,
    CallFailure,
    CallIntent,
    CallRow,
    CallState,
    Failure,
    JournalRefused,
    PreparedRequest,
    RepairTransport,
    RunStopped,
    Settlement,
    StopReason,
    UnreadableAnswer,
    money,
)
from .pricing import RATE_CARD, ModelNotPriced, rate_for, unknown_outcome_bound
from .repository import CallStore, SqlCallStore, StoreConflict
from .runner import (
    SAMPLE_PROCEED,
    SAMPLE_STOP,
    DurableRepairRunner,
    PageProgress,
    ReconcileReport,
    RunSummary,
    build_ledger,
    page_progress,
)

__all__ = [
    "CEILING_USD",
    "MAX_CONSECUTIVE_UNKNOWN",
    "MAX_PROVIDER_TRIES",
    "RATE_CARD",
    "RETRY_AFTER_CAP_SECONDS",
    "RETRY_DELAYS_SECONDS",
    "SAMPLE_MARGIN",
    "SAMPLE_PROCEED",
    "SAMPLE_SIZE",
    "SAMPLE_STOP",
    "AnswerReader",
    "CallFailure",
    "CallIntent",
    "CallRow",
    "CallState",
    "CallStore",
    "DurableRepairRunner",
    "Failure",
    "JournalRefused",
    "LocalJournal",
    "ModelNotPriced",
    "PageProgress",
    "PreparedRequest",
    "ReconcileReport",
    "RepairTransport",
    "RunStopped",
    "RunSummary",
    "Settlement",
    "SqlCallStore",
    "StopReason",
    "StoreConflict",
    "UnreadableAnswer",
    "build_ledger",
    "money",
    "page_progress",
    "rate_for",
    "unknown_outcome_bound",
]
