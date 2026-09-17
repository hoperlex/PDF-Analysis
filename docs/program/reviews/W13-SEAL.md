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
