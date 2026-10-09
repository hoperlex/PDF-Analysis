# W53-EXEC-01 — executor handback

Base: 6b110c9478c301a9b1436c589803a639124647d6. Branch: agent/w53-exec-01. The exact repaired HEAD is reported to the integrator after commit.

## 1. Changed files

The complete changed-path audit from base to the repaired HEAD is:

- docs/program/W53-EXEC-01.md
- src/auditmanager/analysis/text/adapter.py
- src/auditmanager/analysis/text/proxy.py
- src/auditmanager/analysis/text/stage.py
- src/auditmanager/api/app.py
- src/auditmanager/bootstrap/adapters.py
- src/auditmanager/bootstrap/composition.py
- src/auditmanager/execution/__init__.py
- src/auditmanager/execution/public.py
- src/auditmanager/jobs/commands.py
- src/auditmanager/jobs/events.py
- src/auditmanager/jobs/lease.py
- src/auditmanager/jobs/public.py
- src/auditmanager/jobs/repository.py
- src/auditmanager/runs/__init__.py
- src/auditmanager/runs/carrier.py
- src/auditmanager/runs/commands.py
- src/auditmanager/runs/executor.py
- src/auditmanager/runs/reconciliation.py
- src/auditmanager/runs/repository.py
- tests/integration/analysis_text/test_proxy_adapter.py
- tests/integration/composition/test_the_run_leaves_the_request_thread.py
- tests/integration/runs/test_durable_effect_boundaries.py
- tests/integration/runs/test_w53_execution.py

## 2. Checks and results

A fresh isolated PostgreSQL database migrated to 0017_execution_queue. The serial focused API contract, proxy, run, fault, command, race and composition suite passed 239 tests in 33.36 seconds; log: /tmp/w53exec-final-focused.log. Subsequent targeted checks after the final journal and validating-cancel changes passed: 10 tests in the W53 execution suite (/tmp/w53exec-newdb.log), 2 journal tests (/tmp/w53exec-journal.log), and 1 validating-cancel test (/tmp/w53exec-validating.log). Python compileall and git diff --check passed. Disk preflight reported more than 12 GB available before costly runs. The integrator owns the full make gate.

## 3. Contracts

No contracts or migrations changed. Frozen OpenAPI SHA-256: 008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193. Frozen state-machine SHA-256: cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466. Migration head remains 0017_execution_queue.

## 4. Risks and known limitations

No measured own-proxy 503 discriminator exists in the frozen input. Every 503 remains outcome_unknown with no replay; see the integrator's W53-EXEC-STOP-01. The frozen graph has no validating-to-cancelled edge. Cancellation there is refused without changing Run, Job or Attempt; see W53-EXEC-STOP-02. A dispatch pause is audited under CommandRecord in audit_event with the actor identity; the sealed public execution journal requires a Run ID, so this global event is outside that API. Active carrier drain waits for all nonterminal Jobs in the database, including Jobs accepted by another process; it is a test/admin wait and is not called by the request path.

## 5. Instructions to the integrator

Review the clean repaired commit and exact path audit, cherry-pick its HEAD onto the integration SHA, then run independent QA and the full gate on a clean exact candidate. Keep the own-proxy 503 and validating-cancel stops open until an owner decision or exact repair grant. No agent ref or tag was published and no working stand was used. The assigned disposable PostgreSQL and S3 containers and ignored local .env were removed at handback.

## 6. Forbidden-hotspot proof

The path list above contains only this repair-granted handback and W53-EXEC-01 source/test allowed paths. It contains no docs/program/tasks file, contracts, migrations, root dependency or lockfile, global styles, generated client, MinIO, backup, VERSION, release notes, publication refs or working-stand file. The frozen hashes in item 3 were checked after implementation.
