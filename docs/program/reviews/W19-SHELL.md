# W19-SHELL — the screens half of `D-16`: routes a fresh tab can render

**Session** `W19-SHELL`. **Branch** `agent/w19-shell`, worktree `/root/w19shell`.
**HEAD on arrival** `653152f` — *docs: record R-7 through R-10, ruled by direct poll*,
the tip of `origin/dev` at provisioning.
**Gate lane** `gate-w19a` — PostgreSQL 55820, S3 59420/59421, database `audit_w19a`,
bucket `auditmanager-gate-w19a`. **Logs** `/root/w19shell-logs/`.
**`df -h /` on arrival:** 11 GB free of 119 G (91 % used).

*This document is written as the work lands. Sections below are filled in order.*

## Summary

| | before | after |
|---|---|---|
| addressable screens | 4 | **6** — a document and a version each have a URL |
| API calls a project page makes on a fresh load | **0** | **1** (`listDocuments`) |
| screens calling `listDocuments` / `listVersions` / `listRuns` | **0** | 1 each |
| "No version published in this session" | on screen | **gone**, and its absence is asserted |
| copies of the intent-key rule (`D-22`) | 4 | **1** |
| frontend suite | 595 (44 files) | **633 (46 files)** |
| gate | — | **exit 0**, battery and foundation unchanged |

* **Six addresses, loaded cold in six separate browser processes, each one asking the
  server for what it shows** (§4). The figure `D-16` opened on — *"bff calls made by that
  page load: (none — zero)"* — is now 1, 1, 1, 2, 1 and 5.
* **Eleven mutations, eleven killed** (§5), including re-inserting the defect itself.
* **`D-22` closed on the way past** (§7): the rule is one pure function over an opaque
  signature, and `W16-WEB`'s `U-06`/`U-07`/`U-08` are reddenable for the first time.
* **A document route earns its place as an *address*, not as a *step*** (§6), because
  `document_uid` is a value this product prints — a CSV column, a field of every
  `DocumentVersion`, the subject of a `404` — and an identifier a product prints and cannot
  open is `D-16` in miniature.
* **One premise of the dispatch is wrong in the way that matters** (§8.1): `web/src/app/**`
  could not have held this defect, and repairing it there alone is not possible.
* **Elapsed 45 minutes**, measured (§11). **Disk is down to 5.2 GB** and the next session
  should reclaim rather than check (§10).

## 1. The defect, restated from the measurement

`W15-RUN` §6 `W15RUN-3`, measured in a real browser against the deployed stack: a project
page on a fresh load makes **zero** API calls and says *"No version published in this
session"*. `W18-SEAL` closed the contract half under `R-5`; `DEBT_REGISTER.md` **D-16**
records the remaining half as *"`web/src/app/**` is untouched … no screen renders them"*.


## 2. HEAD, lane, and the premises I checked

**HEAD on arrival** `653152f`. Worktree `/root/w19shell`, branch `agent/w19-shell` from
`origin/dev`. `make bootstrap` exit 0, `npm --prefix web ci` exit 0 (184 packages, 6 s).
`df -h /` on arrival **11 GB free**; at the time of writing **5.2 GB**, and §9 says what
consumed it and what the next session should do about it.

Five premises of the dispatch were checked against the tree. **Four hold. One does not,
and one more is incomplete in a way that changed what I built.** §8 has all of them.

## 3. The route map, and why this one

| URL | Screen | Reads on mount | New |
|---|---|---|---|
| `/` | redirect to `/projects` | — | |
| `/projects` | project list, create | `listProjects` | |
| `/projects/{project_uid}` | one project: its documents, then the upload | **`listDocuments`** | rewired |
| `/projects/{project_uid}/documents/{document_uid}` | one document, its versions | **`listVersions`** | **new** |
| `/projects/{project_uid}/versions/{version_uid}` | one version: manifest, runs, Start run | **`getDocumentVersion` + `listRuns`** | **new** |
| `/projects/{project_uid}/runs/{run_id}` | run progress | `getRunStatus` | |
| `/projects/{project_uid}/runs/{run_id}/review` | findings, evidence, decisions, export | five reads | |

