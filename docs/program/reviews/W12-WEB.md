# `W12-WEB` — mutation sweep of `web/src`

Session `W12-WEB`, wave 12 stage A. Tests only; no product code changed.

- **HEAD on arrival**: `3ebe34dbdeda5873e51c8067d227a4c41e28a025` (`merge: two tests-only
  streams for wave 12 stage A`), worktree `/root/w12web`, branch `agent/w12-web` off
  `origin/dev`.
- **Started**: 2026-09-17 11:29:45 +05:00.
- Baseline before any work: `npx vitest run` in `web/` → **289 passed / 24 files**.

## 1. The harness

`make mutation-copy` has no vitest equivalent, and the brief is right that one should not
be pretended. The obstacle is not the alias — it is that the web suite reaches `web/src`
by **two different routes**, and a harness that only redirects one of them produces
silent false greens:

1. `tests/unit/**` and `tests/contract/csv-columns` import through the `@` alias that
   `web/vitest.config.ts` maps to `./src`.
2. `tests/guards/**` and two contract suites read `web/src` **as text**, resolving their
   root from `tests/guards/lib/repo.ts`:
   `WEB_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..','..','..')`.

A path-alias-only harness (copy `src`, point `@` at the copy) leaves route 2 reading the
*pristine* tree. That is exactly failure mode 4 in the dispatch, and I hit it: the first
prototype had `@` resolving to `/root/w12web-mut/src` while `WEB_ROOT` still pointed at
`/root/w12web/web`. Every source-scanning guard would have been green against a tree that
still had the defect.

### Mechanism actually used

A **full copy of the web tree plus the authorities the suites read**, rebuilt from the
worktree before every single mutation (`/root/w12web-mut/rebuild.sh`):

```
/root/w12web-mut/repo/web/{src,tests,scripts,openapi,package.json,package-lock.json,
                           .nvmrc,.npmrc,FRONTEND_LOCK.json,eslint.config.mjs,
                           tsconfig.json,vitest.config.ts,next.config.mjs,docs}
/root/w12web-mut/repo/web/node_modules  -> symlink to /root/w12web/web/node_modules
/root/w12web-mut/repo/contracts/api/v1/openapi.json
/root/w12web-mut/repo/docs/program/P02_SEAMS.md
```

vitest runs with `cwd=/root/w12web-mut/repo/web` and the tree's **own committed**
`vitest.config.ts`, so the `@` alias resolves relative to the copy and `import.meta.url`
inside `tests/guards/lib/repo.ts` resolves into the copy as well. Both routes move
together. No tracked file in `/root/w12web` is ever edited.

### Evidence the mutated tree is the one under test

The vitest equivalent of printing `auditmanager.__file__`. A probe suite
(`/root/w12web-mut/provenance.probe.test.ts`, copied into the mutation tree at
`tests/probe/` by `rebuild.sh`; **not** committed to the repository, because it must fail
outside the harness) proves both routes at runtime:

- **Route 1 (import)** — it calls `assertNever` from `@/shared/lib/assert-never`, catches
  the throw and reads the module's own frame out of the V8 stack:

  ```
  PROVENANCE module frame: at assertNever (/root/w12web-mut/repo/web/src/shared/lib/assert-never.ts:10:9)
  ```

  The stack frame is emitted by the loader, not by anything the test declares, so it is
  the imported module reporting its own file — `__file__`'s exact analogue.

- **Route 2 (source scan)** — it imports `WEB_ROOT` and `REPO_ROOT` from the *suite's own*
  `tests/guards/lib/repo.ts`, the same bindings every scanning guard uses:

  ```
  PROVENANCE WEB_ROOT: /root/w12web-mut/repo/web REPO_ROOT: /root/w12web-mut/repo
  ```

Both probe assertions compare against `process.env.MUT_WEB_ROOT`, supplied by the driver,
so the probe **fails** if either route leaks back to `/root/w12web`. Every row of the
table below was produced by a run in which both probe assertions passed.

### Baseline of the unmutated copy

The copy with no mutation applied: **291 passed** — the repository's 289, plus the 2 probe
assertions. The copy mechanism reddens nothing by itself.

### Driver

`/root/w12web-mut/mut.py <label> <path> <old> <new>` rebuilds the copy, applies exactly
one textual substitution, refuses to continue if the literal is absent or ambiguous,
**prints the before/after line so the mutation is read back for meaning**, then runs the
suite and names the failing tests by full test name.

## 2. The sweep

Every row below is one single-substitution mutation of the copied tree, applied and run on
its own from a freshly rebuilt copy. `KILLED` names the tests that went red; `SURVIVED`
means the whole suite stayed green; `TIMEOUT` means no test went red and the suite never
finished (see §2.1).

### 2.1 Batch 1 — `run-presentation.ts` and `run-state.ts`

| # | Mutation | Result | What refused |
|---|---|---|---|
| RP-01 | `PROVIDER_MODE_UNKNOWN` sentinel becomes `'live'` | KILLED | `run/provider-mode` — *renders unknown for an absent, null, empty or unrecognised value*, *offers the badge only the two qualifiers it declares*, *covers exactly the contract value set…*, *says an unknown provenance is not treated as live* |
| RP-02 | unrecognised provider mode passes through unnarrowed | KILLED | `run/provider-mode` — *renders unknown for an absent, null, empty or unrecognised value* |
| RP-03 | `badgeProviderMode` passes `unknown` to the badge | KILLED | `run/provider-mode` — *offers the badge only the two qualifiers it declares* |
| RP-04 | the `recorded` caption claims live-call evidence | KILLED | `run/provider-mode` — *says a recorded run is not evidence of a live provider call* |
| RP-05 | `interruptedReason` stops treating `''` as absent | KILLED | `run/provider-mode` — *treats an empty or null reason as no reason* |
| RP-06 | `isRunAnimating` ignores the interrupted reason | KILLED | `run/provider-mode` — *stops on a non-terminal reading that carries an OD-10 interrupted reason* |
| RP-07 | `isRunAnimating` keeps animating a terminal run | KILLED | `run/provider-mode` — *stops on every terminal state* |
| RP-08 | a `partial` run is classified as `published` | KILLED | `run/vocabulary` — *gives published, partial and failed three different outcome kinds*, *reports the recorded degradation set on a partial run* |
| RP-09 | a failed run drops its `terminal_reason` | KILLED | `run/vocabulary` — *reports the terminal reason on a failed run* |
| **RP-10** | **a failed run drops its `interrupted` reason** | **SURVIVED** | — |
| RP-11 | `PC01_STAGE_IDS` order swapped | KILLED | `run/stage-rows` ×2, `run/vocabulary` ×1 |
| RP-12 | `PC01_STAGE_IDS` loses `text_analysis` | KILLED | `run/stage-rows` ×4 |
| RP-13 | `stageRows` marks scheduled stages unexpected | KILLED | `run/stage-rows` — *always produce four rows…* |
| RP-14 | `stageRows` drops unscheduled stages the run reported | KILLED | `run/stage-rows` — *appends it after the four, flagged as unexpected* |
| RP-15 | `stageRows` invents `succeeded` for an unreported stage | KILLED | `run/stage-rows` ×2 |
| **RS-01** | **`TERMINAL_RUN_STATES` loses `cancelled`** | **TIMEOUT** | nothing red; the suite hangs |
| RS-02 | `EXPORTABLE_RUN_STATES` admits `failed` | KILLED | `review/provider-mode`, `run/provider-mode` |
| RS-03 | `EXPORTABLE_RUN_STATES` drops `partial` | KILLED | `export/export-panel` and others |
| **RS-04** | **`stageCarriesError` always returns `false`** | **SURVIVED** | — |
| **RS-05** | **`isTerminalRunState` always returns `false`** | **TIMEOUT** | nothing red; the suite hangs |

