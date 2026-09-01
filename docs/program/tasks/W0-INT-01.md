# Task W0-INT-01 — ratify and publish CP-00 architecture checkpoint

> **Status: backlog draft. Not executable yet.**
> Start only after every preceding W0.3 task is independently accepted and integrated,
> and after `W0-QA-01` records `ACCEPT` for that exact convergence commit. Pin all
> placeholders before executing the task.

## Outcome

Produce the complete reproducible CP-00 evidence bundle, execute and record manual
architecture acceptance, ratify the eligible candidate set, fast-forward it to
`main`, and publish the annotated `v0.0.0-architecture` tag only if every gate passes.

## Ownership

- implementation/integration owner: primary agent `/root`
- checkpoint/freeze governor: primary agent `/root`
- independent manual tester: assigned person or agent who did not author the reviewed
  contracts or the W0-QA-01 test/report
- repository owner: approval authority for any newly discovered semantic decision;
  no new decision is expected

## Depends on

- `W0-ARC-02`, integrated at `<pending integration commit>`.
- `W0-QA-03`, integrated at `<pending integration commit>`.
- `W0-DOM-02`, integrated at `<pending integration commit>`.
- `W0-EVT-01`, integrated at `<pending integration commit>`.
- `W0-QA-01`, accepted and integrated at `<pending integration commit>` with an
  `ACCEPT` report for the exact convergence commit.

## Frozen inputs

- base/candidate commit: the accepted `W0-QA-01` integration commit
- contract set: domain, analysis and events `1.0.0-draft.1` candidates at that commit
- golden baseline: exact five-journey selection and complete 62-row name-resolution
  map at that commit
- architecture review, owner decisions and lint-rule specification at that commit
- manual runbook: `docs/manual-tests/CP-00_architecture.md`, read-only
- dependency locks: `requirements/validation.in` and `.lock`, read-only
- migration head: none

## Allowed paths

- `docs/architecture/CP00_ARCHITECTURE_REVIEW.md`
- `docs/architecture/CP00_ARCHITECTURE_REVIEW.json`
- `docs/program/CURRENT_STATE.md`
- `docs/program/CHECKPOINT_REGISTRY.md`
- `docs/program/waves/W0.3_ratification_integration.md`
- `docs/stages/S00_architecture_and_behavior_freeze.md`
- `artifacts/checkpoints/CP-00/**`

The Git merge, annotated tag and push are integration operations authorized only after
the file-level gates and manual acceptance succeed.

## Forbidden hotspots

- all machine contracts, golden fixtures, architecture Bible/ADR/lint-rule sources
- validators/tests, dependencies/locks, source/runtime code and manual-runbook text
- migrations, composition root, generated client and global styles
- every legacy repository file, ref and worktree entry

## Non-goals

- No repair of a failed lane, QA result or manual case inside the integration task.
- No ratification of `ADR-0014`, retention/legal-hold clauses or any tenant/IdP value;
  `U-04` remains open within its recorded scope.
- No numeric lease, heartbeat, grace, retry/backoff or cost policy.
- No production implementation and no tag other than the registry-defined CP-00 tag.
- No force-push, history rewrite or tag move.

## Deliverables

1. `artifacts/checkpoints/CP-00/` contains `checkpoint-report.md`,
   `contract-manifest.yaml`, `automated-summary.txt`, `manual-test-report.md`,
   `migration-head.txt`, `build-info.json`, `known-risks.md` and
   `restore-or-rollback-note.md`.
2. The contract manifest records exact file hashes, contract versions, candidate
   commit, dependency-lock hashes, `migration_head: none`, golden selection hash and
   the complete analysis registry/name-map hashes.
3. The manual report records tester identity, timestamps and `PASS`/`FAIL`/`BLOCKED`
   plus actual result for MT00-01 through MT00-06. Any failure or unexplained block
   stops the task.
4. The CP-00 review is reconciled with final W0.2/W0.3 evidence: the accepted ANA
   precondition and ID-03 condition are recorded satisfied, point-in-time wording is
   retained where historically material, eligible dispositions are ratified, and
   `ADR-0014` remains explicitly deferred. Markdown and JSON agree.
5. `CURRENT_STATE`, the checkpoint registry, W0.3 plan and S00 checklist agree on the
   accepted commit, tag, frozen contract set, explicit exclusions and next unlocked
   S01 preparation tasks.
6. After the evidence commit and clean final rerun, `integration/W0.3` is
   fast-forwarded to `main`; annotated tag `v0.0.0-architecture` is created at the
   resulting checkpoint commit and both refs are pushed. The tag message names CP-00,
   the evidence folder and frozen contract versions.

## Required tests

- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0` with standalone `PASS`.
- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/contract -v`.
  Expected: exit `0`; validator and CP-00 candidate suites pass together.
- Command: `.venv/bootstrap/bin/python -c "import json; from pathlib import Path; r=json.loads(Path('docs/architecture/CP00_ARCHITECTURE_REVIEW.json').read_text()); assert r['ratified'] is True; assert r['review_status']=='ratified'; assert sum(x['disposition']=='defer' for x in r['adrs'])==1; assert next(x for x in r['adrs'] if x['adr_id']=='ADR-0014')['disposition']=='defer'"`.
  Expected: exit `0`; ratification does not silently absorb the explicit defer.
- Command: `git diff --check`.
  Expected: exit `0` and no output.
- Command: `git status --short`.
  Expected: no output immediately before the tag.
- Command: `git rev-parse v0.0.0-architecture^{commit}` after tagging.
  Expected: exactly the accepted checkpoint commit.
- Command: `git ls-remote --heads --tags origin main integration/W0.3 v0.0.0-architecture` after push.
  Expected: `main`, the integration branch and the peeled annotated tag resolve to the
  recorded checkpoint commit; no force update was used.

## Integration contract

After success, downstream work may consume only the contract files and hashes listed
in the CP-00 manifest. The tag proves checkpoint acceptance, not implementation
readiness for every future capability. Explicit deferred scopes remain non-consumable
until their named later tasks close them.

## Failure/idempotency/security cases

- Any automated or manual failure stops before ratification/tag; the owning task is
  reopened and the candidate/QA chain reruns as required.
- Remote divergence stops the fast-forward; never force-push or move an existing tag.
- Re-running report generation for identical inputs preserves semantic content and
  hashes; timestamps/tester records remain append-only evidence.
- Evidence uses synthetic/anonymized references only and contains no credentials,
  protected payloads, environment dumps or mutable legacy content.

## Rollback / feature flag

No feature flag applies. Before tag, revert only the integration evidence commit and
reopen the failed owner task. After tag, never move the tag: use the formal
freeze-break procedure and, if a replacement checkpoint is required, a new registry
version decided by the integrator and repository owner.

## Handoff

- changed files and checkpoint/evidence commit
- full automated and manual results
- frozen contracts, hashes, migration head and dependency locks
- known risks/deferred scopes and rollback note
- pushed `main`, `integration/W0.3` and annotated tag refs
- next unlocked S01 task plan
