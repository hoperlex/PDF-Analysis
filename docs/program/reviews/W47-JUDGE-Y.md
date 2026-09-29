# W47-JUDGE-Y — the wave read from the operator's side, starting with the runbook

**Judge:** `W47-JUDGE-Y` · **lane:** `gate-w47k` (PostgreSQL `56440`, S3 `60040`/`60041`, API
`56441`, Next `56443`) · **worktree:** `/root/w47k` · **branch:** `agent/w47-judge-y` ·
**tree judged:** `44937fe`, the merged tip of wave 47.

Brief: `docs/program/dispatch/W47-JUDGES.md`, section *"Y starts from the operator"*. Entry
point: `docs/program/DEPLOYMENT_RUNBOOK.md`, read and driven the way the owner would on the day
he deploys. **Where the runbook and the tree disagree, the runbook is the finding.**

Written as the work lands and committed section by section, so a restart loses only the step in
progress. Every probe is reverted; the section *"What this judge left in the tree"* at the end
accounts for that.

## Summary of findings, most severe first

Each row names the file and line, states what is false, and the section behind it carries the
command that reproduces it. **`R-51` and `R-50` themselves work** — §9 says where, driven.

| # | what is false, or missing | where | this wave's? | §  |
|---|---|---|---|---|
| **Y1** *(confirmed by the integrator)* | The runbook never mentions the session register, its volume, or that `docker compose down --volumes` signs every reviewer out. `R-51`'s whole operator surface lives in the reference and not in the order of operations. | `DEPLOYMENT_RUNBOOK.md` — absent from §1 (`:124` says *both* volumes), §3, §5, §7, §10 | **yes** | 5 |
| **Y-C** | §7 ends the pilot with three bare-`python` commands that cannot run on the host §1 specifies (*"no `.venv`"*). The deployment's own migration log tells the operator to run two of them. `R-42` puts the owner himself at that keyboard. | `DEPLOYMENT_RUNBOOK.md:400`, `:426`, `:458` vs `:43-46` | no — but §7 is what this wave rewrote | 5 |
| **Y-F** | §2 says the signing key *"goes to the API process and nowhere else — not to a reviewer, not into a browser, not into a request header."* It is given to the `web` container too, and travels in an `Authorization: Bearer` header on every sign-in forward. | `DEPLOYMENT_RUNBOOK.md:166-170` vs `compose.server.yml:208`, `route.ts:382`, `credentialed-forward.ts:163` | no | 14 |
| **Y8** | The `R-4` wipe leaves three complete 199-character reviewer credentials in a file on the server's disk, byte-identical across the wipe. Neither §7 nor the README's wipe section says so. | `infra/deploy/reset.sh` (no reach); `DEPLOYMENT_RUNBOOK.md` §7 | **yes** (the file is new this wave) | 6 |
| **Y-D** | `reset.sh --yes-destroy-everything` dies with a **silent, undocumented exit 1** when the bucket is empty, leaving a dump directory whose sidecar holds an error payload. `--dry-run` handles the same case correctly. | `infra/deploy/reset.sh:406-407` | no | 6 |
| **Y-G** *(found at cross-examination)* | A trailing slash on any `/api/v1/…` path answers `307` with `location: http://127.0.0.1/<path>` — the `/api/v1` prefix **and the port** both dropped, so the caller is sent off this origin and onto the web screen of the same name. | `infra/deploy/proxy/nginx.conf` (`Host $host`, `proxy_pass …:8000/`, no `proxy_redirect`) | no | 15.3 |
| **Y2** | `readiness.sh` prints at the operator that *"deploy.sh's own proxy-answers guard requires 200 on this exact port"*. That guard requires **401** and refuses on 200. | `infra/deploy/readiness.sh:176`, `:185` | **yes** — the file is this wave's | 3 |
| **Y-A** *(confirmed by the integrator; his defect, not the stream's)* | §7's rewrite fixed §7 and `OWNER_RULINGS` §4 and left the runbook's **own preamble** saying the end of the pilot is *"not settled"*, four lines from the top. | `DEPLOYMENT_RUNBOOK.md:14-18` vs `:369` | **yes** — today's commit `98aa688` | 1a |
| **Y4** | A corrupt register file is reported into the container log with a ~20-character window of the file's own bytes, which can be live credential material. | `web/src/app/bff/session/store.ts:199-205` | **yes** | 2c |
| **Y3** | The runbook says the deploy asks the live stack for *"the published port answering 200"*, and §6 rests an argument on the same sentence. | `DEPLOYMENT_RUNBOOK.md:217`, `:334-335`; `infra/deploy/README.md:308` | no (`R-31`) | 3 |
| **Y5** | Thirteen guards, seven before docker. The tree has **fourteen** and **eight**, and `W47-GATE` is what moved both. | `DEPLOYMENT_RUNBOOK.md:212`, `:215`; `infra/deploy/README.md:171` | **yes** | 3 |
| **Y6** | `alpha.env.example` — the one file a human writes — still tells the operator the browser presents `AUDITMANAGER_API_TOKEN` as `Authorization: Bearer <token>`. §2 says that paragraph was corrected; it was corrected in `README.md` only. | `infra/deploy/env/alpha.env.example:147` vs `DEPLOYMENT_RUNBOOK.md:166-170` | no | 3 |
| **Y7** | `sessionDurability()` answers `durable: true` on a volume the process provably cannot write. It reports the configuration, not the register in force. | `web/src/app/bff/session/store.ts:249-252` | **yes** | 2e |
| **Y9** | `alpha.env.example` says `ALPHA_INSTANCE` derives **both** named volumes. There are three. | `infra/deploy/env/alpha.env.example:48` | **yes** | 3 |
| **Y-B** | §7 warns the operator that the rehearsal's total over-reports. `D-39` closed that on 2026-09-21 and the total now sums base tables only. | `DEPLOYMENT_RUNBOOK.md:501-505` | no | 3 |
| **Y-E** *(narrowed at cross-examination)* | The baseline 2567 / 1139-in-81 is **cited to a document that states 2516 / 1135-in-80**, in both judges' briefs and in `W47-LOCK.md`. The figure itself is real — `/root/w47-a-merged-gate.log:125,230-231`, the gate on merged sub-stage A. **My original claim that it was never measured is falsified**; the citation, not the number, is the defect. | `docs/program/W47-LOCK.md:334,336` vs `dispatch/W47-DISPATCH.md:14-18` | **yes** | 12, 15.4 |
| **Y10** | The runbook says the origin serves *"nineteen operations"*; three files say fifteen. The contract declares **twenty**, and the deploy prints it on every run. | `DEPLOYMENT_RUNBOOK.md:66`, `:173`; `alpha.env.example:75`, `:136`; `deploy.sh:215`, `:895`; `compose.server.yml:248` | no | 3 |

**Status after `W47-FIX` (`88757dc`) and the integrator's `Y-B` repair (`6ad43a0`), re-driven on a
deployed stack in §16:** `Y8`, `Y-D` and `Y-G` are **repaired, and measured repaired on a real
stack**; `Y-C`'s command form is repaired and the repaired form runs in a real deploy; `Y-E` is
corrected against the integrator's own log; `Y1` and `Y-A` he confirmed as his. `R-52` — the
ruling the cross-examination produced — is **upheld end to end**, §16.

**Provenance of this file.** §1–§14 were written on `agent/w47-judge-y` at `a2c1553` (base
`44937fe`), §15 the same day. §16 is on `agent/w47-judge-y2`, base `6ad43a0`. That branch did not
carry this file — `88757dc` merged `W47-FIX` without the judges' reports — so the whole report is
reassembled here and `agent/w47-judge-y2` is the branch to take.

Everything below carries the command that produced it.

---

## 1. The two parts the integrator changed today

### 1a. §7, the `R-4` wipe — the rewrite is faithful to `R-41`/`R-42`, and it left a third live list behind it

**What is right.** §7's new text matches both rulings clause for clause. `R-41` says the pilot
ends by the owner's explicit instruction, with no date and no observable event, with the caveat
stated and accepted; §7 says exactly that and records that the runbook argued the other way and
was overruled rather than deleting the argument. `R-42` says the owner performs the wipe
personally and instructs that it be recorded as his decision and **not as a role**; §7 records it
that way and says why (`T-6`). Nothing in §7 claims more than the rulings ruled.

```
sed -n '829,845p'  docs/program/OWNER_RULINGS_2026-09-17.md     # R-41, R-42
sed -n '365,385p'  docs/program/DEPLOYMENT_RUNBOOK.md           # the rewritten answer
```

§7's description of `reset.sh` also holds against the script:

```
grep -n '^# >>> guard:' infra/deploy/reset.sh | wc -l      # 12 -- and README.md:389 says twelve
grep -n 'destructive-flag\|database-matches\|bucket-matches\|dump-verified' infra/deploy/reset.sh
```

— dumps and verifies before dropping (`dump-verified`), refuses without an explicit flag
(`destructive-flag`), refuses names the environment does not configure (`database-matches`,
`bucket-matches`). The revoke/unlock exit statuses §7 quotes (`0`/`1`/`2`, and `2` when run bare)
are the ones the modules return:

```
grep -n 'return 0\|return 1\|return 2' src/auditmanager/access/revoke.py src/auditmanager/access/unlock.py
```

**Y-A (finding).** The rewrite fixed §7 and `OWNER_RULINGS` §4 and left the runbook's **own
preamble** stating the opposite, four lines from the top of the file:

- `docs/program/DEPLOYMENT_RUNBOOK.md:14-18` — *"`R-4` is an owner ruling with **two halves still
  open**. Who uploads a real client document, and what event counts as *"the end of the pilot"*,
  are the owner's and are **not settled**"*
- `docs/program/DEPLOYMENT_RUNBOOK.md:369` — *"**Answered by `R-41`**: the pilot ends when the
  owner says so"*

An operator who reads the file from the top is told the trigger is unsettled before he reaches
the section that settles it, and the preamble is the paragraph that justifies the section
existing at all.

```
cd /root/w47k
sed -n '14,18p'   docs/program/DEPLOYMENT_RUNBOOK.md
sed -n '369,369p' docs/program/DEPLOYMENT_RUNBOOK.md
git show 98aa688 -- docs/program/DEPLOYMENT_RUNBOOK.md | head -40   # the diff starts at line 336
```

The same paragraph also still carries the half that **is** open (*who uploads a real client
document*) — and §7, after the rewrite, no longer says that half is open anywhere. The correct
repair is one sentence in the preamble, not a deletion: the preamble is where the reader learns
that one half is answered and one is not.

### 1b. `infra/deploy/README.md`'s `R-51` cost — every claim in it is true of the tree

Driven claim by claim. This is the block at `infra/deploy/README.md:311-352`.

| the README says | measured | verdict |
|---|---|---|
| volume `${ALPHA_INSTANCE}-web-sessions`, declared in `compose.server.yml` | `grep -n 'web-sessions' infra/deploy/compose.server.yml` → declared at `:56-57`, `name: ${ALPHA_INSTANCE}-web-sessions` | true |
| mounted at `/var/lib/auditmanager/sessions`, **by `web` only** | `grep -n -A2 'volumes:' infra/deploy/compose.server.yml` — the only service-level mount is `web`'s, at `:220` | true |
| the file is `register.json`, mode `0600`, in a directory the image creates owned by `node` | probe §3 below: file mode `600`, directory mode `700`; `infra/deploy/Dockerfile.web:58-60` creates and `chown node:node`s it **before** `USER node` | true |
| configured by `AUDITMANAGER_SESSION_STORE`, set in `compose.server.yml`, not in `alpha.env` | `grep -n 'AUDITMANAGER_SESSION_STORE' infra/deploy/compose.server.yml infra/deploy/env/alpha.env.example` → present in the first, absent from the second | true |
| "until each credential expires — one hour, `TOKEN_LIFETIME_SECONDS`" | `src/auditmanager/api/security.py:253` → `TOKEN_LIFETIME_SECONDS: Final[int] = 3600` | true |
| the browser holds "a 32-byte opaque number in an `HttpOnly` cookie" | `web/src/app/bff/session/store.ts:72` (`SESSION_ID_PATTERN = /^[0-9a-f]{64}$/`), `mintSessionId()` draws 32 bytes, `sessionCookie()` sets `HttpOnly; SameSite=Strict` | true |
| a revoked credential still stops at once, because the API compares `token_epoch` on every request | `src/auditmanager/api/security.py` reads `AccountStandings.standing_of` on every guarded request; `W47-LOCK` §3 | true, not re-driven here (judge X's A3) |
| `docker compose down` does not remove it; `down --volumes` does, "and doing that signs everybody out" | it is an ordinary named volume in the same `volumes:` block as `postgres-data` and `s3-data` | true |
| a `web` container that cannot write the file **still serves**, and says so on every attempt starting `[session-register] could not write` | probe §5 below, on a filesystem with no space: sign-in succeeds, subject readable, the log line is exactly that | true |
| unset → `[session-register] AUDITMANAGER_SESSION_STORE is not set` at the first sign-in | probe §1 below: that exact line | true |

**So the README's block is true of the tree.** Where the cost is *not* written is the runbook —
see `Y1`.

---

## 2. `R-51` — the register under the four conditions the brief names

Driven against the real module, not a description of it, with `vite-node` and the suite's own
alias configuration, in a probe file that was deleted afterwards. Its source is in §11 so
any of this can be re-run.

```
cd /root/w47k/web && node_modules/.bin/vite-node --config vitest.config.ts <probe>.ts
```

### 2a. the variable unset — **a configured absence, announced**

```
durability: {"durable":false,"path":null}
[session-register] AUDITMANAGER_SESSION_STORE is not set: sessions are held in this process
and end when it does. Every reviewer signs in again on the next deploy. ...
openSession ok: true count: 1
after restart, subject: null
```

Right, and right in the way `AGENTS.md` §4 demands: the memory-only register works, and it says
which of the two is in force rather than letting an incident discover it.

### 2b. the ordinary case — **a session really does outlive the process**

```
file exists: true   file mode: 600   dir mode: 700
credential is in the file: true
after restart subject: {"login":"admin","openedAt":…,"expiresAt":…,"isDefaultCredential":true}
after restart credential: CRED-SURVIVOR
closeSession removes it: true -> file still has it: false
```

`isDefaultCredential` survives the restart, which matters: a reviewer who reconnects after a
redeploy is still sent to the change screen rather than walking into a wall of `403`s. And
`closeSession` is a real logout on the file as well as in memory.

### 2c. the file corrupt — **recovered from, and the recovery prints the file's own bytes**

```
[session-register] /tmp/jy-register/bad/register.json could not be read
(SyntaxError: Unexpected token '@', ..."edential":@"eyJTOKEN"... is not valid JSON).
Starting with no open sessions: every reviewer signs in again. ...
count (0, must not throw): 0
still serves a new sign-in: true
```

The recovery behaviour is exactly what `W47-LOCK` claims — reported, treated as empty, the tier
keeps serving.

**Y4 (finding).** `web/src/app/bff/session/store.ts:199-205` interpolates `String(error)` into the
log line. V8's JSON errors quote **a window of the document around the fault**, so a corruption
that lands in or beside a `"credential"` value puts live credential bytes in the container log —
the one place `store.ts`'s own opening docstring says the credential must never go. Independent of
this repository, on the register's own shape:

```
node -e '
const good = JSON.stringify({version:1,sessions:[{id:"a".repeat(64),login:"admin",
  credential:"eyJSECRET-CREDENTIAL-VALUE.signature",openedAt:1,expiresAt:2,
  isDefaultCredential:false}]});
try { JSON.parse(good.replace(String.fromCharCode(34)+"credential"+String.fromCharCode(34)+":"+String.fromCharCode(34)+"eyJ",
  String.fromCharCode(34)+"credential"+String.fromCharCode(34)+":@eyJ")); }
catch (e) { console.log(String(e)); }'
# SyntaxError: Unexpected token '@', ..."edential":@eyJSECRET"... is not valid JSON
```

It is a ~20-character window, not the whole token, and the log is on the host — so this is a
narrowing of a property, not an open door. The repair is one line: log `error instanceof Error ?
error.name : 'unreadable'` (or `error.constructor.name`) instead of `String(error)`. The path and
the outcome are already in the same sentence, which is what an operator needs; the parser's
quotation of the file is what he does not.

### 2d. the volume fresh and owned by root — **the image's `chown` is what prevents it, and it works**

The `Dockerfile.web` comment claims docker seeds a fresh named volume from the image's directory
*including its ownership*. Driven both ways, with a three-line image that reproduces only that
part of `Dockerfile.web`:

```
# A: a fresh named volume
docker volume create jy-fresh
docker run --rm -v jy-fresh:/var/lib/auditmanager/sessions jy-voltest \
  sh -c 'id -un; ls -ld /var/lib/auditmanager/sessions; touch …/register.json && echo WRITE-OK'
  node
  drwx------ 2 node node 4096 … /var/lib/auditmanager/sessions
  WRITE-OK

# B: a volume that already holds something, owned by root
docker run --rm -u 0 -v jy-rootvol:/mnt alpine sh -c 'touch /mnt/stale; chown 0:0 /mnt; chmod 700 /mnt'
docker run --rm -v jy-rootvol:/var/lib/auditmanager/sessions jy-voltest sh -c '…'
  node
  drwx------ 2 root root 4096 … /var/lib/auditmanager/sessions
  WRITE-REFUSED
  touch: cannot touch '…/register.json': Permission denied
```

So the mechanism the stream relied on is real (**A**), and the failure it is protecting against is
real too (**B**): a volume that already exists with root-owned content is not re-seeded, and the
`node` process cannot write it. On a first deploy **A** is the case that happens. **B** is
reachable by an operator who pre-creates the volume, or restores one from a backup taken as root.
What happens then is §2e.

### 2e. the disk full (and the unwritable volume) — **it still serves, and it says so every time**

On a filesystem with no free space (`mount -t tmpfs -o size=16k`, filled):

```
[session-register] could not write /tmp/jy-fullfs/register.json
(Error: ENOSPC: no space left on device, write). The sessions open now will not survive this
container being recreated.
sign-in succeeds: true | subject readable: true
leftover files on the full fs: [ 'filler' ]      # no orphaned .writing-<pid> temp file
```

Exactly the README's promise, including that the line repeats per attempt rather than once, and
the temp file is cleaned up rather than left holding a credential.

**Y7 (finding).** `web/src/app/bff/session/store.ts:249-252`:

```ts
export function sessionDurability(): { readonly durable: boolean; readonly path: string | null } {
  const path = getSessionStorePath();
  return { durable: path !== null, path };
}
```

Its docstring says *"Which of the two registers is in force, for a diagnostic and for a test."* On
the **B** volume above, and on a full disk, the register in force is the memory one and this
answers `durable: true`. Measured in the probe:

```
===== 4. unwritable directory =====
sign-in succeeds: true | subject readable: true
sessionDurability() claims: {"durable":true,"path":"…/ro/register.json"}
```

It is a diagnostic that cannot distinguish the state the whole wave is about. Nothing in the
deployment reads it today, so this is a latent defect rather than a live one — but it is the
function an operator or a later readiness check would reach for, and it would answer the question
about the configuration while appearing to answer it about the register.

---

## 3. The runbook against the tree — every number I could check

Each row was checked by running the thing the runbook describes, on the throwaway instance
`jy-w47k-alpha` (port `56441`) built from this worktree. **Where the two disagree, the runbook is
the finding.**

### Y5 — thirteen guards, seven before docker: both wrong, and this wave is why

`DEPLOYMENT_RUNBOOK.md:212` — *"it refused, and said which of **thirteen** guards refused and
why"*; `:215` — *"**Seven** guards answer before docker is touched at all"*. Also
`infra/deploy/README.md:171` — *"**Thirteen** guards"*.

```
cd /root/w47k
grep -c '^# >>> guard:' infra/deploy/deploy.sh                 # 14
grep -n  '^# >>> guard:' infra/deploy/deploy.sh | head -8      # the 8 that precede any docker call
grep -n  'compose()' infra/deploy/deploy.sh                    # :350 -- the first docker invocation
grep -n  'compose ps --quiet proxy' infra/deploy/deploy.sh     # :371, inside guard 9, port-not-foreign
```

Fourteen guards; **eight** complete before docker is touched (`known-options`,
`env-file-present`, `instance-configured`, `identity-policy-known`, `placeholder-secrets`,
`derived-secrets-coherent`, `compose-file-present`, `build-context-complete`), and the ninth,
`port-not-foreign`, is the first that runs `compose ps`.

**This wave moved the number.** `W47-GATE`'s `D-103` repair added `derived-secrets-coherent`:

```
git show 02fe00a:infra/deploy/deploy.sh | grep -c '^# >>> guard:'   # 13, before W47
git show e114519:infra/deploy/deploy.sh | grep -c '^# >>> guard:'   # 14, after it
git log --oneline -1 e114519
# e114519 repair(W47-GATE): D-103 -- deploy.sh's guard now reads all seven secret names, not four
```

The guard's own comment says it *"sits beside `placeholder-secrets` in the set that refuses
before docker is touched at all"* (`infra/deploy/deploy.sh:258`) — so the stream knew which set
it was joining and neither count was carried into the two documents that state it.

`reset.sh`'s count, by contrast, is right: `grep -c '^# >>> guard:' infra/deploy/reset.sh` → 12,
and `infra/deploy/README.md:389` says twelve.

### Y3 — "the published port answering 200" — it answers **401**, and a 200 is a refusal

`DEPLOYMENT_RUNBOOK.md:217` lists the four questions the deploy asks the running stack and names
the third as *"the published port answering 200"*. `:334-335` builds an argument on it: *"there is
deliberately no redirect from it, because `deploy.sh`'s `proxy-answers` guard requires 200 on
that port"*. `infra/deploy/README.md:308` repeats it.

The guard requires **401** and treats 200 as a refusal — `R-31` closed those four documentation
routes and the guard was changed with it:

```
sed -n '751,772p' infra/deploy/deploy.sh
#  `R-31` CLOSED THIS PATH BEHIND A CREDENTIAL, SO THE ANSWER THAT PROVES LIFE IS NOW 401.
#  ...
#  A 200 here is therefore a REFUSAL, and deliberately so
```

Driven on the deployed stack, and on the deploy's own screen:

```
grep -n -A1 'the published port answers' /root/w47k-deploy.log
#   401 on http://127.0.0.1:56441/api/v1/openapi.json -- the API answered
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:56441/api/v1/openapi.json    # 401
```

The **conclusion** §6 draws from the false premise still holds — a proxy-level `301` would turn
the 401 into a 301 and refuse the deploy — so this is a false sentence carrying a true argument,
which is the kind that survives review. It is also now printed at an operator, which is `Y2`.

### Y2 — `readiness.sh` prints the false sentence at the operator

`infra/deploy/readiness.sh:176` (comment) and `:185` (**the printed finding**):

> `… and deploy.sh's own proxy-answers guard requires 200 on this exact port (DEPLOYMENT_RUNBOOK.md section 6).`

Reproduced, on a copy of the env file with the published bind address the check is about:

```
cd /root/w47k
cp infra/deploy/env/alpha.env infra/deploy/env/.jyprobe/published.env
sed -i 's|^#ALPHA_BIND_ADDRESS=0.0.0.0|ALPHA_BIND_ADDRESS=0.0.0.0|' infra/deploy/env/.jyprobe/published.env
infra/deploy/readiness.sh --env-file infra/deploy/env/.jyprobe/published.env | grep plain-http
# readiness FINDING plain-http  ALPHA_BIND_ADDRESS is 0.0.0.0, publishing plain HTTP off this
# host. ... deploy.sh's own proxy-answers guard requires 200 on this exact port ...
```

`readiness.sh` is **this wave's file** (`26cd836`, `W47-GATE`), and this is the one line in it
that is an assertion about another file's behaviour rather than a reading of the tree. It is the
line an operator meets in exactly the situation — a published stand — where he most needs the
tree described accurately. The repair is two words in one string and one comment.

Everything else `readiness.sh` printed on a live post-wave-47 stack is true (§4).

### Y6 — the file the operator edits still tells him to hand the signing key to the browser

`DEPLOYMENT_RUNBOOK.md:166-170` is emphatic:

> **Since wave 34 this is the key the API signs reviewer credentials with, not a token anyone
> presents.** … it goes to the API process and nowhere else — not to a reviewer, not into a
> browser, not into a request header. **The paragraph that used to tell operators to present it
> as a bearer token is corrected in `infra/deploy/README.md`.**

It was corrected there. It was **not** corrected in `infra/deploy/env/alpha.env.example`, which is
the file §2 tells the owner to `cp` and open in `$EDITOR` — the only file a human writes:

```
grep -n 'Bearer' infra/deploy/env/alpha.env.example
# 147:# The browser client presents it as `Authorization: Bearer <token>`.
```

`infra/deploy/README.md:123-130` records why this matters in its own words — *"`JUDGE-SEC` raised
this as blocking on wave 34's merge: the code changed and the runbook did not, which is the shape
where a document becomes an attack"*. The same sentence is still live, three lines below the
value it describes, in the file that gets copied.

It is false twice over: the browser presents nothing (the web tier forwards server-side,
`W15-AUTH`), and since wave 34 the value is a signing key, not a bearer
(`src/auditmanager/api/security.py`, `_SIGNING_CONTEXT`).

### Y9 and Y10 — counts the tree has outgrown

```
grep -n 'BOTH named volumes' infra/deploy/env/alpha.env.example        # :48
docker compose --env-file infra/deploy/env/alpha.env \
  -f infra/deploy/compose.server.yml config --volumes                  # three: postgres-data, s3-data, web-sessions
```

`R-51` added the third volume and the line an operator reads while deciding what `ALPHA_INSTANCE`
governs still says both. **This wave's.**

```
python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));\
print(sum(1 for p,i in d['paths'].items() for m in i if m in ('get','post','put','patch','delete')))"   # 20
grep -n 'nineteen operations' docs/program/DEPLOYMENT_RUNBOOK.md        # :66, :173
grep -n 'fifteen operations' infra/deploy/env/alpha.env.example infra/deploy/deploy.sh infra/deploy/compose.server.yml
```

The deploy's own last guard prints the true number on every run:

```
grep -n 'frozen ops\|served ops' /root/w47k-deploy.log
#   frozen ops : 20
#   served ops : 20
```

Nineteen and fifteen are both wrong and neither is this wave's doing (`git show ce25e14:contracts/api/v1/openapi.json`
already counts 20). Listed because an operator reading §1's argument about what an
unauthenticated origin exposed is reading a number the deploy contradicts on screen.

### Y-B — §7 warns the operator against a number that was repaired eight days before the runbook shipped

`DEPLOYMENT_RUNBOOK.md:501-505`:

> `--dry-run`'s **per-table figures are exact**, and its **total is not** — it counts one view
> (`finding_current_verdict`) whose rows are already counted elsewhere, so the total
> **over-reports** … (`D-39`).

Driven, on the throwaway instance:

```
infra/deploy/reset.sh --database jy_w47k --bucket jy-w47k --dry-run | tail -8
#   finding_current_verdict  (0 rows, view: these rows are counted above)
#   total: 26 rows in 17 base tables (and 1 view listed above, projecting rows already in that number)
```

The total sums base tables only and names the view separately.

```
sed -n '1322,1326p' docs/program/DEBT_REGISTER.md
# ### D-39 — the wipe rehearsal's total counted a view — **CLOSED**
# **Closed 2026-09-21 by `W26-OPS`.**
grep -n 'AND THE SEVENTEENTH IS NOT A TABLE' infra/deploy/reset.sh    # :300, the repair
```

The runbook is dated 2026-09-21 and `D-39` closed 2026-09-21. The operator is being told to
distrust a figure that is correct, in the section that runs the wipe — the one procedure where
he is deciding how much he is about to destroy.

---

## 4. `R-50` from the operator's side

### 4a. the readiness command, re-run against a live post-wave-47 stack — it tells the truth

```
cd /root/w47k && infra/deploy/readiness.sh ; echo "exit=$?"
```

against `jy-w47k-alpha`, freshly migrated, `admin` still on the seeded password (2 s, exit 1):

```
readiness FINDING default-credential 1 account(s) still on the password this system seeded them
    with -- step 5 is not done. access-check's own lines:
    access-check DEFAULT CREDENTIAL: login=admin user_uid=usr_01M3P3YCSA2B3GZ767282HA78V
      created_at=… password_unchanged_since=…
readiness FINDING tls                no usable certificate pair at …/proxy/tls
readiness OK      plain-http         ALPHA_BIND_ADDRESS is 127.0.0.1 …
readiness FINDING provider-mode      AUDITMANAGER_PROVIDER_MODE is 'recorded' …
readiness OK      cost-ceiling       the run cost ceiling resolves to $1.0.
readiness FINDING off-host-backup    no destination exists in this repository …
readiness.sh: 4 finding(s), 0 unknown, 6 checks.
```

Five of the six checks are answered from the tree and the live stack correctly. `R-50` did not
move any of them: `default-credential` asks the database, and the refusal `R-50` added is at the
API seam, so the check neither gained a false green nor lost its subject. Its output names the
login, the uid and two timestamps and **no credential material**.

The sixth, `plain-http`, is `Y2`: its `OK` branch is true and its `FINDING` branch carries a false
sentence about `deploy.sh`.

### 4b. does anything in the deploy path print, log or forward a credential? — **no**

Driven against the whole running stack after a sign-in with the seeded account, with the
deployment's own generated values as the sentinels:

```
cd /root/w47k
DC="docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml"
TOK=$(sed -n 's/^AUDITMANAGER_API_TOKEN=//p' infra/deploy/env/alpha.env)
PGPW=$(sed -n 's/^POSTGRES_PASSWORD=//p' infra/deploy/env/alpha.env)
curl -s -o /dev/null -X POST -F login=admin -F password=password http://127.0.0.1:56441/bff/v1/session
$DC logs --no-log-prefix > /root/w47k-stacklogs.txt 2>&1
grep -c -- "$TOK"  /root/w47k-stacklogs.txt     # 0  -- the signing key
grep -c -- "$PGPW" /root/w47k-stacklogs.txt     # 0  -- the database password
grep -c    "am2\." /root/w47k-stacklogs.txt     # 0  -- any minted reviewer credential
grep -ci   "password=password" /root/w47k-stacklogs.txt   # 0  -- the seeded password
```

153 log lines across five containers, none of them carrying a credential. The one
`[session-register]` line the new code adds names the **path** and the cost and nothing else:

```
[session-register] sessions persist to /var/lib/auditmanager/sessions/register.json. Until each
credential expires, the API credentials are on that volume; they still never reach the browser,
and a revoked credential still stops working on its next request.
```

The scripts are clean too — `deploy.sh`, `reset.sh` and `verify-deployed.sh` print no value read
out of `alpha.env`:

```
grep -n 'echo\|printf' infra/deploy/deploy.sh infra/deploy/reset.sh infra/deploy/verify-deployed.sh \
  | grep -i 'token\|password\|DATABASE_URL\|secret\|credential'      # no output
```

The one exception is deliberate and is not a secret: `placeholder-secrets` prints `  $name = $mine`
when a value is **byte-identical to the published example**, which is the only case it fires in
(`infra/deploy/deploy.sh:230-237`).

And the error path of the module `readiness.sh` reuses does not leak a connection string, which it
easily could have:

```
cd /root/w47k
DATABASE_URL='postgresql+psycopg://amuser:SENTINELPASSWORD123@nosuchhost.invalid:5432/amdb' \
  PYTHONPATH=src .venv/bin/python -m auditmanager.access.check
# access-check FAILED: (psycopg.OperationalError) failed to resolve host 'nosuchhost.invalid' …
DATABASE_URL='not-a-url://amuser:SENTINELPASSWORD123@x/y' \
  PYTHONPATH=src .venv/bin/python -m auditmanager.access.check
# access-check FAILED: DATABASE_URL is not a parseable SQLAlchemy URL (ArgumentError).
#                      Expected postgresql+psycopg://...
```

The second is the interesting one: the obvious implementation prints the `ArgumentError`, which
quotes the URL — password included. This one names the class and re-states the expected shape.
**That is the tree doing the right thing on purpose**, and it is the same discipline `Y4` asks
`store.ts` to apply to `String(error)`.

### 4c. the checks `deploy.sh` runs against a live stack — there are **four**, and this wave moved none of them

```
grep -n '^# >>> guard:' infra/deploy/deploy.sh | tail -4
# 640:# >>> guard: services-healthy
# 713:# >>> guard: migrations-at-head
# 751:# >>> guard: proxy-answers
# 785:# >>> guard: schema-conforms
```

(The brief said three. Four is what the file has, and what the deploy printed:
`-- every service is there …`, `-- the database is at the head this code expects --`,
`-- the published port answers --`, `-- the served schema conforms to the frozen contract --`.)

The only `deploy.sh` commit in wave 47 is `e114519`, which added a **pre-docker** guard:

```
git log --oneline ce25e14..44937fe -- infra/deploy/deploy.sh
# e114519 repair(W47-GATE): D-103 -- deploy.sh's guard now reads all seven secret names, not four
git log --oneline 45d784f..44937fe -- infra/deploy/deploy.sh    # (empty -- nothing after the merge)
```

What the wave *did* move is what two of the four **see**, and both survived:

- `schema-conforms` compares the served document with a contract `R-50` resealed. Both moved in one
  commit (`ff1db5e`), and the deployed stack agrees: `frozen ops : 20 / served ops : 20 /
  differences: 0`;
- `services-healthy` depends on the `web` container answering `/`, which `R-50` turned into a
  redirect chain (`/` → `/projects`, and `/projects` → `/account/password` for a default
  credential). Measured on the deployed stack: `/` → `307`, `/projects` → `200` with no session,
  and the container reported healthy. `requireAChangedPassword()` returns without redirecting when
  there is no session (`web/src/app/bff/session/screen-lock.ts:48`), which is what keeps the
  healthcheck green — **an unremarked dependency**: a future lock that redirected an
  unauthenticated caller would turn every deploy into a `services-healthy` refusal.

---

## 5. What the runbook does not say

### Y1 — the runbook never mentions the session register at all

This is the finding I was sent to look for and it is the largest. `R-51` is an operator-facing
change — a new named volume, a new failure mode, and one command that undoes it — and **none of it
is in the order of operations**:

```
cd /root/w47k
grep -c -i 'session'                docs/program/DEPLOYMENT_RUNBOOK.md    # 0
grep -n  -i 'web-sessions\|register' docs/program/DEPLOYMENT_RUNBOOK.md   # nothing
grep -n  'down --volumes'           docs/program/DEPLOYMENT_RUNBOOK.md    # nothing
grep -n  'both named volumes'       docs/program/DEPLOYMENT_RUNBOOK.md    # :124
```

Four specific places where an operator following this document is missing something the tree now
does:

1. **§1, Disk** (`:124`) — *"**both** named volumes, just after a first deploy | ~76 MB"*. There are
   three. The figure is a `W26-HOST` measurement and cannot simply be edited, but the word
   *both* is now wrong and the third volume is the one holding credentials;
2. **§3, Deploy** — the runbook's account of what a redeploy costs says nothing about what it now
   *preserves*. The sentence this wave earned — *a redeploy no longer signs every reviewer out* —
   appears in `infra/deploy/README.md` and in three source docstrings, and nowhere in the
   procedure;
3. **nowhere** — that `docker compose down --volumes` signs every reviewer out. `compose.server.yml:30-32`
   warns about it for the documents; the README warns about it for the sessions; the runbook, which
   is the document an operator reads while deciding which form of `down` to type, warns about
   neither. §5's *"what this runbook does not do"* would be the natural home;
4. **§10, When it goes wrong** — the new failure signature is absent. `[session-register] could not
   write …` is a line an operator will see (a restored volume, a full disk — both driven in §2),
   and §10 is the table of *"what you see / what it is"*.

The integrator's brief asked *"does the runbook say so?"* — it does not, in any of the four
places. The stream's own report is explicit that it put the cost in the README *"where an operator
meets it"* (`docs/program/W47-LOCK.md` §6), and its commit message says *"the cost `R-51` states is
in the runbook"* (`a134f9a`) — which is the sentence that is not true of the tree:

```
git show a134f9a --stat | grep -c DEPLOYMENT_RUNBOOK     # 0
git log --oneline -1 --format=%B a134f9a | grep -n 'in the runbook'
```

That is a documentation split the runbook's own preamble authorises — *"the order and the decisions
live here, the mechanism and the measurements live in `infra/deploy/README.md`, and neither
restates the other"*. By that division `down --volumes` signing everybody out is **a decision and an
order of operations**, not a mechanism, and it belongs here.

### Y-C — §7's end-of-pilot commands cannot run on the host §1 describes

§1 is categorical about what the deploy host has:

> **And nothing else.** No `make`, no `npm`, **no `.venv`, no `web/node_modules`** … `make
> bootstrap` and `npm ci` are the *developer's* gate, not this. (`:43-46`)

§7 then tells the operator to end the pilot with:

```
PYTHONPATH=src python -m auditmanager.access.revoke --everyone      # :400
PYTHONPATH=src python -m auditmanager.access.unlock --login <login> # :458
python -m auditmanager.access.check                                 # :426
```

Three bare-`python` commands that import `sqlalchemy` and `psycopg`. On a host provisioned by §1
there is no interpreter that can run them:

```
cd /root/w47k
PYTHONPATH=src /usr/bin/python3 -m auditmanager.access.revoke --everyone
#   File "/root/w47k/src/auditmanager/access/ports.py", line 52, in <module>
#     from sqlalchemy.orm import Session
# ModuleNotFoundError: No module named 'sqlalchemy'
```

(Run with the system interpreter deliberately: a development host's `PATH` carries a `.venv` and
would hide this.)

The tree already knows the rule and already has the idiom. `readiness.sh` says so in its own
comment — *"`DEPLOYMENT_RUNBOOK.md` section 1 promises this host bash/docker/curl/sed/git and
explicitly does not promise python3"* — and runs the same package **inside the api image**:

```
grep -n 'entrypoint python api' infra/deploy/readiness.sh
#   docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" \
#     run --rm --no-deps -T --entrypoint python api -m auditmanager.access.check
```

So the repair is mechanical — the same `docker compose run … --entrypoint python api -m
auditmanager.access.revoke --everyone` — and the finding is that §7, the section rewritten today
to say *who* ends the pilot, still tells him to end it with a command his host cannot execute.
**`R-42` makes this worse rather than milder:** the person typing it is now, by ruling, the owner
himself on the server.

This is not wave 47's defect (the text is `W39-REVOKE`'s and `W40-LIMIT`'s), but §7 is the section
this wave rewrote, and the rewrite passed over it.

---

## 6. `R-51` driven on a deployed stack — the question the brief asked first

The probes in §2 drive the module. This section drives the **deployment**: `deploy.sh` from this
worktree, on the throwaway instance `jy-w47k-alpha`, port `56441`.

### 6a. does a redeploy keep reviewers signed in? — **yes, and it is the container being replaced that proves it**

```
cd /root/w47k
C=$(curl -s -i -X POST -F login=admin -F password=password \
      http://127.0.0.1:56441/bff/v1/session | sed -n 's/^set-cookie: \(am_session=[a-f0-9]*\);.*/\1/p')
curl -s -o /dev/null -w '%{http_code}\n' -H "Cookie: $C" http://127.0.0.1:56441/bff/v1/projects   # 403

DC="docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml"
$DC up -d --force-recreate web          # 4 s;  container id 957d9f5f… -> 5a96c5876b3b…
curl -s -o /dev/null -w '%{http_code}\n' -H "Cookie: $C" http://127.0.0.1:56441/bff/v1/projects   # 403

$DC down && $DC up -d                   # 28 s; the whole stack replaced
curl -s -o /dev/null -w '%{http_code}\n' -H "Cookie: $C" http://127.0.0.1:56441/bff/v1/projects   # 403
```

`403 permission_denied` and not `401` is the load-bearing detail: the request reached the API
carrying the credential the register had kept, and was refused by `R-50`'s lock rather than by the
absence of a session. Before `R-51` the same cookie would have been `401`.

The file, on the volume, after the sign-in:

```
docker exec $($DC ps -q web) ls -la /var/lib/auditmanager/sessions/
# drwx------ 2 node node 4096 …  .
# -rw------- 1 node node  409 …  register.json
docker exec $($DC ps -q api) ls -la /var/lib/auditmanager/sessions
# ls: cannot access '/var/lib/auditmanager/sessions': No such file or directory
```

So *"mounted by the `web` container and by nothing else"* is true of a running stack and not only
of the compose file, and the file's row carries `login: admin`, `isDefaultCredential: true` and an
`am2.…` credential — `R-51`'s stated cost, on disk, as stated.

### 6b. does `docker compose down --volumes` really sign them out? — **yes**

```
$DC down --volumes
#  Volume jy-w47k-alpha-web-sessions Removing / Removed
$DC up -d
curl -s -o /dev/null -w '%{http_code}\n' -H "Cookie: $C" http://127.0.0.1:56441/bff/v1/projects   # 401
#  {"error_code":"authentication_required","message":"Сеанс на сервере уже закрыт или …"}
```

That is also the negative control for §6a: the same cookie, the same stack, one flag's difference,
`403` → `401`. **And the runbook does not say it** — `Y1`.

### 6c. `R-50`'s whole loop, from the operator's side, on the deployed stack

```
# sign in on the seeded password
POST /bff/v1/session                -> 303  location: /account/password
                                       set-cookie: am_session=…; Path=/; HttpOnly; SameSite=Strict; Max-Age=3600
GET  /bff/v1/projects               -> 403  permission_denied, details.required_capability=password_changed
# change it, through the tier's own route
POST /bff/v1/session/password       -> 303  location: /account/password?outcome=changed
                                       set-cookie: <a NEW session id>
GET  /bff/v1/projects (new cookie)  -> 200
GET  /bff/v1/projects (old cookie)  -> 401     # the change revoked it
```

No `Secure` on the cookie, correctly: the stand is plain HTTP and `sessionCookie()` takes that from
`x-forwarded-proto` rather than assuming (`store.ts:443-453`, `requestIsSecure`).

### Y8 — the `R-4` wipe leaves the credentials on the disk, and nothing says so

Driven to the end, on an instance holding a real uploaded document (a project created and
`fixtures/synthetic/ar/ar_baseline.pdf` uploaded through the BFF — `201`, which is also §7's own
post-wipe write proof):

```
cd /root/w47k
docker exec $($DC ps -q web) md5sum /var/lib/auditmanager/sessions/register.json
# 90749ba15f07c13f8df4de67887983cc

infra/deploy/reset.sh --database jy_w47k --bucket jy-w47k --yes-destroy-everything   # exit 0, 9 s

docker exec $($DC ps -q web) md5sum /var/lib/auditmanager/sessions/register.json
# 90749ba15f07c13f8df4de67887983cc          <-- byte-identical
docker exec $($DC ps -q web) cat /var/lib/auditmanager/sessions/register.json | python3 -c '…'
# login admin | credential am2.eyJleH… 199 chars | isDefault True
# login admin | credential am2.eyJleH… 199 chars | isDefault True
# login admin | credential am2.eyJleH… 199 chars | isDefault False
```

Three complete reviewer credentials, 199 characters each, in a file on the server's disk, after the
command that is the whole of the `R-4` commitment. `reset.sh` cannot reach that volume and does not
try:

```
grep -c -i 'session' infra/deploy/reset.sh          # 2 -- :272 "one psql session" and :304 "this session wrote"
grep -n 'web-sessions\|register.json' infra/deploy/reset.sh   # nothing
```

**What this is not.** It is not an access hole *as measured*: the wipe drops and recreates the
schema, so `app_user` comes back with a new `user_uid` and each of those credentials is refused —
`401`, driven above. The wipe also does not pretend otherwise: §7 is explicit that the wipe does
not touch credentials and that `revoke` is the other half.

**What it is.** `R-51`'s cost is *"until each credential expires, the API credentials sit on the
server's disk"*, and the end-of-pilot procedure now ends with that sentence still true. §7's
sequence — `reset.sh`, then `revoke --everyone`, *"in the same sitting"* — takes the documents and
the access and leaves the credential material. The repair is one line in §7 (and `docker volume rm
<instance>-web-sessions`, or `down --volumes`, is the command that does it), not a change to
`reset.sh`.

### Y-D — `reset.sh --yes-destroy-everything` dies with a silent, undocumented exit 1 when the bucket is empty

Found by running §7's own sequence on a fresh instance. Reproduction, from a deployed stack whose
bucket holds no objects:

```
cd /root/w47k
infra/deploy/reset.sh --database jy_w47k --bucket jy-w47k --dry-run
#   … total: 0 objects            <-- the rehearsal handles empty correctly
infra/deploy/reset.sh --database jy_w47k --bucket jy-w47k --yes-destroy-everything ; echo "exit=$?"
#   reset.sh: dumping into …/dumps/jy-w47k-alpha-20260929T082636Z
#   (three s3-init containers)
#   exit=1              <-- and not one word about why
```

The cause, isolated:

```
$DC run --rm --no-deps --entrypoint sh s3-init -c 'mc --quiet alias set local http://s3:9000 \
  "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null; mc --json stat --recursive "local/jy-w47k"; echo "exit=$?"'
# {"status":"error","error":{"message":"Unable to stat `local/jy-w47k`.","cause":{"message":"Object does not exist",…
# exit=1
```

`infra/deploy/reset.sh:406-407` runs that command with its stdout redirected into
`$DUMP_DIR/objects.stat.json`, under `set -euo pipefail`. On an empty bucket `mc stat` exits 1, the
error JSON lands **in the sidecar file** instead of on the terminal, and the script dies with an
exit status its own `usage()` does not list (it documents `2` for arguments and uses `3` for every
refusal). What is left behind is a dump directory that looks complete:

```
ls -l infra/deploy/dumps/*/
# -rw-r--r-- 1 root root 100701 … database.dump        <-- a real, complete dump
# drwxr-xr-x 2 root root   4096 … objects
# -rw-r--r-- 1 root root    143 … objects.stat.json    <-- {"status":"error", …}
```

Not this wave's code, and not on the path a real end-of-pilot wipe takes (a pilot bucket holds
objects). It is squarely on the path §7 *tells the operator to take* — rehearse, then run it — the
first time he tries it on an instance with nothing in the bucket yet, and it fails in the one shape
this programme has paid for repeatedly: silently, with an exit code nobody documented, leaving a
half-truthful artefact on disk.