### 2.2 Batch 2 — `csv-columns.ts` and the upload envelope

The dispatch asks whether the frontend's column check has the wave-9 defect the Python one
had — comparing the header against the list it was built from. **It does not.**
`tests/contract/csv-columns.contract.test.ts` parses the column table out of
`docs/program/P02_SEAMS.md` §6 and compares `CSV_COLUMNS` against *that*, and the seam
document is resolved from `tests/guards/lib/repo.ts` (an authority read from the test
file's location, which is the correct form). Every reorder, rename, drop and addition
reddened.

The dispatch also asks whether anything notices if the two copies of the list disagree.
Something does, and it is not in this tree: `tests/integration/exports/test_frozen_column_list.py`,
written by `W10-FND`, pins seventeen literals and asserts
`_web_columns() == FROZEN_COLUMNS == tuple(COLUMNS)`, reading
`web/src/shared/api/csv-columns.ts` from the repository root. That gap is already closed.

| # | Mutation | Result | What refused |
|---|---|---|---|
| CSV-01 | columns 1 and 2 swapped | KILLED | `contract/csv-columns` — *matches the frontend constant exactly, in order*, *starts with the identity columns…*, *detects a reordering* |
| CSV-02 | columns 12 and 13 swapped | KILLED | `contract/csv-columns` — *matches the frontend constant exactly, in order* |
| CSV-03 | `current_verdict` renamed to `verdict` | KILLED | `contract/csv-columns` ×2 |
| CSV-04 | `run_state` dropped | KILLED | `contract/csv-columns` ×4 |
| CSV-05 | an eighteenth column added | KILLED | `contract/csv-columns` — *matches the frontend constant exactly, in order* |
| CSV-06 | `byteOrderMark` false | KILLED | `contract/csv-columns` — *records the bytes the seam document fixes*; `export/export-panel` — *states the encoding facts the seam fixes* |
| CSV-07 | delimiter `;` | KILLED | `contract/csv-columns` — *records the bytes the seam document fixes* |
| CSV-08 | line ending `\n` | KILLED | same |
| CSV-09 | null projection `NULL` | KILLED | same |
| **CSV-10** | **`charset` becomes `windows-1251`** | **SURVIVED** | — |
| CSV-11 | `quoting` becomes `none` | KILLED | `export/export-panel` — *states the encoding facts the seam fixes* |
| CSV-12 | download name loses the run id | KILLED | `export/export-panel` — *names the file after the run id* |
| UE-01 | `maxBytes` raised to 26 MiB | KILLED | `projects/upload-envelope` — *states 25 MiB in bytes, not megabytes* (pinned `26_214_400`) |
| UE-02 | `maxBytes` becomes 25 MB | KILLED | same |
| UE-03 | `maxPages` raised to 300 | KILLED | `projects/upload-envelope` ×2 |
| UE-04 | `fileCount` raised to 2 | KILLED | *states 30 pages and one PDF* |
| UE-05 | `mediaType` widened | KILLED | `projects/upload-envelope` ×5 |
| UE-06 | size bound `>` becomes `>=` | KILLED | *accepts a file exactly at the bound and refuses one byte more* |
| UE-07 | the `too_large` check deleted | KILLED | same |
| UE-08 | the `empty_file` check deleted | KILLED | *refuses an empty file* |
| UE-09 | the `not_pdf` check deleted | KILLED | ×2 |
| UE-10 | extension fallback applies even with a declared type | KILLED | *refuses a declared non-PDF* |
| **UE-11** | **`endsWith('.pdf')` becomes `includes('.pdf')`** | **SURVIVED** | — |
| UE-12 | extension match becomes case-sensitive | KILLED | *falls back to the extension only when the browser declares nothing* |
| **UE-13** | **the declared media type is no longer lower-cased** | **SURVIVED** | — |
| UE-14 | the OCR sentence dropped from the stated rules | KILLED | *names every refusal reason before a file is chosen* |
| UE-15 | the encryption rule dropped | KILLED | same |
| UE-16 | the page-count rule dropped | KILLED | same |
| **UE-17** | **the one-PDF / no-archive rule dropped** | **SURVIVED** | — |
| UE-18 | the `too_large` message offers a retry | KILLED | *gives every problem a message that offers no retry* |
| UE-19 | `formatBytes` uses decimal units | KILLED | *formats in binary units* |
| UE-20 | `formatBytes` invents a size for a negative input | KILLED | *does not invent a size for a nonsense input* |

### 2.3 Batch 3 — the evidence surface (`quotation.ts`, `pages.ts`, `admission.ts`, `grouping.ts`)

This is criterion 6's surface and it is where the sweep found most of what it found.

| # | Mutation | Result | What refused |
|---|---|---|---|
| QT-01 | `quotationText` trims the quotation | KILLED | `review/evidence-viewer` — *renders "  leading and trailing whitespace  " byte-for-byte* |
| QT-02 | `quotationText` collapses interior whitespace | KILLED | `review/evidence-viewer` ×4 |
| **QT-03** | **`quotationText` NFC-normalizes the quotation** | **SURVIVED** | — |
| **QT-04** | **code-point length becomes UTF-16 length** | **SURVIVED** | — |
| **QT-05** | **`anchorMatchesQuotation` always true** | **SURVIVED** | — |
| **QT-06** | **`anchorLabel` drops the character range** | **SURVIVED** | — |
| **QT-07** | **`anchorLabel` reports `page_number + 1`** | **SURVIVED** | — |
| **PG-01** | **`declaredPages` sorts lexicographically** | **SURVIVED** | — |
| PG-02 | `declaredPages` stops de-duplicating | KILLED | `review/evidence-viewer` — *offers navigation only to the declared pages* |
| **PG-03** | **`firstDeclaredPage` returns the last page** | **SURVIVED** | — |
| **PG-04** | **`isDeclaredPage` admits every page** | **SURVIVED** | — |
| **PG-05** | **`evidenceOnPage` stops filtering by page** | **SURVIVED** | — |
| PG-06 | `evidenceOnPage` orders by descending ordinal | KILLED | `review/evidence-viewer` — *renders every quotation on the page, not only the first* |
| **PG-07** | **`orderedEvidence` ignores the page** | **SURVIVED** | — |
| PG-08 | `observationProviderMode` hardcodes `live` | KILLED | `review/provider-mode` ×2 |
| AD-01 | admission stops refusing a diagnostic row | KILLED | `review/finding-admission` |
| **AD-02** | **the diagnostic-field check ignores `grounded: true`** | **SURVIVED** | — |
| **AD-03** | **`DIAGNOSTIC_FIELDS` loses `ungrounded_reason`** | **SURVIVED** | — |
| **AD-04** | **`DIAGNOSTIC_FIELDS` loses `grounded`** | **SURVIVED** | — |
| AD-05 | an empty `finding_uid` is admitted | KILLED | `review/finding-admission` |
| AD-06 | a finding with no evidence is admitted | KILLED | `review/finding-admission` |
| AD-07 | `admitFindings` drops the integrity fault | KILLED | `review/finding-admission` |
| AD-08 | `admitFindings` counts nothing as refused | KILLED | `review/finding-admission` |
| GR-01 | grouping renders empty categories | KILLED | `review/finding-admission` |
| GR-02 | grouping follows the reversed contract order | KILLED | `review/finding-admission` |
| **GR-03** | **`countGrouped` counts groups, not findings** | **SURVIVED** | — |

### 2.4 Batch 4 — the decision ledger, intents, the page fragment, selection, failure presentation, the download sink

Thirty-one of thirty-three reddened. The ledger is the best-guarded module in the tree:
every one of its eleven rules has a test that can tell it from a deleted rule.

| # | Mutation | Result | What refused |
|---|---|---|---|
| LG-01 | `compareEvents` drops the `decision_id` tiebreaker | KILLED | `decisions/ledger` — *orders by (recorded_at, decision_id)* |
| LG-02 | `compareEvents` orders newest first | KILLED | `decisions/ledger` |
| LG-03 | `orderEvents` sorts the caller's array in place | KILLED | `decisions/ledger` — *never mutates the array it is given* |
| LG-04 | `isVerdictBearing` keys off `event_type` | KILLED | `decisions/ledger` — *classifies verdict-bearing events by the verdict field, not the event type* |
| LG-05 | a comment overwrites the current verdict | KILLED | `decisions/ledger` — *leaves the verdict standing* |
| LG-06 | `latest_comment` takes the first comment | KILLED | `decisions/ledger` |
| LG-07 | the default projection is `accepted` | KILLED | `decisions/ledger` — *is pending when nothing has judged the finding* |
| LG-08 | `decision_recorded_at` from the oldest event | KILLED | `decisions/ledger` |
| LG-09 | `appendEvent` duplicates a replayed `decision_id` | KILLED | `decisions/ledger` — *treats re-appending the same decision_id as a no-op* |
| LG-10 | `appendEvent` mutates the input list | KILLED | `decisions/ledger` |
| LG-11 | `reconcile` prefers the client projection | KILLED | `decisions/ledger` — *prefers the server projection when one is supplied* |
| IN-01..03 | `intentSignature` drops a part | KILLED | `decisions/intent` |
| **IN-04** | **parts joined by a separator instead of length-prefixed** | **SURVIVED** | — (see §4: the mutation as written was too weak; re-run as `W7-IN-04`) |
| IN-05 | `resolveIntentKey` mints on every call | KILLED | `decisions/intent` — *reuses the key when the same intent is retried* |
| IN-06 | `resolveIntentKey` reuses across intents | KILLED | `decisions/intent` ×3 |
| CT-01..03 | comment check accepts empty / stops trimming / collapses | KILLED | `decisions/intent` |
| PU-01..04 | page fragment rules | KILLED | `review/evidence-viewer` |
| SEL-01..04 | selection rules | KILLED | `review/failure-and-selection` |
| PF-01..03 | failure presentation and retry offer | KILLED | `review/failure-and-selection` |
| DS-01 | `deliverDownload` stops revoking | KILLED | `export/export-panel` — *revokes even when saving throws* |
| **DS-02** | **`deliverDownload` revokes before saving** | **SURVIVED** | — |

### 2.5 Batch 5 — the failure surface, the polling schedule, configuration, keys and caches

This batch found more than the other five together. `shared/api/errors.ts`,
`shared/config/env.ts`, `shared/api/idempotency.ts`, `shared/api/query-keys.ts` and
`entities/expert-decision/model/cache.ts` were read by **no test in `web/tests`** before
this wave. The four `classify*Failure` modules above `errors.ts` are well covered, and
they hide it: each of them re-decides `retryable` itself for the non-`ApiError` cases, so
`UnrecognizedApiError.retryable` and `TransportError`'s default are never read by anything.

| # | Mutation | Result | What refused |
|---|---|---|---|
| ER-01 | `PC01_ERROR_CODES` loses `internal_error` | KILLED | `contract/seam-operations` |
| **ER-02** | **`isErrorCode` admits anything** | **SURVIVED** | — |
| **ER-03** | **`isPc01ErrorCode` admits any catalog code** | **SURVIVED** | — |
| ER-04 | `ApiError.retryable` inferred from the status | KILLED | `projects/upload-failure` ×2 |
| **ER-05** | **`UnrecognizedApiError.retryable` becomes true** | **SURVIVED** | — |
| **ER-06** | **`TransportError` defaults to retryable** | **SURVIVED** | — |
| **ER-07** | **`isErrorEnvelope` stops requiring `retryable`** | **SURVIVED** | — |
| **ER-08** | **`isErrorEnvelope` stops requiring `error_code`** | **SURVIVED** | — |
| **ER-09** | **`hasErrorCode` ignores the code** | **SURVIVED** | — |
| **ER-10** | **`isIdempotencyInProgress` answers for reuse** | **SURVIVED** | — |
| CP-01..05 | every polling-schedule constant and the ceiling | KILLED | `run/polling` — *is 0, 2000, 3000, 4500, 6750, 10125 then capped at 15000*, *has no wall-clock deadline to configure* |
| **PO-01** | **the loop absorbs a non-retryable failure** | **TIMEOUT** | nothing red; the suite hangs |
| PO-02 | the loop rethrows a retryable failure | KILLED | `run/polling` — *absorbs a retryable failure and keeps polling* |
| **PO-03** | **the loop ignores an abort** | **TIMEOUT** | nothing red; the suite hangs |
| PO-04 | the loop stops calling `onUpdate` | KILLED | `run/polling` |
| PO-05 | the loop returns the first reading | KILLED | `run/polling` |
| PJ-01..07 | the project name bounds, the unknown count, the uid check | KILLED | `projects/project` |
| **PJ-08** | **the uid regular expression is unanchored** | **SURVIVED** | — |
| **FI-01** | **`formatInstant` localises instead of using UTC** | **SURVIVED** | — |
| **FI-02** | **an unparseable instant becomes an em dash** | **SURVIVED** | — |
| **FI-03** | **an absent instant becomes the epoch** | **SURVIVED** | — |
| **EN-01** | **a missing API base URL defaults instead of throwing** | **SURVIVED** | — |
| **EN-02** | **the trailing slash is no longer stripped** | **SURVIVED** | — |
| **EN-03** | **`hasApiBaseUrl` reports a blank value as configured** | **SURVIVED** | — |
| **ID-01** | **the `ik_` key prefix is dropped** | **SURVIVED** | — |
| **ID-02** | **every minted key is the same constant** | **SURVIVED** | — |
| **QK-01** | **the findings detail key collides with the runs detail key** | **SURVIVED** | — |
| **QK-02** | **`QUERY_NAMESPACES` loses `findings`** | **SURVIVED** | — |
| **DC-01** | **a decision stops invalidating the run finding list** | **SURVIVED** | — |
| **DC-02** | **a decision stops invalidating the decision history** | **SURVIVED** | — |

### 2.6 Batch 6 — the widgets, the transport and the boundary scanner

| # | Mutation | Result | What refused |
|---|---|---|---|
| EV-01 | the viewer opens an undeclared page | KILLED | `review/evidence-viewer` |
| EV-02 | the viewer falls back to the last declared page | KILLED | `review/evidence-viewer` |
| EV-03 | a finding with no evidence renders an empty pane | KILLED | `review/evidence-viewer` |
| EV-04 | the quotation is trimmed in the component | KILLED | `review/evidence-viewer` |
| **EV-05** | **the anchor line is dropped from the quotation card** | **SURVIVED** | — |
| **EV-06** | **the span-mismatch alert never renders** | **SURVIVED** | — |
| EV-07 | `block_id` is printed on the anchor line again | KILLED | `review/key-leakage` |
| EV-08 | navigation offers every page up to the highest declared | KILLED | `review/evidence-viewer` |
| EV-09 | a missing document URL renders a blank pane | KILLED | `review/evidence-viewer` |
| **EV-10** | **the `<object>` drops the `#page=` fragment** | **SURVIVED** | — |
| EV-11 | the observation provider mode is not rendered | KILLED | `review/provider-mode` |
| DP-01 | the decision panel gains a fourth control | KILLED | `decisions/ledger` — *has exactly three controls and no revoke, undo or clear* |
| DP-02 | the comment control becomes an undo control | KILLED | `decisions/ledger` |
| **DP-03** | **the empty-comment refusal never renders** | **SURVIVED** | — |
| **DP-04** | **the current verdict is derived from the pending intent** | **SURVIVED** | — |
| **DH-01** | **an empty history renders an error, not not-applicable** | **SURVIVED** | — |
| DH-02 | the history renders only the most recent event | KILLED | `decisions/ledger` |
| **DH-03** | **the history stops rendering comments** | **SURVIVED** | — |
| **DH-04** | **the history stops rendering the verdict of an event** | **SURVIVED** | — |
| FL-01 | the empty finding list renders nothing | KILLED | `review/finding-admission` |
| FL-02 | integrity faults are not surfaced | KILLED | `review/finding-admission` |
| **TR-01** | **writes no longer require an idempotency key** | **SURVIVED** | — |
| **TR-02** | **the query string is built from the caller's object** | **SURVIVED** | — |
| **TR-03** | **a missing path parameter becomes the empty string** | **SURVIVED** | — |
| **TR-04** | **path parameters are no longer percent-encoded** | **SURVIVED** | — |
| **TR-05** | **an unrecognised code becomes an `ApiError`** | **SURVIVED** | — |
| **TR-06** | **a non-envelope JSON body becomes an `ApiError`** | **SURVIVED** | — |
| **TR-07** | **an abort is reported as retryable** | **SURVIVED** | — |
| SB-01..03, RB-01 | the boundary scanner's own rules | KILLED | `guards/transport-boundary` — the scanner is run against fixtures that violate every rule, which is why it is the one helper that cannot be hollowed out |

### 2.7 The sweep in one line

**183 mutations, 121 killed, 58 survived, 4 hung.** Method: `/root/w12web-mut/sweep.py`
over a full copy of the web tree rebuilt per mutation, vitest 3.2.7, node 22.23.1, at
`3ebe34d` with no test files added. The four hangs are `RS-01`, `RS-05`, `PO-01` and
`PO-03`, all of them in `pollRunStatus`; §3 explains why a hang and not a red.

## 3. Four mutations that hung instead of reddening, and why

`RS-01`, `RS-05`, `PO-01` and `PO-03` all change when `pollRunStatus` stops. None of them
turned the suite red; all four made it **run forever**, at rising memory, until the
harness killed it at 150 s. Two independent things had to be wrong for that:

1. **The script's own safety net is absorbed.** `polling.test.ts`'s `scripted()` fetch
   throws `polled more times than the script allows` once the script runs out. That throw
   is raised inside the fetch implementation, and `transport.request` catches anything the
   fetch throws and rethrows it as a `TransportError` with **`retryable: !aborted`** —
   that is, retryable. `pollRunStatus` absorbs a retryable failure and continues. So the
   guard against over-polling is converted, by the code under test, into a reason to keep
   polling.

2. **`testTimeout` cannot fire.** The injected `sleep` is `async () => {}`, which resolves
   in a microtask. A loop of `await sleep(...)` never yields to the macrotask queue, so
   vitest's 120 s timer never runs. The process grows until something kills it.

A hang is not a green, so the gate would not have *passed* with the defect — but it would
not have named it either, and on a shared machine a hang reads as a slow lane. The fix is
in a path this session owns: the bound now lives in the injected `sleep`, which the loop
calls **outside** that `try`, so it escapes.

- Red: with `TERMINAL_RUN_STATES` missing `cancelled`, `the loop stops on every terminal
  state > stops on 'cancelled' after one reading` now fails with *the poll loop asked for
  more than 3 readings and did not stop* in 13 ms instead of hanging.
- Green: unmutated, `tests/unit/run/polling.test.ts` — 14 passed, 13 ms.

## 4. What `web/tests` could not reach at all

Before any mutation: **34 of the 110 modules under `web/src` are imported, transitively,
by no test in `web/tests`.** That is 1 352 of 7 604 lines — 18% of the tree — and it
includes every screen the manual PC-01 runbook is driven through.

Measured, not estimated, by resolving the `@/` alias and every relative import from each
test file and taking the transitive closure:

```
cd /root/w12web/web && python3 -              # the script is in the appendix, §11
src modules: 110   reachable from tests: 76   unreached: 34   unreached lines: 1352
```

The unreached set, largest first:

| lines | module |
|---|---|
| 231 | `widgets/run-progress/ui/run-progress.tsx` |
| 169 | `features/upload-document/ui/upload-document-form.tsx` |
| 128 | `features/create-project/ui/create-project-form.tsx` |
| 82 | `features/start-run/ui/start-run-control.tsx` |
| 74 | `widgets/project-list/ui/project-list.tsx` |
| 73 | `widgets/upload-panel/ui/upload-panel.tsx` |
| 53 | `_pages/project-detail/ui/project-detail-page.tsx` |
| 50 | `features/upload-document/model/use-upload-document.ts` |
| 45 | `_app/query-client.ts` |
| 41 | `features/start-run/model/use-start-run.ts` |
| 36 | `features/create-project/model/use-create-project.ts` |
| 35 | `_app/app-frame.tsx`, `_pages/run/ui/run-page.tsx` |
| 30, 27, 26 | the three copies of `use-intent-key.ts` |
| 28, 27, 25 | `app/layout.tsx`, `_app/providers.tsx`, `_pages/projects/ui/projects-page.tsx` |
| ≤20 | the six `app/**` route files and seven barrel `index.ts` files |

`run-progress.tsx` is the file the dispatch points at: it is the only place
`terminal_reason` is rendered, and no test imports it.

This is the boundary of the sweep, and it is stated rather than papered over: §2 mutated
the 76 reachable modules, and §5 records what happens to a mutation inside the other 34.

## 5. Rules that cannot be reddened by construction

Three, and only three. Everything else the sweep found unreddenable was reachable, and has
a guard in §6.

**1. `browserDownloadSink()` — `features/export-run/model/download-sink.ts`.**
Its three statements are `document.createElement('a')`, `anchor.click()` and
`URL.createObjectURL`/`revokeObjectURL`. `web/vitest.config.ts` pins
`environment: 'node'`, and `web/package.json` has no `jsdom`, no `happy-dom` and no
`@testing-library/*`; `node_modules` confirms none is installed. Rule 3 of this session's
dispatch forbids adding one. The module's own docstring makes the same argument and is the
reason the sink is behind an interface at all: `deliverDownload` — the part that carries
the rule about ordering and revocation — **is** tested, against an injected sink, and is
guarded further in §6. What is unreachable is the four-line adapter, and mutating it
proves nothing a DOM would not immediately show.

**2. The three `useIntentKey` hooks — `features/{create-project,start-run,upload-document}/model/use-intent-key.ts`.**
The rule is *the key is stable across renders and changes when the signature changes*. It
needs at least two render passes of the same component instance.
`renderToStaticMarkup` — the only renderer available here — performs exactly one pass and
discards the instance, so `useRef` is fresh on every call and a hook that re-minted on
every render is indistinguishable from one that does not. A second pass needs
`react-dom/client` against a DOM, or `react-test-renderer`; neither exists in this tree
and neither may be added. `W12-WEB` confirmed it empirically as well: mutations `U-06`,
`U-07` and `U-08` replace the stability condition with `if (true)` and survive.

This is worth stating precisely because the rule **is** guarded, in its pure form:
`entities/expert-decision/model/intent.ts`'s `resolveIntentKey` holds the same rule as a
function over a previously recorded intent, and `tests/unit/decisions/intent.test.ts`
reddens on `IN-05` and `IN-06`. The three hooks are hand-copies of that rule rather than
callers of it — each file says so, and says the shared version "belongs in `shared/lib`,
which a Gate B session may not write to". So the rule has one tested statement and three
untestable duplicates. That is a product observation, reported in §7, not a repair.

**3. Anything whose rule lives in a `useEffect`** — `entities/audit-run/api/use-run-status.ts`,
`features/*/model/use-*.ts`. `renderToStaticMarkup` never runs effects. The polling
lifecycle, the cache write on each reading, and the abort on unmount are therefore not
observable from this suite. The loop *inside* the effect is `pollRunStatus`, which is in
`shared/api` and is fully guarded; what cannot be reached is the adapter around it.

## 6. The guards

Eleven new suites under `web/tests`, **151 new tests**, 289 → 440. No product code was
changed. Every expected value is a literal; no test builds its expectation from the
constant it is asserting about, and no test derives its *input* from one either.

Each guard's red is the mutation it was written for, re-applied to the mutation copy after
the guard was committed (`/root/w12web-logs/b7.log`); its green is the same suite on the
unmutated copy.

| Guard | Rules it defends | Literals pinned |
|---|---|---|
| `unit/review/quotation-anchor-and-pages.test.ts` | QT-03..07, PG-01, PG-03, PG-04, PG-05, PG-07, GR-03 | `'café'` vs `'café'`; `'a\u{1F5CE}b'` is 3 code points and 4 units; `'page 7, chars 1200–1232'`; pages `[2, 7, 10]` |
| `unit/review/admission-diagnostic-fields.test.ts` | AD-02, AD-03, AD-04 | the refusal name `'ungrounded_diagnostic'`, asserted on a payload whose **only** fault is the diagnostic key |
| `unit/review/viewer-and-panels.test.ts` | EV-05, EV-06, EV-10, DP-03, DP-04, DH-01, DH-03, DH-04 | `data="<blob>#page=11"` on the `<object>` itself; `'am-quotation__inconsistent'`; `'am-state--neutral'`; `data-verdict="pending"` |
| `unit/review/fixture-conformance.test.ts` | the fixtures themselves | `'^prj_[0-9A-HJKMNP-TV-Z]{26}$'`, `/^b_[0-9]{6}$/`, the ten identifier prefixes |
| `unit/run/terminal-and-stage-vocabulary.test.ts` | RP-10, RS-04, RS-01, RS-05 | `stageCarriesError` truth table written out; `['succeeded','partial','failed','skipped']`; a poll bound of 1 reading per terminal |
| `unit/projects/envelope-encoding-and-delivery.test.ts` | CSV-10, UE-11, UE-13, UE-17, DS-02 | `'utf-8'`; `'annual-report.pdf.exe'` → `'not_pdf'`; `'APPLICATION/PDF'` → accepted; `['create','save:…','revoke:…']` |
| `unit/projects/instant-and-project-address.test.ts` | FI-01, FI-02, FI-03, PJ-08 | `'2026-09-10 09:00:00 UTC'` from a `+03:00` input; `'—'` for absent only |
| `unit/decisions/intent-signature-collision.test.ts` | IN-04 (re-run as `W7-IN-04`) | the colliding pair `('fobs_X', 'a\|b')` vs `('fobs_X\|a', 'b')` |
| `unit/api/failure-surface.test.ts` | ER-02, ER-03, ER-05, ER-06, ER-07, ER-08, ER-09, ER-10 | catalog length 20; PC-01 subset length 10; `'cost_budget_exhausted'` is not a catalog code |
| `unit/api/configuration-and-cache-keys.test.ts` | EN-01..03, ID-01, ID-02, QK-01, QK-02, DC-01, DC-02 | `['projects','versions','runs','findings']`; `['runs','findings',<id>,{}]`; `/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/` |
| `unit/api/transport-rules.test.ts` | TR-01..07 | `https://api.test/v1/runs/run%201%2F2%3Fx%3D1`; `?limit=25` with `api_key` dropped; `calls` empty when a write has no key |

Plus two repairs inside suites this session owns:

- `unit/run/polling.test.ts` — the injected `sleep` is now bounded (§3). Red: `RS-01`
  fails *stops on `cancelled` after one reading* in 13 ms instead of hanging for 150 s.
  Green: 14 passed, 13 ms.
- `unit/review/key-leakage.test.ts` — `expect(markup).not.toContain('blk_')` replaced by an
  assertion against the `block_id` the observation actually carries. The old form looked
  for a prefix the contract cannot produce (`^b_[0-9]{6}$`), so it could not fail.

### The discipline, checked against the four named failure modes

1. *Importing the constant you test.* `CSV_ENCODING.charset` is compared to the literal
   `'utf-8'` **and** to the seam document's prose; `stageCarriesError` is written out as a
   four-row truth table rather than looped over its own vocabulary;
   `PROJECT_UID_PATTERN` is used as the authority for the fixtures and is itself pinned to
   `'^prj_[0-9A-HJKMNP-TV-Z]{26}$'`, so the generated file and the fixture cannot move
   together.
2. *Deriving the input from the constant.* No guard allocates anything sized from a
   constant. The upload guards use fixed 4 096-byte files; the existing
   `maxBytes + 1` case in `upload-envelope.test.ts` was left alone because the sibling
   assertion pins `26_214_400` and `UE-01` proved it reddens.
3. *A mutation that does not mutate.* The driver prints the before and after of every
   changed line and refuses a substitution that is absent, ambiguous or a no-op. It caught
   one of mine: `IN-04` left the inner length prefix in place, so no collision was
   possible and `SURVIVED` was the wrong word for it — re-run as `W7-IN-04` with the
   prefixing removed entirely.
4. *Reading source text from your own file's location.* The harness copies `tests/` as
   well as `src/`, so `tests/guards/lib/repo.ts` resolves `WEB_ROOT` **into the mutation
   tree** — proved at runtime by the probe in §1. The contract and seam documents are read
   from the same place, which is the authority case and is correct.

## 7. Product defects, left unrepaired

Four, all in trees this session does not own. None is repaired here; each is reported with
the mutation that exposed it.

**D-W1 — `stageCarriesError` is declared, exported and read by nothing.**
`src/shared/api/run-state.ts:67`, exported through `src/shared/api/index.ts:58`. No file
under `web/src` or `web/tests` called it before this wave. Its docstring says it exists
"so a stage row does not re-derive it from the presence of `error_code`" — and
`src/shared/ui/stage-status-badge.tsx:39` re-derives it anyway:
`const reason = status === 'succeeded' ? null : (errorCode ?? null);`. So the rule has two
statements, one of which nobody calls. This is the `SORT_KEY` shape `W10-FND` found on the
Python side. Owner: `A5` (`shared/api`, `shared/ui`). Exposed by `RS-04`. It is now pinned
by a guard, which defends the constant but does not make it consumed.

**D-W2 — six more declared-and-unconsumed helpers on the same surface.**
`isPc01ErrorCode`, `hasErrorCode`, `isApiError`, `isIdempotencyInProgress`,
`isIdempotencyKeyReuse` (`shared/api/errors.ts`), `hasApiBaseUrl` (`shared/config/env.ts`)
and `QUERY_NAMESPACES` (`shared/api/query-keys.ts`) are each exported from the public seam
and called from no module in `web/src`. The two idempotency predicates are the ones that
matter: they encode the distinction between a retry under the same key and a terminal
conflict, the distinction the whole idempotency rule rests on, and they were reachable
only through a `hasErrorCode` that a mutation could make answer `true` for any `ApiError`.
Owner: `A5`. Exposed by `ER-03`, `ER-09`, `ER-10`, `EN-03`, `QK-02`.

**D-W3 — `isErrorEnvelope` does not check `contract_version`, which the contract declares
required.** `src/shared/api/errors.ts` checks `error_code`, `message`, `correlation_id`
and `retryable`; `ErrorEnvelope` in `generated/types.gen.ts:187` declares five required
properties, the fifth being `contract_version: "1.0.0-draft.1"`. A body from a server
speaking a different contract version — or from no server at all — is therefore accepted as
an envelope and decoded into an `ApiError`. Whether that is the intended latitude is a
design call for the owner; this session pinned the **current** behaviour rather than
asserting the stricter rule, so a change to it is visible rather than silent. Owner: `A5`.

**D-W4 — the idempotency-key rule has one tested statement and three untestable copies.**
`entities/expert-decision/model/intent.ts` states it as `resolveIntentKey`, a pure function
that `tests/unit/decisions/intent.test.ts` reddens on. The three write features each carry
a hand-copied `useIntentKey` hook instead of calling it, and each file records that the
shared version "belongs in `shared/lib`, which a Gate B session may not write to". Because
the copies are hooks and this tree has no second-pass renderer, they are unreddenable by
construction (§5): `U-06`, `U-07` and `U-08` replace the stability condition with
`if (true)` and survive. Owner: `A5` for `shared/lib`, `B7`/`B8` for the call sites.

### Defects inside `web/tests`, which this session owns and therefore repaired

- **`tests/unit/review/fixtures.ts` violated the contract in three places** while its
  docstring claimed it did not: `PROJECT_UID` was `proj_…` against `^prj_…$`,
  `provenance().stage_id` was `'analysis'` which is not one of the nine `StageId` values —
  hidden from `tsc` by an `as ObservationProvenance` cast, the exact escape the docstring
  promised was absent — and `evidence().block_id` was `'blk_0042'` against `^b_[0-9]{6}$`.
  All three corrected, the cast removed, and `fixture-conformance.test.ts` added.
- **`tests/unit/review/key-leakage.test.ts` carried an assertion that could not fail**:
  `expect(markup).not.toContain('blk_')`, a prefix nothing in the contract produces.
- **`tests/unit/run/polling.test.ts` could hang instead of reddening** (§3).
- A stale comment in `fixtures.ts` says the vitest JSX fix "belongs to `A5` — one line in
  `web/vitest.config.ts`, `esbuild: { jsx: 'automatic' }` — and is reported as a seam
  defect, not repaired here". That line **is** in `web/vitest.config.ts` now, so the
  `globalThis.React` shim beside the comment is redundant. Left in place: removing it is a
  behaviour change to a working suite with no defect behind it, and it is cheap to drop
  when someone is next in that file.

## 8. Anything false in the brief

**1. "wave 11 added `cost_basis`" — not to anything `web/` can see.**
The dispatch's first pointer says `run-presentation.ts` maps run state to what a user sees
and that "wave 3 changed what `terminal_reason` carries and wave 11 added `cost_basis`".
`cost_basis` exists in the backend — `db/migrations/versions/20260914_0004_cost_basis.py`,
`src/auditmanager/runs/executor.py` and eight documents — and appears **nowhere** in the
API contract, in `web/openapi/openapi.json`, or in `web/src`:

```
$ grep -c cost_basis contracts/api/v1/openapi.json   -> 0
$ grep -rn cost_basis web/                            -> (nothing)
$ RunStatus properties: analysis_profile_id, created_at, degradation_set,
  diagnostic_observation_count, interrupted_reason, project_uid, prompt_bundle_id,
  provider_mode, published_finding_count, run_id, stages, state, terminal_at,
  terminal_reason, version_uid
```

There is no frontend mapping for `cost_basis` to have changed, and none was swept. The
other half of the sentence is right: `terminal_reason` is carried raw, by
`runOutcome`'s `failed` arm into `run-progress.tsx:112`.

**2. "ask the same question here" about `csv-columns.ts` — the answer is no, twice.**
The frontend's column check does **not** have the wave-9 defect. It parses the column
table out of `docs/program/P02_SEAMS.md` §6 and compares `CSV_COLUMNS` against that, so
every reorder, rename, drop and addition reddened (`CSV-01`..`CSV-05`). And the brief's
second question — "whether anything notices if the two copies disagree" — was already
answered by `W10-FND`: `tests/integration/exports/test_frozen_column_list.py` reads
`web/src/shared/api/csv-columns.ts` from the repository root and asserts
`_web_columns() == FROZEN_COLUMNS == tuple(COLUMNS)` against seventeen written-out
literals. That gap is closed and the brief does not know it.

**3. Two counts are close but not exact.** `web/src` is **7 604 lines** as stated. It has
**45** `export const` declarations, not 47 (`grep -rhn '^export const ' web/src | wc -l`);
the "17 files that refuse something" is defensible on a narrow reading — 20 files contain
a `throw`, a refusal type or a refusal value, of which 5 throw. Neither number changed
anything about the sweep; recorded so the next brief can use measured ones.

**4. The wave-12 plan and this dispatch disagree about parallelism.** `W12-PLAN.md` §1
argues at length that wave 12 "cannot" run streams in parallel and its table lists two
sequential sessions. `W12-WEB.md` opens "One of three parallel streams in wave 12's stage
A". The reconciliation is in the history — `9f3a90d docs: two tests-only streams for wave
12 stage A, restoring the parallelism` — and the argument holds, because the two added
streams write tests only and so cannot stale a certification. The plan document was not
updated to say so. Not a defect in the work; a stale document that reads as a contradiction.

## 9. Verification: the guards were re-measured, not asserted

Every one of the 62 mutations that survived or hung in §2 was **re-applied to a freshly
rebuilt mutation copy after the guards were committed**, together with the two corrected
forms. `/root/w12web-logs/b7.log`, 64 mutations:

**63 killed, 1 survived.**

The one survivor is `IN-04` as originally written, and it is the third named failure mode
in my own work rather than a gap in the guard. `IN-04` replaced
`.map((part) => `${part.length}|${part}`).join('')` with `.join('|')` while **leaving the
inner `${[...comment].length}:${comment}` prefix in place** — so the comment part is still
length-prefixed and no two distinct intents collide. It is a mutation that does not mutate
the rule. The honest form, `W7-IN-04`, removes the prefixing entirely:

```
-    `${[...comment].length}:${comment}`,
-  ]
-    .map((part) => `${part.length}|${part}`)
-    .join('');
+    comment,
+  ].join('|');
```

and is **KILLED** by `unit/decisions/intent-signature-collision.test.ts > keeps a comment
containing the separator apart from an id containing it`, and by the five-separator case
beside it. `IN-04` is therefore recorded as **NOT A VALID MUTATION**, not as an unguarded
rule.

`W7-RS-01N` is the natural form of `RS-01` — deleting `'cancelled'` from the literal rather
than slicing the array — and is **KILLED** by
`unit/run/polling.test.ts > stops on 'cancelled' after one reading`, in milliseconds,
where the original hung for 150 s.

## 10. The unreached 34, confirmed by mutation

§4's reachability figure is static analysis. Ten mutations inside those modules make it
empirical — `/root/w12web-logs/b8.log`, run against the tree **with all eleven new guards
in place**:

| # | Mutation | Result |
|---|---|---|
| U-01 | `run-progress.tsx` stops rendering `terminal_reason` (replaced by `redacted`) | SURVIVED |
| U-02 | `run-progress.tsx` keeps the activity indicator on a stopped run | SURVIVED |
| U-03 | `run-progress.tsx` offers the review link for every run, including `failed` | SURVIVED |
| U-04 | the upload form stops pre-checking the chosen file | SURVIVED |
| U-05 | the upload form submits a file the pre-check refused | SURVIVED |
| U-06 | the upload intent key is re-minted on every render | SURVIVED |
| U-07 | the create-project intent key is re-minted on every render | SURVIVED |
| U-08 | the start-run intent key is re-minted on every render | SURVIVED |
| U-09 | the upload panel stops stating the envelope before the file picker | SURVIVED |
| U-10 | the run-status hook stops seeding from the cache | SURVIVED |

**Ten for ten.** `U-01` is the one to look at: `terminal_reason` is rendered in exactly one
place in this application, and that place can be made to print a constant with 440 tests
green. `U-03` is the same shape on criterion 7's surface — the review entry point. `U-05`
is criterion 10's: the browser pre-check exists, is well guarded as a function, and the
form is free to ignore it.

Of these ten, `U-06`, `U-07` and `U-08` are unreddenable **by construction** (§5). The
other seven are unreddenable **as the suite is shaped**: `run-progress.tsx`,
`upload-panel.tsx`, `project-list.tsx` and the three form components are ordinary
components that `renderToStaticMarkup` can render exactly as this suite already renders
the evidence viewer, the decision panel and the finding list. `RunProgress` additionally
needs a `QueryClientProvider` around it and a seeded `queryKeys.runs.detail(runId)` entry,
both of which are available — `@tanstack/react-query` is a dependency and the hook reads
the cache in a `useState` initialiser, before any effect.

**This is the recommended next wave and it is not this one.** Seven components on the
delivered PC-01 surface, roughly 700 lines, each carrying criteria 3, 5, 6, 7 or 10. The
sweep swept the 76 modules `web/tests` reaches; it did not sweep the 34 it does not, and
saying so is the result.

## 11. Appendix — reproducing this

### The harness

```
/root/w12web-mut/rebuild.sh                 # full copy of web/ + contracts + P02_SEAMS
/root/w12web-mut/provenance.probe.test.ts   # the `auditmanager.__file__` equivalent
/root/w12web-mut/sweep.py <batch>.json      # one substitution per mutation, read back, run
/root/w12web-mut/b1..b8.json                # the 257 mutations, as data
/root/w12web-logs/b1..b8.log                # every run, with the diff and the failing tests
```

The harness lives outside the worktree on purpose: nothing about it is committed, because
committing it would put a second, competing copy of `web/src` where a later session could
mistake it for the tree.

### The reachability measurement

```python
import os, re
def resolve(spec, frm):
    if spec.startswith('@/'):   base = os.path.join('src', spec[2:])
    elif spec.startswith('.'):  base = os.path.normpath(os.path.join(os.path.dirname(frm), spec))
    else:                       return None
    for c in (base+'.ts', base+'.tsx', os.path.join(base,'index.ts'), os.path.join(base,'index.tsx')):
        if os.path.isfile(c): return c
    return None

