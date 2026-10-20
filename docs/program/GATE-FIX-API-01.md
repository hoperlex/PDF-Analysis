# GATE-FIX-API-01 — the API and composition suite reds before the complete gate

Task: `docs/program/tasks/GATE-FIX-API-01.md`. Branch `agent/gate-fix-api-01`, based on `7bdb254e`
(`origin/dev` `8697baea` plus the three frozen task files); test commit `11b377b9`; real merge of
`802b3823` (`integration/night-1020`) as `049f2fcb` (`git merge-base --is-ancestor 802b3823 HEAD`
holds). Debt `D-187`.

## Result

`tests/integration/api` is green on the merged tree (624 passed). `tests/integration/composition`
was green on the merged tree in everything that ran (`test_every_port_implementation_is_whole.py`
29 passed; the two deploy/infra chunks 222 + 371 passed, 2 skipped) and **stopped before its last
chunk** (see "What was not run"). All three named reds were stale pins; none was a product defect.
No `contracts/**`, no `src/**`, no migration, no `web/**`, no dependency file and no
`tests/support/**` changed. `src/auditmanager/bootstrap/adapters.py` did not change either:
`DecisionAdapter` is right, its test was not.

| Red | Cause | Decision |
| --- | --- | --- |
| `test_query_surface.py::test_the_filter_vocabularies_are_the_frozen_ones` | the last line pinned `len(FindingCategory) == 2 and len(Verdict) == 4`; the sealed `FindingCategory` in `contracts/api/v1/openapi.json` has 12 values (seven prior and five v3 normative ones, `W57A-SEAL-01B`), `Verdict` 4 | stale pin. The two counts are no longer typed: each vocabulary is compared to the contract's `enum` as a set, the contract's `enum` must hold no repeat, and `len(vocabulary) == len(contract enum)`. The set equality that was already there is kept |
| `test_query_surface.py::test_every_declared_query_parameter_is_read_by_the_router_that_declares_it` | in two layers. First: `compareDocumentVersions` (`W59-VERSION-COMPARE-01`) and `listPriceListPositions` (`W60-PRICE-LIST-01`) declare query parameters and are in neither `targets` nor the declared-surface literal (`set(targets) == set(declared)` failed with those two names). Second, behind it: with the vocabulary at 12, the sweep's `category` case asked every one of the 12 values for a non-empty homogeneous page, but the fixture publishes findings in two categories only, so ten values were reported as ignored filters on `listRunFindings` and `listDecisions` | stale test. The two operations are in `targets` and in the declared-surface literal (`target_version_uid`, `source_run_id`, `target_run_id`, `mode`, `diff_offset`, `diff_limit`; `offset`, `limit`) and, like `getSpecificationPrices`, `listOptimisationProposals` and `getSectionSpecification`, driven by tests of their own (below). The `category` case keeps the two held categories as literals (non-empty page of exactly that category, premise asserted against the listing) and drives the other ten as the empty counterpart: no other category may come back and, for the run's own findings, the page is empty |
| `test_every_port_implementation_is_whole.py::test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it` | `TypeError: 'NoneType' object is not callable` at `DecisionAdapter._write`. `12916869` (`W56A-INT-DECIDED-SEVERITY-01`, task file in `docs/program/tasks/`) removed `if severity is not None: raise DomainError(DEPENDENCY_UNAVAILABLE, dependency="v2_decision_ledger")` from `append_decision` and passes `severity=severity` into `append_decision_under_key`, because migration `0022` and the ledger now store a severity on an `accept`. The test pinned the removed refusal and, since the refusal precedes nothing any more, reached the `None` session factory | stale pin, not a defect. Replaced by `test_the_decision_adapter_hands_a_severity_to_the_ledger_instead_of_dropping_it` (two cases, `"economic"` and `None`): the rule the old name stated, a severity is never silently dropped, is kept and now means that the value given is the value the ledger receives and the answer reports |

## New and changed tests

- `test_compare_document_versions_reads_the_query_parameters_it_declares`: a port that echoes what
  it received; bare request (only the required parameter) shows the defaults `mode=version`,
  `diff_offset=0`, `diff_limit=10`, no runs; a full request shows `mode=stage`, `diff_offset=7`,
  `diff_limit=3` and both run ids reach the port and come back in the answer; twelve malformed
  queries (parameter absent, empty, malformed ids, `mode=Version`/`other`, `diff_offset` -1/`x`,
  `diff_limit` 0/26/`x`) are `422` and never reach the port.
