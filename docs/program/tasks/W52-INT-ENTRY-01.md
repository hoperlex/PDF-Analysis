# Task W52-INT-ENTRY-01 — adopt and reconcile the W52 development entry

task_id: W52-INT-ENTRY-01

## Outcome

The judged W52 plan and its owner-answer source are available on the development
line. Its entry and integration order distinguish code-only development from
the deferred QA, built-stand, manual and full-gate release checks. W52 remains
unfrozen until its ruling and freeze tasks are completed.

## Depends on

- `W51-INT-CLOSE` — completed on `origin/dev` at
  `4159d4e8d831b4aa7ea8eaefa5bc21bb77ed43d5`.
- `W52-INT-VERSION-READ-PREP-01` — completed in the same development
  lineage before that close; its report records the latest code preparation.

## Frozen inputs

- Exact clean base `4159d4e8d831b4aa7ea8eaefa5bc21bb77ed43d5`.
- Planning source `plan/roadmap-to-beta` at
  `2b45a11ec558df1452a4822149e54d2fe0ddb57e`; its tracked W52 plan,
  roadmap and judging record are read-only inputs. Its untracked W58 files
  and worktree are outside this task.
- Domain candidate revision 9 / 29 identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head
  `0015_accounts_roles_registration`.
- Owner direction of 2026-10-08 recorded in `W51-INT-CLOSE` and D-137–D-140:
  implementation may proceed with basic checks while QA, live/manual
  acceptance and full gate are deferred to a separate validation wave.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the proposed W52 plan is absent on dev and still requires a
  literal `GATE OK` on the W51 close SHA, which the owner deferred.

### P-01 — entry contradiction

- captured_at: 2026-10-08
- command: `git ls-tree --name-only 4159d4e docs/program/dispatch/W52-PLAN.md; git show 2b45a11:docs/program/dispatch/W52-PLAN.md | sed -n '30,44p'; git show 4159d4e:docs/program/W51-INT-CLOSE.md | rg -n 'GATE OK|full gate'`
- captured_output:
  ```text
  [no path from git ls-tree]
  | `W51-INT-CLOSE` done, literal `GATE OK` on its SHA | `docs/program/W51-INT-CLOSE.md`; `origin/dev` |
  | baseline gate timing recorded on an idle host (§3.7) | `W52-FREEZE-01.md` |
  52:`W52-INT-VALIDATE-01` full gate on `e2cfea92` did not produce `GATE OK`;
  58:| D-138 | Complete `make gate` with literal `GATE OK` on the exact clean release candidate after correction |
  ```
- interpretation: W51's development closure is a valid code-entry dependency;
  its deferred gate cannot be represented as passed or required for the
  code-only W52 entry under the later owner direction.

## Historical evidence

- correction_mode: addendum
- source_record: planning source `W52-PLAN.md` at `2b45a11`
- addendum_path: `docs/program/W52-INT-ENTRY-01.md`

The planning branch is not rewritten; the adopted plan records its execution
amendment and source SHA.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-INT-ENTRY-01.md`
- `docs/program/W52-INT-ENTRY-01.md`
- `docs/program/dispatch/W52-PLAN.md`
- `docs/program/dispatch/ROADMAP-TO-BETA.md`
- `docs/program/reviews/W52-PLAN-JUDGING.md`
- `docs/program/CURRENT_STATE.md` — W52 entry status only
- local integrator card/handoff under `.local/`
- `integration/w51` local commit and, after remote verification, fast-forward
  publication to `origin/dev`

## Forbidden hotspots

Everything else, especially the planning worktree, contracts, migrations,
root dependency/lock files, composition root, global styles, product code,
tests, `origin/main`, tags and deployment.

## Non-goals

No W52 owner ruling, freeze, lane dispatch, QA, stand, human acceptance, full
gate, W52 close, release tag or main publication. No historical W51 gate is
claimed. The W52 release criteria remain due in D-137–D-140.

## Deliverables

- Source-identifiable copies of the W52 plan, roadmap and judging record on
  the development line.
- Reconciled W52 code-entry and deferred-validation text, with a bounded
  integration report naming the remaining freeze prerequisites.
- A local clean commit; publish only after the remote ref can be checked and
  exact fast-forward ancestry proved.

## Required tests

- `git diff --check` and exact changed-path review.
- Focused programme governance/prose tests that read the adopted documents.
- No full `make gate` under the owner's development direction.

## Integration contract

The integrator alone adopts the planning files and publishes this docs-only
candidate to `origin/dev` after remote-ref verification. `W52-RULE-01` still
records the plan's owner confirmations and `W52-FREEZE-01` re-sweeps grants,
pins and entry evidence before W52 Stage A/B/C is dispatchable. Later release
validation closes D-137–D-140 on an exact candidate; it is not waived here.

## Failure/idempotency/security cases

- A moved remote `dev`, a red document guard or unresolved owner confirmation
  stops publication/freeze. An unavailable remote leaves a local candidate.
- Repeating adoption must not duplicate the plan or change its planning source.

## Rollback / feature flag

Revert this docs-only commit if the entry record is wrong. No behavior or
feature flag changes.

## Handoff

The integration report lists changed files, checks, contracts, risks,
integration instruction and forbidden-hotspot proof.
