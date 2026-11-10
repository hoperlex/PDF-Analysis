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
from auditmanager.precedents.similarity import VECTOR_PROFILE, Thresholds, band
from auditmanager.precedents.stemming import StopWordMatcher, compile_stop_words, stem
from auditmanager.precedents.votes import (
    MAX_VOTES_PER_VERSION,
    WINDOW_MONTHS,
    Vote,
    VoteSet,
    case_vote,
    is_independent,
    select_votes,
)
