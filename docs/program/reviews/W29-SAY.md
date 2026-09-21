# W29-SAY — a failed run says a sentence, and says it without inventing a cause

**Session `W29-SAY`, 2026-09-21. Branch `agent/w29-say` from `origin/dev` at `714da53`.**
**Elapsed 16:12:04 → 16:38 +05 — 26 minutes, measured from this session's first
`date -Is` to its last.**

## 0. The question, and the answer in one line

`W28-LIVE` measured a failed run in a browser and found the screen honest and well built,
with one hole: **it printed an identifier where every neighbouring line is a sentence.**

The repair is made and gated. **A failed run now renders the code *and* a sentence, for
every one of the twenty-two catalog reasons, with an explicit honest default for a
twenty-third.** The sentences are restatements of the frozen catalog and nothing more; the
one for `dependency_unavailable` earns its place mostly by what it refuses to say.

Cold-loaded in a fresh browser tab:

> **The run terminated `failed`. Nothing was published.**
> **Terminal reason: `dependency_unavailable`**
> **A dependency this run needs was unavailable. The catalog groups the metadata store,
> blob storage, a model provider and the worker transport into that one reason, and this
> reading does not record which of them it was — so on its own it is not evidence that the
> model provider is down. The catalog marks the reason retryable, which is permission to
> start the run again rather than a prediction that a second run gets further.**

## 1. Verified before building on it, because the brief said to

Every premise the dispatch carried was re-read in this tree at `714da53`. All four hold,
with one citation off by five lines.

| claim | verdict |
|---|---|
| The screen prints `Terminal reason: dependency_unavailable` and no sentence | **true.** `web/src/widgets/run-progress/ui/run-progress.tsx`, the `failed` arm of `Outcome`, rendered the code in a `<code>` and nothing else. |
| *"a required dependency is unavailable"* is not UI text | **true.** It exists once in the tree, at `src/auditmanager/api/routers/declarations.py:56`, as the OpenAPI **503 response description**. Nothing renders it. |
| Real UI text exists at `run-failure.ts:76` | **true, with the line five off.** `:76` is `case 'dependency_unavailable':`; the string *"The provider this run needs is unavailable."* is `:81`. |
| It is unreachable on this path | **true, and now for a stated reason.** `classifyRunFailure` is only ever handed something *thrown*. A `failed` run is a **200 `RunStatus`**, so nothing throws, so no classifier is consulted. `startRun` answered `202 queued` and the stage failed asynchronously, exactly as `W28-LIVE` wrote. |

## 2. Which terminal reasons are reachable, and how that was established

**From the contract and the schema, not from the executor.**

1. **The API contract.** `contracts/api/v1/openapi.json`, `RunStatus.terminal_reason`:
   *"The catalog code a `failed` run terminated with. Null otherwise."*, typed
   `oneOf: [ErrorCode, null]`. `ErrorCode` is the **whole closed twenty-two-code catalog**,
   not a subset. The wire type is the upper bound and it is the catalog.
2. **The database.** `db/migrations/versions/20260910_0002_pc01_schema.py`:
   `ck_audit_run_terminal_reason CHECK (terminal_reason IS NULL OR <in ERROR_CODES>)`, with
   `ck_audit_run_failed_has_reason CHECK (state <> 'failed' OR terminal_reason IS NOT NULL)`
   beside it. So a stored reason is a catalog member or nothing, and a `failed` row must
   have one.
3. **Today's producers**, read from `src/**` for orientation only:
   `findings/terminal.py::_reason_for` passes through **the failing stages' own
   `error_code`** when they agree on one catalog member, and falls back to
   `analysis_failed` when they disagree or carry none; `runs/executor.py:714`,
   `runs/carrier.py:309`, the gate-did-not-run branch and
   `runs/reconciliation.py`'s `INTERRUPTED_TERMINAL_REASON` all record `analysis_failed`.
   The stage codes raised under `analysis/` and `runs/` today are
   `analysis_input_invalid`, `analysis_failed`, `dependency_unavailable`, `internal_error`,
   `validation_failed`, `unsupported_contract_version`, `cost_budget_exceeded`,
   `dependency_credential_refused`, `not_found`, `idempotency_key_stale`,
   `state_transition_not_allowed` and `partial_result_not_publishable`.

**The render list is keyed on (1) and (2) and deliberately not on (3).** Two reasons, and
the second is the one that matters:

* `W29-RETRY` is live in `src/auditmanager/analysis/` and `runs/` **right now** and may
  change which reason this screen receives. A list measured against today's executor would
  be stale before it merged, and following it there is forbidden here anyway.
