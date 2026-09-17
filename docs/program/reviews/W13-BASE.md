# W13-BASE — the pre-FastAPI response baseline

Session `W13-BASE`, wave 13 stage 1. Rebased onto `7399d65`; captured against `85aaa24`, which differs from it only in `docs/`. **The branch is `agent/w13-gold` and the worktree is
`/root/w13gold`**: the session was dispatched as `W13-GOLD` and renamed to `W13-BASE` after
launch, because the owner's direction to carry the normative document corpus into PostgreSQL
would have made "golden corpus" name two different things in one programme (`D-1.6`, `D-8`).
The branch keeps the old name deliberately — renaming a branch mid-run risks the commits and
buys nothing. Everything this session writes is named "response baseline".

- **HEAD on arrival:** `85aaa248043b16348d54f6d3f08b0660baa7c7c3` (`85aaa24`, `origin/dev`).
- **Instance:** `gate-w13a`, PostgreSQL `55690`, S3 `59290`/`59291`, database `audit_w13a`,
  bucket `auditmanager-gate-w13a`.
- **Scope:** `tests/**` and this file. Nothing under `src/`, `db/`, `contracts/`, `web/`.
  No new dependency, no bytes added under `fixtures/`.

## 1. Where the baseline lives, and why

`tests/characterization/w13_baseline/`.

`tests/characterization/` already exists in the tree and holds a README and nothing else:
*"Behavior/golden evidence extracted from legacy and product requirements."* That is exactly
what this is — evidence of what a surface does, captured before it is rewritten — and it is
the only top-level suite directory whose stated purpose is that and not "cross-boundary
evidence of a thing being built". It is under `tests/**`, which this session owns, so nothing
here needs another writer's tree.

It is not under `tests/integration/api/`, because those suites assert *rules*; this asserts
*bytes*, it is deleted the moment wave 13 ends, and mixing the two would leave a reader unsure
which failures are contract failures.

## 2. What is captured

33 records, `tests/characterization/w13_baseline/records/*.json`. Each carries the request,
the status, **every** response header, and the body — bytes for the binary ones, text for the
JSON ones — plus the enumerated list of substitutions that record used and why each was
allowed.

**`startRun` is case 03**, as early as its own prerequisites (a project, a document) allow.
`D-5` records `POST /api/v1/runs` answering **500 twice** to the only browser that has ever
driven this system, while every in-process suite and every certification had it green.
Capturing it first means a wrong in-process capture shows up at the start of the run.

| Group | Cases |
|---|---|
| the twelve operations, success | `01` createProject, `02` uploadDocument, `03` startRun, `06` getRunStatus, `08` listRunFindings, `09` getFinding, `10` appendDecision, `11` listDecisionHistory, `12` exportRunCsv, `13` getDocumentVersion, `14` streamDocumentVersionContent, `16` listProjects |
| the five negative-envelope refusals | `17` `pdf_magic_bytes`, `18` `byte_size <= 26214400`, `19` `not_encrypted`, `20` `1 <= page_count <= 30`, `21` `every_page_has_extractable_text` |
| `additionalProperties`, every write body | `23` createProject, `24` startRun, `25` appendDecision, `26` uploadDocument (an undeclared **part**) |
| idempotency | `04` startRun replay, `05` startRun replay under a normalised property, `05b` key-reuse **conflict**, `05c` createProject replay |
| the 26 MiB boundary, both sides | `18` framed body of exactly 27 262 976 bytes → the **envelope** answers; `22` one byte more → the **transport** answers with `max_bytes` |
| Range | `15` `bytes=100-163` → 206, `Content-Range`, a 64-byte window |
| the CSV | `12`, bytes: BOM `ef bb bf` and CRLF, compared as bytes |
| `X-Correlation-Id` | `07` supplied and echoed (the supplied value is a literal, so the echo is pinned exactly); assigned in the other 32 |
| the layer's own refusals | `27` missing `Idempotency-Key`, `28` no route, `29` **404 and not 405** for a declared path under an undeclared method, `30` a malformed identity → `not_found` |
| **the D-7 exception** | `31`, and only `31` |

