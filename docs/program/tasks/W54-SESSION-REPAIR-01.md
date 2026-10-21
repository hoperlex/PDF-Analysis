# Task W54-SESSION-REPAIR-01 — re-recognise the 121 degenerate blocks in session

task_id: W54-SESSION-REPAIR-01

## Outcome

The 121 W54 blocks whose corpus text is the recognition model's own reasoning
are re-read from their crops by Sonnet subagents of an interactive Claude Code
session (`R-137`), not by the paid proxy run. The answers pass through the
unchanged `rerecognise()` rule and become a version-2 repair ledger with its
`drop_sums_sha256`, which the existing loader and bundle export accept. The
ledger is checked by a command and by an independent spot check against the
page images.

## Depends on

- `W54-CORPUS-PROMOTION-01` — completed restore-verified base dump;
- `W54-REPAIR-01` — completed rerecognition rule, ledger v2 and sums binding;
- `W54-CORPUS-REPAIR-PLAN-01` — completed 121-page enumeration.

## Frozen inputs

- code base: `origin/dev` `ec41bb5881b2e677af7f22af62266818f37b2a61` (dev66);
- source drop: `/root/projects/PDF-Analysis/.local/norms/corpus` (read-only);
- source SHA256SUMS: `/root/projects/PDF-Analysis/.local/norms/corpus-sums/2026-10-15/SHA256SUMS`,
  SHA-256 `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- base snapshot content key `2026-07-23..2026-08-20+17d.4b74348debf7`;
- `RECOGNITION_SYSTEM_PROMPT`, `MAX_ATTEMPTS = 2`, `RENDER_DPI = 150` and
  `LEDGER_VERSION = "2"` as on the code base;
- owner direction `R-137` (2026-10-19, this session): the 121 recognition
  failures are redone by the session's Sonnet subagents. It supersedes the
  2026-10-16 `claude-opus-5` proxy selection for this repair only.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the drop holds exactly 121 degenerate blocks in 54 documents, and
  no repair ledger exists because the proxy credential is absent.

### P-01 — degenerate block population

- captured_at: 2026-10-19
- command: `PYTHONPATH=src .venv/bin/python -c "from pathlib import Path; from auditmanager.norms.corpus_source import degenerate_pages; p=list(degenerate_pages(Path('/root/projects/PDF-Analysis/.local/norms/corpus'))); print(len(p), len({x.document_slug for x in p}))"`
- captured_output:
  ```text
  121 54
  ```
- interpretation: the population equals `W54-CORPUS-REPAIR-PLAN-01`'s 121
  pages; nothing in the drop changed since the plan.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W54-SESSION-REPAIR-01.md`;
- `docs/program/W54-SESSION-REPAIR-01.md`;
- `docs/program/OWNER_RULINGS_2026-09-17.md` (the `R-137` and `R-138` entries only);
- `src/auditmanager/norms/session_repair.py` (new);
- `src/auditmanager/norms/__main__.py` (the two `repair session-*` commands
  and their docstring lines only);
- `tests/integration/norms/repair/test_session_repair.py` (new);
- ignored `/root/projects/PDF-Analysis/.local/norms/repairs/session-20261019/**`.

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global
styles, the rerecognition rule, degeneracy check, ledger model and its
version, the durable journal and pricing, source corpus and sums bytes,
promotion database and dumps, proxy credential, production stand, S3,
`CURRENT_STATE.md` (integration step), remote `origin/main` and tags.

## Non-goals

No proxy or paid call, no journal row, no change to what counts as degenerate
or repaired, no repaired-snapshot load, embedding build, bundle export,
stand import, deployment, full gate or beta verdict. Those are the next W54
steps and take this ledger as input.

## Deliverables

- `repair session-prepare`: enumerate, check every crop against the sums,
  render each crop at 150 dpi and write `pages/`, `prompt.txt` and
  `session.json`; it never overwrites an existing session;
- `repair session-ledger`: re-check the drop, sums, prompt and page images,
  replay `answers/<block_id>.<n>.md` through `rerecognise()` and write the
  ledger file, or refuse and list the reads still owed;
- the transcribed session directory, its ledger, and the result report.

## Required tests

- `PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/repair/test_session_repair.py`;
- `PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms -k "not postgres" --ignore=tests/integration/norms/custody/test_two_phase_custody.py`;
- `PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program tests/contract/architecture/test_alr05_boundaries.py`;
- `ruff check` over the changed Python files, `git diff --check`, direct
  task `governance_findings` = `[]`, exact changed-path proof;
- the real `session-ledger` over the transcribed directory: exit 0, 121
  repairs, ledger `drop_sums_sha256` equal to the frozen sums digest.

## Integration contract

The ledger file at
`/root/projects/PDF-Analysis/.local/norms/repairs/session-20261019/ledger.json`
feeds `python -m auditmanager.norms.loader --ledger` and
`auditmanager.norms.bundle export --ledger` unchanged. Its attempts name the
session model, `stop_reason` `session_transcript`, zero tokens and an unpriced
cost; no figure in it is a proxy charge. Any later reader treats it as
`R-137` evidence, not as a priced `R-106` run.

## Failure/idempotency/security cases

A changed crop, sums file, prompt, page image or corpus snapshot refuses. An
answer for a block outside the set, an answer the rule did not consume, a
non-UTF-8 answer or a missing first read refuses; a missing second read for a
degenerate first answer stops and lists the read owed. Re-running the ledger
over unchanged answers yields the same repairs. No credential is read.

## Rollback / feature flag

Revert the code commit to remove the two commands; delete the ignored session
directory to discard the transcription. No runtime, contract or data changes.

## Handoff

- changed files: the allowed paths above;
- contracts: none;
- next: the repaired-snapshot load, embedding build and bundle export under
  the W54 §3.9 resource floors;
- forbidden hotspots remain untouched.
