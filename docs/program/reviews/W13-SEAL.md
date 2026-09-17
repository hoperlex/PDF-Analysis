# W13-SEAL — the contract reseal

Session `W13-SEAL`, wave 13 stage 0b. Branch `agent/w13-seal`, worktree `/root/w13seal`.

- **HEAD on arrival:** `876e095c81bb49948a894aa69e3298df020d2f86` — see §0, which records why
  this is not the commit the brief named.
- **Instance:** `gate-w13b`, PostgreSQL `55700`, S3 `59300`/`59301`, database `audit_w13b`,
  bucket `auditmanager-gate-w13b`.
- **Started:** 2026-09-18T00:14:48+05:00.

## 0. The base commit, and why it is not `origin/dev`

The brief says `git worktree add /root/w13seal -b agent/w13-seal origin/dev`. I did that and
landed on `7399d65`, where `tests/characterization/` holds a `README.md` and nothing else:
**the response baseline this brief requires me to update is not on `dev`.** `W13-BASE`'s merge
`876e095` has never been pushed; it exists only on the local branch `agent/w13-pin`.

`git merge-base --is-ancestor 876e095 origin/dev` → false.
`git merge-base --is-ancestor origin/dev 876e095` → true.

So `876e095` is `dev` plus the baseline, and it is the tree the brief's own gate expectation
describes: 1543 / 5 / 167 is `W13-BASE`'s recorded figure, the 1505 of `dev` plus that
session's 38. I reset the worktree to `876e095` and worked there. I did **not** take
`agent/w13-pin`'s tip `b12c4d0` (`feat(pins)`), which is stage 0a's in-flight work and not
mine to carry.

*(sections follow as the work lands)*

## 1. The security scheme, and why that shape

`contracts/api/v1/openapi.json`, at `a5f4001`.

```json
"securitySchemes": { "bearerAuth": { "type": "http", "scheme": "bearer", "description": "..." } }
```

and, at the document root, `"security": [{ "bearerAuth": [] }]`.

**Four decisions, each of which could have gone the other way.**

**`http`/`bearer`, not `apiKey`.** An `apiKey` scheme is a named header carrying a shared
secret. The owner's ruling `C` distinguishes exactly that from what the destination needs: *a
public application requiring HTTPS and authorization tokens*. A shared secret is a gate; a
bearer credential is an identity, and `Authorization: Bearer` is the shape OIDC hands you
without a translation layer. `D-6` makes the same distinction in its own words — "a shared
secret is a gate; a token is an identity. They are different deliverables and only the second
answers the owner's statement."

**No `bearerFormat`, and not `openIdConnect`.** This is where "the contract describes the seam,
not the implementation" is actually spent. An `openIdConnect` scheme *requires* an
`openIdConnectUrl`, which is a deployment's issuer — the contract would then have to change
when the deployment does, which is the opposite of what `T-6` buys. `bearerFormat` is softer
but the same mistake: the alpha's static token is opaque and a public OIDC token is a JWT, and
naming either pins the document to whichever is current. A guard asserts the scheme's key set
is exactly `{type, scheme, description}` and that the rendered scheme contains no URL.

**Declared once at the root, not twelve times.** The contract's own `info.description` already
establishes the convention: *"Three rules hold everywhere and are not repeated per operation."*
Opaque identity, one failure shape and correlation are declared once; authorization is the
fourth rule of that kind. A root requirement is also **fail-closed** — an operation added later
is covered unless it deliberately opts out — where twelve per-operation declarations leave a
thirteenth silently open.

The guard does not assert that shape. It computes each operation's *effective* security the way
OpenAPI 3.1 resolves it (an operation's own `security` overrides the root; `security: []`
removes the requirement) and requires all twelve to resolve to `bearerAuth` with no empty
alternative. So it holds however the requirement is expressed, and it catches the two ways an
operation leaves the authorized surface quietly. Both are in the mutation table.

**401 and 403 declared on all twelve.** A scheme with no declared refusal leaves a generated
client no typed shape for the failure it just made reachable. Two new response components:
`AuthenticationRequired` and `PermissionDenied`, both the `ErrorEnvelope`, both carrying
`X-Correlation-Id` like every other response here.

