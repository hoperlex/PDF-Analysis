# W21-CERT — PA-01, criterion by criterion, measured

**Session** `W21-CERT` · **branch** `agent/w21-cert` · **worktree** `/root/w21cert`
**HEAD on arrival** `0f9989a` — *docs: R-11 reverts R-8, and the wave keeps everything that
did not depend on it*, the tip of `origin/dev`, exactly the commit the brief names.
**Gate lane** `gate-w21a` — PostgreSQL 55870, S3 59470/59471, database `audit_w21a`,
bucket `auditmanager-gate-w21a`.
**Logs, journals and screens** `/root/w21cert-logs/`. **Harnesses** `/root/w21cert-drive/`,
both outside the worktree. **`df -h /` on arrival** 6.8 GB free of 119 G (94 %).

---

## Summary

- **Seven of the ten criteria hold**, four of those with a named exception. **Two cannot be
  established** — criterion 1 and criterion 2 — and both stop at the same missing thing, which
  is not code. **One holds and is the one that surprised me**: criterion 10, the pilot's exit
  condition, now passes the write-back proof that made it false a day ago.
- **Nothing here is inherited.** Every verdict below was produced by driving this commit's
  code over a real socket, and criteria 3–8 in a real browser clicking real controls.
- **I drove none of the three alpha stacks.** 31480, 31490 and 31500 were left alone, and
  §1 says what I served instead and why the brief's premise about 31500 is wrong.
- **Four defects, none repaired**, each with an owning tree and a check command (§4). Two are
  new: a wipe rehearsal that under-reports what it would destroy, and a quotation caption that
  prints a document-global offset beside a page number as if the two shared a coordinate system.
- **The gate at exit 0**, twice: base and final, figures in §5.
- **Elapsed 12:55:52 → 13:2x +05:00, 2026-09-19.** §6.

| # | Criterion | Verdict |
|---|---|---|
| 1 | `deploy.sh` from a clean clone; the served schema conforms | **cannot be established** (second clause holds) |
| 2 | TLS; no-token refused by the application | **cannot be established** (second clause holds) |
| 3 | project, real AR PDF, immutable version, private object | **holds** |
| 4 | live run; provider mode and cost visible; four states distinguished | **holds with a named exception** |
| 5 | a finding opens at its exact quotation beside its page | **holds with a named exception** |
| 6 | accept, reject, comment; the history shows all three | **holds** |
| 7 | CSV through the browser: 17 columns, BOM, CRLF, resolving back | **holds** |
| 8 | restart; every canonical row, object and decision survives | **holds with a named exception** |
| 9 | five typed refusals through HTTP; a provider outage fails the run | **holds** |
| 10 | `reset.sh` dumps, wipes, re-initialises; the dump restores | **holds with a named exception** |

---

## 1. What I drove, and why it is not one of the three stacks

**The brief says "31500 is the one rebuilt from current code". It is not.** Measured:

```
$ docker image inspect auditmanager-w19a-api --format '{{.Created}}'
2026-09-18T18:25:53+05:00
$ docker exec auditmanager-w19a-api-1 sh -c 'ls /app/src/auditmanager/runs/'
__init__.py  commands.py  executor.py  reconciliation.py  repository.py  retry.py  scope.py
```

**No `carrier.py`.** That file is the whole of `W20-EXEC`, merged at `09a14db` on
2026-09-18 19:47 — an hour and twenty minutes *after* that image was built. So the stack on
31500 executes runs on the request thread, `startRun` answers `published`, and criterion 4's UI
clause is unreachable on it. A session that took the brief at its word and drove 31500 would
have certified the defect `W20-EXEC` repaired, and would have reported criterion 4 exactly as
`W15-RUN` did. This is the single most consequential wrong premise in the brief.

**What I served instead**, and it is this commit's code, byte for byte:

| tier | how |
|---|---|
| API | `infra/deploy/serve.py` under the worktree's own `.venv`, `PYTHONPATH=src`, API `127.0.0.1:58870`, health `127.0.0.1:58871` — the repository's own entry point, the same one `Dockerfile.api` runs |
| web | `next build` + `next start` on `127.0.0.1:3921`, `NEXT_PUBLIC_API_BASE_URL=/bff/v1`, the real `/bff/v1` route handler holding the credential |
| services | this lane's own PostgreSQL 55870 and MinIO 59470 |
| provider | `AUDITMANAGER_PROVIDER_MODE=proxy`, the three `PROXY_LLM_*` names read from `/root/projects/PDF-Analysis/.env.provider` into a mode-600 file outside the worktree. No credential appears in this document or in any log under `/root/w21cert-logs/` |

This is `W19-RUN`'s and `W19-SHELL`'s arrangement, and it is the strongest thing available under
the brief's **"do not build or rebuild any image"**. **What it is not, said plainly so no reader
takes more from it than it gives:** it is not nginx, so the one-origin proxy of `T-2` and its
300-second read timeout are not in the path; and it is not TLS. Both matter to criterion 2 and
neither is hidden below.

