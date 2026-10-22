# Task EXTRACTION-GC-01 — the per-page full gc.collect() of the extraction stage stops starving the heartbeat on a large heap

task_id: EXTRACTION-GC-01

## Outcome

`analysis/stages/extraction.py::_release` frees a page's reference cycle without a full-heap `gc.collect()` per page, or with
one amortised so that its cost does not scale with the process's whole heap, while the memory bound it was added for
(`W55B-FIX` X-2: 172 MiB after every page of a 500-sheet drawing set, instead of the cap kill at page 127) still holds. `D-200`.

## Depends on

- `GATE-REPAIR-02` — completed (`D-200` was opened by its measurements).

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `51b1ed43`);
- migration head `0029_routing_refusal_codes`; API 73/83/242; 27 error codes; contract `1.0.0`; this task changes no contract and
  adds no migration;
- rulings: `R-135`, `R-144d` (while another session's complete gate runs on this host: no containers and no test batteries, only
  container-free checks), and the owner's standing order of 2026-10-22 «гони до беты без вопросов»: a choice that no recorded
  decision blocks is taken with the conservative default and reported under "Decisions taken", not asked.

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

- `src/auditmanager/analysis/stages/extraction.py`
- `tests/unit/analysis/**`
- `tests/integration/analysis/**`
- `docs/program/EXTRACTION-GC-01.md`
- `docs/program/tasks/EXTRACTION-GC-01.md`

## Lane resources

- container-free until the integrator says the host gate has ended; reserved and unused: foundation_instance `auditmanager-lane-e`,
  postgres_port `57661`, s3_api_port `61462`

## Forbidden hotspots

Every `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, `pyproject.toml`, `uv.lock`, `web/package.json`,
`web/package-lock.json`, `web/FRONTEND_LOCK.json`, `src/auditmanager/bootstrap/**`, `src/auditmanager/runs/**`,
`src/auditmanager/workers/**`, `src/auditmanager/executors/**` (the executor-connections line, `EXEC-*`, owns those slots and
paths), `tests/support/**`, any `conftest.py`, `tests/e2e/**`, `web/src/shared/**`, `web/src/_app/providers.tsx`, global styles,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, refs, tags and the stand. The worktree `.local/worktrees/gate-night`
belongs to a running gate: never run anything there or write to it (a `web/node_modules` symlink into it is read-only use through
`npm --prefix web run ...` with `--no-cache`). A change that needs a path outside the allowed list is reported to the integrator
(SendMessage to "main") instead of made.

## Non-goals

No change of the extraction's output (text, lines, hashes of the recorded corpus stay identical). No change to the worker, the
lease or the heartbeat. No raising of any watchdog.

## Work

1. Reproduce the cost: a container-free script or test that builds a heap of about 2 M tracked objects and times a full
   `gc.collect()` (0.08 s on a worker-like heap, 0.32 s on 2.1 M simple objects, 2.5-3.6 s in the complete battery's process,
   `D-200`); and a heartbeat-shaped thread beside a main thread that holds the GIL for that long.
2. Find WHO owns the per-page cycle (the comment in `_release`: pdfminer's content parser holds a bound method of itself, so each
   page leaves one reference cycle that owns the decoded stream). Prefer breaking that cycle explicitly after the page (drop the
   reference that closes it) so reference counting frees it and no collection is needed. If the cycle cannot be broken from
   outside, replace the per-page full collection by a generation-limited one, or by a full one every N pages with N derived and
   argued, never by guesswork.
3. Prove the memory bound is kept: the existing page-release test (find it: `grep -rn "_release\|releases_each_page" tests`)
   and a measurement of resident memory over a synthetic many-page document, before and after, quoted.
4. Prove the cost is gone: the same large-heap model, before and after; a test that fails if a full collection is run per page.
5. A quoted mutation per new branch (`-o pythonpath=<copy>/src`, prove the copy was imported).

## Deliverables

The changed stage file, the tests, and `docs/program/EXTRACTION-GC-01.md` with the before/after numbers and the cycle's owner.

## Required tests

The page-release and extraction tests that run without containers (say which ones were not run and why), `git diff --check`.
One pytest process at a time under `nice -n 10`; check `free -m` (>= 1500 MiB available) and `df -B1M /` (>= 3000 MiB free)
before each run. Do not hold more than 1.5 GB of memory in any experiment.

## Integration contract

Merged by the integrator (not by the executor) as a real merge into the integration branch; light acceptance only (`AGENTS.md` §8):
`git diff --check`, the named tests, `tests/contract` with the complete gate's own three ignores. Commit after every solid step; hand
back with a SendMessage to "main" (the report is the last commit).

## Failure/idempotency/security cases

A document that fails mid-page still frees that page; the extraction output is byte-identical on the recorded corpus.

## Rollback / feature flag

Revert the merge. No flag.
