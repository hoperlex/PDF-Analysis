# W15-RUN — the first live journey, and what a user actually sees

**Session** `W15-RUN` · **branch** `agent/w15-run` · **worktree** `/root/w15run`
**HEAD on arrival** `315de25` — *merge: the clean-lane breaker, and the two infra lines
W15-AUTH stopped at*, the tip of `origin/dev` at provisioning.
**Gate lane** `gate-w15b` — PostgreSQL 55760, S3 59360/59361, database `audit_w15b`,
bucket `auditmanager-gate-w15b`.
**Logs** `/root/w15run-logs/`. **Screenshots** `/root/w15run-logs/browser/`.

---

## Summary

- **`D-5` is answered.** `POST /runs`, clicked by a real headless Chromium against the
  deployed origin, answers **`202 Accepted`** with `state: published`. The envelope is
  kept this time (§2). The 500 does not reproduce, and §2 says exactly how far that
  goes and where it stops.
- **All seven steps completed**, twice over: once through the application's own generated
  client over a real socket, once through a real browser clicking the real controls (§4).
- **Two live `text_analysis` runs**, `$0.038500` and `$0.038425`, **`$0.076925` total**
  against the `OD-03` USD 1.00 ceiling, both `cost_basis: measured` (§5). The second one
  is the browser's, and §5 says why it was worth the second four cents.
- **Six defects, none repaired**, each with its owning tree (§6). The largest is not a bug
  in anything: **the contract has no operation that lists a project's documents, versions
  or runs**, so a published version is unreachable the moment the browser tab is reloaded.
  Four certifications did not surface it because no certification ever reloaded a page.
- **Three premises of the dispatch are wrong or incomplete** (§8).
- **Elapsed 03:56 → 04:31 +05:00, 2026-09-18. 35 minutes.**

---

## 1. The stack: reused, then rebuilt, then replaced

Three states, and each move was forced by a measurement rather than chosen.

**Reused first.** Wave 14's `auditmanager-w14a` was still up on 31480 with the restored
fixture document, exactly as `W14-PKG` §9 said. It could not be driven as it stood, and the
dispatch's "reuse or rebuild" understates why: those images were built **before** `W15-AUTH`,
so the deployed browser bundle carried `NEXT_PUBLIC_API_BASE_URL=/api/v1`, there was no
`/bff/v1` route handler in the image, and the `web` container had no runtime environment and
therefore no credential. A browser loading that deployment gets `401` on all twelve
operations. **A rebuild was mandatory.**

**Rebuilt in place** — same instance, same volumes, same port, `up -d --build` from this
worktree, so the restored document survived. Five services healthy; the token channel and
`/bff/v1` verified before anything else:

```
GET  /                       -> 307 -> /projects, the PC-01 shell, instance label "alpha"
GET  /api/v1/projects        -> 401 authentication_required   (direct, no credential)
GET  /bff/v1/projects        -> 200 {"items":[{"project_uid":"prj_01M2RP57JJ…","name":"W14-PKG drive"…
web container bundle          -> let e="/bff/v1"
api container                 -> AUDITMANAGER_PROVIDER_MODE=proxy, PROXY_LLM_* present
```

**Replaced, because the reused volume carried a defect.** The journey's second step died on
that stack (§6, `W15RUN-1`). A second instance, `auditmanager-w15b` on **31490**, with its
own database `auditmanager_w15b` and bucket `auditmanager-w15b`, was brought up from the same
compose file with empty volumes. Wave 14's stack was deliberately **left running and
untouched** on 31480 so the defect can be re-measured rather than described.

Both stacks are still up. `docker compose --env-file <env> -f infra/deploy/compose.server.yml
down` stops either; the env files are `/root/w14pkg/infra/deploy/env/alpha.env` and
`/root/w15run-logs/alpha-w15b.env`.

**Disk.** `df -h /` on arrival: **17 G free of 119 G, 86 %**. After two image builds and two
stacks: **10 G free, 92 %**. Never near MinIO's ~1 GB refusal threshold, so nothing below is
that failure wearing an application's clothes. It is worth saying that the margin halved in
one wave.

## 2. `D-5`, answered, with the envelope

