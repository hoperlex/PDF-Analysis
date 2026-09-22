# W37-CERT4 — PA-01 re-certified at `b0e5c07`

- **Task:** `W37-CERT4`. Re-certify `PA-01` against the tree at `b0e5c07`.
- **Record:** `artifacts/checkpoints/PA-01/certification-b0e5c07.json`, superseding `certification-ac7c348.json`.
- **Worktree:** `/root/w37cert4`, branch `agent/w37-cert4`, head on arrival `b0e5c07`.
- **Gate lane:** `gate-w37b` — POSTGRES_PORT 56160, S3_API_PORT 59760, S3_CONSOLE_PORT 59761, POSTGRES_DB `audit_w37b`, S3_BUCKET `auditmanager-gate-w37b`.
- **Logs:** `/root/w37-logs/cert4-*`.
- **This session writes two files and no code.** It repairs nothing it finds.

## Status

OPEN — this file was committed before the first measurement, per the dispatch, so that a
session that dies leaves its evidence. Sections below are filled as each verdict is produced.

## 1. The answer

*pending*

## 2. Stacks driven

*pending*

## 3. The ten verdicts

### Criterion 1 — `deploy.sh` from a clean clone + the served schema conforms

> *"`deploy.sh` brings the stack up from a clean clone on a machine that has never run it, and
> the schema the running app serves conforms to the frozen `contracts/api/v1/openapi.json` —
> the same check the gate runs, re-run against the deployed process rather than against a
> build artifact"* — `ALPHA_ROADMAP.md` §5, read from the file.

**Second clause: HOLDS.** The schema the *running process* serves, fetched over HTTP from
`http://127.0.0.1:31500/api/v1/openapi.json` (68402 bytes), compared against
`contracts/api/v1/openapi.json` by the gate's own engine
(`tests/contract/api_v1/openapi_conformance.py`, `surface()` then `differences()`):
**0 differences**, 16 operations on both sides, 13 paths and 48 schemas on both sides.

The two documents are **not** byte-identical and cannot be — `infra/deploy/verify-deployed.sh`
explains at length why the served document is generated and the frozen one is written by hand.
Canonical digests: served `b65177b5…`, frozen `de213e7e…`. Conformance is the declared
normalization, not equality.

**Anti-vacuity, against the served document itself** — three plants, three reds, one green
control:

| plant | differences |
|---|---|
| delete `/auth/token` from the served document | 1 |
| `POST /projects` response `201` → `299` | 2 |
| an extra key on schema `AnalysisProfileId` | 1 |
| *control: unmutated* | **0** |

So the comparison behind this clause can fail, and does, on a semantic change to the served
document. `make mutation-copy` was not needed: the subject here is a JSON document fetched over
HTTP, and mutating the fetched copy is the stronger test — it mutates what the *process served*,
not what the tree contains.

**First clause: not driven as the criterion writes it.** See the verdict below.

**Verdict: `cannot be established, because R-1`.** No machine here has never run this stack.
`deploy.sh` can be driven, and was (below), but the clause says *a machine that has never run
it*, and this host has run it since wave 14. `cannot be established` is not a synonym for
`fails`, and the half that could be measured holds.

### Criterion 2 — TLS, and a request carrying no token refused **by the application**

> *"the browser reaches the app over TLS, and a request carrying no token is refused with
> `authentication_required` **from the application**, not by the proxy — shown for an operation
> of each kind, so the dependency is proved to be in front of all twelve rather than in front of
> the one that was tried"* — `ALPHA_ROADMAP.md` §5.

**First clause — TLS: NOT ESTABLISHED.** Measured inside the running proxy container, not from
the tree: `docker exec auditmanager-w19a-proxy-1` shows `/etc/nginx/conf.d/` holding exactly one
file, `default.conf`, with exactly one listen directive, `listen 8080;`. `docker port` publishes
`8080/tcp -> 127.0.0.1:31500`. There is an **inert** TLS path in the tree —
`infra/deploy/proxy/tls-server.conf` (`listen 8443 ssl`), `compose.tls.yml`, `enable-tls.sh` —
and it is not loaded by the running container. There is no host name and no certificate. `R-1`.

**Second clause — HOLDS, and this is the verdict that moved.** The previous record
(`ac7c348`) recorded this clause as holding *with a named qualification*, `W30CERT3-1`: the
published origin carried a second, credential-free path to all fifteen operations through
`/bff/v1`. **That is repaired at `b0e5c07`, measured rather than inherited.**

All **sixteen** declared operations driven over HTTP through the published origin
`http://127.0.0.1:31500`, on **both** surfaces, in six credential conditions each
(`/root/w37-logs/cert4-criterion2.json`, `/root/w37-logs/cert4-auth.log`):