def imports_of(path):
    txt = open(path, encoding='utf-8').read()
    specs = re.findall(r"""(?:from|import)\s+['"]([^'"]+)['"]""", txt)
    return [r for r in (resolve(s, path) for s in specs) if r]

seeds = [os.path.join(d, f) for d, _, fs in os.walk('tests') if 'fixtures' not in d
         for f in fs if f.endswith('.ts')]
seen, stack = set(), [i for s in seeds for i in imports_of(s)]
while stack:
    p = stack.pop()
    if p in seen: continue
    seen.add(p); stack += imports_of(p)
allsrc = [os.path.join(d, f) for d, _, fs in os.walk('src') for f in fs
          if f.endswith(('.ts', '.tsx'))]
print(len(allsrc), len(seen & set(allsrc)), len(set(allsrc) - seen))
```

Run from `web/`. At `3ebe34d` it prints `110 76 34`.

### Figures, with the command and the tree

| figure | command | tree |
|---|---|---|
| `web/src` = 7 604 lines | `find web/src -name '*.ts*' \| xargs wc -l` | `3ebe34d` |
| 45 `export const` | `grep -rhn '^export const ' web/src \| wc -l` | `3ebe34d` |
| frontend 289 passed | `npx vitest run` in `web/` | `3ebe34d` |
| frontend 440 passed | `npx vitest run` in `web/` | this branch, HEAD |
| 183 mutations / 121 killed | `sweep.py b1..b6` | `3ebe34d` + harness |
| 64 re-runs / 63 killed | `sweep.py b7` | this branch after the guards |
| 10 unreached / 10 survived | `sweep.py b8` | this branch after the guards |
