# `W40-LIMIT` — a rate limit that recovers, and a lockout with three ways back

**`R-26`'s second half, executed on 2026-09-23 from `ccaeed8`, on branch `agent/w40-limit`.**
Revocation and password change were wave 39's. This is the half that can be aimed, which is
why most of what follows is about bounding it rather than about building it.

---

## 1. They are two different things, and the difference decides everything below

**A rate limit** counts. `app_user.failed_sign_ins` with `last_failed_sign_in_at` is a count
of consecutive **recent** failures for one account. It slows a guesser, it recovers on its
own — the count restarts by itself once the failures stop being recent — and **on its own it
refuses nothing.** Nobody ever has to operate it.

**A lockout** refuses. `app_user.sign_in_blocked_until` is an instant before which that
account's password is **not consulted at all**, so that even the right password mints
nothing. It stops a guesser rather than slowing one.

The two live in the same table and invite being read as one mechanism. They are not, and the
sentence that separates them is this:

> **A lockout a correct password defeats does not stop guessing, because a guess that
> succeeds *is* a correct password.**

That is why a lockout cannot be made harmless. It is a deliberate trade of availability for
confidentiality, and the trade cannot be avoided — only bounded. Everything in §2 is the
bounding.

### The way back, stated as the brief demands

There are three, and **all three are code**. A way back that lives only in a runbook
paragraph is a way back nobody finds at two in the morning.

1. **Time.** `COOLING_OFF_SECONDS` passes. The ordinary one, and it needs nobody.
   **And the first failure after a served block starts a fresh allowance** rather than
   adding to the count that earned the last one. Without that clause a single attempt per
   cooling-off period re-trips the block for ever — a permanent lockout wearing a temporary
   one's clothes, which is the exact thing this section exists to refuse. It is the first
   branch of `_NEXT_FAILED_SIGN_INS` and mutation `L5` is what proves it is load-bearing.
2. **A password change.** `POST /auth/password` clears all three columns in the UPDATE it
   already performs. An account that has just proved its current password is not what the
   brake exists to slow — and this is the way back for a reviewer who is shut out of the
   exchange while still holding a live credential.
3. **The operator.** `python -m auditmanager.access.unlock --login <login>` or `--everyone`.
   Immediate, no redeploy, no restart, and **no HTTP operation**: the surface this wave adds
   is zero.

### And the residual, which the ways back bound and do not remove

It would be dishonest to let "there are three ways back" read as "therefore not a denial of
service". **Under a *sustained* attack the account stays shut**: five requests every five
minutes hold it closed at essentially no cost to the attacker, and ways 1 and 2 help only
against an attacker who stops. §7 is where that goes to the owner.

What is load-bearing instead — and it is the design's real answer for a pilot — is that
**a lockout does not touch a credential anybody already holds.** See §5.

---

## 2. What is counted, and against what key

**Against the account, keyed by the normalised login.** The other two candidates lost, and
one of them lost to a measurement rather than to an argument.

### The address lost because this deployment does not have one

The obvious way to make a lockout un-aimable is to count per *address*, so that a guesser
only ever shuts themselves out. **The API cannot see the caller's address**, and that is a
property of the tree rather than a worry:

* a browser signs in at `POST /bff/v1/session`, which is answered by the Next process; that
  handler builds **a new request** and forwards it to the API through
  `web/src/shared/api/credentialed-forward.ts`;
* that module's header handling is an **allowlist**, and its own comment says what it drops:
  *"Everything else is dropped, including `cookie`, `authorization`, `host` and every
  `x-forwarded-*` the proxy added."*

So every reviewer's sign-in reaches `issueToken` from **one** address — the web container's.
Keying on it would mean one reviewer's five mistakes shut **every** reviewer out, which is
strictly worse than what this wave is bounding. Making it work would mean trusting a
forwarded header the browser can also set, and a rate limit an attacker can reset by
changing a header is a rate limit that protects the honest caller only.

That the catalog forbids `ip` and `ip_address` as detail keys outright is the same judgement
recorded one layer up.

### "Both" lost because the second key is the first one again

With no trustworthy address there is no second key. A pair key `(login, address)` degenerates
to `(login, the web container)`, which is the login.

### The account key is wrong in its own way, and here is the way

Keying on the account is what makes the lockout aimable. It is the cost of the only key
this deployment actually has, and §7 says so to the owner rather than burying it.

Two smaller decisions fall out of the key:

* **An unknown login records nothing.** There is no row to count against, and inventing one
  would be a table an unauthenticated caller can grow without limit. What keeps that path
  indistinguishable from a known one is the derivation it still spends.
* **A candidate the mechanical bounds refuse is counted like any other refusal.** An empty or
  over-long password could not have matched any stored digest, which is what it has in common
  with every other refused attempt; an uncounted refusal is an attempt shape a guesser would
  find and use.

---

## 3. Where the counter lives, and whether wave 39's argument applies

Wave 39 refused an in-memory register on two grounds: a web-container restart already signs
everyone out and *that is not revocation*, and an operator closing a pilot must not have to
guess which processes have been restarted.