| condition | result over the 15 guarded operations |
|---|---|
| `/api/v1`, no `Authorization` header | **15/15** `401 authentication_required` |
| `/api/v1`, a forged `am1.` credential with a wrong tag | **15/15** `401 authentication_required` |
| `/api/v1`, a credential that is not even the right shape | **15/15** `401 authentication_required` |
| `/bff/v1`, no session cookie | **15/15** `401 authentication_required` |
| `/bff/v1`, a cookie naming no live session | **15/15** `401 authentication_required` |
| *positive control:* `/api/v1` with a credential minted by the stand | **15/15** reached the operation (200 / 404 / 422, never 401) |

The positive control is what makes the other five rows mean something: the same fifteen requests,
same paths, same bodies, differing only in the credential, are **not** refused. So the 401 is the
seam and not a routing miss.

`issueToken` — the one operation in `UNAUTHENTICATED_OPERATIONS`, and the one operation the
contract publishes with an empty security requirement — answers `200` without a credential on
`/api/v1`, which is the register working. On `/bff/v1` it answers `404 not_found`: the browser
tier refuses to forward the exchange at all, so a minted token cannot be returned to a page.

**Refused by the application, not by the proxy — proved by removing the proxy.** Both readings
below bypass nginx entirely, from inside the containers:

- `docker exec auditmanager-w19a-api-1` → `http://127.0.0.1:8000/projects` → `401`,
  `{"error_code": "authentication_required"}` in a full `ErrorEnvelope`.
- `docker exec auditmanager-w19a-web-1` → `http://127.0.0.1:3000/bff/v1/projects` → `401`,
  `authentication_required`, `correlation_id` `web-…`.

**Verdict: `cannot be established, because R-1`** — unchanged, and for the first clause only.
There is no TLS, no host and no certificate on this host. The second clause is stronger than it
has ever been recorded and is stated above in full.

### Criteria 3–7 — driven in a real Chromium process through the published origin

One journey on the **owner's stand**, `http://127.0.0.1:31500`, in a headless Chromium
(playwright-core 1.56.0, `chromium-1234`). Journals:
`/root/w37-logs/cert4-browser/review-main.json`, `/root/w37-logs/cert4-browser/recon.json`.

The journey now **begins at the sign-in screen**, which is new since `ac7c348`: `/login`,
`#sign-in-login` = `admin`, `#sign-in-password` = `password`, a real `<form method="post">`.
After it the browser holds one cookie:

```
am_session   HttpOnly=true   SameSite=Strict   Secure=false   Path=/   64 chars
             carries the minted am1. token: NO
```

`Secure=false` is a consequence of criterion 2's first clause, not a separate defect: there
is no TLS to set it over.

**Zero `Authorization` headers left the browser** across the whole journey, and the only
origin contacted was `http://127.0.0.1:31500` (plus the `blob:` the PDF viewer makes). The
credential is held in the Node tier.

#### Criterion 3 — a project, a real AR PDF, an immutable version, a verified private object

> *"a project is created and a real AR PDF is uploaded through the browser, producing an
> immutable version and a verified private object"*

Created through the real controls: project `prj_01M34RWTX9GXAG69X21VZQ8TY4`, document
`doc_01M34RWZ28C484W579CMVS2V4G`, version `ver_01M34RWZ29KMC4F60RSS5YH0N3`,
`byte_size` 58978, `sha256`
`6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f`, 8 pages.

**Immutable — three independent readings, none inherited:**

1. The frozen contract declares **only `get`** on every path that addresses a version:
   `/versions/{version_uid}`, `/versions/{version_uid}/content`, `/versions/{version_uid}/runs`,
   `/documents/{document_uid}/versions`. There is no write method to call.
2. Re-uploading the **same bytes** through `POST /projects/{uid}/documents` answered `201`
   with a **new** `document_uid` and a **new** `version_uid` — it created an aggregate, it did
   not replace one.
3. The original version re-read afterwards is unchanged, field for field, including
   `published_at`.

**Verified private object — checked against the bucket itself.** `docker port
auditmanager-w19a-s3-1` publishes **nothing**. Inside the compose network, with the
application's own credentials, the bucket `auditmanager-alpha` holds 49 objects under
content-addressed keys; exactly one is 58978 bytes,
`blobs/7K/DZ/7KDZE8SQTZ9K23JYB742HG7K8J`, and its sha256 is the version's sha256. An
**anonymous** `GET` of that exact key answers `403 Forbidden`; an anonymous bucket listing
answers `403 AccessDenied`. `/root/w37-logs/cert4-object.log`.

**Verdict: `holds`.** Stack: the owner's stand.

#### Criterion 4 — a live run, provider mode and cost visible, four states distinguished

> *"a live `text_analysis` run completes, with its provider mode and cost visible, and the UI
> distinguishes running, published, partial and failed"*

**The live run: `run_01M34RX7PH00Y6J6Y6E8RDJRJZ` on the owner's stand**, started from the
real control (`Запустить прогон`) on the version screen. `state: published`,
`provider_mode: live`, four stages all `succeeded`, `published_finding_count: 3`,
`model_call_count: 1`, `cost_micros: 38350`, `cost_basis: measured`. 12.4 s of
`text_analysis`. `/root/w37-logs/cert4-run.json`.

