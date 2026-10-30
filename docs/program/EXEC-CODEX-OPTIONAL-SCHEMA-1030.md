# EXEC-CODEX-OPTIONAL-SCHEMA-1030 — result

## Failure and repair

For the owner's failed text-analysis Run `run_01M665J7PHK5JN195F963PZSGR`, the Codex pull agent claimed a real task and reported `codex_failed` / `command_failed`. A synthetic CLI request using the current section response schema reproduced the provider refusal: HTTP 400 `invalid_json_schema` because `schema.properties.observations.items.required` omitted the optional `omission` property. The short connection probe has a different schema, which explains its success.

The Codex command now gives its strict output mode an `anyOf` with two complete object shapes: one without `omission`, one with it required. It neither changes the task schema nor interprets the result. The application validates every submitted answer against the unchanged task schema.

## Checks

- `tests/unit/executor_runner/test_codex_answer.py`: 16 passed.
- `tests/unit/executor_runner`: 297 passed with local loopback sockets available. The first sandboxed run had 79 socket-permission failures and 218 passes; its failure was environmental, and the complete rerun passed.
- `python3 -m py_compile tools/executor-runner/codex_answer.py`: passed.
- `git diff --check`: passed.
- Synthetic live Codex CLI call on the unmodified section schema: exit 1, `invalid_json_schema`, missing `omission` in `required`. The same synthetic task through the corrected adapter: exit 0, `{"observations":[]}`. No customer document or runner token was used in these calls.
- The corrected adapter was installed at `/opt/pdf-analysis-codex-prod/codex_answer.py` after backing up the old file as `codex_answer.py.bak-20261030-optional-schema`. Installed and candidate SHA-256 match; systemd restart succeeded and the service is active. The failed Run is terminal.
- Post-fix, the owner started `run_01M666W9WQ1Z567K6PNWBRHFXM` with a section profile. The agent claimed four model tasks and the stand accepted all four answers (`state=answered`); the last was accepted at 10:54:32 UTC. The owner then reported a terminal partial result: stage 4 showed `analysis_failed`, block analysis and comprehensive analysis were partial, the observation merge completed, and normative verification was unavailable. Coverage was 16 processed blocks out of 47 total, with 31 outside the accepted window; page context was truncated. No customer document content is copied into this report.

The later partial result is distinct from the repaired `dependency_unavailable` failure. The frozen extended policy allows at most 16 blocks (`MAX_BLOCKS`), and `run_extended_review` marks partial coverage when blocks remain or page context is cut. If normative candidates are absent, the normative procedure is marked unavailable; the owner's UI displays a generic explanation, so its exact underlying reason cannot be established from that report. The Run executor maps any partial or unavailable extended procedure to a partial text-analysis stage with the generic `analysis_failed` code. Expanding coverage or changing normative corpus availability requires a separate policy/integration task and, where cost authority changes, fresh user consent.

## Integration and limits

Changed repository files are the task file, this report, `tools/executor-runner/codex_answer.py` and `tests/unit/executor_runner/test_codex_answer.py`. No contract, migration, dependency, composition root, global style, API or other forbidden hotspot changed. The host fix will be overwritten by a later deployment unless this branch is integrated. Integrate the exact candidate into `origin/dev` after review; no `origin/main` publication is authorised by this task. Rollback on the host is to restore the saved adapter and restart `pdf-analysis-codex-prod.service`.

The Codex CLI binary is currently provided by a versioned VS Code extension path in the systemd unit, so an extension replacement can break that path. The runner token shared earlier in chat remains a separate rotation item: install a new token in the service's protected environment file and revoke the exposed one. Neither is changed by this code repair.
