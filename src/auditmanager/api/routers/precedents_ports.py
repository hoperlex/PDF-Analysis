"""The port of the vectors' pause and night window (`EMBED-01`, contract 1.51.0), beside ``ports.py`` for the reason ``hosts_ports.py`` gives.

``build_precedent_routes(router, vector_control=...)`` answers ``getVectorControl`` and ``setVectorPaused`` through it. With no port the two
routes keep the answer the seal gave them (``503 dependency_unavailable``, ``details.dependency`` ``vector_control``); the composition root
wires ``auditmanager.precedents.public.VectorControlService`` into ``build_router(vector_control=...)``. Every method takes what the route parsed
and returns the contract's shape as a mapping the route validates against ``VectorControl``; a rule -- a role beyond the register, who sees the
counts, what a repeated key answers -- is the implementation's, never the route's.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

__all__ = ["DecisionPatternsPort", "PrecedentSettingsPort", "PrecedentsPort", "StageQualityPort", "VectorControlPort"]


class VectorControlPort(Protocol):
    """The pause of the vectors and the state of the night window: the read for ``expert`` and ``admin``, the keyed write for ``admin``."""

    def get_vector_control(self, *, user_uid: str) -> Mapping[str, Any]: ...

    def set_vector_paused(self, *, paused: bool, user_uid: str, idempotency_key: str) -> Mapping[str, Any]: ...


class PrecedentSettingsPort(Protocol):
    """The journal of the programme's switches and settings (`PREC-SETTINGS-01`): the read and the keyed write, both for ``admin``.

    With no port ``listPrecedentSettings`` and ``appendPrecedentSetting`` keep the answer the seal gave them (``503 dependency_unavailable``,
    ``details.dependency`` ``precedent_settings``); the composition root wires ``auditmanager.precedents.public.PrecedentSettingService`` into
    ``build_router(precedent_settings=...)``. A rule -- a role, the shape of a value, what a repeated key answers -- is the implementation's."""

    def list_precedent_settings(self, *, user_uid: str) -> Mapping[str, Any]: ...

    def append_precedent_setting(
        self, *, setting_name: str, value: Mapping[str, Any], user_uid: str, idempotency_key: str,
    ) -> Mapping[str, Any]: ...


class PrecedentsPort(Protocol):
    """The labels of a run's findings and the card of a finding (`PREC-PASS`): both reads, for ``expert`` and ``admin``.

    With no port ``getRunPrecedents`` and ``getFindingPrecedents`` keep the answer the seal gave them (``503 dependency_unavailable``, ``details.dependency``
    ``precedents``); the composition root wires ``auditmanager.precedents.public.PrecedentService`` into ``build_router(precedents=...)``. Each method answers in
    the contract's shape as a mapping the route validates against ``RunPrecedents`` and ``FindingPrecedents``; who may read, what is unavailable and what is not
    found are the implementation's rules, never the route's. An unknown run or finding is ``not_found``; a run or finding the pass has not reached is not an
    error but ``available: false``."""

    def get_run_precedents(self, *, run_id: str, user_uid: str) -> Mapping[str, Any]: ...

    def get_finding_precedents(self, *, finding_uid: str, user_uid: str) -> Mapping[str, Any]: ...


class DecisionPatternsPort(Protocol):
    """The failure patterns (`PAT-01`, contract 1.53.0): the read and the keyed review, both for ``expert`` and ``admin``.

    With no port ``listDecisionPatterns`` and ``reviewDecisionPattern`` keep the answer the seal gave them (``503 dependency_unavailable``,
    ``details.dependency`` ``decision_patterns``); the composition root wires the lane's service into ``build_router(decision_patterns=...)``. Each method
    answers in the contract's shape as a mapping the route validates against ``DecisionPatternList`` and ``DecisionPattern``; a rule -- a role, which
    transition is allowed (``not_found``, ``state_conflict``), what a repeated key answers -- is the implementation's, never the route's. The review is
    recorded under the command type ``review_decision_pattern``."""

    def list_decision_patterns(
        self, *, status: str | None, section_code: str | None, limit: int, user_uid: str,
    ) -> Mapping[str, Any]: ...

    def review_decision_pattern(
        self, *, pattern_id: str, decision: str, user_uid: str, idempotency_key: str,
    ) -> Mapping[str, Any]: ...


class StageQualityPort(Protocol):
    """The quality table (`QUAL-01`, contract 1.53.0): the read, for ``admin``. With no port ``getStageQuality`` keeps the answer the seal gave it
    (``503 dependency_unavailable``, ``details.dependency`` ``stage_quality``); the composition root wires the lane's service into
    ``build_router(stage_quality=...)``. It answers in the contract's shape as a mapping the route validates against ``StageQualityTable``."""

    def get_stage_quality(self, *, user_uid: str) -> Mapping[str, Any]: ...