**Provider mode visible in the UI, read from the attribute and not from prose:** four
`[data-provider-mode="live"]` nodes on the run and review screens, rendering *«живой вызов»*
and *«режим провайдера: живой вызов»*.

**Cost visible:** the run screen prints the spend; the API's `cost_micros` 38350 with
`cost_basis: measured` is the integer behind it.

**Verdict: `holds` for the live-run, provider-mode and cost clauses on the owner's stand.**
The four-state clause is driven on this session's own stack — see below — because `partial`
and `failed` cannot be produced on the owner's stand without changing its provider
configuration, which this session may not do.

#### Criterion 5 — a finding opens at its exact quotation beside the page it came from

> *"a finding opens at its exact quotation beside the page it came from"*

Clicking a finding row on the review screen of the owner's stand:

- selected `fnd_01M34RXKTCW6WNY74RMJTKKT8C`, `data-selected="true"`;
- `.am-evidence` carries `data-active-page="3"`;
- the page navigation offers pages 3 and 7 with `data-active="true"` on **3**;
- the PDF pane's `data-viewer-src` is `blob:http://127.0.0.1:31500/…#page=3` — the viewer is
  pointed at page 3, beside the quotation;
- the quotation's `data-evidence-quote` attribute and its **visible text are byte-identical**:
  `«2.4. Из надземной части здания предусмотрено два эвакуационных выхода.»`

**Checked with an extractor the application does not use.** `pdfminer.high_level.extract_text`,
page by page, over the bytes the API served back (`GET /versions/{uid}/content`, 58978 bytes,
sha256 matching). The quotation occurs on **page 3 and on no other page of the eight**. The
CSV's own `evidence_page` for the same finding is also `3`, and its `evidence_quote` is
byte-identical to the screen's.

**Verdict: `holds`.** Stack: the owner's stand.

**What the second extractor still cannot confirm, restated rather than inherited.** The
anchor line also says *«символы 1282–1352 по всему документу»*. `pdfminer`'s whole-document
text puts the same quotation at offset 1320. A character offset is defined relative to an
extractor's own text stream, and this is not the extractor the application uses, so the
difference is **not evidence of a defect** and is **not evidence the number is right**
either. It is unverifiable from outside, and it is recorded as `W37CERT4-3` below rather
than as a qualification on the verdict, because the criterion asks for the page and the
quotation and both are confirmed.

#### Criterion 6 — an accept, a reject and a later comment; the history shows all three

> *"an accept, a reject and a later comment are recorded, and the history shows all three"*

