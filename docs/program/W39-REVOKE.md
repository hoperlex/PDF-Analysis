# `W39-REVOKE` — revocation and password change

**`R-26`'s first half, executed on 2026-09-23 from `3fd5c17`, on branch `agent/w39-revoke`.**
Rate limit and lockout are wave 40's. This is the half that cannot be added later.

---

## 1. What is revoked, and how a request finds out

### The problem, stated exactly

A credential minted by `auditmanager.api.security` is `am1.<payload>.<tag>`: a JSON payload
and an HMAC-SHA256 tag over it, under a key derived from `AUDITMANAGER_API_TOKEN`. Verifying
it costs one HMAC and reaches for nothing. **That is what made it fast and that is what made
it irrevocable.** Between issuing one and its `exp` passing, the only lever was rotating the
deployment secret — which invalidates *every* credential including the operator's own, and
needs a redeploy.

`0006_app_user`'s own docstring already names the shape of this, about the thing it replaced:
a credential in the environment "cannot be created, changed or revoked without a redeploy".
Wave 34 fixed creation and change. Revocation was left, and the `CredentialPort` docstring
said so in as many words: *"the port cannot … revoke a credential"*.

**The general fact, which decides everything below: a statement that can be taken back cannot
be verified by reading only the statement.** Revocation of an already-issued stateless
credential requires server-side state read at verification time. There is no clever encoding
that avoids it. So the design question is not *whether* to read, but **what** to read and
**how much** of it.

### What is revoked: an account's credentials, all of them, never one token

`app_user` gains **`token_epoch`** — an integer, starting at 1, never 0, `CHECK (>= 1)`. Every
credential carries the epoch it was minted under, in the payload as `ver`. On every guarded
request the seam reads that account's *current* epoch and refuses a credential that disagrees.

**Raising the column by one invalidates every credential ever minted for that account**, in
one statement, immediately, everywhere, with no list of tokens kept anywhere.

And a second column, `token_epoch_updated_at`: the epoch is a number nobody can date, and the
question an operator asks after an incident is always *when, and to whom*. It is separate from
`password_updated_at` because a password change moves both and a revocation moves only this
one, and collapsing them would make two events with different remedies one record.

### How a request finds out

One `SELECT token_epoch FROM app_user WHERE user_uid = :user_uid` — a primary-key lookup
returning one integer — **after** the signature and the expiry have been checked and before
the handler runs. The order is deliberate: a forged credential must not cost a database round
trip, or an unauthenticated caller can make the deployment query on demand.

`None` — no such account — is a **refusal**, never a permissive default. That is what makes
deleting a row a revocation, which it was not before: a credential for a deleted account went
on working until its expiry, because nothing on the request path ever asked whether the
account was still there.

### The three alternatives, and why each lost

| Design | Why not |
|---|---|
| **A denylist of token identities (`jti`)** | needs a second table that grows with traffic and must be swept; expresses "this one token" when the only question anybody asks is "everything this account holds"; and **cannot revoke a credential minted before the denylist existed**, because such a credential carries no identity to list. The counter revokes credentials it has never seen. |
| **A shorter lifetime** | does not revoke. It bounds the damage window, and it cannot be applied to a credential already issued — which is the whole problem. |
| **Rotating `AUDITMANAGER_API_TOKEN`** | signs out everybody including the operator, needs a redeploy, and is the exact property `0006_app_user` criticised in what it replaced. |
| **Caching the epoch with a short TTL** | buys back the per-request read at the price of the property being bought: a revocation that takes effect *in a little while*. The request **after** a revocation is refused, not the one after that. |

### What it costs, said plainly

The seam was free — one HMAC, no I/O. **It is not free any more.** One indexed single-column
read per guarded request is the entire price of revocation, and it is not avoidable by
cleverness. Every request on this surface already performs several database reads behind its
handler; this one is smaller than any of them and it is the only one that can refuse.

### A restart is not revocation, and nothing here leans on one

`web/src/app/bff/session/store.ts` is process memory, so restarting the web container already
signs everybody out. **That is not revocation**: it is a side effect of one deployment topology,
it does not survive a second replica, and an operator ending a pilot must not have to reason
about which processes have been restarted since. The epoch is a column. It gives the same
answer after a restart, after a redeploy, and to every replica at once.

