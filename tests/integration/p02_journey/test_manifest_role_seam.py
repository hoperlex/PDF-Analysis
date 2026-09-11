"""The ingest -> runs seam: the manifest role a real upload writes.

This is the first thing that fails when the modules are composed, and it fails before
any stage runs, so nothing downstream of it has ever been exercised on a version that
the real ingest path produced.

The frozen contract is the authority. ``contracts/analysis/v1/stage-registry.json``
declares ``source.document`` as the input artifact role of ``source_preparation``, and
``contracts/analysis/v1/examples/job-package.example.json`` shows the same spelling.
``auditmanager.runs`` and ``auditmanager.analysis.ports`` both read that value and are
therefore correct. ``auditmanager.documents`` writes ``source_document`` instead, and
``auditmanager.ingest`` publishes it, so a version created through the public upload
surface carries a manifest the run refuses.

These tests assert the contract, not the current behaviour. They are expected to be red
until the owning tree is corrected, and they will go green with no edit here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import text

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
STAGE_REGISTRY = REPOSITORY_ROOT / "contracts" / "analysis" / "v1" / "stage-registry.json"


def _contract_source_role() -> str:
    """The input role ``source_preparation`` declares, read out of the frozen contract.

    Read from the file rather than from either module's constant on purpose: taking it
    from a module would make this test agree with whichever side it imported from, which
    is the shape of vacuity this session exists to avoid.
    """
    registry = json.loads(STAGE_REGISTRY.read_text(encoding="utf-8"))
    roles: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            role = node.get("role")
            if isinstance(role, str) and role.endswith("document"):
                roles.add(role)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(registry)
    assert roles, f"no document input role found in {STAGE_REGISTRY}"
    assert len(roles) == 1, f"ambiguous document roles in the contract: {sorted(roles)}"
    return roles.pop()


def test_contract_declares_the_dotted_source_role() -> None:
    """Anchors the expectation, so a later contract change is visible here rather than silent."""
    assert _contract_source_role() == "source.document"


def test_the_role_a_real_upload_writes_matches_the_contract(session, ingest, journey_harness) -> None:
    """A version from the public upload surface must carry the contract's input role.

    DEFECT as of base 92bece8: it carries ``source_document``. The database cannot catch
    it -- ``ck_input_manifest_entry_role`` is a shape pattern that admits both spellings --
    so the divergence survives every per-module suite and only appears in composition.
    """
    from auditmanager.shared.identity import ProjectUid

    h = journey_harness
    project = ingest.create_project(name=f"B-III manifest role {h.new_key('p')}")
    outcome = ingest.upload_single_pdf(
        project_uid=ProjectUid(str(project.project_uid)),
        content=h.BASELINE_PDF.read_bytes(),
        source_filename="ar_baseline.pdf",
        display_title="AR baseline",
        idempotency_key=h.new_key("upload"),
    )

    written = {entry.role for entry in outcome.version.manifest}
    persisted = {
        row[0]
        for row in session.execute(
            text("SELECT role FROM input_manifest_entry WHERE version_uid = :v"),
            {"v": str(outcome.version.version_uid)},
        )
    }
    assert written == persisted, "the returned manifest disagrees with the persisted rows"
    assert _contract_source_role() in written, (
        f"ingest wrote manifest role(s) {sorted(written)}; the frozen stage registry "
        f"declares {_contract_source_role()!r} as the input of source_preparation. "
        "auditmanager.documents.ROLE_SOURCE_DOCUMENT is the blob-role spelling; the "
        "manifest role is a different namespace and the contract fixes its value."
    )


def test_a_real_upload_can_start_a_run(session, ingest, journey_harness) -> None:
    """The composition claim in one line: what ingest produces, runs must accept.

    This is the journey's step 2 and the gate for everything after it.
    """
    from auditmanager.analysis.text import AR_TEXT_PROFILE, AR_TEXT_PROMPT_BUNDLE
    from auditmanager.runs import start_audit_run
    from auditmanager.shared.identity import ProjectUid

    h = journey_harness
    project = ingest.create_project(name=f"B-III start from upload {h.new_key('p')}")
    outcome = ingest.upload_single_pdf(
        project_uid=ProjectUid(str(project.project_uid)),
        content=h.BASELINE_PDF.read_bytes(),
        source_filename="ar_baseline.pdf",
        display_title="AR baseline",
        idempotency_key=h.new_key("upload"),
    )

    started = start_audit_run(
        session,
        version_uid=str(outcome.version.version_uid),
        analysis_profile_id=str(AR_TEXT_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id),
        provider_mode="recorded",
        idempotency_key=h.new_key("run"),
    )
    session.commit()
    assert started.run_id
