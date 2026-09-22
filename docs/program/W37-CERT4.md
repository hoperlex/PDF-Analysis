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

## 4. Findings

*pending*

## 5. Spend

*pending*

## 6. False premises in the dispatch brief

*pending*

## 7. Gate

*pending*