### Deploying this change is itself a global revocation

Every credential minted before it carries no `ver` at all, and an unreadable epoch is refused
by the same path that refuses an unknown format version. **Everyone signs in again, once.**
That is the correct direction for a change whose purpose is that credentials can be taken away,
and it is written into the migration's log line rather than left to be discovered.

### Decision-event revocation is a different thing, and I checked

`DecisionEventType` declares `revoke`, and the contract says in two places that it is *"declared
so PD-01 revocation stays implementable without a schema change; no PC-01 client offers it."*
**That is a reviewer withdrawing a verdict on a finding.** It is an append-only decision-ledger
event about an *audit finding*; this wave is about *credentials*. Measured rather than assumed:

```
grep -rn "revoke" contracts/domain/v1/*.json contracts/api/v1/openapi.json
```

`DecisionEventType.enum` carries `revoke` beside `accept`, `reject` and `comment`; nothing in
`contracts/**` was touched by this wave except `contracts/api/v1/openapi.json`, and the two
concepts share no code, no column, no enum and no operation. Nothing here makes PD-01 revocation
any more or less implementable than it was.

---

## 2. Where revocation is triggered from, and where it deliberately is not

Two triggers, and **only one of them is a network surface**.

**Password change — `POST /auth/password`, `changePassword`.** The two share a mechanism, which
is why they are one wave: the epoch is raised **in the same UPDATE** that writes the new digest.
Two statements would leave a window in which the password is new and the old password's
credentials still work, and that window is the whole of what this closes. A password change
that does not invalidate the credentials minted under the old password is a password change in
name only.

**Operator revocation — `python -m auditmanager.access.revoke`, and no operation at all.** Ending
a pilot is an operator's action taken on the deployment. Publishing it as an operation would
require deciding **who may revoke whom**, and this system has no roles — `permission_denied` sits
in the catalog precisely because nothing raises it, and `api/security.py` says in as many words
that it decides *who* the subject is and not *what they may do*. An operation every authenticated
reviewer could call to revoke an account is not a smaller decision than adding roles; it is the
same decision taken by accident.

**So the new surface is exactly one operation, and `R-29`'s reserved list is untouched**: nothing
here publishes the stand on any interface, changes a default account, or exposes a surface that
is not exposed today beyond the one operation this brief commissions.

A reviewer who wants to invalidate their own credentials changes their password, which revokes
them as part of the same statement. An operator who wants to end the pilot runs the command.

### The command's shape, and the two defaults that were refused

```
PYTHONPATH=src .venv/bin/python -m auditmanager.access.revoke --login admin
PYTHONPATH=src .venv/bin/python -m auditmanager.access.revoke --everyone
```

`--login` and `--everyone` are mutually exclusive and **one is required**. Neither available
default is defensible: revoking everybody by default is a command that ends the pilot when
somebody presses up-arrow, and revoking nobody by default is a command that reports success
having done nothing.

Three exit statuses, and the middle one is the point: `0` revoked something, **`1` was
well-formed and matched nothing**, `2` could not act. Reporting "no such login" as success would
make `--login typo` indistinguishable from a revocation that happened.

---

## 3. `changePassword`, and the two decisions inside it

**It answers with a credential, and that is the revocation being visible rather than a
convenience.** Changing the password revokes every credential minted under the old one —
*including the one this very request presented*. A `204` would leave the caller holding
something already dead, with no way to tell that from a failure. So the answer is the
replacement: minted after the change, under the new epoch, the only credential this account
now accepts.

**The account is the credential's, never the body's.** There is no `login` property in
`ChangePasswordRequest` and there will not be one: the subject comes from
`CurrentSubject`, which the seam published after verifying it. A login in the body would be an
operation one reviewer could aim at another, and the only thing between that and a working
impersonation would be a check nobody has specified.

**No schema was added for the response.** `changePassword` answers `IssueTokenResponse`, because
a credential and its lifetime is one shape and the document already had a name for it.

