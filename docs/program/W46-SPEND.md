# W46-SPEND — the reseal for `F-1`, `F-2` restated as a test, and two backend guards

**task_id:** `W46-SPEND` · **wave:** 46, sub-stage B · **lane:** `gate-w46a`
**worktree:** `/root/w46seal` · **branch:** `agent/w46-spend`, dispatched at `fbea618`
(docs-only on top of `2ffca8c`, which is the base this stream measures against)

Opened before the first measurement, per discipline. Written as the work is found, one
step at a time, and committed after each step so a session restart loses nothing.

## 0. Premises, from `docs/program/reviews/W46-JUDGE-A.md`

- **F-1** (section 3): `getDashboardSummary` answers
  `"cost_basis":"measured","cost_micros":0` on a deployment with **zero** `model_call`
  rows — an invented measurement. `RunRepository.cost()` returns `None` for the same
  state and says why in its docstring; the aggregate's own docstring claims to lift that
  rule and drops the `calls == 0 -> None` branch. Repair, per the integrator's shape:
  `RunActivity.spend` becomes optional, absent when there is nothing to report, present
  with all three fields otherwise. A reseal.
- **F-2** (section 3, `F-2b`): gate red #5,
  `test_every_operation_can_report_not_found_or_validation`, is a rule that shared an
  assumption with its subject. Integrator's ruling: the rule is wrong, the operation is
  right, repair the test, no reseal for this finding.
- **F-5a** (section 3, "What is not guarded"): `_filled`'s absent-is-not-empty mutation
  survives 609/609 — no test observes a response row.
- **F-5c** (section 6, `F-5`): `ff686b1`'s structural historical-section control lost the
  assertion that the live section still yields a claim the guard can read; a premature
  heading blinds the scan and the control stays green.

## 1. Baseline

Taken at this branch's tip `fbea618`, which is `2ffca8c` plus docs-only commits
(`git diff --name-only 2ffca8c..fbea618` touches only `docs/program/DEBT_REGISTER.md`
and `docs/program/dispatch/**`), so this baseline stands for `2ffca8c` as the brief asks.

**First attempt, lost — not a result.** `make gate > /root/w46a-gate.log 2>&1`, tree
clean at `63dbd60`. The battery reached 64% (past foundation, past the known red at
~14%, past a second failing node at ~61%) when the host ran out of memory system-wide:
`dmesg` — `Out of memory: Killed process 1125603 (python)`, `total-vm:1196752kB`. Swap
was 15/15 GB across roughly 54 concurrent sessions on the shared host, `W46-WIRE`'s own
baseline in `/root/w46dash` died the identical way at the identical time. The log's own
tail: `GATE: the canonical battery failed with pytest exit status 137.` **137 is
`SIGKILL`, not a test failure, and no `GATE OK` line exists in this log** — a killed
process is not a measurement and this attempt is discarded rather than read for a
verdict. Confirmed via the integrator (session restarted after the same event) before
re-running: kill only by confirmed-own PID, never by pattern, on a host every project
shares.

Second attempt, after confirming no other `make gate` under `/root/w46*` was running
(`readlink -f /proc/<pid>/cwd` on every `make gate`/`pytest` PID) and the host had
calmed (load ~3, ~3.5 Gi available, swap 5.4/15 Gi). Ran to completion, no OOM:

```
1 failed, 2499 passed, 5 skipped, 4 warnings, 169 subtests passed in 755.26s (0:12:35)
FAILED tests/contract/domain_p02/test_openapi_document.py::test_every_operation_can_report_not_found_or_validation
GATE: the canonical battery failed with pytest exit status 1.
```

**No `GATE OK` line** (`grep -n "GATE OK" /root/w46a-gate.log` → nothing). `run_battery`
failing aborts the recipe before `run_frontend`/`check_whitespace` run — this log says
nothing about the frontend battery or whitespace, only about the backend one, which is
this stream's to fix.

**One red, by node id**, exactly the brief's premise (`F-2`, gate red #5) and nothing
else:

- `tests/contract/domain_p02/test_openapi_document.py::test_every_operation_can_report_not_found_or_validation`
  — `AssertionError: getDashboardSummary declares no client-fault response`.

Reported to the integrator (`SendMessage`, `to: "main"`) with this exact line and list
before starting `S1`.

## 2. `S1` — `F-1`, the reseal