Three clicks on the real controls of the owner's stand, on finding
`fnd_01M34RXKTCW6WNY74RMJTKKT8C`, each a separate `POST /bff/v1/findings/{uid}/decisions`
answering `201` (seen in the browser's own response log):

| control | verdict badge after |
|---|---|
| *(before)* | `не решено` |
| `button[data-intent="accept"]` → *Принять* | `принято` |
| `button[data-intent="reject"]` → *Отклонить* | `отклонено` |
| `button[data-intent="comment"]` → *Добавить* | `отклонено` *(unchanged — a comment is not a verdict)* |

The history renders **three** `[data-decision-id]` events, in order, none replacing another:

```
dec_01M34S62R2E4KGNYW68V3SPBWH  ПРИЁМ       → принято    14:44:12 UTC  local-reviewer
dec_01M34S65RCM0XV0WFTA2KBSJKA  ОТКЛОНЕНИЕ  → отклонено  14:44:15 UTC  local-reviewer
dec_01M34S6944WVAV73TSF0TYXWCE  КОММЕНТАРИЙ              14:44:18 UTC  local-reviewer
                                "W37-CERT4: a later comment, recorded after the accept and the reject."
```

The comment is the **later** event and the verdict badge did not move for it, which is the
half of the criterion that a history of three rows alone would not prove.

**Verdict: `holds`.** Stack: the owner's stand.

#### Criterion 7 — the CSV through the browser, seventeen columns, BOM, CRLF, resolving back

> *"the CSV downloads through the browser with its seventeen columns, its BOM and its CRLF
> intact, and resolves back to the same version and run"*

A real browser download from the real `button[data-intent="export"]` (*«Скачать
run_…-findings.csv»*) on the review screen, saved by the browser's own download handler to
`/root/w37-logs/cert4-browser/export-main.csv`. 4628 bytes.

| clause | measured |
|---|---|
| seventeen columns | **17** header fields |
| BOM | first three bytes `EF BB BF` |
| CRLF intact | **6** `CRLF`, **0** bare `LF` |
| resolves back to the same run | all **5** data rows carry `run_01M34RX7PH00Y6J6Y6E8RDJRJZ` |
| resolves back to the same version | all **5** data rows carry `ver_01M34RWZ29KMC4F60RSS5YH0N3` |

Column names, in order: `project_uid, document_uid, version_uid, run_id, run_state,
provider_mode, finding_uid, finding_observation_id, category, finding_text,
recommendation_text, evidence_page, evidence_quote, current_verdict, latest_comment,
latest_decision_id, decision_recorded_at`. `/root/w37-logs/cert4-csv.log`.

**Verdict: `holds`.** Stack: the owner's stand.

### This session's own stack, and what it was for

`auditmanager-w37cert4` at `http://127.0.0.1:31570`, built by `deploy.sh` from this
worktree, `ALPHA_INSTANCE=auditmanager-w37cert4`, `ALPHA_HTTP_PORT=31570`,
`POSTGRES_DB=auditmanager_w37cert4`, `S3_BUCKET=auditmanager-w37cert4`. The env file lives
**outside the tree** at `/root/w37-logs/cert4-drive/alpha.env`.

**`verify-deployed.sh` exits 0 on BOTH stacks against this worktree** — 156 `src/`, 10 `db/`,
34 `contracts/`, 7 `fixtures/recorded/`, `docs/program/P02_LOCK.json`,
`infra/deploy/serve.py` and 262 `web/` files **identical**, twice.
`/root/w37-logs/cert4-verify-own.log`, `/root/w37-logs/cert4-verify-stand.log`.

**That is the licence for certifying `b0e5c07` from the owner's stand.** `git diff --name-only
31a8a53..b0e5c07` is **one file**, `docs/program/dispatch/PORT_REGISTRY.md`, and nothing
outside `docs/`. The stand was deployed from `31a8a53`; its images are byte-identical to the
code at `b0e5c07`; `verify-deployed.sh` says so by comparing the bytes inside the running
containers. Measured, not assumed.

**One file was written into the worktree and it is git-ignored.** `infra/deploy/env/provider.env`
is matched by `.gitignore:34` (`infra/deploy/env/*.env`) and is the file `compose.server.yml`
names as `env_file`, which is the only way to point an api container at a different provider.
`git status --short` was empty after every write, and no tracked file under `infra/` was
touched. Proof: `git diff --stat b0e5c07..HEAD` at the foot of this report.

#### Criterion 4's remaining clause — the four states distinguished in the UI

Driven on **this session's own stack**, because `partial` and `failed` cannot be produced on
the owner's stand without changing its provider configuration.

The provider was pointed at a local stub of the proxy's own documented OpenAI-compatible
contract, run as a **container on the compose network** (`w37cert4-stub`) so the real
`ProxyAdapter` really opens a socket to it. Nothing in the application is stubbed.

Five runs, and the badge read from `.am-badge[data-run-state]` on **the run's own screen**:

| run | state | how it was produced |
|---|---|---|
| `run_01M34SPD64EM0YY0JPZQBYX8C2` | `published` | `recorded` mode, no provider call |
| `run_01M34T6DET614KYYZ90NTXYNZA` | `partial` | the stub answers `finish_reason: "length"`; `degradation_set: ["text_analysis"]`, `text_analysis` stage `partial`, 1 finding published |
| `run_01M34T7HJ5AWGSM6K3BFMAYCXK` | `failed` | the provider's port unreachable; `terminal_reason: dependency_unavailable`, 0 findings |
| `run_01M34T1JMDNJRATRHAJDBGFMD3` | `failed` | its api process was replaced mid-flight; `interrupted_reason: executor_process_ended_before_terminal` |
| `run_01M34T980709YBN41J4J9KYJ2C` | `partial` | **the control** — same stack, same version, same stub, the base URL reachable again |

**And `running` was caught live, on the run's own screen, not inferred.** Following
`run_01M34TD3NGG30J1HSNKCNDSJR1` from the moment its control was clicked, the badge read, in
order:

```
queued    «в очереди»     -> running  «выполняется»   -> failed  «отказ»
```

**Five distinct contract values rendered by the badge component: `queued`, `running`,
`published`, `partial`, `failed`.** The Russian label is the visible text; the contract value
stays intact in `data-run-state`.

**The selector matters, and getting it wrong nearly produced a wrong reading.** A first pass
read every `[data-run-state]` on the page and got three states on one run's screen:
`run-progress.tsx` and `export-panel.tsx` render bare `<span data-run-state="published">`
inside *explanatory prose* («опубликован или частично»), and the version screen lists every
prior run's badge. Only `span.am-badge[data-run-state]`, which is what `RunStateBadge` emits,
is the run's own state. Recorded here because the previous certification's sentence —
*"read from the `[data-run-state]` badge, never from page prose"* — describes the right
intention and the wrong selector.

**Verdict on criterion 4: `holds`.** Stacks: the owner's stand for the live run, its provider
mode and its cost; this session's own stack for `running`, `partial` and `failed`.

#### Criterion 8 — a restart, and every canonical row, object and decision survives

> *"the server is rebooted and every canonical row, object and decision survives"*

**What was driven, on this session's own stack, entirely.** The owner's stand was never
stopped, restarted, recreated or reset.

1. A **43-line census taken below the application** — straight from PostgreSQL and from
   MinIO, never through the tier under test: every base table's row count, the migration
   head, every project, version, run, model call, finding and decision by identifier, and
   every object by exact key and size. `/root/w37-logs/cert4-drive/census.sh`.
2. `docker compose down` **without `-v`**: all seven containers **removed**, both named
   volumes kept. The published port answered `000` — the stack was genuinely gone.
3. `deploy.sh` again. **Every one of the seven container ids differs** from before:
   `5400e88a144f → 8ad34b705309` for the api, and six more.
   `/root/w37-logs/cert4-containers-before.txt`, `…-after.txt`.
4. The same census again. **`diff` is empty.**

```
$ diff /root/w37-logs/cert4-census-before.txt /root/w37-logs/cert4-census-after.txt
THE CENSUS DIFFS TO NOTHING
```

17 base tables, migration head `0006_app_user`, 1 project, 1 version
(`6d53674f…`, 58978 bytes, 8 pages), 1 run, 1 model call, 3 findings, 5 evidence rows,
3 decision events (`accept`, `reject`, `comment`) and 7 objects — identical on both sides.

**Reachability afterwards, in a fresh browser process per screen**, each signing in from
scratch: `projects`, `project`, `version`, `run`, `review`, `document` — **6/6 answer `200`**
and carry their canonical identifiers. `/root/w37-logs/cert4-browser/cold-after-restart.json`.

**Named exception — `W37CERT4-1`, and its reason was re-measured, not inherited.**
**This is a container destruction and recreation, not a host reboot.** The reason on record
(`D-51`, raised as `W30CERT3-3`) is *"a certifying session runs on the host it would have to
reboot, and cannot witness its own reboot."* **That still holds at `b0e5c07`**, and it is now
narrower and stronger than when it was written:

- it is structural, not a property of a tidy host: this session is a process on the host, and
  a reboot ends it before it can read anything back;
- and there is a **second** reason that did not exist in wave 30: a peer stream, `W37-D57`,
  was live on this host throughout, together with the owner's stand and two other lanes'
  foundation services. A reboot is a host-wide action on a shared resource, which
  `OPERATING_CONSTRAINTS.md` §4.5 is entirely about. `W30-CERT3`'s replacement reason
  (*"the host carries three alpha stacks"* was false; it carried one) is not the reason
  being used here.

**Verdict: `holds with a named exception` (`W37CERT4-1`).** Unchanged from `ac7c348`, and the
exception's reason re-measured and found still true.

#### Criterion 9 — five typed refusals through HTTP, and a provider outage that fails the run

> *"each of the five refusals answers with its own typed code **through HTTP**, and a provider
> outage fails the run rather than publishing it"*

**Which five.** Read from the roadmap, not inherited: §"Stage 1 — `W13-BASE`" names *"the five
refusals with their distinct `details.constraint` values"*. They are the five upload
constraints, and they are five because the constraints are five.

**Driven with curl through the OWNER'S STAND's nginx origin**, each with a valid credential —
so what refuses is the validation and not the seam:

| fixture | status | `error_code` | `details.field` | `details.constraint` |
|---|---|---|---|---|
| `not_a_pdf.txt` | 422 | `validation_failed` | `content` | `pdf_magic_bytes` |
| `encrypted.pdf` | 422 | `validation_failed` | `content` | `not_encrypted` |
| `image_only.pdf` | 422 | `validation_failed` | `page_text` | `every_page_has_extractable_text` |
| `too_many_pages.pdf` | 422 | `validation_failed` | `page_count` | `1 <= page_count <= 30` |
| `oversize.pdf` | 422 | `validation_failed` | `file` | `max_bytes` |

Five distinct constraints out of five, five distinct `correlation_id`s, every one
`retryable: false`. Afterwards the project they were uploaded to lists **zero** documents:
nothing half-created survived a refusal. `/root/w37-logs/cert4-refusals.log`.

**A provider outage fails the run rather than publishing it — driven on this session's own
stack**, because it needs the provider taken away.

`PROXY_LLM_BASE_URL` was pointed at `http://w37cert4-stub:59991`, a port nothing listens on
inside the compose network. `run_01M34T7HJ5AWGSM6K3BFMAYCXK`:

```
state            failed
terminal_reason  dependency_unavailable
published_finding_count 0
model_call rows  none -- no answer ever came
elapsed          13 s  (ATTEMPT_BUDGET 3, BACKOFF_SECONDS 2.0 + 8.0)
```

**The control that proves the boundary.** Driven minutes later on the **same stack**, same
version, same stub container, differing **only** in whether the port was the one the stub
listens on: `run_01M34T980709YBN41J4J9KYJ2C` → `partial`, 1 finding published. So the
`failed` above is the outage and not the stack.

**What an outage *is* at this commit, established by reading the tree** — `W29-RETRY` moved
this boundary and the previous record re-established it from scratch, so this one did too.
`src/auditmanager/runs/retry.py`: `RETRYABLE_STAGE_ERRORS` is exactly
`{DEPENDENCY_UNAVAILABLE}`, narrower than the frozen catalog's retryable set, and
`RetryPolicy.__post_init__` refuses to construct over any code the catalog does not mark
retryable — so a policy that retries `analysis_failed` is **not expressible** without editing
a frozen contract.

**Verdict: `holds`.** Stacks: the owner's stand for the five refusals; this session's own
stack for the outage and its control.

#### Criterion 10 — `reset.sh` dumps, wipes and re-initialises; the dump restores

> *"`reset.sh` dumps, wipes and re-initialises; the app comes back empty and working; the dump
> restores the wiped state."*

**This session's own stack, entirely.** The owner's stand was never a candidate for this
criterion and was not touched by it.

**The guards first — seven refusals, each `exit 3`, each read from `$?` after a redirect to a
file and never through a pipe** (`/root/w37-logs/cert4-reset-guards.log`):

| what was typed | exit |
|---|---|
| no mode flag at all | 3 |
| `--dry-run` and `--yes-destroy-everything` together | 3 |
| no `--database` / `--bucket` | 3 |
| a database that is not the configured one (`auditmanager_alpha` — **the owner's**) | 3 |
| a bucket that is not the configured one (`auditmanager-alpha` — **the owner's**) | 3 |
| an env file that is not there | 3 |
| an unrecognised option | 3 |

Two of those seven are the guard that would have stopped this session wiping the owner's
stand by typing its names, and they were driven with the owner's actual names.

**The rehearsal.** `--dry-run`, **exit 0**. 17 base tables listed by name with their counts,
**`total: 111 rows in 17 base tables (and 1 view listed above, projecting rows already in that
number)`** — `W26-OPS`'s `D-39` repair, which moved this criterion from an exception to `holds`
at `ac7c348`, is still in place and was re-read rather than assumed. 11 objects listed exactly
by key, size and time. Nothing was touched.

**The cycle.** `--yes-destroy-everything`, **exit 0**.

```
dumping into infra/deploy/dumps/auditmanager-w37cert4-20260922T150754Z
object_attrs: recorded 11 objects
dump verified -- database.dump readable, 11/11 objects mirrored
   ... drop, recreate, migrate to 0006_app_user, purge, re-initialise private ...
bucket-init: Access permission for `local/auditmanager-w37cert4` is `private`
```

The dump directory holds `database.dump` (103434 bytes), `objects/`, `objects.attrs` and
`objects.stat.json`. It is git-ignored (`.gitignore:35`) and was removed afterwards.

**Empty and working — in the SAME api process, proved and not asserted.** The api container's
id was `e8b617bad7fe` before the wipe and `e8b617bad7fe` after it: no restart.

- `POST /auth/token` with `admin`/`password` mints a credential — the seeded account came back
  with the migrations, and the migration logged its own warning about the default password;
- `GET /projects` → **0 projects**;
- a project was created, and `ar_baseline.pdf` uploaded → `201`, a new version,
  58978 bytes, `6d53674f…`. **Empty *and* working.**

**The restore.** `--restore` with the **relative** path — the shape `D-31` broke on — **exit 0**,
`restored 11 objects`.

The census taken after the restore **diffs to nothing** against the census taken before the
wipe:

```
$ diff /root/w37-logs/cert4-census-prewipe.txt /root/w37-logs/cert4-census-restored.txt
THE RESTORED STATE DIFFS TO NOTHING AGAINST THE PRE-WIPE CENSUS
```

and the post-wipe project that existed between the two is gone, which is the other half of
"the dump restores the wiped state".

**The bytes, and the write-back proof.** `GET /versions/{uid}/content` after the restore
returns 58978 bytes whose sha256 is `6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f` —
the version's declared digest. Re-uploading exactly those bytes **after** the restore answers
`201` and not `409`, with a new `version_uid`: the restored instance is writable, not a
read-only replay.

**Verdict: `holds`.** Unchanged from `ac7c348`, re-taken end to end at this tree.

## 3a. Anti-vacuity: can the thing that certifies criterion 2 fail?

Two sweeps, because criterion 2 has two instruments.

**The conformance engine** — three plants into the *served* document, three reds, one green
control. Table in criterion 1 above.

**The authorization seam.** Criterion 2's second clause is the verdict that moved, and it rests
on `src/auditmanager/api/security.py`. `make mutation-copy MUT=/root/w37cert4-mut`, the copy
proved to be the imported tree (`auditmanager.api.security.__file__` resolves under the copy),
`PYTHONDONTWRITEBYTECODE=1` and `__pycache__` cleared between cases (§10.2), baseline green
first. Suites: `tests/integration/api/test_authorization.py`, `tests/integration/auth`,
`tests/integration/composition/test_api_token_channel.py`.

| | mutation | result |
|---|---|---|
| **CTRL** | *unmutated copy* | **77 passed** |
| **M1** | `verify()` accepts every credential | **RED** — the suite refuses to collect: *"this case is only a case if the credential really has expired"* |
| **M2** | `UNAUTHENTICATED_OPERATIONS` also holds `listProjects` | **RED** — 15 failed |
| **M3** | the expiry check removed | **RED** — same collection-time precondition |
| **M4** | `hmac.compare_digest` → `!=` | **GREEN — BLIND** |
| **M5** | an unreadable route is **exempted** instead of guarded | **GREEN — BLIND** |
| **M6** | an empty deployment secret derives a key anyway | **RED** — 3 failed |
| **REV** | reverted | **77 passed** |

**Four of six redden, two are blind, and the answer the brief asks for is: sound on the
substance, blind on two stated properties.** Both blind spots are written up as findings
below. The sweep did not manufacture a red — the baseline and the revert are both 77 green on
the same copy.

## 4. Findings

Eight, none repaired. `DEBT_REGISTER.md` is the integrator's file and a forbidden hotspot for
this task, so each row is written here with the command a later session re-runs.

### `W37CERT4-1` — criterion 8 is a container destruction and recreation, not a host reboot

- **Tree:** none. This is a property of the certifying arrangement.
- **Severity:** the named exception on criterion 8. Nothing to repair.
- **Already registered as `D-51`.** Its reason was **re-measured at `b0e5c07` and still holds**:
  a certifying session is a process on the host it would have to reboot and cannot witness its
  own reboot. A **second** reason now stands beside it that did not exist in wave 30: the peer
  stream `W37-D57` was live on this host throughout, as were the owner's stand and two other
  lanes' services. `OPERATING_CONSTRAINTS.md` §4.5 is exactly about host-wide actions on shared
  resources.
- **Check:** `diff` of the census either side of a `docker compose down` (no `-v`) plus
  `deploy.sh`, as in criterion 8 above.

### `W37CERT4-2` — every screen of the alpha tells the reviewer there are no accounts

- **Tree:** `web/src/_app/app-frame.tsx:70`.
- **Measured:** the footer of **every screen, including `/login`**, reads
  *«Альфа-версия. Один проверяющий, без учётных записей и разделения доступа.»* — "one reviewer,
  no accounts and no access separation". At `b0e5c07` there is a sign-in screen, an `app_user`
  table, a seeded account and a surface that refuses all fifteen guarded operations without a
  credential.
- **Severity:** medium. It is not a stale count: it is a **statement about the security posture**
  rendered to whoever uses the alpha, and it is now the opposite of the truth. It reads as
  reassurance that nothing is protected, next to a sign-in form.
- **Check:** `grep -n "без учётных записей" web/src/_app/app-frame.tsx` — one hit at `b0e5c07`.

### `W37CERT4-3` — the file that holds the credential still documents the behaviour it replaced

- **Tree:** `web/src/app/bff/v1/[...path]/route.ts`, the `## Which credential is presented`
  block, lines 39–45.
- **Measured:** it says *"**no session cookie** — the deployment's own credential, exactly as
  `W15-AUTH` left it. **Nothing about the alpha's behaviour changes for a browser that has not
  signed in.**"* One hundred and sixty lines further down, the same file documents and
  implements the opposite: `noSession()` answers `401` and forwards nothing, and its own comment
  says *"**This replaces forwarding the deployment credential**"*.
- **Severity:** medium, and it is `OPERATING_CONSTRAINTS.md` §4.7's exact shape one level in.
  §4.7 caught the stale instruction in `infra/deploy/README.md` and `DEPLOYMENT_RUNBOOK.md` —
  **both of those are correct at `b0e5c07`, verified** — and left the same claim standing inside
  the module that holds the key. A reviewer reading this file to answer *"can a browser reach the
  API without signing in?"* is told **yes** by its own header.
- **Check:** `sed -n '39,46p' 'web/src/app/bff/v1/[...path]/route.ts'` against
  `sed -n '195,218p'` of the same file.

### `W37CERT4-4` — two collection endpoints answer `200` for a parent that does not exist

- **Tree:** the `listRunFindings` and `listDecisions` operations.
- **Measured** on the owner's stand, with a valid credential and a **well-formed 26-character
  ULID that names nothing** (`/root/w37-logs/cert4-nonexistent-parent.log`):

  | request | answer |
  |---|---|
  | `GET /runs/run_01M34N4H18E6570C3HTMXA0000` | `404 not_found` |
  | `GET /runs/run_01M34N4H18E6570C3HTMXA0000/findings` | **`200`, `items: []`** |
  | `GET /runs/run_01M34N4H18E6570C3HTMXA0000/export.csv` | `404 not_found` |
  | `GET /findings/fnd_01M34N4H18E6570C3HTMXA0000` | `404 not_found` |
  | `GET /findings/fnd_01M34N4H18E6570C3HTMXA0000/decisions` | **`200`, `items: []`** |
  | `GET /versions/ver_…0000/runs` | `404 not_found` |
  | `GET /documents/doc_…0000/versions` | `404 not_found` |
  | `GET /projects/prj_…0000/documents` | `404 not_found` |

- **Severity:** low-to-medium. Seven of the nine agree; two do not. A client cannot tell
  *"this run published no findings"* from *"this run does not exist"*, and the CSV endpoint on
  the same parent disagrees with the findings endpoint about whether that parent is there.
- **Check:** the nine requests above, verbatim.

### `W37CERT4-5` — the seam's fail-closed default for an unreadable route has no guard

- **Tree:** `src/auditmanager/api/security.py`, `_operation_of` and `require_authorization`.
- **Measured:** mutation **M5** — rewriting the guard so that a route the seam cannot identify
  is **exempted** instead of guarded — leaves `tests/integration/api/test_authorization.py`,
  `tests/integration/auth` and `tests/integration/composition/test_api_token_channel.py` at
  **77 passed**. The module's own docstring states the opposite as a property:
  *"A route whose `operationId` the seam cannot read is guarded, not exempted, so a new
  operation is closed by default."*
- **Not currently exploitable, and that is the point.** All **16** routes on the built
  application carry an `operation_id` (measured: `routes total: 16, routes with NO
  operation_id: 0`). So the claim is true today and **nothing would redden on the day it stops
  being true** — which is precisely the day a route is added without one.
- **Severity:** low now, high the first time a route is added carelessly.
- **Check:** `make mutation-copy MUT=<dir>`, then in the copy replace
  `if _operation_of(request) in UNAUTHENTICATED_OPERATIONS:` with
  `if _operation_of(request) is None or _operation_of(request) in UNAUTHENTICATED_OPERATIONS:`
  and run the three suites: still green.

### `W37CERT4-6` — the credential tag's timing-safe comparison is unguarded

- **Tree:** `src/auditmanager/api/security.py`, `TokenSigner._tag` / `verify`.
- **Measured:** mutation **M4** — `hmac.compare_digest(presented_tag, self._tag(signed))` →
  `presented_tag != self._tag(signed)` — leaves the three suites at **77 passed**.
- **Severity:** low. The behaviour is identical; what is lost is the constant-time property the
  module deliberately chose and explains in a comment (*"a short-circuiting one leaks its
  length and its prefix to a caller who can time it"*). It is a property with a stated reason
  and no test.
- **Check:** as `W37CERT4-5`, with that substitution.

### `W37CERT4-7` — the interface's only console error, on every screen of both stacks

- **Tree:** `web/` — there is no favicon asset and no `icon` export.
- **Measured:** every screen load in every browser journey of this session produced exactly one
  console error: `Failed to load resource: the server responded with a status of 404`.
  `curl -o /dev/null -w '%{http_code}' http://127.0.0.1:31500/favicon.ico` → **404**, and
  the same on this session's own stack.
- **Severity:** cosmetic, and recorded only because `R-18` asks for a finished interface and this
  is the single error a reviewer's console shows. It is **not** a `/bff/v1` failure: every one of
  the 11 BFF responses in the certified journey was `200`, `201` or `303`.
- **Check:** the `curl` above.

### `W37CERT4-8` — `ALPHA_ROADMAP.md` still says *twelve operations*, in nine places

- **Tree:** `docs/program/ALPHA_ROADMAP.md`. **A forbidden hotspot for this task**, so it is
  recorded and not repaired.
- **Measured:** `grep -c "twelve operations" docs/program/ALPHA_ROADMAP.md` → **9**. The surface
  is **13 paths / 16 operations / 48 schemas** since the wave-34 reseal added `POST /auth/token`.
- **Why it matters here rather than in a documentation pass:** one of the nine is **inside
  criterion 2 itself** — *"the dependency is proved to be in front of all twelve"*. A criterion
  that names a count the contract no longer declares is a criterion that can be satisfied by
  probing the wrong surface. This session drove all sixteen and said so; a later one reading the
  criterion literally would drive twelve.
- **Check:** `grep -c "twelve operations" docs/program/ALPHA_ROADMAP.md` against
  `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(len(d['paths']), sum(1 for p,v in d['paths'].items() for m in v if m in ('get','post','put','patch','delete')))"`.

### Not a new finding: the character offset

The anchor's *«символы 1282–1352 по всему документу»* is unverifiable from outside, and it is
**already registered as `D-50`** (*"a character offset no second extractor can resolve"*). This
session reproduced the condition — `pdfminer` puts the same quotation at offset 1320 — and
confirms the row rather than opening a second one.

## 5. Spend

**USD 0.038350, one paid provider call**, against a ceiling of 1.00.

| run | stack | provider | cost |
|---|---|---|---|
| `run_01M34RX7PH00Y6J6Y6E8RDJRJZ` | the owner's stand, `proxy` mode | the operated `proxyllm.fvds.ru` | `cost_micros 38350`, `cost_basis measured`, 1 model call |
| everything else | this session's own stack | `recorded` mode, then a **local stub container** on the compose network | **0** |

The certified journey behind criteria 3, 5, 6 and 7, and criterion 4's live half, hang off that
one run. Criterion 4's `partial` and `failed`, criterion 9's outage and its control, criterion
8's restart and criterion 10's whole cycle cost nothing, because the provider was a stub this
session ran, or was absent on purpose.

The brief's figure — *"the last live run cost USD 0.038"* — is confirmed: this one cost
0.038350.

## 6. False premises in the dispatch brief

*pending*

## 7. Gate

*pending — run once, at the end, from a committed-clean tree.*
