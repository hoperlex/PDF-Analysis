# Task W53-JUDGE-X-RECHECK — independent security/boundary verdict on repaired candidate

## Outcome

Independently decide whether X's W53 findings are corrected on the merged candidate: truthful ambiguous-503 handling and no response-body leak, pause/claim authority boundary, ALR-05 context boundaries, and safe journal payloads. Give an exact PASS/REJECT with evidence; preserve the separate owner stop decisions.

## Depends on

- W53-JUDGE-X
- W53-QA-RECHECK-01
- W53-PROXY-REPAIR-01
- W53-ALR05-REPAIR-01
- W53-JOBS-REPAIR-03
- W53-QUEUE-TEST-REPAIR-02

## Frozen inputs

- Integrated pre-grant SHA `bb5508413935ccb2e4e784fb7dfddf913dbb708c`; integrator supplies exact post-grant base.
- API `1.0.0-draft.1`, OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`; domain rev 9/29, state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`; migration `0017_execution_queue`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- `docs/program/W53-JUDGE-X.md` and `docs/program/W53-QA-01.md` record the original failures. Repairs are in `W53-PROXY-REPAIR-01`, `W53-ALR05-REPAIR-01`, `W53-JOBS-REPAIR-03` and the integrated QA recheck. The integrator independently repeated ALR/proxy **4/4** and combined QA/concurrency **23/23** at `c65d3a30c014aaa029b558ad04f72e282de37dd9`; log `/tmp/w53-int-qa/combined.log` SHA-256 `fb788e63b37c86f64a2f090a4bcf10d801197fb07d84e8cf7ae7c96354ded360`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/W53-JUDGE-X-RECHECK.md` only.

## Forbidden hotspots

Every product/test/contract/migration/dependency/composition/global-style/release/backup/deployment path, other reports, refs/tags and the working stand.

## Non-goals

Changing behavior, a contract reseal, opening own-proxy 503 retry without a genuine envelope, deciding validating cancellation or global-pause journal scope for the owner, a MinIO upgrade, release notes or full gate.

## Deliverables

Fresh code review against the original X findings, exact targeted pure guard reruns, log/hashes and precise residual risk. Check journal allowlist/call sites for new provider events and absence of arbitrary 503-body logging. Report-only six-item AGENTS.md §5 handback and exact path audit.

## Required checks

Run `tests/contract/architecture/test_alr05_boundaries.py` and `tests/integration/qa_w53/test_proxy_refusal_boundary.py` without services. Inspect the private QA/concurrency logs and verify their hashes. Verify frozen hashes, `git diff --check` and code paths. No Docker lane is granted; disk check before any substantial test run under AGENTS §8.

## Integration contract

Integrator audits and cherry-picks only the report. A new confirmed defect needs an exact repair grant. X's verdict does not itself accept the wave or authorize publication.

## Failure/idempotency/security cases

Foreign 503 ambiguous/no repeat, redacted logging, no direct cross-context import, pause after hint before claim, no secret journal payload or broad exception masking.

## Rollback / feature flag

No behavior change.

## Handoff

Six AGENTS.md §5 items, clean branch and exact HEAD.