* It is the `D-40` defect. `PC01_ERROR_CODES` was a hand-kept subset of a resealable
  surface with nothing reading it; `W15-AUTH` found it missing both authorization codes and
  `W25-SEAL` found it missing `staged_upload_lost`. **A list narrower than its surface
  fails twice before anyone notices.** Covering the catalog cannot be narrower than the
  surface, because the catalog *is* the surface.

`web/tests/contract/terminal-reason-sentences.contract.test.ts` reads
`contracts/domain/v1/error-codes.json` itself and reddens if a code the document declares
has no sentence. A twenty-third code cannot reach this screen undescribed without failing
the gate first.

## 3. The sentences, and what licenses each

Each is a restatement of that code's own `summary` in `contracts/domain/v1/error-codes.json`
— the frozen catalog the database constrains the column against. **No sentence reads a
stage, a provider mode or a document**, because the reading does not carry the facts that
would license it. They live in `web/src/entities/audit-run/model/terminal-reason.ts`, one
table, `Readonly<Record<ErrorCode, string>>` so a reseal stops the file type-checking.

The load-bearing one is `dependency_unavailable`, and its value is in three refusals:

* **It names the class, never a member.** The catalog's own summary groups *"the metadata
  store, blob storage, a model provider or the worker transport"* under this one code. The
  sentence lists all four and says the reading does not record which.
* **It says out loud that this is not evidence the provider is down.** `W28-LIVE` measured
  three of three `recorded`-mode runs failing with this code **while the provider was
  healthy** — the real cause was a missing local recording. A sentence reading *"the
  provider is unavailable"* would be `W27-REFUSE`'s nginx `413` all over again: true of a
  layer, wrong about the cause.
* **Retryability is a permission, not a prediction.** The catalog marks the code retryable;
  in the measured case no number of retries could ever succeed, because the missing thing
  is a file. The sentence says *"permission to start the run again rather than a prediction
  that a second run gets further"*.

The other twenty-one are the same discipline applied where less is at stake: `not_found`
says the reason does not name what was addressed *because the catalog forbids revealing a
resource the caller may not see*; `dependency_credential_refused` says no user of the API
did anything wrong and retrying changes nothing until an operator acts; `analysis_failed`
says it names the outcome rather than one cause and points at the stage table.

**The identifier is kept.** The sentence is added beside the `<code>`, not in place of it.
An operator quoting a code into an issue still can, `W12-WEB`'s U-01 mutation stays
reddened by the existing `run-progress` test, and nobody loses the string they can search.

## 4. The default, and the two other arms

Three arms, all of which say something a reader can act on:

| arm | when | what it says |
|---|---|---|
| `described` | the reason is in the sentence table | the catalog's meaning for that code |
| `undescribed` | anything else | *"This screen has no description for that reason and does not guess one. The code above is the word the run recorded, and this client holds no description for it. Nothing was published, and the stage table below shows which stage carried it."* |
| `absent` | a `failed` reading carrying no reason at all | *"This reading carries no terminal reason. A failed run is required to record one, so this reading is missing something the contract obliges it to carry. Nothing is assumed in its place."* |

**The `undescribed` arm is reachable, not decorative.** The generated client casts the
response body and never validates it, so a deployment one reseal ahead of this client puts
a string here that `ErrorCode` says cannot exist. `W15-AUTH` found five classifiers ending
in `server_error` for want of a branch; this is the branch, and it carries the code it
actually received rather than a generic apology.

**It does not borrow a neighbour's sentence**, which is asserted rather than intended:
mutation M4 points the default at the `dependency_unavailable` sentence and dies.

## 5. Every mutation, and the test that killed it

Six mutations, each **applied to the tree, run, and reverted** — never reasoned about. The
runner refuses to start on a dirty tree and asserts a clean revert afterwards.

| | mutation | result |
|---|---|---|
| **M1** | all twenty-two sentences replaced by one constant | **30 failed**, of which **22 are the named per-code rendered cases** — `renders a sentence for validation_failed`, `… for not_found`, one per code |
| **M2** | `dependency_unavailable` alone reworded to the `run-failure.ts` text, *"The provider this run needs is unavailable."* — the plausible wrong repair | **7 failed**, all of them the `dependency_unavailable` case and its four refusal guards. **The other 21 per-code cases stayed green**, which is what "able to fail per rendered sentence" means |
| **M3** | the `undescribed` arm returns `''` — the default prints nothing | **3 failed**, including the rendered default case |
| **M4** | the `undescribed` arm returns the `dependency_unavailable` sentence | **4 failed**, including *"does not borrow the sentence of a code it does know"* |
| **M5** | one code deleted from the sentence table | **4 failed**, including the contract guard *"describes every code the catalog declares"* |
| **M6** | the `<p>` removed from the widget — the module is right and nothing renders it | **25 failed**: every rendered case, while the pure-function tests stayed green, which is the correct split |

