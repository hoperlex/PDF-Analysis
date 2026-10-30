from auditmanager.analysis.extended.coverage import (
    coverage_policy,
    plan_extended_coverage,
    validate_coverage_policy,
)


def test_statistics_mode_plans_all_observation_batches() -> None:
    items = [
        {"title": f"item {index}", "description": "review", "source_ids": ["page-1"]}
        for index in range(200)
    ]
    policy = coverage_policy(unbounded_stats=True)
    assert validate_coverage_policy(policy)
    limited = plan_extended_coverage(kind="finding_review", items=items, limit=8)
    complete = plan_extended_coverage(kind="finding_review", items=items, limit=None)
    assert limited["pending_items"] == 40
    assert complete["pending_items"] == 0
    assert len(complete["batches"]) == 10
