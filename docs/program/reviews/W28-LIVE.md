# W28-LIVE — a real analysis of a document that has no recording

**Session `W28-LIVE`, 2026-09-21. Branch `agent/w28-live` from `origin/dev` at `ca16a18`.**

The question was what a person gets when they upload **their own** PDF — one the recorded
corpus has never seen — in `proxy` mode and in `recorded` mode. Both were driven through a
browser, on one instance this session brought up and controlled, at a commit
`verify-deployed.sh` says the stack **is**.

**Both answers, in one line each.**

| mode | what the person gets | how long | what it costs |
|---|---|---|---|
| `proxy` | `published`, **1 finding**, correct, grounded at its quotation, cost basis `measured` | 9.1 s from pressing **Start run** to the terminal | **USD 0.018305** for a 3-page document |
| `recorded` | `failed`, nothing published, the screen prints the bare code `dependency_unavailable` and no sentence explaining it | **16.1 s**, of which **10.0 s is a retry ladder waiting for a local file to appear** | nothing |

**The verdict: yes, switch the owner's stand to `proxy`.** §6 says why and what it costs.

---

## 1. The stand, and what was and was not touched

**31500 was not touched.** `auditmanager-w19a`, mode `recorded`, is the owner's stand and
this session neither switched it, restarted it, nor wrote a single row into it. No project,
document, version or run in this review lives on it.

**This session's own instance:**

```
ALPHA_INSTANCE=auditmanager-w28live        ALPHA_HTTP_PORT=31580
POSTGRES_DB=audit_w28live                  S3_BUCKET=auditmanager-w28live
env file: /root/w28live/infra/deploy/env/alpha.env   (mode 600, git-ignored, its own secrets)
```

**It was brought up without a cold build, on purpose.** `df -h /` on arrival read **6.3 GB
free on a 119 GB disk, 95 % used**, and `W26-HOST` §5 measures one clean-clone cold-cache
deploy at ≈ 5.5 GB. So instead of `deploy.sh`'s unconditional `compose build`, the two
images already on the host were retagged onto this instance's names and `compose up -d` was
asked to use them:

```
docker tag auditmanager-w19a-api:latest auditmanager-w28live-api:latest
docker tag auditmanager-w19a-web:latest auditmanager-w28live-web:latest
docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml up -d
```

`UP_EXIT=0`, zero bytes of disk. **Then the retag was checked rather than trusted**, and it
did not survive the check:

```
verify-deployed.sh --env-file …/alpha.env --repo /root/w28live     EXIT=6
  -- the api image against the tree --
    src/ 141 files, identical | db/ 9 | contracts/ 34 | fixtures/recorded/ 7 : all identical
  -- the web image against the tree --
    /web/tests/contract/pc01-error-codes.contract.test.ts  MISSING FROM THE IMAGE
    /web/src/shared/api/authorization.ts     DIFFERENT BYTES
    /web/src/shared/api/errors.ts            DIFFERENT BYTES
    /web/src/shared/config/server-env.ts     DIFFERENT BYTES
    …and two test files.  219 files: 1 missing, 5 different, 0 unexpected
  the deployed stack is NOT this tree -- 6 file(s) disagree.
```

### Finding 1 — the owner's stand is serving a web tier that predates `W27-WEB`

Those six files are `137689a fix(W27-WEB): the PC-01 code subset is derived from the
contract, and the guard reads web/src` — **the commit that repaired the error-code render
list**, merged yesterday as *"the render list is derived from the contract, and it was
missing four codes"*. The api image rebuilt at 13:50 today matches `ca16a18` exactly; the
web image, built at 13:39, does not.

This is a statement about **`auditmanager-w19a`**, the owner's stand, because that is where
these images came from. **`origin/dev` has the repair and 31500 does not serve it.** It is
not a defect in the tree and it is not mine to fix — it needs a redeploy of 31500, which is
the integrator's act. Registered below.

It is also the reason the rest of this review is trustworthy: `run-progress.tsx` and
`run-presentation.ts`, which render every sentence quoted in §4 and §5, are **not** among
the six, so what this session measured is what 31500 renders too.

**The web image was therefore rebuilt**, alone, and the cache reclaimed immediately:

```
docker compose … build web          BUILD_EXIT=0   df: 5.7 G -> 2.9 G free
docker builder prune -af            Total: 1.838GB  df: 2.9 G -> 4.3 G free
docker compose … up -d ; reload-proxy.sh
verify-deployed.sh …                EXIT=0
  the api image against the tree --  src/ 141 files, identical  (+ db, contracts, fixtures)
  the web image against the tree --  web/ 219 files, identical
  verify-deployed.sh: the deployed stack IS this tree (36bb85e).
```

Every measurement below was taken after that line. Disk never went below **2.9 GB free**,
and the host ended with more headroom than it started with on the docker side.

## 2. The document

`fixtures/synthetic/ar/ar_baseline.pdf` is the **one** document with a recording —
`fixtures/recorded/text_analysis/6c208358….json`, keyed by request checksum, with
`inputs/` and `variants/` invisible to `RecordedAdapter()` by construction. Driving it
would have measured the replay path, which is the opposite of the question. Every fixture
under `negative/` violates exactly one envelope rule on purpose, so none of them is a valid
upload either.

So this session built a second one:

```
tests/e2e/pc01/journey/fixtures/w28-live/w28_own_document.pdf
  48450 bytes   sha256 4a61f44d72363611783a9ce77acdbc8834fd5bc98dbe13e608bc28707eba2dc7
  3 pages, A4, embedded text layer on every page, unencrypted
  built by make_document.py beside it — same generator, same committed font subset,
  no clock and no PRNG: two runs of the builder produced the same digest
```

It is a different building (a 120-place kindergarten, not a 64-flat block), it says
different things, and it carries **one deliberate internal contradiction**: §1.3 *"Степень
огнестойкости здания — II."* on page 2 against §4.1 *"Степень огнестойкости здания принята
III"* on page 3. It lives under `tests/e2e/**` and **not** in `fixtures/synthetic/ar/`: that
corpus is sealed, enumerated by contract tests and hashed into `SHA256SUMS`, and this
session owns no slot in it.

## 3. The instrument

The journey's own write half — `tests/e2e/pc01/journey/write.mjs` over `cdp.mjs` — pointed
at a manifest of this session's own. One cold Chromium process per step, own profile, no
cache; every response body fetched from the browser before it dies; `innerText` read rather
than status codes (`D-28`).

Nothing in `tests/e2e/pc01/journey/manifest.json` or its conformance guard was touched —
`W28-GUARD` owns both, and the guard reads `manifest.json` and only `manifest.json`, so
none of the four files added here can redden or green the gate. Two new files:

* `tests/e2e/pc01/journey/look.mjs` — read one named screen in a cold browser and write down
  what it said. It **asserts nothing**, deliberately: a reading tool that also judged would
  invite the judgement to be written after the reading.
* `fixtures/w28-live/` — the document, its builder, and four manifests.

## 4. `proxy` mode, on a document with no recording

`AUDITMANAGER_PROVIDER_MODE=proxy`, the three `PROXY_LLM_*` names in
`infra/deploy/env/provider.env`. Driven 2026-09-21 09:51–09:52 UTC.

```
ok  create-project   api=3  prj_01M31P235TXNZDXPWWJ1C7T2SW
ok  upload-document  api=4  ver_01M31P2Y5TPMWMP6MNTM0W89AY
ok  start-run        api=7  run_01M31P3RHXB778RRKYZ1FSX8F0  terminal=published in 9060ms/150000ms
write steps checked: 3/3 — e2e:pc01 OK
```

**The envelope, from the body the browser itself received:**

```json
{"run_id":"run_01M31P3RHXB778RRKYZ1FSX8F0","state":"published","provider_mode":"live",
 "degradation_set":[],"published_finding_count":1,"diagnostic_observation_count":0,
 "cost_micros":18305,"cost_basis":"measured","model_call_count":1,
 "created_at":"2026-09-21T09:52:47.162679Z","terminal_at":"2026-09-21T09:52:54.197291Z"}
```

All four stages `succeeded`; `text_analysis` took **6.6 s** of the 7.0 s.

### What the screen showed, stage by stage

**After Create** (`/projects`), in its own `role=status` line:

> Created W28-LIVE own document 2026-09-21T09-51-26-267Z — prj_01M31P235TXNZDXPWWJ1C7T2SW

**After Upload**, having navigated by itself to the published version:

> This version ⏎ My own AR document … ⏎ Version ver_01M31P2Y5TPMWMP6MNTM0W89AY ⏎ Document
> doc_01M31P2Y5S7EVM10ZJ26QQD00C ⏎ Ordinal 1 (display order only, never an identity) ⏎
> Media type application/pdf ⏎ **Pages 3** ⏎ **Size 47.3 KiB (48450 bytes)** ⏎ **SHA-256
> 4a61f44d72363611783a9ce77acdbc8834fd5bc98dbe13e608bc28707eba2dc7** ⏎ Published 2026-09-21
> 09:52:20 UTC ⏎ … ⏎ This version and its manifest are immutable. There is no endpoint that
> changes either. ⏎ … ⏎ The version is published and immutable. Starting a run reads it; it
> never changes it. ⏎ **Start run** ⏎ The run uses the provider mode this deployment is
> configured for. It is shown on the run, and it is never chosen here.

The digest the screen prints is the digest of the file on disk. A person can check that
their own document arrived unaltered, with no tooling.

**The run screen**, readings `0ms in_flight` → `9060ms published`, then
`data-run-activity="stopped"`:

> published ⏎ live ⏎ provider mode: live ⏎ **Live provider calls were made for this run.** ⏎
> … ⏎ Took **7.0 s** ⏎ … ⏎ **The run reached its success terminal, `published`.** ⏎
> **Published findings: 1** ⏎ Diagnostic observations ⏎ Recorded: 0 ⏎ A diagnostic
> observation is something the run noticed and did not admit as evidence. It is not a
> finding, it is not counted as one, and the two totals are never added together. ⏎ **Cost**
> ⏎ Spent **0.018305 provider currency units (18305 millionths, the integer the run
> stored)** ⏎ Provider calls this total sums **1** ⏎ Basis **measured** ⏎ **Every call this
> figure sums reported its own cost, so the figure is measured.** ⏎ … ⏎ Stages ⏎
> source_preparation succeeded 99 ms | page_geometry_extraction succeeded 251 ms |
> document_context_build succeeded 26 ms | **text_analysis succeeded 6.6 s** ⏎ Review ⏎
> Review findings — this run's provider mode is live. ⏎ Is this reading final? ⏎ **Not
> polling. This reading is final.**

**The review screen** — `look.mjs`, cold browser, `/projects/…/runs/…/review`:

> internal_contradiction 1 ⏎ **Степень огнестойкости одного и того же здания указана
> по-разному: в общих данных — II, в разделе противопожарных требований — III.** ⏎ pending
> ⏎ **pages 2, 3** ⏎ … ⏎ Согласовать единое значение степени огнестойкости здания во всех
> разделах документа. ⏎ page 2 page 3 live ⏎ **Quotations on page 2** ⏎ **1.3. Степень
> огнестойкости здания — II.** ⏎ **page 2, characters 663–702 of the whole document, not of
> page 2** ⏎ Page-level navigation only: no highlight overlay and no bounding box. The
> quotation above is the exact string the grounding gate verified at its anchor. ⏎ Decision
> ⏎ current verdict pending ⏎ Accept Reject ⏎ Append a comment … ⏎ No decisions yet ⏎
> Nobody has judged this finding. Accepting or rejecting appends the first event. ⏎ Export ⏎
> Download run_01M31P3RHXB778RRKYZ1FSX8F0-findings.csv ⏎ 17 columns, utf-8 with a
> byte-order mark, RFC 4180 quoting, one row per evidence item.

**This is the product working.** A document the system had never seen, a real provider
call, one correct finding, grounded at a character range in a quotation that is verbatim in
the file, with a recommendation, a verdict the reviewer owns, and a CSV. Zero console
errors, zero uncaught exceptions, **zero browser requests carrying an `Authorization`
header** — the journey fails on any, and it exited 0.

**Repeated.** A second run of the same document, from a second manifest that *declares* this
outcome instead of recording it: `published` in 9062 ms, 1 finding, **`cost_micros 18480`**,
basis `measured`. The two costs differ by 175 millionths — output length, not instability.

## 5. `recorded` mode, on the same document

Same instance, same document, `AUDITMANAGER_PROVIDER_MODE=recorded`, `api` recreated, proxy
reloaded, mode confirmed inside the container. Driven three times; all three identical.

