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

---

## 3. What I built, and the red each guard was watched to produce

### 3.1 `web/src/shared/api/catalog-message.ts` — the sentence the screen says instead

A `Readonly<Record<ErrorCode, string>>` over the **whole 22-code catalog**, each entry a
Russian restatement of that code's own `summary`, plus `catalogMessage(code: string)` and
`UNDESCRIBED_MESSAGE_PREFIX`. Exported from `shared/api/index.ts`. It stands where the four
entity classifiers printed `error.envelope.message`.

**Which list it is keyed on, argued from what constrains the field.** `transport.ts`'s
`decodeFailure` constructs an `ApiError` **exactly when `isErrorCode()` passes**, and
`isErrorCode` tests membership of `ERROR_CODE_VALUES` — all 22 — not `PC01_ERROR_CODES`.
Every classifier consuming this map has a `default:` arm that fires for any code it has no
branch for, and **six** catalog codes sit outside `PC01_ERROR_CODES`:
`unsupported_contract_version`, `required_norm_unavailable`,
`partial_result_not_publishable`, `cost_budget_exceeded`, `stale_attempt`,
`execution_token_invalid`. Keying on the narrower list would leave those six rendering
English or nothing. This is `W29-SAY`'s argument re-measured for a different field, not
copied from it — `W30-LISTS` §4 records that `W29-SAY` was *not* a member of the stale-list
class at all, and that its real defect was *a consumer reading the right set for the wrong
question*. That is the defect this section is trying not to commit.

**What the substitution loses, stated rather than discovered.**
`src/auditmanager/shared/errors/envelope.py:126` is
`screen_message(message) if message is not None else code.summary`. The envelope carries no
record of which of the two it is, so **the client cannot tell a catalog summary from a
custom backend sentence** and this substitution replaces both. 122 call sites in
`src/auditmanager/**` pass a custom `message`. What is **not** lost is the discriminating
fact: every classifier still renders `classifiers(error.details, [...])` beside the
sentence, and the three `expects_rendered_from_envelope` entries the browser journey
depends on — `not_encrypted`, `every_page_has_extractable_text`, `page_count` — are all
`details.constraint` values, not words of the English prose. What **is** lost is prose like
`ingest/envelope.py`'s *"This prototype never substitutes OCR for a text layer."* §4 prices
making the backend say that in Russian.

### 3.2 The residue `W31-UI` left, closed

`run-failure.ts`, `upload-failure.ts`, `create-failure.ts`, `list-failure.ts`,
`upload-envelope.ts`, `project.ts`, `version-panel.tsx`, `version-row.tsx`,
`project-row.tsx`, `run-row.tsx`, `errors.ts`, `transport.ts`, `credentialed-forward.ts` —
census rows R1–R18. Each file **looked** translated, which is why a file-by-file pass left
them: a Russian title with an English tail appended, `<Field label="Media type">` two lines
below `<Field label="Версия">`, and two of four upload rules in English beside two in
Russian.

### 3.3 `web/tests/contract/catalog-message.contract.test.ts` (9 tests)

Derived from `contracts/domain/v1/error-codes.json`, never from the module. Asserts: every
catalog code is described; the catalog document and the generated enum agree; the six
non-PC-01 codes are described **by name**; every sentence carries Cyrillic and does not
contain its code's English summary; each sentence is distinct, ends in a full stop, and
does not echo its own identifier; **no sentence equals `terminal-reason.ts`'s** for the same
code; and a rogue code says it is undescribed rather than borrowing a neighbour.

### 3.4 `web/tests/guards/presentation-language.guard.test.ts` (4 tests)

Not a list of strings. It walks `web/src/entities/**` and `web/src/shared/api/**` (less
`generated/**`, which is produced from the contract and never rendered), strips comments,
extracts every string literal and — in `.tsx` only — every JSX text node, and fails on
anything reading as English prose. **Prose is decided by a closed list of English function
words**: two or more distinct members, as whole words, plus a space. A Latin-letter test
would fire on `am-badge am-badge--ok`, `application/pdf` and `0.4rem 0.5rem`, and the
allowlist needed to quieten it would grow past the next real sentence. `NOT_PROSE` has
**one** member and says that a second is a reason to re-read the guard.

