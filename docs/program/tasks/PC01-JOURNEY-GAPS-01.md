# Task PC01-JOURNEY-GAPS-01 — the PC-01 journey walks the menu destinations `BETA-MATRIX-02` found unwalked

task_id: PC01-JOURNEY-GAPS-01

## Outcome

The browser journey (`npm --prefix web run e2e:pc01 -- --phase all`, manifest `tests/e2e/pc01/journey/manifest.json`) gains write or
read steps, each with its refusal or result case, for the gaps `docs/program/BETA-MATRIX-02.md` §B12 names, so that B12 can be read as
ready on code: «Блоки» (choose a version, read its portal blocks, crops and text lines), the norms document view
(`getNormDocument`, `listNormParagraphs`, `streamNormDocumentContent`), a successful «Вернуть» on «Главная», `correctVersionClassification`,
and, where the lane's recorded stack allows it, the identity continuation (`approveRegistration`, `rejectRegistration`, `updateUser`,
`purgeUser`). The conformance test over the manifest is extended so that a step or a route that disappears is a red test.

## Depends on

- `BETA-LIVE-JOURNEY-01` — completed (the journey this extends); `BETA-MATRIX-02` — merged (it names the gaps).

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `7dc61757`);
- migration head `0029_routing_refusal_codes`; API 73/83/242; 27 error codes; contract `1.0.0`; this task changes no contract and
  adds no migration; the journey today: 29 read routes, 95 write steps, 6 refusal cases, an identity continuation of 11 operations;
- rulings: `R-135`, `R-144d` (no containers and no test batteries on this host while another session's complete gate runs: write the
  code and run container-free checks until the integrator says the gate has ended), and the owner's standing order of 2026-10-22
  «гони до беты без вопросов».

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

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/e2e/pc01/journey/**`
- `tests/e2e/test_pc01_journey_conformance.py`
- `docs/program/PC01-JOURNEY-GAPS-01.md`
- `docs/program/tasks/PC01-JOURNEY-GAPS-01.md`

## Lane resources

- foundation_instance: `auditmanager-lane-g`
- postgres_port: `57670`
- s3_api_port: `61470`
- s3_console_port: `61471`
- postgres_db: `auditmanager_lane_g`
- s3_bucket: `auditmanager-lane-g`
- the recorded local stack of `BETA-LIVE-JOURNEY-01` (read `docs/program/BETA-LIVE-JOURNEY-01.md` for how it was started and which
  environment names it needs); ports chosen by the executor must be below the kernel's ephemeral range (`D-189`), never 57500-57501,
  28500-28501, 28520-28521, 57600, 57650, 57690.

## Forbidden hotspots

Every `src/**`, `web/src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock files, `tests/support/**`,
any `conftest.py` outside the journey's own directory, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, refs, tags and
the stand. A screen that cannot be walked because the application lacks something is reported to the integrator, not fixed here.
The worktree `.local/worktrees/gate-night` belongs to a running gate: never run anything there or write to it.

## Non-goals

No product change, no live provider call, no paid call (`R-29`), no run against the published stand. The identity continuation needs a
read-only path to the web tier's session register (`E2E_PC01_SESSION_STORE_PATH`): on the lane's local stack it exists; if it cannot be
made to run there, the step stays documented as «not walked» with the reason, not faked.

## Work

1. Read `tests/e2e/pc01/journey/README.md`, `manifest.json`, `write.mjs`, `refusals.mjs`, `journey.mjs` and
   `tests/e2e/test_pc01_journey_conformance.py`, and `docs/program/BETA-LIVE-JOURNEY-01.md` (how a recorded local stack is run).
2. For each gap add the step the way the neighbouring steps are written (a manifest entry with `screen`, `case` and `action` or
   `refused`, and its implementation in the `.mjs` files); a successful «Вернуть» needs the preceding take-the-work step in the same run.
3. Extend the conformance test so the new steps and routes are pinned; every new guard is shown failing under a quoted mutation
   (remove a step from the manifest; rename a case).
4. Container-free checks first: `node --check` on every changed `.mjs`, the journey's own unit tests (`write.test.mjs`,
   `navigation-retry.test.mjs`), and `python3 -m pytest -q tests/e2e/test_pc01_journey_conformance.py` (container-free).
5. **After the host gate ends** (the integrator tells you; marker `.local/gates/night-b315655d/END` exists) bring up the lane's recorded
   stack and run `npm --prefix web run e2e:pc01 -- --phase all --origin <your origin> --out <dir>`; quote the exit status and the counts
   (before 95 write steps and 29 routes). If the stack cannot be started, say so and hand back what the container-free checks prove.

## Deliverables

The journey code and manifest, the extended conformance test, and `docs/program/PC01-JOURNEY-GAPS-01.md` (what each step proves, the
commands with exit status, the live-run envelope path, what was not walked and why).

## Required tests

`node --check` of the changed files, the two journey unit tests, `tests/e2e/test_pc01_journey_conformance.py`, `git diff --check`;
the live `--phase all` run after the gate (one run, one lane stack, `nice -n 10`).

## Integration contract

Merged by the integrator (not by the executor) as a real merge; light acceptance (`AGENTS.md` §8): `git diff --check`, the named
tests, `tests/contract` with the complete gate's own three ignores. Commit after every solid step; hand back with a SendMessage to
"main" (the report is the last commit).

## Failure/idempotency/security cases

A step that passes without touching the screen it names is not a repair. No credential, token or session cookie appears in a manifest,
a log or the report.

## Rollback / feature flag

Revert the merge. Tests only; no flag.