**What is not captured**, said plainly so nobody reads an absence as a pin:

- **anything about authorization.** The contract carried no `securitySchemes` when this was
  taken (`D-6`), so every request here is unauthenticated **and is answered**. `T-6` changes
  every operation's unauthenticated behaviour and this baseline has nothing to say about that.
  It is the first thing the corpus's own `README.md` says;
- **any `live` or `proxy` provider path.** Recorded mode throughout; no live provider is
  needed and the capture asserts it cannot spend;
- **pagination past the first page.** `16` pins the page envelope and asserts the cursor
  decodes to exactly the page's last sort key, but no second page is fetched;
- **the query filters** on `listRunFindings` (`category`, `verdict`) and the `limit`/`cursor`
  refusals. `tests/integration/api/test_query_surface.py` covers those as rules; this is a
  baseline of bytes and it does not duplicate them;
- **the database-refusal paths** (`AM001`/`AM002`/`AM003` → `state_transition_not_allowed`).
  `tests/integration/api/test_database_refusals.py` owns them;
- **`dependency_unavailable`,** which needs the store to be down rather than to refuse a
  credential.

## 3. How generated values were made comparable

A value may be replaced by a `{{token}}` in exactly two ways, and the record names every one
it used:

1. **the journey already knows it** — it supplied the value or read it from an **earlier**
   response in the same journey. Substitution is by **exact value**, never by pattern;
2. **it sits under a field named one at a time in `journey.py`** — `TIMESTAMP_FIELDS`,
   `GENERATED_ID_FIELDS` — **and matches a pinned format** (`TIMESTAMP_FORMAT`,
   `CORRELATION_FORMAT`, the per-field identity shapes). The value is checked against its
   pattern *first*, then replaced by exact value.

Nothing is substituted by scanning a body for things that look generated. A changed key
order, a changed separator, a renamed property, a dropped field, a different message, a moved
constraint, a different status or a missing header is a byte difference.

Two values get a rule rather than a literal, and both say so in the record:

- **`Content-Length`** is tokenised unconditionally. It is a function of the body, the body is
  compared byte for byte, and the comparison separately asserts
  `Content-Length == str(len(body))` — `test_a_content_length_that_does_not_describe_the_body_is_reported`
  proves that half can fail. Pinning the number as well would restate the body comparison and
  would go red for a token whose replacement is a different length, which is noise;
- **`X-Correlation-Id` when the request supplies none.** Checked against the pinned
  `^cid-[0-9a-f]{32}$` before it is tokenised. Case `07` supplies one and pins the echo as a
  literal.

**Nothing was silently normalised, and the harness proved it twice.** The first capture left
`model_call_id` untokenised; the comparison went red against a second journey and named the
byte. It is now a declared `GENERATED_ID_FIELDS` entry with its own pinned shape rather than
an unexplained exclusion. The same run found identities leaking into the *request* targets of
seven records, which are now tokenised too.

Every expectation is a literal. Not one is imported from the module it checks —
`docs/program/dispatch/OPERATING_CONSTRAINTS.md` §12, three instances on record.

## 4. The demonstration that the comparison can fail

Two layers, both required, because a baseline nobody has seen reject anything will accept
anything.

**In the tree, permanently.** `test_the_comparison_reddens_on_a_planted_difference` plants a
moved status, a dropped `X-Correlation-Id`, a renamed body property, a body whose keys were
re-ordered and re-separated by `json.dumps`, a CSV with its BOM removed, a CSV with LF for
CRLF, and a fixture whose pinned digest no longer matches — and requires each to be reported.
It asserts the unperturbed record matches first, so the test cannot pass by being broken.

**By hand, against the committed records.** Log: `/root/w13gold-logs/perturbation-demo.log`.
Four committed records were edited — `03` status `202`→`200`, `18`'s constraint
`byte_size <= 26214400`→`max_bytes`, `12`'s first CRLF→LF, `31`'s
`permission_denied`→`storage_credential_refused` — and the suite went

```
5 failed, 33 passed
```