Its discriminator is exercised in the file itself, both directions, and it asserts **a path
set** — that `run-failure.ts` and `catalog-message.ts` are among the files read and that no
`generated/` path is — rather than an exit code.

### 3.5 The three mutations, and their red verbatim

Run against the worktree's own copies with the originals restored immediately after; the
tree was `git status --porcelain`-clean before and after each.

**M1 — drop `stale_attempt` from the map** (what a reseal adding a 23rd code looks like from
the other side; `Record` was weakened to `Partial<Record>` so the mutation could compile,
which is itself the point of the `Record`). `/root/w31-logs/rus-mutation-M1.log`, **3 of 9
red, `EXIT=1`**:

```
 × the sentence set is the frozen catalog, read from the contract > describes every code the catalog declares
   → contracts/domain/v1/error-codes.json declares these and catalog-message.ts has no
     sentence for them. A failure carrying one would render the undescribed default where
     the screen used to render the API English.: expected [ 'stale_attempt' ] to deeply equal []
 × ... > is keyed on the whole catalog and not on the PC-01 render subset
   → stale_attempt renders the undescribed default
 × a code outside the catalog says so instead of guessing > is not what any catalog code renders
```

**M2 — put one English sentence back** into `upload-failure.ts`, the exact shape `W31-UI`
left behind. `/root/w31-logs/rus-mutation-M2.log`, **1 of 4 red, `EXIT=1`**:

```
 × no English prose reaches a reviewer from the paths W31-RUS owns > finds none in web/src/entities and web/src/shared/api
   → R-18 requires the alpha in Russian. These strings read as English prose and the paths
     they sit in are W31-RUS’s. …: expected [ Array(1) ] to deeply equal []
   + [
   +   "web/src/entities/document-version/model/upload-failure.ts:108  \" Nothing was published: no version, no manifest and no readable object.\"",
   + ]
```

**M3 — collapse this map into `terminal-reason.ts`'s**, by pasting that module's
`dependency_unavailable` sentence over this one. `/root/w31-logs/rus-mutation-M3.log`,
**1 of 9 red, `EXIT=1`**:

```
 × it is not a second copy of terminal-reason.ts > shares no sentence with the terminal-reason table
   → dependency_unavailable: catalog-message.ts and terminal-reason.ts render the same
     sentence: expected 'Зависимость, нужная прогону, была нед…' not to be
     'Зависимость, нужная прогону, была нед…' // Object.is equality
```

M2 also caught a defect in the guard itself before it was committed: its first run reported
`entities/expert-decision/model/ledger.ts:50` as prose. It was not — the JSX-text pattern
`>text<` matches a **generic** closing in a `.ts` file. The guard now scans JSX text in
`.tsx` only, and says so where the parameter is declared. It also reported
`admission.ts`'s `"not_a_finding"`, which carries `not` and `a`; the space test separates
that from prose without an allowlist.

### 3.6 Six existing tests repaired, and how

They asserted the English I replaced. Each was repaired to assert **the claim**, not to
re-capture the new bytes — `MEMORY.md`'s *characterization can freeze a defect*. The one
that mattered is `upload-failure.test.ts`'s *"renders the server reason rather than a
generic sentence"*, which asserted the envelope message **and** `page_count_at_most_30`. Its
name's claim survives the change and is now what it checks: the constraint is still
rendered, the detail still differs from two other codes' details, it carries Cyrillic, and
it no longer carries the fixture's English message.

---

## 4. What I did not build, priced in files and in resealing

### 4.1 The backend's own sentences — a `src/` change, not a contract change

