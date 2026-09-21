# `W31-RUS` — every English sentence that can still reach a reviewer

Wave 31. Worktree `/root/w31rus`, branch `agent/w31-rus`, based on `ae2adf5`.
Gate lane `gate-w31c`, ports `56100 / 59700 / 59701`. Logs `/root/w31-logs/rus-*`.

`R-18` (`OWNER_RULINGS_2026-09-17.md` §3.9, amending `ALPHA_ROADMAP.md` §1) requires the
alpha to be shown **in a finished interface, in Russian**, and names *mixed language —
finding content in Russian, labels in English* as a defect a manual test must not meet.

`W31-UI` translated the interface and then reported a wall it could not pass: several
failure `detail` strings are `error.envelope.message`, **the API's own English text**. This
stream establishes the whole set that wall belongs to, decides where each sentence's Russian
must live, and closes the half that is `web/src`'s.

---

## 1. The census

**Method, so it can be re-run and disbelieved.**
`/tmp/.../census.py` (reproduced as the command below) strips comments from every `.ts`/`.tsx`
under a tree, extracts every string literal and JSX text node, keeps those with two or more
ASCII words and a space, and drops any that contains a Cyrillic character. Nothing is piped
through `head` — `OPERATING_CONSTRAINTS.md` §12's fourth shape. The backend half is an `ast`
walk over every `message=` keyword argument in `src/auditmanager/**`, which is the only way a
non-default sentence reaches `ErrorEnvelope.message`.

```
# frontend
python3 - <<'PY'   # comment-stripping literal + JSX extractor, full output, never truncated
PY
# backend
python3 -c "ast.walk over every message= keyword in src/auditmanager"   # 122 sites
# catalog
python3 -c "json.load(contracts/domain/v1/error-codes.json)['codes']"   # 22 codes
grep -c '[а-яА-ЯёЁ]' contracts/domain/v1/error-codes.json               # 0
```

Measured on `ae2adf5`, in `/root/w31rus`. Frontend: **214** multi-word strings, **204**
without a single Cyrillic character — but most of those 204 are `'use client'`, CSS class
templates, `${a}${b}` format strings and generic-type noise my JSX regex caught. The table
below is the reviewer-facing residue after reading every one of them.

### 1.1 Reachable — and mine to fix

| # | Origin | What a reviewer sees | Path to the screen |
|---|---|---|---|
| R1 | `entities/audit-run/model/run-failure.ts` ×10 | `error.envelope.message` as the whole `detail`, under a Russian title | `startRun` / run poll fails → `run-progress` error block |
| R2 | `entities/audit-run/model/run-failure.ts:85,140,151,162` | English **tails** appended to that message — *"Nothing was partially applied. Retrying reuses the same idempotency key;"*, *"No run was created and nothing was resubmitted."*, *"Retrying asks about the same request under the same key. A new key would be a second run."*, *"It is not guessed."* | same |
| R3 | `entities/audit-run/model/run-failure.ts:211,223` | *"Error code 'x' is outside this client's contract. Nothing was retried."* / *"… The run state shown, if any, is the last reading and may be stale."* | unrecognized code, transport failure |
| R4 | `entities/document-version/model/upload-failure.ts` ×9 + `:107,118,129,140,151,214,226` | same two shapes on the upload screen | upload refused → `data-upload-failure` |
| R5 | `entities/project/model/create-failure.ts` ×7 + `:86,115,126,135,166,178` | same two shapes on project creation | create-project form |
| R6 | `entities/project/model/list-failure.ts:80` | *"Error code 'x' is outside this client's contract. Nothing was retried."* | project list |
| R7 | `entities/document-version/model/upload-envelope.ts:39,40` | Two of the four browser-visible upload rules, **in English beside two Russian ones**: *"At most 25 MiB."*, *"At most 30 pages."* | upload panel, always rendered |
| R8 | `entities/document-version/model/upload-envelope.ts:89` | *"That file is larger than 25 MiB."* — the `too_large` precheck, beside a Russian `not_pdf` one | drop an oversize PDF |
| R9 | `entities/project/model/project.ts:47` | *"A project name is at most 200 characters."* beside a Russian `empty` sibling | type a long project name |
| R10 | `entities/document-version/ui/version-panel.tsx:51–66` | Field labels `Ordinal`, `Media type`, `Pages`, `Size`, `bytes`, `SHA-256`, `Published`, `Uploaded as` — **beside `Версия`, `Документ`, `Входной манифест`** | every version detail screen |
| R11 | `entities/document-version/ui/version-row.tsx:46` | *"Version 1 · 12 pages · 4.2 MiB · published …"* | every version list row |
| R12 | `entities/project/ui/project-row.tsx:30` | *"Created … · documents 3"* | every project list row |
| R13 | `entities/audit-run/ui/run-row.tsx:38–46` | *"Created … · terminal …"*, *"Findings 7 · stages 5"* | every run list row |
| R14 | `shared/api/errors.ts:150` | `UnrecognizedApiError.message`, rendered verbatim by `present-failure.ts`'s `ApiFailure` arm | server ahead of client |
| R15 | `shared/api/transport.ts:185,192,233,234,252` | `TransportError.message` — *"HTTP 502 with a body that is not the contract error envelope."*, *"startRun could not reach the API."* — rendered **with an `operationId` in it** | any non-envelope response, any network failure |
| R16 | `shared/api/transport.ts:82,94,125,160,173` | `ClientUsageError.message` — reaches the `unknown` arm of every classifier | a client-side programming fault |
| R17 | `shared/api/credentialed-forward.ts:229` | *"The web server could not reach the API. Nothing was applied and the request may be retried."* — put into a **synthesized `ErrorEnvelope`** and answered `503 dependency_unavailable` to the browser | API container down |
| R18 | `shared/api/credentialed-forward.ts:108,112,116,121,203` | the same, as `404 not_found`'s envelope message | a malformed `/bff/v1` path |