### M1 found a defect in the tests before it found one in the code

The first draft of the rendered suite asserted
`expect(markup).toContain(terminalReasonNote(code).sentence)`. That is a **re-capture, not
an assertion**: the expectation moves with the implementation, so M1 left every per-code
case green and reddened only seven tests elsewhere. Commit `3a09f9e` replaced it with a
literal phrase per code, declared in the test file; M1 then reddened 22 named cases. This is
the `characterization can freeze a defect` shape, caught by running the mutation rather than
trusting the suite.

### M5 found a defect in the code

The lookup tested `ERROR_CODE_VALUES.has(reason)` and *then* indexed the sentence table —
two sources for one fact. A code present in the generated enum and absent from the table
returned `sentence: undefined`, and the screen rendered **an empty paragraph**: the silent
hole this module exists to close, reintroduced by the check meant to close it. `tsc` refuses
that state, but the runtime should not depend on `tsc` for it. Commit `bda3162` keys
membership on the table itself. Both defects were discovered only by running the mutation,
which is what the task file said would happen.

## 6. Measured in a browser, cold, reading the body and never the status

**The acceptance reading was taken through Chromium**, one cold process per screen, own
profile, no cache, via `tests/e2e/pc01/journey/look.mjs` over `cdp.mjs` — read first, both
untouched, and `look.mjs` asserts nothing by design. `innerText`, never a status code
(`D-28`).

**No paid call, and no image build.** The brief forbids building images, the disk had
~11 GB, and the owner's stand on 31500 is in `proxy` mode where every run spends real money.
So the screen was driven against a Next production build of **this tree** (`next build`,
exit 0) whose `/bff/v1` route was pointed at a 40-line stand-in serving **one** run reading:
the `recorded`-mode failed envelope `W28-LIVE` recorded verbatim from a real run, with only
the identifiers rewritten. The stand-in computes nothing and decides nothing.

**What that proves and what it does not.** It proves the screen renders these sentences for
these envelopes, in a real browser, on a cold load, from a real build. It does **not**
re-prove that the backend produces that envelope — `W28-LIVE` measured that three times out
of three against a deployed stack, and nothing in `web/**` could change it.

Four readings, all exit 0, **zero console errors and zero uncaught page errors** in each:

| reading | what the screen said |
|---|---|
| `dependency_unavailable` | the code, then the four-class sentence quoted in §0 |
| `analysis_failed` | the code, then *"The analysis ended in the failed terminal state. This is the general execution failure: it names the outcome rather than one cause…"* — **a different sentence, in a browser, for a different code** |
| `recording_not_found_for_this_document` (off-catalog) | the code, then *"This screen has no description for that reason and does not guess one…"* |
| no `terminal_reason` at all | *"Terminal reason: not reported"*, then *"This reading carries no terminal reason. A failed run is required to record one…"* |