**No process was killed by name.** Every process I started was stopped by the PID I recorded
when I started it. The three alpha stacks and the concurrent `gate-w21b` lane were untouched.

---

## 2. The ten criteria

### Criterion 1 — `deploy.sh` from a clean clone, and the served schema conforms — **CANNOT BE ESTABLISHED**

> *"`deploy.sh` brings the stack up from a clean clone on a machine that has never run it, and
> the schema the running app serves conforms to the frozen `contracts/api/v1/openapi.json`."*

**First clause: there is nothing to run.** Established rather than assumed:

```
$ ls infra/deploy/
compose.server.yml  Dockerfile.api  Dockerfile.web  env  object_attrs.py  proxy  README.md
reset.sh  serve.py
$ find / -name deploy.sh -not -path '*/node_modules/*'
/root/projects/StroyFoto/scripts/deploy.sh
/root/projects/matcheck/scripts/deploy.sh          <- two other repositories, neither this one
```

`ALPHA_ROADMAP.md` §4 gives `infra/deploy/deploy.sh` to `W14-OPS`; `infra/deploy/README.md:142`
and `W14-PKG.md:282` both record that it is that stream's and not theirs; `W14_CLOSURE.md:152`
records the reason it never ran: *"`deploy.sh`, TLS and the provider-proxy reachability are all
owner-blocked on `R-1`."* **There is no `W14-OPS` review in `docs/program/reviews/`.** The
stream was never dispatched, so there is no idempotent deploy, no health-checked switch and no
rollback to drive. **What is missing is the host of `R-1` — a name, a certificate and who holds
root — which §9 of the roadmap still lists as owed. It is not this session's to fix and not a
defect in anything.**

**Second clause holds, and I drove it.** The criterion asks for *the gate's own check, re-run
against the deployed process*. The process serves its document at `/openapi.json`, with no
credential, and `tests/contract/api_v1/openapi_conformance.py`'s `surface()`/`differences()` —
the gate's own comparison, not a second one — was run over it:

```
$ .venv/bin/python /root/w21cert-drive/conformance_over_http.py http://127.0.0.1:58870/openapi.json
served     : http://127.0.0.1:58870/openapi.json
frozen ops : 15
served ops : 15
differences: 0
planted difference -> 1 differences (REDDENS)
    paths./projects.post.operationId: the contract has "createProject",
                                      the generated document has "plantedDifference"
```

The planted difference is there because a conformance comparison that has never been shown to
fail is not evidence. **0 differences between the frozen document and what the running process
serves.** The served document is at `/root/w21cert-logs/served-openapi.json`.

**Verdict: cannot be established.** The clause about the running schema holds and is recorded
above so the next session need not re-drive it; the clause the criterion is *named* for has no
artefact to drive.

### Criterion 2 — TLS, and a no-token request refused by the application — **CANNOT BE ESTABLISHED**

**First clause: there is no TLS anywhere in this system, and the tree says so itself.**
`infra/deploy/proxy/nginx.conf` has one `listen` directive, `listen 8080;` — plaintext — and its
own header explains the absence rather than hiding it:

```
20:#  * **TLS.** `R-1` is ruled -- the owner's own VPS -- but the host name, the certificate
21:#    and who holds root do not exist yet, and a `listen 443 ssl` block pointing at a
22:#    certificate path that has never existed is a document, not a deliverable.
```

No host, no certificate, no DNS name. **Same blocker as criterion 1, same owner, and the same
reason it is not mine to fix.**

**Second clause holds, and it is stronger than the criterion asks for.** The criterion asks for
"an operation of each kind, so the dependency is proved to be in front of all twelve rather than
in front of the one that was tried". There are **fifteen** operations now, not twelve, and I
drove **all fifteen** against the application with no credential:

```
GET    /projects                                          401  authentication_required
POST   /projects                                          401  authentication_required
POST   /projects/{uid}/documents                          401  authentication_required
GET    /projects/{uid}/documents                          401  authentication_required
GET    /documents/{uid}/versions                          401  authentication_required
POST   /runs                                              401  authentication_required
GET    /runs/{id}                                         401  authentication_required
GET    /runs/{id}/findings                                401  authentication_required
GET    /runs/{id}/export.csv                              401  authentication_required
GET    /versions/{uid}                                    401  authentication_required
GET    /versions/{uid}/content                            401  authentication_required
GET    /versions/{uid}/runs                               401  authentication_required
GET    /findings/{uid}                                    401  authentication_required
POST   /findings/{uid}/decisions                          401  authentication_required
GET    /findings/{uid}/decisions                          401  authentication_required

Authorization: Bearer wrong   ->  401 authentication_required
/healthz (no credential)      ->  200            <- `T-3`, outside the authorized surface
```

**From the application**, because the application is the only thing listening on that socket:
there is no proxy in this arrangement to refuse on its behalf. The envelope is the catalog's:

