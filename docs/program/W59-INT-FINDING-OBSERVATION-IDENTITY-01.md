# W59-INT-FINDING-OBSERVATION-IDENTITY-01 — result

Base: published dev63 `417123c729599cfa075d3461038c8dd15b86d4a3`.

The unserved exact finding matcher now refuses a source and target observation
with the same `finding_observation_id`. The guard runs after each version's
existing identity, Run and evidence validation and before any suggestions are
built. A `finding_observation_id` is a primary key in the existing schema, so
the same ID cannot identify two observations in distinct versions. Valid
distinct IDs keep the same exact-match result and digest.

## Checks

- Red regression before the source fix: the reused-ID case failed because the
  matcher returned a suggestion; the distinct-ID case passed.
- Focused finding-match, carryover and raw-evidence-seal suite after the fix:
  **40 passed**.
- Python compilation, direct task governance, frozen SHA-256 readback,
  allowed-path handoff and `git diff --check`: passed at commit.
- No DB/S3, provider, network, Docker or complete gate; R-135 defers the
  complete beta gate.

## Contracts and limitations

No contract, migration, API, run, active profile, corpus or persisted matching
state changed. The caller still must load complete published findings of one
source Run and one target Run under an authoritative comparison snapshot. The
pure suggestion does not approve a match or carry an expert verdict.

## Integration handoff

Integrate only the four owned paths. The new internal refusal reason is
`finding_observation_identity_crosses_versions`. Keep the matcher unserved
until the W59 comparison owner seals approved links, source custody and expert
approval. Reverting the source commit removes this preflight; no data rollback
or feature flag is needed.

Changed paths:

- `src/auditmanager/comparison/finding_match_suggestions.py`;
- `tests/integration/comparison/test_finding_match_suggestions.py`;
- `docs/program/tasks/W59-INT-FINDING-OBSERVATION-IDENTITY-01.md`;
- this report.

The forbidden hotspots, including `contracts/**`, `db/migrations/**`, other
comparison modules, served API/UI, root dependencies/locks, composition root,
global styles, `CURRENT_STATE.md`, refs and tags were not edited.