**The first ground does not transfer and the second does, and saying which is the work.**

**Revocation and a failure counter fail in opposite directions.** For revocation, memory is
fatal because a restart would **undo the operator's decision** — the thing that must survive
is a deliberate act. A failure counter has the mirror-image failure mode: a restart
**forgets an attacker's accumulated budget**. That costs a bounded amount of protection and
undoes nothing anybody decided, and an attacker has no way to cause a restart. So wave 39's
first argument, applied here, is genuinely weaker than it was there.

**What makes it a column is the lockout, not the counter.** A lockout is a refusal state
somebody has to be able to **see** and **clear**. In memory the only way to clear it is to
restart the API — and *"restart something and hope that was the process holding it"* is
precisely the reasoning wave 39 refused, arriving by a different road. A second replica makes
it worse in both directions at once: N replicas mean N times the allowance and an unlock that
reaches one of them.

**And once the lockout is durable the count must be too**, because the count is the only
evidence the lockout was ever earned.

So: the same conclusion as wave 39, for a different reason, and the reason is worth having
written down because the next state somebody wants to keep may fail in the first direction
rather than the second.

### One consequence that had to be paid for, and a stale sentence it produced

`CredentialAdapter.issue` opened a **read** session. It now opens a **write** one, because
`authenticate` records a refused attempt and clears the record on a successful one, and the
caller owns the transaction: a read session discards both on the way out, so the brake would
be applied **in the log and nowhere else**. Mutation `L14` is that sentence as an assertion.

And the adapter's own docstring said, in as many words:

> **Authenticating writes nothing.** No session row, no last-login column, **no attempt
> counter.**

The third of those is exactly what this wave adds. The paragraph is replaced rather than left
standing beside the code that falsified it — `OPERATING_CONSTRAINTS.md` §4.7, in the module
that holds the credential, which is where the last one of these was found too. The first two
clauses are still true and are the load-bearing half; they are kept and said to be kept.

---

## 4. What a limited caller sees, and the catalog argument for the code

**`401 authentication_required`, in an `ErrorEnvelope` byte-identical to the one a wrong
password gets apart from `correlation_id`.** No new code, no `Retry-After`, no hint.

### The catalog argument, in the order `D-13` made it

`429` has no code in this catalog. That is a fact to reason from:

1. **A 23rd code is the owner's, not this wave's.** `internal_mapping` rule 4 —
   *"Giving a recurring internal reason its own stable external code is a deliberate change
   to this catalog under the versioning policy, not an edge-local or provider-local
   decision."* `D-13` closed the same way: it recorded **dependency-misconfigured** as a
   candidate and did not propose a reseal. `contracts/domain/v1/error-codes.json` is also a
   `forbidden_hotspot` for this stream, and those two facts agree.
2. **Borrowing a code that means something else repeats `D-7` while citing `D-13`.**
   `cost_budget_exceeded` is the tempting one: `409`, category `policy`, *"An explicit product
   or operational policy refused the operation"*, and its safe detail key is `budget_scope`.
   Its summary says **cost or token budget**, and nothing here is a cost or a token budget.
   `D-13` rejected `dependency_credential_refused` in exactly these words — *"nothing refused
   a credential"* — and this is the same move.
   `dependency_unavailable` fails for its own reason: it is `retryable: true` and about an
   adapter, and nothing here is transiently unavailable.
3. **`authentication_required` is not a fallback; it is the correct code.** Its summary is
   *"No valid authenticated subject was presented. The response carries no hint about the
   addressed resource."* Both clauses are exactly true of a shut account: no subject was
   established, and the response must carry no hint.
4. **`retryable: false` is right and is the part worth checking.** The catalog says
   *"retryable is authoritative. A caller never infers retryability from the HTTP status or
   the message text."* Retrying **this request** — the same login and the same password —
   never succeeds, whether the password was wrong or the door is shut. `retryable: true`
   would tell an automated client to do the one thing that both wastes its time and spends
   the account's next allowance.

### And the stronger form: even a `429` would not be used here

This is the part that matters more than the catalog arithmetic. `issueToken` answers **one
refusal for every cause** — unknown login, wrong password, a login this deployment would
never have stored — because two answers let anyone with the sign-in form enumerate accounts.
**A distinct code for "shut" would say: this account exists, *and* somebody is attacking it
right now.** That is the enumeration oracle the operation already refuses to be, with a
progress bar.

So the absence of a `429` in this catalog is not a constraint being worked around. It
coincides with what this operation should do anyway, and if the code existed this operation
still would not emit it.

### Three consequences carried through the whole path

* **The timing is flat.** The blocked path spends `spend_a_verification` — the same
  derivation the unknown-login path already spends. A cheap refusal there would answer a
  *better* question than the original oracle: not merely "does this account exist" but "is it
  under attack right now". `ports.py` states the obligation as *"comparable work on both
  paths"*; there are four paths now and the sentence is unchanged. Mutation `L8`.
* **No header tells a caller when to come back.** `Retry-After` is the same disclosure one
  layer out.