Four decisions worth stating, each with the thing in the tree that decided it.

**Every address is built once**, by `routes` in `web/src/shared/lib/routes.ts`, and never
by a template literal at a call site. The property this session has to prove is that a
*string* pasted into a fresh tab renders; an address that exists in four places can be
wrong in three of them. `tests/unit/screens/routes.test.ts` now derives each URL back out
of the `src/app/**` directory layout and compares, so a route file moved without its
builder is red.

**A document and a version are nested under the project**, not addressed at the root,
because that is the convention this application already had: a run is
`/projects/{project_uid}/runs/{run_id}` even though `run_id` is globally addressable. The
cost of the convention is that a pasted URL can carry a project a version does not belong
to. That is handled rather than ignored: the version screen reads the version's own
`project_uid` out of the fetched body and links **there**, so a mismatched segment sends
the user to the right project. It has its own test and its own killed mutation (M5).

**The Start-run control moved off the project screen and onto the version.** It used to
appear only after an upload in the same browser session, beside a version held in React
state — which is why a returning user had no way to run anything. It now hangs off the
version's address, where a user who has one can reach it; the empty run list carries it as
its action, and a version that already has runs offers "Start another run".

**`document_count` was left exactly alone.** `W19-API` is populating it under ruling
`R-10` and the dash is still on screen in §4. Nothing here computes it from
`listDocuments`; the screens assume the number arrives.

## 4. Each route, cold, in a real browser


**How.** A `next build` of this worktree served by `next start` on `127.0.0.1:3919`
(`NEXT_PUBLIC_API_BASE_URL=/bff/v1`), forwarding through the real `/bff/v1` route handler
to this repository's own `infra/deploy/serve.py` on `127.0.0.1:58820` against this lane's
PostgreSQL (55820) and MinIO (59420), `AUDITMANAGER_PROVIDER_MODE=recorded`. **No image
was rebuilt and neither alpha stack was touched** — 31480 and 31490 were left running.

The data was seeded through the public origin, as a user: a project, an upload of
`fixtures/synthetic/ar/ar_baseline.pdf` (201, 8 pages, 58 978 bytes,
`sha256 6d53674f…`), and a run (202, `published`, `recorded`, 4 stages, 3 findings).

**The browser is `chromium-1234` already on this host**, driven by the `playwright-core`
installed outside the repository by `W15-RUN` at `/root/w15run-browser`. No repository
dependency was added; `web/package.json` and `web/package-lock.json` are untouched.

**Each row below is a separate browser process.** Not a new tab in a warm browser and not
a client-side navigation — `chromium.launch()` per URL, so there is no cache, no storage
and no prior client state of any kind. That is the acceptance test this row is about.
Full journal: `/root/w19shell-logs/browser/cold-loads.json`.


### `/projects` — the project list

```
GET http://127.0.0.1:3919/projects  ->  200
  200 /bff/v1/projects?limit=50
```

What the browser rendered:

```
Projects

One local reviewer. No authentication, no roles, no tenancy.

New project
Create
All projects

W19-SHELL cold load

prj_01M2T7DTGFN0G83S7PVC2EDM04

Created 2026-09-18 12:21:27 UTC · documents —
```

### `/projects/{project_uid}` — **the screen `D-16` was written about**

```
GET http://127.0.0.1:3919/projects/prj_01M2T7DTGFN0G83S7PVC2EDM04  ->  200
  200 /bff/v1/projects/prj_01M2T7DTGFN0G83S7PVC2EDM04/documents?limit=50
```

What the browser rendered:

```
Project

prj_01M2T7DTGFN0G83S7PVC2EDM04

All projects
Documents

AR baseline

ver_01M2T7E4KZV4H1ZKR4PW90XY02

Version 1 · 8 pages · 57.6 KiB · published 2026-09-18 12:21:37 UTC

All versions of this document

Upload

What this accepts

One PDF per upload. No archive, no companion file and no second document.
At most 25 MiB.
At most 30 pages.
Not password-protected and not encrypted.
Every page carries extractable embedded text. A scanned or image-only PDF is refused; text is never recovered by optical recognition instead.

A file outside this envelope is refused with the reason on screen. Text is never recovered by optical recognition instead, and a partially readable document is never accepted quietly. The limits are 25 MiB and 30 pages.

A published version is immutable: nothing here edits or replaces one. A second upload publishes a second document, and both stay addressable.

PDF
Display title (optional; never an identity)
Upload
```