```
ok  start-run  api=8  run_01M31PBCQKH8QZ3KEDM93PCWD1  terminal=failed in 16077ms/150000ms
{"state":"failed","provider_mode":"recorded","terminal_reason":"dependency_unavailable",
 "degradation_set":["text_analysis"],"published_finding_count":0,
 "stages":[… {"stage_id":"text_analysis","status":"failed",
              "error_code":"dependency_unavailable",
              "started_at":"…09:56:57.600969Z","finished_at":"…09:57:07.610672Z"}]}
```

Note what is **absent**: no `cost_micros`, no `cost_basis`, no `model_call_count`.

### What the screen actually renders — measured, not predicted

> failed ⏎ recorded ⏎ provider mode: recorded ⏎ **Replayed from recordings. This run is not
> evidence of a live provider call.** ⏎ … ⏎ Took **10.4 s** ⏎ … ⏎ **The run terminated
> `failed`. Nothing was published.** ⏎ **Terminal reason: `dependency_unavailable`** ⏎
> Diagnostic observations ⏎ Recorded: 0 ⏎ … ⏎ **Cost** ⏎ **This run made no provider call,
> so it has no cost to report. That is not a cost of zero — nothing was spent here because
> nothing was called, and the two are different claims.** ⏎ Stages ⏎ source_preparation
> succeeded 90 ms | page_geometry_extraction succeeded 262 ms | document_context_build
> succeeded 27 ms | **text_analysis failed dependency_unavailable 10.0 s** ⏎ Review ⏎
> **There is nothing to review.** ⏎ **A run has findings only once its terminal publishes a
> result — published or partial. This run is `failed`.** ⏎ Is this reading final? ⏎ Not
> polling. This reading is final.

There is **no `Retry` button** on this screen and no alert. Zero console errors, zero
uncaught exceptions.

### Finding 2 — the sentence the dispatch predicted is rendered by nothing

The task file expected *"a required dependency is unavailable"*. **No screen renders it.**
That string exists once in the tree, at `src/auditmanager/api/routers/declarations.py:56`,
as the OpenAPI **description of the 503 response** — documentation, never UI text.

The other candidate, *"The provider this run needs is unavailable."*
(`web/src/entities/audit-run/model/run-failure.ts:76`), is real UI text with a genuinely
good paragraph behind it — *"Retrying reuses the same idempotency key; the run is not
started in a different provider mode instead."* — but it is reachable only when the
**`startRun` request itself** answers an error envelope. Here `startRun` answered **`202
queued`** and the stage failed asynchronously, so that branch never runs. The run screen's
`failed` arm renders the raw code and no sentence at all.

This was asserted, not merely observed:
`fixtures/w28-live/w28-recorded-redden.manifest.json` declares both sentences and a
`published` terminal. Measured: **exit 1, four findings**, two of which are *"the screen did
not render …"* with the whole rendered body attached. `w28-recorded.manifest.json`, which
declares the five sentences above, exits **0**.

### Is that acceptable for a prototype? Partly — and the split is the useful part

**True:** yes, every word. `failed` is the state, `dependency_unavailable` is the stage's
error code, nothing was published, and nothing was spent. The cost paragraph is unusually
careful: it refuses to print `0.00`, because an uncalled provider and a free call are
different claims. The provider-mode caption is honest in both directions.

**Useful:** no. `dependency_unavailable` is a code, not an explanation. It does not say
*which* dependency, and it does not say the one thing the person needs: **their document is
fine, the provider is fine, and this deployment simply has no recording for it.**

**Misleading:** not in the `W27-REFUSE` sense, but adjacent to it. `W27-REFUSE` found
nginx's `413` rendering as *"The upload did not reach the API"* — true, wrong cause. Here
the screen states **no cause at all**, so it cannot state a wrong one; but the code it does
print names a *dependency outage*, and a reasonable operator reading
`dependency_unavailable` will go and check whether the provider is down. It is not. The
word is the transport word being used for a local cache miss.