failing exactly those four cases plus the planted-difference test (whose precondition is
record `03`). `git checkout` restored them and the suite returned `38 passed`. **The D-7
record is compared like any other**: being the permitted exception does not make it
unwatched, it makes the change require a citation.

## 5. The D-7 path, marked

`records/31-streamDocumentVersionContent.storage_permission_denied.json`, and it is the only
record carrying an `exception` block. Today it is:

```
403  error_code "permission_denied"
     details {"required_capability": "blob_storage_rw", "aggregate_type": "Blob"}
     message "The authenticated subject is not permitted to perform this operation
              on this resource. Authorization is decided server-side."
```

— for a refusal in which **there is no authenticated subject at all**: the application's own
S3 credential was rejected by the store. Reached by building a second application through the
composition root's own `environ` parameter with a wrong `S3_SECRET_ACCESS_KEY`; nothing under
`src/` is touched and no module is patched.

`test_exactly_one_record_is_marked_as_the_permitted_exception` requires the marked set to be
exactly this one case, so the exception is countable rather than arguable at the end of a long
wave. **Every other difference is a failure of the wave, whatever argument accompanies it.**
## 6. What is false or imprecise in the brief

Checked against the tree at `85aaa24`, with the query beside each.

**6.1 — the rename was not on `dev` when I was dispatched; it is now. Withdrawn, with the
measurement kept.**
When I checked at my base commit, `git merge-base --is-ancestor 23076e0 85aaa24` was **false**
— `23076e0` was on `planning/prototype-roadmap` only, and `ALPHA_ROADMAP.md` in my worktree
still read `Stage 1 — W13-GOLD` and `golden corpus` at six places. I wrote it up as a finding.
It has since stopped being one: `origin/dev` advanced from `85aaa24` to `7399d65` during this
session and now carries the rename, so §4 reads `W13-BASE` and `response baseline`. I rebased
onto `7399d65` and re-ran the suite before saying so. **A stage-2 session branching from `dev`
now reads the new name.** Recorded rather than deleted, because the window in which a dispatch
and its plan disagreed was real, and because withdrawing a finding is cheaper than a stage-2
session hunting a corpus under the wrong name. The three commits `dev` gained
(`f240f86`, `054c329`, `7399d65`, plus `06d32bd`) touch `docs/` only —
`git diff --name-only 85aaa24..origin/dev | grep -E '^(src|contracts|db|web|fixtures)/'` is
empty — so nothing under this baseline moved.

**6.2 — "the 26 MiB boundary" is the *transport's*, and `26214400` is 25 MiB.**
Measured: `multipart.MAX_BODY` = `26 * 1024 * 1024` = **27 262 976**;
`ingest.MAX_BYTES` = `25 * 1024 * 1024` = **26 214 400**. So the constraint string
`byte_size <= 26214400` is the **25 MiB** envelope bound, and the 26 MiB figure is the
transport's. The brief — and `ALPHA_ROADMAP.md` §4 — put the two in one phrase in a way that
reads as though 26 MiB were the envelope's number. Nothing downstream is wrong because of it,
but "the 26 MiB boundary on both sides" has only one coherent reading and I captured that one:
`18` frames a body to exactly 27 262 976 bytes so the transport passes it and the **envelope**
answers; `22` adds one byte so the **transport** answers. It is the only boundary at which
both guards can be made to speak, which is the point
`tests/integration/ingest/test_size_guard_boundary.py` makes.

**6.3 — "~1 800 lines get rewritten" is low; the measured figure is ~1 968.**
`wc -l src/auditmanager/api/routers/*.py src/auditmanager/api/schemas/*.py` at `85aaa24` in
`/root/w13gold` → **2 511** total. `ALPHA_ROADMAP.md` §4 keeps `ports.py` (233),
`errors.py` (196) and the package `__init__.py` (114), leaving **1 968** replaced. The
roadmap's own "~1 950" is right; the brief's "~1 800" is not. Figures in this programme
travel by being repeated, so this one is recorded with its command and its tree
(`OPERATING_CONSTRAINTS.md` §12).

