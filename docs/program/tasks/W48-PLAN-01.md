# Task W48-PLAN-01 — разложить W48 на замороженные, непересекающиеся слоты

## Outcome

Следующая волна имеет один исполнимый master-plan: измеримые результаты, карту долгов,
последовательные стадии, disjoint ownership, независимое judging, двухуровневую release-проверку
и единственный слот, которому разрешено обновлять `origin/dev`, `origin/main` и тег.

## Depends on

- `W47-INT-CLOSE`
- `NORM-INT-01`
- `NORM-ADR-01`
- `MAIN-AUTODEPLOY-01`

## Frozen inputs

- domain contract: `1.0.0-draft.1`, candidate revision 8, 27 opaque identities;
- API contract: 17 paths / 20 operations / 61 schemas, SHA-256
  `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`;
- error catalog: 22 codes;
- migration head: `0013_norm_embeddings`;
- planning base commit: `deda5337565e67e09a881d3f03d5673966fcfb2a`;
- controlling ruling: `R-49` — W48 is correction, debt closure and whole-tree audit;
- release boundary: `docs/program/MAIN_AUTODEPLOY_POLICY.md`.

## Allowed paths

- `docs/program/tasks/W48-PLAN-01.md`
- `docs/program/dispatch/W48-PLAN.md`
- `docs/program/dispatch/W48-JUDGES.md`
- `docs/program/W48-PLAN-01.md`
- `docs/program/CURRENT_STATE.md` — только ориентация следующей волны по `R-49`

## Forbidden hotspots

- `contracts/**`, generated contract consumers and the error catalog;
- `db/migrations/**` and migration head;
- root dependency/lock files, `Makefile`, composition roots and global styles;
- runtime, frontend, deploy and workflow implementation;
- `docs/program/CURRENT_STATE.md` вне одной разрешённой ориентационной строки и весь
  `docs/program/DEBT_REGISTER.md`;
- Git refs, tags, deployment host and `origin/main`.

## Non-goals

- no implementation or debt closure in the planning task;
- no claim that `MAIN-AUTODEPLOY-02`, `ALPHA-MANUAL-01` or D-70 is complete;
- no new product vertical, normative search API, corpus load, contract reseal or migration;
- no dispatch before `W48-FREEZE-01` records one clean exact base SHA.

## Deliverables

- `W48-PLAN.md` with entry conditions, task graph, ownership matrix, gates and release sequence;
- `W48-JUDGES.md` with independent entry points and cross-examination requirements;
- completion report `docs/program/W48-PLAN-01.md`.

## Required tests

- `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py -q` — green;
- every open debt named in `R-49` maps to one task or to an explicit owner-held/non-goal row;
- every hotspot has one owner per stage and parallel tasks have no overlapping writable path;
- `git diff --check` — empty output.

## Integration contract

The integrator may use the plan to open `W48-FREEZE-01`. Candidate implementation tasks are not
dispatch briefs until that task replaces the symbolic frozen base with an exact accepted SHA and
writes individual task files. Contract/migration changes stop W48 and require a separately ruled
contract wave.

## Failure/idempotency/security cases

- an unverified deployment, dirty tree, diverged publication refs or incomplete pending task
  blocks freeze;
- `make gate` remains hermetic and credential-free; public/live evidence is a separate mandatory
  release gate rather than a silent skip inside the canonical gate;
- no task receives credentials, production data or authority to push by implication;
- a failed post-deploy check leaves W48 untagged and requires an explicit gated forward repair or
  revert.

## Rollback / feature flag

Documentation-only. Revert these planning files if the owner changes `R-49`; no runtime flag,
data rollback or deployment action applies.

## Handoff

- changed files and checks are recorded in `docs/program/W48-PLAN-01.md`;
- the next executable task is `W48-FREEZE-01`, not an implementation lane;
- known limitation: owner-held product/security/storage decisions remain outside W48;
- forbidden hotspots remain byte-untouched by this task.