`403` is declared even though the alpha's single static token can never produce one — with one
token there are no differentiated rights. That is the point: the catalog has carried
`permission_denied` with `aggregate_type` and `required_capability` since CP-00 and `not_found`'s
summary already promises never to reveal a resource the caller may not see. **The contract was
designed for an authorized, multi-subject system and had that part left unfilled.** Filling it
now is what makes the public version a change of implementation rather than a second reseal.

**What was not added.** No thirteenth operation: no `/auth`, `/login` or `/token` path — the
seam is a header the deployment satisfies. No role, subject, scope or capability vocabulary.
Nothing about the health plane, which `T-3` puts outside `/api/v1` on its own port and which
therefore needs no credential; the contract does not describe it and still does not. Paths,
operations and component schemas are unchanged at **10 / 12 / 43**, and
`test_the_document_declares_no_operation_outside_the_twelve_capabilities` now asserts both
counts beside the scheme, so "the seam did not grow the surface" is checked rather than claimed.

`info.description` no longer says the surface *"deliberately does not have: authentication"*.
A document that declares a scheme and denies having one is the `D-8` shape exactly — a sentence
repeated until nobody opens the file — so a guard asserts that sentence is gone.

## 2. The new code — name, definition, keys, and the argument for each

`contracts/domain/v1/error-codes.json`, at `e6d0a6a`. This is the commit cited in the
baseline record.

```json
"dependency_credential_refused": {
  "http": 500,
  "retryable": false,
  "category": "dependency",
  "safe_detail_keys": ["dependency"],
  "evidence": ["D-7", "OWNER_RULINGS_2026-09-17.md R-3"]
}
```

> A required dependency refused the application's own credential. This is a server-side
> configuration fault with no authenticated subject of this API involved: nothing was created,
> and retrying does not change the outcome until an operator repairs the credential.

### The name

Two shapes were available: **storage-specific** (`storage_credential_refused`, matching
`storage_integrity_error`) or **dependency-generic**.

I took the generic one, and the deciding evidence is in the tree rather than in a document.
`src/auditmanager/analysis/text/proxy.py:222` maps a **401 from the model proxy** —
its own comment says *"the model proxy refused the token"* — onto `dependency_unavailable`,
which the catalog pins **`retryable: true`**. That is the same misclassification `D-7` names,
in a second adapter, on a second credential, and with a worse consequence: a caller reading
`retryable` as authoritative, which the catalog instructs it to do, retries forever against a
rejected token. `D-7` found one instance and generalised from it correctly.

So the code is named for the axis it actually sits on. `dependency_unavailable` and
`dependency_credential_refused` are a pair a reader can hold: the dependency could not be
reached, versus the dependency answered and refused us. The detail key `dependency` carries
which one, in the vocabulary that already exists — `blob_storage` today, the provider's class
name when someone takes the second instance.

**I did not change `proxy.py`.** `R-3` ruled on the storage collision; the provider 401 is an
unruled behaviour change in an adapter I do not own, and it moves a `retryable` flag a caller
may act on. It is recorded in §6 as a finding for the integrator instead. The generic name
costs nothing if it is never taken up and costs a second catalog addition if it is not there.

### `http: 500`

The hardest call, and the one I would defend first.

Keeping `403` was tempting: the envelope's `error_code` is the authoritative discriminator, so
two codes may share a status, and `D-7`'s complaint is literally that the two are
"indistinguishable **in the envelope**". A distinct code fixes that at any status.

It is still wrong. RFC 9110 makes 4xx the class where *the client* erred; 5xx is where the
server is aware it has. A rejected **application** credential is unambiguously the second: the
caller presented nothing wrong and nothing the caller can change alters the outcome. After this
reseal `403` genuinely means "you lack rights" — and leaving a second meaning on the *status*
would settle half of `D-7` and leave the half a browser actually reacts to. Wave 13 is the wave
that makes this a public application with real authentication; a 403 from a storage
misconfiguration would send a real user to re-authenticate, repeatedly, for a fault
re-authentication cannot touch. `D-1.5` is on record as this programme's one certified
exception and it is about exactly that: what a user sees.

