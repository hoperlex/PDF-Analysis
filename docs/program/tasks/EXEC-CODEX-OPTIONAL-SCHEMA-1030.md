# EXEC-CODEX-OPTIONAL-SCHEMA-1030 — Codex accepts the section observation schema

task_id: EXEC-CODEX-OPTIONAL-SCHEMA-1030

## Outcome

A `pull` Codex agent can answer a section text-analysis task whose observation has the optional `omission` field. A synthetic Codex CLI call accepts the provider schema, and the application's existing answer validator continues to judge the original task schema.

## Depends on

- `EXEC-CODEX-SSH-01` — completed Codex pull-command adapter.

## Frozen inputs

- Base `cd4dc8ca` (`origin/dev` at task start); API contract `1.14.0`, 233 paths / 259 operations / 620 schemas; migration head `0043_stage_ai_generations`.
- `analysis.text.prompt.response_schema_for` declares `omission` optional for section profiles. `codex exec --output-schema` rejects that object because its `required` list omits the property.
- The `pull` task and server answer validator remain unchanged.

## Enumerator ownership

- enumerated_set_changed: no

## Captured premise evidence

- premise: the section schema adds `omission` to observation properties without adding it to `required`
- captured_at: 2026-10-30
- command: `git show cd4dc8ca:src/auditmanager/analysis/text/prompt.py | rg -n 'properties\["omission"\]|item\["properties"\]|item\["required"\]'`
- captured_output:
  ```text
  216:        properties = dict(item["properties"])
  218:        properties["omission"] = OMISSION_SCHEMA
  219:        item["properties"] = properties
  ```

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tools/executor-runner/codex_answer.py`
- `tests/unit/executor_runner/test_codex_answer.py`
- `docs/program/tasks/EXEC-CODEX-OPTIONAL-SCHEMA-1030.md`
- `docs/program/EXEC-CODEX-OPTIONAL-SCHEMA-1030.md`
- Operational hotfix only: `/opt/pdf-analysis-codex-prod/codex_answer.py` and its backup on the existing host, under the owner's direct repair request.

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies/lockfiles, `src/auditmanager/**`, `web/**`, `infra/**`, global styles and composition roots.
- No `origin/main` push, merge, tag or deployment of an image.

## Non-goals

- No change to the canonical response schema, prompt, task payload, token or model pin.
- No automatic retry of the failed Run or other paid model calls on customer documents.

## Deliverables and checks

- Codex-only schema conversion that represents absent versus present `omission` as two complete object alternatives, without changing any other response shape.
- A focused test over the actual section schema and the existing adapter tests.
- `python -m pytest -q tests/unit/executor_runner/test_codex_answer.py`; `python -m py_compile tools/executor-runner/codex_answer.py`; `git diff --check`.
- One synthetic CLI check with no customer content, then an operator check on a new Run.

## Integration contract and rollback

The adapter alone writes a Codex-compatible copy to `--output-schema`; it still reads one task and prints one JSON answer. The server validates that answer against the task's unchanged schema. Back up the installed adapter before replacement; restoring the backup and restarting the service rolls back the host fix. Integration may publish the reviewed branch to `origin/dev`; `origin/main` requires its separate owner instruction and deploy gate.