Census rows **B2–B8**, roughly **29** English literals in `src/auditmanager/api/**`,
`ingest/envelope.py`, `decisions/ledger.py`, `exports/policy.py`, `runs/commands.py` and
`runs/executor.py`. These are **custom `message=` values**, not catalog summaries, and they
are the ones a reviewer meets most often — `ingest/envelope.py`'s twelve are what the upload
refusals say.

**Cost: six `src/` files, no contract, no reseal, no lock.** `message=` is a free-text
parameter the catalog does not constrain; `shared/errors/envelope.py` screens it for unsafe
content and does not require English. So the whole of B2–B8 can be made Russian without
touching `contracts/**` or `web/FRONTEND_LOCK.json` at all.

**It has a real consequence and it must be decided, not defaulted.** These sentences are
also what the **API's own consumers** read, and `tests/**` asserts some of them (e.g.
`test_pc01_journey_conformance.py` reads `refusals.cases[].constraint`, not the prose, but
other suites do assert message text). A pass over them is one wave, and its risk is
entirely in the Python battery, not in the seam.

**And note which way this cuts against §3.1.** If B2–B8 become Russian, then
`catalogMessage()`'s substitution starts discarding a *Russian* sentence that is more
specific than the one it renders. At that point the right shape is for the classifiers to
render `error.envelope.message` again and for `catalog-message.ts` to become the fallback
for the codes that have no custom message. **That is a reason to sequence B2–B8 before any
further work here, not a reason to delay it.**

### 4.2 The 22 catalog summaries — a two-document change plus a frontend reseal

Census row **B1**. Making `contracts/domain/v1/error-codes.json` carry Russian summaries,
or carry a second `summary_ru` field, is **not** the same size of change and the owner
should be able to price it rather than discover it:

1. `contracts/domain/v1/error-codes.json` — the catalog itself. `status: draft_candidate`,
   `frozen: false`, `candidate_revision: 7`, so a revision bump is the declared mechanism.
2. `contracts/api/v1/openapi.json` — the response component descriptions name codes and
   restate their meanings; `tests/contract/api_v1/` and
   `web/tests/contract/pc01-error-codes.contract.test.ts` both **derive** from those
   descriptions.
3. **`web/FRONTEND_LOCK.json` records the contract's sha256 by hand.** It currently pins
   `openapi.sha256` and `openapi.snapshot_sha256` to
   `68762ec8…f1513`, plus `web/openapi/openapi.json` as a committed snapshot, the generator
   script's own sha256, and `content_commit c87a630`. Any touch of `openapi.json` invalidates
   all of it and forces a regenerate-and-reseal.

**The history that makes this worth writing down.** `W20-CODE` discovered the lock coupling
the hard way, and **`R-11` reverted a wave's work over it**; `D-18` is the register row, and
`W30-LISTS` §4 classifies it as its own defect class — *a hand-maintained digest whose cost
appears only at change time* — distinct from the stale-subset class. `R-13` has already paid
one reseal this programme, and `R-18` itself warns that *"a frontend reseal is likely… to be
planned from the start rather than discovered at the end."*

**So: B1 is a three-artifact change with a mandatory reseal; B2–B8 is a six-file change with
none.** They are not one decision and should not be taken as one.

### 4.3 `shared/lib/listing-failure.ts` — nine sentences, one ungranted file

Census row **N2**, and the largest single block of reviewer-facing English left in `web/`.
Nine titles built by interpolating an English noun into an English frame — *"There is no
such project."*, *"You are not permitted to read runs."* — reachable from the document,
version and run lists, i.e. from three of the six screens on the `R-18` path.

**Cost: one file, about 40 lines, no contract, no reseal.** It is not in my
`forbidden_hotspots` and not in my `allowed_paths`, so I did not touch it. It needs
`catalogMessage()` wired in exactly as the four entity classifiers now have it, plus Russian
nouns for `collection`/`parent`, which are supplied by its callers in `widgets/**` — so it
is **`W31-STYLE`-adjacent**, and sequencing it after `W31-STYLE` lands is cheaper than
racing it.

### 4.4 `transport.ts`'s `operationId` in a user sentence — reported, not fixed