> `D-5` — *"`POST /api/v1/runs` **500 — twice — and the session ends there**… the harness
> logged status lines only, so the envelope behind the 500 was not kept."*

**A real browser, clicking the real button, against the deployed origin:**

```
2026-09-17T23:16:04.463Z   click "Start run"
  POST /bff/v1/runs  ->  202
  {"run_id": "run_01M2RTFR8TNHN7A6QK0WXEJ2ZV",
   "project_uid": "prj_01M2RTFKME4MJ8WTP24BM63WG1",
   "version_uid": "ver_01M2RTFNXDQED5W3XVW3FRQ285",
   "state": "published", "provider_mode": "live",
   "stages": [{"stage_id":"document_context_build","status":"succeeded","stage_version":"1.0.0"}, …]}
  +11 793 ms   the browser is on /projects/…/runs/run_01M2RTFR8TNHN7A6QK0WXEJ2ZV showing "published"
```

and independently, through the application's own generated client over the same origin:

```
POST /bff/v1/runs  ->  202  correlation cid-8eb5ef29db5e5eaf29209f959d1f8ec4
state published, 4 stages succeeded, degradation_set [], 10 475 ms
```

Full wire journal: `/root/w15run-logs/journey-wire.json`,
`/root/w15run-logs/browser/13-d5-network.json`.

### What that does and does not settle

**It settles the operational question.** `startRun` over a real socket, through nginx,
through the Next route handler that holds the credential, from a client that holds none,
answers 202 and publishes. The 500 does not reproduce, in either client, on either stack.

**It does not identify the original fault, and I will not pretend it does.** There is exactly
one recorded 500 with `D-5`'s signature — commit `47469a5`, *fix(C1)*, defect **D2**:

> *"`start_run` returned a two-field receipt while the router renders both `startRun` and
> `getRunStatus` with the same `run_status_body`… the run executed first, every row was
> written, and then it answered 500 with no `run_id`."*

That is `D-5`'s shape precisely. **But it is dated 2026-09-14, two days before the browser
session, and it is an ancestor of `241ae92`, the commit that recorded `D-5` on 09-17.** So it
explains the 500 only if that harness was driving an older checkout, and the harness is gone.
`D-5`'s own row says it: *"this row may outlive its own evidence — which is the argument for
reproducing it under a real server rather than preserving a log."* That is what this is.

**Recommended disposition:** close `D-5` as *not reproducible under a real server; superseded
by this measurement*, citing this section and the two envelopes, and noting that the
attribution question is permanently unanswerable because the envelope was discarded. The row
already contains the lesson it was written to carry.

## 3. How it was driven, and what that client is worth

**Two clients, and the second is a real browser.**

**(a) The application's own code, over a socket.** `/root/w15run-drive/` — a directory
outside the worktree holding a symlink to `web/src`, a symlink to `web/node_modules`, copies
of `vitest.config.ts`/`tsconfig.json`/`package.json`, and one driver file. It imports
`web/src/shared/api/index` and calls the **generated client** → the **real `transport.ts`**.
It passes no `RequestOptions` override at all: `NEXT_PUBLIC_API_BASE_URL` is set to
`http://127.0.0.1:31490/bff/v1` (`env.ts` documents an absolute origin as a supported value)
and `globalThis.fetch` is wrapped for journalling, so what is recorded is what the app really
sent. It holds no credential. Nothing in the worktree is edited — `W12-WEB`'s reason, kept.

**(b) A real headless browser.** Chromium was **already on this host**
(`/root/.cache/ms-playwright/chromium-1234`, put there by something else). The only thing
installed is `playwright-core@1.56.0`, **one package, 2 seconds, into
`/root/w15run-browser/`, outside the repository**. `web/package.json` and
`web/package-lock.json` are untouched, and `git status --porcelain` is empty. The cached
browser is a different build number from the one that package expects, so it is launched with
an explicit `executablePath`; it worked without complaint. **That is the whole cost, and no
repository dependency was added.** Had it needed one, that would have been a finding and not
a licence — the reason it did not is that somebody else had already paid for the browser.