Not `503`: that is "try again later" and the condition does not clear on its own. Not `502`:
the store answered correctly and promptly, and refused. `500` with a *stable, specific* code is
the design the catalog already uses — `internal_error` is 500 and carries a code and a
correlation id — and this code is strictly more informative than `internal_error`, which is the
whole point of adding one rather than mapping to it.

### `retryable: false`

A refused credential is not fixed by retrying; it is fixed by an operator. The class that
raises it has said so in its own docstring since P1: *"a refused credential is not retryable and
is not a degraded service"* — which is why `dependency_unavailable`, `retryable: true`, was
rejected for it. (Small correction to the brief: that sentence is in `StoragePermissionDenied`'s
docstring, not in `StorageUnavailableError`'s.)

### `category: dependency`

The schema pins the category set to ten, so the choice was among those. `internal` is defined
as *"an unclassified server fault"* and this one is now classified; `policy`, `validation` and
`authorization` are all wrong on their face. `dependency` is right on the axis but its
description named only two situations, so it was widened to three: *transiently unavailable,
**refused the application's own credential**, or a required authoritative reference cannot be
resolved.* The category **set** is untouched; only a description grew, and it grew to stop
being a place where a true thing was unsayable.

### `safe_detail_keys: ["dependency"]` — exactly one, and the two that were dropped

**`dependency` is in** because it is the one classifier that changes what an operator does:
rotate the object-store key, or rotate the provider token. It is already declared safe for
`dependency_unavailable`, it carries a stable class name and never a host, URL, bucket or
endpoint, and it adds no new leak surface.

**`aggregate_type` and `required_capability` are out, and this is the substance of the
settlement.** `D-7`'s finding is that both codes declared *exactly* those two keys and neither
carried a discriminator. Carrying them forward under a new name would reproduce the collision
with an extra step. They are also simply false here: `required_capability: blob_storage_rw`
describes a **subject's** capability and there is no subject, and `aggregate_type: Blob` names
the addressed aggregate when the addressed aggregate is not what failed — it invites the exact
reading "you lack rights on this Blob".

**`field` was considered and rejected.** `StorageConfigurationError` already carries `field` to
name the environment variable at fault, on the principle that *a name is not a value*, and it is
the single most actionable thing an operator could receive. But the envelope is a **caller**-facing
document on a public surface, and the catalog's own safety rule places operator diagnostics
elsewhere: *"correlation_id is always present so an operator can find the full diagnostic record
without the response having to carry it."* The operator gets the variable name from diagnostics;
the caller gets a dependency class name and a correlation id. The narrower set is also the
fail-closed one.

### The size of the act

`D-8` is the frame and it holds: the catalog declares `"frozen": false`,
`"status": "draft_candidate"`, `"contract_version": "1.0.0-draft.1"`. **This is an addition to a
draft candidate, not a freeze-break.** Two further measurements say the same thing:

- the catalog's own schema was already built to admit one. `properties.codes` declares
  `minProperties: 20` and **no** `maxProperties`, with an `additionalProperties` subschema for
  the shape of a code. A 21st code validates without touching that constraint — I raised the
  floor to 21 and added the name to `required` so the *new* state is pinned as tightly as the
  old one was;
- `contract_version` does not move. The candidate is unreleased, so the addition supersedes
  nothing. `candidate_revision` moves 5 → 6 across all three domain catalogs and all three
  schemas, which is the discipline round 5 recorded and the mechanism the schema's own comment
  describes: the pin exists "so the candidate cannot change meaning without a deliberate edit of
  both the catalog and this schema".

I did **not** add an entry to `open_owner_decisions`. That register's `id` is a closed enum of
`PD-*` identifiers from the CP-00 architecture review; `R-3` is a 2026-09-17 owner ruling from a
different register. Putting it there would need a schema enum edit and would put two kinds of
thing under one name — `D-1.6` and `D-8`'s shape. The citation lives in the code's `evidence`,
its `notes` and the `revision_note` instead.

## 3. Everything that moved with the contract

The brief's Step 4 list is four items. The measured list is twelve, and the difference is §6.2.

| Artefact | What moved | Commit |
|---|---|---|
| `contracts/domain/v1/error-codes.json` | the 21st code; `dependency` category description; `candidate_revision` 6 + note | `e6d0a6a` |
| `contracts/domain/v1/error-codes.schema.json` | `codes.required` + the name, `minProperties` 21, `candidate_revision` const 6 | `e6d0a6a` |
| `contracts/domain/v1/error-envelope.schema.json` | the `error_code` enum, and a new `allOf` branch pinning `retryable: false` for it | `e6d0a6a` |
| `contracts/domain/v1/identifiers{,.schema}.json`, `state-machines{,.schema}.json` | `candidate_revision` 6 only — the family carries one, and `W0-DOM-02` permits no other byte in those two | `e6d0a6a` |
| `src/auditmanager/shared/errors/codes.py` | the `ErrorCode` member; "twenty" → "twenty-one" | `e6d0a6a` |
| `src/auditmanager/storage/errors.py`, `s3.py`, `port.py`, `__init__.py`, `README.md` | the class renamed and moved to the new code; `SAFE_DETAIL_KEYS` loses the two subject-shaped keys with the code that declared them | `e6d0a6a` |
| `db/migrations/versions/20260910_0002_pc01_schema.py` | `ERROR_CODES` — three `CHECK` constraints are built from it | `e6d0a6a` |
| `contracts/api/v1/openapi.json` | the scheme, the root requirement, 401/403 on twelve, the enum, `info.description` | `a5f4001` |
| `web/openapi/openapi.json` | byte copy of the above | `b370b03` |
| `web/src/shared/api/generated/**` | all four files, regenerated — never hand-edited | `b370b03` |
| `web/FRONTEND_LOCK.json` | six digests, `content_commit` `a5f4001`, a new `commit_note` | `b370b03` |
| `tests/characterization/w13_baseline/**` | record 31, `journey.py`, `README.md`, two new tests | `d8b3fff`, `09e863b` |

**Seven tests pinned the catalog's size as a literal**, and every one was moved deliberately
rather than loosened. The programme demands literals (`OPERATING_CONSTRAINTS.md` §12) and this
is the bill for them, paid the right way:

| File | Pin |
|---|---|
| `tests/contract/domain_p02/test_contract_vocabulary.py` | `len(migration_module.ERROR_CODES) == 20` |
| `tests/contract/domain_p02/test_openapi_document.py` | `len(declared) == … == 20` |
| `tests/contract/shared_kernel/test_error_kernel.py` | `test_there_are_twenty` → `…_twenty_one` |
| `tests/integration/api/test_envelope_screen_rules.py` | `len(raw["codes"]) == 20` |
| `tests/contract/test_cp00_candidate.py` | `len(catalog["codes"]), 20` |
| `web/tests/contract/seam-operations.contract.test.ts` | `toHaveLength(20)` |
| `web/tests/unit/api/failure-surface.test.ts` | `toHaveLength(20)` |

I found four by reading, the gate found the fifth, and a sweep
(`grep -rn "== 20\|toHaveLength(20)"` across `tests/`, `web/tests/`, `src/`, `db/`) found the
last two. **The sweep mattered more than it should have**, because neither of the last two can
fail the gate on its own: `Makefile:488` excludes `tests/contract/test_cp00_candidate.py` from
the battery, and the frontend step runs *after* the battery, so the first failure hid the
second. A guard in a gate-excluded suite is a guard that goes red in private — recorded in §6.9.
I measured the CP-00 suite before and after against a throwaway worktree at `876e095` rather
than trusting its summary line: that suite is already 64+ red at base (`CP-00` was never
ratified), and the diff of the two `FAILED` lists showed exactly one failure attributable to me.

And
`tests/integration/api/test_operation_surface.py`, whose assertion was
`"securitySchemes" not in components` with the reason "PC-01 has no authentication and no role
model" — **inverted, not deleted**, with the superseded premise named in the docstring.

### The database, and the one thing to know about it

`test_error_code_domain_equals_the_frozen_catalog` requires the migration's `ERROR_CODES` tuple
to equal the catalog's key set **in both directions**, so the catalog cannot gain a code without
the DDL gaining it too. I edited the tuple in `20260910_0002_pc01_schema.py` rather than adding
a `0006`, because the test reads that module by path and a new migration would leave it failing
— and because **no database anywhere was created from the old tuple and has to be migrated off
it**: nothing is deployed (`ALPHA_ROADMAP.md` §2 — no packaging, no application image, no host
yet under `R-1`), and every lane's instance is built by `alembic upgrade head` from empty. My
own `audit_w13b` was.

**That stops being true the moment `R-1`'s VPS holds a database.** The next catalog addition
after that is a real migration with a real `ALTER ... DROP CONSTRAINT` / `ADD CONSTRAINT` on
three columns. Recorded here so the cheapness of this one is not read as a precedent.

## 4. The baseline record, and the citation

`records/31-streamDocumentVersionContent.storage_credential_refused.json`.

|  | as captured by `W13-BASE` | now |
|---|---|---|
| status | `403` | `500` |
| `error_code` | `permission_denied` | `dependency_credential_refused` |
| `message` | the catalog's *"the authenticated subject is not permitted…"* | the new summary |
| `details` | `{aggregate_type: Blob, required_capability: blob_storage_rw}` | `{dependency: blob_storage}` |
| `retryable` | `false` | `false` |

`exception.decided_by` is **`e6d0a6a`**, with its subject and date beside it, and
`exception.status` is now `"taken"`. The count stayed at one:
`test_exactly_one_record_is_marked_as_the_permitted_exception` is unchanged and still passes.

**The evidence that the change is confined to that one record.** Before touching anything under
`records/`, I ran the suite against the changed implementation. `journey.py`'s own literal
assertion `storage.status == 403` fired first and aborted the session fixture — one cause, named
in advance, and nothing else got as far as disagreeing
(`/root/w13seal-logs/baseline-before-update.log`). Then I re-ran **`capture.py`**, which
rewrites all 33 records, rather than hand-editing one. `git status` afterwards listed exactly
one changed file. A hand edit would have proved only that I edited one file; the recapture
proves the other 32 responses are byte-identical to what `W13-BASE` committed.

The file was renamed with the code it carries — `storage_permission_denied` →
`storage_credential_refused`. The `31-` prefix is deliberately unchanged, so "record 31", which
is how `W13-BASE.md` §10 and the roadmap refer to it, still finds it.

### Keeping "this baseline says nothing about authorization" true rather than old

The contract now declares the seam; the implementation does not, because that is stage 2's.
So the 33 records still show unauthenticated requests being answered — and after this reseal
that is a thing a later reader can mistake for the surface's *intended* unauthenticated
behaviour. The README paragraph stayed true by accident of ordering; that is not a property to
leave unguarded.

`test_the_baseline_makes_no_authorization_claim` reports any record that carries an
`Authorization` or `Proxy-Authorization` header, pins `401` or `403`, or drops its
`pre_authorization` declaration. Its prover plants all three and requires each to be reported,
and both call the **same** `_authorization_claims` function — the first version of the prover
re-implemented the rule, which proves only that a copy can fail. The README is amended with the
reseal commit, the before/after table, and the sentence that if stage 2 makes the journey
authenticate, that test and that paragraph change together.

## 5. Every guard, shown red without the change

Log: `/root/w13seal-logs/perturbation-demo.log`. Each case plants one difference in the tracked
file, runs the single test that should object, and restores with `git checkout`. The unmutated
tree is run first — **a red from a tree you never baselined is not evidence** — and
`git status --porcelain` is empty at the end of the run, which the script asserts.

| # | Planted | Guard | Result |
|---|---|---|---|
| 1 | `securitySchemes` removed entirely — the state `D-6` measured | `test_the_document_declares_exactly_one_security_scheme` | **red** |
| 2 | scheme gains `bearerFormat: "JWT"` | `test_the_scheme_declares_the_seam_and_not_its_implementation` | **red** |
| 3 | scheme becomes `openIdConnect` with an issuer URL | same | **red** |
| 4 | root `security` dropped — every operation open again | `test_every_operation_requires_the_bearer_scheme` | **red** |
| 5 | `exportRunCsv` opts itself out with `security: []` | same | **red** |
| 6 | root requirement gains an empty alternative `{}` | same | **red** |
| 7 | a requirement names an undeclared `apiKeyAuth` | `test_every_declared_scheme_is_required_somewhere` | **red** |
| 8 | `createProject` loses its `401` | `test_every_operation_can_report_401_and_403` | **red** |
| 9 | `info.description` goes back to denying authentication exists | `test_the_document_no_longer_says_it_has_no_authentication` | **red** |
| 10 | the 21st code removed from the catalog | `tests/contract/shared_kernel/test_error_kernel.py` | **red** (import-time `RuntimeError`) |
| 11 | the new code given back `aggregate_type`/`required_capability`, and the class made to emit them | `test_refused_credentials_are_typed_dependency_credential_refused` | **red** |
| 12 | the storage class put back on `permission_denied` — the `D-7` collision restored | the baseline suite | **red**, 33 errors |
| 13 | `web/openapi/openapi.json` loses the scheme — snapshot ≠ contract | `openapi-drift.contract.test.ts` | **red** |
| 14 | record `01` starts carrying an `Authorization` header | `test_the_baseline_makes_no_authorization_claim` | **red** |
| 15 | `FRONTEND_LOCK.json`'s `openapi.sha256` goes stale | `frontend-lock.guard.test.ts` | **red** |

Cases 4, 5 and 6 are three different ways to leave the authorized surface and they are three
cases on purpose: a guard that asserted the literal document shape would catch only the first.

Case 11 needed two attempts and the first one is worth recording. Widening the code's
`safe_detail_keys` and the class's `allowed_details` alone left the test **green** — because
nothing *sets* `aggregate_type`, so the rendered details did not change. The mutation was
ineffective, not the guard weak. Making the class `setdefault` the key too reddened it. A
mutation that does not reach the observable is a green that means nothing, which is the same
family as `OPERATING_CONSTRAINTS.md` §12.

**On `make mutation-copy`.** The brief says to use it with `FULL=1` for contract mutations. I
made the copy (`/root/w13seal-mut`) and it does copy `contracts/` as a real directory rather
than a symlink — but the copy contains **no `tests/`**, and the contract suites resolve
`contracts/` from the test file's own location, i.e. the real worktree. So mutating the copy's
contract cannot reach the guard that reads it. The copy works for `src/` mutations through
`-o pythonpath=<mut>/src`; for a contract document the technique is the one `W13-BASE` used —
mutate the tracked file, run, `git checkout`, and assert the tree is clean afterwards. Recorded
in §6.

## 6. What is false or imprecise in the brief

Each with the query beside it, against `876e095`.

**6.1 — Step 0's base commit does not contain the artefact Step 4 requires me to edit.**
Already §0. `git worktree add ... origin/dev` lands on `7399d65`, where
`tests/characterization/` holds a `README.md` and nothing else. `W13-BASE`'s merge `876e095`
was never pushed and lives only on the local branch `agent/w13-pin`.
`git merge-base --is-ancestor 876e095 origin/dev` → false. The brief's own gate expectation
(1543/5/167, "the response baseline added 38") describes `876e095`, not `7399d65`, so the two
halves of the brief disagree and the gate figure is the half that is right. **This is the
fourth wave-13 document to be written against a `dev` that had not caught up** — `W13-BASE`
§6.1 records the same shape from the other direction.

**6.2 — the Step 6 ownership list is not the set of files this change requires.**
Step 6 grants `contracts/**`, `web/openapi/**`, `web/FRONTEND_LOCK.json`, the generated client,
`src/auditmanager/shared/errors/**`, `tests/characterization/w13_baseline/**` and the review.
Settling `D-7` is impossible inside that set. Five trees outside it had to move, and none is
the API layer:

- `src/auditmanager/storage/**` — the class that raises the code. Step 3 names
  `storage/errors.py:153` explicitly, so this is a gap in Step 6 rather than a disagreement
  between them;
- `db/migrations/**` — `ERROR_CODES` builds three `CHECK` constraints, and a test requires set
  equality with the catalog;
- `tests/contract/**` — three literal `20`s;
- `tests/integration/api/test_operation_surface.py` — asserted `securitySchemes` **not** in
  `components`. The brief's own premise ("the contract declares no `securitySchemes`") had a
  guard behind it and the brief does not mention it;
- `tests/integration/storage/**` and `web/tests/contract/**` — the same, one each.

I made all of them. A reseal that stopped at the granted paths would have left a red gate and a
half-settled debt.

**6.3 — `openapi-drift.contract.test.ts` does not say the contract has twelve operations.**
`grep -c "twelve\|12" web/tests/contract/openapi-drift.contract.test.ts` → **0**. That file
checks the snapshot, the four generated files and regeneration determinism. The twelve is
asserted by `web/tests/contract/seam-operations.contract.test.ts` ("the twelve seam
operations"), by `tests/contract/domain_p02/test_openapi_document.py::test_the_surface_is_exactly_the_declared_capabilities`
and by `tests/integration/api/test_operation_surface.py`. The instruction was right and I obeyed
it; the citation was wrong, and a stage-2 session told to check the count there would find
nothing.

**6.4 — "`authentication_required` (401) and `permission_denied` (403) … with `safe_detail_keys`
`aggregate_type` and `required_capability`" is true of one of them.**
Measured: `authentication_required.safe_detail_keys` is **`[]`**, and its summary says why —
*"The response carries no hint about the addressed resource."* Only `permission_denied` carries
the two. This matters more than a footnote: the empty set is a deliberate design, and a reader
who took the brief literally would have "completed" the design by giving 401 detail keys it must
not have.

**6.5 — `dependency_unavailable`'s rejection is argued in the other class's docstring.**
Step 3 says *"it is not retryable and it is not a degraded service, which is why
`dependency_unavailable` was rejected for it; see that class's own docstring"*. That sentence is
in `StoragePermissionDeniedError`'s docstring. `StorageUnavailableError`'s says something else
("the type that exists so that 'storage is down' is never a silent fallback"). The argument is
correct and I used it; it is one class along.

**6.6 — `make mutation-copy FULL=1` does not let you mutate a contract *against its guards*.**
§5. `FULL=1` does make `contracts/` real rather than a symlink, so half the sentence holds, but
the copy has no `tests/` and the contract suites read the contract relative to their own
location. Anyone briefed to prove a contract guard this way will get a green from a mutation the
guard never saw.

**6.7 — the gate figure moves, and by more than the change itself.**
The brief expects 1543/5/167. This session adds two tests to the baseline suite, so the figure
is **1545**. §7 has the run.

**6.9 — two of this change's guards cannot fail `make gate`, and that is not in the brief.**
`Makefile:488-490` runs the battery with `--ignore=tests/contract/test_cp00_candidate.py`
(and `test_cp00_final_state.py`, `test_validate_bootstrap.py`), and `--ignore=tests/checkpoint`.
`test_cp00_candidate.py` contains `DomainErrorEnumParityTests`, which checks the envelope enum
against the catalog and pins the count — a guard directly over the artefact this session
changed, invisible to the gate. It is also already ~64 red at `876e095`, so its summary line
tells a reader nothing. Any session told "run `make gate`" is not told this. Measured:
`grep -n -- "--ignore" Makefile`, and the before/after `FAILED` diff in §3.

**6.8 — everything else held.** The contract's three measured absences (no `securitySchemes`,
no top-level `security`, zero operations carrying their own); `not_found`'s summary verbatim;
`D-8`'s `"frozen": false, "status": "draft_candidate"`; `storage/errors.py:153` carrying
`code = "permission_denied"` as a string on a `ClassVar`; that both sides declared exactly
`aggregate_type` and `required_capability` with no discriminator; `T-3`'s health plane outside
`/api/v1`; `OPERATING_CONSTRAINTS.md` §12 and its three instances; the instance values; and
`W13-BASE`'s single marked exception and the test that counts it.

## 7. One finding for the integrator, not settled here

**`proxy.py:222` is a second `D-7`, and it is the worse of the two.**

```python
if exc.code == 401:
    return DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE,
                       message="the model proxy refused the token")
```

A refused provider credential reported as `dependency_unavailable`, which the catalog pins
**`retryable: true`**, and with no `dependency` detail at all. The storage instance at least had
a code whose status was merely misattributed; this one tells the caller to retry a condition
that will not clear, and the catalog's own rule is that `retryable` is authoritative and a
caller never second-guesses it from the status.

`dependency_credential_refused` is deliberately shaped to take it: generic name, `dependency`
detail key, `retryable: false`. I did not take it, because `R-3` ruled on the storage collision
and this is an unruled behaviour change in the analysis lane touching a flag callers act on.
**It wants a `D-` row and an owner's eye, not a session's initiative.**

Found by `grep -rn "401" src/auditmanager/analysis/` while checking whether a generic name had a
second consumer — which is the whole reason the name is generic.

### Smaller, and also not mine

`StorageBucketMissingError` carries `validation_failed` (**422**, category `validation`,
`field`/`constraint`) for *"the configured private bucket does not exist"* — a server
configuration fault reported to the caller as a validation failure on their request. It is the
same misattribution `D-7` describes, one class along in the same file, and it is **not** a
precedent for the choice in §2; I noticed it while reading and left it alone.

## 8. For stage 2 (`W13-API`) and `W13-CONF`

1. **The scheme is `http`/`bearer` with no `bearerFormat`.** FastAPI's `HTTPBearer` generates
   exactly `{"type": "http", "scheme": "bearer"}` — it will not emit `bearerFormat` unless asked,
   so the conformance comparison has nothing to reconcile. `auto_error` is the thing to watch:
   FastAPI's default raises its own `HTTPException`, and a bare 403 or a `{"detail": ...}` body
   would violate the one-failure-shape rule this document has held since CP-00. **`401` is
   `authentication_required` in an `ErrorEnvelope` with `X-Correlation-Id`, and nothing else is
   acceptable.** The same trap `W13-BASE` §10.3 names for `RequestValidationError`.
2. **Declare the requirement once, at the router or the app, not twelve times.** The contract
   does, and `test_every_operation_requires_the_bearer_scheme` resolves effective security the
   way the spec does — so a FastAPI document that declares it per-operation still conforms. What
   does not conform is any operation that ends up with no requirement, or with an empty
   alternative.
3. **The health plane carries no dependency.** `T-3` puts it outside `/api/v1`, on its own port,
   and the deploy script and the proxy poll it. If it inherits an app-wide dependency it stops
   answering and wave 14 discovers that in a deployment.
4. **Record 31 is still the only record you may change, and it has already been changed.**
   Its `exception.status` is `"taken"`. A *second* difference in that record is now a failure of
   the wave like any other — the exception was spent, not made permanent.
5. **`test_the_baseline_makes_no_authorization_claim` will go red the moment the journey
   authenticates**, which it should. Change it and the README paragraph together, in the same
   commit, and say which era the records then belong to.
6. **The frontend has no branch for 401.** `web/src/shared/api/errors.ts` narrows to ten
   `PC01_ERROR_CODES`, and `authentication_required`, `permission_denied` and
   `dependency_credential_refused` are all outside it. That is correct by construction — the
   narrowing is documented as "a code outside the list but inside the catalog is still an
   `ApiError`" — but 401 is now reachable on every operation, and a generic `ApiError` toast is
   not what an expired credential should produce. A UI decision, not a contract one, and it is
   not made here.
7. **`dependency_credential_refused` is a 500 that is not `internal_error`.** Anything that
   maps "5xx → internal_error" at the edge will erase it. `envelope_response()` already reads
   the status *from* the code, which is the behaviour to preserve.

## 9. Scope

Written: `contracts/**`, `web/openapi/**`, `web/FRONTEND_LOCK.json`, the generated client,
`src/auditmanager/shared/errors/**`, `tests/characterization/w13_baseline/**`, this file — and,
by necessity, `src/auditmanager/storage/**`, `db/migrations/versions/20260910_0002_pc01_schema.py`,
three files under `tests/contract/**`, `tests/integration/api/test_operation_surface.py`,
`tests/integration/storage/test_unavailable.py` and
`web/tests/contract/seam-operations.contract.test.ts`. §6.2 is the argument for each.

**Nothing under `src/auditmanager/api/**`.** Stage 2 writes the API layer; this session wrote
the document it will be checked against and did not anticipate a line of it.

No dependency added — `pyproject.toml` and `web/package-lock.json` are untouched, and
`agent/w13-pin`'s FastAPI pins were deliberately not carried into this branch. No bytes added
under `fixtures/synthetic/ar/**` or `fixtures/validation/PC-02/**`; nothing under `fixtures/` at
all. No tag, no push, no merge to `main` or `dev`.
