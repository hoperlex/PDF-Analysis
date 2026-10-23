"""The read-only web preview mirrors the frozen backend beta policy and six scopes."""

from __future__ import annotations

import json
from pathlib import Path

from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership


ROOT = Path(__file__).resolve().parents[3]
SERVER = ROOT / "src/auditmanager/analysis/profiles/ar_v3/norm_map/beta_sources.json"
WEB = ROOT / "web/src/widgets/ar-v3-beta-status/ui"


def test_web_policy_is_byte_identical_and_scopes_are_total() -> None:
    server = SERVER.read_bytes()
    assert (WEB / "beta_sources.json").read_bytes() == server
    policy = json.loads(server)
    groups = json.loads((WEB / "scope_groups.json").read_text())
    titles = json.loads((WEB / "topic_titles.json").read_text())
    assert policy["scenario"] == "new_multi_apartment_residential_F1.3"
    assert policy["numeric_output_policy"] == "expert_review_required"
    assert tuple(group["id"] for group in groups) == ("F1", "F2", "A1", "A2", "S1", "S2")
    expected = tuple(f"C{number:02d}" for number in range(1, 23))
    assert tuple(item["id"] for item in policy["items"]) == expected
    assert tuple(titles) == expected
    assert tuple(item for group in groups for item in group["items"]) == expected
    for group in groups:
        membership = scope_membership(group["id"])
        assert tuple(group["items"]) == membership.item_ids
        assert policy["composition_sha256"] == membership.composition_sha256
    assert sum(item["mode"] == "provisional_citation" for item in policy["items"]) == 14
    assert sum(item["mode"] == "context_only" for item in policy["items"]) == 8