### 1.2 Reachable — and **not** mine this wave

| # | Origin | What a reviewer sees | Owner |
|---|---|---|---|
| N1 | `_pages/review/model/present-failure.ts:69` | `` `${error.errorCode}: ${error.envelope.message}` `` — code **and** English sentence, on the review screen | `_pages/**` = `W31-STYLE`. §5. |
| N2 | `shared/lib/listing-failure.ts:78–128` | **Nine** English titles built from an English noun — *"The request for documents was refused."*, *"There is no such project."*, *"A dependency needed to read runs is unavailable."*, *"Reading documents is not authorized."*, *"You are not permitted to read runs."*, *"Documents could not be read."*, *"The request for versions did not reach the API."* — plus a half-Russian `not_found` detail | `shared/lib` is in neither my `allowed_paths` nor my `forbidden_hotspots` |
| N3 | `widgets/run-progress/ui/run-progress.tsx:134,156` | *"The run terminated `failed`. Nothing was published."* — **the single most-read failure sentence in the application**, sitting directly above `terminalReasonNote`'s Russian sentence | `widgets/**` = `W31-STYLE` |
| N4 | `widgets/run-progress/ui/run-progress.tsx:261` | *"provider mode: live"* | `W31-STYLE` |
| N5 | `widgets/{project,document,version,run}-list/ui/*.tsx` | *"First page"* / *"Next page"* — **eight buttons, four widgets** | `W31-STYLE` |
| N6 | `widgets/finding-list/ui/finding-list.tsx:43–52` | `categoryHeading` returns the **raw contract value**: `internal_contradiction`, `explicit_placeholder`. §6 of my brief forbids deciding this; recorded here as what the reviewer sees. | owner question, `DEBT_REGISTER.md` §2 |
| N7 | `entities/expert-decision/ui/verdict-badge.tsx:44` | renders the raw `Verdict`: `pending`, `accepted`, `rejected`, `needs_manual_review`. Same class as N6. It **is** in my `allowed_paths` and I did not touch it, because the brief forbids translating contract vocabulary. | owner question |
| N8 | `_app/app-frame.tsx:30` | *"Local prototype. One reviewer, no authentication, no tenancy."* — **`R-18` names this footer as a defect by name**, on every page | `_app/**`, ungranted |
| N9 | `shared/ui/states.tsx:41` | *"Correlation id"*, on every error and empty state | `shared/ui/**` = `W31-STYLE` |
| N10 | `shared/ui/states.tsx` + callers | `LoadingState what=` takes an English noun phrase from eleven call sites — `"the run"`, `"the finding"`, `"the decision history"`, `"the document page"`, `"the new project"`, `"the upload"`, `"the run request"` | `shared/ui` + `widgets` + `features` + `_pages` |
| N11 | `features/start-run/ui/start-run-control.tsx:43,62` | *"Start run"* button, *"Correlation id"*. **The button's label is a handle the journey presses** — `tests/e2e/pc01/journey/manifest.json` names it as `text`, and `test_every_control_the_write_half_presses_still_exists_in_the_application` asserts it appears in `web/src`. Translating it turns `make gate` red and the manifest is in the Python tree. | `features/**` = `W31-STYLE`; the repair needs `tests/**` too |
| N12 | `features/upload-document/ui/upload-document-form.tsx:94,144` | *"Display title"* label, *"Correlation id"* | `W31-STYLE` |
| N13 | `_pages/version-detail/ui/version-detail-page.tsx:81` | *"All versions of this document"* | `W31-STYLE` |
| N14 | `app/not-found.tsx:39` | a 40-word English paragraph on the 404 screen | `app/**`, ungranted |
| N15 | `app/layout.tsx:14` | `<title>AuditManager — PC-01</title>`, the browser tab | `app/**`, ungranted |

### 1.3 Reachable — and **backend**, therefore a contract or a `src/` question