**What (b) buys that (a) cannot.** (a) proves the bytes. (b) proves the product: it executes
the client JavaScript, renders the screens, and clicks the controls. Every screen this system
serves is a **loading shell** on the server — `GET /projects` server-renders *"Loading
projects…"*, the run page *"Loading the run…"* — so a client that does not run JavaScript
observes nothing about the product at all. Three of the six defects below are only visible
through (b).

## 4. The seven steps

Through the public origin, `/bff/v1` only. Run `run_01M2RT02YTYZ9HGC8C545KJ153`, project
`prj_01M2RT029F51H3J8F3VBR7MDEM`, version `ver_01M2RT02WWX9C4JWA170SFGH2Q`.

| # | Step | Status | Time | What a user saw |
|---|---|---|---|---|
| — | load the app | **200** | 35 ms | `/` redirects to `/projects`; header *"AuditManager PC-01 · ALPHA"*, *"One local reviewer. No authentication, no roles, no tenancy."* |
| 1 | create a project | **201** | 49 ms (form: 1 request) | the new project appears at the top of *All projects* with its `prj_…` and a UTC creation time. **`documents —`**, a dash, on every row (§6 `W15RUN-3`) |
| 2 | upload `ar_baseline.pdf` | **201** | 567 ms | *"Chosen: ar_baseline.pdf · 57.6 KiB"*, then the whole manifest: version `ver_…`, ordinal 1, 8 pages, 58 978 bytes, sha `6d53674f…`, *"This version and its manifest are immutable."* On the **reused** stack this step was **409** (§6 `W15RUN-1`) |
| 3 | **start a run — `D-5`** | **202** | 10 475 ms API / 11 793 ms browser | *"Loading the run request…"* for eleven seconds with no progress of any kind, then the run page at `published` |
| 4 | poll to terminal | **200** | 14 ms, **1 reading** | *"Not polling. This reading is final."* — the run is already terminal in the response to the POST. The UI never shows `running` (§6 `W15RUN-6`) |
| 5 | read the findings, open one | **200** | 26 ms + 15 ms | 3 findings, grouped *internal_contradiction 2* / *explicit_placeholder 1*, each with its verdict and pages. Opening one: the finding text, the recommendation, *"Quotations on page 2 — 1.3. Степень огнестойкости здания — II. · page 2, chars 707–746"*, and the honest caption *"Page-level navigation only: no highlight overlay and no bounding box."* `GET /versions/{uid}/content` returns the 58 978 PDF bytes at 200 |
| 6 | accept, reject, comment | **201 ×3** | 30 / 32 / 38 ms | *"current verdict accepted"*, and a History list: `accept → accepted`, then `comment`, both `local-reviewer`, with UTC times. Repeated through the **browser**: `POST …/decisions → 201` and the history gains the row within 1 s |
| 7 | download the CSV | **200** | 24 ms | a real browser download named `run_01M2RT02YTYZ9HGC8C545KJ153-findings.csv`, offered as *"17 columns, utf-8 with a byte-order mark, RFC 4180 quoting"* |

**The CSV, parsed as RFC 4180 rather than split on commas** (my first pass split on commas
and produced nonsense; the file was right and the check was wrong):

```
4302 bytes · BOM ef bb bf present · 6 CRLF, 0 bare LF · 17 columns, in the frozen order
5 data rows (one per evidence item, as OD-11 says) over 3 findings
project_uid = prj_01M2RT029F51H3J8F3VBR7MDEM   ← the project created in step 1
version_uid = ver_01M2RT02WWX9C4JWA170SFGH2Q   ← the version published in step 2
run_id      = run_01M2RT02YTYZ9HGC8C545KJ153   ← the run started in step 3
run_state = published · provider_mode = live
current_verdict = accepted (2 rows), rejected (2 rows), pending (1 row)
latest_comment  = "W15-RUN: checked against the PDF page; the quotation is on the page it names."
```

It resolves to exactly that project, that version and that run. The copy the **browser**
downloaded differs from the API's by exactly three fields — `latest_comment`,
`latest_decision_id`, `decision_recorded_at` — because a comment had been appended through the
UI between the two downloads. The export reflects a decision recorded seconds earlier.