**No error code was added** (`D-18`). A wrong current password is the catalog's
`authentication_required` — the same refusal a missing credential gets, because "this deployment
does not accept this" is one fact. A new password equal to the current one is `validation_failed`:
that is a statement about the request rather than about who the caller is, and it is only ever
reported to somebody who has already proved the current password. The `403` is declared like every
other authorized operation's, because `tests/contract/domain_p02/test_openapi_document.py`
requires it and the reason it requires it is right — a generated client needs a typed shape for
`permission_denied` on every operation behind the seam. Nothing raises it, here or anywhere.

### The refusal order is the security property

1. the **current** password is proved first, so nothing about the new one — not even that it was
   malformed — reaches somebody who has not shown they may change it;
2. the new password is refused when it is the current one;
3. the new digest is derived, which is where the mechanical bounds apply and raise;
4. **one** UPDATE writes the digest, clears `is_default_credential` and raises `token_epoch`.

Step 4 also closes something `0006_app_user`'s own column comment demanded and nothing implemented:
*"Whoever changes the password sets this to false in the same statement."* Until this wave nothing
could change a password at all, so the sentence described an obligation with no code under it.

---

## 4. Where the port travels, and why it is on the router

The authorization seam is assembled in `api/app.py::_assemble`, which is handed **a router and an
environment** and nothing else. The epoch read needs a port.

`bootstrap/composition.py` is a single-owner hotspot and is in this brief's
`forbidden_hotspots`, so `Application` could not gain a field — and a seam that depended on a
field being added there would be a seam nobody could wire without taking that lock.

So the port travels on the router, which is the object that already went through the composition
root holding it. `Router` stopped being `Router = APIRouter` and became an `APIRouter` subclass
carrying `credentials: CredentialPort | None`. `build_router` already receives that port and now
keeps it.

**`None` refuses.** `create_documentation_app` builds a router with no ports at all; its
authorization dependency refuses every guarded request rather than admitting one, which is the
same bargain the module already strikes for a missing deployment secret. It can serve no request
anyway.

---

## 5. The reseal, item by item

**Surface: 14 paths / 17 operations / 50 schemas → 15 / 18 / 51.** One path, one operation, one
schema (`ChangePasswordRequest`). No response schema, no error code, no parameter.

| Document | What moved |
|---|---|
| `contracts/api/v1/openapi.json` | `/auth/password` (after `/auth/token`), `ChangePasswordRequest`, and an `info.description` block for `R-26`. The previous block's closing sentence *"The surface moves to fourteen paths, seventeen operations and fifty schemas"* was rewritten as a delta, the way `W34-CONTRACT`'s was, because a reseal's own arithmetic stops being true at the next reseal. |
| `web/src/shared/api/generated/*.ts` | 4 files, regenerated with `npm --prefix web run api:generate`; `api:verify` → `OK - 18 operations` |
| `web/openapi/openapi.json` | the mirror, byte-identical to the contract |
| `web/FRONTEND_LOCK.json` | six digests recomputed, counts 15/18/51, `content_commit` `2e6b409`, a new `commit_note` paragraph |

### The lock's digest, verified against the contract's bytes before the gate ran

```
$ sha256sum contracts/api/v1/openapi.json web/openapi/openapi.json \
    web/src/shared/api/generated/*.ts web/package-lock.json \
    web/scripts/generate-api-client.mjs
29b3fa5fa34b561deda9795283e77a0236c154d9bc47db4a2b0282b9d7225fc0  contracts/api/v1/openapi.json
29b3fa5fa34b561deda9795283e77a0236c154d9bc47db4a2b0282b9d7225fc0  web/openapi/openapi.json
8531d10627ebdec407df90195bd650654e12c58a8ff3e68c437908297550a155  web/src/shared/api/generated/client.gen.ts
c19e40cbd4126b1e4ef6c308ce51218ebdf80306845866e1633c5cb5a12533b3  web/src/shared/api/generated/index.ts
758deabe85211575511e8e4d615c0e143f5f69c454a63dda9ebe862bc90c5e28  web/src/shared/api/generated/operations.gen.ts
96c1c01885f6d957b2e4f0f22daf9a9d4dc153782c44e59295ecd55ee9dc075a  web/src/shared/api/generated/types.gen.ts
98691bc83549225d6d94ec53c1fc810a58b12cf74487786638fd007d57fd3b77  web/package-lock.json
787c744d0c97420b0c1c1bd33bcc530d7ce803a21db07a5ef9557de4a02ee123  web/scripts/generate-api-client.mjs
```