| # | Origin | Count | What a reviewer sees |
|---|---|---|---|
| B1 | `contracts/domain/v1/error-codes.json` → `codes[*].summary` | **22** | the default `ErrorEnvelope.message`. `validation_failed`'s is *"The request or payload violates a declared schema, enum, format or invariant. Nothing was created or changed."* |
| B2 | `src/auditmanager/api/routers/handlers.py:110–156` | 14 literals | *"The request body is not valid JSON."*, *"The cursor parameter is not a continuation token from this API."*, *"The {field} filter must be one of: {allowed}."*, … — every edge refusal a browser can provoke |
| B3 | `src/auditmanager/ingest/envelope.py:108–242` | 12 literals | **the upload-refusal sentences the journey drives**: *"The document is encrypted. This prototype accepts unencrypted…"*, *"At least one page carries no extractable embedded text. This prototype never substitutes OCR for a text layer."*, *"The document carries more pages than the accepted envelope allows…"* |
| B4 | `src/auditmanager/api/schemas/{common,decisions}.py` | 4 literals | *"The cursor parameter is not a continuation token from this API."*, *"A comment event must carry a comment."* |
| B5 | `src/auditmanager/api/routers/{documents,multipart}.py` | 5 literals | *"The Range header is not a single satisfiable byte range."*, the upload/body size refusals |
| B6 | `src/auditmanager/decisions/ledger.py:186–246` | 6 literals | *"no published finding carries that identity"*, *"author_label must not be empty"*, … — reachable from the verdict panel |
| B7 | `src/auditmanager/exports/policy.py:88` | 1 | *"this run's state does not publish a result, so there is nothing to export…"* — reachable from the export button |
| B8 | `src/auditmanager/runs/commands.py:164`, `runs/executor.py:595` | 2 | *"the document version's input manifest carries no source.document entry, so there is nothing for source_preparation to read"*, *"the run declares a provider mode the supplied adapter does not provide…"* — both **raise**, and `D-20` makes `execute_run` inline inside `startRun`, so they leave through the `startRun` envelope |

**122 `message=` sites in total** across `src/auditmanager/**`; the ~93 not listed are inside
`analysis/**` and `storage/**`, where the sentence becomes a **stage** failure and the run's
public reading carries only a code — see §2.

---

## 2. The strings that are **not** reviewer-facing, and why

`R-18` is about *"the finish and the language of what is shown"*, and the owner explicitly
excluded logging. Saying which side of that line each string falls is what stops this stream
from sprawling into the whole repository.

| Origin | Verdict | Why |
|---|---|---|
| `src/auditmanager/analysis/**` — 70 `message=` sites | **not reachable** | These raise inside a stage. `RunStatus.stages[]` publishes a *status* and an *error code*, never a message — verified against `contracts/api/v1/openapi.json`'s `StageState`, whose properties are `stage_id, stage_version, status, error_code, started_at, finished_at` — and no message field. The sentence lands in the diagnostic record, which is `R-18`-excluded logging. |
| `src/auditmanager/storage/**`, `runs/repository.py`, `findings/publication.py` | **not reachable as written** | *"the database refused the write"* maps to `internal_error`, whose envelope message the API replaces with the catalog summary unless a call site passes one. These do pass one — so they **are** B-class if a write fails; they are listed as a residual risk in §4 rather than claimed clean. |
| `web/src/shared/config/env.ts:24,42` | **not reachable** | `MissingConfigurationError extends Error`, not `ApiFailure`. Every classifier's `unknown` arm reads `error instanceof ApiFailure ? error.message : 'Клиент получил нечто, что не смог разобрать как отказ по контракту.'` — so the English is **masked by a Russian fallback**. `W31-UI`'s verdict is right; its stated reason ("server-side") is wrong, because `getApiBaseUrl()` is called from `transport.ts:216` **in the browser**. |
| `web/src/shared/config/server-env.ts:59–105` | **not reachable** | Only `app/bff/v1/[...path]/route.ts` calls these, and it catches the throw and answers `unconfigured()` **without forwarding the message**, with a comment saying why: a variable name on a public response is a deployment hint. |
| `app/bff/v1/[...path]/route.ts:78` — *"This deployment presented no credential…"* | **not reachable** | It is a synthesized `authentication_required` envelope, and **all five** consumers (`run-failure`, `upload-failure`, `create-failure`, `list-failure`, `present-failure`) replace that code's message with `AUTHENTICATION_REQUIRED_DETAIL`, which is already Russian. |
| `web/src/shared/api/generated/**` | **not reachable** | OpenAPI `description`/`summary` land there as JSDoc. Nothing renders a JSDoc comment. |
| `contracts/api/v1/openapi.json` `description`/`summary` | **not reachable** | No code path reads them at runtime; the generator reads them at build time into comments. This answers the brief's fourth census bullet: **nothing renders them to a user.** |
| `'use client'`, `am-badge am-badge--…`, `0.4rem 0.5rem`, `${a}.${b}` | **not strings** | directives, class names, style literals and format skeletons. ~150 of the 204. |
| Every `assertNever(value, 'Context')` context label | **not reachable** | thrown only on a contract value the union says cannot exist; it is a crash, not a screen. |