**6.4 — "a four-times-certified surface" against `D-5`'s "three certifications".**
`DEBT_REGISTER.md` D-5 says `startRun` "is green in every suite and in **three**
certifications"; the brief and the coordinator both say four. Two figures are in circulation
for the same fact. Not mine to settle — flagged because D-5 is the row this stage's ordering
was changed for.

**6.5 — `OPERATING_CONSTRAINTS.md` is not at the repository root.**
It is `docs/program/dispatch/OPERATING_CONSTRAINTS.md`. Its §12 says exactly what the brief
says it says, including that the third instance was the integrator's own.

**6.6 — everything else in the brief held.** Base commit, the instance and its six values,
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, foundation 35, the absent
`web/node_modules`, "no live provider needed", the five constraint strings, the D-7 path and
its reachability, `make mutation-copy`, and that every oversize fixture in the repository
(`oversize.pdf` is 27 303 204 bytes) trips the transport guard first.

## 7. One finding about the surface itself

**`startRun` with the same key and a payload that differs only by `provider_mode` is a
replay, not a conflict.** Captured as `05`.

`src/auditmanager/runs/commands.py:200` says "the same key with a **different payload** raises
`idempotency_key_reuse`", and that is true at the command layer. At the transport it is not
the whole story: `RunAdapter.start_run` refuses a `provider_mode` that disagrees with the
deployment's and otherwise passes the *configured* value down, so the property is normalised
away before the fingerprint is taken. A caller who adds `"provider_mode": "recorded"` to the
body and re-sends under the same key gets **202 and the original run**, byte for byte — not a
409. The genuine conflict is captured separately at `05b`, on `createProject` with a different
`name`.

This matters to stage 2 because it is precisely the kind of behaviour a rewrite moves without
noticing: a Pydantic model that gives `provider_mode` a different default, or that forwards
`None` where the current parser forwards the configured value, changes which of `04`, `05` and
`05b` a request lands in — and all three are pinned.
## 8. The gate, and the numbers

`make gate` on `agent/w13-gold` at `/root/w13gold`. Run twice — before the rebase
(`/root/w13gold-logs/gate.log`) and again on the rebased tree
(`/root/w13gold-logs/gate-rebased.log`) — with identical counts:

```
1543 passed, 5 skipped, 167 subtests passed in 248.94s
frontend:    35 files, 440 tests passed
foundation:  35 passed
GATE OK: battery, foundation, frontend and whitespace all pass
```

1543 = the expected 1505 plus this suite's **38**: 33 record comparisons and five structural
tests (the record set matches the journey; the twelve operations are all covered; exactly one
record is the permitted exception; the planted differences are reported; a `Content-Length`
that does not describe its body is reported). Skips and subtests unchanged.

The suite writes nothing while it runs, so it does not trip the gate's
changed-during-the-run check. `git status --porcelain` is empty before and after.

## 9. Scope kept

Written: `tests/characterization/w13_baseline/**` and this file. Nothing under `src/`, `db/`,
`contracts/`, `web/`. No dependency added. No bytes added under `fixtures/` — the four
negative fixtures are read, and both size-boundary bodies are built in process. No tag, no
push, no merge.

## 10. For stage 2

1. **Run this suite first, before writing a FastAPI model.** It is green now; it tells you the
   moment it stops being.
2. **`records/29-dispatch.method_not_allowed.json` pins 404, not 405.** FastAPI answers 405
   with its own body by default. That is one of the twelve operations' paths under an
   undeclared method, and the surface's answer is `not_found` — deliberately, so the API is
   not an oracle for which paths exist.
3. **`27` and `30` pin what a framework most wants to answer for you**: a missing required
   header and a malformed path identity. Neither may reach a client as
   `RequestValidationError`.
4. **`04`, `05` and `05b` are three different idempotency outcomes on two operations.** §7
   says why a Pydantic default can move a request between them.
5. **`31` is the only record you may change**, and the commit that decided it is cited beside
   the new expectation. `test_exactly_one_record_is_marked_as_the_permitted_exception` will
   tell you if a second one appears.