All eight equal what `FRONTEND_LOCK.json` records, checked by reading the file back and
recomputing rather than by trusting the write. Before the reseal the lock recorded
`976df5c1492575754394bafc3131f8a42d1951c774279f6ccbbadde25e204619` and the contract hashed to the
same value — so the coupling was intact at `3fd5c17` and is intact now.

---

## 6. The residue

**Measured on this branch, and that is the caveat §4.7 attaches to it**: a count from the branch
that made the change is not the count. The integrator must re-run this on the merged tree.

### The command

```
grep -rInE "seventeen[- ](operations|operation)|fourteen paths|fifty schemas|50 schema|\b17 operations|\b14 paths|\b50 schemas" \
  --include=*.py --include=*.ts --include=*.tsx --include=*.md --include=*.json --include=*.sh . \
  | grep -v node_modules | grep -v '^\./artifacts/' | grep -v '^\./docs/program/reviews/'
```

### What it found, and what happened to each

Thirteen of them were found for me: `tests/contract/api_v1/test_surface_counts_in_prose.py`
reads `src/auditmanager/api`, `infra/deploy` and `web/src` and **reddens on a stale surface
count**, so the first gate run after the reseal named them in one failure. That guard is the
single best thing in this repository's anti-rot machinery and it is why this wave's residue was
cheap.

**What it cannot see is `docs/`, `tests/` and everything else** — and that is where the
interesting ones were.

**Twenty-four statements in fourteen files, repaired in the commit that moved the surface.**

| Where | How many | Found by |
|---|---|---|
| `infra/deploy/README.md` | 3 | the prose guard |
| `infra/deploy/serve.py` | 1 | the prose guard |
| `src/auditmanager/api/README.md` | 2 | the prose guard |
| `src/auditmanager/api/app.py` | 2 | one by the prose guard, one by reading |
| `src/auditmanager/api/health.py` | 1 | the prose guard |
| `src/auditmanager/api/routers/__init__.py` | 2 | the prose guard |
| `src/auditmanager/api/routers/declarations.py` | 2 | the prose guard |
| `src/auditmanager/api/routers/errors.py` | 1 | the prose guard |
| `web/src/app/bff/v1/[...path]/route.ts` | 2 | the prose guard |
| `web/src/shared/api/authorization.ts` | 1 | the prose guard |
| `docs/program/P02_SEAMS.md` | 1 | reading §7 |
| `docs/program/DEPLOYMENT_RUNBOOK.md` | 2 | the sweep above |
| `tests/integration/api/test_served_document_and_health_plane.py` | 2 | the sweep above |
| `web/tests/contract/seam-operations.contract.test.ts` | 2 | one by the sweep, one **by a mutation** |

### Three of them are worth naming individually

**`P02_SEAMS.md` §7 opened with *"Fifteen operations, sealed"* over a table of seventeen.**
It had been wrong since wave 34 and survived wave 38 as well. Nothing could see it: the
prose guard does not read `docs/`, and the thing that *does* check §7 —
`tests/contract/domain_p02/test_seam_register.py` — compares the **table** against the frozen
document and never the sentence above it. So the table could not rot and the sentence could.

**`api/app.py` said *"Twelve of the seventeen operations"* declare their own 422.** Twelve
plus the four it then names is sixteen, which was never the size of this surface; the correct
figure was thirteen, and it is written correctly one directory away in
`test_served_document_and_health_plane.py`. A number whose own arithmetic did not sum, sitting
in the file the prose guard reads most closely — because the guard checks *"N operations"*
against the surface and this one was *"twelve of the seventeen"*, a subset phrase.

**`web/tests/contract/seam-operations.contract.test.ts` said `describe('the sixteen seam
operations')`.** Two reseals stale. It was found by **mutation `W6`**, whose failure output
printed the describe name — not by any sweep, because `web/tests` is deliberately outside the
prose guard's reach (a suite proving a guard can fail has to write the stale spelling down on
purpose).

### One that is not mine to fix