**Every sentence `W28-LIVE` measured and praised is still there, verbatim** — the provider
mode caption, the cost paragraph (*"That is not a cost of zero — nothing was spent here
because nothing was called, and the two are different claims."*), the review panel, the
stage table and *"Not polling. This reading is final."* A repair that broke a neighbouring
true sentence would be a net loss, so that is asserted too.

Both processes were stopped **by PID**; `web/.next` was removed afterwards.

## 7. The boundary this session stopped at

**The screen cannot say why the dependency was unavailable, and no wording can fix that.**
`dependency_unavailable` is one code covering four dependency classes, and neither
`RunStatus` nor `StageState` carries a `details` object at all — the catalog declares
`safe_detail_keys: ['dependency']` for this code, but that key lives on the **error
envelope**, which a 200 run reading is not. So the distinction the useful sentence would
need — *your document is fine, the provider is fine, this deployment has no recording for
it* — **is not in the envelope**, and inventing it is exactly what this task forbids.

**What the envelope would have to carry**, in order of cost:

1. **A safe classifier on the terminal.** `RunStatus` gains an optional
   `terminal_detail: { dependency: string }`, restricted to the same `safe_detail_keys` the
   catalog already declares for the reported code — no host, URL, credential or vendor
   endpoint. Then the sentence can name the dependency class the run actually lost. This is
   a `contracts/api/v1/openapi.json` reseal plus a column; **it is the smallest honest fix**.
2. **A distinct catalog code** for a replay miss, on the `staged_upload_lost` precedent:
   `R-8` added a twenty-second code precisely because two situations demanding opposite
   operator responses were answering one code with byte-identical envelopes. That is the
   same argument, and this is the same shape of defect one layer down.

Both are `contracts/**` changes and this session owns no contract slot. **Registered, not
attempted.**

The related `W28-LIVE` Finding 3 — `RecordedAdapter` raising the *transport* code for a
local file miss, and the executor then retrying it on a 2 s + 8 s ladder for ten seconds —
is the reason the wrong word is being displayed in the first place. It is in `src/**`, and
`W29-RETRY` is live there. Untouched, by instruction.

## 8. What is not true in the task file

* **`run-failure.ts:76`** is `case 'dependency_unavailable':`. The sentence *"The provider
  this run needs is unavailable."* is at **`:81`**. The claim is right, the line is five off.
* Everything else the brief asserted was checked and holds: the missing sentence, the
  OpenAPI 503 description, the unreachable classifier, `W27-WEB`'s derivation of
  `PC01_ERROR_CODES`, and `W28-LIVE`'s verbatim reading of the screen.
* One thing the brief implies but does not say, and it turned out to be the design
  question: **`PC01_ERROR_CODES` is not the right list for this screen.** It is the set of
  codes the fifteen PC-01 operations can put in an **error envelope**; `terminal_reason` is
  a field on a **200 response** and is constrained by the catalog, not by that subset. Four
  catalog codes are outside `PC01_ERROR_CODES` and still legal here. Keying the render list
  on `PC01_ERROR_CODES` would have shipped a list narrower than its surface for the third
  time in this programme.

## 9. The gate

`make gate FOUNDATION_PYTHON=/usr/bin/python3.12` on lane **`gate-w29b`** (POSTGRES_PORT
56050, S3 59650/59651, `audit_w29b`, bucket `auditmanager-gate-w29b`), exit read from `$?`
after a redirect and never through a pipe. **16:29:12 → 16:34:46 +05, 5 min 34 s.**

```
1998 passed, 5 skipped, 1 warning, 169 subtests passed in 279.34s
35 passed in 30.03s
Test Files  52 passed (52)     Tests  764 passed (764)
GATE OK: battery, foundation, frontend and whitespace all pass
GATE_EXIT=0
```

**Against the stated base — battery 1998 / 5 / 169, foundation 35, frontend 715 in 49
files:** the backend halves did not move by a single test, which is the expected result for
a change confined to `web/**`, and also a check that nothing here is being collected by the
battery. The frontend moved **+49 tests in +3 files**, all of them this session's.

Provisioning, in that order and each believed only after the next one:
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` (exit 0), then
**`.venv/bin/python -c "import boto3"` → `boto3 ok 1.43.90`**, then
`npm --prefix web ci` (exit 0, 184 packages, 4 s). `npm run typecheck` and `npm run lint`
both exit 0.

The lane was torn down with `make down` (exit 0); no `w29b` container or volume remains.

## 10. For the register

| | |
|---|---|
| **The `failed` run screen renders a bare error code and no sentence** | **CLOSED by this session.** `W28-LIVE`'s check command — `journey.mjs … --manifest …/w28-recorded-redden.manifest.json` → exit 1 — was written against the two sentences that screen *could* have said, neither of which is the one it now says; the live check is `npm --prefix web test` with the three files added here. |
| **`dependency_unavailable` cannot name its dependency** | Open, `contracts/**`. `RunStatus` and `StageState` carry no `details`; §7 gives the two shapes that would close it. |
| **A missing recording is reported with the transport code** | Open, `src/**`, `W28-LIVE` Finding 3. Not touched: `W29-RETRY` is live in `runs/`. |
| **Concurrent sessions share one scratchpad directory** | Observed, not a code defect. Another live W29 session (lane `gate-w29a`) was writing `npmci.log` and `bootstrap.log` under the same scratchpad path as this one, at the same minute. This session moved its own work into a private subdirectory after noticing. A session that trusted a log file it did not write would read someone else's exit code. |

## 11. Forbidden hotspots

`git diff --stat origin/dev...HEAD` is **seven files**, all inside `allowed_paths`:

```
docs/program/reviews/W29-SAY.md
web/src/entities/audit-run/index.ts
web/src/entities/audit-run/model/terminal-reason.ts      (new)
web/src/widgets/run-progress/ui/run-progress.tsx
web/tests/contract/terminal-reason-sentences.contract.test.ts   (new)
web/tests/unit/run/terminal-reason.test.ts                      (new)
web/tests/unit/screens/run-terminal-reason.test.ts              (new)
```

**Nothing under `src/**`, `contracts/**`, `infra/**`, `tests/e2e/**`, `artifacts/**`, the
`Makefile`, `DEBT_REGISTER.md` or `CURRENT_STATE.md` was changed.** `tests/e2e/**` was
**read and run** — `look.mjs` and `cdp.mjs` — and not edited. **`web/FRONTEND_LOCK.json`
did not move and did not need to**: it seals the toolchain pins, the OpenAPI bytes, the
generator and the four generated client files, and this session touched none of them. No
tag, no checkpoint, no push.
