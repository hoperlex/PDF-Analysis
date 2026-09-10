"""The stage registry loader: canonical stage identity, read from the contract.

``GJ-02-EO-11`` and ``GJ-02-EO-13`` require that stage identity and skippability come
only from the versioned registry. So this module restates neither. It reads
``contracts/analysis/v1/stage-registry.json`` and exposes what it found; a stage
version hard-coded in Python would be a second place to be wrong, and the first place
to drift.

Two refusals are the point of the module:

* **An unknown stage is refused, never defaulted.** ``stage()`` raises rather than
  returning a permissive default, because the alternative is running a stage under an
  identity the contract does not declare.
* **A legacy alias is never accepted.** The registry's own ``alias_resolution`` rule
  says the control plane resolves a legacy name to a canonical ``stage_id`` at its
  boundary and "the engine never accepts a legacy name". This loader reads only
  ``stages[].stage_id``; there is no alias table here to consult, so there is no code
  path by which one could be honoured.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Mapping

from auditmanager.shared.errors import DomainError, ErrorCode

#: Repository-relative location of the frozen contract. Read-only for this package.
CONTRACT_PATH: Final[Path] = (
    Path(__file__).resolve().parents[4]
    / "contracts"
    / "analysis"
    / "v1"
    / "stage-registry.json"
)

_EXPECTED_CONTRACT: Final[str] = "auditmanager.analysis.stage_registry"


@dataclass(frozen=True, slots=True)
class StageDefinition:
    """One stage exactly as the registry declares it. Nothing is inferred."""

    stage_id: str
    stage_version: str
    title: str
    depends_on: tuple[str, ...]
    required_input_roles: tuple[str, ...]
    optional_input_roles: tuple[str, ...]
    required_output_roles: tuple[str, ...]
    skip_allowed: bool
    partial_allowed: bool
    retryable: bool
    succeeded_requires_all_required_outputs: bool

    def missing_inputs(self, supplied: Mapping[str, Any]) -> tuple[str, ...]:
        """Required input roles the caller did not supply, in registry order."""
        return tuple(role for role in self.required_input_roles if role not in supplied)

    def missing_outputs(self, produced: frozenset[str]) -> tuple[str, ...]:
        """Required output roles the stage did not produce, in registry order."""
        return tuple(role for role in self.required_output_roles if role not in produced)


class StageRegistry:
    """The loaded contract. Immutable, and the only source of stage identity."""

    __slots__ = ("_stages", "_contract_version")

    def __init__(self, document: Mapping[str, Any]) -> None:
        contract = document.get("contract")
        if contract != _EXPECTED_CONTRACT:
            raise DomainError(
                ErrorCode.UNSUPPORTED_CONTRACT_VERSION,
                message=(
                    "the stage registry document does not declare the expected "
                    "analysis stage-registry contract"
                ),
            )
        self._contract_version = str(document.get("contract_version", ""))
        stages: dict[str, StageDefinition] = {}
        for entry in document.get("stages", ()):
            definition = _definition_from(entry)
            stages[definition.stage_id] = definition
        self._stages: Mapping[str, StageDefinition] = stages

    @classmethod
    def load(cls, path: Path | None = None) -> "StageRegistry":
        source = path or CONTRACT_PATH
        document = json.loads(source.read_text(encoding="utf-8"))
        return cls(document)

    @property
    def contract_version(self) -> str:
        return self._contract_version

    @property
    def stage_ids(self) -> frozenset[str]:
        return frozenset(self._stages)

    def stage(self, stage_id: str) -> StageDefinition:
        """Return the declared stage, or refuse.

        The refusal carries ``stage_id`` only. That key is in the catalog's
        ``safe_detail_keys`` for ``analysis_input_invalid``, and a canonical stage id
        is a contract constant rather than caller-supplied protected content.
        """
        definition = self._stages.get(stage_id)
        if definition is None:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message=(
                    "the requested stage is not declared by the analysis stage "
                    "registry; the engine accepts canonical stage identity only"
                ),
                stage_id=stage_id if isinstance(stage_id, str) else "<not-a-string>",
                reason="unknown_stage",
            )
        return definition


def _definition_from(entry: Mapping[str, Any]) -> StageDefinition:
    policy = entry.get("status_policy", {})
    inputs = entry.get("required_inputs", ())
    outputs = entry.get("produced_outputs", ())
    return StageDefinition(
        stage_id=str(entry["stage_id"]),
        stage_version=str(entry["stage_version"]),
        title=str(entry.get("title", "")),
        depends_on=tuple(str(item) for item in entry.get("depends_on", ())),
        required_input_roles=tuple(
            str(item["role"]) for item in inputs if item.get("required")
        ),
        optional_input_roles=tuple(
            str(item["role"]) for item in inputs if not item.get("required")
        ),
        required_output_roles=tuple(
            str(item["role"]) for item in outputs if item.get("required")
        ),
        skip_allowed=bool(policy.get("skip_allowed", False)),
        partial_allowed=bool(policy.get("partial_allowed", False)),
        retryable=bool(policy.get("retryable", False)),
        succeeded_requires_all_required_outputs=bool(
            policy.get("succeeded_requires_all_required_outputs", True)
        ),
    )


@lru_cache(maxsize=1)
def default_registry() -> StageRegistry:
    """The contract on disk, parsed once per process."""
    return StageRegistry.load()


__all__ = [
    "CONTRACT_PATH",
    "StageDefinition",
    "StageRegistry",
    "default_registry",
]