* **The screen states the policy and never the state.** `signInRefusalMessage('credentials')`
  gained one Russian sentence saying that repeated failures pause sign-in for a while and
  that waiting is the answer. It is **public knowledge about nobody** — rendered on every
  credentials refusal, whether or not the account in front of it is anywhere near its
  allowance. Without it a reviewer who mistypes five times and then types their real password
  concludes their password is broken, and the screen is the only place that can be said.
  **No fifth `SignInRefusal` value was added**, and could not have been: the API answers a
  shut account exactly as it answers a wrong password, so the BFF cannot tell them apart —
  and must not want to.

---

## 5. Does it interact with the epoch? No, and the "no" is the `R-29` property

A **locked account** and a **revoked credential** are different states acting at opposite
ends of a credential's life:

| | what it refuses | who moves it | how it ends |
|---|---|---|---|
| `token_epoch` (W39) | **presenting** a credential | a password change, or an operator | never; it is a deliberate act |
| `sign_in_blocked_until` (W40) | **minting** a credential | consecutive failures, by itself | by itself, and by two levers |

**A lockout does not touch a credential anybody already holds, and that is the single
property that keeps it from being a weapon.** If shutting an account also raised its epoch,
an unauthenticated caller could **sign out a reviewer who is working** by typing wrong
passwords at their login — a caller who never had access taking it away from one who did,
which is `R-29` clause 2 in one sentence. It does not, and mutation `L10` adds the epoch
increment to prove the guard sees it.

It also runs the other way: revoking an account does not shut it, so `revoke` is not an
unlockable lockout, and `unlock` does not undo a revocation.

**Can a caller tell the two apart?** No, and deliberately. A revoked credential gets
`401 authentication_required` on a guarded request; a shut account gets the same on the
exchange. They are told apart by the **operator**, through `access.check`, `access.unlock`
and the deployment log — never by the caller, for the reason §4 gives.

**And this is the practical answer to the residual in §1.** Under a sustained attack on a
login, anybody already signed in keeps working: their credential is untouched, and
`changePassword` — which is guarded, is not rate-limited, needs the current password, and
mints a fresh credential while clearing the brake — lets them stay signed in indefinitely.
The attack denies **new** sign-ins and nothing else.

---

## 6. The contract did not have to move, and here is why that is not luck

**Nothing in `contracts/**`, the generated client, the mirror or `web/FRONTEND_LOCK.json`
was touched.** The surface is still **15 paths / 18 operations / 51 schemas**.

The previous half had to reseal because *a password change must return a credential*: there
was a new operation and a new request schema, and `D-18`'s four-file coupling applied. A rate
limit needs none of that, and the test is a simple one: **does any byte a client can see
change?**

* no operation is added — the lever is a shell command, exactly as revocation's is;
* no request or response property is added;
* no error code is added — §4;
* no header is added — deliberately, §4;
* the only observable difference is **which** of two already-declared outcomes `issueToken`
  produces for a given body, and the document already declares both.

A reseal would have meant claiming the surface had moved when it had not, and `D-18` exists
because that coupling is expensive to get wrong in either direction.

**The migration head moved**: `0007_credential_epoch` → **`0008_sign_in_throttle`**, and
`db/migrations/README.md`'s head table moved with it. Unlike `0007`, **deploying this one
locks nobody out** — every existing account starts with a clean count and no block — and the
migration says so in its own log line, because the two land close enough together to be
confused.

---

## 7. `R-29`: what I shipped, and the two things I stopped at

`R-29` stops at *"anything that changes who can reach the system, or exposes something that
was not exposed"*, and its own text settles the first question: **`R-26` is a ruling, and
building what it rules is execution.** The owner was polled and took the wider option, in
which the word *lockout* appears. A lockout that denies sign-in after repeated failures is
what that word means.

So the ruling's own content is not what I stop at. What I stop at is the choices **the ruling
did not make**, and I resolved each in the least-exposing direction available:

| choice the ruling did not make | what I did | what the other branch would have been |
|---|---|---|
| permanent or bounded | bounded, self-clearing, with an operator lever | an operator-only release — an **unbounded** denial of service |
| does it reach issued credentials | **no** | an unauthenticated caller could sign out a working reviewer |
| is it published as an operation | no — a shell command | deciding *who may unlock whom*, which is the role model `T-6` forbids inventing here |
| does the refusal say what it is | no — the exchange's one answer | an enumeration oracle with a progress bar |

### And here is the residual I am flagging rather than shipping

**The account an unauthenticated caller can hold shut is `admin`.** Its login is published in
`0006_app_user`'s docstring, in `access/__init__.py`, and in `DEPLOYMENT_RUNBOOK.md`. With one
account in the pilot, *"shut the owner's account"* and *"shut the installation's sign-in"* are
the same sentence, and the ways back in §1 bound the damage without removing it.

Two things would change that, and **both are `R-29` clause 2 by name, so I did neither**:

1. **rename or replace the seeded account** — *a default account changed*;
2. **restrict `/api/v1/auth/token` at the proxy** to known addresses — *a port binding, and a
   published surface narrowed*.

`infra/**` is untouched and `127.0.0.1:31500` was not touched. This is a decision for the
owner, stated here in one place, and the alpha is shippable without it: a reviewer who is
already signed in is unaffected, and an operator has a one-line lever.

---

## 8. Every premise of this brief I measured and found false

**1. *"Disk 87% — do not build images."*** It was **91%** when I started — `102G` used of
`119G`, `df -h /` — and is 91% now. The instruction is right and the figure is four points
low, in the direction that matters. No image was built.

**2. *"`src/auditmanager/access/` — `check.py`, `models.py`, `passwords.py`, `ports.py`,
`repository.py`, `revoke.py`, `README.md`. **Six files**."*** That sentence **names seven
items** and the directory holds **eight**. `__init__.py` is the eighth and it is not a stub:
78 lines, and the only place the boundary's whole story is told in one piece. The number is
wave 39's — its report said *"there are six"* correctly, **before `revoke.py` existed** — and
this brief carried the six forward while adding a name to the list. A count copied across a
wave boundary is exactly `D-23`'s shape, in a brief instead of in the tree.

**3. *"Baseline at `ccaeed8`: battery 2265 / 5 / 169, foundation 35, frontend 1013 in 72
files."*** **All four true**, and the only figures in the brief that were. Checked by
measuring the delta rather than by re-running the base battery, because one measurement per
lane: `pytest --collect-only` with the canonical ignores in a detached worktree at `ccaeed8`
gives **2235** excluding `tests/integration/foundation` (which refuses `--collect-only`, by
its own `P1-QA-00` guard, with *"Collection is not evidence"*); the same command on this
branch gives **2267**. `+32` is this wave's suite exactly, and `2265 + 32 = 2297` is what the
gate reported.

**4. *"`D-66` is not yours — `W40-GUARDS` has the fail-closed default and
`hmac.compare_digest`. **You will be in that code.**"*** **I was not in that code, and the
premise that this task lands in the seam is the one substantive thing the brief got wrong
about the work.** `src/auditmanager/api/security.py` is untouched, and so is every other file
under `src/auditmanager/api/**`. The whole of the rate limit and the lockout sits behind
`credentials.issue(...)` returning `None`, which the router already turns into
`authentication_required`. Neither `D-66` guard's subject moved, nothing needs coordinating
with `W40-GUARDS` through the integrator, and the two streams do not share a file.

**5. *"`POST /auth/token` → `issueToken` is your subject."*** True as a description of what a
caller sees and **incomplete in a way that decided a design question**. The operation itself
did not change a byte. The subjects are `UserRepository.authenticate` and
`CredentialAdapter.issue` — and `changePassword`, which the brief's framing excludes and
which **had to** change, because clearing the brake is one of the three ways back and it
belongs in the UPDATE that already proves the current password.

**6. *"Surface is 15 paths / 18 operations / 51 schemas."*** True, measured off
`contracts/api/v1/openapi.json`, and still true: nothing resealed.

**7. *"`allowed_paths` … `docs/program/W40-LIMIT.md`"* — narrower than the brief's own
instructions, in two places**, which is precisely what `W39-REVOKE` reported one wave ago and
what `MEMORY.md` already carries as *ownership globs must come from the tree*:

* **`web/tests/**`.** The brief's method rules require every guard to be proved able to fail.
  `web/src/**` is in the globs and holds no tests, so a screen change the brief's own
  paragraph invites (*"what does a limited caller see"*) could not be guarded from inside the
  glob. One case was added to `web/tests/unit/session/sign-in-screen.test.ts`;
* **`docs/program/DEPLOYMENT_RUNBOOK.md`** — not in `allowed_paths` and **not in
  `forbidden_hotspots` either**. The brief says *"Say what the way back is"*, and
  `OPERATING_CONSTRAINTS.md` §4.7 says a document that tells an operator **what to do** with a
  changed value lands in the same commit. A lockout whose way back exists only in a Python
  docstring is a way back nobody finds at two in the morning, and this is §4.7 with the sign
  reversed — exactly the argument wave 39 used for the same file. §12 lists what I added.

**8. *"`make gate` … then read the log for `GATE OK`."*** Followed, and §4.62's trap did not
fire — but **a smaller one in the same family did, to me, and it is worth recording.** A
watcher waiting for the gate to finish grepped for `passed in`, which matched the
**foundation** suite's line from six minutes earlier and reported the gate done while the
battery was at 88%. §12's *"a query that shares an assumption with the thing it measures"*, in
the instrument I built to watch the instrument. The fix was to wait on the process, not on the
log.

**9. *"`__pycache__` validates by mtime in whole seconds … check the subprocess's
`PYTHONPATH`."*** Both acted on, and **the second earned its place**: `L11`–`L13` and `L15`
mutate `access/unlock.py` and `access/check.py`, which this suite drives as subprocesses, and
all four reddened. That is the positive proof wave 39 lacked — the helper derives its
`PYTHONPATH` from `auditmanager.__file__` rather than from the test file, so the subprocess
executed the mutated copy.

