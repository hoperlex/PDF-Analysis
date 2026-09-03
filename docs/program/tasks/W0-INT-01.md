# Task W0-INT-01 — ratify and publish CP-00 architecture checkpoint

> **Status: candidate preparation permitted; ratification and publication blocked.**
> Every preceding W0.3 task is integrated and both acceptance streams returned `PASS`
> on the third round, but two conditions are unmet. `W0-QA-01` is reopened: its suite
> currently accepts a ratification that is declared and not performed. And the
> acceptance that returned `PASS` ran against a candidate whose digest has since been
> corrected, so a fresh round is owed on the corrected tree. Executing before both
> land would ratify against evidence that no longer describes the tree.

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

- `W0-ARC-02`, integrated at
  `a67ba31e7748c02974ae9ae93c7f30b6f141d417`.
- `W0-QA-03`, integrated at
  `23dddf99f833d12cd4cc22d11e224d4b278872bf`.
- `W0-DOM-02`, integrated at
  `478d32e90d1cbb2c691e0ac0b61b68dadcf0d397`.
- `W0-EVT-01`, integrated at `3ca8e25413426ff8efec41cd850c325331d181fc`.
- `W0-CLN-01`, integrated at `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`.
- `W0-QA-01`, accepted and integrated at `854a68201cdd857abf6a12989f254f5d2e0928af` with an
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
- `docs/INDEX.md` — final status column only, so the index does not contradict the
  ratified state it indexes
- `docs/program/tasks/W0-INT-01.md` — this task's own status banner and handoff, which
  no other task may close
- `docs/program/tasks/W0-*.md` — status banners only, for tasks whose own execution is
  finished. A completed task cannot update its own banner, and the CP-00 audit found
  five state documents disagreeing because no task was authorized to. Nothing but the
  banner may change here: requirements, gates and deliverables of an accepted task are
  frozen by its acceptance.
- `docs/architecture/CP00_OWNER_DECISIONS.md` — point-in-time statements only, where a
  recorded decision's precondition has since been satisfied. The `PD-02` alias-map
  precondition is the known case: it is recorded as unmet in two documents, and only
  one of them was in any task's scope.
- `docs/program/CHECKPOINT_REGISTRY.md` and `docs/INDEX.md` — checkpoint status and the
  index status column.
- `docs/architecture/ARCHITECTURE_LINT_RULES.md` and `docs/architecture/ADR_INDEX.md` —
  point-in-time statements only. Two stale claims were assigned to this task while it
  could not write either file: the lint document's GATE-E prose still calls its own
  JSON untracked, false since `a67ba31e`, and the ADR index enumerates `PD-01`–`PD-04`
  against five recorded decisions. `ARCHITECTURE_LINT_RULES.md` is otherwise writable
  only by `W0-ARC-02` and `W0-CLN-01`, both closed and accepted. `W0-CLN-01` is one of
  the three commits named in the recorded wave exception; `W0-ARC-02` is not, and is
  simply an accepted task whose reopening would invalidate an independent `ACCEPT`. `ADR_INDEX.md` was writable by no task at
  all, since `W0-ARC-02` removed that slot as impossible. Assigning an item to an owner
  who cannot act on it is how the same defect survived two acceptance rounds.

  Both files sit inside `docs/architecture/`, one of the four families `W0-QA-01`
  certified byte-identical, so editing them changes `artifact_manifest_sha256` and
  fails `test_reviewed_families_are_byte_identical_to_the_candidate`. That is expected
  and is the same by-design consequence already recorded for
  `CP00_ARCHITECTURE_REVIEW.{md,json}`: ratification changes the reviewed artifact,
  which is why the `W0-QA-01` `ACCEPT` binds to `reviewed_candidate_commit` and not to
  what follows it. Change nothing in either file but the stale statement itself — no
  rule, `rule_id`, `severity`, `detection`, `enforcement` or ADR row.

`docs/architecture/REPOSITORY_LAYOUT.md` is deliberately **not** writable, even though
describing the `artifacts/` tree there would be natural. It sits inside
`docs/architecture/`, one of the four families `W0-QA-01` certified byte-identical, and
`test_cp00_candidate.py` fails the moment any of them drifts from the reviewed
candidate. The integrator learned this by breaking it: the `artifacts/` description was
written there and the test caught it immediately. `docs/INDEX.md` is outside the
reviewed families and carries the pointer instead.

Note that `CP00_ARCHITECTURE_REVIEW.{md,json}` above are inside a reviewed family too.
Editing them is this task's declared job and will make that byte-identity test fail by
design — ratification changes the reviewed artifact. That is expected and is why
`W0-QA-01`'s `ACCEPT` is bound to `reviewed_candidate_commit`, not to whatever follows
ratification.

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
6. After the evidence commit and clean final rerun, **`main` is fast-forwarded to
   `integration/W0.3`** — the branch is the source and `main` is the ref that moves.
   The earlier wording had it backwards, which would have described moving the
   integration branch onto `main` and losing the accepted checkpoint. The
   fast-forward must be a genuine one: if `main` is not an ancestor of
   `integration/W0.3`, stop rather than merge or force. The annotated tag
   `v0.0.0-architecture` is then created at the resulting checkpoint commit, and the
   branch, `main` and the tag are pushed together. The tag message names CP-00, the
   evidence folder and the frozen contract versions.

## CP-00 runtime fields are not applicable

`docs/manual-tests/CP-00_architecture.md` carries `backend_runtime` and
`frontend_runtime` header fields, inherited from the shared runbook template used by
every later checkpoint. CP-00 is an **architecture-only** checkpoint: no production
backend, frontend, worker, migration or composition root exists yet, and building one
is prohibited before CP-01. Both fields are therefore recorded verbatim as

```text
not applicable - architecture-only checkpoint
```

This is a recorded disposition, not a skipped field. Leaving them blank would read as
an untested runtime; inventing a version string would assert a runtime that does not
exist. The same applies to any other runbook field that presupposes a running system.
What CP-00 acceptance does test is reproducibility of the architecture package, its
schemas, its evidence and its recorded decisions.

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
