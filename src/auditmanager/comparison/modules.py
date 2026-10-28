"""The comparison module set (`CMP-SEAL-C0`, ADR-0025 decision 23).

``AUDITMANAGER_COMPARISON_MODULES`` names which comparison modules a deployment serves:

* ``none`` (the default, and what an unset or empty variable means) -- neither: no menu entry exists
  and every comparison operation answers ``503 dependency_unavailable``;
* ``versions`` -- «Сравнение версий»;
* ``versions,stages`` -- «Сравнение версий» and «Сравнение стадий».

The set reaches the web through the contract (``ProductVersion.comparison_modules``), never through
a client read of the environment; the worker loop and every comparison command refuse when the module
they belong to is off. This module only parses and names the set: it reads nothing and decides
nothing about any request. Any other value is a configuration error that stops the process while it
is wiring, never a quiet fall back to ``none``.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "COMPARISON_MODULES_ENV",
    "DEFAULT_MODULES",
    "MODULE_SETS",
    "MODULE_STAGES",
    "MODULE_VERSIONS",
    "enabled_modules",
    "parse_modules",
]

COMPARISON_MODULES_ENV: Final[str] = "AUDITMANAGER_COMPARISON_MODULES"
MODULE_VERSIONS: Final[str] = "versions"
MODULE_STAGES: Final[str] = "stages"
DEFAULT_MODULES: Final[str] = "none"
#: The closed set of values, as the contract's ``ComparisonModules`` enum spells them.
MODULE_SETS: Final[tuple[str, ...]] = (DEFAULT_MODULES, "versions", "versions,stages")


def parse_modules(value: str | None) -> str:
    """The module set a configured value names; ``ValueError`` for anything outside the three."""
    if value is None or not value.strip():
        return DEFAULT_MODULES
    candidate = value.strip()
    if candidate not in MODULE_SETS:
        raise ValueError(
            f"{COMPARISON_MODULES_ENV} must be one of {', '.join(MODULE_SETS)}; "
            f"got {len(candidate)} characters that are none of them"
        )
    return candidate


def enabled_modules(value: str) -> frozenset[str]:
    """The modules a set turns on: ``{}`` for ``none``, ``{versions}``, ``{versions, stages}``."""
    if value == DEFAULT_MODULES:
        return frozenset()
    if value not in MODULE_SETS:
        raise ValueError(f"{value!r} is not a comparison module set")
    return frozenset(value.split(","))