**10. *"when a mutation reddens nothing, establish whether the guard is weak or the mutation
insufficient and say which."*** One did. **It was both**, and §10 is the answer.

**11. *"`D-70` … its provider is a stub, so nothing there can run an analysis anyway."***
Not measured. `127.0.0.1:31500` was not touched and nothing in this wave needs it.

---

## 9. The gate

```
$ make gate > /root/w40-logs/limit-gate.log 2>&1
$ grep -a "GATE OK" /root/w40-logs/limit-gate.log
GATE OK: battery, foundation, frontend and whitespace all pass
```

Asserted on `GATE OK` **in the log file**, never on an exit code and never on a completion
notification — §4.62. `git status --porcelain` was empty before the run and after it. Lane
`gate-w40a`, ports `56200 / 59800 / 59801`, database `audit_w40a`, bucket
`auditmanager-gate-w40a`, all six set in a `.env` copied from `.env.example`.

| | baseline at `ccaeed8` | at `dc9b09b` | delta |
|---|---|---|---|
| battery | 2265 / 5 skipped / 169 subtests | **2297 / 5 / 169** | **+32** |
| foundation | 35 | **35** | — |
| frontend | 1013 in 72 files | **1014 in 72** | **+1** |

**Case by case, and nothing had to be taught anything.** This is the unusual part and it is
the same fact §6 is about: the whole change is behind one port method's `None`, so **no
existing test moved** — no count literal, no fixture, no driver. Wave 39's equivalent run
reported `23 failed` on its first battery and had to repair twenty-three tests. This one was
green on the first full run.

* the battery's `+32` is `tests/integration/auth/test_sign_in_throttle.py` alone
  (32 at the gate; **33** after §10's repair added the thirty-third);
* the frontend's `+1` is one case in `web/tests/unit/session/sign-in-screen.test.ts`;
* `+0` files on the frontend, because the case joined an existing suite.

Wall clock: the battery took **364.74 s** against wave 39's quiet-machine **306 s**, with
three other lanes' container stacks up (`gate-b0`, `gate-w39a`, `gate-w39b`, plus
`auditmanager-w19a`) and a load average around 3. §4.6: a gate that took longer than usual is
evidence about the machine. Nothing was red, so nothing was re-run on that account.

The typecheck ran inside the gate and passed — `✓ the compiler runs inside the gate, not only
in a command nobody runs there > typechecks web/ clean 3501ms`, §4.65.

### The second gate, and it is the one that counts

§10's repair added a thirty-third case, so the figures above describe `dc9b09b` and not the
tree being handed over. The gate was run again on `687bfa2`, from a `git status --porcelain`
that was empty:

```
$ make gate > /root/w40-logs/limit-gate-final.log 2>&1
$ grep -a "GATE OK" /root/w40-logs/limit-gate-final.log
GATE OK: battery, foundation, frontend and whitespace all pass
```

| | baseline at `ccaeed8` | **at `687bfa2`** | delta |
|---|---|---|---|
| battery | 2265 / 5 skipped / 169 subtests | **2298 / 5 / 169** | **+33** |
| foundation | 35 | **35** | — |
| frontend | 1013 in 72 files | **1014 in 72** | **+1** |

`365.38 s` for the battery against `364.74 s` for the first run — the same machine, and the
difference is the thirty-third case.

### A third instrument trap, in something built to watch the instrument

§8 item 8 records one. There were two more of the same family, both mine, both costing only
time — and the third is the one worth copying out:

**`while pgrep -f "make gate"; do sleep; done` never terminates, because `pgrep -f` matches
the watcher's own command line.** The watcher waits for itself. Four of them ran to their
timeouts reporting *"still running"* over a gate that had printed `GATE OK` minutes earlier —
a status which, taken at face value, is §4.62 exactly: **a harness reporting about the
harness.** It was caught by reading the log, which is the same instruction that catches the
other two. (And `pkill -f` on that pattern kills the shell issuing it, for the same reason.)

All three are one sentence: **an instrument built to watch an instrument is an instrument,
and none of them is evidence. The log file is.**

---

## 10. Mutation: every guard proved able to fail

**Backend: fifteen cases against `make mutation-copy MUT=/root/w40limit-mut`.** The copy was
proved to be the imported tree before anything was believed — all four mutated modules print
a `__file__` under `/root/w40limit-mut` — and the unmutated copy was baselined green:
**58 passed** (`tests/integration/auth/test_sign_in_throttle.py` plus
`tests/integration/db/test_app_user_repository.py`). `PYTHONDONTWRITEBYTECODE=1`, and
`__pycache__` cleared **before and after** every case (§10.2). Every case reverts with
`git show HEAD:<path>`, never by re-editing, and every substitution refuses unless the text
it replaces occurs exactly once.