### `/projects/{project_uid}/documents/{document_uid}`

```
GET http://127.0.0.1:3919/projects/prj_01M2T7DTGFN0G83S7PVC2EDM04/documents/doc_01M2T7E4KY03MVNBJHKBS1A9Y6  ->  200
  200 /bff/v1/documents/doc_01M2T7E4KY03MVNBJHKBS1A9Y6/versions?limit=50
```

What the browser rendered:

```
Document

doc_01M2T7E4KY03MVNBJHKBS1A9Y6

Back to project All projects
Published versions

AR baseline

ver_01M2T7E4KZV4H1ZKR4PW90XY02

Version 1 · 8 pages · 57.6 KiB · published 2026-09-18 12:21:37 UTC

One version per upload: this surface gives `uploadDocument` no `document_uid`, so every upload starts a new document at ordinal 1. The service underneath already publishes a second version onto an existing document; only the transport withholds it.
```

### `/projects/{project_uid}/versions/{version_uid}`

```
GET http://127.0.0.1:3919/projects/prj_01M2T7DTGFN0G83S7PVC2EDM04/versions/ver_01M2T7E4KZV4H1ZKR4PW90XY02  ->  200
  200 /bff/v1/versions/ver_01M2T7E4KZV4H1ZKR4PW90XY02
  200 /bff/v1/versions/ver_01M2T7E4KZV4H1ZKR4PW90XY02/runs?limit=50
```

What the browser rendered:

```
Version

ver_01M2T7E4KZV4H1ZKR4PW90XY02

Back to project All projects
This version

AR baseline

Version ver_01M2T7E4KZV4H1ZKR4PW90XY02

Document doc_01M2T7E4KY03MVNBJHKBS1A9Y6

Ordinal 1 (display order only, never an identity)

Media type application/pdf

Pages 8

Size 57.6 KiB (58978 bytes)

SHA-256 6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f

Published 2026-09-18 12:21:37 UTC

Input manifest

source.document · application/pdf · 57.6 KiB · 6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f

This version and its manifest are immutable. There is no endpoint that changes either.

All versions of this document

Runs

run_01M2T7EB1930BTCMY2K649FTWE
published
recorded

Created 2026-09-18 12:21:44 UTC · terminal 2026-09-18 12:21:44 UTC

Findings 3 · stages 4

Start another run
Start run

The run uses the provider mode this deployment is configured for. It is shown on the run, and it is never chosen here.
```

### `/projects/{project_uid}/runs/{run_id}`

```
GET http://127.0.0.1:3919/projects/prj_01M2T7DTGFN0G83S7PVC2EDM04/runs/run_01M2T7EB1930BTCMY2K649FTWE  ->  200
  200 /bff/v1/runs/run_01M2T7EB1930BTCMY2K649FTWE
```

What the browser rendered:

```
Run

run_01M2T7EB1930BTCMY2K649FTWE

Back to project All projects

published
recorded
provider mode: recorded

Replayed from recordings. This run is not evidence of a live provider call.

Not polling. This reading is final.

Run
run_01M2T7EB1930BTCMY2K649FTWE
Version
ver_01M2T7E4KZV4H1ZKR4PW90XY02
Created
2026-09-18 12:21:44 UTC
Terminal at
2026-09-18 12:21:44 UTC

The version this run read — ver_01M2T7E4KZV4H1ZKR4PW90XY02. A run never changes the version it read, and that version's other runs are listed there.

The run reached its success terminal, published.

Published findings: 3

Stages
Stage	Status	Started	Finished
source_preparation
succeeded
	2026-09-18 12:21:44 UTC	2026-09-18 12:21:44 UTC
page_geometry_extraction
succeeded
	2026-09-18 12:21:44 UTC	2026-09-18 12:21:44 UTC
document_context_build
succeeded
	2026-09-18 12:21:44 UTC	2026-09-18 12:21:44 UTC
text_analysis
succeeded
	2026-09-18 12:21:44 UTC	2026-09-18 12:21:44 UTC
Review

Review findings — this run's provider mode is recorded.
```