- `test_price_list_positions_read_the_query_parameters_they_declare`: defaults `(0, 100)`, then
  `offset=120&limit=7` reach the port; `offset=-1`, `limit=0`, `limit=501`, `offset=x`, `limit=x`
  are `422` and never reach the port.
- `MixedRun`'s docstring said "both frozen categories"; it now says two of the twelve.

## Quoted mutations (each repaired guard shown failing; every mutated file restored, byte-identical)

Method: `.local/mut/mut.py` applies one exact-string mutation, runs the named test, and writes the
original text back (git-ignored scratch).

| Guard | Mutation | Failure |
| --- | --- | --- |
| vocabulary | `models.py`: delete `SOUND = "sound"` from `FindingCategory` | `AssertionError: FindingCategory` (`Extra items in the left set: 'sound'`) |
| compare, each of six parameters | `comparison.py`: `mode=mode,` -> `mode="version",`; `diff_offset=diff_offset,` -> `diff_offset=0,`; `diff_limit=diff_limit,` -> `diff_limit=10,`; `source_run_id=source_run_id,` -> `=None,`; `target_run_id=target_run_id,` -> `=None,`; `target_version_uid=target_version_uid,` -> `=version_uid,` | `compareDocumentVersions accepts and ignores: ['mode']` / `['diff_offset/diff_limit']` (twice) / `['source_run_id']` / `['target_run_id']` / `['target_version_uid']` |
| price-list positions | `optimisation.py`: `offset=offset` -> `offset=0`; `limit=limit` -> `limit=100`; the default `limit: LimitParam = 100` -> `= 50` | `listPriceListPositions accepts and ignores: ['offset/limit']` (twice) / `['defaults']` |
| sweep scaffolding | delete `"listPriceListPositions"` from `targets`; delete it from the declared-surface literal | `an operation declaring query parameters is not driven here: ['listPriceListPositions']`; `the contract's query surface moved` |
| category, held and absent values | `adapters.py` `FindingAdapter`: `if category is not None:` -> `if False:` | the sweep names all twelve `category=...` values for `listRunFindings` |
| category, the new absent-value branch alone | `adapters.py`: `views = [v for v in views if v.category == category]` -> `kept = [...]; views = kept or views` (an unmatched category falls back to everything) | the sweep names the ten absent values only (`category=accessibility`, ... `sound`) |
| adapter forwards the severity | `adapters.py` `DecisionAdapter`: drop the `severity=severity,` argument | `the adapter gave the ledger severity='<not passed>', not 'economic'` (and `not None`) |
| | `severity=severity,` -> `severity="economic",` | `the adapter gave the ledger severity='economic', not None` (the `None` control case) |
| | `severity = None` before the ledger call | `the adapter gave the ledger severity=None, not 'economic'` |
| | the removed refusal re-introduced | `DomainError ... transiently unavailable` at `adapters.py:1588` for the `economic` case |

## Failing list before and after

Lane stack: `foundation_instance auditmanager-gate-fix-api`, PostgreSQL 57630, MinIO 61230/61231,
database `auditmanager_gate_fix_api`, bucket `auditmanager-gate-fix-api`, `make up` then `make migrate`
(head `0027_optimisation_proposals`), `make down` at the end and the lane's two volumes removed. Runs
were detached (`nohup setsid .local/runs/run_chunks.sh <label>`, one log and one rc file per chunk
under `.local/runs/<label>/`, git-ignored), one chunk after the other, with the lane's fifteen `.env`
names exported and `PYTHONPATH=src PYTHONUNBUFFERED=1`, as `make gate` does. Command per chunk:
`$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider -rfE[s] --durations=10 <files>`.
Disk free (`df -BM /`) 7952 MiB before the first run (8438 MiB at the start of the session), 7234 MiB before the second; the host was
shared and load was other lanes'.

Before: tree `7bdb254e`, started 13:43, finished 14:04 (+05:00).

| chunk | files | result |
| --- | --- | --- |
| 01 api a-d | `test_[a-d]*.py` | 115 passed |
| 02 api e-j | `test_[e-j]*.py` | 110 passed |
| 03 api l-o | `test_[l-o]*.py` | 126 passed |
| 04 api p-r | `test_[p-r]*.py` | **2 failed**, 109 passed |
| 05 api s-z | `test_[s-z]*.py` | 111 passed |
| 06 api qa_w49 | `qa_w49/` | 49 passed |
| 07 composition port | `test_every_port_implementation_is_whole.py` | **1 failed**, 27 passed (400 s) |
| 08 composition deploy a | bundle transport, deploy image identity, deploy script refusals | 222 passed |
| 09 composition deploy b | deployed stack probe, minio/norms-worker/pgvector image contracts, proxy config and TLS, readiness, reset rehearsal and refusals, session register volume, stand copy refusals | 371 passed, 2 skipped |
| 10 composition application | the other 20 files | 187 passed, 1 skipped |