`TransportError`'s sentences are now Russian but still read *"Запрос `getRunStatus` не дошёл
до API."* `R-18`'s defect list names *identifiers such as `prj_01M2WW…` set in body text
beside content*. An `operationId` is a milder instance of the same thing. Removing it is a
**behaviour** change, not a translation, and it removes the only handle an operator has for
which call failed — so it is a decision, priced at one file and about six lines, and left to
whoever owns the error-presentation shape.

---

## 5. The collisions with `W31-STYLE` I stopped at

`W31-STYLE` is live in `web/src/widgets/**`, `_pages/**`, `features/**`, `shared/ui/**` and
the CSS. Naming these is the deliverable; the integrator sequences them.

| # | File | What is needed | Why I stopped |
|---|---|---|---|
| C1 | `_pages/review/model/present-failure.ts:69` | one line: `` `${error.errorCode}: ${error.envelope.message}` `` → the code plus `catalogMessage(error.errorCode)`. `catalogMessage` is exported from `@/shared/api` and this file already imports from there. | `_pages/**` is `W31-STYLE`'s. **The module it needs is built and exported; only the call site is out of reach.** This is a one-line follow-up for whoever holds `_pages` next. |
| C2 | `widgets/run-progress/ui/run-progress.tsx:134,156` | *"The run terminated `failed`. Nothing was published."* → Russian. It sits **directly above** `terminalReasonNote`'s Russian sentence, so the screen currently reads English-then-Russian in one block. | `widgets/**` |
| C3 | `widgets/run-progress/ui/run-progress.tsx:261` | *"provider mode:"* → Russian. The value beside it is a contract value and stays. | `widgets/**` |
| C4 | `widgets/{project,document,version,run}-list/ui/*.tsx` | *"First page"* / *"Next page"*, eight buttons across four widgets | `widgets/**` |
| C5 | `shared/ui/states.tsx:41` + eleven callers | *"Correlation id"*, and `LoadingState what=` taking an English noun phrase. **This one cannot be done in `shared/ui` alone** — every call site passes the noun. | `shared/ui/**` plus `widgets`, `features`, `_pages` |
| C6 | `features/start-run/ui/start-run-control.tsx:43` | *"Start run"*. **This needs `tests/**` too, and that is the trap my brief briefed.** `tests/e2e/pc01/journey/manifest.json` names the button's visible text as the only handle it has, and `test_pc01_journey_conformance.py::test_every_control_the_write_half_presses_still_exists_in_the_application` asserts that text appears somewhere in `web/src`. Translating it turns `make gate` red with the frontend battery green, and neither `W31-STYLE` nor I can edit the manifest. | needs a grant over `tests/e2e/pc01/journey/` |
| C7 | `_app/app-frame.tsx:30` | the footer *"Local prototype. One reviewer, no authentication, no tenancy."* — **`R-18` names this by name as a defect a manual test must not meet**, and it is on every page. `_app/**` is in nobody's `allowed_paths` this wave. | ungranted |
| C8 | `app/not-found.tsx:39`, `app/layout.tsx:14` | a 40-word English paragraph on the 404 screen; `<title>` and `<html lang="en">`. `R-18`'s own check names `lang=` at `layout.tsx:20`. | ungranted |

**I did not edit any of them and did not work around any of them.** `git diff --stat
ae2adf5..HEAD` in §7 is the proof.

---

## 6. Every premise of this brief I measured, and what was false

