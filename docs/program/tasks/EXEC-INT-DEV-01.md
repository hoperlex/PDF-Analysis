# Task EXEC-INT-DEV-01 — publish the subscription-session pull channel to dev

task_id: EXEC-INT-DEV-01

## Outcome

`origin/dev` contains the completed `EXEC-PULL-01` channel and the `EXEC-HTTP-01`
stage-level model check. An administrator can configure a `claude_code_session`
runner in the «Подключения» UI; a real Claude Code session remains a separate
manual acceptance step.

## Depends on

- `EXEC-HTTP-01` — completed implementation and stage-level model check.
- `EXEC-PULL-01` — completed pull channel and candidate acceptance.

## Frozen inputs

- domain and API contracts: `1.0.0`, candidate surface 87 paths / 99 operations /
  284 component schemas;
- analysis and event contracts: `1.0.0`;
- migration head: `0031_executor_pull_channel`;
- base: `origin/dev` at `7a2270fabf56a3cf89987373846663b55b480051`;
- source candidate: `agent/exec-cand2` at `f51aeb62`, plus
  `agent/exec-http-01-r133` at `8801814e`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `tests/support/expected_facts.json`
- enumerator_owner: `EXEC-PULL-01`
- totality_query: `python3 -c "import json; d=json.load(open('tests/support/expected_facts.json')); print(d['surface']['path_count'],len(d['surface']['operations']),len(d['surface']['schema_names']),d['migration_head'])"`

## Captured premise evidence

- premise: observed remote development base

### P-01 — current remote development base

- captured_at: 2026-10-22
- command: `git rev-parse refs/remotes/publish/dev`
- captured_output:
  ```text
  7a2270fabf56a3cf89987373846663b55b480051
  ```
- interpretation: remote dev at the first read; recheck under the publication lock.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

Direct owner reply on 2026-10-22 transferred EXEC integration in dev to this
session, superseding the integrator assignment in `R-144g` for this publication.
`origin/main` requires a separate direct instruction for the exact SHA and the
full `make gate` under `MAIN_AUTODEPLOY_POLICY.md`.

## Allowed paths

- `docs/program/tasks/EXEC-INT-DEV-01.md`
- `docs/program/EXEC-INT-DEV-01.md`
- `tools/executor-runner/README.md`

Completed source-task commits are merged intact. This allowlist covers only this
integration task's own edits.

## Forbidden hotspots

- direct edits to `contracts/**`, migration head, composition root, dependency or
  lock files, global styles and `docs/program/OWNER_RULINGS_2026-09-17.md`;
- `origin/main`, tags and deployment host.

## Non-goals

- No autonomous Claude Code subscription daemon or paid call.
- No Codex/GPT implementation in this slice; options are evaluated in the report.
- No claim of a real Claude Code session acceptance without its transcript.

## Deliverables

- Merge of the two completed source tasks into a clean dev candidate.
- Corrected runner setup order in `tools/executor-runner/README.md`.
- Integration evidence in `docs/program/EXEC-INT-DEV-01.md`.
- Fast-forward publication to `origin/dev` after bounded checks.

## Required tests

- command: `python -m pytest -q -p no:cacheprovider tests/unit/executors tests/unit/executor_runner`
- expected: green.
- command: `python -m pytest -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py`
- expected: green.
- command: `npm --prefix web run typecheck && npm --prefix web run lint -- --quiet && npm --prefix web test -- --run --no-cache && npm --prefix web run build`
- expected: green.

## Integration contract

The `pull` kind and `claude_code_session` client are served in dev. The UI issues
a one-time token; the session uses the stdio MCP bridge to claim and answer tasks
through the runner API. The configured route activates it. Publication to dev
does not deploy the public alpha.

## Failure, idempotency and security cases

Existing `EXEC-PULL-01` tests cover token revocation, wrong model, malformed
answer, expiry, cross-connection claim and no-runner failure. The integrator
checks that the token is not logged and that the tree contains no secret.

## Rollback / feature flag

The connection is inert until an administrator selects its route. On a live
connection, clear that route or select the previous one first. A later code
rollback is a reviewed revert; do not downgrade migration `0031` on a live DB.

## Handoff

- changed files, commands/results, known limits and integration notes: see
  `docs/program/EXEC-INT-DEV-01.md`.
