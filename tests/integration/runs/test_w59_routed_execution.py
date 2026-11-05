"""`W59-SECTION-SEAL-01`: a section-routed run executes with **its own** prompt bundle.

Before this seal the executor handed every v1-style run the АР profile whatever the run
had pinned. With the registry's resolver (what the served application and the worker pass):

* an ``AR``-classified version starts a run on АР's own pair (`HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030`; between
  `PROD-11-AR-V1-V2-REMOVAL-01` and that hotfix it could not start at all: ``section_profile_unavailable``,
  nothing written). The test that showed the АР run reproducing the recorded corpus run is replaced by a ``PB``
  run that does the same: ПБ's recording carries the corpus run's findings;
* a ``KJ``-classified run reaches ``text_analysis`` with the ``KJ`` package's profile and its
  ``system_prompt.md`` (one trailing newline stripped) as the bundle's system prompt;
* a run whose pinned pair the registry does not hold is refused before any stage runs, with
  ``required_norm_unavailable`` (``reference_kind: analysis_profile``) -- no AR substitute.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.text import RecordedAdapter
from auditmanager.analysis.text.profile_registry import PACKAGES_ROOT, load_text_profile_registry
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.runs import executor as executor_module
from auditmanager.sections.public import classify_document_version
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE

REGISTRY = load_text_profile_registry()


def _classified_run(session: Session, seeded: Any, code: str, key: str) -> str:
    from am_test_accounts import provisioned_record

    classify_document_version(
        session,
        project_uid=seeded.project_uid,
        document_uid=seeded.document_uid,
        version_uid=seeded.version_uid,
        project_stage="R",
        section_code=code,
        actor_uid=str(provisioned_record("w59-routed-execution").user_uid),
        actor_roles=frozenset({"expert"}),
    )
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        provider_mode="recorded",
        idempotency_key=key,
        section_profiles=REGISTRY.section_profiles(),
    )
    return started.run_id


def test_an_ar_classified_version_starts_a_run_on_the_ar_profile_pair(
    session: Session, seeded, new_key
) -> None:
    """`HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030` (3821261a): АР is a text profile again (draft 1.0.0).

    `PROD-11-AR-V1-V2-REMOVAL-01` had АР refused with ``section_profile_unavailable`` and nothing written. The
    hotfix registered the original-source profile, so the routed start pins АР's own pair -- the one no other section
    shares -- and writes the run and its command. What the run then does is `AR`'s recorded replay, not this seal's.
    """
    key = new_key("w59-ar-routed")
    run_id = _classified_run(session, seeded, "AR", key)
    table = REGISTRY.section_profiles()
    assert "AR" in table
    pinned = session.execute(
        text("SELECT analysis_profile_id, prompt_bundle_id FROM audit_run WHERE run_id = :r"), {"r": run_id}
    ).one()
    assert tuple(pinned) == table["AR"]
    assert all(pair != table["AR"] for code, pair in table.items() if code != "AR")
    assert session.execute(
        text("SELECT count(*) FROM audit_run WHERE version_uid = :v"), {"v": seeded.version_uid}
    ).scalar_one() == 1
    assert session.execute(
        text("SELECT count(*) FROM command_record WHERE idempotency_key = :k"), {"k": str(key)}
    ).scalar_one() == 1


def test_a_pb_routed_run_reproduces_the_recorded_corpus_run_end_to_end(
    session: Session, seeded, blob_store, provider_config, new_key
) -> None:
    run_id = _classified_run(session, seeded, "PB", new_key("w59-pb-routed"))
    result = execute_run(
        session, run_id, blob_store=blob_store, adapter=RecordedAdapter(),
        provider_config=provider_config, text_profiles=REGISTRY.resolve,
    )
    assert result.terminal_state == "published", dict(result.stage_statuses)
    pinned = session.execute(
        text("SELECT analysis_profile_id, prompt_bundle_id FROM audit_run WHERE run_id = :r"),
        {"r": run_id},
    ).one()
    assert tuple(pinned) == REGISTRY.section_profiles()["PB"]


def test_a_kj_routed_run_sends_the_kj_packages_own_prompt(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[Any] = []
    real = executor_module.run_text_analysis

    def spy(**kwargs: Any) -> Any:
        seen.append(kwargs["profile"])
        return real(**kwargs)

    monkeypatch.setattr(executor_module, "run_text_analysis", spy)
    run_id = _classified_run(session, seeded, "KJ", new_key("w59-kj-routed"))
    execute_run(
        session, run_id, blob_store=blob_store, adapter=recorded_adapter,
        provider_config=provider_config, text_profiles=REGISTRY.resolve,
    )
    assert seen, "the text stage was never reached"
    kj_profile, kj_bundle = REGISTRY.section_profiles()["KJ"]
    expected_prompt = (PACKAGES_ROOT / "kj" / "system_prompt.md").read_text(encoding="utf-8")
    for profile in seen:
        assert str(profile.analysis_profile_id) == kj_profile
        assert str(profile.prompt_bundle.prompt_bundle_id) == kj_bundle
        assert profile.prompt_bundle.system_prompt == expected_prompt[:-1]
        assert profile.prompt_bundle.system_prompt != V1_REFERENCE_PROFILE.prompt_bundle.system_prompt
        assert profile.discipline == "KJ"


def test_an_unregistered_pinned_pair_is_refused_before_any_stage(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("w59-unregistered"),
    )
    with pytest.raises(DomainError) as refused:
        execute_run(
            session, started.run_id, blob_store=blob_store, adapter=recorded_adapter,
            provider_config=provider_config, text_profiles=REGISTRY.resolve,
        )
    assert refused.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
    assert refused.value.detail_fields["reference_kind"] == "analysis_profile"
    assert session.execute(
        text("SELECT count(*) FROM stage_result WHERE run_id = :r"), {"r": started.run_id}
    ).scalar_one() == 0
    assert session.execute(
        text("SELECT state FROM audit_run WHERE run_id = :r"), {"r": started.run_id}
    ).scalar_one() == "created"
