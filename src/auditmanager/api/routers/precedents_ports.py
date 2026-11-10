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

__all__ = ["PrecedentSettingsPort", "VectorControlPort"]


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
