# W53-GATE-QUERY-REPAIR-01 handback

Base: `8d94517e30c91564557d1f30ba98cd76cd559c62`. Branch: `agent/w53-gate-query`.
The grant closes only the exhaustive query guard failure from the first full gate.

## 1. Changed files

- `tests/integration/api/test_query_surface.py` — added the two W53 operations to both
  exact OpenAPI set assertions; drove queue `limit`/`cursor` and journal
  `limit`/`cursor`/`run_id` through ASGI over the shipped `ExecutionAdapter`, with three
  distinct rollback-isolated Run/Job records and their real journal events.
- `docs/program/W53-GATE-QUERY-REPAIR-01.md` — this handback.

## 2. Checks and results

- Before starting services, ports `56921`, `60522`, `60523` were free. At
  `2026-10-09T14:46:07Z`, the worktree and Docker data root shared `/dev/vda3` with
  `8,540,463,104` bytes available. Cached images and a new disposable DB/S3 pair
  gave an estimated incremental peak below 2 GiB, with more than 3 GiB spare.
- `make up` and `make migrate` succeeded on only `gate-w53query`; Alembic reached
  `0017_execution_queue`.
- `.venv/bin/python -m pytest -q tests/integration/api/test_query_surface.py`:
  **29 passed**, one upstream Starlette deprecation warning. Complete log
  `/tmp/w53-query-green.log`, SHA-256
  `88c1941a4413eec0f772e05f55f04f1edfff27dd3977c1ff445a074c17ab9139`.
- Temporary `/tmp/w53_query_mutation.py` changed only the in-process adapter call.
  Ignoring queue `cursor` made the totality test fail with
  `{'listExecutionQueue': ['cursor']}` (exit 1; log SHA-256
  `d0d7ee736c13953d947e48e21d7a866de8fab436f6ea7a7af0f17bc665f5c6d1`).
  Ignoring journal `run_id` failed with
  `{'listExecutionJournal': ['run_id']}` (exit 1; log SHA-256
  `7925627e6aaccd5b06bb81dce579d6fcc60c6fe09714144fc476e09ad1a89f6a`).
  Production and contract files were never edited for these probes.
- `git diff --check` passed.

## 3. Contracts

No contract changes. OpenAPI SHA-256 remains
`008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`;
state machine SHA-256 remains
`cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
The frozen API version remains `1.0.0-draft.1` and migration head is
`0017_execution_queue`.

## 4. Risks and limits

The W53 read checks use the real `build_execution_routes` declaration and shipped
`ExecutionAdapter` with the suite's credential port and rollback-bound session factory.
Only the two GET operations are exercised on that small ASGI surface; the adapter's
`runs` argument is unused by those reads. The other declared query operations retain
the existing full `shipped_router` fixture. This task supplies no full-gate verdict.

## 5. Integrator instructions

Cherry-pick the branch commit onto the W53 integration candidate. Recheck both exact
set assertions and the full owned module in the final private gate lane. The first
gate's other three failures have separate repair grants.

## 6. Allowed-path audit

The exact base-to-HEAD changed paths must be checked with
`git diff --name-only 8d94517e30c91564557d1f30ba98cd76cd559c62 HEAD`.
The result is the two files in §1 only. No `contracts/**`, migration, production,
composition, root dependency/lock, global style, working-stand or publication path
was changed. No ref was pushed and no tag was created.