**The credential never reached the browser.** 85 browser requests across the journey, **0
carrying an `Authorization` header**, one origin touched. `GET /bff/v1/projects/..%2f..%2fhealthz`
→ 404 *"A path separator inside a single segment is not a path this forwarder builds."*
`/healthz` through the public origin → 404. Direct `/api/v1/projects`, `/api/v1/runs/{id}`,
`/api/v1/findings/{uid}` and `POST /api/v1/runs` with no credential → **401
`authentication_required`** from the application, one of each kind.

## 5. Live, not recorded — and what it cost

`AUDITMANAGER_PROVIDER_MODE=proxy`, the three `PROXY_LLM_*` names copied from
`/root/projects/PDF-Analysis/.env.provider` into `infra/deploy/env/provider.env` (git-ignored,
mode 600, never passed to `--env-file`). No credential is printed anywhere in this document or
in any log under `/root/w15run-logs/`.

```
run_01M2RT02YTYZ9HGC8C545KJ153  live  3895 in / 761 out  9 943 ms  cost 38 500 µ$  measured
run_01M2RTFR8TNHN7A6QK0WXEJ2ZV  live  3895 in / 758 out 11 119 ms  cost 38 425 µ$  measured
                                                                  total  $0.076925
```

against the `OD-03` ceiling of USD 1.00. `cost_basis` is **`measured`**, not estimated, on
both. Model identity recorded as `claude-opus-5`, provider `anthropic`, through the proxy.

**Why two and not one.** The dispatch asked for one. The first was the client journey. The
second is the browser's own click on *Start run* — which is `D-5` itself, and the one thing
the register has been asking for since 09-16. Four more cents to answer a debt row from the
browser rather than from a client that imitates one seemed the right trade; it is 7.7 % of the
ceiling and I am recording it rather than rounding it.

## 6. Defects, unrepaired, with their trees

### `W15RUN-1` — a restored dump refuses every later upload of its own bytes · `infra/deploy/**` (wave 14)

**Measured, twice, on the stack wave 14 left running:**

```
POST /bff/v1/projects/prj_01M2RSTFM6PZDS994KZVJPPSWC/documents   (ar_baseline.pdf)
409
{"contract_version":"1.0.0-draft.1","error_code":"conflict",
 "message":"A concurrent write lost the optimistic-concurrency check or a uniqueness
            invariant would be violated. Used only when no more specific conflict code applies.",
 "correlation_id":"cid-716da0ea33c53b162f75f48aca9f94ee","retryable":false,
 "details":{"aggregate_type":"Blob"}}
```

**The discriminator, and it is clean.** The *same bytes*, in a *second project*, on the
**clean** instance where that blob was published by the adapter itself: **`201`**. So the
publish path is right and content-addressed idempotency works. The fault is in what the
restore left behind.

**The mechanism, read off the source and confirmed against the bucket.**
`storage/s3.py:_metadata_for` writes **four** user-metadata keys onto every canonical object:
`blob-id`, `blob-role`, `content-sha256`, `content-size`. The restored object carries **one**:

```
blobs/7K/DZ/7KDZE8SQTZ9K23JYB742HG7K8J  58978  application/pdf  {"content-sha256": "6d53674f…"}
```

`infra/deploy/object_attrs.py` records only `content-sha256` and `content-type`;
`reset.sh` line 217 reattaches only those two with `mc cp --attr`. So `_record_from_head`
reads `BlobRole("")`, `publish()` finds `record.role != verified.role`, and raises
`BlobAttributeConflictError`.

**Why nothing caught it.** Reads only verify `content-sha256`, so `W14-PKG`'s restore check —
*"the API served the document's bytes again at 200, sha256 identical"* — passes on a
half-restored object. **The restore was verified by reading and the loss is only visible by
writing.** This is the same bug wave 14 found (*"`mc mirror` is not a backup of an object"*)
surviving inside its own repair: two of four attributes were fixed, and the `dump-verified`
guard was written to refuse a short sidecar, which cannot see a sidecar that is complete in
the columns it has and missing two columns it never had.

**Blast radius.** `PA-01` criterion 10 — *"the dump restores the wiped state"* — is currently
**false**, and false in the direction that looks true. After the pilot's wipe-and-restore,
every document already in the system is a landmine: re-upload it and the operator gets a 409
naming nothing.

