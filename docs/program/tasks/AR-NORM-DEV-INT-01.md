# Task AR-NORM-DEV-INT-01 — carry verified-set preparation onto current dev and audit draft profiles

task_id: AR-NORM-DEV-INT-01

## Outcome

On the exact development base, the completed `AR-SET-PROMOTION-01` code and its
public Run pin seam are integrated without changing the served v1/v2 route. An
exact evidence report identifies what W56a/W57a/W57b/W56b can and cannot serve,
and records a technical check of every draft section profile.

## Depends on

- `AR-ORIGINAL-CITATIONS-PLAN-01` — completed implementation map.
- `AR-SET-PROMOTION-01` — completed source branch and isolated DB/Blob acceptance.
- `W59-SECTION-PROFILES-01` — completed draft legacy profile packages.
- `PB-PROFILE-01` — completed authored PB draft.

## Frozen inputs

- development base: `origin/dev=3bc7dae1a62ccd871ed42fc364ffa139cc2313f3` at task start;
- API SHA-256 `53d289eceaa4e1b77b1bf86c4bdca0c0be693f81669ded299a02c5122685b9ee`;
- domain identifier SHA-256 `6d203856576f87631f072f46c3a4b506ba0a4e9caf35c479e0a8e7d2e5c90fc5`;
- analysis stage SHA-256 `9680a3a1e40c7c24a00b3939071bfa83bb15e5edd6ae5ef0322f1a6e0ab20faa`;
- error catalogue SHA-256 `e9b52e8f1dd6dd8f2018826b8f32163401c07c8f99fa434f037fa27d0c9f9e03`;
- migration head `0031_executor_pull_channel`; 0023 SHA-256
  `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/AR-ORIGINAL-CITATIONS-PLAN-01.md`
- `docs/program/tasks/AR-ORIGINAL-CITATIONS-PLAN-01.md`
- `docs/program/AR-SET-PROMOTION-01.md`
- `docs/program/tasks/AR-SET-PROMOTION-01.md`
- `src/auditmanager/norms/public.py`
- `src/auditmanager/norms/retrieval/promotion.py`
- `src/auditmanager/norms/retrieval/promotion_repository.py`
- `src/auditmanager/runs/commands.py`
- `src/auditmanager/runs/repository.py`
- `tests/integration/norms/custody/test_retrieval_set_promotion.py`
- `tests/integration/norms/retrieval/test_promotion.py`
- `tests/integration/runs/test_retrieval_set_persistence.py`
- `docs/program/tasks/AR-NORM-DEV-INT-01.md`
- `docs/program/AR-NORM-DEV-INT-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, root dependency/lock files,
`src/auditmanager/bootstrap/**`, API routes and schemas, `web/**`, global styles,
the corpus, `CURRENT_STATE.md`, refs, tags and deployment host.

## Non-goals

No live v2/v3 model activation, invented model or tariff, unreviewed normative
map qualification, W56b vision policy, expert profile approval, release or beta
claim. This local candidate does not update `origin/dev` or `origin/main`.

## Deliverables

The four completed source commits replayed on the frozen dev base, targeted
checks, and `AR-NORM-DEV-INT-01.md` with exact remaining prerequisites and the
draft-profile audit. No profile status is promoted from `draft`.

## Required checks

- Focused promotion, Run pin, retrieval candidate and qualification tests;
- `tests/contract/program` and the draft profile package/registry tests;
- focused recorded v2, v3 citation and profile content tests;
- Python compilation, `git diff --check`, and exact changed-path proof.

## Integration contract

The candidate adds a retrieval-set promotion capability to the public norms
boundary. A future caller must provide an independently reviewed map, source
and embedding evidence, expected digests, current Attempt authority and two
confirmed custody bindings. The served start/reaudit commands still pass no
set ID and preserve their v1/v2 frozen digest. The integrator may accept this
candidate onto development only after inspecting the exact diff and rerunning
the service-backed promotion check on the merged tree. Publication to main has
no authority from this task.

## Failure, rollback and feature flag

Digest mismatch refuses before Blob dispatch; only the completed custody
workflow may verify a set. The new Run pin is nullable and unselected by the
served route. Revert this bounded candidate before activation if it fails
integration; no schema rollback or feature flag is needed.
