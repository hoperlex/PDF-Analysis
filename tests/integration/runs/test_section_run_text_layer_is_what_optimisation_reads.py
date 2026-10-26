"""`OPT-PROJECT-ALL-SECTIONS-01`: a published run of a non-АР section leaves the text layer the
optimisation reads, and it is the same layer an АР-profile run of the same bytes leaves.

«Спецификация и цены», «Предложения» and «Оптимизация разделов» take the saved page text of the
newest **published** run of a version through the composition root's ``_SpecificationTextReader``.
Opening the first two to every section assumes that a run of any section's text profile leaves the
layer that reader returns. This module measures that assumption on real PostgreSQL and MinIO, in
recorded mode, with the section profiles of the shipped registry:

* a ``KJ``, ``OV`` and ``PB`` version each run to ``published`` under their own profile and
  recording (the ``W59`` pattern of ``test_w59_section_profile_recorded.py``);
* the reader names that run as the version's newest published one and returns a verified layer
  for every page;
* the layer's digest equals the digest of the layer a run of the same version under the v1
  reference profile leaves (``source_preparation`` produces it before any profile is consulted).

**What this does not measure.** The recorded section fixtures are all built over the АР corpus
bytes, whose text has **no specification table**; ``extract_specification`` finds zero tables in
the layer asserted below. So this proves the reader path for a real section run, and says nothing
about whether the extraction understands a real ПБ, ОВ or КЖ volume's Form-7 table.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.text import RecordedAdapter
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.bootstrap import adapters
from auditmanager.optimisation.specification import extract_specification
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.sections.public import classify_document_version
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE, resolve_reference_profile

REGISTRY = load_text_profile_registry()
PAGES = 8  # the baseline corpus PDF the harness publishes


def _classify(session: Session, seeded: Any, code: str) -> None:
    from am_test_accounts import provisioned_record

    classify_document_version(
        session,
        project_uid=seeded.project_uid,
        document_uid=seeded.document_uid,
        version_uid=seeded.version_uid,
        project_stage="R",
        section_code=code,
        actor_uid=str(provisioned_record("opt-all-sections-text-layer").user_uid),
        actor_roles=frozenset({"expert"}),
    )


def _layer_digest(session: Session, run_id: str) -> str:
    artifacts = session.execute(
        text("SELECT artifacts FROM stage_result WHERE run_id = :r AND stage_id = 'source_preparation'"),
        {"r": run_id},
    ).scalar_one()
    (layer,) = [a for a in artifacts if a.get("role") == "prepared.text_layer"]
    return str(layer["sha256"])


@pytest.mark.parametrize("code", ["KJ", "OV", "PB"])
def test_a_published_section_run_leaves_the_layer_the_optimisation_reads(
    session: Session, seeded, blob_store, provider_config, new_key, helpers, code: str
) -> None:
    _classify(session, seeded, code)
    section_run = start_audit_run(
        session, version_uid=seeded.version_uid, provider_mode="recorded",
        idempotency_key=new_key(f"opt-all-sections-{code}"),
        section_profiles=REGISTRY.section_profiles(),
    ).run_id
    done = execute_run(
        session, section_run, blob_store=blob_store, adapter=RecordedAdapter(),
        provider_config=provider_config, text_profiles=REGISTRY.resolve,
    )
    assert done.terminal_state == "published", (dict(done.stage_statuses), done.degradation_set)
    assert helpers.run_state_of(session, section_run) == "published"

    reader = adapters._SpecificationTextReader(blob_store)
    runs = [(run.run_id, run.state) for run in reader.runs_newest_first(session, version_uid=seeded.version_uid)]
    assert runs == [(section_run, "published")]
    saved = reader.saved_page_text(
        session, run_id=section_run, version_uid=seeded.version_uid, page_count=PAGES
    )
    assert saved is not None and saved.run_id == section_run
    assert sorted(saved.pages) == list(range(1, PAGES + 1))
    assert all(isinstance(page, str) for page in saved.pages.values())
    assert any(page.strip() for page in saved.pages.values())  # not vacuous: there is text
    assert saved.text_layer_sha256 == _layer_digest(session, section_run)

    # the layer does not depend on the profile: a v1 reference-profile run of the same bytes
    reference_run = start_audit_run(
        session, version_uid=seeded.version_uid,
        analysis_profile_id=str(V1_REFERENCE_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(V1_REFERENCE_PROFILE.prompt_bundle.prompt_bundle_id),
        provider_mode="recorded", idempotency_key=new_key(f"opt-all-sections-reference-{code}"),
    ).run_id
    execute_run(
        session, reference_run, blob_store=blob_store, adapter=RecordedAdapter(),
        provider_config=provider_config, text_profiles=resolve_reference_profile,
    )
    assert _layer_digest(session, reference_run) == saved.text_layer_sha256

    # the limit, measured: the corpus text holds no specification table
    extraction = extract_specification(version_uid=seeded.version_uid, pages=saved.pages)
    assert (extraction.table_count, len(extraction.rows)) == (0, 0)
