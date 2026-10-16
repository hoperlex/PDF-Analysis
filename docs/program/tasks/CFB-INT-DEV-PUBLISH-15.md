# Task CFB-INT-DEV-PUBLISH-15 — publish checked code and corpus evidence

task_id: CFB-INT-DEV-PUBLISH-15

## Outcome

One exact, clean fast-forward `origin/dev` candidate contains three completed
unactivated W56a/W57b/W59 code slices and the W54 verified-base/offline-plan
evidence. It also carries the explicitly incomplete W55b main-gate record for
visibility. The published SHA is read back; no deployment or beta verdict is
inferred.

## Depends on

- `CFB-INT-DEV-PUBLISH-14` — completed prior dev publication at `445efc5d`;
- `W56A-INT-RECORDED-MERGE-STAGE-01` — completed saved merge stage;
- `W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01` — completed export preflight;
- `W59-INT-SUMMARY-INPUT-PREP-01` — completed comparison input;
- `W54-CORPUS-PROMOTION-01` — completed base restore verification;
- `W54-CORPUS-REPAIR-PLAN-01` — completed zero-call plan.

## Frozen inputs

- code base: `41a4aa17538940534306d53ba269e41bee654154`;
- remote `dev`: `445efc5db8556ef5a5e13fa680f9f49eb9783954` at preparation read;
- remote `main`: `23fd729dbb06c642be0588017f6b195305e2e53e` at preparation read;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- W54 plan SHA-256 `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W54 verified dump SHA-256 `e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d`;
- W55b main candidate `6d63802ab465a0317839c9b57abd5e90f3d91769`, migration head `0021_portal_bundles`;
- code-first migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the exact dev predecessor lacks the three completed source slices
  and the W54 restore/plan reports, while W55b's first complete gate attempt
  is recorded as failed and a retry remains separate.

### P-01 — exact remote predecessor

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  445efc5db8556ef5a5e13fa680f9f49eb9783954 refs/heads/dev
  23fd729dbb06c642be0588017f6b195305e2e53e refs/heads/main
  ```
- interpretation: reread both refs immediately before publication; any
  moved dev predecessor stops this integration.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md` — one leading paragraph;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-15.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-15.md`;
- exact fast-forward update of `origin/dev` after checks.

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, application/runtime/test source in this integration commit,
source corpus/sums bytes, production DB/S3, `origin/main`, tags and deployment
workflow.

## Non-goals

No W55b main deployment, paid W54 repair, embedding build, corpus DB/S3
publication, live AR v2, XLSX route, AI summary output, complete beta gate or
beta verdict. The W55b interim report is not a completed prerequisite.

## Deliverables

The leading state entry, this task, integration report and exact pushed
`origin/dev` SHA read-back.

## Required tests

- combined focused W56a/W57b/W59 and program-governance suite;
- direct task governance, frozen SHA values, exact staged paths and whitespace;
- clean tree, fresh remote refs, fast-forward proof and exact push read-back;
- complete beta `make gate` deferred under R-135. W55b's separate SHA owns
  its complete main-candidate gate and cannot borrow these focused checks.

## Integration contract

Only this integration task publishes the exact checked candidate to
`origin/dev`. The code remains unactivated; W54 evidence remains local to
the isolated promotion environment. `W55B-INT-MAIN-PREP-01` is carried only
as an interim failed-gate diagnostic, with no `origin/main` authority or
completion claim. A moved ref or dirty candidate stops publication.

## Failure/idempotency/security cases

Do not add ignored promotion dumps, plans, credentials or gate logs to Git.
Never force-push. Retry reads the remote and does nothing if already equal.
No W55b main candidate or unverified beta tree is pushed to `origin/main`.

## Rollback / feature flag

No runtime behavior is activated. Corrections use reviewed forward commits;
no history rewrite, deployment rollback or feature flag is needed.

## Handoff

- changed files: exactly the three integration documentation paths above;
- contracts: none;
- next: W54 credential-gated sample, W56 executor/DB acceptance, W57 seal,
  W59 approval/runtime and separate W55b complete gate;
- forbidden hotspots remain untouched by this integration commit.
