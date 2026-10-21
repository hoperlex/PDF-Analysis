# W56A-INT-V2-PUBLICATION-PREP-01 — result

The additive `publish_v2_merge_plan` writes each validated AR v2 merge group as one finding with all member observations and their PDF evidence. It stores each member's proposed severity and sets the group's canonical observation through the 0022 composite FK in the same savepoint. Rejected proposals are returned as diagnostics without any identity allocation or database row. The caller owns the outer transaction; this module does not commit, activate a runtime stage or write an expert verdict.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/findings/test_v2_publication_sql.py`: **10 passed**. The fake session checks the ordered 10-statement two-group write, bound member/evidence/provenance fields, canonical IDs, no rejected inserts, savepoint rollback, SQLSTATE mapping, failed canonical update and pre-write validation.
- Combined publisher, planner and merge-core suite: **37 passed**.
- `../../../.venv/bin/python -m py_compile src/auditmanager/findings/v2_publication.py tests/integration/findings/test_v2_publication_sql.py`: passed.
- Task governance (`governance_findings`): `[]`; whitespace scan of the four owned files: no trailing whitespace; `git diff --check`: passed.
- Isolated PostgreSQL acceptance and full `make gate`: deferred under `R-135`; no database acceptance or beta claim.

## Contracts and limits

No contract, migration, provider lock, existing v1 publication, executor, composition root, dependency file or global style changed. The only new files are the additive publisher, its fake-session test, this report and its exact task file. The module is not exported by `findings.public` or wired into a run.

The trusted caller must pass a plan produced by `plan_v2_merge_publication` after `finish_response`. The publisher checks structural invariants but cannot prove the merge rule or PDF grounding from a hand-built dataclass. Provenance identity types and `recorded`/`live` provider mode are checked before opening the savepoint. Run-level idempotency, true PostgreSQL constraints/trigger behavior and transaction integration still require a separately owned runtime/DB task. This module currently imports AR v2 profile internals; the integrator has reserved a separate boundary facade task for that dependency.

## Integration instruction

First add a public AR v2 profile boundary for the typed plan and enum access. Then wire the publisher only after the grounded planner output is available, and run an isolated PostgreSQL test against migration head `0022_findings_v2`. Keep the v1 `publish_gate_result` path unchanged. The four task-owned files are additive and can be removed before runtime wiring to roll back this preparation.