**What it is not**: usable-looking to the restore path. `objects.attrs` is written by
`object_attrs.py` *after* the step that fails, so it is absent, and `restore-complete`
(`infra/deploy/reset.sh:212-224`) refuses such a directory by name. The defect is the silence and
the undocumented status, not a dump that would be restored wrongly.

### Where the wipe is right

Everything else §7 claims, driven: it dumped (100 KB `database.dump`, the object mirror and
`objects.attrs`), **verified before dropping**, and refused rather than purging when the sidecar was
incomplete — I gave it a hand-uploaded object with no application metadata and it stopped:

```
reset.sh: REFUSED: the object metadata sidecar is incomplete -- a row is missing an attribute.
    first bad row       : 1:probe/o.txt<tabs>text/plain
  Nothing has been purged. A restore missing blob-role gives back an object that
  reads correctly and answers 409 to the next upload of its own bytes (D-17).
```

That is `D-17`'s lesson enforced at the one moment it can still be acted on. And after a successful
wipe, §7's own checklist holds: the instance comes back (a fresh sign-in on the re-seeded default
password answers `403` per `R-50`, which is the application working), and
`infra/deploy/verify-deployed.sh` still exits `0`.

---

## 7. The runbook, timed — every step I ran, with the condition it ran under

**The host, stated because every figure below depends on it:** the shared development host,
11 GB RAM, `/` at 96% with **4.8 GB free** when I started — against §1's *"**≥ 8 GB** free before
the first deploy"*. The four pinned third-party images and both language base images were already
present. Another judge's `make gate` and two other lanes' stacks were running for part of it.
**None of these is a cold `R-1` host**, and §1 says so about itself first.

