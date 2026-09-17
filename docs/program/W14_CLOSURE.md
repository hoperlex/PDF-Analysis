# Wave 14 closure: the prototype is a stack, and the wipe is a guard that has refused

Written 2026-09-18 by the integrator. **`make gate` → `GATE OK`, exit 0**, measured by
`W14-PKG` on its own tip (§6) and again by me on the wave-15 tip that contains it.

One stream, `W14-PKG`. Wave 13 made the twelve operations serve HTTP; nothing had ever
**packaged** them. `find . -iname "*Dockerfile*"` found nothing in the tree. After this wave
there is an image, a compose stack with one published port, a proxy that makes the whole
system one origin, and a wipe script that has refused a real database on this host.

## 1. The result

| Path | What it is |
|---|---|
| `infra/deploy/Dockerfile.api` | the twelve operations under uvicorn, plus `T-3`'s health plane |
| `infra/deploy/Dockerfile.web` | `npm ci`, `npm run build`, `next start` |
| `infra/deploy/serve.py` | the entry point — one built application, two ports |
| `infra/deploy/compose.server.yml` | PostgreSQL, MinIO, bucket-init, migrate, api, web, proxy |
| `infra/deploy/proxy/nginx.conf` | `T-2` — the app at `/`, the API at `/api/v1`, one origin |
| `infra/deploy/reset.sh` | `T-5` — the guarded wipe, and the restore of its own dump |
| `infra/deploy/env/alpha.env.example` | the deployment environment — **not `.env`** (§3) |

Brought up with `docker compose --env-file infra/deploy/env/alpha.env -f
infra/deploy/compose.server.yml up -d --build`: five services healthy, and everything
exercised through the **one published port**, 31480. Image sizes measured, not estimated:
api **401 MB**, web **1.21 GB** (`output: "standalone"` would roughly halve the second and
lives in a file that session did not own — recorded as a cost, not hidden).

## 2. The `T-5` wipe, and why it is the load-bearing artefact

`R-4` permits real client PDFs on the alpha server **on condition they are wiped at the end
of the pilot**. That makes `reset.sh` a commitment to the owner, not a convenience.

**Eleven guards, each shown able to fail by deletion rather than by assertion.**
`test_reset_script_refusals.py` reads the `# >>> guard: <name>` markers, produces a copy of
the script with **exactly one block removed**, runs the same invocation, and asserts the
refusal is gone. A message can be emitted by a guard that is unreachable; a deletion cannot
be faked. A meta-test pins the marker count at 11 and asserts each has a case, so a twelfth
guard added without a test fails here rather than during a wipe.

Nothing in that suite can destroy anything, and not by hoping: `docker` is replaced on
`PATH` by a stub that records its arguments and exits 0. The stub is also the instrument —
for guards that run before any connection, **an empty call log is the evidence the refusal
came first**.

**It refused a real database.** Typing this session's own gate-lane database at it:

```
reset.sh: REFUSED: the typed database is not the configured alpha database.
    typed     : audit_w14a
    configured: auditmanager_alpha
```

`audit_w14a` exists on this host with data in it. That is `T-5` demonstrated, not described.
The real run then dumped, verified, dropped, re-migrated, purged and re-initialised; the
restore brought both halves back and the API served the document's bytes at `200`, **sha256
identical to the original fixture**.

## 3. The finding worth more than the stack

**`mc mirror` is not a backup of an object.** The bytes came home with `Content-Type:
application/octet-stream` and no `X-Amz-Meta-Content-Sha256`, and the storage adapter then
refused them — `422 validation_failed`, `constraint = "recorded on every object this adapter
publishes"`. The restored instance **listed the document and 422'd on its bytes**, which is
worse than an empty instance, because it looks recovered.

A dump is therefore three things — `database.dump`, `objects/`, and `objects.attrs` — and
`dump-verified` refuses a run whose sidecar is short or carries an empty digest.

A second bug in the same class: `pg_restore --list /dev/stdin` cannot read a dump `file(1)`
calls valid, so the readback guard **refused a wipe that should have proceeded**. The safe
direction, still a bug — a guard that refuses a good backup is a guard that gets disabled at
two in the morning.

Both were findable only by running the thing. Neither is reachable from a unit test.

## 4. What the brief got wrong, and it would have broken the gate

**"Put the token in `.env.example`" — no.** The Makefile parses `.env` against
`FROZEN_ENV_NAMES`, a strict allowlist of the fifteen names FF-01 §3 freezes, and refuses
every other name. That instruction would have **broken `make gate`** rather than configured
anything, and `api/security.py:33` already recorded that the token is deliberately *"not in
`.env.example` and not on `AppSettings`"*. The channel is `infra/deploy/env/alpha.env`, one
step out; the provider credential is one step further out again, in `env/provider.env`,
which is never passed to `--env-file` and therefore never appears in `docker compose config`.

`AppSettings` gains exactly one field, `api_token`, required at construction — so an
unconfigured deployment has **no application object at all**, rather than a 401 on first
request. Compose carries `${AUDITMANAGER_API_TOKEN:?…}` as a second, independent refusal one
layer further out.

**And the correction that set wave 15's agenda.** The brief said the frontend "has no branch
for 401". The truth was worse: **the frontend sent no credential at all**, on any of the
twelve operations, and had no channel through which one could be supplied. That is not a
missing branch, it is a missing path — and `W14-PKG` correctly declined to fix it from
outside its ownership and named it a `W15-RUN` blocker instead. It was.

## 5. The boundary with `R-1`, stated rather than papered over

Three things stopped at the ruling, and each is a claim about a server, not about code:

- **TLS.** No host name, no certificate, no DNS. A `listen 443 ssl` block naming a
  certificate path that has never existed is a document, not a deliverable. Everything else
  about `T-2` — one origin, a relative base URL, no CORS surface — is independent of TLS and
  is done and proved.
- **`deploy.sh`.** "Run it twice and the second changes nothing" and "a broken build rolls
  back and leaves the previous version serving" are both assertions about a server that has
  a previous version on it.
- **The provider proxy.** Whether it is reachable from the alpha host is still one of the
  open `R-1` items. The stack was driven in `recorded` mode throughout; no model call was
  made and none could have been, since no credential is in the tree.

## 6. The gate, and one operational fact for the deploy host

```
GATE OK: battery, foundation, frontend and whitespace all pass
1726 passed, 5 skipped, 168 subtests passed in 200.24s
foundation 35 passed, frontend 440 passed (35 files)
```

The +33 against arrival was accounted for commit by commit against a detached worktree at
`4a8cf23`, not assumed — the two new files collect 33, the two edited files collect 31 at
both commits.

**The host filesystem was 100% full** at the first `docker compose up` and killed `initdb`
with *"No space left on device"*. More usefully: **MinIO refuses writes under ~1 GB free**,
and the first symptom is a `dependency_unavailable` on `blob_storage` that reads like an
application fault. The deploy host needs headroom, and this is written down so the next
session to see that error does not spend an hour inside the storage adapter.

**Elapsed: 33 minutes wall-clock.**

## 7. What wave 14 hands forward

- The stack is **built and driven, not deployed.** No `R-1` host exists yet.
- The first live browser journey is still owed, and wave 14 named exactly why it could not
  start: no credential path. Wave 15 built one.
- `deploy.sh`, TLS and the provider-proxy reachability are all owner-blocked on `R-1`.
