# W53-JUDGE-Y — independent invariant and recoverability review

Assigned base: `f0b1a0ede0c6edb90d4d0072429cb95b28e7a945`.
Branch: `agent/w53-judge-y`. Review is independent of implementation and uses only
the granted report path. The exact handback HEAD is supplied to the integrator
after this report is committed, since a commit cannot contain its own SHA.

## Findings under review

### Y-01 — proposed S3 restore does not read the upgraded source

`scripts/rehearsal/w53/minio_upgrade.py:187–190` reads the new image's versioned
objects into a manifest, then starts an empty old-image restore volume and
replays the original in-process `payloads` fixture to it. A successful `--full`
run would therefore prove that the old image can re-write known fixture bytes;
it would not prove that data exported from the upgraded image can be restored.
The script was only run with `--old-only`; no new-image or restore PASS exists.
The integrator has issued `W53-REHEARSAL-REPAIR-01` for the exact source/export
proof. This finding is an evidence defect, not a claim of lost product data.

### Y-02 — recovery outcome changes omit journal entries — confirmed

`JobRepository.reclaim_expired` (`src/auditmanager/jobs/repository.py:381–388`)
directly changes a prepared provider effect to
`outcome_unknown` without `append_execution_event`. The bulk
`_SETTLE_TERMINAL_PROVIDER_EFFECTS` statement at lines 205–231 changes prepared or
response-received effects to `abandoned` with no event either. Both happen in
ordinary recovery paths. W53's frozen plan requires provider outcomes in the
same transaction as the state change and one journal event per transition.
`process_recovery.py` checks ordering of two earlier events and counts all
events; it does not assert a one-to-one mapping for reconciliation outcomes.
Severity: acceptance blocker for journal completeness. A focused disposable
database probe on migrated `0017_execution_queue` set a prepared effect's
state to `outcome_unknown` through `reclaim_expired` and counted **zero**
matching `provider.outcome_unknown` audit events. Its lease recovery count was
one. Stage-C's earlier process log separately observed
`response_received → abandoned` with `settled=1`; the settlement SQL has no
append operation. Repair must append one safe event for each changed effect
in the same transaction, including the bulk settlement path.

### Y-03 — queue cursor loses items after priority mutation — confirmed

`ExecutionRepository._QUEUE` (`src/auditmanager/execution/public.py:40–63`)
resolves a cursor's sort coordinates by reading
the current Job row. The same Job's priority and state are mutable. If page 1
returns queued A at priority 100 while B remains at 90, then an administrator
lowers A to priority 0, page 2 after A queries for priority below 0 and omits B.
The existing test covers a new row inserted between pages, not an anchor
mutation. The query also sorts equal-priority queued Jobs newest first while
the dispatcher claims oldest first. Severity: user-visible loss of queue items
while paging and misleading order. A private two-session probe returned A on
page 1; after A's priority changed from 100 to 0, page 2 with A as cursor
returned `[]` and omitted still-queued B at priority 90. B's exact identity
and the empty result are in the hashed probe log.

### Y-04 — the public journal omits global pause/resume audit events

`jobs.commands.set_execution_paused` (`src/auditmanager/jobs/commands.py:54–60`)
appends
`execution.dispatch_paused_changed` with aggregate type `CommandRecord` and
actor identity. `execution.public._JOURNAL_ALL` includes only `AuditRun`, `Job`
and `Attempt` (`src/auditmanager/execution/public.py:73–102`), so no public
journal page can show that event. The frozen
`ExecutionJournalEntry` requires a `run_id`, while pause applies to all Runs
and has none. W53's plan says the control actor is in the journal and live
acceptance shows each step. The contract's exact intended scope is ambiguous:
including global command events would require a reseal allowing absent
`run_id`, plus API/client/UI/query changes; excluding them requires an explicit
plan and acceptance correction. An arbitrary Run identity must not be made up.

### Y-05 — ALR-05 guard fails on three deep imports

The exact-base architecture test failed: `1 failed, 1 passed` in 0.29 s.
Deep imports are `api/app.py:309 → runs.carrier`,
`jobs/repository.py:338 → runs.repository`, and
`runs/executor.py:113 → jobs.lease`. The boundary requires a context's
`public` module. Command:
`/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q
tests/contract/architecture/test_alr05_boundaries.py`.
Evidence: `/tmp/w53-judge-y/alr05.log`.

### Y-06 — cross-run lock inversion deadlocks concurrent reclaim sweeps — confirmed