| runbook step | command | measured | condition |
|---|---|---|---|
| §2, the one file a human writes | `cp … && chmod 600 && edit` | **< 1 s** mechanically; 9,452 bytes and ~200 lines to read, **17 values to set** | scripted with `sed`; an operator reads the commentary |
| §2, the token | `python3 -c 'import secrets; …'` | < 1 s | §1's optional `python3`; `openssl rand -base64 32` also works and its `+/=` survive the `sed` reader |
| §3, deploy | `infra/deploy/deploy.sh` | **1 m 56 s** | warm build cache from another lane |
| §3, deploy again | `infra/deploy/deploy.sh` | **2 m 22 s** | **empty** build cache (`docker builder prune -af` first), base images present |
| — its slowest steps | | export image **26.9 s**, `npm run build` **21.8 s**, `npm ci` **19.5 s** | from the BuildKit `DONE` lines in the log |
| §4, is it this tree | `infra/deploy/verify-deployed.sh` | **11 s**, exit 0 | 333 web files and the api tree compared |
| §4, after a rebuild | `infra/deploy/reload-proxy.sh` | **2 s** | |
| §9, readiness | `infra/deploy/readiness.sh` | **2 s**, exit 1, 4 findings | `docker` and this repository's `.venv` both present |
| §7, rehearse | `reset.sh … --dry-run` | **3 s** | 17 base tables and one view counted |
| §7, the wipe | `reset.sh … --yes-destroy-everything` | **9 s**, exit 0 | one real uploaded document; dump 100 KB |
| §1's cleanup | `docker builder prune -af` | **17 s**, returned **8.56 GB** | after two deploys |
| a web-container replacement | `compose up -d --force-recreate web` | **4 s** | `R-51`'s subject |
| the whole stack down and up | `compose down && compose up -d` | **28 s** | sessions survive |
| the same with `--volumes` | `compose down --volumes && up -d` | **17 s** | sessions gone |

