# EXEC-FORCED-COMMAND-TEST-01 — the forced-command test describes the script it tests

**Source base:** `4802b8a3` (`origin/main`). Tests and this record only: no script, source, contract, migration or `VERSION` change.

## Found

Five cases of `tests/unit/executor_runner/test_ssh_forced_command.py` failed on `origin/main` and on
`origin/dev`, so any full run of the unit tests was red for a reason unrelated to the change under test.
The cause was read from the code, not guessed: `tools/executor-runner/ssh-forced-command.sh` was changed to
answer with the stand's envelope (`model`, `output_text`, `stop_reason`, token counts, cost) built from the
CLI's report, and to refuse a report that is not whole. The test kept the older picture: a stub whose
`modelUsage` was empty (`{"claude-opus-5": {}}`, no whole token counts, so the script answered exit 65),
an assertion that the CLI's JSON «passes through untouched», an argument list without `--json-schema`
and a working directory without `schema.json` and `result.json`.

## Changed

| Path | Reason |
| --- | --- |
| `tests/unit/executor_runner/test_ssh_forced_command.py` | the stub prints a realistic report (whole token counts and a cost); the stdout assertion compares the whole envelope (model, text, `end_turn`, 11 + 3 + 5 tokens in, 7 out, cost); the argument list and the working directory match what the script really passes and writes; 11 refusal cases and one structured-answer case are new |

The replaced assertion was weaker, not stronger (a key lookup against a pass-through the script no longer
does); the new one compares the complete object.

## Checks

| Check | Result |
| --- | --- |
| `test_ssh_forced_command.py` before | 5 failed, 24 passed |
| `test_ssh_forced_command.py` after | 41 passed |
| mutations of `ssh-forced-command.sh` (five edits, each restored byte-for-byte) | each made at least one test fail: two models accepted, a failed turn (`is_error`) accepted, a non-success `subtype` accepted, non-integer output tokens accepted (2 failed), a negative cost accepted |
| `tests/unit/executor_runner` and `tests/unit/executors` together | 645 passed, 0 failed |

## Limits

The script's API-key path was not run against a real Claude Code (no API key here); the tests use a stub CLI,
as before. This record changes no behaviour.
