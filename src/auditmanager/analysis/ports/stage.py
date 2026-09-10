"""The stage seam: what a stage is handed, and what it is allowed to hand back.

The shape of :class:`StageProduction` is the mechanism that makes ``partial`` and
``skipped`` *structurally* impossible for the three deterministic preparation stages,
rather than merely discouraged. A handler returns artifacts and metrics. It has no
status field, no degraded marker and no way to describe a subset of the work, so
there is no value a handler could return that the runner would translate into
``partial``. The only other thing a handler can do is raise, and a raise is
``failed``. Two outcomes in, two statuses out.

``StageContext`` carries the blob store, the inputs by ``blob_id`` and the version
identity. It deliberately carries no attempt id, no execution token, no lease and no
worker identity: ``PC-01`` runs stages in process, and a seam that accepted an
authority token would invite one to be minted for a call that needs none.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from auditmanager.analysis.engine.registry import StageDefinition
from auditmanager.analysis.engine.result import ArtifactRef, MetricValue
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import BlobStore
from auditmanager.storage.models import BlobId


@dataclass(frozen=True, slots=True)
class StageContext:
    """Everything a stage is given, and nothing it is not."""

    definition: StageDefinition
    version_uid: str
    inputs: Mapping[str, BlobId]
    blob_store: BlobStore

    def blob(self, role: str) -> BlobId:
        """The ``blob_id`` supplied for ``role``, or a typed refusal.

        The runner has already proved every *required* role is present, so this
        raising path belongs to an optional role a stage asked for and did not get.
        """
        blob_id = self.inputs.get(role)
        if blob_id is None:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="a declared stage input was not supplied",
                stage_id=self.definition.stage_id,
                reason="missing_input",
            )
        return blob_id


@dataclass(frozen=True, slots=True)
class StageProduction:
    """What a handler returns: published artifacts and stage metrics.

    There is no ``status`` here on purpose. See the module docstring.
    """

    artifacts: tuple[ArtifactRef, ...] = ()
    metrics: Mapping[str, MetricValue] = field(default_factory=dict)

    @property
    def roles(self) -> frozenset[str]:
        return frozenset(ref.role for ref in self.artifacts)


class StageHandler(Protocol):
    """A stage implementation. Succeeds and returns, or raises ``DomainError``."""

    def __call__(self, context: StageContext) -> StageProduction: ...


__all__ = ["StageContext", "StageHandler", "StageProduction"]