**The recommendation is to repair nothing, and this session repaired nothing.** The screen
is honest, the run is correctly `failed`, no result is invented, and the blast radius is a
prototype with one reviewer. The cheap repair — a `recorded`-mode sentence saying *this
deployment replays recordings and has none for this document* — lives in `src/**` or a new
`web/src` branch keyed on a distinction the envelope does not currently carry, and neither
is this session's slot. **Registered, not fixed**, and §6 makes it moot for the owner
anyway: the answer to the `recorded` screen is not to reword it, it is to stop being in
`recorded` mode.

### Finding 3 — a missing local file is retried on a network-outage ladder, and it costs 10 seconds

`text_analysis` took **10.0 s** to fail. `RecordedAdapter.complete` fails on an
`except OSError` from a `Path.read_text` — a deterministic local-filesystem fact, known in
microseconds, that cannot become true by waiting. The 10.0 s is exactly
`src/auditmanager/runs/retry.py`:

```
ATTEMPT_BUDGET   = 3
BACKOFF_SECONDS  = (2.0, 8.0)      # 2.0 + 8.0 = 10.0
```

That policy is well-argued and correct **for the case it was written for**: `P4-RUN-01`
measured three of seventeen live attempts losing the provider, and all three succeeded on
the next try. But it is keyed on the error **code**, not on whether the failure is really
transport, and `RecordedAdapter` raises the transport code for a local miss — so the miss
is retried twice and the file is re-read, absent, three times.

The cost to a person is the **16.1 s** they wait, three times out of three measured, before
being told something that was knowable immediately. It is not a correctness defect and it
touches `src/**`, a forbidden hotspot here. Registered.

## 6. The verdict: switch the owner's stand to `proxy`

**Yes. It is safe, it is cheap, and `recorded` is not a mode a person can use.**

**What the owner meets today, in `recorded` mode, on their first upload.** Exactly one
document in the world works on that stand: `ar_baseline.pdf`, the one with a recording.
Every other PDF — including every real document the owner would ever want to try — creates
a project, uploads and publishes a version correctly, then waits 16 seconds and says
`failed / dependency_unavailable` with nothing to review. Nothing is broken and nothing is
wrong; the product simply cannot be evaluated in this mode, because the only question worth
asking it is one it declines to answer.

**What they meet in `proxy` mode.** The run in §4: 9 seconds, a published result, a correct
finding on a document nobody had prepared for, grounded at its quotation, with a decision
control and a CSV.

**The money, measured rather than estimated.**

| | |
|---|---|
| this session's total spend | **USD 0.036785** — two runs, 18305 + 18480 micros, both `measured` |
| per run, 3-page document | **USD 0.0183** |
| per run, 8-page `ar_baseline` | **USD 0.037225** (`W24-CERT2`, one live run) |
| `OD-03` ceiling, per run | **USD 1.00** |

Two documents, 3 and 8 pages, cost 1.8 % and 3.7 % of one run's ceiling. The upload envelope
caps a document at **30 pages**, so linear extrapolation from those two points puts the
worst admissible document near **USD 0.14** — about a seventh of the ceiling, and that is an
extrapolation from two measurements, not a measurement. The ceiling is enforced per run and
defaults to `OD-03`'s value; nothing here approached it.

**What an operator sets, and what changes for them.** One environment variable, in
`infra/deploy/env/alpha.env` on the stand:

```
AUDITMANAGER_PROVIDER_MODE=proxy
```

then `docker compose --env-file … up -d` (which recreates `api` only) and
`infra/deploy/reload-proxy.sh`. Confirm with
`docker exec auditmanager-w19a-api-1 sh -c 'echo $AUDITMANAGER_PROVIDER_MODE'`.
`infra/deploy/env/provider.env` must carry `PROXY_LLM_BASE_URL` and `PROXY_LLM_TOKEN` — the
api refuses to start in `proxy` mode without both, at `settings.load`, rather than starting
and failing later. Measured on this instance: the switch each way took **under 40 seconds**
and recreated `api` alone.

**Rolling back is the same variable set to `recorded`**, with the same two commands. It is
reversible at any moment and no run already recorded changes: `provider_mode` is stamped per
run, `live` runs stay `live` and `recorded` runs stay `recorded`, and the screen keeps
saying which. **There is no silent downgrade** — `run-failure.ts` states outright that the
application never offers to fall back to `recorded`, and this session saw nothing that
contradicts it.

**Three things to know before switching.**

1. **Every run then spends.** There is no per-day or per-deployment budget in PC-01, only
   the per-run ceiling. The owner's own uploads are the only thing bounding the total.