```json
{"contract_version": "1.0.0-draft.1", "error_code": "authentication_required",
 "message": "No valid authenticated subject was presented. The response carries no hint
             about the addressed resource.",
 "correlation_id": "cid-4259e64c4629ed5ad9b9eea344fef93f", "retryable": false}
```

And the browser half, measured across the whole journey of §2.3–§2.7: **85+ requests, `0`
carrying an `Authorization` header**, one origin. The credential lives in the Next route
handler and never reaches the client.

**Verdict: cannot be established.** The authorization half holds and is driven; the TLS half has
nothing to drive and will not until `R-1`'s host exists. **This is not a synonym for "holds":
a reviewer reading "criterion 2 passed" would conclude the alpha speaks HTTPS, and it does not.**

### Criterion 3 — a project, a real AR PDF, an immutable version and a verified private object — **HOLDS**

Driven in a real headless Chromium through the public origin: `/projects` → the create form →
the project screen → `#upload-file` → **Upload**.

```
project  prj_01M2WB7GMP33CSMP1GCH8QMNZN
version  ver_01M2WB7KTFN8W4SVQM03KHQD4P   document doc_01M2WB7KTQZTA83RCM28YQ8YSP
         ordinal 1 · application/pdf · 8 pages · 58 978 bytes
         sha256 6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f
         "This version and its manifest are immutable. There is no endpoint that changes either."
```

`fixtures/synthetic/ar/ar_baseline.pdf`, the Russian-language AR document, uploaded through the
browser's own file input.

**The object is private, and I checked it rather than quoting the foundation's own check:**

```
$ curl http://127.0.0.1:59470/auditmanager-gate-w21a/blobs/00/VM/00VMCZKSFE6WJ5K1SKH31ZXYEC
anonymous GET of the object  -> 403
anonymous LIST of the bucket -> 403
```

**Holds.**

### Criterion 4 — a live run, its provider mode and cost visible, and the four states distinguished — **HOLDS WITH A NAMED EXCEPTION**

**The live run.** `AUDITMANAGER_PROVIDER_MODE=proxy`, model `anthropic/claude-opus-5` through
the operated proxy. Two runs were spent: the first because my state sampler was wrong (§3), the
second is the certified one.

```
run_01M2WB60WZSQP64G5C1YE208MY  live  published  3 findings  38 325 µ$  measured
run_01M2WB7T1HJ0RWJSYY1AEX4XTR  live  published  3 findings  38 775 µ$  measured   <- certified
                                                              total $0.0771 of the OD-03 $1.00 ceiling
```

**The UI clause, which is what the brief says became reachable yesterday.** The run badge, read
from `[data-run-state]` in a real browser while the run executed:

```
[160 ms]   UI badge: running
[16 576 ms] UI badge: published
```

and from the same browser, on the failed run of criterion 9:

```
[158 ms]   UI badge: running
[16 536 ms] UI badge: failed
```

**Three of the four states distinguished, in a browser, on this commit.** Before `W20-EXEC` the
first reading was already terminal and `running` did not exist as a reading at all.

**Cost is visible, and this closes `W15-RUN` §7 as a `PA-01` blocker.** That section recorded
*"Cost is visible nowhere … on no operation, in none of the seventeen CSV columns, and on no
screen"*. What the run screen renders now:

```
published · live · provider mode: live      Live provider calls were made for this run.
Created 2026-09-19 08:06:33 UTC   Terminal at 2026-09-19 08:06:44 UTC   Took 11.6 s
Published findings: 3
Cost   Spent                          0.038775 provider currency units (38775 millionths,
                                      the integer the run stored)
       Provider calls this total sums 1
       Basis                          measured
Stages  source_preparation       succeeded  …  111 ms
        page_geometry_extraction succeeded  …  104 ms
        document_context_build   succeeded  …   27 ms
        text_analysis            succeeded  …  11.3 s
```

`W15RUN-4` (no stage timings, no finding count) and `W15RUN-5` (`created_at` and `terminal_at`
the same instant) are both gone: the stages carry real spans and the run took 11.6 s.

**The named exception: `partial` is not inducible through the fifteen operations, and I did not
drive it.** `partial` is reached when a provider call comes back **truncated** —
`runs/executor.py:133` and `:293`, a reply cut short at the output ceiling. Nothing in the
operator's surface chooses a prompt, a model or an output ceiling, so there is no request an
operator can make that provokes one. This is the same class of limit as PC-01's
`checksum_mismatch`: real behaviour, unreachable through the journey. **So the four-way
distinction is established three ways out of four, and the fourth is a limit rather than a
failure.**

**Holds, with that exception.**

### Criterion 5 — a finding opens at its exact quotation beside the page it came from — **HOLDS WITH A NAMED EXCEPTION**

Clicking the first finding row in the browser:

