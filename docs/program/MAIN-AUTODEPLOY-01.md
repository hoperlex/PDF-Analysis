# MAIN-AUTODEPLOY-01 — documentation handoff

**task_id:** `MAIN-AUTODEPLOY-01`
**base:** `3489378ab8e916876688045085b51618d19d20b8`
**date:** 2026-10-01

## Result

`origin/main` is documented as an external deployment boundary once the owner enables the GitHub
workflow. Push authority, pre-push evidence, post-push verification, serialization, rollback and
secret handling are explicit and fail closed. The temporary alpha URL is recorded only as dated
reachability evidence, never as proof of a deployed revision.

## Changed files

- `AGENTS.md`
- `docs/program/MAIN_AUTODEPLOY_POLICY.md`
- `docs/program/tasks/MAIN-AUTODEPLOY-01.md`
- `docs/program/MAIN-AUTODEPLOY-01.md`

## Verification

- `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py -q` — **47 passed**;
- `git diff --check` — exit `0`;
- policy/reference `rg` — the mandatory `AGENTS.md` pointer, main boundary and
  `verify-deployed.sh` post-push proof are all present.
- point-in-time origin probe — valid TLS; `/` returned `307` to `/projects`; protected
  `/api/v1/openapi.json` returned `401`.

## Contracts

No API, domain, event, generated-consumer or migration contract changes. No workflow,
composition, dependency, deployment script or runtime file changes.

## Risks and known limitations

- The owner is still implementing the GitHub workflow; this task cannot establish its trigger,
  permissions, concurrency or secret scopes.
- The public URL observation is point-in-time and intentionally does not name a deployed SHA.
- `docs/program/CURRENT_STATE.md` is concurrently owned by `NORM-ADR-01` and was not touched.

## Integrator instruction

Keep these four documentation paths together. Do not infer that auto-deploy exists merely from
this policy: review the workflow bytes and drive its first run independently. No forbidden
hotspot was touched.