Two commits. `f50e656` — the Python implementation:
`src/auditmanager/dashboard/repository.py` (`_SPEND`'s `calls == 0 -> None` branch,
mirroring `runs.repository.RunCost.cost()`), `dashboard/models.py`
(`DashboardSummaryRecord.run_spend: RunActivitySpendRecord | None`),
`api/schemas/dashboard.py` (`DashboardSummaryView.run_spend` optional,
`dashboard_summary_body`'s `spend` key conditional), `bootstrap/adapters.py`
(`DashboardAdapter.get_summary` carries `None` through), `api/schemas/models.py`
(`RunActivity.spend` moved to `Field(default=None,
json_schema_extra=optional_property)`, the same "optional but not nullable" spelling
`RunStatus.cost_basis` already uses). `069f656` — the reseal itself, one commit, five
documents: `contracts/api/v1/openapi.json` (`RunActivity.required` drops `"spend"`),
`web/openapi/openapi.json` (regenerated, byte-identical to the contract — verified),
the four generated client files (`npm --prefix web run api:generate`; only
`types.gen.ts` changed in substance, `spend: RunActivitySpend` →
`spend?: RunActivitySpend`; the other three only carry the new digest comment), and
`web/FRONTEND_LOCK.json` with all six digests recomputed by `sha256sum` against this
tree (cross-checked against the file's own recorded values — equal) and its
`commit_note` corrected in place (see below).

**Every pin checked, none of them moved** — the surface stays 17 / 20 / 61 and the
error catalog stays 22, so no `D-102`/`D-105` pin has a reason to move:

| pin | file | value found | moved? |
|---|---|---|---|
| surface triple | `tests/contract/api_v1/test_doc_prose_facts.py:316` | `17/20/61` | no |
| migration head | `tests/contract/api_v1/test_doc_prose_facts.py:285` | `0011_document_section` | no |
| `FROZEN_OPERATION_COUNT`/`FROZEN_SCHEMA_COUNT` | `tests/contract/api_v1/test_openapi_conformance.py:89-90` | `20`/`61` | no |
| `PATH_COUNT`/`OPERATION_COUNT`/`SCHEMA_COUNT` | `tests/integration/api/test_served_document_and_health_plane.py:33-35` | `17`/`20`/`61` | no |
| path/operation counts | `tests/integration/api/test_operation_surface.py:61-62,172-177` | `17`/`20` | no |
| error catalog | `tests/contract/domain_p02/test_contract_vocabulary.py:23`, `test_openapi_document.py:497` | `22` | no |

**`commit_note` correction.** The judge (section 2, section 6's findings table) found it
false: it said the two extra pin files
(`test_openapi_conformance.py`, `test_served_document_and_health_plane.py`) moved
*before* the reseal commit `d7ac848`, when `git show --stat d7ac848` carries both
alongside the five documents, in the same commit. Corrected in place, not narrated
beside the false sentence.

**Verification beyond the (still-pending) full gate**, run targeted while no other
lane's gate was active:

```
.venv/bin/python -m pytest tests/contract/domain_p02/test_openapi_document.py \
  tests/contract/api_v1/test_openapi_conformance.py \
  tests/integration/api/test_operation_surface.py \
  tests/integration/composition/test_every_port_implementation_is_whole.py
  -> 1 failed (the known F-2 red, untouched by S1), 147 passed

.venv/bin/python -m pytest tests/integration/api/test_served_document_and_health_plane.py \
  tests/contract/api_v1/test_doc_prose_facts.py \
  tests/contract/domain_p02/test_project_section_catalog.py
  -> 36 passed

npm --prefix web run test:guards -- frontend-lock  -> 15 files, 149 passed (incl. the
  typecheck guard and frontend-lock.guard.test.ts's own 8 assertions)
npm --prefix web run test:contract                  -> 7 files, 104 passed
```

## 3. `S2` — `F-2`, gate red #5 repaired as a test

`a6e3015`. `tests/contract/domain_p02/test_openapi_document.py`'s
`test_every_operation_can_report_not_found_or_validation` replaced by
`test_every_operation_that_takes_input_can_report_a_client_fault` plus
`test_the_input_less_operation_set_is_exactly_the_pinned_one`. `_takes_caller_input`
derives input from the document: a path parameter, a query parameter, a header other
than `X-Correlation-Id`, or a request body. **Measured before committing, not
assumed:** the first version checked only `operation.get("parameters", [])` and called
`getDocumentVersion` input-less, because its `version_uid` path parameter is declared
once on the *path item* (shared with every method of that path), not repeated on the
operation — the same thing `test_every_operation_declares_its_path_parameters` already
merges two lists to see. Fixed before it ever reached a commit.

Two-sided (an input-less operation must declare **none** of `404`/`409`/`422`), and the
input-less set is pinned as `INPUT_LESS_OPERATIONS = {"getDashboardSummary"}`, checked
in its own test rather than folded into the rule, per the brief. `500` stays required,
unchanged.

**Both directions shown failing**, on an in-memory deep copy of the real
`contracts/api/v1/openapi.json`, nothing committed to disk:

```
=== direction 1: 422 added to getDashboardSummary (no input) ===
AssertionError: getDashboardSummary takes no caller input but declares ['422'] --
a response no request can produce

=== direction 2: client-fault codes removed from an input-taking operation ===
mutating: issueToken
AssertionError: issueToken takes caller input and declares no client-fault response
```

Verification: `tests/contract/domain_p02/test_openapi_document.py` → `46 passed` (was
`1 failed`). The full canonical-ignore contract scope —
`tests/contract --ignore=tests/contract/test_cp00_candidate.py
--ignore=tests/contract/test_cp00_final_state.py
--ignore=tests/contract/test_validate_bootstrap.py`, the exact ignores `run_battery`
uses — → `367 passed`. **A trap avoided and reported, not fallen into:** an earlier,
unscoped `pytest tests/contract/` (no ignores) reported `66 failed, 126 errors` — noise
from sweeping in `test_cp00_candidate.py` and friends, which `run_battery` excludes by
name and which fail for reasons unrelated to this stream (CP-00 ratification mechanics,
`PROTOTYPE_PROFILE.md` section 6.3). Not read as a result, exactly the trap the brief
names in its own words.
