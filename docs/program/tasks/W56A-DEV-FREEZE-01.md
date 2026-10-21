# Task W56A-DEV-FREEZE-01 — recorded-only freeze для первых задач W56a

## Outcome

Одна точная база W56a и два непересекающихся задания готовы к коду:
`W56A-SEAL-01` и `W56A-GENERATOR-PREP-01`. Заморозка не утверждает
идентичность live-модели и не включает v2 proxy mode.

## Depends on

- `W55B-INT-CLOSE` — завершена на `6d63802a`;
- `W56A-RULE-01` — принята документами в `dev`;
- `CODE-FIRST-INT-01` — принят в `dev` на `d600fe69`.

## Frozen inputs

- domain contract: candidate revision 12, error-code digest
  `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16`;
- API contract: 47 paths / 54 operations / 123 schemas, SHA-256
  `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`;
- analysis contract: stage registry SHA-256
  `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`;
- provider lock: SHA-256
  `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`,
  review-only until `W56A-MODEL-PIN-01`;
- migration head: `0021_portal_bundles`; W56a SEAL alone owns proposed
  `0022_findings_v2`;
- code base: `d600fe69777c923e246d89bc4a9451c3974eaf53`;
- check policy: R-135; split and model refusal: R-136/R-133.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

SEAL alone changes contract enumerators in its separate task.

## Captured premise evidence

- premise: the published W55b code is unchanged by the plan, and the frozen
  contract/lock bytes still match W56a's earlier preflight

### P-01 — exact development base

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev`
- captured_output:
  ```text
  d600fe69777c923e246d89bc4a9451c3974eaf53
  d600fe69777c923e246d89bc4a9451c3974eaf53
  ```
- interpretation: the local integration tree matches the read-back dev ref;
  it says nothing about deployment.

### P-02 — migration and pin inventory

- captured_at: 2026-10-15
- command: `/root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py reseal-surface migration table error-code > /tmp/w56a-dev-pin-sweep.txt && wc -l /tmp/w56a-dev-pin-sweep.txt && sha256sum /tmp/w56a-dev-pin-sweep.txt`
- captured_output:
  ```text
  98 /tmp/w56a-dev-pin-sweep.txt
  dd6d025853316a6764b8c66856b6952408f1e43e72c01b664f01c30cd250c11b  /tmp/w56a-dev-pin-sweep.txt
  ```
- interpretation: the inventory equals the 98-line complete listing in
  `W56A-FREEZE-01.md` §4; that historical report remains stopped.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`W56A-FREEZE-01.md` and `W56A-PROBE-01.md` are immutable failed preflight
evidence. This new task is a separate recorded-only freeze.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W56A-DEV-FREEZE-01.md`
- `docs/program/W56A-DEV-FREEZE-01.md`
- `docs/program/tasks/W56A-SEAL-01.md`
- `docs/program/tasks/W56A-GENERATOR-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, migrations, root dependencies/locks, composition roots,
  global styles, runtime/UI/test code, `P02_LOCK.json`;
- owner rulings, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, the stand,
  credentials, `origin/main`, tags.

## Non-goals

- no live/paid gateway probe, model pin, v2 activation or product change;
- no full local gate, manual acceptance or beta verdict;
- no grant to PROVIDER or any W57/W58–W63 implementation lane.

## Deliverables

- completed freeze report with exact base, checked inputs and owner matrix;
- two complete code task files with frozen contracts, allowed paths,
  targeted checks and stop conditions.

## Required tests

- `git diff --check` and exact changed-path proof — clean;
- `.venv/bin/python -m pytest -q -p no:cacheprovider
  tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py
  tests/contract/program/test_wave_governance.py` — green;
- SHA-256 and migration-head commands above — equal to Frozen inputs;
- pin sweep — same complete inventory digest;
- before push, remote dev equals `d600fe69`; normal fast-forward only;
  after push, remote read-back equals the new exact task tip.

## Integration contract

On the published dispatch tip, SEAL and GENERATOR-PREP may start from the same
code base in separate worktrees. They write disjoint paths; merge SEAL first,
then GENERATOR. SEAL must not write `P02_LOCK.json`. PROVIDER has no grant
until a future `W56A-MODEL-PIN-01` passes the two distinct gateway probes.
Every subsequent task receives a fresh base and grant after its predecessor.

## Failure/idempotency/security cases

- If code/contract bytes or remote dev moved, stop and re-freeze.
- The failed stand model response cannot be copied into the lock or accepted
  as the configured model.
- No client PDF, provider credential, host or raw model response is recorded.

## Rollback / feature flag

Documentation only; revert these four files. No runtime flag or data rollback.

## Handoff

- changed files: the four Allowed paths;
- checks/results: recorded in `W56A-DEV-FREEZE-01.md`;
- limitations: live model identity unresolved; earlier freeze still STOPPED;
- next: dispatch only the two Stage-A tasks after dev read-back.