`JobRepository.reclaim_expired` takes Run→Job→Attempt→Lease per candidate but
holds those locks across up to 100 candidates in one transaction. The periodic
sweep uses lease expiry order; the watchdog sweep promotes its forced Attempt
to the front (`jobs/repository.py:49–57`). For two expired Runs A and B, one
sweep can lock A then B while the forced watchdog for B locks B then A. This is
a PostgreSQL deadlock across Runs even though each Run's internal lock order is
correct. A coordinated two-connection probe confirmed opposite candidate
orders, synchronized both sessions after their first Run lock, and observed
periodic sweep `OperationalError:40P01` while the watchdog sweep committed
two recovered Runs. Both threads exited. The repair must impose a stable
cross-Run batch order or use independent bounded transactions per candidate,
and must test the periodic/forced overlap. A 2-second lock timeout is not a
substitute for a deterministic order.

## Verified limits and further checks

- Frozen OpenAPI SHA-256 is
  `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`;
  state-machine SHA-256 is
  `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
- The prior Stage-C logs' bytes match their reported SHA-256 values for
  `process-recovery.log`, `proxy-faults.log` and `old-minio-versions.log`.
  Their own assertions support only the stated disposable observations.
  The recovery log observes `response_received → abandoned` and `settled=1`;
  its `journal_events=21` is a count, not a one-to-one assertion.
- Before the private DB/S3 launch at 2026-10-09 13:46:11 UTC,
  `df -B1 . /var/snap/docker/common/var-lib-docker` showed
  **11,145,834,496** available bytes on the same filesystem. The run used
  prebuilt images (no image build); a credible bound below 1 GiB plus 2 GiB
  margin fitted. At 13:48:00 UTC 10,995,216,384 bytes remained. The five
  reserved ports were clear before launch.
- Private images were PostgreSQL
  `sha256:4c34fc74b2e596ec32e40006f009025895afc520b083635e969c3526c48827f6`
  and old MinIO
  `sha256:d06b201c2490dfe8e98e03d29c5ee1de070d8cebec89d6d89e12850024077a28`.
  Both containers carried `auditmanager.lane=gate-w53judge-y`; the database
  reported `0017_execution_queue`. The new pinned MinIO image was never used.
- Disposable probe source: `/tmp/w53-judge-y/probe.py`, SHA-256
  `1759a4a36707da765092906a75de3e4e0acf04f8fb13466f976dd6383877b03f`.
  Output: `/tmp/w53-judge-y/probe.log`, SHA-256
  `a9ec0aa9f1f5068b6549b30b7951709bc461a0be9c4ff257028698251613a074`.
  Alembic log SHA-256
  `a0d302093da343bda890db0d31976107ca602b4f21e9fa44264fa61eed79c036`.
  The ALR-05 log SHA-256 is
  `c146c92512b0361cae7b335fbc681d1ac0a7c8b9db5fd0f964ed0d964675e7af`.
  Commands were `PYTHONPATH=src python -m alembic --config
  db/migrations/alembic.ini upgrade head`, `PYTHONPATH=src python
  /tmp/w53-judge-y/probe.py`, and the focused pytest command cited above,
  with the repository's pinned `.venv/bin/python` executable.
- After evidence capture, only `gate-w53judge-y-pg`,
  `gate-w53judge-y-s3` and their named volumes were removed. `docker ps -a`
  and `docker volume ls` with that lane filter returned no resources; all five
  reserved ports were clear. The mode-0600 disposable credential file was
  deleted. No working-stand resource, shared cache or image tag was touched.
- The payload key allowlist contains identity and bounded classifier keys;
  inspected call sites do not place non-identity model names, request IDs,
  idempotency keys, paths, prompts or credentials in event payloads.
- Within one Run, inspected Run/Job/Attempt/Lease writers take Run before Job
  before Attempt before Lease when they need more than one lock. Lease heartbeat
  touches only its lease. The confirmed Y-06 inversion is between Runs in one
  multi-candidate transaction.

## AGENTS.md §5 handback

1. Changed files: this report only.
2. Checks/results: focused ALR-05 **1 failed / 1 passed**; private migrated
   queue/journal/deadlock probe produced all three counterexamples; frozen
   SHA-256 values and Stage-C log hashes matched; `git diff --check` passed.
3. Contracts: none changed.
4. Risks: Y-01–Y-06; own-proxy 503 and `validating` cancellation remain the
   separately recorded `W53-EXEC-STOP-01`/`02` conditions.
5. Integrator: issue exact repair grants, then independently repeat the
   affected checks before final gate; preserve the old-image-only limitation.
6. Forbidden hotspots: the base-to-handback changed-path audit contains only
   `docs/program/W53-JUDGE-Y.md`; no product, contract, migration, image,
   release, dependency, composition, global-style, ref or tag path is changed.
   The clean branch, path audit and exact HEAD are read back after commit.
