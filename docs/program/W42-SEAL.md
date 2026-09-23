# W42-SEAL — one reseal, two migrations, and the door the owner asked to close

**task_id:** `W42-SEAL` · **wave:** 42 · **lane:** `gate-w42a` · **base:** `b0a329b`
**worktree:** `/root/w42seal` · **branch:** `agent/w42-seal`

Opened before the first measurement, as the brief requires. Everything below is written as
it was found, including the three places where the brief's own premises did not survive
being checked.

---

## 0. Premises the brief asserts, checked before anything was built

The brief that dispatched this stream says, in as many words, that it *"is written by
someone who got it wrong last wave"* and asks for every premise to be verified and the
false ones reported as a deliverable. Four were checked. **Three did not hold.**

### 0.1 HELD — `require_authorization` publishes the verified subject

`src/auditmanager/api/security.py` ends `require_authorization` with
`request.state.subject = subject`, and `current_subject` reads it back. `W41-AUTHOR`'s brief
was the one that got this wrong; this one states it correctly.

### 0.2 FALSE — "the authorization dependency attached to the application covers the four routes"

The brief says: *"The authorization dependency is attached with
`app.include_router(router, dependencies=[...])`, so it covers the router's eighteen routes
and not the four the application itself carries. Move the seam so it covers the served
application."*

The first half is true. **The obvious reading of the second half produces a no-op that looks
like a fix.** `/openapi.json`, `/docs`, `/redoc` and `/docs/oauth2-redirect` are not API
routes at all: `FastAPI.setup()` installs them with `self.add_route(...)`
(`fastapi/applications.py`, measured on FastAPI 0.141.1), which is Starlette's
`Router.add_route` and builds a plain `starlette.routing.Route`. A `Route` has no dependant
tree, so **no** dependency mechanism reaches it — including `FastAPI(dependencies=[...])`,
which only seeds `self.router.dependencies` for `add_api_route`.

Measured rather than reasoned:

```
$ .venv/bin/python scratch/probe.py          # FastAPI(dependencies=[Depends(deny)])
/openapi.json 200
/docs 200
/redoc 200
/docs/oauth2-redirect 200
/thing 500                                    # the seam ran here and only here
```

A stream that had moved the argument from `include_router(...)` to `FastAPI(...)`, run the
suite and seen green would have reported `D-73` closed with all four routes still open.
**This is the case the brief's own sentence — "a mutation that comes back green is a
finding" — is about, one layer up: a repair that comes back green is a finding too.**

**What this stream did instead** is in §4.

### 0.3 FALSE — "the sealed copy" of the false `author_label` description is one copy

It is **two**: `components.schemas.DecisionEvent.properties.author_label.description` and
`components.schemas.DecisionRecord.properties.author_label.description`, byte-identical.
`DecisionRecord` restates `DecisionEvent`'s properties rather than composing them with
`allOf`, for the JSON-Schema-2020-12 reason the schema's own description gives, so the
sentence is carried twice and a reseal correcting one of them would leave `listDecisions`
— the knowledge base's own operation — still describing the field falsely.

### 0.4 FALSE — "your migration is `0009`", singular

`R-37` needs a column on `app_user`. `D-46`'s chosen shape needs a column on `audit_run`.
They are two unrelated facts about two unrelated tables, and every migration in this tree
is named for one subject (`0006_app_user`, `0007_credential_epoch`,
`0008_sign_in_throttle`). This stream writes **two**: `0009_reviewer_display_name` and
`0010_run_terminal_detail`. Head moves `0008` → `0010`.

**The decisive reason is not tidiness, it is rollback.** The brief's own rollback policy
says *"the migration must roll back"*, and `R-11` reverted an entire wave over a reseal.
`terminal_detail` is part of the reseal and `display_name` is not: one migration would make
reverting the reseal either impossible without also un-naming every reviewer, or possible
only by a downgrade that undoes more than the revert does. Two revisions can be rolled back
independently, which is what the policy is for.

