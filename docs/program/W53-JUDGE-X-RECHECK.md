# W53-JUDGE-X-RECHECK — independent final X verdict

Branch `agent/w53-judge-x-recheck`, exact assigned base `4f9db3af870b5a94fafec8bdba40f49456c86f44`. The verdict below concerns only the repaired X/security boundary on this candidate. No Docker lane, working stand, provider endpoint, ref or tag was used.

## 1. Changed files

Only this report, `docs/program/W53-JUDGE-X-RECHECK.md`. No product or test file was edited.

## 2. Checks and evidence

Frozen API OpenAPI SHA-256 is `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`; domain state-machine SHA-256 is `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`. Both match the task. The task's `0017_execution_queue` migration head was not changed by this report. These checks are pure and build no image or substantial disk data, so AGENTS.md §8's heavy-run preflight was not invoked.

| Check on this exact worktree | Result | Log SHA-256 |
| --- | --- | --- |
| `PYTHONPATH=src .../python -m pytest -q tests/contract/architecture/test_alr05_boundaries.py` | 2 passed | `/tmp/w53-judge-x-recheck-alr05.log`: `87b1ffae008cb01b1cb73d443fc6366001240a196a4124ad7aea5b0a001096d6` |
| `PYTHONPATH=src .../python -m pytest -q tests/integration/qa_w53/test_proxy_refusal_boundary.py` | 2 passed | `/tmp/w53-judge-x-recheck-proxy-qa.log`: `cdf8d13a3f141b449c7d92c9b86d6fd681de17445a1d661236b92f93860eafac` |
| `PYTHONPATH=src .../python -m pytest -q tests/integration/analysis_text/test_proxy_adapter.py` | 89 passed | `/tmp/w53-judge-x-recheck-proxy-baseline.log`: `2a735c3209a767bf5c3003de3e74eb21b0bf80b10153221a745b4c3b0fa897f8` |
| Independent replay of X's arbitrary-prose foreign-503 example | `outcome_unknown`, `retry_safe=False`, message says outcome unknown, no body/private marker in warning | `/tmp/w53-judge-x-recheck-own-probe.log`: `33754e6f9c329aa5c209aefb7c9312d66bac0cc0b694773007bf6ebf39c77ba6` |
| Fresh interpreter imports `jobs.public → runs.public → api.app` and reverse | Both passed | `/tmp/w53-judge-x-recheck-imports.log`: `8f82f6d8de79227fefa958e826632f70961c8ac8479dd682887c9e8c86d6a2ca` |

I read and verified the integrator's combined QA/concurrency log `/tmp/w53-int-qa/combined.log` SHA-256 `fb788e63b37c86f64a2f090a4bcf10d801197fb07d84e8cf7ae7c96354ded360` (**23 passed**), the Job-repair concurrency log `/tmp/w53-jobs-repair-03/qa-concurrency-final-2.log` SHA-256 `8376d3323faccbacb6ce46a1b2d6848f70989bb8a28aabe1af2ce9c6e` (**5 passed**), and the queue test repair's two complete orders, SHA-256 `c60c39fcd4c8cf695a22c32c63a1c0cb589c06594ebebeedb535f872ac62d51c` and `cd9f3293cfbe864926b41b6dfe69be33503f3a4fd80cecaba98e4adaba043d26` (**23 passed each**). These are other lanes' database results, not new Judge X live-service evidence. The diff from the integrated `23/23` source SHA `c65d3a30c014aaa029b558ad04f72e282de37dd9` to this assigned base changes only QA report, port registry and judge task files; product source is identical.

### Verdict against the prior X findings

| Finding | Verdict | Reason |
| --- | --- | --- |
| X-01: arbitrary proxy response body in service log | **PASS** | `_map_http_failure` now logs only numeric status and truncation. The old private-prose reproducer is absent from warning and envelope. The bounded body is still read for classification but never interpolated into a log. |
| X-02: foreign 503 falsely says the call was not made | **PASS** | All 503 remain `outcome_unknown`, `retry_safe=False`; their message now explicitly says outcome unknown. The old contradictory phrase is absent. No own-proxy 503 safe-retry claim was introduced. |
| X-03: pause committed between queue hint and claim still permits authority | **PASS** | `start_execution` ensures and locks the singleton control row before Run/Job/Attempt claim and refuses an already committed pause with `CONFLICT`. A concurrent pause upsert waits for the claim transaction. The unchanged QA pause counterexample and real two-connection absent-row regression passed on private 0017 databases. |
| ALR-05 direct cross-context imports | **PASS** | The product uses `runs.public` and `jobs.public` instead of the three deep imports. The architecture guard and both fresh import orders passed. |
| New recovery journal payloads | **PASS for the new events** | Reclaim emits `provider.outcome_unknown` only for changed prepared effects; settlement emits `provider.abandoned` only for changed effects. Both use the effect's actual Run/Attempt identities plus constant `error_code`/`dispatch_class`/`state` through `append_execution_event`'s scalar key allowlist. Repeated sweeps add no event in the focused regression evidence. No prompt, provider body, URL, path, idempotency key or execution token is copied into these payloads. |

The repaired claim's control-row lock is global and serializes concurrent claims. That is the deliberate pause boundary; performance under future parallel dispatch is unmeasured here. The `_EXPIRED_LEASES` forced query now selects only its target Attempt; periodic candidates are ordered by Run identity. The two-connection regression coordinates overlapping forced and periodic sweeps and completed without PostgreSQL `40P01` in the verified log. This recheck has no Docker grant and makes no new database-runtime claim of its own.

## 3. Contracts

No contract changed in this lane. The repair commits did not alter the frozen API or domain digests. New `jobs.public` and `runs.public` functions are internal Python context surfaces; the external API, migration and provider retry rules stay sealed.

## 4. Risks and known limits

`W53-EXEC-STOP-01` remains open: no genuine own-proxy 503 envelope/source proves safe retry. `W53-EXEC-STOP-02` remains open: `validating` cancellation is still a typed refusal pending owner choice. Y-04's global pause/resume audit events are stored as `CommandRecord` events but cannot enter the Run-ID-required public execution journal without an owner scope/contract decision. Do not invent a Run identity or count Y-04 as closed by this X verdict. The new MinIO image build/copy/rollback capacity stop, backup deferral to beta, release lineage, full `make gate` and deployment checks remain separate. This report is an X security/boundary PASS, not wave acceptance or publication authority.

## 5. Integrator instructions

Audit the exact one-path handback and cherry-pick only this report. Keep the three owner/scope stops and MinIO capacity stop visible. Use the full gate and independent final candidate checks as separate acceptance evidence; this report neither runs nor substitutes for them. If a later exact SHA changes proxy, Job claim, public context imports or journal event construction, repeat the affected X guards on that SHA.

## 6. Allowed paths and forbidden hotspots

The base-to-HEAD changed-path audit must list only `docs/program/W53-JUDGE-X-RECHECK.md`; `git diff --check` must pass. No source, tests, contracts, migration, root dependency/lock, composition root, global style, `VERSION`, release notes, backup or deployment path was changed. No Docker resource, working stand, ref or tag was touched. No behavior change needs a rollback or flag.
