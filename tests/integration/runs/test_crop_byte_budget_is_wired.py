"""Every deterministic stage publishes through the crop byte budget (`RUN-ROBUSTNESS-01`, D-177).

``tests/unit/runs/test_crop_byte_budget.py`` and
``tests/integration/analysis/geometry/test_crop_byte_budget_stage.py`` show what the decorator
does. This shows the executor uses it: a real run, its stages driven through the real chain,
and the store each of the three deterministic stages is handed is a :class:`CropByteBudget`
for that stage, over the durable publication store -- not the bare store, which is what the
chain handed them before and what a refactor of ``execute_run`` could quietly return to.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from auditmanager.runs import execute_run, executor, start_audit_run
from auditmanager.runs.crop_budget import MAX_CROP_BYTES, CropByteBudget
from auditmanager.storage.public import DurablePublicationStore
from tests.support.v1_reference_profile import resolve_reference_profile


def test_each_deterministic_stage_is_handed_the_crop_byte_budget(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key, monkeypatch
) -> None:
    handed: list[tuple[str, Any]] = []
    real_run_stage = executor.run_stage

    def spy(stage_id: str, **arguments: Any) -> Any:
        handed.append((stage_id, arguments["blob_store"]))
        return real_run_stage(stage_id, **arguments)

    monkeypatch.setattr(executor, "run_stage", spy)
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("crop-budget-wired"),
    )

    execute_run(
        session,
        str(started.run_id),
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
        sleep=lambda _seconds: None,
        text_profiles=resolve_reference_profile,
    )

    stages = [stage_id for stage_id, _store in handed]
    assert stages[:3] == ["source_preparation", "page_geometry_extraction", "document_context_build"]
    for stage_id, store in handed[:3]:
        assert isinstance(store, CropByteBudget), stage_id
        assert store._stage_id == stage_id
        assert store._budget == MAX_CROP_BYTES
        assert isinstance(store._store, DurablePublicationStore), (
            "the budget sits over the durable publication store, not instead of it"
        )