| Case | Mutation | Red |
|---|---|---|
| `L1` | `COALESCE(sign_in_blocked_until > now(), false)` → `false` — the lockout is never read | **6 failed** |
| `L2` | `>= :allowance` → `> :allowance` | **1 failed** — `assert 6 == 5` |
| `L3` | a wrong password stops being counted | **20 failed** |
| `L4` | a successful sign-in stops clearing the count | **1 failed** — `assert 2 == 0` |
| `L5` | the served-block branch deleted from `_NEXT_FAILED_SIGN_INS` | **nothing, then 1 failed** — see below |
| `L6` | the attempt-window branch → `WHEN false` | **1 failed** — `assert 3 == 1` |
| `L7` | an attempt made while shut is counted | **2 failed** |
| `L8` | `spend_a_verification` removed from the blocked path | **1 failed** — `assert [] == ['correct-hor...-staple-4471']` |
| `L9` | `change_password` stops clearing the brake | **1 failed** — `assert 5 == 0` |
| `L10` | the lockout also raises `token_epoch` | **3 failed** |
| `L11` | the unlock CLI's required-argument group → `required=False` | **1 failed** — `assert 1 == 2` |
| `L12` | the unlock CLI's "released nothing" exit `1` → `0` | **2 failed** — `assert 0 == 1` |
| `L13` | the "no such account" sentence collapsed into the no-op one | **1 failed** |
| `L14` | `CredentialAdapter.issue` back to a `_read` session | **2 failed** |
| `L15` | `check.py` stops reporting blocked accounts | **1 failed** |

The verbatim reds are in `/root/w40-logs/limit-mut-L*.log`, one per case. The ones worth
quoting:

```
L1  test_a_shut_account_refuses_the_right_password
    AssertionError: assert UserRecord(..., failed_sign_ins=0, last_failed_sign_in_at=None,
    sign_in_blocked_until=None) is None

L7  test_an_attempt_while_shut_does_not_extend_the_block
    AssertionError: assert datetime(2026, 9, 23, 9, 0, 45, 654091, ZoneInfo('Etc/UTC'))
                        == datetime(2026, 9, 23, 9, 0, 45, 538069, ZoneInfo('Etc/UTC'))
    ... and test_the_moment_a_block_is_set_is_logged_once: assert 4 == 1

L8  test_an_attempt_while_shut_spends_the_same_derivation_every_refusal_spends
    AssertionError: assert [] == ['correct-hor...-staple-4471']

L10 test_the_lockout_leaves_the_epoch_alone
    AssertionError: assert 6 == 1
    ... and test_a_lockout_does_not_touch_a_credential_anybody_already_holds:
    AssertionError: {"contract_version": "1.0.0-draft.1",
      "error_code": "authentication_required", "message": "No valid authenticated subject
      was presented. ...", "correlation_id": "cid-213c...", "retryable": false}
    assert 401 == 200

L13 test_releasing_a_login_nobody_holds_says_so_and_is_still_not_a_success
    AssertionError: assert 'access-unlock: no account has that login'
      in 'access-unlock: nothing was shut, so nothing was released\n'

L14 test_the_exchange_shuts_an_account_and_then_refuses_its_real_password
    AssertionError: the exchange never shut the account
    ... and the byte-identity case: assert 200 == 401

L15 test_the_check_command_reports_a_shut_account_without_changing_its_status
    AssertionError: assert 'access-check SIGN-IN BLOCKED' in 'access-check DEFAULT
      CREDENTIAL: login=admin ...'
```

`L10` is the one to keep. It is the `R-29` property as an assertion, and its red says it in
the caller's own vocabulary: with the lockout wired to the epoch, a credential minted **before**
the account was shut answers `401 authentication_required` on a guarded operation — an
unauthenticated caller having signed a working reviewer out.

`L11`–`L13` and `L15` matter for a second reason. All four mutate modules this suite drives
as **subprocesses**, and all four reddened — which is the positive proof wave 39 could not
give, because two of its cases died silently on exactly this. The helper derives its
`PYTHONPATH` from `auditmanager.__file__`, so the subprocess executed the copy.

### `L5` reddened nothing, and it is both kinds of failure at once

**`58 passed.`** The mutation deleted the branch that makes a served block *spent* — the one
clause standing between a five-minute cooling-off and a permanent lockout anybody can aim.

**The mutation was insufficient and the guard was blind, and they are the same defect seen
from two sides.** `test_a_served_block_is_spent_and_the_next_failure_starts_a_fresh_allowance`
ages the row by **an hour**, which puts the last failure outside the *attempt window* as well.
So the window branch restarts the count, the served-block branch is never reached, and the
test asserts the right outcome for the wrong reason — indefinitely, and with no symptom.

The interval that discriminates is **longer than the cooling-off period and shorter than the
attempt window**: only there is the block spent while the last failure is still recent. It is
also the only interval a real reviewer ever meets, five minutes after being shut.

`test_a_block_that_has_passed_is_spent_while_the_last_failure_is_still_recent` uses
`interval '6 minutes'`, a literal chosen to sit in that gap and deliberately **not** computed
from either constant (§12: never build an input out of the thing under test). That makes it a
statement *about the gap*: raise the cooling-off past six minutes, or lower the window below
it, and this test fails and sends the person moving the number here. `L5` re-run against the
repaired suite:

```
L5  test_a_block_that_has_passed_is_spent_while_the_last_failure_is_still_recent
    AssertionError: a block that has been served must be spent: a single attempt per
      cooling-off period would otherwise hold the account shut for ever
    assert 6 == 1
    1 failed, 58 passed
```

**This is the seventh wave running in which a quietly-dying mutation was the only thing that
found a blind guard**, and it is the only instrument that could have: the suite was green, the
gate was green, and a coverage report would have counted the deleted line as covered, because
the test does execute it — it just does not depend on it.

**Frontend: three cases**, in-tree against a committed tree, each reverted with
`git checkout --` in a trap, because `make mutation-copy` does not provide `web/`. Run as
`npm --prefix web test -- …` throughout — §4.62, the pin only protects a command that reads
it, and this is vitest **3.2.7** from the tree. Baselined green first: **9 passed**.

| Case | Mutation | Red |
|---|---|---|
| `W1` | the policy sentence deleted from the `credentials` refusal | `states the throttling policy…` — `expected false to be true` |
| `W2` | the policy sentence written in English | the same case **and** the language guard — `expected [ 'After', 'a', 'again', 'and', …(20) ] to deeply equal []` |
| `W3` | a fifth `SignInRefusal`, `'throttled'` | `expected [ 'credentials', 'validation', …(3) ] to deeply equal [ 'credentials', 'validation', …(2) ]`, and `expected '<section class="am-page">…' to include undefined` |

`W3` is the one that guards a decision rather than a string: a fifth refusal value is how the
screen would come to say *"this account is being attacked"*, and the second red in that row is
the existing screen guard discovering that nobody wrote a message for it.

---

## 11. The residue

**Nothing was resealed, so there is no surface-count residue**: 15 / 18 / 51 before and after,
and `tests/contract/api_v1/test_surface_counts_in_prose.py` — the guard that catches those —
had nothing to say, which is the correct answer rather than a silence.

The residue class this wave *could* leave is a different one: **statements about how the
exchange behaved before it had a brake.** Measured on this tree, with the command:

```
grep -rInE "no attempt counter|[Aa]uthenticating writes nothing|as many (passwords|guesses|attempts) as|unlimited (sign-in|attempts)|nothing (limits|slows) (a guesser|repeated)" \
  --include=*.py --include=*.ts --include=*.tsx --include=*.md --include=*.json --include=*.sh . \
  | grep -v node_modules | grep -v '^\./artifacts/' | grep -v '^\./docs/program/reviews/'
```

**One hit, and it is deliberate**: `src/auditmanager/bootstrap/adapters.py:686`, which
**quotes** the sentence it replaced in order to say it is no longer true. There was exactly
one statement of that class in the tree and it was repaired in the commit that falsified it
(§3), which is what §4.7 asks for.

**§4.7's own caveat applies and I am stating it rather than hoping**: this count was taken on
the branch that made the change, and *a count from the branch that made the change is not the
count*. Three streams got three different numbers this way in wave 34. The integrator must
re-run the command on the merged tree.

### One that is not mine, found while sweeping

**`docs/manual-tests/PC-01_prototype.md:39` says *"Observe the migration head is
`0005_truncated_call_status`"*.** It is **three heads stale** — `0006_app_user`,
`0007_credential_epoch` and now `0008_sign_in_throttle` — and it was already two heads stale
before this wave began. It is a document that tells an operator **what to observe**, so a
reader following it concludes the migration did not apply.

It was already known: `artifacts/checkpoints/PC-01/recertification-beaa7f7.json:97` records
*"docs/manual-tests/PC-01_prototype.md step 1 expected migration head 0003_open_items; the
head is 0005_truncated_call_status"*. **The certification noticed, the document was never
corrected, and it has gone stale twice more since.** `docs/manual-tests/**` is outside this
brief's `allowed_paths`, so it is untouched and handed over. After this wave it should read
`0008_sign_in_throttle`.

```
$ grep -rInE "head is \`?0(00[0-7])" --include=*.md --include=*.py --include=*.json . \
    | grep -v node_modules | grep -v '^\./artifacts/' | grep -v reviews | grep -v W39-REVOKE
docs/manual-tests/PC-01_prototype.md:39:**Observe the migration head is `0005_truncated_call_status`**, not merely "a head".
```

---

## 12. For the integrator

1. **The migration head is `0008_sign_in_throttle`.** `make migrate` before anything is
   driven against a database from this branch. Unlike `0007`, **this one locks nobody out**:
   every existing account starts with a clean count and no block, and the migration says so
   in its own log line.
2. **Nothing in `contracts/**` moved, and neither did the lock, the generated client or the
   mirror.** The surface is still 15 / 18 / 51. §6 argues why, and the wave plan said the same
   thing in advance (*"no contract change expected"*). `D-18`'s four-file coupling is
   untouched because there was nothing to couple.