| Premise | Verdict |
|---|---|
| *"the catalog has 22 codes and **zero of them contain a single Cyrillic character**"* (integrator) | **True, and true of the whole document, not just the codes.** `grep -c '[а-яА-ЯёЁ]' contracts/domain/v1/error-codes.json` → `0`, exit 1. `json.load(...)['codes']` → 22 keys. |
| *`W31-UI` classified `credentialed-forward.ts` as server-side and deliberately left it* | **False for the module, and it is the most consequential false premise here.** The module runs server-side; **its output does not stay there.** `synthesizedEnvelope()` puts its sentences into an `ErrorEnvelope` **body** that the browser decodes — *"The web server could not reach the API…"* as `503 dependency_unavailable`, and the five path-validation sentences as `404 not_found`'s message. `run-failure.ts`'s `dependency_unavailable` and `not_found` arms rendered `error.envelope.message` verbatim. Six reviewer-facing English sentences, closed this wave. **The general shape: "which process executes this" is not the same question as "who reads its output".** |
| *`W31-UI` classified `env.ts` as server-side* | **Verdict right, reason wrong.** `getApiBaseUrl()` is called from `transport.ts:216`, which runs **in the browser**, so "server-side" is false. The strings are nonetheless unreachable, for a different reason: `MissingConfigurationError extends Error`, not `ApiFailure`, and every classifier's `unknown` arm renders a Russian fallback for anything that is not an `ApiFailure`. A correct verdict from a wrong reason survives only until the reason changes. |
| *`W31-UI` classified `server-env.ts` as server-side* | **True.** Only the `bff` route calls it, and the route catches the throw and answers `unconfigured()` without forwarding the message, with a comment saying why. |
| *`W31-UI` classified the bff route as server-side* | **True of the one string it is usually about, false of the file.** Its `401` message is masked, because all five consumers replace `authentication_required`'s message with the already-Russian `AUTHENTICATION_REQUIRED_DETAIL`. But the file is the entry point for C1's sibling problem and for the `credentialed-forward.ts` row above. |
| *`W31-UI` reported 106 sentences in 16 `.ts` model files and says it translated them* | **Translated, and incomplete — the completeness is what was false.** `W31-UI`'s own earlier commit had already claimed completeness falsely once (`b0b8148`). Measured here: **18 origin groups** of reviewer-facing English remained inside `web/src`, including four mixed-language files where a Russian title carries an English tail in the same expression, and `version-panel.tsx` rendering `<Field label="Media type">` four lines below `<Field label="Версия">`. Not a criticism of the pass — a file-by-file reading cannot see this, which is why §3.4 exists. |
| *"the OpenAPI document's `description`/`summary` fields, **only** where something renders them to a user"* | **Nothing does.** The generator writes them into `generated/**` as JSDoc at build time; no runtime path reads them. The census bullet closes empty. |
| *"`error.envelope.message` is the known one; there will be others"* | **True, and the others are larger than it.** 122 `message=` sites in `src/auditmanager/**`; ~29 reachable through a browser body, ~70 unreachable because they become **stage** failures and `StageState` publishes `stage_id, stage_version, status, error_code, started_at, finished_at` — and no message field. |
| *"`make gate` catches something `npm test` structurally cannot… if it happens, stop and report"* | **It did not happen, and that is a measurement rather than an absence.** `tests/e2e/test_pc01_journey_conformance.py` → **47 passed**, `EXIT=0`, run on its own after the gate. None of the manifest's pinned sentences (`не является PDF`, `Ничего не отправлено`, `25 MiB`, `выходит за допустимые ограничения`) or handles is in a string I moved. **C6 is where it would have fired**, and C6 is in `features/**`, which I cannot edit. |
| *"`web/src/entities/**` and `web/src/shared/api/**` — yours alone this wave"* | **True, and `shared/lib/` is the gap the grant leaves.** `listing-failure.ts` is the third-largest block of reviewer-facing English in `web/` and belongs to neither me nor `W31-STYLE`. §4.3. |
| *`terminal-reason.ts` is `W29-SAY`'s work and is exactly this mechanism* | **True, and it is not a template to copy.** Its sentences are in the register of a run that has stopped — *"прогон остановился"* — and this map is read by four classifiers, only one of which is about a run. The contract test asserts the two tables share no sentence, and M3 is that assertion watched to fail. |

### The contract vocabulary, as asked: what the reviewer currently sees

Not translated, per the brief; recorded because `PA-01` criterion 4 is driven by reading
these badges and `DEBT_REGISTER.md` §2 carries it as an open owner question.