**`docs/program/ALPHA_ROADMAP.md` §3 states the surface as `13 paths / 16 operations / 48
schemas`.** That is **wave 34's** figure: it was already two reseals stale before this wave
began, and wave 38 did not correct it either. `ALPHA_ROADMAP.md` is in this brief's
`forbidden_hotspots`, so it is untouched and handed over. After this wave it should read
**15 / 18 / 51**.

---

## 7. What the `infra/**` change was, and why §4.7 required it

Two kinds of change, in two files, and the second is the one that matters.

**Counts.** `infra/deploy/README.md` ×3 and `infra/deploy/serve.py` ×1 said *"the seventeen
operations"*. The prose guard reddened on all four; they now say eighteen. That is arithmetic.

**`DEPLOYMENT_RUNBOOK.md` §7 gained a subsection, and it is not a count.** The runbook's §7 is
`R-4` — the wipe, and *"what the end of the pilot is, operationally"*. `reset.sh` destroys
documents and rows. **It does not touch credentials**, and until this wave nothing could: every
credential handed out during a pilot stayed valid until its own expiry, and the only lever was
rotating the deployment secret.

So the runbook now carries, in §7 and beside the wipe it belongs with:

* the command, both forms, and what its three exit statuses mean — including that **`1` means
  the `--login` matched nothing**, which is what a typo looks like and must not be read as
  success;
* that running it bare does nothing and exits `2`;
* that **a password change revokes too** — the fact a reviewer will produce without reading
  anything;
* that **deploying `0007_credential_epoch` signs everybody out once**, so an operator meets
  that at the upgrade rather than in an incident;
* a pointer to `python -m auditmanager.access.check`, which is the same operator view from the
  other side.

`OPERATING_CONSTRAINTS.md` §4.7 was written because two runbooks told an operator to hand out
the signing key — a stale instruction that is *followed*. **This is the same rule with the
sign reversed**: a mechanism that answers `R-4`'s standing question and that no runbook names
is a mechanism nobody runs, and "the pilot has ended" would go on being a claim this system
cannot make true. Nothing else in `infra/**` or the runbook was touched — no port, no binding,
no default account, no published surface.

---

## 8. Every premise of this brief I measured and found false

**1. *"`src/auditmanager/access/` — `check.py`, `models.py`, `passwords.py`, `ports.py`. Read
all four first."*** There are **six**: `repository.py` is the largest and most important of
them — it is the only reader and writer of `app_user`, it holds the "a digest never leaves
this module" property, and it is where most of this wave's backend work landed. `__init__.py`
is the sixth. A session that read the four named would have read the boundary's *shape* and
none of its behaviour.

**2. *"`DecisionEventType` already declares `revoke` … say in your report that you checked."***
Checked, and the premise holds — but the brief's framing understates it. It is not merely a
different *thing*; `contracts/domain/v1/state-machines.json` gives it its own semantics
(*"A revocation event withdraws the revoked verdict and the projection moves to pending"*).
The two share no code, no column, no enum member and no operation.

**3. *"the surface is 14 paths / 17 operations / 50 schemas today."*** True, and the only
figure in the brief that was.

**4. *"`api/app.py` … Twelve of the seventeen operations do exactly that. Four cannot."***
Not the brief's sentence but the tree's, and false: thirteen declared their own 422, and
twelve plus four is sixteen, which is not a size this surface has ever had.

**5. *"`P02_SEAMS.md` §7"*** — correct as a path, and the section's opening sentence was two
reseals stale. See §6.

**6. *"Wave 38 found six registers … and 22 stale statements in 10 files."*** Mine were
**twenty-four in fourteen**, and the distribution is the interesting part: thirteen were found
by a guard, and the three that mattered most were found by reading, by arithmetic, and by a
mutation's failure output.

**7. *"`make gate` runs `npm --prefix web run typecheck` before the suite."*** True, and it
earned its place here: it caught an unused import in the new test file before the suite ran.

**8. *"Disk is at 86%."*** It was at **88%** when I started and is at 88% now. No image was
built. One thing did land on it that I did not intend: an `npx vitest` invocation without
`--prefix web` **downloaded vitest 5.0.1 from the registry** rather than using the pinned
3.2.7 — see §10.