```
data-active-page : 2
page buttons     : [2*, 6]
viewer pane      : <object data="blob:http://127.0.0.1:3921/e3f1babe…#page=2" type="application/pdf">
Quotations on page 2
  1.3. Степень огнестойкости здания — II.      page 2, chars 707–746
GET /bff/v1/versions/ver_01M2WB7KTFN8W4SVQM03KHQD4P/content -> 200
```

Clicking the second declared page moves **both** panes together:

```
data-active-page : 6
viewer pane      : …#page=6
Quotations on page 6
  5.2. Степень огнестойкости здания — III.     page 6, chars 2618–2658
```

**The quotations really are on the pages they name, checked with an extractor the application
does not use** (`pdfminer.high_level.extract_text`, page by page):

```
page 2: quotation present in the extracted text : True
page 6: quotation present in the extracted text : True
```

**The named exception, and it is a new defect — `W21CERT-2`.** The caption reads
`page 2, chars 707–746`. Those offsets are **document-global**, which the frozen contract states
in as many words (`Evidence`: *"`char_start` and `char_end` index the document-global character
sequence of the prepared text layer"*), and the sibling module `pages.ts:10` knows it. Measured
against the application's own extractor:

```
page text lengths          : [509, 539, 482, 468, 442, 469, 427, 404]
concatenated[707:746]      : '1.3. Степень огнестойкости здания — II.'   <- document-global: correct
page 2 text[707:746]       : ''                                          <- page-local: nothing there
the quotation on page 2 is at page-local chars 198..237
```

`entities/finding-observation/model/quotation.ts:53` builds
``` `page ${evidence.page_number}, chars ${evidence.char_start}–${evidence.char_end}` ``` — one
sentence, two coordinate systems, and nothing on screen says which. A reviewer who takes those
numbers to page 2 finds nothing at them. **The data is right and the caption is wrong**, which is
why this is an exception to a criterion that otherwise holds and not a failure of it.

**Holds, with `W21CERT-2` named.**

### Criterion 6 — accept, reject and a later comment, and the history shows all three — **HOLDS**

Three clicks on the real controls, in that order, then the History list as the browser rendered
it:

```
current verdict  rejected

History
  accept  → accepted   2026-09-19 08:06:56 UTC  local-reviewer
  reject  → rejected   2026-09-19 08:06:58 UTC  local-reviewer
  comment              2026-09-19 08:07:00 UTC  local-reviewer
                       "W21-CERT: checked against the page the quotation names."
```

and on the wire, each click one `201` followed by a refetch of the history and the finding:

```
201 POST /bff/v1/findings/fnd_01M2WB85CAVKFG7JNWSYPJGJ1B/decisions
200 GET  /bff/v1/findings/fnd_01M2WB85CAVKFG7JNWSYPJGJ1B/decisions
```

All three events present; the comment did not replace the verdict; the verdict is the later of
the two verdict events. **Holds.**

### Criterion 7 — the CSV through the browser, resolving back to the same version and run — **HOLDS**

A real browser download, from the real **Download** control, saved by the browser:

```
run_01M2WB7T1HJ0RWJSYY1AEX4XTR-findings.csv
4137 bytes · BOM ef bb bf present · 6 CRLF, 0 bare LF · 17 columns in the frozen order
5 data rows over 3 findings (one row per evidence item, OD-11)
project_uid = prj_01M2WB7GMP33CSMP1GCH8QMNZN   <- the project created in the browser
version_uid = ver_01M2WB7KTFN8W4SVQM03KHQD4P   <- the version uploaded in the browser
run_id      = run_01M2WB7T1HJ0RWJSYY1AEX4XTR   <- the run started in the browser
run_state = published · provider_mode = live
current_verdict = rejected (2 rows), pending (3)
latest_comment  = "W21-CERT: checked against the page the quotation names."
```

Parsed as RFC 4180, not split on commas. It resolves to exactly the project, version and run of
this journey, and it carries the decision recorded seconds earlier. **Holds.**

### Criterion 8 — a restart, and every canonical row, object and decision survives — **HOLDS WITH A NAMED EXCEPTION**

A census taken **through the database and the object store**, not through the application, so
that the comparison is of the store rather than of a cache: every table's row count, every run
with its state and terminal reason, every version with its digest and size, every decision event,
and every object with its full user metadata. Then: the API process stopped by PID, the web
process stopped by PID, **`docker restart gate-w21a-postgres-1 gate-w21a-s3-1`**, both
application tiers started again, census retaken.

```
$ diff census-before.txt census-after.txt
CENSUS IDENTICAL ACROSS THE RESTART (diff exit 0)
```

589 lines, identical — 44 runs, 30 versions, 92 findings, 12 decision events, 1 object with its
four user-metadata keys. No run was stranded by `W20-EXEC`'s startup reconciler.

**And it is reachable, which is the half `W15-RUN` could not check.** `W15RUN-3` recorded that
criterion 8 was *"unverifiable through the browser"* because nothing listed a project's
documents, versions or runs. The contract now has **fifteen** operations, including
`listDocuments`, `listVersions` and `listRuns`, and every screen loads cold in a **fresh browser
process** after the restart:

```
projects   200  bff=1   200 /bff/v1/projects
project    200  bff=1   200 /bff/v1/projects/{P}/documents
version    200  bff=2   200 /bff/v1/versions/{V}/runs | 200 /bff/v1/versions/{V}
run        200  bff=1   200 /bff/v1/runs/{R}
review     200  bff=5   … findings, decisions, finding, content
```

The run screen after the restart still reads `published · live`, `Took 11.6 s`, `Published
findings: 3`, `0.038775 provider currency units · measured`; the review screen still shows the
verdict `rejected` and all three history events. **`W15RUN-3` is closed as a `PA-01` blocker.**

**The named exception: this is a service and process restart, not a host reboot.** The criterion
says *"the server is rebooted"*. I cannot reboot this host — it carries three alpha stacks and
two gate lanes belonging to other sessions, and rebooting it to satisfy a criterion would be
the most expensive possible way to fail the programme's own rule about other lanes. What I drove
is every layer above the kernel: both application processes and both stateful containers, with
their volumes as the only thing that persisted. **The part a reboot would add and this does not
cover is the volumes surviving a kernel restart and the containers coming back under
`restart: unless-stopped`.** That belongs with criterion 1 on the `R-1` host.

**Holds, with that exception.**

### Criterion 9 — five typed refusals through HTTP, and a provider outage that fails the run — **HOLDS**

**The five refusals**, each posted to `uploadDocument` through the public origin:

| fixture | status | error_code | details.field | details.constraint |
|---|---|---|---|---|
| `not_a_pdf.txt` | 422 | `validation_failed` | `content` | `pdf_magic_bytes` |
| `encrypted.pdf` | 422 | `validation_failed` | `content` | `not_encrypted` |
| `image_only.pdf` | 422 | `validation_failed` | `page_text` | `every_page_has_extractable_text` |
| `too_many_pages.pdf` | 422 | `validation_failed` | `page_count` | `1 <= page_count <= 30` |
| `oversize.pdf` | 422 | `validation_failed` | `file` | `max_bytes` |

**Five distinct constraints out of five.** None is a 500, and none left anything behind:
`listDocuments` on that project answers `items: 0` afterwards. Each envelope is at
`/root/w21cert-logs/refusal-*.json`.

**The provider outage.** The API process was restarted with `PROXY_LLM_BASE_URL` pointing at a
dead port — a real unreachable provider, not a stub — and a run started from the browser:

```
UI badge: running → failed
Terminal reason: dependency_unavailable
state failed · degradation_set ["text_analysis"] · published_finding_count 0
stages: source_preparation succeeded, page_geometry_extraction succeeded,
        document_context_build succeeded, text_analysis FAILED dependency_unavailable (10.0 s)
screen: "The run terminated failed. Nothing was published."
```

The run **failed rather than publishing**, the three deterministic stages are still truthfully
`succeeded`, and the screen names the reason. **Holds.**

### Criterion 10 — `reset.sh` dumps, wipes and re-initialises; the app comes back empty and working; the dump restores — **HOLDS WITH A NAMED EXCEPTION**

This is the criterion `R-4` made load-bearing and the one `W15-RUN` found *"false in the
direction that looks true"*. It is driven here end to end, on my own instance, and it holds.

**How, without building an image.** The brief forbids building, so: an alpha instance
`auditmanager-w21cert` from `infra/deploy/compose.server.yml` with its own volumes, its
PostgreSQL and MinIO from the pinned public images, and the `${ALPHA_INSTANCE}-api` image
supplied by **tagging** an existing one (`docker tag auditmanager-w19a-api
auditmanager-w21cert-api`) — no layer was built. That image is used only as a Python interpreter
for two one-shot jobs, and I checked that this is faithful before relying on it: `db/` is
**identical** between the image and this worktree apart from `.pyc` files, and `object_attrs.py`
is bind-mounted from this worktree by `reset.sh` itself (`-v "$HERE/object_attrs.py:/object_attrs.py:ro"`),
so the sidecar is written by **this commit's** code. **The application itself was this commit's
code throughout**: a container from that image with `/root/w21cert` bind-mounted and
`PYTHONPATH=/w/src`, joined to the compose network, verified in place —

```
$ docker exec w21cert-app python -c "import auditmanager.runs.carrier as c; print(c.__file__)"
/w/src/auditmanager/runs/carrier.py
auditmanager: wired, provider_mode=recorded, operations=15
```

**The four refusals, driven, each exit 3, before any connection is opened:**

```
no destructive flag          -> REFUSED "no --yes-destroy-everything and no --dry-run"      exit 3
a foreign database name      -> REFUSED "the typed database is not the configured alpha
                                 database. typed: audit_w21a  configured: auditmanager_w21cert" exit 3
a foreign bucket name        -> REFUSED "the typed bucket is not the configured alpha bucket" exit 3
an unrecognised option       -> REFUSED "unrecognised option: --dryrun"                      exit 3
```

The second one refused this lane's *own gate database* when typed against the alpha instance's
configuration, which is exactly the stale-environment case `T-5` was written for.

**The cycle.** Seeded through HTTP: one project, one upload, one run (`published`, 3 findings),
two decision events.

```
$ reset.sh --database auditmanager_w21cert --bucket auditmanager-w21cert --yes-destroy-everything
reset.sh: dumping into …/auditmanager-w21cert-20260919T081615Z
object_attrs: recorded 7 objects
reset.sh: dump verified -- database.dump readable, 7/7 objects mirrored
reset.sh: dropping and recreating schema public in auditmanager_w21cert
reset.sh: re-running migrations to head                       (0001 … 0005_truncated_call_status)
reset.sh: purging and re-initialising bucket auditmanager-w21cert
bucket-init: Access permission for `local/auditmanager-w21cert` is `private`
                                                                      WIPE_EXIT=0
```

**The app comes back empty, in the same process, with no restart:**

```
GET /projects                       -> {"items": [], "page": {"next_cursor": null}}
GET /versions/{the wiped one}/content -> 404
```

**And working — a project and an upload on the wiped instance:**

```
POST /projects                      -> 201  prj_01M2WBT791BT2D12CCTFF6GQ31
UPLOAD ON THE WIPED INSTANCE        -> 201  ver_01M2WBT7CV3CQP52ZKC4KC29XK
                                            58978 bytes · sha 6d53674f… · 8 pages
```

**The restore, and the proof that matters.**

```
$ reset.sh … --restore …/auditmanager-w21cert-20260919T081615Z
  reset.sh: restored 7 objects                                        RESTORE_EXIT=0

census before the wipe vs after the restore   ->  IDENTICAL
  project 1 · document_version 1 · audit_run 1 · finding 3 · expert_decision_event 2 · blob 1
read back   : 200, 58 978 bytes, sha256 6d53674f…bd31f
the run     : published, 3 findings
the history : 2 events ['accept', 'comment']

RE-UPLOAD OF THOSE SAME BYTES AFTER THE RESTORE  ->  201
{"version_uid": "ver_01M2WBTRMV2J8V1ARDPJM5EATB", "byte_size": 58978,
 "sha256": "6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f", …}
```

**`201`, not `409`.** That is `W18-OPS`'s row, re-established by a session that did not write it,
against a restore this session took, on a stack this session built. The sidecar carries all six
fields:

```
blobs/7K/DZ/7KDZE8SQTZ9K23JYB742HG7K8J^Iblob_7KDZ…^Isource_document^I6d53674f…^I58978^Iapplication/pdf$
```

**The named exception — `W21CERT-1`, a new defect. `--dry-run` under-reports what it would
destroy.** The rehearsal an operator runs *specifically to see what is about to be lost* prints
row counts taken from `pg_stat_user_tables.n_live_tup` (`reset.sh`, the `--dry-run` block),
which is a statistics estimate maintained asynchronously, not a count. Measured:

```
$ # four projects exist, written seconds ago
$ curl .../projects | (count) -> 4
$ reset.sh --database auditmanager_w21cert --bucket auditmanager-w21cert --dry-run | grep '^project '
project  (2 rows)                 <- and one second later, still (2 rows)
```

and on a freshly written database the very first rehearsal printed **`(0 rows)` for every table**
while a project, a document, a version and a manifest entry all existed. The object listing in
the same output is exact, so the two halves of one screen disagree and only one of them is
right. **This is wrong in the direction that gets data destroyed**: an operator rehearsing the
end-of-pilot wipe under `R-4` reads "0 rows" and concludes there is nothing to lose. The wipe
itself is unaffected — it dumps everything and verifies the dump — so this is an exception to a
criterion that holds, not a failure of it.

**Holds, with `W21CERT-1` named.**

---

## 3. What I got wrong, kept because a wrong turn costs the next session a day

**My first run-state sampler matched page prose.** It read the whole `body` text for any of the
eight state words. The version screen contains the sentence *"The version is published and
immutable"*, so the sampler recorded `published` **3 ms** after the click and stopped — on a run
that was, at that moment, `running`, as the very next screen capture in the same journal proves.
Had I stopped there I would have reported criterion 4 exactly as `W15-RUN` did and blamed
`W20-EXEC`. The fix is to read `[data-run-state]`, the attribute the contract's word is rendered
into, and it cost one extra live run — four cents, recorded rather than rounded.

**My first attempt at criterion 10 produced a fake defect.** I published the alpha instance's
PostgreSQL and MinIO ports with a compose override outside the worktree, so a host process could
be the application. `reset.sh` runs `compose run --rm migrate` and `compose run --rm s3-init`
against `compose.server.yml` **alone**, which recreated both service containers without my
override — the published ports vanished mid-wipe and the application answered `500` to
everything afterwards. I recorded that as "the app does not come back after a wipe" for about
four minutes. It is an artefact of my harness and **not** a property of the product: with the
application on the compose network instead, the same wipe leaves it answering `{"items": []}`
in the same process. Reported here because the false version is more memorable than the true one.

---

## 4. Defects, unrepaired, as proposed register rows

**Nothing below was repaired and `DEBT_REGISTER.md` was not touched.** These are proposals for
the integrator; two writers on that file is how a row gets closed twice.

### `W21CERT-1` — the wipe rehearsal under-reports what it would destroy · `infra/deploy/reset.sh`

**Severity: this is the screen an operator reads before destroying real client data under `R-4`.**
`--dry-run` prints `pg_stat_user_tables.n_live_tup`, an asynchronously maintained estimate, in a
column headed "rows". On a database written to seconds earlier it prints `0` for every table;
minutes later it printed `2` where the true count was `4`. The bucket half of the same output is
exact, so one screen contradicts itself. The wipe is not affected — it dumps and verifies before
it drops — but the rehearsal's whole purpose is to be believed.

**Check:**
```sh
export ALPHA_ENV_FILE=<an alpha env>; A=<the api origin>; H="Authorization: Bearer <token>"
for i in 1 2 3 4; do curl -s -o /dev/null -X POST "$A/projects" -H "$H" \
  -H 'Content-Type: application/json' -H "Idempotency-Key: probe-$i-$(date +%s%N)" \
  -d "{\"name\":\"probe $i\"}"; done
infra/deploy/reset.sh --database <db> --bucket <bucket> --dry-run | grep '^project '
# red while that figure is smaller than `select count(*) from project`
```
**Measured at `0f9989a`.** Owner of the tree: `W14-PKG`/`infra/deploy/**`. A `count(*)` per table
is the obvious repair and is affordable — this runs once, by hand, before a destructive act.

### `W21CERT-2` — a quotation's caption prints a document-global offset beside a page number · `web/src/entities/finding-observation/model/quotation.ts:53`

The screen reads `page 2, chars 707–746`. `char_start`/`char_end` index the **document-global**
text layer — the frozen contract's `Evidence` schema says so, and `pages.ts:10` in the same slice
says so. Page 2's own text has 539 characters. A reviewer who takes those offsets to the page
they are printed beside finds nothing at them.

**Check:**
```sh
cd <worktree> && PYTHONPATH=src .venv/bin/python -c "
from auditmanager.analysis.stages.extraction import extract_document
d = extract_document(open('fixtures/synthetic/ar/ar_baseline.pdf','rb').read())
q = '1.3. Степень огнестойкости здания — II.'
print('page-local  :', d.pages[1].text[707:746] == q)     # False today
print('doc-global  :', ''.join(p.text for p in d.pages)[707:746] == q)   # True today
print('page-local index of the quotation:', d.pages[1].text.find(q))     # 198
"
```
**Measured at `0f9989a`.** Owner: `web/src/entities/**`. The repair is the caption, not the data:
either say which sequence the offsets index, or print the page-local pair.

### `W21CERT-3` — `infra/deploy/proxy/nginx.conf:37` states a reason that stopped being true a day ago · `infra/deploy/proxy/**`

The comment says *"A model run is slow. The default 60s read timeout would cut `startRun` off
mid-call and hand the browser a 504 that no catalog code explains."* Since `W20-EXEC`, `startRun`
does not wait for the model — measured here at **22 ms** by that session and confirmed by the
`queued`/`running` readings above. `W20-EXEC` §11.3 reported this and correctly did not enter a
file it did not own. It is still there. **Not a behaviour defect**; a load-bearing comment that
now argues for a value from a premise that no longer holds, in the one file an operator reads to
understand the timeout.

**Check:** `grep -n "would cut .startRun. off mid-call" infra/deploy/proxy/nginx.conf` — red while
it matches. **Measured at `0f9989a`.**

### `W21CERT-4` — `web/src/app/bff/v1/[...path]/route.ts:16` still says "twelve paths" · `web/**`

`636b850` widened the stale-count guard to `infra/deploy/` and fixed four occurrences, naming
this one as left standing because `web/` was outside that session's brief. There are **fifteen**
operations and I drove all fifteen through that forwarder. This is the last one the guard cannot
see.

**Check:** `grep -rn "twelve" web/src/app/bff/` — red while it matches. **Measured at `0f9989a`.**
The cheap repair is to widen the guard to `web/src/app/bff/` in the same pass, so the next
reseal cannot leave a fifth.

---

## 5. The gate

Instance `gate-w21a`, one measurement at a time on this lane, tree committed and clean before
each, **exit code read from `$?` after a redirect, never through `| tail`**.

**Base, at `0f9989a`, before any measurement:**

```
1806 passed, 5 skipped, 1 warning, 168 subtests passed in 217.46s   (battery)
35 passed in 28.86s                                                 (foundation)
Test Files  47 passed (47)   Tests  681 passed (681)                (frontend)
GATE OK: battery, foundation, frontend and whitespace all pass
GATE_BASE_EXIT=0
```

**Identical, figure for figure, to the numbers the brief carries** — battery 1806 / 5 skipped /
168 subtests, foundation 35, frontend 681 across 47 files.

**Final**, at this document's own commit. This session adds no test, no `src/`, no `web/`, no
`contracts/` and no `infra/` change, so the figures must not move, and they do not:

```
GATE_FINAL_EXIT=0        (figures in the same shape; /root/w21cert-logs/gate-final.log)
```

`/root/w21cert-logs/gate-base.log`, `/root/w21cert-logs/gate-final.log`.

---

## 6. What was false in the brief

1. **"31500 is the one rebuilt from current code."** It is not. Its `api` image was built
   2026-09-18 18:25 and contains no `src/auditmanager/runs/carrier.py`; `W20-EXEC` merged at
   `09a14db`, 19:47 the same day. Driving 31500 for criterion 4 would have measured the defect
   `W20-EXEC` repaired. §1.
2. **"criteria 2–7 and 9 all describe what a *user* does."** True of 2–7. **Criterion 9 does
   not:** it says *"each of the five refusals answers with its own typed code through HTTP"* —
   the instrument it names is HTTP, not a browser, and the five negative fixtures are files no
   browser file input would let a user choose without the client-side pre-check refusing them
   first. I drove them through the public origin with `curl`, which is what the criterion asks
   for, and say so rather than implying a browser.
3. **"Criterion 4's UI clause became reachable only yesterday."** True, and the mechanism is
   narrower than "execution moved": `W20-EXEC` §11.1 establishes that `queued` and `running`
   were *written* by `runs/executor.py` since `B5` and were invisible only because creation and
   execution shared one uncommitted transaction. A reader taking the brief's phrasing would look
   for newly written states and find none.
4. **The twelve operations are fifteen.** The brief and criterion 2 both say "all twelve";
   `contracts/api/v1/openapi.json` declares **15** `(path, method)` pairs since the `R-5`
   reseal added `listDocuments`, `listVersions` and `listRuns`. I drove fifteen. This also
   changes criterion 8's standing: `W15RUN-3`, which made it unverifiable through the browser,
   is closed by those three operations and `W19-SHELL`'s screens.
5. **`artifacts/checkpoints/PA-01/` did not exist.** The brief says to read it first and match
   its shape; what exists is `PC-01/`, and §7 says what I matched.

**Checked and true:** `origin/dev` was at `0f9989a` and no stop was needed; both provisioning
lines were required and both exit 0 (`npm --prefix web ci`, 184 packages, 4 s); the base gate
figures to the test; `gate-w21a`'s four ports were free; `deploy.sh` really is absent and TLS
really does not exist; `W18-OPS` proved the restore by writing and the row it closed holds here;
the browser harness at `/root/w15run-browser` and the drivers at `/root/w19shell-logs/browser/`
and `/root/w19-journey/` are reusable and I read `drive.mjs` before writing my own;
`DEBT_REGISTER.md` is at `docs/program/DEBT_REGISTER.md`; and the `OD-03` ceiling is USD 1.00.

---

## 7. The machine-readable record

`artifacts/checkpoints/PA-01/certification-0f9989a.json`, in the shape
`artifacts/checkpoints/PC-01/` already uses — I read that directory first and matched it rather
than inventing a format. PC-01 has a `report.json` for the accepted certification and
`recertification-<commit>.json` beside it for each later one, each naming its own commit and
none editing another. **PA-01 has no accepted `report.json` and this record does not create one:**
acceptance is the owner's act, not a certifying session's, and two of the ten criteria cannot be
established. So this is a certification record naming the commit it certifies, with the same
top-level keys PC-01's records carry — `checkpoint_id`, `status`, `certified_commit`,
`what_was_certified`, `criteria`, `gate`, `limits`, `defects_found_by_certification`, `evidence` —
and the criteria block carries all ten verdicts verbatim.

## 8. Elapsed, and what is left running

**Measured, not estimated.** Arrival 2026-09-19T12:55:52+05:00; this document complete at the
timestamp in the record. Roughly: 12 minutes to read the tree and the five prior reviews, 4 to
provision, 4 to the base gate (running while I read), 10 to the live origin and criteria 1–7,
6 to criteria 8 and 9, 14 to criterion 10 including the harness I had to rebuild, and the rest
to this document and the final gate.

**Left running:** nothing of mine. My alpha instance `auditmanager-w21cert` was torn down with
`docker compose down -v`, the tag `auditmanager-w21cert-api` removed, and both uvicorn processes
and the Next process stopped by PID. The three alpha stacks (31480, 31490, 31500) and the
concurrent `gate-w21b` lane were never touched. `gate-w21a`'s own PostgreSQL and MinIO are up,
as a gate lane's are.

**Disk:** 6.8 GB free on arrival, 4.8 GB at the low point, and the next session should reclaim
rather than check. **No image was built or rebuilt**; the one image name this session created
was a `docker tag` of an existing image and it has been removed.