### `/projects/{project_uid}/runs/{run_id}/review`

```
GET http://127.0.0.1:3919/projects/prj_01M2T7DTGFN0G83S7PVC2EDM04/runs/run_01M2T7EB1930BTCMY2K649FTWE/review  ->  200
  200 /bff/v1/runs/run_01M2T7EB1930BTCMY2K649FTWE
  200 /bff/v1/runs/run_01M2T7EB1930BTCMY2K649FTWE/findings
  200 /bff/v1/findings/fnd_01M2T7EBM4AN3HNR3KV8TK7R82/decisions
  200 /bff/v1/findings/fnd_01M2T7EBM4AN3HNR3KV8TK7R82
  200 /bff/v1/versions/ver_01M2T7E4KZV4H1ZKR4PW90XY02/content
```

What the browser rendered:

```
Review

published
recorded
 prj_01M2T7DTGFN0G83S7PVC2EDM04 run_01M2T7EB1930BTCMY2K649FTWE

Back to the run Back to project All projects
internal_contradiction 2
Степень огнестойкости одного и того же здания указана по-разному: II в разделе общих данных и III в разделе противопожарных мероприятий.
pending
pages 2, 6
Количество эвакуационных выходов из надземной части здания указано как два в объёмно-планировочных решениях и как три в разделе эвакуационных путей и выходов.
pending
pages 3, 7
explicit_placeholder 1
Тип заполнения оконных проёмов не определён: вместо проектного решения оставлено буквальное указание «уточнить».
pending
page 8
Степень огнестойкости одного и того же здания указана по-разному: II в разделе общих данных и III в разделе противопожарных мероприятий.

Согласовать степень огнестойкости здания между разделом общих данных и разделом противопожарных мероприятий, оставив одно значение.

page 2page 6recorded
Quotations on page 2
Степень огнестойкости здания — II.

page 2, chars 712–746

Page-level navigation only: no highlight overlay and no bounding box. The quotation above is the exact string the grounding gate verified at its anchor.

Decision
current verdict
pending
AcceptReject
Append a commentAppend comment

A comment is a new event. It never replaces the verdict above and never edits an earlier event.

No decisions yet

Nobody has judged this finding. Accepting or rejecting appends the first event.

Export
published
recorded
Download run_01M2T7EB1930BT
…
```

### A project that does not exist

```
GET http://127.0.0.1:3919/projects/prj_01M2T7DTGFN0G83S7PVC2EDM99  ->  200
  404 /bff/v1/projects/prj_01M2T7DTGFN0G83S7PVC2EDM99/documents?limit=50
```

What the browser rendered:

```
Project

prj_01M2T7DTGFN0G83S7PVC2EDM99

All projects
Documents

There is no such project.

The server does not have this project, so there is nothing here to list. That is a different answer from an empty list, and it is not retried.

Correlation id cid-2b3631dacd18567ebdcc428363e61b68

Upload

What this accepts

One PDF per upload. No archive, no companion file and no second document.
At most 25 MiB.
At most 30 pages.
Not password-protected and not encrypted.
Every page carries extractable embedded text. A scanned or image-only PDF is refused; text is never recovered by optical recognition instead.

A file outside this envelope is refused with the reason on screen. Text is never recovered by optical recognition instead, and a partially readable document is never accepted quietly. The limits are 25 MiB and 30 pages.

A published version is immutable: nothing here edits or replaces one. A second upload publishes a second document, and both stay addressable.

PDF
Display title (optional; never an identity)
Upload
```

### A malformed version address

```
GET http://127.0.0.1:3919/projects/prj_01M2T7DTGFN0G83S7PVC2EDM04/versions/ver_lowercase  ->  200
  (no API call, and that is the answer: see below)
```

What the browser rendered:

```
Version
All projects

That is not a version address.

A project and a version are each addressed by an opaque identifier. Nothing was requested.
```
**What every row of §4 says together.** Six addresses, six separate browser processes,
**every one of them asking the server for what it shows**. The number `D-16` opened on —
*"bff calls made by that page load: (none — zero)"* — is now 1, 1, 1, 2, 1 and 5. The
sentence it opened on — *"No version published in this session"* — is not in this
application any more, and a test asserts its absence.