- **Finding-category headings** — `widgets/finding-list/ui/finding-list.tsx:43–52`.
  `categoryHeading()` is a `switch` that returns **the contract value unchanged**:
  `internal_contradiction`, `explicit_placeholder`. These sit as headings **above** the
  findings list, which makes them the most visible instance: a reviewer reads an identifier
  where every neighbouring line is a sentence.
- **Verdict badges** — `entities/expert-decision/ui/verdict-badge.tsx:44` renders
  `{verdict}` raw: `pending`, `accepted`, `rejected`, `needs_manual_review`. **This file is
  in my `allowed_paths` and I left it alone deliberately.**
- **Run-state and stage-status badges** — `shared/ui/run-state-badge.tsx`,
  `stage-status-badge.tsx`, same shape.
- Every one already carries its machine value in a `data-` attribute (`data-verdict`,
  `data-terminal-reason`, `data-run-outcome`, `data-provider-mode`), so **it is a one-pass
  change either way** and no test or journey handle depends on the visible text.

---

## 7. Verification, and the proof the forbidden hotspots are untouched

**`make gate`**, from a committed-clean tree (`git status --porcelain` empty before the
run), lane `gate-w31c` on ports `56100 / 59700 / 59701`, log
`/root/w31-logs/rus-gate.log`:

```
2013 passed, 5 skipped, 1 warning, 169 subtests passed in 275.13s
35 passed in 29.43s                          (foundation)
Test Files  55 passed (55) / Tests  785 passed (785)   (frontend)
GATE OK: battery, foundation, frontend and whitespace all pass
EXIT=0
```

Battery **2013 / 5 / 169** and foundation **35** are the briefed baseline **unchanged**.
Frontend moves **772 in 53 files → 785 in 55 files**: `+13` tests in `+2` files, which are
`catalog-message.contract.test.ts` (9) and `presentation-language.guard.test.ts` (4).

**The journey-conformance trap, measured rather than assumed.**
`.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py -q` → **47 passed, `EXIT=0`**
(`/root/w31-logs/rus-journey-conformance.log`). Nothing I moved is a manifest handle or a
pinned sentence. C5/C6 in §5 are where it would have fired, and both are outside my grant.

**Mutation logs**: `/root/w31-logs/rus-mutation-M{1,2,3}.log`, all `EXIT=1`, all reverted,
tree clean after each.

### `git diff --stat ae2adf5..HEAD`

```
 docs/program/W31-RUS.md                                    |
 web/src/entities/audit-run/model/run-failure.ts            |
 web/src/entities/audit-run/ui/run-row.tsx                  |
 web/src/entities/document-version/model/upload-envelope.ts |
 web/src/entities/document-version/model/upload-failure.ts  |
 web/src/entities/document-version/ui/version-panel.tsx     |
 web/src/entities/document-version/ui/version-row.tsx       |
 web/src/entities/project/model/create-failure.ts           |
 web/src/entities/project/model/list-failure.ts             |
 web/src/entities/project/model/project.ts                  |
 web/src/entities/project/ui/project-row.tsx                |
 web/src/shared/api/catalog-message.ts                      |
 web/src/shared/api/credentialed-forward.ts                 |
 web/src/shared/api/errors.ts                               |
 web/src/shared/api/index.ts                                |
 web/src/shared/api/transport.ts                            |
 web/tests/contract/catalog-message.contract.test.ts        |
 web/tests/guards/presentation-language.guard.test.ts       |
 web/tests/unit/api/transport-rules.test.ts                 |
 web/tests/unit/projects/create-and-list-failure.test.ts    |
 web/tests/unit/projects/upload-envelope.test.ts            |
 web/tests/unit/projects/upload-failure.test.ts             |
 web/tests/unit/run/run-failure.test.ts                     |
 web/tests/unit/screens/widgets.test.ts                     |
 24 files changed, 808 insertions(+), 103 deletions(-)
```