Nothing in the tree pins the head to a literal —
`grep -rn "0008_sign_in_throttle" --include=*.py tests/ src/` finds one docstring mention in
`tests/integration/auth/test_sign_in_throttle.py` and no assertion.

---

## 1. S1 — `R-37`: a decision shows a display name, not a login

### 1.1 The empty case, decided and argued

**An account with no display name writes its login, and every layer says so out loud.**

The three candidates, and why the other two lose:

* **a blank** — `author_label` is `minLength: 1` in the contract and
  `CHECK (length(...) >= 1)` at the ledger, and `record_decision` refuses an empty one
  explicitly. A blank is not a label that renders badly; it is a refused write on the
  path of an expert recording a verdict, i.e. a `500` at the worst possible moment. Out.
* **inventing one** — "Reviewer 3", "usr_01M25…", the first half of an email. The brief
  forbids it and it is forbidden for a reason this programme has already paid for: a
  fabricated name in an append-only ledger is indistinguishable, later, from a name
  somebody chose, and `P04` exists to learn whose judgement was whose. Out.
* **the login** — it is a real, server-held, reviewer-typed string, `1..100` characters of
  `[a-z0-9._-]`, unique, and already what the ledger carried for the whole of wave 41. It
  is within `author_label`'s `1..128` **by construction**, not by luck, so the resolved
  label can never be empty and can never be too long. **Chosen.**

**The fallback is not silent, and that is the part the brief asks to be argued rather than
asserted.** `AGENTS.md` §4 forbids a silent fallback, and a fallback that only lives inside
one `or` expression is exactly one. So it is said in four places, three of which a person
can query rather than remember:

1. **one expression, named for what it answers** —
   `auditmanager.access.models.UserRecord.display_label`, a property on the account's own
   record, where the account's rules already live. Nothing else in the tree resolves this.
   It is a property on `UserRecord` and not a free function, so that the composition
   root can reach it without importing the `access` boundary to name a type it only
   passes through — which is the deep import `AGENTS.md` §4 forbids;
2. **the column stays nullable, so the state is a query** —
   `SELECT login FROM app_user WHERE display_name IS NULL` names every account on the
   fallback. This is `is_default_credential`'s own idiom: `0006` made "still on the seeded
   password" a query rather than folklore, and this is the same shape. A `NOT NULL` column
   backfilled from `login` would have been simpler and would have destroyed the
   distinction between *"has not chosen a name"* and *"chose their login"* permanently, in
   data, on the first upgrade;
3. **`python -m auditmanager.access.check` reports it**, once per account, under its own
   stable prefix `access-check NO DISPLAY NAME`, beside the two states it already reports.
   The exit status deliberately does **not** move: `check.py`'s own docstring argues that a
   status is for a state that is supposed to be temporary and becomes permanent unseen, and
   an unset display name is a cosmetic default, not a live credential;
4. **migration `0009` logs it while it runs**, naming the accounts, so the deployment log
   of every installation carries the sentence — `0006`'s third visibility mechanism,
   applied to the same table for the same reason.

### 1.2 Where the name comes from, and why it travels in the credential

`Subject` gains **`display_label: str`, required, no default.** The name is
`display_label` and not `display_name` on purpose: `UserRecord.display_name` is the
*nullable thing the reviewer chose* and `display_label` is the *resolved, always-present*
answer. Two names for two facts, spelled the same way at every layer. The no-default is the point,
exactly as it is for `token_epoch`: a caller that could omit it would attribute a decision
to whatever the default said, which is `D-66`'s shape and the thing
`TestThereIsNoConfiguredDefaultToFallBackInto` exists to keep out.

The name is resolved **once**, at the moment the account's row is read — in
`CredentialAdapter.issue` and `CredentialAdapter.change_password`, via
`display_name_for` — and is then carried in the signed credential beside `login`. Three
reasons, in order:

* **it is the mechanism `D-78` already established**, and `R-37` changes only the *source*
  of the label, not how it reaches the handler. `appendDecision` still reads a signed claim
  off the verified subject and still cannot be told one by a body;