Red list before (3, all named by the task): `test_query_surface.py::test_the_filter_vocabularies_are_the_frozen_ones`,
`test_query_surface.py::test_every_declared_query_parameter_is_read_by_the_router_that_declares_it`,
`test_every_port_implementation_is_whole.py::test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it`.
The directories revealed **no further red**.

After: tree `049f2fcb` (`11b377b9` plus the merge of `802b3823`), started 14:09 (+05:00).

| chunk | result |
| --- | --- |
| 01-03 | 115, 110, 126 passed |
| 04 api p-r | 113 passed (109 + the two repaired + the two new tests) |
| 05, 06 | 111, 49 passed |
| 07 composition port | 29 passed (27 + the two cases of the replacement test; 422 s) |
| 08 | 222 passed |
| 09 | 371 passed, 2 skipped |
| 10 | **not completed**, see below |

`tests/integration/api`: 622 tests, 2 red before; 624 tests, 0 red after.

## What was not run (stopped on the integrator's instruction)

While chunk 10 of the second run was in progress the integrator reported that the complete gate was
running on this host on `43670efc` (which contains `049f2fcb`) and asked to stop all runs. The runner
and its pytest child were killed by PID (both started by this session), the lane was taken down and
its volumes removed. Therefore, **on the merged tree `049f2fcb` these were not re-run here**:
`test_dashboard_summary_over_a_fresh_deployment.py` and `test_optimisation_proposals_over_http.py`
(both in chunk 10), and the other 18 files of that chunk. On the pre-merge tree `7bdb254e` the whole
chunk was green (187 passed, 1 skipped). The integrator's change to
`test_dashboard_summary_over_a_fresh_deployment.py` and `attachment_disposition()` in
`api/routers/export.py` are therefore covered by the integrator's gate, not by this lane. On the
merged tree these did run green: `test_query_surface.py` (chunk 04), `test_every_port_implementation_is_whole.py`
(chunk 07) and the API suites that touch export/download names (`test_document_content_*`,
`test_streaming_wire_response.py`, `test_served_document_and_health_plane.py`, `test_schema_conformance.py`
in chunks 01 and 05).

Skips seen (`-rs` was on in the second run only): `test_proxy_config_follows_checkout.py:788` (the
disposable proxy stand is opt-in, `AUDITMANAGER_PROXY_STAND=1`), `test_stand_copy_refusals.py:1633`
(a heavy step, `W54_STAND_COPY_WINDOW=1`); the third skip, in chunk 10 of the first run, was not
captured with its reason.

## Risks and known limitations

- A first attempt at the baseline ran without the lane's `.env` names exported and was void: ten
  `tests/integration/api/qa_w49` setup errors (`DATABASE_URL is not set`). `make gate` exports them;
  anyone running these directories by hand must too. The void run is kept as
  `.local/runs/before-noenv-void/`.
- `tests/integration/api/conftest.py::LedgerDecisionAdapter` (the older stand-in behind the `router`
  fixture, not `shipped_router`) still refuses a severity with `v2_decision_ledger`. No test sends
  a severity through it, so nothing is red; it diverges from the shipped adapter and is the next
  place to look if a test ever does. Left unchanged: not part of any red.
- `test_every_port_implementation_is_whole.py` takes about 7 minutes: every parametrised case
  re-parses all 1017 `src` and `tests` files and re-walks the tree per port argument. Not a defect and
  not changed here (it would be a change of the guard's structure); a cached parse is the obvious
  speed-up for whoever owns it.
- The category sweep now takes its "held" set as two literals (`explicit_placeholder`,
  `internal_contradiction`) and asserts that the fixture still publishes exactly those. A fixture
  that publishes a third category turns that assertion red until the literal is extended.

## Integrator instruction

Merge `agent/gate-fix-api-01` at `049f2fcb` (already contains `802b3823`) or its descendant that adds
this report. The checks to re-run on the merged tree: `tests/integration/api/test_query_surface.py`
(35 tests) and `tests/integration/composition/test_every_port_implementation_is_whole.py`
(29 tests), plus chunk 10 of the composition directory, which this lane could not finish.

## Forbidden hotspots

`git diff --stat 802b3823 HEAD` (before this report) lists exactly
`tests/integration/api/test_query_surface.py` and
`tests/integration/composition/test_every_port_implementation_is_whole.py`; this report and the task
file are the only other paths.
