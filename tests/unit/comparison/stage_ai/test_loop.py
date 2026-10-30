"""Model-selected context stays within immutable source fragments."""

import pytest

from auditmanager.comparison.stage_ai.loop import final_document, resolve_context, with_loop
from auditmanager.comparison.stage_ai.reviewer import build_review_requests
from auditmanager.comparison.stage_ai.source import build_source_groups
from auditmanager.comparison.stage_ai.validation import StageAiValidationError
from tests.unit.comparison.stage_ai.test_runtime import snapshot


def test_context_can_only_read_loaded_source_and_returns_anchored_excerpts():
    source = snapshot()
    target = source["fragments"][1]
    result = resolve_context(source, [{"kind": "fragment", "value": target["stage_text_fragment_id"], "side": "right"},
                                      {"kind": "mark", "value": "https://outside.invalid", "side": "both"}])
    assert result[0]["matches"][0]["content_key"] == target["content_key"]
    assert result[0]["matches"][0]["profile_id"] == target["page_profile_id"]
    assert result[1]["status"] == "not_found"


@pytest.mark.parametrize("requests", [
    [{"kind": "file", "value": "/etc/passwd", "side": "both"}],
    [{"kind": [], "value": "x", "side": "both"}],
    [{"kind": "rows", "value": "x\ncommand", "side": "both"}],
    [{"kind": "rows", "value": "x", "side": "both"}] * 2,
    [{"kind": "rows", "value": str(n), "side": "both"} for n in range(7)],
])
def test_invalid_context_request_is_rejected_before_lookup(requests):
    group = build_source_groups(snapshot())[0].review
    plan = with_loop(build_review_requests(group, model="recorded")[0])
    with pytest.raises(StageAiValidationError):
        final_document(plan, {"output_text": {"group_id": plan.group_id, "chunk_id": plan.unit_key,
            "source_sha256": plan.source_sha256, "decisions": [], "context_requests": requests}})