2. **`proxy` is a transport, not a provenance.** A proxied call is recorded and displayed as
   `provider_mode: live`, and the screen says *"Live provider calls were made for this
   run."* That is correct — a real model answered — but the word `proxy` appears nowhere in
   the UI, and anyone reading the run for provenance should know it.
3. **Redeploy 31500 first** (Finding 1). It is serving a web tier without `W27-WEB`'s error
   render repair. Nothing in §4 or §5 depends on those files, but switching a stale stand to
   a paying mode is the wrong order.

## 7. What is not true in the task file

* *"Today that is `dependency_unavailable` — 'a required dependency is unavailable'"* —
  the state is right and the code is right; **the sentence is rendered by no screen.** It is
  an OpenAPI 503 description. §5, Finding 2, with a red manifest proving it.
* *"`recorded.py:95` turns a miss into `dependency_unavailable` on an `except OSError`"* —
  true, and the line is 95. What it does not say is that the executor then **retries it
  twice on a 2 s + 8 s ladder**, which is where two thirds of the person's wait goes.
  Finding 3.
* *"A cold clean deploy costs ≈ 5.5 GB"* — accurate, and the reason none was run. The web
  image alone cost **2.8 GB peak, 1.0 GB net after `docker builder prune -af`**.
* `OD-03`, the `env_file`/`environment` override, the `-v`/`D-37` and host-gateway traps,
  the fixture paths and `W24-CERT2`'s `cost_micros 37225` were all checked and are correct
  as stated. No stub was needed this session, so neither trap was engaged.

## 8. For the register

| | |
|---|---|
| **`auditmanager-w19a` serves a web tier without `137689a` (`W27-WEB`)** | `cd <tree at dev> && ./infra/deploy/verify-deployed.sh --env-file infra/deploy/env/alpha.env` → exit 6, six files. Closes on a redeploy of 31500. |
| **The `failed` run screen renders a bare error code and no sentence** | `node tests/e2e/pc01/journey/journey.mjs --origin <origin> --phase write --manifest tests/e2e/pc01/journey/fixtures/w28-live/w28-recorded-redden.manifest.json` → exit 1 while it stays true. |
| **A missing recording costs 10.0 s of retry ladder** | `src/auditmanager/runs/retry.py` `BACKOFF_SECONDS = (2.0, 8.0)`; measured 16.08 s to terminal, three of three runs, `text_analysis` 10.0 s. |

## 9. The gate

`make gate FOUNDATION_PYTHON=/usr/bin/python3.12`, on lane **`gate-w28a`** (POSTGRES_PORT
56020, S3 59620/59621, `audit_w28a`, bucket `auditmanager-gate-w28a`), exit code read from
`$?` after a redirect and never through a pipe. **15:07:16 → 15:12:50 +05, 5 min 34 s.**

```
1970 passed, 5 skipped, 1 warning, 169 subtests passed in 278.13s
35 passed in 29.24s
Test Files  49 passed (49)     Tests  715 passed (715)
GATE OK: battery, foundation, frontend and whitespace all pass
GATE_EXIT=0
```

**The stated base, to the test: 1970 / 5 / 169, foundation 35, frontend 715 in 49 files.**
Nothing moved, which is the expected result and also a check — the four files this session
added sit under `tests/e2e/pc01/journey/fixtures/w28-live/` and in `look.mjs`, and the
conformance guard reads `manifest.json` alone, so a gate that had moved would have meant one
of them was being collected.

Provisioning, in that order and not inside a backgrounded subshell:
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` (exit 0), then
`npm --prefix web ci` (exit 0, 184 packages, 4 s), then
**`.venv/bin/python -c "import boto3"` → `boto3 ok 1.43.90` before believing either**.

## 10. Teardown and housekeeping

* Every process and container this session created was stopped by **ID**, never by name.
* `auditmanager-w28live` and lane `gate-w28a` were both removed, with their volumes.
* `auditmanager-w28live-api:latest` was only ever a tag on the existing api image; the web
  image this session built was removed with the instance.
* **31500 was never touched.** No mode change, no restart, no write.
* Disk: **6.3 GB free on arrival, 2.9 GB at the low point, and more than 6.3 GB on exit.**
