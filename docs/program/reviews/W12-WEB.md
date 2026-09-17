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