### `W15RUN-2` — that 409 is undiagnosable from the wire · `contracts/domain/v1/error-codes.json` + `src/auditmanager/storage/errors.py`

`conflict` declares `safe_detail_keys: ["aggregate_type", "expected_revision"]`, so the
`blob_id`, `role` and `media_type` that `BlobAttributeConflictError` is constructed with are
**all dropped before the wire**. `TemporaryBlobLostError` — *"the temporary upload is no longer
present"*, a completely different fault — produces a **byte-identical** envelope.

Diagnosing `W15RUN-1` took a source read and a `head_object`. An operator has neither. The
catalog is frozen, so this is a reseal question and not a lane decision; naming it here so the
next reseal has a reason on the table.

### `W15RUN-3` — nothing lists a project's documents, versions or runs · `contracts/api/v1/openapi.json` (frozen) + `web/src`

**This is the biggest thing in this report and it is not a bug in any code.** The twelve
operations are:

```
POST /projects · GET /projects · POST /projects/{uid}/documents · POST /runs
GET /runs/{id} · GET /runs/{id}/findings · GET /runs/{id}/export.csv
GET /versions/{uid} · GET /versions/{uid}/content
GET /findings/{uid} · POST /findings/{uid}/decisions · GET /findings/{uid}/decisions
```

Every read below the project list takes an identifier the client must already be holding.
**There is no `listDocuments`, no `listVersions`, no `listRuns`.**

**What that does to a user, measured in the browser.** Load a project page on which a version
*was* published, in a new tab:

```
Published version
  No version published in this session. Upload a PDF above.
Start run controls present: 0
bff calls made by that page load: (none — zero)
```

The project screen queries **nothing**. The version is in the database, the object is in the
bucket, the run and its three findings and four decision events are all there — and there is
no screen that can reach any of it. Reload the tab and yesterday's work is gone from the
product, though not from the store. `listProjects` cannot even say a project *has* documents:
`document_count` is optional and is not populated, so every row on the project list reads
`documents —`.

**Why four certifications missed it.** They all drive forward, in one process, holding every
identifier they minted. None of them ever reloaded a page or came back to a project. Nothing
about the product is wrong on the path they walk.

**Consequence for `PA-01`.** Criterion 8 — *"the server is rebooted and every canonical row,
object and decision survives"* — is **unverifiable through the browser** as the product
stands. The rows survive; no screen reaches them. Closing this is a contract change, and the
frozen document is nobody's lane decision.

### `W15RUN-4` — a published run reports neither its stage timings nor its finding count · `src/auditmanager/bootstrap/adapters.py`

The run screen shows, for a run with three published findings and four completed stages:

```
Published findings: not reported
Stages   Stage                      Status      Started   Finished
         source_preparation         succeeded      —         —
         page_geometry_extraction   succeeded      —         —
         document_context_build     succeeded      —         —
         text_analysis              succeeded      —         —
```

**The data exists in all three layers except the one that assembles the response.** The
`stage_result` rows carry real timestamps — `text_analysis` ran `23:07:31.582 → 23:07:41.561`,
9.98 s. The contract's `StageState` **declares** `started_at` and `finished_at`.
`api/schemas/runs.py:68-71` **serializes them when the view has them**. And `RunStatusView`
carries `published_finding_count` and `diagnostic_observation_count` as `int | None`, with
`runs.py:95-98` ready to emit them.

`_run_status_view` in `bootstrap/adapters.py:266` constructs each `StageStateView` from
`stage_id`, `status`, `stage_version` and `error_code` only, and never sets either count. Four
declared, populated, serializable fields with no producer — the same shape as `D3` in that
function's own history (*"a required API property simply had no producer"*), in the same
function, one field set further along.

### `W15RUN-5` — `created_at`, `updated_at` and `terminal_at` are the same instant · `src/auditmanager/runs/**`

```
run_01M2RT02YTYZ9HGC8C545KJ153  created 23:07:31.160011  terminal 23:07:31.160011
run_01M2RTFR8TNHN7A6QK0WXEJ2ZV  created 23:16:04.502542  terminal 23:16:04.502542
```

