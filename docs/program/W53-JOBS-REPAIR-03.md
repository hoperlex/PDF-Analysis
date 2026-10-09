# W53-JOBS-REPAIR-03 — atomic pause claim and effect history

Assigned branch `agent/w53-jobs-repair-03`, exact base
`a958f532267254369cae2f32ec551fd4956e9846`. The integrator reads back
the committed handback SHA because this report cannot contain its own commit.

## Repair and boundaries

`start_execution` now ensures and locks the singleton control row before it
locks Run → Job and creates Attempt authority. The insert also serializes the
initial absent-row race against an administrator's pause upsert. A pause already
committed is refused with `CONFLICT`; a pause that arrives after a claim waits
for that transaction and applies to later claims.

The forced watchdog sweep now selects only its named Attempt. Periodic reclaim
orders candidates by Run ID, so two periodic sweeps acquire cross-Run locks in
one order while a forced sweep cannot hold a different Run and invert the
order. The 100-row periodic bound remains; later sweeps take remaining eligible
rows. Each prepared provider effect changed to `outcome_unknown` by reclaim
gets one safe `provider.outcome_unknown` event in the mutation transaction.
Each effect changed to `abandoned` by terminal settlement gets one safe
`provider.abandoned` event in that transaction. Repeated sweeps emit none.
Events use the effect's actual Run and Attempt identities and allowlisted state
classifiers only; no model text, response, prompt, key, path or credential is
copied into the journal.

## Verification

Frozen OpenAPI SHA-256:
`008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
Frozen state-machine SHA-256:
`cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
The private database migrated to `0017_execution_queue`.

At 2026-10-09 13:55:53 UTC, `df -B1 .
/var/snap/docker/common/var-lib-docker` showed 10,733,735,936 bytes free on
the same filesystem and `ss` showed ports 56950/60550/60551 unbound. The
test lane used already-local PostgreSQL
`auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9` and old MinIO
`auditmanager-minio:RELEASE.2025-09-07T16-13-09Z-07c3a42`. Its expected
incremental peak was below 1 GiB plus a 2 GiB margin; no image build or shared
cache action was used. Preflight log
`/tmp/w53-jobs-repair-03/preflight.log` SHA-256
`d0a0a5190ead57225c1f28442202ad93ab4ef0056f8dd99275546e47ca842259`.

On a fresh private 0017 database, the unchanged independent pause and two
effect-journal QA tests plus two real two-connection regressions passed **5/5**.
One regression removes the initially absent control row, holds a claim while a
concurrent pause waits, then confirms the committed pause refuses the next
claim. The other coordinates periodic and forced recovery after opposite first
Run locks, verifies both transactions commit without PostgreSQL `40P01`, and
checks both Runs' final Job/lease states. Command:
`PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q
tests/integration/runs/test_w53_jobs_repair.py
tests/integration/qa_w53/test_queue_and_effect_journal.py::test_pause_between_hint_and_claim_refuses_new_authority
tests/integration/qa_w53/test_queue_and_effect_journal.py::test_lease_reclaim_journals_the_effect_outcome
tests/integration/qa_w53/test_queue_and_effect_journal.py::test_terminal_effect_settlement_journals_abandonment`.
Log `/tmp/w53-jobs-repair-03/qa-concurrency-final-2.log` SHA-256
`8376d3323faccbacb6ce46a1b2d6848f70989bb8a28aabe1af2ce9fcfe3e6c6e`.
Migration log SHA-256
`a0d302093da343bda890db0d31976107ca602b4f21e9fa44264fa61eed79c036`.

The full focused `test_w53_execution.py` and
`test_durable_effect_boundaries.py` files passed **29/29** on a freshly reset
private 0017 database. Their strengthened assertions require two reclaim
events for two changed effects, no event on repeat reclaim, one settlement
event for either prepared or response-received state, and no event on repeat
settlement. Command:
`PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q
tests/integration/runs/test_w53_execution.py
tests/integration/runs/test_durable_effect_boundaries.py`.
Log `/tmp/w53-jobs-repair-03/focused.log` SHA-256
`5aac96dc66464f719499c233058e71180d48c836e51329f4a8b3ae77ffacc3d6`.
ALR-05 architecture guard passed **2/2**:
`/tmp/w53-jobs-repair-03/alr05.log` SHA-256
`4de64934605dc63b561f8b2a59ff4a7fa10d1068e8dfcae0f632ddefa3a3b684`.
`git diff --check` passed. The first small probe caught a PostgreSQL untyped
NULL in the new query; the final query casts the parameter and the fresh
database run above is green. A second probe reused committed data from that
first probe; only the lane-owned database was reset before final checks.

## AGENTS.md §5 handback

1. **Changed files:** `src/auditmanager/jobs/repository.py`,
   `tests/integration/runs/test_w53_execution.py`,
   `tests/integration/runs/test_durable_effect_boundaries.py`,
   `tests/integration/runs/test_w53_jobs_repair.py`, and this report.
2. **Checks/results:** migrated private 0017 database; independent QA plus
   concurrent regressions 5/5; focused execution/effect suites 29/29; ALR-05
   2/2; frozen hashes and `git diff --check` match. Logs and hashes above.
3. **Contracts:** no API, domain, migration, event schema, dependency or
   external contract file changed. The existing journal projection now records
   two previously omitted provider outcomes.
4. **Risks/limits:** global control-row locking serializes concurrent claim
   transactions; only a measured throughput need would justify a later design
   change. The 100-row periodic sweep may need another invocation to recover
   later candidates. Global pause's public-journal scope remains the separate
   owner question; no MinIO upgrade, release decision or full gate is claimed.
5. **Integrator:** audit this clean branch against the exact base, cherry-pick
   only these five paths, then independently repeat the three unchanged QA
   cases, two-connection regression and ALR-05 guard on the merged SHA.
6. **Forbidden hotspots:** base-to-handback `git diff --name-only` contains
   only the five granted paths listed in item 1. Independent `qa_w53` tests
   are unchanged. No contract, migration, composition root, router, UI,
   dependency/lock, global style, queue, proxy, release, backup, deployment,
   tag or published ref was touched. The private `gate-w53jobs` containers and
   named volumes were removed, credential file deleted, lane ports are clear;
   the working stand was never used.
