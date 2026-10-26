# Task EXEC-CLAUDE-SONNET-01 — the subscription command also serves claude-sonnet-5

task_id: EXEC-CLAUDE-SONNET-01

## Outcome

`claude_answer.py` serves `claude-sonnet-5` as well as `claude-opus-5`. The served model is chosen by
one optional argument, `--model`, whose only accepted values are the two pins of `R-143g`; without it
the command serves Opus exactly as before, so a deployed `authorized_keys` line or agent configuration
keeps working. A stand has Sonnet as a second connection with its own key and `command=` line.

## Depends on

- `EXEC-CLAUDE-SSH-01` — merged on `origin/main`.

## Frozen inputs

- base commit: `cecf8668` (`origin/main` after the 0.8.2 publication `8f86ddfd`);
- shared contract `1.6.0`, migration head `0032_ar_v3_run_group`, `VERSION` `0.8.2`: none changes;
- `R-143g` (sessions and agents run on the pinned `claude-opus-5` or `claude-sonnet-5`);
- the real Claude Code `2.1.310` on the owner's machine reports `modelUsage` with the key
  `claude-sonnet-5` for a Sonnet call (read from a real call on 2026-10-26).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the command is tied to one model by a constant
- captured_at: 2026-10-26
- command: `git grep -n 'MODEL = ' cecf8668 -- tools/executor-runner/claude_answer.py`
- captured_output:
  ```text
  cecf8668:tools/executor-runner/claude_answer.py:29:MODEL = "claude-opus-5"
  ```
- interpretation: a Sonnet task is refused as `model_mismatch` today; the change is in this one file and its tests.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits to its own branch. Publication to `origin/main` needs the owner's separate instruction naming the exact SHA.

## Allowed paths

- `tools/executor-runner/claude_answer.py`
- `tools/executor-runner/agent.claude-ssh.example.toml`
- `tools/executor-runner/README.md`
- `tests/unit/executor_runner/test_claude_answer.py`
- `tests/unit/executors/test_claude_answer_envelope.py`
- `docs/program/tasks/EXEC-CLAUDE-SONNET-01.md`, `docs/program/EXEC-CLAUDE-SONNET-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, `src/**`, `web/**`, `infra/**`, root dependency and lock files,
`docs/program/CURRENT_STATE.md`, `VERSION`, `release-notes/**`, refs, tags, the stand.

## Non-goals

No other model, no per-task model choice (the model is fixed by the command line, never read from the
task), no change to the stand, the API or the pin lock, no image support, no change to the default.

## Work

1. `ALLOWED_MODELS` and `DEFAULT_MODEL`; the model becomes a parameter of `read_task`, `_report`,
   `_envelope`, `_run`, `answer` and `ssh_reply`; `main` accepts `--model` once, only from the two pins.
2. The task's model, the CLI's start argument, the reported `modelUsage` and the envelope's model all
   use the served model; a mismatch anywhere is a typed refusal.
3. README sections E and F and the example configuration describe `--model`.

## Deliverables

The change, its tests with mutation proofs, one real call per model through the script read by the
stand's own parser, and the report `docs/program/EXEC-CLAUDE-SONNET-01.md`.

## Required tests

- command: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/executor_runner/test_claude_answer.py tests/unit/executors/test_claude_answer_envelope.py tests/unit/executor_runner/test_readme.py`; expected: pass.
- command: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py`; expected: pass.
- command: `git diff --check`; expected: exit 0.

## Integration contract

Default: `claude_answer.py [--ssh-envelope] [--claude PATH]` serves `claude-opus-5`, unchanged. With
`--model claude-sonnet-5` it serves Sonnet. It refuses any other `--model`, a repeated `--model`, a task
that names the other model, and a CLI whose `modelUsage` names a model other than the served one.

## Failure/idempotency/security cases

- an unknown or repeated `--model` exits 2 and prints only the usage line;
- a task for the other model never starts the CLI (`model_mismatch`);
- a CLI that answers on the other model, or on two, is `claude_model_mismatch`;
- no task text, key or token is ever printed.

## Rollback / feature flag

Remove `--model` from the `command=` line: the command serves Opus again. Revert the commit to remove the option.

## Handoff

changed files; commands and results; the mutation table; what was not run (a stand with a Sonnet
connection); the instruction to the integrator (publish only on the owner's exact-SHA instruction).