The two refusals at the end are the other half of the same claim. An unknown project is a
`404` from the server rendered as *"There is no such project"*, not as an empty page; and a
malformed address costs **zero** requests, which is a claim about the wire and is checked
against the query cache rather than against the sentence.

## 5. Which test reddens for which screen

Every claim above has a test, and every test was **shown able to fail** by breaking the
thing it guards, running it, and reverting. Eleven mutations, all eleven killed. Logs:
`/root/w19shell-logs/mutations/`.

| # | The mutation | In | Result | The test that went red |
|---|---|---|---|---|
| `M1` | document-list always reports the project empty | `document-list.tsx` | KILLED | the project screen asks the server on a cold load (D-16) > renders documents that came from the server, each addressable by its version |
| `M2` | useDocumentList drops the project from its cache key | `use-document-list.ts` | KILLED | the project screen asks the server on a cold load (D-16) > files the pending read under the listDocuments key for THIS project |
| `M3` | a 404 parent is classified as an ordinary server error | `listing-failure.ts` | KILLED | the project screen asks the server on a cold load (D-16) > distinguishes an empty project from a project that does not exist |
| `M4` | the empty run list drops the Start-run control | `run-list.tsx` | KILLED | the version screen asks the server on a cold load (D-16) > offers Start run when the version has no run yet |
| `M5` | the version screen trusts the project segment in the URL | `version-detail-page.tsx` | KILLED | the version screen asks the server on a cold load (D-16) > builds the back link from the fetched body, not from the pasted address |
| `M6` | the version address is built at a segment no route file serves | `routes.ts` | KILLED | every screen address is built once and matches a route file on disk > '/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4…' is served by a file that exists |
| `M7` | the version route file crosses its two parameters | `page.tsx` | KILLED | each route delegates to its screen and to no other > /projects/{project_uid}/versions/{version_uid} passes both, and does not cross them |
| `M8` | the intent rule mints a fresh key on every retry | `intent-key.ts` | KILLED | the rule: one key per intent, reused on every retry > mints NOTHING on a retry of the same intent, however many times |
| `M9` | the intent rule never mints again, even when the payload changed | `intent-key.ts` | KILLED | the rule: one key per intent, reused on every retry > mints again the moment the intent changes |
| `M10` | the upload panel keeps the published version in session state again | `upload-panel.tsx` | KILLED | the upload panel states the envelope before the file picker (U-09) > offers no run control at all: the run is started from the version address (D-16) |
| `M11` | the document screen stops saying why it lists one version | `version-list.tsx` | KILLED | the document screen asks the server on a cold load (D-16) > says why one version is what this transport can produce, rather than looking empty |
`M1`–`M5` and `M11` are the screens; `M6`–`M7` are the addresses; `M8`–`M9` are `D-22`;
`M10` is the defect itself, re-inserted — putting *"No version published in this session"*
back on the upload panel is red.

**What the render harness can and cannot reach, stated rather than discovered later.**
`tests/unit/screens/harness.ts` renders one pass with no DOM: it *can* render a component
whose state comes from a seeded query cache, and it *cannot* fire a handler, run a
`useEffect`, or render the same instance twice. So the half of "fetches on mount" it
proves is the half decided during render — *does this screen file a pending query under
the key its fetch will answer, or does it report emptiness without asking?* — and the
tests assert that by reading the key back out of the cache, so a hook wired to the wrong
key is red rather than differently green (`M2`). The other half, that the query reaches
the network and the page arrives over a socket, is not claimed by any test here. It is
§4, in a browser, by URL.

## 6. Does a document→version route earn its place?

**`W18-SEAL` §2's measurement is right, and I re-checked it rather than inheriting it:**
`uploadDocument` declares no `document_uid` in `contracts/api/v1/openapi.json`, so every
upload through this transport starts a new document at ordinal 1, and `listVersions`
returns exactly one row. `IngestService.upload_single_pdf` does take a `document_uid`; only
the transport withholds it.