3. **Re-measure the residue on the merged tree.** §11 has the command and says why my own
   count does not count — §4.7.
4. **`docs/manual-tests/PC-01_prototype.md:39` needs `0005_truncated_call_status` →
   `0008_sign_in_throttle`.** Three heads stale, already flagged by a certification in
   `artifacts/`, outside this brief's `allowed_paths`. §11.
5. **Two paths I touched are outside the brief's `allowed_paths` glob and inside its own
   instructions**, exactly as wave 39 reported for two others — §8 item 7:
   * `web/tests/unit/session/sign-in-screen.test.ts` — one case, so the screen change is
     reddenable;
   * `docs/program/DEPLOYMENT_RUNBOOK.md` — one new §7 subsection, *"When somebody cannot
     sign in and the password is right"*: what the two mechanisms are, that a lockout can be
     aimed and what bounds it, the `unlock` command with both forms and its three exit
     statuses, that it undoes no revocation, and that deploying `0008` locks nobody out. One
     existing sentence about `access.check` gained a clause. **Nothing else in that file
     changed**, and no count in it moved.
6. **`infra/**` is untouched.** No port, no binding, no proxy rule, no default account, and
   `127.0.0.1:31500` was not touched. No image was built; disk was 91% throughout.
7. **`D-66` and `D-67` are `W40-GUARDS`' and are untouched.** I was **not** in
   `api/security.py` at all — §8 item 4 — so neither guard's subject moved and there is
   nothing to coordinate. `src/auditmanager/api/**` has no change in this branch.
8. **Two rows could be added to `DEBT_REGISTER.md`** if wanted; it is a forbidden hotspot for
   this stream so I add neither:
   * the stale manual-test head above, which a certification already recorded once and which
     has gone stale twice more since;
   * **`D-69`'s pattern, seventh instance** — §10's `L5`: a guard that was sound, green and
     blind, found only because a mutation was expected to kill something and did not. Its
     check command is the `L5` row in §10.
9. **Nothing was tagged, pushed, merged, or written to `main`/`dev`.** No rebase. Branch
   `agent/w40-limit`, six commits on `ccaeed8`. **The final gate ran on `687bfa2`**, one
   commit below `HEAD`; the commit above it changes `docs/program/W40-LIMIT.md` and nothing
   else, which no guard in the gate reads — `test_surface_counts_in_prose.py` reads
   `src/auditmanager/api`, `infra/deploy` and `web/src`, not `docs/`. Saying so rather than
   letting a figure stand over a tree it does not describe. **`GATE OK` twice**, and the
   second —
   `/root/w40-logs/limit-gate-final.log`, battery **2298 / 5 / 169**, foundation **35**,
   frontend **1014 in 72 files** — is the one that describes the tree being handed over.
10. **`R-29`: §7 is the part that needs your eye.** Building the lockout is execution under
    `R-26`. The residual — that the account an unauthenticated caller can hold shut is the
    seeded `admin`, whose login is published — is **not** something I acted on, because both
    remedies (renaming the default account, restricting the exchange at the proxy) are
    `R-29` clause 2 by name. It goes to the owner as a question, and the alpha ships without
    it.

### The diff, whole

```
$ git diff --stat ccaeed8..HEAD
 db/migrations/README.md                            |   6 +-
 .../versions/20260923_0008_sign_in_throttle.py     | 192 +++++
 docs/program/DEPLOYMENT_RUNBOOK.md                 |  55 +-
 src/auditmanager/access/__init__.py                |  21 +
 src/auditmanager/access/check.py                   |  53 +-
 src/auditmanager/access/models.py                  |  20 +
 src/auditmanager/access/ports.py                   |  21 +
 src/auditmanager/access/repository.py              | 382 +++++++++-
 src/auditmanager/access/unlock.py                  | 199 ++++++
 src/auditmanager/bootstrap/adapters.py             |  30 +-
 tests/integration/auth/test_sign_in_throttle.py    | 787 +++++++++++++++++++++
 tests/integration/db/test_app_user_repository.py   |  10 +
 web/src/features/sign-in/model/exchange.ts         |  20 +-
 web/tests/unit/session/sign-in-screen.test.ts      |  22 +
 14 files changed, 1793 insertions(+), 25 deletions(-)
```

**Every `forbidden_hotspot` is absent from that list**, and the list is the proof:
`contracts/domain/v1/error-codes.json`, `contracts/analysis/**`, `src/auditmanager/norms/**`,
`tests/integration/norms/**`, `src/auditmanager/bootstrap/composition.py`, `infra/**`,
`DEBT_REGISTER.md`, `CURRENT_STATE.md`, `ALPHA_ROADMAP.md`, `OWNER_RULINGS_*`,
`PORT_REGISTRY.md`, `WAVE_PLAN_39_42.md`, `Makefile`, the root `pyproject.toml`,
`package.json` and every lockfile, and `artifacts/**`. `tests/e2e/pc01/journey/manifest.json`
is also absent, as the brief's two `allowed_paths` exceptions require. **No dependency was
added**, in either language.