Every path is `web/src/entities/**`, `web/src/shared/api/**`, `web/tests/**` or
`docs/program/W31-RUS.md` — the four `allowed_paths` and nothing else. **Zero** entries under
`web/src/app/globals.css`, `web/src/**/*.module.css`, `web/src/widgets/**`,
`web/src/_pages/**`, `web/src/features/**`, `web/src/shared/ui/**`, `contracts/**`,
`web/FRONTEND_LOCK.json`, `src/**`, `db/**`, `infra/**`, `tests/**`,
`docs/program/DEBT_REGISTER.md`, `CURRENT_STATE.md`, `ALPHA_ROADMAP.md`,
`OWNER_RULINGS_2026-09-17.md`, root `package.json`/lockfiles or the `Makefile`.

**Contracts touched: none.** No contract, no lock, no migration, no dependency.

## 8. Risks and known limitations

1. **§3.1's trade-off is real and is the one thing to re-read before extending this.** The
   substitution replaces a *custom* backend sentence as readily as a catalog summary,
   because the envelope does not distinguish them. It is sound today because the custom
   sentences are English too. The moment §4.1 lands, it stops being sound — see §4.1's last
   paragraph.
2. **`catalog-message.ts` is a new member of `W30-LISTS`'s class**: a second description of
   something, maintained by hand. Its defence is the contract-derived guard in §3.3 and the
   `Record` type; both were watched to fail (M1). It is not defended against a *wrong
   restatement* — only against a *missing* one. Nothing can check a sentence's fidelity to a
   summary except a reader.
3. **The prose guard's word list is a heuristic.** A short English label with fewer than two
   function words — a bare `Ordinal`, say — passes it. That class is caught by the census,
   not by the guard, and the guard says so where `ENGLISH_FUNCTION_WORDS` is declared.
4. **The guard covers two trees only.** The remaining English in `web/` is in §1.2 and §5,
   unguarded by construction: a guard over a path whose owner cannot satisfy it gets deleted.
   When `W31-STYLE` lands, extending `OWNED` is a two-line change and is the cheapest moment
   to do it.
5. `transport.ts` still puts an `operationId` in a user-facing sentence — §4.4.

## 9. Rollback

Two commits, additive, and they drop in this order:

- **`31cb5d8`** — `catalog-message.ts`, the translations, both guards, six repaired tests.
  Dropping it restores the English and reverts the battery to 772 in 53 files.
- **`0ecde20`** — the census. Documentation only; there is no reason to drop it, and it is
  the deliverable the brief says stands even if nothing else does.

If only the guard proves noisy, `web/tests/guards/presentation-language.guard.test.ts` can
be deleted on its own without touching anything else; `catalog-message.contract.test.ts`
cannot, because `catalog-message.ts` is the only thing keeping the screens Russian.

## 10. For the integrator

1. **Merge `agent/w31-rus` after `W31-STYLE`, or resolve `web/src/shared/api/index.ts`.**
   My only edit outside `entities/`, `shared/api/` and `tests/` is `index.ts`, which is
   mine.
2. **C1 is a one-line follow-up and the module it needs is already exported.**
   `_pages/review/model/present-failure.ts:69` → `catalogMessage(error.errorCode)` from
   `@/shared/api`, which that file already imports from. Hand it to whoever holds `_pages`
   next; it is the last `envelope.message` render in `web/`.
3. **C6 needs a grant that spans `features/**` and `tests/e2e/pc01/journey/`**, because the
   Start-run button's visible text is a journey handle. Dispatching it into `features/**`
   alone produces a red gate and a session that cannot fix it.
4. **§4.1 and §4.2 are two different decisions and §4.1 should go first.** Six `src/` files
   with no reseal, against three artifacts with a mandatory one.
5. **§4.3 (`shared/lib/listing-failure.ts`, nine sentences) belongs to the next `web/`
   wave and to nobody this one.** It is the largest remaining block and the grant gap that
   left it is worth closing explicitly.