Identical to the microsecond, on runs that took **9.9 s** and **11.1 s** — a figure the
`model_call` row records correctly as `latency_ms`. The run screen therefore tells the
operator *"Created 23:07:31 UTC / Terminal at 23:07:31 UTC"*, and any duration computed from
the API is zero. Nothing in the product can answer "how long did that run take", which is the
first question anyone asks about a model run and one of the measurements `P04` wants from real
use.

### `W15RUN-6` — there is no observable `running` state · `src/auditmanager/bootstrap/adapters.py`

`start_run` calls `execute_run(...)` **inline** before returning, so the `202 Accepted` carries
a terminal `state`. Measured: the polling loop made **exactly one request** and found
`published` in it. The browser sits on *"Loading the run request…"* for 11.4 s with no state,
no stage progress and no cost, then jumps to `published`.

Two consequences, and I am reporting them rather than calling either one wrong, because
`nginx.conf`'s 300 s read timeout shows wave 14 knew the call was synchronous:

1. `PA-01` criterion 4 asks that *"the UI distinguishes running, published, partial and
   failed"*. Two of those four states are **unreachable through the product** — no client can
   observe a run that is `running`, because no response exists while it is. `W12-WEB`'s polling
   machinery, `RUN_POLLING`'s backoff schedule and `pollRunStatus` are all exercised by exactly
   one reading in practice.
2. The 300 s proxy timeout is the entire safety margin. One AR page cost ~1.4 s of model
   latency here; the contract permits **30** pages. A long document that crosses 300 s hands
   the browser an nginx 504 — an HTML page, not an `ErrorEnvelope`, and no catalog code
   explains it.

### Not a defect, and I checked rather than reported it

**The decision history refreshes.** My first browser pass appeared to show a comment appended
without the History list updating. It was my own script truncating its output at 1400
characters. Measured deliberately: `POST …/decisions → 201`, a `GET …/decisions → 200`
refetch, and the new event on screen inside **1 second**. Recorded because the programme's
habit is to keep the wrong turns, and a false defect costs another session a day.

**`provider_mode: "live"` on a `proxy` deployment is correct.** The contract's `ProviderMode`
enum is exactly `["live", "recorded"]`; `proxy` is a *how*, and a proxied call is a live call.
The reported value is right.

**A `favicon.ico` 404** on every page load, one console error. Cosmetic; named so it is not
mistaken for something.

## 7. Cost visibility — a `PA-01` blocker that is nobody's bug

`PA-01` criterion 4 requires a live run *"with its provider mode and cost visible"*.

