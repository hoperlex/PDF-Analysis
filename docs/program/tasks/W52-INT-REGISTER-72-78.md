# Task W52-INT-REGISTER-72-78 — reconcile two W41 fixes

task_id: W52-INT-REGISTER-72-78

## Outcome

D-72 and D-78 no longer appear as current defects after their W41 repairs;
adjacent live comments stop claiming the old hostless URL is on today's stand.

## Depends on

- `W52-INT-87-01` — published at
  `350c5fb294188110bd3c7a8cb474f28f21c6e48d`.

## Frozen inputs

- Exact base `350c5fb294188110bd3c7a8cb474f28f21c6e48d`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- `docs/program/W41-AUTHOR.md` §§1–2 records code commits `14a0913` and
  `b56d103`; D-72/D-78 opening evidence in the debt register remains historical.
- Owner direction 2026-10-08: basic tests/lint only; no stand, QA or full gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the summary still lists the original D-72 and D-78 defects as open,
  while current code has their repairs.

### P-01 — exact base and repairs

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; rg -n 'D-72 \||D-78 \||author_label=subject.display_label|author_user_uid=subject.user_uid|host = urllib.parse.urlsplit' docs/program/DEBT_REGISTER.md src/auditmanager/api/routers/decisions.py src/auditmanager/analysis/text/proxy.py`
- captured_output:
  ```text
  350c5fb294188110bd3c7a8cb474f28f21c6e48d
  docs/program/DEBT_REGISTER.md:52:| D-78 | `CONFIGURED_AUTHOR_LABEL` attributes every verdict by every reviewer identically | **wave 41, `W41-AUTHOR`** |
  docs/program/DEBT_REGISTER.md:85:| D-72 | a URL with no host becomes a retryable outage | argue it from the catalog, as `D-13` was |
  src/auditmanager/api/routers/decisions.py:94:            author_label=subject.display_label,
  src/auditmanager/api/routers/decisions.py:98:            author_user_uid=subject.user_uid,
  src/auditmanager/analysis/text/proxy.py:99:            host = urllib.parse.urlsplit(self.base_url).hostname
  ```
- interpretation: the dated findings were true when opened, but current code
  and the W41 report support closure. Current deployment configuration is not
  inferred from repository comments.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W41-AUTHOR.md` and D-72/D-78 opening entries
- addendum_path: `docs/program/W52-INT-REGISTER-72-78.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/proxy.py` — comment only
- `tests/integration/analysis_text/test_proxy_adapter.py` — docstring only
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`
- `docs/program/tasks/W52-INT-REGISTER-72-78.md`
- `docs/program/W52-INT-REGISTER-72-78.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, dependencies/locks,
runtime statements, composition root and global styles.

## Non-goals

No proxy or author behavior change, deployment-state claim, QA, temporary stand,
full gate, release, tag or `origin/main` publication.

## Deliverables

- Close D-72/D-78 in the current-status summary with exact W41 evidence.
- Correct adjacent historical-present-tense comments without changing tests.

## Required tests

- Run the focused hostless-URL tests, Python compilation,
  governance/prose tests, frontend lint and `git diff --check`.

## Integration contract

Only prose changes. Publish to `origin/dev` after exact remote-ref and
fast-forward verification. W41's test evidence remains the D-78 runtime record;
the deferred full gate remains D-140.

## Failure/idempotency/security cases

No assertion about what is currently deployed. The old findings remain
readable as dated history; the new closure note cites current code and W41.

## Rollback / feature flag

Revert this docs commit. No feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes and
  forbidden-hotspot proof.