* **the alternative widens the seam's port**, and `api/security.py` argues at length that
  `CredentialEpochs` must stay one method returning one integer on the path of every
  request. A display name reached through that port is a second column on the hot read;
* **the alternative crosses a bounded context.** A decisions router reaching the `access`
  boundary for a name is the deep import `AGENTS.md` §4 forbids.

**What it costs, stated rather than discovered:** the label is the display name as it was at
sign-in, for up to `TOKEN_LIFETIME_SECONDS` (one hour). A rename is visible on the next
credential. For an append-only ledger this is arguably the *right* reading — the row records
who made the decision under the name they had then — but it is a consequence, not a design
goal, and it is written down here.

### 1.3 The credential format moves `am1` → `am2`

A credential minted before this lands carries no `name`. There are exactly two things that
can be done with it and only one of them is allowed:

* refuse it — the same direction `0007` took, and everyone signs in again once;
* accept it and fall back to `login` **inside the seam**, which is a silent fallback on the
  authorization path, in the module that must not have one.

So it is refused. It is refused **at the version check**, by bumping `_FORMAT`, because that
constant's own docstring says it exists so that *"a future body — a different payload, a
different algorithm — is distinguishable rather than merely different"*. A required field
added to an `am1` payload makes the body different and not distinguishable, which is the one
thing the constant was put there to prevent. `grep -rn am1` finds no guard, fixture or
client that pins the string; the two test sites that use it are negative cases that stay
refused either way.

---

## 2. S2 — `D-86`: the sealed description, corrected in both copies

Replaced, in `DecisionEvent` and `DecisionRecord` alike, with a sentence that describes what
the field carries after S1 and keeps the half of `OD-12` that was always the point. The
schema does not move: same `type`, same `minLength: 1`, same `maxLength: 128`. The
conformance gate drops `description` under `N4`, so this is invisible to it — which is
precisely why it needs a reseal to reach a reader at all, and why `W41-AUTHOR` refused to do
it quietly.

**Reported, not repaired:** `docs/program/P02_SEAMS.md:508` and
`web/src/widgets/decision-history/ui/decision-history.tsx:13` were corrected in wave 41 to
say *"the login of the reviewer"*. `R-37` makes **both of those false too**, in the same way
and for the same reason `D-86` records. Neither path is in this stream's grant — the widget
is `W42-LOOK`'s and `P02_SEAMS.md` is outside `allowed_paths` — so both are handed to the
integrator in §7.

---

## 3. S3 — `D-46`: `RunStatus.terminal_detail`

The row's cheaper option, taken under `R-29`. `RunStatus` gains an optional
`terminal_detail`: a flat object of safe scalar classifiers, **restricted to the
`safe_detail_keys` the catalog declares for the code in `terminal_reason`**. No catalog code
is added; the catalog stays 22 and frozen.

### 3.1 How the restriction is enforced, and where

**One screen, not a second implementation.** `shared/errors/envelope.py` already screens an
envelope's `details` against `code.safe_detail_keys`, rejects non-scalars, bounds the value
length and runs the six forbidden shapes over every string. That logic is lifted verbatim
into a public `screen_details(code, details)`; `envelope.build` now calls it, and so does
the run terminal path. **The restriction therefore holds by construction rather than by a
second author remembering it**, and `OPERATING_CONSTRAINTS.md` §12's rule about two
spellings of one fact does not get a new instance.

It is applied at three points, each of which can refuse:

1. **at the point of decision** — `TerminalSelection.__post_init__` refuses a detail whose
   key is not in `ErrorCode(terminal_reason).safe_detail_keys`, and refuses a detail with no
   terminal reason to screen it against;
2. **at the database** — `0010` writes `CHECK (terminal_detail IS NULL OR terminal_reason
   IS NOT NULL)` and `CHECK (jsonb_typeof(terminal_detail) = 'object')`. A detail with no
   code beside it is unscreenable by anything, at any later time, so the coupling is
   structural and not advisory;
