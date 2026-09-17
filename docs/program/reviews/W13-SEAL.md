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