- **Provider mode is visible**, and well: on the run page (*"published · live · provider mode:
  live — Live provider calls were made for this run"*), on the review screen, in the finding's
  provenance, and in CSV column 6.
- **Cost is visible nowhere.** It is recorded — `model_call.cost_micros = 38500`,
  `cost_basis = measured` — and it is on **no** operation, in **none** of the seventeen CSV
  columns, and on **no** screen. `grep -c cost contracts/api/v1/openapi.json` → **1**, and that
  one is the string `cost_budget_exceeded`.

So criterion 4 cannot be satisfied as the contract stands, and satisfying it is a reseal, not
a lane fix. Raising it here because it is the kind of thing that gets discovered on the day of
the checkpoint.

## 8. What is false in the dispatch

**8.1 — "reuse or rebuild" is not a free choice; reuse was impossible.** §1. Wave 14's images
predate `W15-AUTH`, carry `NEXT_PUBLIC_API_BASE_URL=/api/v1` in the bundle, have no `/bff/v1`
route and no credential in the `web` container. A browser against that deployment gets 401 on
everything. The rebuild is mandatory for any browser journey, and a session that took the
"reuse" branch at face value would have spent its first half diagnosing `W15-AUTH`'s blocker a
second time.

**8.2 — "`.env.provider` carries `PROXY_LLM_*`" is right about one file and not the one the
stack reads.** `/root/projects/PDF-Analysis/.env.provider` does carry them, and it is where I
took them from. But the deployed stack reads `infra/deploy/env/provider.env`, a different file
in a different tree, present in a fresh worktree only as `.example` with every value blank
(`compose.server.yml`'s `env_file: … required: false`). Copying the three names across is a
step the dispatch does not mention and without which the stack starts happily in `proxy` mode
and refuses at `settings.load`.

**8.3 — `W15-AUTH` §7's "two lines in `infra/**` … are reported rather than reached for" was
true when written and is stale at this HEAD.** `7477b79` landed both. A session reading
`W15-AUTH` as current would go looking for work already done. Noted because the dispatch sends
the reader to that document as if it described the tree.

**Checked and true:** `checkout_is_unchanged` really is at
`tests/integration/foundation/conftest.py:542`; the AR fixture is at
`fixtures/synthetic/ar/ar_baseline.pdf`, 58 978 bytes, 8 pages; `gate-w15b` and its four ports
were free; wave 14's stack really was up on 31480 with the restored document; a run really
does cost about $0.038; the `OD-03` ceiling is 1.00 and `settings.load` defaults to it; the
proxy at `PROXY_LLM_BASE_URL` is reachable from this host; and `D-5`, `W14-PKG` and
`W15-AUTH` say what the dispatch says they say.

## 9. The gate

Instance `gate-w15b`, at the commit this document is in, after `git status --porcelain` was
empty:

```
1726 passed, 5 skipped, 168 subtests passed
foundation 35 passed · frontend 39 files, 498 passed
GATE OK: battery, foundation, frontend and whitespace all pass
```

`/root/w15run-logs/gate.log`. The figures are the dispatch's, unchanged: this session adds no
test and touches no `src/`, `web/src`, `contracts/` or `infra/`. Two alpha stacks were running
during the gate on ports the gate does not use, in their own compose projects and networks,
and did not interact — the same arrangement `W14-PKG` §8 recorded.

## 10. Reproducing this

```
git worktree add /root/w15run -b agent/w15-run origin/dev
cd /root/w15run && cp .env.example .env            # instance gate-w15b, ports 55760/59360/59361
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12 && npm --prefix web ci

cp /root/w14pkg/infra/deploy/env/alpha.env infra/deploy/env/alpha.env    # or from .example
sed -i 's#^NEXT_PUBLIC_API_BASE_URL=.*#NEXT_PUBLIC_API_BASE_URL=/bff/v1#' infra/deploy/env/alpha.env
sed -i 's/^AUDITMANAGER_PROVIDER_MODE=.*/AUDITMANAGER_PROVIDER_MODE=proxy/' infra/deploy/env/alpha.env
grep -E '^PROXY_LLM_' /root/projects/PDF-Analysis/.env.provider > infra/deploy/env/provider.env
docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml up -d --build

# the client journey (the app's own generated client, over a socket, no credential of its own)
cd /root/w15run-drive && W15_ORIGIN=http://127.0.0.1:31490 npx vitest run tests/journey.test.ts

# the browser journey
cd /root/w15run-browser && node journey.mjs        # and d5c.mjs for the D-5 click

# W15RUN-1, on a stack restored from a reset.sh dump
curl -s -X POST $ORIGIN/bff/v1/projects/$PRJ/documents -H "Idempotency-Key: $(uuidgen)" \
     -F "file=@fixtures/synthetic/ar/ar_baseline.pdf;type=application/pdf"       # -> 409
```

Both harnesses live outside the worktree, for `W12-WEB`'s reason. **Neither is committed, and
that is a deliberate trade against `D-5`'s own lesson** — the evidence they produced is in
this document and in `/root/w15run-logs/`, where a reader can check it, rather than only in a
log outside the repository. A reusable version belongs to `W15-E2E`, which owns `e2e:pc01`;
committing a second copy of `web/src`'s client wiring here would put a harness where a later
session could mistake it for the tree.

## 11. Left running

`auditmanager-w14a` on **31480**, rebuilt at this HEAD, restored document intact, carrying
`W15RUN-1` — left up on purpose so the defect can be re-measured.
`auditmanager-w15b` on **31490**, clean, holding this journey's project, version, run, three
findings, four decision events and two live model calls.

No tag, no push, no merge to `main`. Branch `agent/w15-run`.