**The deploy is two and a half minutes, not five, and §1's five-minute figure is not thereby
wrong** — it was measured on an isolated builder that *pulls its own base images*, which this host
did not have to do, and §1 says exactly that (*"a host that does not will pay the full 1.6 GB"*).
What the two figures together say is that the build itself is about two minutes and the rest of §1's
five is the network.

**§1's disk figure is the one an operator should take seriously, and this host is the evidence.**
Starting at 4.8 GB free, the first deploy took `/` to **612 MB (100%)**, at which point
`reset.sh` died in a way I could not attribute until I had re-run it with room — exactly §1's
warning that *"a host at 0 bytes does not fail cleanly ... a deploy that looks like four unrelated
faults"*. After `docker builder prune -af` the same deploy left 6.4 GB free. Two numbers in §1's
disk table are now stale, though, and both are `R-51`'s doing: *"**both** named volumes … ~76 MB"*
(`:124`) — there are three — and the totals built on that line.

---

## 8. Every value the runbook says the owner must supply — is it asked for, and is anything else?

The brief's second question. Compared three ways: what `compose.server.yml` (and the TLS overlay)
substitutes, what `alpha.env.example` defines, and what the scripts read.

```
cd /root/w47k
grep -oE '\$\{[A-Z0-9_]+' infra/deploy/compose.server.yml infra/deploy/proxy/compose.tls.yml \
  | sed 's/.*{//' | sort -u
grep -oE '^#?[A-Z0-9_]+=' infra/deploy/env/alpha.env.example | tr -d '#=' | sort -u
```