3. **at the edge** — `run_status_body` screens again before rendering. A row written by an
   older process, or by hand, does not get to publish a key the catalog does not declare.

An unrestricted detail object is how internals leak into a client. Three screens is not
belt-and-braces theatre: they fail in three different *eras* — when the run terminates, when
the row is written, and when a reader asks — and only the third one covers a row this code
did not write.

### 3.2 The true sentence this makes sayable

In `recorded` mode, a document with no recording terminates `analysis_input_invalid` with
`reason: "recording_missing"` and `stage_id: "text_analysis"` — the two keys the catalog
declares safe for that code, already screened once by
`StageError.from_domain_error`. `terminal_detail` is what carries them onto the run reading,
so the screen can finally say *your document is fine, the provider is fine, this deployment
has no recording for it.* `R-30` put the stand in `recorded` mode the same week, which makes
this the ordinary case rather than a hypothetical.

---

## 4. S4 — `R-31` / `D-73`: the four routes

### 4.1 What the repair actually is

Given §0.2, the seam cannot be made to cover a `starlette.routing.Route`. So the application
stops carrying any: `_assemble` builds the `FastAPI` with
`openapi_url=None, docs_url=None, redoc_url=None, swagger_ui_oauth2_redirect_url=None` —
which is what suppresses `setup()`'s four unguarded routes — and **declares the same four
paths itself**, as `APIRoute`s with `include_in_schema=False`, over FastAPI's own
`get_swagger_ui_html`, `get_swagger_ui_oauth2_redirect_html` and `get_redoc_html` so that
nothing about what they serve is re-implemented here.

The authorization dependency and the correlation declaration move from the
`include_router(...)` call to the `FastAPI(...)` constructor, where they seed
`app.router.dependencies` and therefore reach **both** the eighteen included operations and
the four routes the application declares. `include_router` is left with no `dependencies=`
argument at all.

`_operation_of` returns `None` for the four — an `APIRoute` with no `operation_id` — and
`None` is in no register, so they are guarded by the rule
`api/security.py` already states: *an unreadable route is a closed route.* Nothing was added
to `UNAUTHENTICATED_OPERATIONS`; it is still exactly `{"issueToken"}`.

The document does not move. `include_in_schema=False` keeps the four out of
`paths`, and the seam is still a `Security(bearer_scheme)` in every operation's dependant
tree, so `components.securitySchemes.bearerAuth` and every operation's
`security: [{"bearerAuth": []}]` are generated exactly as before. 15 / 18 / 51 throughout,
and the conformance gate is the proof.

### 4.2 The anti-vacuity guard

A test that drives the four paths passes the day somebody adds a fifth. So the guard asserts
a property of the assembled application instead:

> **every route the application serves is an `APIRoute`, and every one of them carries the
> authorization seam in its dependant tree.**

It is stated over `app.routes` with no exempt list. It fails if the dependency goes back to
`include_router` (the four self-declared routes lose it), if `openapi_url` is restored to
FastAPI's own handling (a `Route` appears, which is not an `APIRoute`), and if anyone adds a
fifth application-level route by any means. The seam is recognised by a marker
`build_authorization_dependency` stamps on the callable it produces, not by its name.

### 4.3 What must not break, and does not

* **`POST /auth/token` stays reachable without a credential.** It is still the one member of
  `UNAUTHENTICATED_OPERATIONS` and the one operation whose document `security` is `[]`.
* **The four serve normally to a caller who has one.** `/openapi.json` returns the same
  document bytes as before with a credential presented.

---

## 5. Verification

Provisioning, before any measurement:

```
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12   # exit 0, "bootstrap OK"
.venv/bin/python -c "import boto3"                     # boto3 1.43.90
npm --prefix web ci                                    # added 184 packages
```

Figures, the commit each was taken at, and the mutation ledger are in §6 and §8.

---

## 6. Measurements

*(filled as they are taken; every figure carries the commit it was measured at)*

---

## 7. For the integrator

*(filled at the end)*

---

## 8. Mutation ledger

*(filled as each guard is shown to fail)*