**The answer is: yes as an address, no as a step — and that distinction is what I built.**

*Not as a step.* The project screen links **straight to the version**, past the document,
because `listDocuments` already returns the version each document points at. Making a user
click through a list of one to reach a thing the previous screen could have linked to is a
click that buys nothing today.

*Yes as an address*, for one reason that is not a prediction about the future:
**`document_uid` is a value this product already prints at a user.** It is one of the CSV
export's seventeen frozen columns. It is a field of every `DocumentVersion` body the API
returns. It is the `aggregate_type` subject of a `404` envelope. **An identifier a product
prints and cannot open is `D-16` in miniature** — it is the same defect, one aggregate
smaller, and closing the row while leaving it would be closing it on the version's evidence
only.

The forward-looking argument is real but secondary: when the transport gains
`document_uid`, this screen needs no change, because it was written for a list and renders
its count rather than assuming one. What it must not do is *look* broken in the meantime,
so it says on screen why it shows one row — and that sentence has a test and a killed
mutation (`M11`), because an explanation nobody guards is an explanation that outlives its
reason.

## 7. `D-22`, closed on the way past

`W16-WEB` §5.1 left `U-06`, `U-07` and `U-08` alive **by construction**: the intent-key
rule lived inside a `useRef` that is always fresh on a single render pass, three times, in
three hand-copies that each carried a comment saying it belonged in `shared/lib`.

I touched `start-run`, so I made the repair the row asks for.

* `web/src/shared/lib/intent-key.ts` — the whole rule, as a pure function over an **opaque
  signature**, with `mint` injected.
* `web/src/shared/lib/use-intent-key.ts` — the hook, holding no copy of the rule.
* The three copies under `web/src/features/*/model/use-intent-key.ts` are **deleted**, and
  the three features import `useIntentKey` from `@/shared/lib`.
* `entities/expert-decision` keeps `intentSignature` — *what makes two decision intents the
  same* is genuinely about decisions — and delegates the resolution. Its nine existing
  tests pass unchanged.

`tests/unit/lib/intent-key.test.ts` is what could not be written before: with `mint`
injected, *"a key was minted"* is a counted fact rather than an inference from markup, and
both directions of the rule redden (`M8`, `M9`). Both halves matter — minting on a retry is
a second command, and *never* minting sends a changed payload under an old key, which is
`idempotency_key_reuse` and terminal.

**`D-22` is closeable on this evidence.** Check:
`ls web/src/features/*/model/use-intent-key.ts` finds nothing;
`grep -rn "export function useIntentKey" web/src` returns one line, in `shared/lib`.

## 8. What I found false, incomplete or stale in the dispatch

**One premise is wrong in the way that matters, one is a path, and the rest hold.**

### 8.1 Wrong — *"You own `web/src/app/**`, the routing"* is not where the defect was

`web/src/app/**` at `653152f` is nine files: a layout, a stylesheet, a README, the
`/bff/v1` catch-all, and **five delegation-only route files that decide nothing**. The
project route is six lines and reads:

```
const { project_uid } = await params;
return <ProjectDetailPage projectUid={project_uid} />;
```

**The screen that made zero API calls is not in that directory.** It is
`web/src/_pages/project-detail/**` and `web/src/widgets/upload-panel/**`, and the version
it could not reach was held in a `useState` in the second of those. Repairing `D-16`
inside `web/src/app/**` alone is not possible: the two new route files there are nine
lines each, and every line that closes the row is in `_pages`, `widgets`, `entities` and
`shared`.

I took "and the routing" to carry the screens those routes serve, because nothing else
would have delivered the row. **Everything I edited outside `web/src/app/**` is listed in
§9 with its reason.** If the intent was narrower, the boundary and not the brief is what
needs to move — because the narrow reading makes the row unclosable.

