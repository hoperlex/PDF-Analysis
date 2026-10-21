"""The new findings modules consume AR v2 through the analysis public seam."""

from __future__ import annotations

import ast
from pathlib import Path

from auditmanager.analysis import public as analysis
from auditmanager.findings.merge_publication_plan import MergePreparation


ROOT = Path(__file__).resolve().parents[3]
FINDING_CONSUMERS = (
    ROOT / "src/auditmanager/findings/merge_publication_plan.py",
    ROOT / "src/auditmanager/findings/v2_publication.py",
)


def test_findings_consumers_do_not_import_analysis_implementation_paths() -> None:
    for path in FINDING_CONSUMERS:
        imports = (
            node.module
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.ImportFrom) and node.module is not None
        )
        assert all(
            module == "auditmanager.analysis.public"
            for module in imports
            if module.startswith("auditmanager.analysis.")
        ), path


def test_ar_v2_public_seam_exports_the_same_typed_merge_inputs() -> None:
    required = (
        "AR_V2_CATEGORIES", "AR_V2_SEVERITIES", "MERGE_ARTIFACT_ROLE",
        "MERGE_ARTIFACT_VERSION", "MERGE_RULE_VERSION", "MergePreparation",
        "ProposalGroundingResult", "ProposedObservation", "RejectedProposal",
        "ResolvedAnchor", "prepare_merge",
    )
    assert set(required) <= set(analysis.__all__)
    assert all(getattr(analysis, name) is not None for name in required)
    assert MergePreparation is analysis.MergePreparation
