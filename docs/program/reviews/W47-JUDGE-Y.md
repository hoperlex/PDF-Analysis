
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