*(This is the same shape as the finding the dispatch warned about: "one where the file I
pointed at could not have held the defect".)*

### 8.2 Stale — `DEBT_REGISTER.md` is at `docs/program/DEBT_REGISTER.md`

A navigational nit, not a substantive one: the brief and the register's own prose both
spell it as a bare filename, and there is no such file at the repository root.

### 8.3 Checked and holding

| Premise | Verdict |
|---|---|
| base `653152f` or later | **holds** — provisioned at exactly `653152f` |
| gate at base: battery **1778 / 5 skipped / 168 subtests**, foundation **35** | **holds** — §9 reproduces all three unchanged |
| frontend **595 (44 files)** at base | **holds** — this session adds 2 files and 38 tests; 595 + 38 = 633, 44 + 2 = 46 |
| the three operations are in the contract and the generated client, and **no screen calls them** | **holds** — at `653152f`, `git grep -c listDocuments -- web/src` matches only `generated/client.gen.ts` and `generated/operations.gen.ts`; `web/src/app` has no match |
| `listProjects.document_count` is unpopulated | **holds** — measured in the browser at §4: the project list still reads `documents —`. Nothing here populates it |
| `listRuns` cannot make `running` observable (`D-20`) | **holds** — the seeded `POST /runs` answered `202` already carrying `state: published`. Nothing built here waits for `running`, and the run row asserts it does not render one |
| `D-22`: the rule once as `resolveIntentKey`, three hand-copies in hooks | **holds exactly** — the three were `web/src/features/{create-project,upload-document,start-run}/model/use-intent-key.ts`, byte-identical, each with the comment. §7 |
| `web/FRONTEND_LOCK.json` is a seal | **holds and is untouched** — it seals `generated/**`, the lockfile, the OpenAPI snapshot and the generator script; none of those was edited, and `frontend-lock.guard.test.ts` passes in the gate |
| `df -h /` ~11 GB | **held on arrival**, and does not hold now — §9 |

## 9. Boundaries, and every file I touched outside `web/src/app/**`

### 9.1 Boundaries I stopped at

* **`contracts/**`, `src/**`, `infra/**`, `Makefile` — not touched, and nothing needed
  them.** Every screen here is served by the fifteen operations as sealed. No reseal is
  requested by this session.
* **`web/FRONTEND_LOCK.json` — not touched.** No regeneration was needed.
* **`listProjects.document_count` — deliberately not computed.** A screen *could* derive it
  from one `listDocuments` per project row, and that is exactly the local second source of
  truth `R-10` is avoiding. The dash stays until `W19-API` lands.
* **`docs/program/DEBT_REGISTER.md` — not edited.** `D-16`'s screens half and `D-22` are
  both closeable on this evidence and both are argued above with their check commands, but
  the register is the integrator's and two more streams of this wave land on the same rows.
  Flagging rather than closing:
  * **`D-16`** — check: `grep -rn "listDocuments" web/src/_pages web/src/widgets web/src/entities`
    is now non-empty, and §4 is the browser measurement the row's own text asked for.
  * **`D-22`** — check: `ls web/src/features/*/model/use-intent-key.ts` finds nothing;
    `grep -rn "export function useIntentKey" web/src` returns exactly one line.
* **`W15RUN-5`, `D-15`, `D-20` — untouched.** The run screen still prints
  `Created … / Terminal at …` at the same instant, because `created_at` and `terminal_at`
  are what the API sends. Not a screen defect and not mine.

### 9.2 What I edited, and why each one is not `web/src/app/**`

| Path | Why |
|---|---|
| `web/src/shared/lib/routes.ts` *(new)* | every screen address, built once. The routing, in the only place a test can assert it |
| `web/src/shared/lib/intent-key.ts`, `use-intent-key.ts` *(new)* | `D-22`, which the dispatch asks for by name |
| `web/src/shared/lib/listing-failure.ts` *(new)* | the catalog-code→state mapping for the three listings. It is in `shared/lib` and not in an entity because `document-version` and `audit-run` both need it and an entity may not import another entity |
| `web/src/shared/api/query-keys.ts` | **a judged edit.** The file says the namespaces are fixed "by the toolchain owner". I added three *builder functions* under the existing `projects`, `versions` and `runs` roots and invented no fourth namespace, which keeps both of the file's own rules — every key starts with one of the four roots, and a key is built by calling a function here. Where each listing is filed is argued in the file: `listDocuments` is under `projects` so that `uploadDocument`'s existing invalidation reaches it, and `listRuns` is under `runs` so `startRun`'s does |
| `web/src/entities/{document-version,audit-run}/**` | the three query hooks, two row components, and the `doc_`/`ver_` address shape checks |
| `web/src/widgets/{document-list,version-list,run-list}/**` *(new)* | the three listings, each rendering the mandatory states |
| `web/src/widgets/upload-panel/**` | **the defect itself.** It held the published version in `useState`; that state was the only copy in the product, and a reload lost it |
| `web/src/_pages/{project-detail,document-detail,version-detail}/**` | the screens the two new routes delegate to, and the rewiring of the one that made zero calls |
| `web/src/_pages/{run,review}/**`, `web/src/widgets/run-progress/**` | "a route back from every screen": the review screen had none at all, and run progress now links to the version it read |
| `web/docs/PC01_UI_SEAM.md` §2 | **a frozen table the dispatch did not mention.** It froze four URLs and said *"there is no route for a document version"* — **that sentence is `D-16`**. It is amended, with the reason, in the same commit as the route files, rather than left to contradict the tree |
| `web/tests/unit/**` | §5 |

## 10. The gate

Run after the last **code** commit (`2c1a029`), with nothing else of mine running: the
local API and the `next start` used for §4 were both stopped first, and both alpha stacks
(31480, 31490) were left untouched throughout. The commits after it are this document and
nothing else, so no gated file moved; `check_whitespace` is `git diff --check` over a tree
that is clean at every one of them.

```
$ make gate > /root/w19shell-logs/gate.log 2>&1 ; echo "GATE_EXIT=$?"
GATE_EXIT=0
```

The exit code is taken from `$?` after the redirect, never through a pipe.

| | at base (dispatch) | here |
|---|---|---|
| battery | 1778 passed / 5 skipped / 168 subtests | **1778 passed, 5 skipped, 168 subtests**, 223.84 s |
| foundation | 35 | **35 passed**, 29.04 s |
| frontend | 595 (44 files) | **633 passed (46 files)** |
| exit | — | **0** |

`GATE OK: battery, foundation, frontend and whitespace all pass`. The battery and
foundation figures are **identical** to the base, which is the expected shape of a
frontend-only wave: nothing in `src/`, `db/`, `contracts/` or `infra/` moved.

**Disk, and this is a finding.** `df -h /` was **11 GB free (91 %)** on arrival and is
**5.2 GB (96 %)** now. Two things consumed it and only one is mine: this lane's
containers, volumes and two `next build` outputs, and a parallel session's gate lane
running in `/root/w19api` at the same time. `W15-RUN` warned that "the one after that may
have to reclaim rather than check"; that session is the next one. This host now carries two
alpha stacks and gate lanes from several waves, and MinIO refuses writes near ~1 GB.

## 11. Elapsed — measured

`2026-09-18T12:02:56Z` → `2026-09-18T12:47Z`, **45 minutes** of wall clock, from the two
timestamps in `/root/w19shell-logs/START_UTC` and the gate's completion. Roughly: 9 minutes
reading `W15-RUN`, `W18-SEAL`, `D-16` and the `web/src` tree; 5 on `D-22`; 12 on the routes,
hooks, widgets and screens; 6 on the tests and the eleven mutations; 9 bringing up an API, a
served build and a browser and driving eight cold loads; 4 on the gate, which ran while this
document was being written.

## 12. Reproducing §4

```
make up && make migrate                                     # lane gate-w19a
PYTHONPATH=src .venv/bin/python infra/deploy/serve.py        # with /root/w19shell-logs/api.env
NEXT_PUBLIC_API_BASE_URL=/bff/v1 npm --prefix web run build
AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:58820 \
  AUDITMANAGER_API_TOKEN=... npx next start -p 3919 -H 127.0.0.1
node /root/w19shell-logs/browser/drive.mjs                   # one browser process per URL
```

`drive.mjs` is kept in `/root/w19shell-logs/browser/` rather than in the repository: it
depends on a `playwright-core` installed outside the tree and on a cached Chromium this
host happened to have, and adding either to `web/package.json` would move
`FRONTEND_LOCK.json`. That is a boundary, not an oversight — and it is the same one
`W15-RUN` stopped at.
