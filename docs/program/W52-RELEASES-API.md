# W52-RELEASES-API — release backend and loader hand-back

**Base:** published Stage-C grant
`3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551` on `origin/dev`.
**Lane:** `agent/w52-releases-api`. No origin ref, tag or deployed stand was
changed by this lane.

## 1. Changed files and result

The release port now serves `VERSION=0.3.0`, a content-derived API
`build_id`, database-backed history and the account's monotone mark. The
loader reads only known top-level JSON entries, validates the checked-in
shape, applies authored revisions transactionally and leaves future database
releases hidden on rollback. `whats_new` is computed in the release context
from the database's account and first-load clocks.

Exact changed paths:

```text
VERSION
release-notes/schema.json
release-notes/0.3.0.json
release-notes/0.2.0.json
src/auditmanager/releases/public.py
src/auditmanager/releases/notes.py
src/auditmanager/releases/repository.py
src/auditmanager/releases/load.py
src/auditmanager/bootstrap/adapters.py
src/auditmanager/bootstrap/composition.py
infra/deploy/Dockerfile.api
infra/deploy/compose.server.yml
infra/deploy/deploy.sh
infra/deploy/reset.sh
infra/deploy/README.md
tests/integration/releases/conftest.py
tests/integration/releases/test_build_id.py
tests/integration/releases/test_release_loader.py
tests/integration/releases/test_startup.py
tests/integration/releases/test_deployment_flow.py
tests/integration/api/test_release_routes.py
tests/integration/composition/test_deployed_stack_probe.py
tests/integration/composition/test_session_register_volume.py
docs/program/tasks/W52-RELEASES-API.md
docs/program/W52-RELEASES-API.md
```

## 2. Checks

- `tests/integration/releases` plus the sealed API route test against the
  isolated `gate-w52r` PostgreSQL: **57 passed**. This includes loader rules
  1–4, equal and bumped revisions, rollback visibility, high-water marks,
  first-load `whats_new`, startup refusal, schema parity, Docker ignore and
  deploy/reset order.
- The five granted composition suites: **151 passed, two expected-set
  failures** on the first permitted run. They were the exact Dockerfile COPY
  and compose service inventories, both updated; their two focused reruns
  **passed**. Four MinIO image/order tests also passed.
- API/domain/architecture/governance contract group: **336 passed**.
  `npm --prefix web run api:verify`: 37 operations, exit 0. Frontend lint
  and typecheck: exit 0. Python compilation, shell syntax and
  `git diff --check`: exit 0.
- A real local API image built successfully. Checkout and image both returned
  `0.3.0 bf2911c95fd08cc69`. Image startup built 37 routes. Its one-shot
  loader inserted two entries on the first run and reported two unchanged
  entries on the second. Normalized compose config gives
  `migrate → release-notes → api`.
- The first unprivileged deploy-script test run had socket-permission setup
  errors; the permitted rerun supplied the 151-pass result above. No full
  `make gate`, QA, built-stand acceptance or release verdict is claimed;
  those remain D-137–D-140.

## 3. Contracts

No API/domain contract, generated client, error catalog, migration, migration
head or `contract_version` changed. The Stage-B surface remains
30 paths / 37 operations / 83 schemas, head `0016_release_notes`.
`release-notes/schema.json` is the new file-shape contract and is checked
against the sealed `ReleaseNoteItem` and `ReleaseNoteKind` components.
`VERSION` is the product-version source; root package manifest versions
remain placeholders.

## 4. Risks and limits

`0.3.0.json` and the archive are minimal Stage-C entries. Stage C2
`W52-RELNOTES` still owns substantive, diff-grounded release prose and its
judge. The API build identifier excludes Dockerfile-only and
`infra/deploy/serve.py`-only edits by W52 design; this remains a registered
release-validation limit. The restore path reports a failed post-restore
loader instead of undoing already restored data, as the reset safety policy
requires. No full gate or live deployment has been run on this branch.

## 5. Integrator instruction

Review the exact 25-path diff and the narrow grant correction below, run
focused checks on the merge candidate, then merge this clean lane before
`W52-RELEASES-WEB` and `W52-TRANSLATE-01`. The docs and image notes are
placeholders until Stage C2. The next Stage-C grants require a fresh
current-tree sweep. Only an integration task may publish a checked candidate
to `origin/dev`; `origin/main` still requires the owner's separate direct
exact-SHA instruction.

## 6. Forbidden-hotspot proof

Every path in §1 is in the published task's grant except
`tests/integration/api/test_release_routes.py`, whose Stage-B test
instantiated the removed zero-argument placeholder. The exclusive
integrator added that one test path and the task file itself to
`docs/program/tasks/W52-RELEASES-API.md` before editing the test. The test
now asserts the Stage-C adapter's version and visible-history response.
No `contracts/**`, `db/migrations/**`, root dependency/lock, generated
client, web UI, global style, unrelated test or deployed stand changed.
No checkpoint or tag was created.