**9. *"`tests/e2e/pc01/journey/manifest.json` … that file is yours this wave."*** True, and it
was needed: the conformance guard reddens on a screen the journey does not walk, proved by
mutation `W7`.

**10. The premise under the whole brief — *"no later work reaches backwards to a token already
in someone's browser"*.** True, and stronger than stated. It is not only that later work
cannot reach an issued token; **this** work cannot reach one either. `0007_credential_epoch`
does not revoke old credentials by finding them — it refuses them because they carry no epoch
at all. There was never a way to reach them; there is now a way to make them unusable.

**11. The brief's `allowed_paths` is narrower than the brief's own instructions, in two
places.** The glob list names `web/src/**`, and does not name:

* **`web/openapi/openapi.json`** — the *mirror*, which the brief commissions by name two
  sections earlier (*"the regenerated client and mirror"*) and which
  `npm --prefix web run api:generate` writes whether or not anybody wanted it to. A session
  that took the glob literally could not have resealed at all;
* **`web/tests/**`** — where the brief explicitly sends the session (*"A new screen is added
  to that guard's `SCREENS` list at the end"*, `web/tests/guards/rendered-language.guard.test.ts`),
  and where `SEAM_OPERATIONS` lives, and where a test proving the new screen belongs.

I did the work the brief's body commissions and touched both, and I say so here rather than
leave it to be noticed. `MEMORY.md` already carries *"ownership globs must come from the
tree — three briefs named paths matching nothing"*; this is the same defect with the sign
reversed, a glob that omits paths the brief's own prose requires.

**12. A premise about my own lane, which I found false while acting on it.** The brief says
*"§4.6 … assert on `GATE OK`"*. I did — and the trap fired anyway, one layer further out: a
`nohup make gate &` launched in the background produced a **completion notification with exit
code 0 while the gate was still running its first suite**. The 0 belonged to the shell that
launched it. `GATE OK` was not in the log for another twenty minutes. §4.6 is right and is not
narrow enough: *any* status a harness hands you is about the harness.

---

## 9. The gate

**Twice, both green, and the second is the one that counts.**

```
$ make gate > /root/w39-logs/revoke-gate-final.log 2>&1
$ grep -E "GATE OK" /root/w39-logs/revoke-gate-final.log
GATE OK: battery, foundation, frontend and whitespace all pass
```

Asserted on `GATE OK` in the log and never on an exit code, per §4.6 — and see §8 item 11
for how that rule fired anyway, one layer further out. Both runs were on a tree
`git status --porcelain` reported clean, in lane `gate-w39a`.

| | baseline at `3fd5c17` | at `bca08e7` | at `755c2e4` | delta |
|---|---|---|---|---|
| battery | 2207 / 5 skipped / 169 subtests | 2232 / 5 / 169 | **2233 / 5 / 169** | **+26** |
| foundation | 35 | 35 | **35** | — |
| frontend | 988 in 71 files | 1013 in 72 | **1013 in 72** | **+25, +1 file** |

The battery's own wall clock is worth quoting with the figure: **306 s** on the changed
tree with the host quiet, **330 s** for the first gate, **496 s** for the second — with
`W39-CORPUS`'s `gate-w39b` stack up alongside it and a load average of 15 for the whole run.
§4.6: *a gate that took twice as long as usual is evidence about the machine, not about the
code.* Nothing was re-run on that account because nothing was red.

**Case by case, and nothing was lost.** The first full battery on the changed tree reported
`23 failed, 2184 passed` — and 2184 + 23 is exactly 2207, so no test disappeared; twenty-three
existing ones had to be taught about the epoch. They fall into four groups:

1. **eleven `p02_journey` and seven `composition` tests** built a router from six ports and no
   credential port, so the seam refused every request they made. Each now wires the shipped
   `CredentialAdapter` over its own session factory — the object the composition root wires,
   not a stub;
2. **four count literals** — `len(app.router.routes) == 17` in three composition files and the
   e2e acceptance suite's criterion 1;
3. **one record-shape guard**, `test_the_record_carries_no_credential_material`, whose closed
   field set reported `token_epoch` and `token_epoch_updated_at`. It now also asserts, by name,
   that the four credential columns are absent — which is the thing it was always about and
   which the closed set alone did not say;
4. **one, and it is the one worth reading**: `probe_surface` in `tests/integration/api/driver.py`
   built a bare `APIRouter`, so it carried no credential port and the seam answered `401`
   before any probe's handler ran. **Nine tests** that had staged a `409` or a `500` read
   `authentication_required` instead. The seam was right; the probe had quietly stopped being
   a caller.

The battery took **330 s** against a normal ~306 s, with `W39-CORPUS`'s `gate-w39b` stack up
alongside it for the whole run — §4.6's contention shape, and not enough of one to matter.

The frontend's +25 is one new file, `web/tests/unit/session/change-password.test.ts` (24 cases),
plus one case added to `rendered-language.guard`'s parameterised set by the four new screen
shapes. The battery's +26 is `tests/integration/auth/test_revocation.py` (21) and five cases
added to `tests/integration/api/test_authorization.py`.

---

## 10. Mutation: every guard proved able to fail

**Backend: thirteen cases against `make mutation-copy MUT=/root/w39revoke-mut`.** The copy was
proved to be the imported tree before anything was believed —
`auditmanager.api.security.__file__` → `/root/w39revoke-mut/src/auditmanager/api/security.py` —
and the unmutated copy was baselined green: **92 passed**. `PYTHONDONTWRITEBYTECODE=1`, and
`__pycache__` cleared between cases (§10.2). Every case reverts with
`git show HEAD:<path>`, never by re-editing.

| Case | Mutation | Red |
|---|---|---|
| `G1` | the epoch comparison deleted from `require_authorization` | **6 failed** |
| `G2` | `current is None` treated as permissive | **1 failed** |
| `G3` | `"ver": subject.token_epoch` → `"ver": 1` | **14 failed** |
| `G4` | `payload.get("ver")` → `payload.get("ver", 1)` | **1 failed** |
| `G5` | `change_password`'s UPDATE stops raising the epoch | **2 failed** |
| `G6` | `revoke_credentials`'s UPDATE stops raising it | **2 failed** |
| `G7` | `is_default_credential = false` → `= is_default_credential` | **1 failed** *(after repair — see below)* |
| `G8` | `is_the_same_password` → `return False` | **2 failed** |
| `G9` | the current password is never actually proved | **2 failed** |
| `G10` | the CLI's required-argument group → `required=False` | **1 failed** *(after repair)* |
| `G11` | the CLI's "nothing matched" exit `1` → `0` | **1 failed** *(after repair)* |
| `G12` | the adapter mints under `record.token_epoch - 1` | **1 failed** |
| `G13` | `build_router` drops the credential port | **10 failed** |

The verbatim reds are in `/root/w39-logs/revoke-mut-*.log`, one per case.

### Three mutations died quietly, and that is the finding

**`G10` and `G11` reddened nothing: `20 passed`, twice.** Both mutate
`src/auditmanager/access/revoke.py`, which `tests/integration/auth/test_revocation.py` drives
**as a subprocess** — and the subprocess's `PYTHONPATH` was
`Path(__file__).resolve().parents[3] / "src"`. In a mutation run pytest imports the test module
from the *repository*, so that path pointed at the **pristine** checkout and the subprocess
executed unmutated code. The tests were correct and **could not fail**.

`OPERATING_CONSTRAINTS.md` §10 already records the fix, for the ledger tool, in the same words:
resolve it *test-side* from `auditmanager.__file__` so a mutation run gets the copy. It now
does (`86f493c`), and both cases redden.

**`G7` reddened nothing: `160 passed`.** That one is not an instrument failure — it is a vacuous
assertion of mine. `assert changed.is_default_credential is False` sat beside the epoch check
and read the shared `user` fixture, **whose flag is `False` from the moment it is created**, so
it was true whether or not the UPDATE cleared anything. It is now its own case over an account
created with the flag `True`, reading the row back rather than trusting `RETURNING`
(`3574ed3`), and `G7` reddens.

**All three were found only because a mutation was expected to kill something and did not.** A
coverage report would have counted all three as covered.

**Frontend: seven cases, in-tree against a committed tree, each reverted with
`git checkout --` in a `finally`.** `make mutation-copy` does not provide `web/`, which is
stated in `tests/e2e/test_pc01_journey_conformance.py`'s own docstring. Baselined green first:
**126 passed in 8 files**.

| Case | Mutation | Red |
|---|---|---|
| `W1` | the old session row is not deleted after the swap | `replaces the session…` — `expected 2 to be 1` |
| `W2` | the local "new equals current" check removed | `refuses a new password equal to the current one…` — `expected [ { …(4) } ] to deeply equal []` |
| `W3` | the **deployment secret** forwarded instead of the reviewer's credential | `expected 'Bearer deployment-credential-a1b2' to be 'Bearer minted-token-for-the-reviewer-…'` |
| `W4` | `title="Смена пароля"` → `"Change password"` | the language guard, both cases: `expected [ 'Change password' ] to deeply equal []` |
| `W5` | the lock's recorded contract digest zeroed | `records the digest of every file it names`, and the guard's own can-fail case |
| `W6` | `changePassword` removed from `SEAM_OPERATIONS` | `expected [ 'appendDecision', …(17) ] to deeply equal [ …(16) ]` |
| `W7` | the journey manifest's route path changed | `test_the_journey_walks_every_screen_the_application_offers` + `test_each_route_agrees_with_its_own_page_module` |

`W3` is the one to keep: it is `W37CERT4-3` one operation over, and the guard that catches it
asserts the header's **value** rather than its presence.

### A fourth instrument failure, and it produced a red I nearly believed

The first frontend sweep ran `npx vitest run --root web …` **without `--prefix web`**. `npx`
did not find a local `vitest`, so it **downloaded vitest 5.0.1 from the registry** and ran the
suites under a toolchain this repository does not pin. Four test files failed to parse at all
— *"the content contains invalid JS syntax"* on ordinary JSX in files I had not touched — and
the summary read `4 failed | 1 passed`, which looks exactly like a guard reporting a real
break.

It is §4.6's shape in a third place: **the red was about the instrument.** The tell was that it
named files unrelated to the mutation. Re-run as `npx --prefix web vitest …` — the pinned 3.2.7
— every case reddened precisely and only where it should. It is also why `FRONTEND_LOCK.json`
pins the toolchain in the first place, and it is worth saying out loud that **the pin does not
defend a command that never consults it**.

---

## 11. For the integrator

1. **Merge, then re-measure the residue on the merged tree.** §4.7: a count from the branch
   that made the change is not the count. The command is in §6.
2. **`docs/program/ALPHA_ROADMAP.md` §3 needs `13 / 16 / 48` → `15 / 18 / 51`.** It was stale
   before this wave and is a forbidden hotspot for this stream.
3. **The migration head is `0007_credential_epoch`.** `make migrate` before anything is driven
   against a database from this branch, and **every credential minted before it is refused** —
   any live stand signs everybody out once at the upgrade. That is intended; the migration logs
   a warning saying so.
4. **`DEBT_REGISTER.md`** — `D-66` (the `hmac.compare_digest` mutation that reddens nothing)
   and `D-67` are wave 40's and untouched. I was in that code and did not change the comparison.
   Two rows could be **added** from this wave if the integrator wants them: the roadmap staleness
   above, and the fact that `tests/integration/db/test_app_user_migration.py` derives its
   subprocess root from the test file exactly as `test_revocation.py` did before `86f493c` —
   §10.1 already records that a migration cannot be mutated by the standard copy, so it is a
   known limitation rather than a new defect, but the two are the same shape.
5. **Two paths I touched are outside the brief's `allowed_paths` glob and inside its
   prose** — `web/openapi/openapi.json` (the reseal mirror) and `web/tests/**` (the language
   guard's `SCREENS`, `SEAM_OPERATIONS`, and the new screen's own suite). See §8 item 11.
   Nothing else in `web/` outside `web/src/**` was touched.
6. **Nothing was tagged, pushed, merged, or written to `main`/`dev`.** No rebase: `W39-CORPUS`
   is writing `src/auditmanager/norms/`, which this branch does not touch.
7. **`R-29`'s reserved list is untouched.** No port binding changed, no default account changed,
   no surface was exposed beyond the one operation this brief commissions. `127.0.0.1:31500`
   was not touched and no image was built (disk 88%).