**The two sets agree, and that is the right answer.** Sixteen required names
(`ALPHA_INSTANCE`, `ALPHA_HTTP_PORT`, `POSTGRES_DB/USER/PASSWORD`,
`MINIO_ROOT_USER/PASSWORD`, `S3_BUCKET`, `DATABASE_URL`, `S3_ENDPOINT_URL`, `S3_REGION`,
`S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `AUDITMANAGER_API_TOKEN`,
`AUDITMANAGER_PROVIDER_MODE`, `NEXT_PUBLIC_API_BASE_URL`) and four optional ones, each commented
out in the example with the default written beside it (`ALPHA_BIND_ADDRESS`, `ALPHA_HTTPS_PORT`,
`ALPHA_PRESERVE_IMAGE_IDENTITY`, `NEXT_PUBLIC_INSTANCE_LABEL`).

- **nothing is required that the example does not offer.** Driven the hard way: the deploy I ran
  used only the example's own names and `compose up` raised no `:?` refusal;
- **nothing is offered that nothing reads.** Each of the four optional names is read by
  `compose.server.yml`, the TLS overlay or `deploy.sh`;
- **`AUDITMANAGER_SESSION_STORE` is deliberately not among them**, and this is `R-51` done
  correctly. It is a literal in `compose.server.yml:215` with its reason written beside it — *"an
  operator who could set it could point it outside the volume and get a register that silently
  stops surviving deploys"*. It is the one new value this wave could have asked the owner for and
  should not have;
- the provider credential is the second file, optional, `env_file: required: false`, and I brought
  the stack up with **no `provider.env` at all** in `recorded` mode, which is what §2 promises.

Two things about this file that are **not** about the value set, and are `Y6` and `Y9`: it still
tells the operator the browser presents the signing key as a bearer token, and it still says
`ALPHA_INSTANCE` governs *both* named volumes.

One more, small and worth one line: `.gitignore:34` is `infra/deploy/env/*.env`, which does **not**
cover a subdirectory. I discovered that by making the mistake — a scratch copy of my `alpha.env`
under `infra/deploy/env/.jyprobe/` was not ignored and a `git add -A` took it into an earlier
version of this branch. The branch is rewritten and that throwaway instance is destroyed, but the
pattern is one `**` away from covering the shape an operator would reach for when keeping a second
environment beside the first.

---

## 9. Where this wave did the right thing

Said plainly, because a judge that only lists reds is not reporting a measurement.

1. **`R-51` works, and it works for the reason it claims.** A session survives a replaced `web`
   container and a whole-stack `down`/`up`, and is gone after `down --volumes` — driven both ways on
   a deployed stack, with the `403`-vs-`401` distinction proving the credential really came back out
   of the file (§6a, §6b);
2. **The volume is mounted by `web` and by nothing else, on a running stack** — the `api` container
   cannot even see the path (§6a). The `test_session_register_volume.py` set comparison is the right
   shape for that claim and my measurement agrees with it;
3. **The failure modes were thought about before they happened.** A corrupt file is reported and
   recovered from; a write that cannot happen is reported **and does not refuse the reviewer**; an
   unset variable is a named configuration and not a fallback; the mount point is `chown`ed in the
   image *before* `USER node`, which is what makes a fresh volume writable — and I confirmed both
   halves of that mechanism, including the case it protects against (§2d);
4. **The temp-file discipline is real.** On a full filesystem no orphaned `register.json.writing-<pid>`
   was left holding a credential (§2e);
5. **No credential anywhere in the deploy path.** 153 log lines across five containers after a
   sign-in, greppped for the signing key, the database password, any `am2.` credential and the
   seeded password: zero (§4b). `access.check`'s malformed-URL branch deliberately does not print
   the `ArgumentError` that would quote the password;
6. **`R-50` holds end to end from the operator's side** on a real stack, including that the change
   revokes the credential that made it (§6c);
7. **`readiness.sh` is honest about what it could not reach.** Its `UNKNOWN` class exists, is
   documented, and its `off-host-backup` check reports the finding rather than inventing a variable
   that would let someone make it green;
8. **`reset.sh` refused rather than purging** when the object sidecar was incomplete — `D-17`
   enforced at the last moment it can be (§6, *Where the wipe is right*);
9. **`§7`'s rewrite is faithful to `R-41` and `R-42`**, including recording that the runbook argued
   the other way and lost (§1a). Deleting that argument would have been the easier and worse choice.

---

## 10. Questions I could not answer

1. ~~What `reset.sh --restore` does with the dump directory `Y-D` leaves behind.~~ **Closed while
   writing this, statically and then against the artefact.** The empty-bucket failure happens at
   `mc stat`, *before* `object_attrs.py` runs, so `objects.attrs` is never written
   (`infra/deploy/object_attrs.py:80`) — and `restore-complete` (`infra/deploy/reset.sh:212-224`)
   requires exactly that file and refuses by name. The leftover directory holds `database.dump`,
   `objects/` and `objects.stat.json` and no `objects.attrs`, which is what `ls -l
   infra/deploy/dumps/*/` printed. So `Y-D` leaves an unusable artefact that the restore path
   **refuses**, not a misleading one it would accept. `Y-D` narrows to the silence and the exit
   code;
2. **Whether the three credentials the register keeps through the `R-4` wipe become acceptable again
   after `--restore`.** A restore puts `app_user` back with its original `user_uid` and
   `token_epoch`, and the register file was never touched — so within the credentials' one-hour
   lifetime they would be presented against the accounts they were minted for. I did not drive it,
   and outside that hour the register's own sweep drops them. **Stated as a hypothesis, not a
   finding**;
3. **Anything about a real `R-1` host.** Every figure in §7 is from a shared development host that
   already had the base images and was at 96% disk. §1 says this about itself and I cannot improve
   on it;
4. **TLS (§6 of the runbook).** No certificate exists on this host, so I drove neither the
   `enable-tls` switch nor `verify=%{ssl_verify_result}`. `readiness.sh`'s `tls` check reported the
   finding correctly, which is the only half this repository can answer;
5. **Whether `register.json` can be made to hold more than one deployment's credentials** — i.e.
   what happens if two instances are pointed at one volume. `ALPHA_INSTANCE` scopes the volume name
   and `compose.server.yml` makes the path a literal, so it should not be reachable by
   configuration; I did not try to reach it by hand;
6. **The browser side of `R-51`** — whether the session identifier or anything derived from the
   credential reaches `localStorage`, a JS bundle or an HTML payload. That is `W47-JUDGE-A`'s A3 and
   `W47-JUDGE-X`'s entry point, and I deliberately did not duplicate it. I checked only that the
   deployment's own logs and scripts carry nothing (§4b).

---

## 11. The probe, verbatim

Written to `web/.jyprobe/register-probe.ts`, run with `cd /root/w47k/web && node_modules/.bin/vite-node
--config vitest.config.ts .jyprobe/register-probe.ts`, and deleted afterwards. The full filesystem
in case 5 is `mount -t tmpfs -o size=16k tmpfs /tmp/jy-fullfs` filled with `dd`.

```ts
import { chmodSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync, existsSync } from 'node:fs';
import * as m from '@/app/bff/session/store';

const BASE = '/tmp/jy-register';
rmSync(BASE, { recursive: true, force: true });
mkdirSync(BASE, { recursive: true });
const head = (t: string) => console.log('\n===== ' + t + ' =====');

head('1. AUDITMANAGER_SESSION_STORE unset');
delete process.env.AUDITMANAGER_SESSION_STORE;
m.dropTheInMemoryRegister();
console.log('durability:', JSON.stringify(m.sessionDurability()));
{
  const id = m.openSession('admin', 'CRED-UNSET', 3600, false);
  console.log('openSession ok:', id.length === 64, 'count:', m.openSessionCount());
  m.dropTheInMemoryRegister();
  console.log('after restart, subject:', m.subjectOf(id));
}

head('2. durable path, survives a restart');
const good = BASE + '/ok/register.json';
process.env.AUDITMANAGER_SESSION_STORE = good;
m.dropTheInMemoryRegister();
console.log('durability:', JSON.stringify(m.sessionDurability()));
{
  const id = m.openSession('admin', 'CRED-SURVIVOR', 3600, true);
  console.log('file exists:', existsSync(good), 'file mode:', (statSync(good).mode & 0o777).toString(8));
  console.log('dir mode:', (statSync(BASE + '/ok').mode & 0o777).toString(8));
  console.log('credential is in the file:', readFileSync(good, 'utf8').includes('CRED-SURVIVOR'));
  m.dropTheInMemoryRegister();
  console.log('after restart subject:', JSON.stringify(m.subjectOf(id)));
  console.log('after restart credential:', m.credentialOf(id));
  console.log('closeSession removes it:', m.closeSession(id), '-> file has it:', readFileSync(good,'utf8').includes('CRED-SURVIVOR'));
}

head('3. corrupt register file');
const bad = BASE + '/bad/register.json';
mkdirSync(BASE + '/bad', { recursive: true });
writeFileSync(bad, '{"version":1,"sessions":[{"id":"' + 'a'.repeat(64) + '","login":"admin","credential":@"eyJTOKEN-SENTINEL-XYZ","openedAt":1,"expiresAt":99999999999999}]}');
process.env.AUDITMANAGER_SESSION_STORE = bad;
m.dropTheInMemoryRegister();
console.log('count (0, must not throw):', m.openSessionCount());
console.log('still serves a new sign-in:', m.openSession('admin', 'CRED-AFTER-CORRUPT', 3600, false).length === 64);

head('4. unwritable directory (fresh volume owned by root)');
const ro = BASE + '/ro';
mkdirSync(ro, { recursive: true });
const roFile = ro + '/register.json';
chmodSync(ro, 0o500);
process.env.AUDITMANAGER_SESSION_STORE = roFile;
m.dropTheInMemoryRegister();
{
  const id = m.openSession('admin', 'CRED-RO', 3600, false);
  console.log('sign-in succeeds:', id.length === 64, '| subject readable:', m.subjectOf(id) !== null);
  console.log('file written:', existsSync(roFile));
  console.log('sessionDurability() claims:', JSON.stringify(m.sessionDurability()));
  m.dropTheInMemoryRegister();
  console.log('after restart subject:', m.subjectOf(id));
}
chmodSync(ro, 0o700);

head('5. full filesystem');
const full = '/tmp/jy-fullfs/register.json';
process.env.AUDITMANAGER_SESSION_STORE = full;
m.dropTheInMemoryRegister();
{
  const id = m.openSession('admin', 'CRED-FULL', 3600, false);
  console.log('sign-in succeeds:', id.length === 64, '| subject readable:', m.subjectOf(id) !== null);
  console.log('leftover files on the full fs:', readdirSync('/tmp/jy-fullfs'));
}
```

And the three-line image behind §2d:

```dockerfile
FROM node:24-bookworm-slim@sha256:ba849c60be29959425b8734d57b8b4b7d56f98edd9504c9af091d5281095a71e
RUN mkdir -p /var/lib/auditmanager/sessions \
 && chown node:node /var/lib/auditmanager/sessions \
 && chmod 700 /var/lib/auditmanager/sessions
USER node
```

`docker build` refuses a context outside the clone on this host — `D-37`, the snap build whose
private `/tmp` is not the shell's. The runbook's §10 row is right and I hit it: a `Dockerfile` in
the scratch directory answered *"failed to read dockerfile"* for a file that was plainly there.

---

## 12. `make gate`, run literally, and the counts reconciled by test id

### Y-E — the baseline this wave is accounted against is cited to a file that does not contain it

> **Corrected at cross-examination, and the correction is against me.** The paragraph below
> concluded that 2567 / 1139-in-81 *"has never been printed by a gate"*. **That is false.**
> `/root/w47-a-merged-gate.log` — the gate on merged sub-stage A — prints `2567 passed, 5 skipped`
> at line 125 and `Test Files 81 / Tests 1139` at lines 230-231, and `GATE OK` at 235. The figure
> was measured; only its attribution is wrong. I reached the wrong conclusion by searching the
> document the brief named and reasoning about the world instead of about the pointer —
> `OPERATING_CONSTRAINTS.md` §12, and §15.4 records it as the fourth shared assumption in this
> pair of reports. **What stands:** the number is not in `W47-DISPATCH.md`, which states 2516 and
> 1135 in 80 on the line a reader checks, and `W47-LOCK.md:334,336` and both judges' briefs cite
> it there. What follows is the original text, kept rather than rewritten.

Before running anything, I went to get the baseline my brief named — *"battery 2567 passed / 5
skipped, foundation 35, frontend 1139 in 81 files, from `docs/program/dispatch/W47-DISPATCH.md`"*.
It is not there:

```
cd /root/w47k
grep -c '2567' docs/program/dispatch/W47-DISPATCH.md      # 0
grep -c '1139' docs/program/dispatch/W47-DISPATCH.md      # 0
sed -n '14,18p'  docs/program/dispatch/W47-DISPATCH.md
#  **Baseline, measured on 1196ca7** … GATE OK, battery 2516 passed / 5 skipped,
#  foundation 35, frontend 1135 in 80 files. /root/w46-final-gate.log.
grep -rn '2567' docs/ | grep -v W47-JUDGE-Y
#  docs/program/W47-LOCK.md:334: | battery | 2581 … | 2567 passed / 5 skipped | +14 |
```

`2567` occurs **once in the repository**, as `W47-LOCK.md`'s own citation of a baseline it
attributes to `W47-DISPATCH.md`. What it actually is, is the arithmetic of two sub-stage A gates
run on two different branches:

| | measured by | battery | foundation | frontend |
|---|---|---|---|---|
| baseline | `/root/w46-final-gate.log` on `1196ca7` (`W47-DISPATCH.md:14-18`) | 2516 / 5 skipped | 35 | 1135 in 80 |
| `W47-GATE` | its own final gate (`docs/program/W47-GATE.md:189-200`) | 2550 (**+34**) | 35 | 1135 in 80 (0) |
| `W47-PASS` | its own final gate (`docs/program/W47-PASS.md:320-335`) | 2533 (**+17**) | 35 | 1139 in 81 (**+4, +1 file**) |
| **the sum, after both merged** | **nothing** | **2567** | 35 | **1139 in 81** |
| `W47-LOCK` | its own final gate on `4a4a5d8` (`docs/program/W47-LOCK.md:313-337`) | 2581 (**+14**) | 35 | 1156 in 82 (**+17, +1 file**) |

2516 + 34 + 17 = 2567 and 1135 + 4 = 1139 both check out, so the number is *sound*. ~~It has
simply **never been printed by a gate**~~ — **wrong, see the correction above: a gate on merged
sub-stage A printed exactly it.** The row "the sum, after both merged | **nothing**" in the table
should read `/root/w47-a-merged-gate.log`, and the defect is that neither that log nor `45d784f`
is named anywhere a reader of `W47-LOCK.md` or of a judge's brief can follow.

The consequence for me is small — it is the right number to reconcile against — and the
consequence for the wave is that a reader who checks the citation finds two different numbers and
cannot tell which is stale. That is what happened to me.

### The gate, run literally

```
cd /root/w47k && make gate > /root/w47k-gate.log 2>&1        # literally, nothing else
grep -n 'GATE OK' /root/w47k-gate.log
290:GATE OK: battery, foundation, frontend and whitespace all pass
```

**Read out of the log, never from an exit code.** The run took **991 s** wall clock
(16 m 31 s) on `eaf3725` — this report file and nothing else on top of `44937fe`:

```
git diff --name-only 44937fe..HEAD     # docs/program/reviews/W47-JUDGE-Y.md
git status --short                     # empty, before and after; nothing was edited while it measured
```

| | this gate | the wave's stated baseline | the last **measured** baseline |
|---|---|---|---|
| battery | **2581 passed / 5 skipped**, 169 subtests, 874.62 s | 2567 / 5 → **+14** | 2516 / 5 on `1196ca7` → **+65** |
| foundation | **35 passed**, 43.67 s | 35 → 0 | 35 → 0 |
| frontend | **1156 passed in 82 files** | 1139 in 81 → **+17, +1 file** | 1135 in 80 → **+21, +2 files** |

**Nothing running against it.** `make gate` PID `1690176`, `readlink /proc/1690176/cwd` →
`/root/w47k`; `ps -eo pid,args | grep -E "make gate|vitest|pytest"` was empty before it started,
and `free -m` reported **4029 MB available**. The sibling judge's gate in `/root/w47j` had ended
(`GATE OK`, the same three numbers) and I waited for it rather than running beside it.

**The +14, by test id**, all nine of the API ones and all five of the volume file, each confirmed
present in the tree this gate measured:

```
cd /root/w47k
.venv/bin/python -m pytest -q --collect-only   tests/integration/auth/test_the_exchange_over_real_users.py   tests/integration/api/test_authorization.py   tests/integration/composition/test_session_register_volume.py
#  55 tests collected
for t in test_the_exchange_reports_a_default_credential_as_one … ; do grep -rn "def $t" tests/; done
#  each exactly once
grep -n '^def test_' tests/integration/composition/test_session_register_volume.py   # 5
```

| file | ids |
|---|---|
| `tests/integration/auth/test_the_exchange_over_real_users.py` | `…reports_a_default_credential_as_one`, `…reports_a_changed_credential_as_not_default`, `test_changing_a_default_password_turns_the_field_off_in_the_same_answer` |
| `tests/integration/api/test_authorization.py` | `test_a_default_credential_reaches_exactly_the_register`, `test_the_password_change_is_the_one_operation_that_still_answers`, `test_the_exchange_still_answers_and_says_which_state_the_account_is_in`, `test_the_same_surface_serves_the_same_credential_once_the_flag_is_off`, `test_changing_the_password_lifts_the_refusal_on_the_very_next_request`, `test_a_revoked_default_credential_is_refused_as_revoked_and_not_as_default` |
| `tests/integration/composition/test_session_register_volume.py` (whole file) | `test_the_block_split_finds_the_services_this_stack_has`, `test_the_register_volume_is_declared_and_named`, `test_exactly_one_service_mounts_it_and_that_service_is_web`, `test_the_web_service_is_told_where_the_register_goes`, `test_the_image_owns_the_mount_point_so_the_process_can_write_to_it` |

3 + 6 + 5 = **14**. No baseline id is missing: the battery moved only upward, and the skip count is
the same five.

**The +17 and the 82nd file**, counted the way `W47-LOCK.md` counted them and against the wave-46
tip rather than against its own prose:

```
cd /root/w47k
for f in web/tests/unit/screens/forms-and-pages.test.ts web/tests/unit/session/bff-session.test.ts; do
  echo "$f base=$(git show ce25e14:$f | grep -cE '^\s*it\(') now=$(grep -cE '^\s*it\(' $f)"; done
#  forms-and-pages  base=15 now=16
#  bff-session      base=16 now=18
grep -cE '^\s*it\(' web/tests/guards/default-credential-screens.guard.test.ts   # 9  (new file)
grep -cE '^\s*it\(' web/tests/guards/session-durability.guard.test.ts          # 8  (3 -> 8)
find web/tests -name '*.test.ts' | wc -l                                         # 82
```

9 + 5 + 2 + 1 = **17**, and `default-credential-screens.guard.test.ts` is the 82nd file. One caution
for whoever re-checks this: `forms-and-pages.test.ts` also holds one `it.each`, so a grep for
`it(` **or** `it.each` answers 17 and not 16 — the runtime count is what the gate printed, and it
agrees with the `it(` count here only because that `it.each` was already in the base.

**So the chain closes:** 2516 measured → +34 (`W47-GATE`) → +17 (`W47-PASS`) → +14 (`W47-LOCK`) =
2581, measured here for the first time on the merged tip, and independently by `W47-JUDGE-X` in
`/root/w47j` within the same hour. `1135 → +4 → +17 = 1156 in 82`. Foundation never moved.

---

## 13. What this judge left in the tree

**Nothing but this file.**

```
cd /root/w47k
git diff --name-only 44937fe..HEAD
#  docs/program/reviews/W47-JUDGE-Y.md
git status --short
#  (empty)
```

Everything the probes created was removed:

| created | removed |
|---|---|
| `infra/deploy/env/alpha.env` (git-ignored) and `infra/deploy/env/.jyprobe/` | `rm -rf` |
| `web/.jyprobe/` (the probe and the three-line `Dockerfile`) | `rm -rf` |
| the throwaway instance `jy-w47k-alpha` — five containers, three volumes, one network | `compose down --volumes --remove-orphans` |
| the two images `jy-w47k-alpha-api`, `jy-w47k-alpha-web`, and `jy-voltest` | `docker image rm -f` |
| the volumes `jy-fresh`, `jy-rootvol` | `docker volume rm` |
| `infra/deploy/dumps/` (four dump directories, one of them a real 100 KB dump) | `rm -rf` |
| the `tmpfs` at `/tmp/jy-fullfs`, and `/tmp/jy-register` | `umount`, `rm -rf` |
| the build cache both deploys produced | `docker builder prune -af` — returned 8.56 GB, and `/` ended at **9.6 GB free** against the 4.8 GB it started at |

What is deliberately **left running** is the lane's own three containers —
`gate-w47k-postgres-1`, `gate-w47k-s3-1`, `gate-w47k-s3-init-1` — brought up by `make gate`'s
`foundation` step and governed by the frozen `make up`/`make down`, exactly as lanes `gate-w47j`,
`gate-w47b` and `gate-b0` leave theirs. They hold no deployment state and `make down` in this
worktree removes them.

Two disclosures, because a judge who hides his own mistakes is not one:

1. **An earlier version of this branch committed two probe files**, one of them a copy of the
   throwaway instance's `alpha.env` — `.gitignore:34`'s `infra/deploy/env/*.env` does not match a
   subdirectory, and a `git add -A` took it. The branch history is rewritten to drop them; the
   instance, its volumes and its images are destroyed and the values authorise nothing anywhere;
2. **I ran a full docker build while the host was at 4.8 GB free**, took `/` to 612 MB, and one
   `reset.sh` run failed in that state before I could attribute it. I re-ran everything after
   `docker builder prune -af` and every figure in §7 and §12 is from the second, uncontended pass.
   The host is left with more free space than it had. **No process not my own was killed, and
   nothing was killed by pattern.**

---

## 14. Y-F — §2 says the signing key goes "into no request header". It goes into one, on every sign-in

Found by following the brief's last question — *does anything in the deploy path print, log or
**forward** a credential?* — past the logs, which are clean (§4b), into the forward itself.

`DEPLOYMENT_RUNBOOK.md:166-170`:

> **Since wave 34 this is the key the API signs reviewer credentials with, not a token anyone
> presents.** Whoever holds it can mint a credential for any subject, so it **goes to the API
> process and nowhere else — not to a reviewer, not into a browser, not into a request header.**

Two of those three hold. The third does not, and the second clause — *"the API process and nowhere
else"* — does not either. The chain, four greps:

```
cd /root/w47k
grep -n 'AUDITMANAGER_API_TOKEN' infra/deploy/compose.server.yml
#  173:   api: … (the signing key, where it belongs)
#  208:   web: … "The web tier forwards it; without it every operation answers 401."
sed -n '378,401p' web/src/app/bff/v1/\[...path\]/route.ts
#  token = getApiToken();            <-- the deployment's key, in the web process
#  … forwardWithCredential(new Request('…/bff/v1/auth/token', …), EXCHANGE_SEGMENTS, { upstream, token })
sed -n '155,166p' web/src/shared/api/credentialed-forward.ts
#  // Set last and unconditionally: the deployment's credential is the only one that goes.
#  headers.set('authorization', `Bearer ${token}`);
python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(d['paths']['/auth/token']['post']['security'])"
#  []            <-- issueToken publishes an EMPTY security requirement
```

So on every sign-in the signing key travels `web` → `api` in an `Authorization: Bearer` header, to
an operation the contract declares needs no credential at all. The route file knows and says so —
*"the exchange ignores it … Stripping the header for this one call would mean a second forwarding
path through `credentialed-forward`, which is a wider seam bought for nothing"* — so this is a
deliberate, documented trade inside `web/`. **What is wrong is the runbook's absolute sentence**,
which an operator reads while deciding where this value may go, in the paragraph written to repair
an earlier falsehood of exactly this kind (`OPERATING_CONSTRAINTS.md` §4.7 exists because two
runbooks told an operator to hand the key out).

It is also worth naming what the exposure is and is not. **Is:** key material in a request header
on the compose network, and in a second container's environment — so `docker exec <web> env`, a
`web`-side crash dump, or any future request log on that hop yields the key that mints a credential
for any subject. **Is not:** anything a browser can reach; `NEXT_PUBLIC_` is not involved and
`W15-AUTH`'s build-and-grep proof is untouched.

Two repairs are available and they are not equivalent, which is why this is a finding and not a
patch:

- **the cheap one** — three words in `DEPLOYMENT_RUNBOOK.md:168-170`: *"not to a reviewer, not into
  a browser, and into no request header any reviewer can reach"*, plus the fact that the `web`
  container is given it too. This makes the document true and changes no behaviour;
- **the real one** — stop handing `web` the key at all. `issueToken` needs no credential, and the
  exchange is the only place `web` reads it; the cost is the second forwarding path the route file
  names. That is a decision about who can mint a credential, which under `R-29` §2 is the owner's
  and not a wave's.

`compose.server.yml:208`'s own justification is stale in the same direction: *"The web tier
forwards it; without it every operation answers 401."* Since wave 34 operations are authorized by
the **reviewer's** minted credential; without this value what fails is `openTheSession`, which
answers `refuseSignIn('unconfigured')` — nobody can sign in, so every operation answers 401 for a
different reason than the sentence gives.

---

## 15. Cross-examination of `W47-JUDGE-X` (`a41b4f9`, `/root/w47j`)

X entered from the attacker's side and, by its own §4, **never brought the deployed topology
up**: it drove a bare `serve.py` on `127.0.0.1:8000` and `next dev` on `:3100`. I drove
`compose.server.yml` behind nginx on one published port. So every X conclusion that depends on
*where the request enters* is one I can test and X could not. **Each verdict below carries a
measurement X did not take.** The stack was rebuilt for this section (`/root/w47k-deploy3.log`),
driven, and destroyed; `docker volume ls --filter name=jy-w47k` is empty.

### 15.1 The verdicts

| X's claim | verdict | the measurement X did not take |
|---|---|---|
| **§1.1** the API is fail-closed, even `openapi.json`; 20 operations, 18 protected | **upheld** | X enumerated from `contracts/api/v1/openapi.json` — the document under test. The deployed process's own count, from `deploy.sh`'s `schema-conforms` guard against the running API: `frozen ops : 20 / served ops : 20 / differences: 0`. And through the proxy, `/api/v1/openapi.json` → **401** |
| **§1.2** a default credential gets 403 `required_capability: password_changed` on all 18, **before resource resolution** | **upheld, and strengthened** | all 18 re-driven **through nginx** on the deployed stack with non-existent ULIDs → **403 × 18, no other status**; detail confirmed. Then the anti-vacuity X never took: the *same* ids with a **changed** credential → **404, 404, 404, 404**, and `/dashboard` → **200**. X showed the 403; I showed the 404 was reachable, which is what makes "before resolution" mean anything |
| **§1.3** the change lifecycle: 422s, 401 on a wrong current password, epoch bump, old token dead at once | **upheld** | driven end to end **through the published port and the BFF** rather than against a bare API: `POST /bff/v1/session` → 303 `/account/password`; `/bff/v1/projects` → 403; `POST /bff/v1/session/password` → 303 `?outcome=changed` **with a new cookie**; new cookie → 200; old cookie → 401 |
| **§1.4** path normalisation and casing give no unauthenticated route — incl. `/api/v1/dashboard` → **404** | **narrowed** | that 404 is an artefact of X's topology. In the deployment `/api/v1/…` **is** the public path: `/api/v1/dashboard` → **401**, `//api/v1/dashboard` → 401, `/api/v1//dashboard` → 401, `/api/v1/./dashboard` → 401; `/API/v1/…`, `/api/V1/…`, `/api/v1/Dashboard`, `/api/v1/../dashboard`, `%2e%2e` → 404 **at nginx**, a different refuser than the one X exercised. **The conclusion survives — no unauthenticated route reaches a protected operation — but the evidence X gave for it does not describe the deployed origin.** One more the topology adds: `/dashboard` with no prefix → **200**, because that string is the *web screen*, not the API operation. The same word is two things behind one origin |
| **§1.4** the raw `AUDITMANAGER_API_TOKEN` as a bearer → 401; the signing key cannot act | **upheld** | re-driven **through the proxy**, three header shapes (`Bearer <key>`, bare `<key>`, `X-API-Key`) on `/api/v1/projects` and `/api/v1/dashboard` → **401 in all six**, and `/bff/v1/projects` with the same header → **401**. The 200 those calls get on `/api/v1/auth/token` is `issueToken` ignoring the header, which is its declared `security: []` |
| **§1.5** the register is `0600`, not servable, and the JWT is in no served HTML or bundle | **upheld, on a different artefact** | X grepped a `next dev` server. I grepped the **production build behind nginx**: 5 HTML pages + **17 `_next/static` JS bundles actually referenced and fetched** (728 KB) → **0 files** containing the live credential, **0** containing any `am2.`, **0** containing the signing key, and **0** containing even the session id. Five traversal shapes at the origin (`/var/lib/…/register.json`, `/_next/../var/lib/…`, `/api/v1/../../var/lib/…`) → **404** |
| **§1.5** sessions outlive the process | **upheld, and the stronger event measured** | X restarted the `next dev` **process**. I replaced the **container** (`up -d --force-recreate web`, new container id) and then the whole stack (`down` + `up`), and the same cookie still answered — plus the negative control X had no volume for: `down --volumes` → **401** |
| **§1.5** revocation is immediate wherever the token is kept | **upheld in its password-change form; not re-measured in its `revoke` form** | I drove the change-revokes-at-once half on the deployed stack (old cookie → 401 on the very next request). I did **not** run `python -m auditmanager.access.revoke` against the deployed database — and `Y-C` is why that is not a small omission: as §7 writes that command, the host §1 describes cannot run it |
| **§2.1** no test-only branch, flag or fixture bypasses the refusal; the seam reads the account row | **upheld, by a different kind of evidence** | X grepped the source. I exercised the **built image**: the refusal fires in a container built by `deploy.sh` from this tree, with no test harness anywhere near it, on all 18 operations. A source grep cannot show that what was built enforces what was read; this does |
| **§2.2** the four mutations X ran (M1, M3, W2, R1) are non-vacuous | **upheld — and X's abstention from the other eleven is now closed** | I ran **the eleven X declined**: V1, V2, V3, M2, M4, M5, R2, W1, W3, W4, W5. Every one reddened exactly the test `W47-LOCK.md` §8 names, with the counts it states (M2 `3 failed / 33 passed`; M4 `2 failed / 12 passed`; M5 `1 failed / 35 passed`; R2 `2 failed / 6 passed`; W1 `2 failed / 7 passed`; W3/W4 one each; W5 one). **All fifteen rows of that table are now reproduced by a judge**, and the tree was `git checkout --`'d and verified clean after each |
| **§2.3** the reseal is coherent across four documents by digest | **upheld, against a running artefact** | X compared files on disk. The deploy's last guard compared the **document the deployed process serves** with the frozen contract inside the image: `differences: 0` over 20 operations. That is the reseal checked where a client meets it |
| **F1** the `changePassword` contract text contradicts the enforced `R-48` policy | **upheld, and X's own counter-argument falsified** | see §15.2 |
| **F2 / `D-101`** the shipped default is a legal new password | **upheld, not re-driven** | I did not repeat X's `password` → `Password` change. What I add is a code reading, labelled as one: `readiness.sh`'s `default-credential` check greps `access-check DEFAULT CREDENTIAL`, which is the `is_default_credential` **column**. It flips to `OK` on *any* accepted change, so the operator's own readiness command reports step 5 done for a change the policy should arguably have refused. `D-101` is therefore invisible to the one command an operator runs before publishing |
| **§5** `GATE OK`, 2581 / 35 / 1156 in 82, +14 and +17 by test id | **upheld, independently** | my own `make gate` printed the same three numbers on the merged tip (§12), run after X's had finished. X's caution that `forms-and-pages.test.ts` runs **20** at runtime while a strict `it(` count says 16 is **confirmed**: my W5 mutation run printed `1 failed | 19 passed (20)` on that file |

**Nothing of X's is falsified.** One entry is narrowed (`§1.4`'s `/api/v1/dashboard → 404`), one
counter-argument inside `F1` is falsified (§15.2), and one claim of X's is upheld by evidence X
could not have produced (the production bundle). X's verdict — *"the wave does what it claims
where I could reach it"* — holds where X could not reach, too.

### 15.2 `F1`: upheld, X's counter-argument falsified, and where the sentence belongs

X reports `F1` at low severity and states the honest counter-argument: *"The word 'declares' is
defensible for a document whose schema `minLength` is 1."* **That is the one thing of X's I
think is wrong, and the disproof is the next sentence of the same description:**

```
python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));
print(d['components']['schemas']['ChangePasswordRequest']['properties']['new_password']['description'])"
```

> The password the account will hold. **The bounds are mechanical, not a policy: this surface
> declares no minimum length, no complexity rule, no history and no expiry.** *A value equal to
> `current_password` is `validation_failed`, because a change that changes nothing would report
> a password as changed when it was not.*

The paragraph **declares a rule in its own next clause**, and that rule is in no JSON Schema
keyword — it is prose. So within this document "declares" already includes prose declarations,
and the sentence is false on the document's own usage, not merely ambiguous. X read the word
alone; the sentence beside it fixes its meaning.

A second measurement X did not take, and the one that settles severity: **the tree's own client
already contradicts the sentence.**

```
grep -n "minLength" web/src/features/change-password/ui/change-password-form.tsx
#  76:          minLength={8}
#  92:          minLength={8}
```

The only client in this repository hard-codes the minimum the contract says is not declared —
and it did not get the 8 from the contract, because the contract does not carry it. That is the
drift `F1` names, one level deeper than X took it: not "a sentence a hypothetical caller might
misread", but **a number a real client is already carrying out of band.**

**Where the corrected sentence belongs — my answer to the reseal question.**

- **In that description, and nowhere else.** The false clause is there; the sentence that fixes
  its meaning is there; and the `422` on this operation is a `$ref` to the shared
  `#/components/responses/ValidationFailed`, so a correction placed there would be a claim about
  all twenty operations made to fix one.
- **It must not restate the policy.** Writing "minimum 8" into the contract gives the transport
  document a second authority over `src/auditmanager/access/policy.py`, makes every future
  policy change a reseal, and destroys the property `R-48` was built for — `policy.py` argues
  the policy belongs at the access boundary precisely so a deployment can change it without
  renegotiating the contract. **The repair is to stop claiming there is no policy, not to
  publish the policy.** Something of this shape: *"The bounds are mechanical. The deployment
  enforces a password policy on this operation — a refusal is `validation_failed` and names the
  rule in `message` — and that policy is not declared here, because it is the deployment's and
  may differ between them. No history and no expiry are enforced."*
- **"no history and no expiry" can stay**: nothing in `policy.py` enforces either. Only "no
  minimum length, no complexity rule" is false.
- **The cost is exactly one reseal of four documents** — the contract, the byte-identical mirror
  `web/openapi/openapi.json`, `web/src/shared/api/generated/types.gen.ts` and
  `web/FRONTEND_LOCK.json` — the same four `ff1db5e` moved. **Nothing in prose rides along**:
  `grep -rln "declares no minimum length"` finds those three files and no `.md`.
- **On whether to spend your one reseal on it: conditionally.** `F1` admits nothing and does not
  force a reseal by itself. But `F2`/`D-101` is the other candidate and it changes **behaviour**,
  not text — and if the owner closes `D-101` by adding the shipped default to the blocklist, this
  description is rewritten a second time. **If a `D-101` ruling is close, hold and land both in
  one reseal; if it is not, correct the sentence now** — because the version of this sentence
  that is safe under either outcome is the one that declares no policy content at all, which is
  the wording above.

### 15.3 A finding the cross-examination produced: `Y-G`

Neither judge had this, because it needs the proxy and X had none.

**A trailing slash on any `/api/v1/…` path returns a `307` whose `Location` drops both the
`/api/v1` prefix and the port.**

```
curl -s -i --path-as-is 'http://127.0.0.1:56441/api/v1/dashboard/' | grep -iE '^HTTP|^location'
#  HTTP/1.1 307 Temporary Redirect
#  location: http://127.0.0.1/dashboard
curl -s -i --path-as-is 'http://127.0.0.1:56441/api/v1/projects/' | grep -i '^location'   # http://127.0.0.1/projects
curl -s -i --path-as-is 'http://127.0.0.1:56441/api/v1/runs/'     | grep -i '^location'   # http://127.0.0.1/runs
```

Two faults in one header, and `infra/deploy/proxy/nginx.conf` is where both live:

1. **the port is gone.** `proxy_set_header Host $host` — and `$host` carries no port — so the
   application builds an absolute redirect to `http://127.0.0.1/…`, i.e. **port 80**, which is
   not this deployment. Over the owner's own tunnel (`ssh -L 31500:…`) that sends the browser to
   whatever is on port 80 of *the operator's laptop*;
2. **the `/api/v1` prefix is gone**, because `proxy_pass http://api:8000/` strips it and nothing
   puts it back. So an API path redirects the caller to the **web screen** of the same name —
   `/api/v1/dashboard/` → `/dashboard`, which answers **200** with no credential.

It is not a bypass: the screen renders empty and its data calls answer 401 (§15.1). It is a
correctness defect in the one published origin, and `T-2`'s "one origin" claim is the thing it
bends — a redirect that leaves the origin's port is no longer one origin.

```
grep -n 'proxy_redirect\|absolute_redirect\|http_host' infra/deploy/proxy/nginx.conf   # nothing
grep -rn '307\|trailing slash' infra/deploy/README.md docs/program/DEPLOYMENT_RUNBOOK.md  # nothing
git log --oneline -1 -- infra/deploy/proxy/nginx.conf   # 4f6d9a4 -- not this wave
```

Not wave 47's, and not in anyone's register. The one-line repairs are `proxy_set_header Host
$http_host;` (restores the port) and a `proxy_redirect` rule or `redirect_slashes=False` on the
app (restores or removes the prefix hop) — but which of the two is right is a decision about the
published surface, so it is named here rather than patched.

### 15.4 Where X's method shares an assumption with its subject — `OPERATING_CONSTRAINTS.md` §12

Four, and the fourth is mine.

1. **X's probe inherited its subject's coordinate system, and that is §12's exact shape.** X
   attacked the URL space the *application* defines and read the result as a property of the
   *deployment*. `/api/v1/dashboard → 404` is recorded under *"bypasses attempted that did NOT
   work"*, where a 404 reads as "there is no such door". In the deployment that is the front
   door, and it answers 401. The query could not see the subject being wrong about its own
   surface because the query asked the subject where its surface was. Nothing X concluded turns
   out to be false — but the **evidence** for the safest-sounding line in the report describes a
   topology the owner will never deploy.
2. **X built its input out of the document under test.** The "18 protected operations" X looped
   over came from `contracts/api/v1/openapi.json`. An operation served but not declared would be
   absent from the loop and therefore unprobed, and the loop would still report 18/18 clean —
   §12's *"never build an expectation, or an input, out of the thing under test"*. The gap is
   closed, but **not by X's method**: `deploy.sh`'s `schema-conforms` guard compares the served
   document with the frozen one inside the image (`differences: 0`), which is an independent
   witness X did not call.
3. **X's mutation abstention is a sample supporting "there are none".** X ran 4 of 15 and
   reasoned that *"M1/M3 exercise the same seam and W2/R1 the same two modules, and the doc's
   table is internally consistent with what I did reproduce"* — the shape §12 records as
   `head -20` read as the answer. Four of fifteen agreeing with the table is evidence the table
   is honest about those four. **I ran the other eleven and the inference happens to hold** —
   which makes it correct and unearned, and that distinction is the whole of §12.
4. **And mine, which is the worst of the four, because §12's third instance was the integrator's
   and this one is the same.** `Y-E` concluded the baseline 2567 / 1139-in-81 *"has never been
   printed by a gate"* from its absence in the document the brief cited. My query assumed the
   citation named the measurement. It did not, and the measurement exists:

   ```
   sed -n '125p;230,231p;235p' /root/w47-a-merged-gate.log
   #  2567 passed, 5 skipped, 4 warnings, 169 subtests passed in 650.98s (0:10:50)
   #   Test Files  81 passed (81)
   #        Tests  1139 passed (1139)
   #  GATE OK: battery, foundation, frontend and whitespace all pass
   ```

   A gate **did** run on merged sub-stage A and printed exactly those numbers. I searched the
   document I was pointed at, found different numbers, and wrote a conclusion about the world
   instead of about the pointer. `Y-E` is corrected in §12 and in the table: the figure is
   **measured**, the **citation** is wrong, in both judges' briefs and in `W47-LOCK.md:334,336` —
   and X reconciled against the same misattributed line (*"the `W47-DISPATCH.md` baseline I was
   given"*), so the error reached both of us and neither of us caught it from the number alone.

**Where X's method beat mine**, said because a cross-examination that only finds faults is doing
the same thing §12 warns about. X wrote and committed the whole attack phase **before reading one
line of the diff** — an ordering I did not use and could not have retrofitted. And X took one
measurement on the counts I did not: `git grep -l "def <id>" a53d4a1^ -- tests` to show the
fourteen ids did **not** exist at the wave's base. I only showed they exist now. X's is the
stronger half of the same claim, and X's three-way caution about `it(` counting is more careful
than my single note.

---

## 16. `R-52` driven end to end on a deployed stack — **upheld**

The wave's record rested on a stub that records `docker` calls. This section is the same
mechanism driven against `compose.server.yml` behind nginx on one published port, built from
`6ad43a0` by `infra/deploy/deploy.sh` (`/root/w47k-deploy4.log`). Branch `agent/w47-judge-y2`;
instance `jy-w47k-r52`, port `56441`; `verify-deployed.sh` → **exit 0, "the deployed stack IS
this tree (6ad43a0)"**. Destroyed afterwards: `docker volume ls --filter name=jy-w47k` is empty,
host left at 7.8 GB free and 5.7 GB of memory.

**Verdict: `R-52` is upheld. Every clause of the ruling is true of a real deployment**, including
the one the stub could not reach — `auditmanager.access.revoke` runs inside the `api` image in a
real deploy. One narrowing, in §16.6, and it is about `--restore` rather than about the ruling.

**The instrument, stated because it is what makes "every row" mean anything.** Before the dump I
inserted a **second** account, `judgey2`, copied from the seeded row (so also on the shipped
digest) but carrying `token_epoch = 7` — a value no code would produce. A global
`SET token_epoch = 2` and a per-row `token_epoch + 1` are indistinguishable on one row and
obvious on two.

```
$DC exec -T postgres psql -qtAX -U jy_r52 -d jy_r52 -c \
  "SELECT login||' default='||is_default_credential||' epoch='||token_epoch FROM app_user ORDER BY login;"
#  admin   default=true epoch=1
#  judgey2 default=true epoch=7
```

### 16.1 `--restore` against a pre-change dump — the ruling's own sequence, driven

**The sequence.** default → dump → forced change → restore.

```
# 1. a session on the shipped pair, so the register holds a credential
curl -s -i -X POST -F login=admin -F password=password http://127.0.0.1:56441/bff/v1/session
#    303  location: /account/password   set-cookie: am_session=661f58af…
#    register.json  -rw------- 409 bytes  md5 48d9bd464b7c5f877989baf7012f4bde

# 2. the dump, taken while BOTH accounts are on the shipped password
infra/deploy/reset.sh --database jy_r52 --bucket jy-r52 --yes-destroy-everything   # exit 0, 24 s

# 3. the forced change, through the API
POST /api/v1/auth/token    {"login":"admin","password":"password"}      -> 200
POST /api/v1/auth/password {"current_password":"password", …}           -> 200  (token N)
#    admin default=false epoch=2 ;  token N on /api/v1/projects -> 200
#    the shipped pair now: POST /api/v1/auth/token -> 401     <- the window is shut

# 4. the restore
infra/deploy/reset.sh --database jy_r52 --bucket jy-r52 --restore infra/deploy/dumps/<stamp>
#    exit 0, 6 s
```

**Does `token_epoch` actually rise on every row? — yes, per row, not by assignment.**

```
$DC exec -T postgres psql … "SELECT login||' epoch='||token_epoch||' moved='||token_epoch_updated_at …"
#  admin   default=true epoch=2 epoch_moved=2026-09-29 13:28:39.728011+00
#  judgey2 default=true epoch=8 epoch_moved=2026-09-29 13:28:39.728011+00
```

The dump carried `1` and `7`; the database reads `2` and `8`, both stamped at the same instant.
**`judgey2` is the measurement**: an assignment would have made it `2`.

**Does the script actually name the account that came back on its default password? — yes, both,
by login**, from the script's own screen (`/root/w47k-r52-restore.log`):

```
access-check DEFAULT CREDENTIAL: login=admin   user_uid=usr_01M3PMEYCBGSA08126KCM98E71 …
access-check DEFAULT CREDENTIAL: login=judgey2 user_uid=usr_01JZZZZZZZZZZZZZZZZZZZZZZZ …
access-check: 2 account(s) still hold the seeded password. …

reset.sh: !! AN ACCOUNT CAME BACK ON ITS SHIPPED DEFAULT PASSWORD.
reset.sh: !! … sign in with it and change the password. A default credential reaches the
reset.sh: !! sign-in and the change and nothing else (R-50) …
```

**And it reports rather than refuses** — `exit 0` with the restore completed, which is `R-46`'s
line and `D-72`'s lesson. The mutation the ruling forbids (turning this into a refusal) is
`W47-FIX`'s M4; I did not re-run it.

**Does a credential minted before the restore actually fail afterwards? — yes.**

```
#  token N answered 200 on /api/v1/projects before the restore
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:56441/api/v1/projects   -H "authorization: Bearer $TOKN"   # 401
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:56441/api/v1/dashboard  -H "authorization: Bearer $TOKN"   # 401
```

**Does the shipped pair now reach anything beyond the exchange and the change? — no. It reaches
exactly those two.** The premise is real — the pair mints again — and `R-50` is what bounds it:

```
POST /api/v1/auth/token {"login":"admin","password":"password"}
#  200  is_default_credential=True          <- the window is open again, which is R-52's whole point

# that credential, swept over every protected operation in the contract, through nginx:
#  protected operations probed with the RESTORED shipped pair: 18
#  status distribution: {'403': 18}
#  issueToken -> 200      changePassword -> 200
```

So `R-52`'s premise and `R-50`'s bound are both true at once on a real stack: the restore reopens
a publicly known pair, and that pair can do one thing — change its own password. I then did
exactly what the script's remedy says, and it worked: `changePassword` from the restored default
→ 200, and the account is no longer default.

### 16.2 Does `revoke` run at all in a real deploy? — **yes.** The stub's blind spot, closed

`W47-FIX` named this itself. Driven standalone, with §7's own command text, not inside the restore:

```
DC="docker compose --env-file infra/deploy/env/alpha.env --file infra/deploy/compose.server.yml"
$DC run --rm --no-deps -T --entrypoint python api -m auditmanager.access.revoke --everyone
#  credentials revoked: every credential held by 'admin'   is refused from now on (token_epoch is now 4).
#  credentials revoked: every credential held by 'judgey2' is refused from now on (token_epoch is now 9).
#  access-revoke: 2 account(s) revoked. …
#  EXIT=0
#  the database, read separately: admin epoch 3 -> 4, judgey2 epoch 8 -> 9
```

All three documented forms behave in the deployment exactly as §7 says they do:

| form | exit | what it printed |
|---|---|---|
| `--everyone` | **0** | two accounts revoked, both epochs up by one |
| `--login judgey2` | **0** | `access-revoke REVOKED: login=judgey2 … token_epoch=10` |
| `--login nosuchaccount` | **1** | `access-revoke: nothing matched, so nothing was revoked` |
| (no argument) | **2** | `error: one of the arguments --login --everyone is required` |

`Y-C` is therefore closed by measurement as well as by the repair: the idiom §7 now prints is the
one that runs, and the `PYTHONPATH=src python` form it used to print still cannot
(`ModuleNotFoundError: No module named 'sqlalchemy'`, §5).

### 16.3 `Y8` on a real volume — **repaired**

My first-round control: the wipe left `register.json` **byte-identical**, md5 `90749ba1…`, holding
three 199-character credentials. This round, on the repaired tree:

```
# before the wipe
docker exec <web> md5sum /var/lib/auditmanager/sessions/register.json
#  48d9bd464b7c5f877989baf7012f4bde   (409 bytes, one row, login=admin, isDefault=true)

infra/deploy/reset.sh --database jy_r52 --bucket jy-r52 --yes-destroy-everything   # exit 0

# after
docker exec <web> ls -la /var/lib/auditmanager/sessions/
#  total 8
#  drwx------ 2 node node 4096 …  .        <- the directory, and nothing in it
docker exec <web> md5sum /var/lib/auditmanager/sessions/register.json
#  md5sum: …/register.json: No such file or directory
```

and the pre-wipe cookie answers **401**. The script says so on its own screen —
`reset.sh: clearing the session register on jy-w47k-r52-web-sessions` — and the `sessions-cleared`
guard is what would have stopped it if the file had survived. **`Y8` is gone**: the wipe now takes
the documents, the rows and the credential material in one landing, which is what §7 promised and
did not do.

### 16.4 `Y-D` on a real stack — **repaired, both layers**

```
# the condition: the bucket holds nothing
$DC run --rm --no-deps --entrypoint sh s3-init -c '…; mc ls --recursive local/jy-r52 | wc -l'   # 0

infra/deploy/reset.sh --database jy_r52 --bucket jy-r52 --yes-destroy-everything
#  EXIT=0   SECONDS=24          <- was a silent exit 1 with no message
```

and the dump it leaves is **complete**, which is the second layer `W47-FIX` found underneath —
`grep -c` printing a count *and* exiting 1 on zero, so a correct dump was being read as short:

```
ls -l infra/deploy/dumps/*/
#  -rw-r--r-- 100551  database.dump
#  drwxr-xr-x          objects
#  -rw-r--r--      0  objects.attrs        <- zero lines, and accepted as zero
#  -rw-r--r--      0  objects.stat.json    <- empty, not the {"status":"error"} payload of round one
```

**The strongest evidence that the dump is sound is §16.1**: `--restore` accepted this directory
and put the database back from it. That also closes the question I left open in §10 — a dump taken
on an empty bucket is now a dump the restore path will take.

### 16.5 `Y-G` on the real proxy and the real port — **repaired**

`W47-FIX` probed the new config against a standalone `nginx:1.27-alpine`. Here it is the proxy
container the deploy built, on `56441`, with the API behind it. My round-one control was
`location: http://127.0.0.1/dashboard` — prefix **and** port both lost.

```
for u in /api/v1/dashboard/ /api/v1/projects/ /api/v1/runs/ /api/v1/auth/token/; do
  curl -s -i --path-as-is "http://127.0.0.1:56441$u" | grep -i '^location'; done
#  location: http://127.0.0.1:56441/api/v1/dashboard
#  location: http://127.0.0.1:56441/api/v1/projects
#  location: http://127.0.0.1:56441/api/v1/runs
#  location: http://127.0.0.1:56441/api/v1/auth/token

curl -sL --max-redirs 3 --path-as-is -o /dev/null -w 'final=%{http_code} url=%{url_effective}\n' \
  http://127.0.0.1:56441/api/v1/dashboard/
#  final=401 url=http://127.0.0.1:56441/api/v1/dashboard
```

**Both halves hold**: the port is kept (`Host $http_host`) and the prefix is put back
(`proxy_redirect ~^(https?://[^/]+)/(.*)$ $1/api/v1/$2`), and following the redirect now lands on
the **API** — 401, the authenticated answer — instead of on the web screen of the same name.

**And the web tier did not gain one**, which is the other half of the question:

```
for u in /projects/ /dashboard/ /login/ /account/password/ /blocks/; do …; done
#  308  location: /projects          308  location: /dashboard        308  location: /login
#  308  location: /account/password  308  location: /blocks
```

Next's own redirects are **relative**, so `proxy_redirect`'s absolute-URL pattern cannot match them
and does not. One thing to know rather than a finding: that pattern rewrites **any** absolute
`Location` the API emits, so an API that ever redirected to a third-party host would have
`/api/v1` prepended to it. Nothing in this API does; the rule is right for the surface it has.

### 16.6 The one narrowing: `--restore` kills the register's credentials without clearing the register

Driven, because `R-52` folds `Y8` in and the wipe is only one of the script's three modes:

```
# a live session, then a restore on top of it
curl … POST /bff/v1/session                         -> 303, cookie
curl -H "Cookie: $C" /bff/v1/projects               -> 200
docker exec <web> md5sum …/register.json            -> c072267e34bd255d8c6fca03d0862c46

infra/deploy/reset.sh … --restore <dump>            -> exit 0

curl -H "Cookie: $C" /bff/v1/projects               -> 401          <- dead
docker exec <web> ls -l …/register.json             -> 794 bytes, still there
docker exec <web> md5sum …/register.json            -> c072267e34bd255d8c6fca03d0862c46   <- byte-identical
```

**The access is gone and the file is not.** The epoch raise is what kills the rows, so the
mechanism `R-52` ruled is doing exactly its job — a credential in the register is refused on its
next request wherever it was kept. But the ruling's sentence *"`reset.sh` clears the register
volume in the same movement that clears the database and the bucket"* is true of
`--yes-destroy-everything` (§16.3) and **not** of `--restore`, where the dead credentials stay on
the volume until a sign-in overwrites the file or they expire.

I record it as a **narrowing and not a finding**, for the reason the ruling itself gives: inert
credential material is not access, and after a restore the epoch has already moved. If it is worth
closing, the cheap close is the line `reset.sh` already has, called in the restore branch too —
and the argument against is that a restore is run *because something failed*, and clearing live
reviewers' sessions in that moment is a second outage on top of the first. That trade is the
owner's, not mine.

### 16.7 What I measured, timed

| step | measured |
|---|---|
| `deploy.sh` from `6ad43a0`, cold-ish cache | **~10 min** (host at 2–3 GB available and 6.8 GB disk; two earlier deploys today took 1 m 56 s and 2 m 22 s with more room — this figure is contention, not scope) |
| `reset.sh --yes-destroy-everything`, empty bucket | **24 s**, exit 0 |
| `reset.sh --restore <pre-change dump>` | **6 s**, exit 0 |
| `revoke --everyone` in the `api` image | **~3 s**, exit 0 |
| `verify-deployed.sh` after all of it | exit 0, `the deployed stack IS this tree (6ad43a0)` |

Per the brief I did not re-drive the sixteen-route journey and did not run `make gate`.
