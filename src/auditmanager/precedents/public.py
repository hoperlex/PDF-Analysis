"""Cross-context surface of the precedent core. Other contexts import this module and nothing deeper."""

from __future__ import annotations

from auditmanager.precedents.advice import (
    STATUS_OK,
    STATUS_UNAVAILABLE,
    UNAVAILABLE_NO_VECTOR,
    PrecedentAdvice,
    evaluate,
)
from auditmanager.precedents.budget import (
    MAX_CASES_PER_ENTRY,
    MAX_CHARACTERS,
    BudgetCase,
    BudgetEntry,
    BudgetSelection,
    SelectedEntry,
    not_fitted_line,
    select_within_budget,
)
from auditmanager.precedents.critic import CriticReview, critic_reviewed, link_candidates, review_of
from auditmanager.precedents.hints import MAX_HINTS_PER_FINDING, Hint, build_hints
from auditmanager.precedents.labels import LabelPolicy, PrecedentLabel, compute_label
from auditmanager.precedents.models import (
    HINT_CRITIC_DIVERGES,
    HINT_DOCUMENT_HISTORY,
    HINT_REJECTION_REASON,
    LABEL_CANCEL_SUGGESTED,
    LABEL_CODES,
    LABEL_FEW,
    LABEL_LIKELY_ACCEPTED,
    LABEL_MIXED,
    LABEL_NONE,
    LABEL_OFTEN_REJECTED,
    REJECTION_LABELS,
    SHOWN_NEUTRAL,
    VERDICT_ACCEPTED,
    VERDICT_REJECTED,
    CaseComment,
    CriticCandidate,
    DecisionEvent,
    FindingContext,
    PrecedentCase,
    ScoredCase,
)
from auditmanager.precedents.replay import (
    REPORT_SCHEMA,
    ReplayCase,
    ReplayReport,
    SectionReport,
    SectionRule,
    ShownLabelCounts,
    SliceMetrics,
    replay_history,
    rule_failures,
)
from auditmanager.precedents.settings import SETTING_ONE_LIST, latest_setting_value, one_list_enabled
from auditmanager.precedents.similarity import VECTOR_PROFILE, Thresholds, band
from auditmanager.precedents.stemming import StopWordMatcher, compile_stop_words, stem
# `EMBED-01` (`ADR-0029` decision 8): the night encoder -- the window, the queue of intents, the exchange with the host's timer, the pause of the
# vectors and the wait a queued run is told. The composition root wires `VectorWindowPass` into the worker's housekeeping pass,
# `VectorControlService` into `build_router(vector_control=...)` and asks `window_wait` for the status of a queued run.
from auditmanager.precedents.vectors.control import SET_VECTOR_PAUSED_COMMAND_TYPE, VectorControlService
from auditmanager.precedents.vectors.exchange import EXCHANGE_DIR_ENV, Exchange
from auditmanager.precedents.vectors.wait import CAUSE as VECTOR_WINDOW_CAUSE
from auditmanager.precedents.vectors.wait import WindowWait, window_wait
from auditmanager.precedents.vectors.window import DEFAULT_WINDOW, WindowSetting, wait_text
from auditmanager.precedents.vectors.window_pass import VectorWindowPass
from auditmanager.precedents.votes import (
    MAX_VOTES_PER_VERSION,
    WINDOW_MONTHS,
    Vote,
    VoteSet,
    case_vote,
    is_independent,
    select_votes,
)
