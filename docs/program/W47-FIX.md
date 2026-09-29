# Wave 47, repair — `W47-FIX`

**One stream, per `docs/program/dispatch/W47-FIX-DISPATCH.md`.** Branch `agent/w47-fix`,
worktree `/root/w47pass`, lane `gate-w47b`, cut from `9783e73`.

Every section names the finding, what changed, and **the command that now shows it repaired**.
Every guard added or changed is shown able to fail, with the mutation and its result.

**Baseline, not re-taken** (`W47-FIX-DISPATCH.md` §Base): `GATE OK`, battery **2581 passed /
5 skipped**, foundation **35**, frontend **1156 in 82 files**, from `/root/w47-a2-merge-gate.log`
— `GATE OK` at line **258**, battery at line **134**, frontend at lines **253-254**.

---

## 1. `R-52` — the restore, and the volume, in one change

`infra/deploy/reset.sh`. The dump is the whole database with no `--exclude-table` and the restore
is `pg_restore --clean --if-exists`, so `app_user` comes back entire — `password_hash`,
`token_epoch` **and** `is_default_credential`. `W47-JUDGE-X` §7.1 drove all three consequences;
the third is bounded by nothing, because a password is not a token.

**After the rows are back, `--restore` now:**

1. runs `auditmanager.access.revoke --everyone` — every restored credential is dead;
2. runs `auditmanager.access.check` — which **names by login** any account that came back on its
   default password — and prints what to do: sign in with that login and change the password,
   which is the only thing a default credential can do (`R-50`) and is enough.

Both run **inside the `api` image** (`docker compose run --rm --no-deps -T --entrypoint python
api -m …`), the idiom `readiness.sh` already uses and the only one that works on the host §1 of
the runbook describes — which is also `Y-C`.

**It reports; it does not refuse.** Neither command's status can turn a completed restore into a
non-zero exit. `revoke` exit `1` (a dump with no accounts) is a successful reading and is silent;
exit `≥2` from either prints a marked block with the exact command to run by hand. There is no
exit-non-zero path anywhere in this change for *"a default credential came back"*.

### `Y8` — the wipe clears the session register

The register was byte-identical across a wipe, `md5sum` unchanged, three complete reviewer
credentials in it (`W47-JUDGE-Y` §6). `--yes-destroy-everything` now clears it **in the same
movement as the database and the bucket and before either**, so a stack that cannot clear it
refuses with the documents still whole. The `web` container is stopped for that moment and
started again, because the register is a file *and* a `Map` in that process and `persist()`
writes the map out after every change. New guard `sessions-cleared`; the guard inventory moves
**12 → 13**.

### `Y-D` — an empty bucket is a state, and it took two repairs

`mc --json stat --recursive` exits **1** on a bucket with no objects, writing its error payload to
stdout — which the script redirects into `objects.stat.json`. Under `set -euo pipefail` the wipe
died with **exit 1**, a status `usage()` does not list and the script issues nowhere else, after
a complete database dump had been written and with not one word about why.

**And one layer on, uncovered by repairing the first.** `grep -c` **prints** the count and
**exits 1** when it is zero, so `RECORDED="$(grep -c . … || echo 0)"` captured *both* — the
two-line string `0\n0` — and `dump-verified` then refused a correct dump as *"short"*:

```
$ : > /tmp/empty.attrs; R="$(grep -c . /tmp/empty.attrs 2>/dev/null || echo 0)"; printf '[%s]\n' "$R"
[0
0]
```

An **absent** sidecar still refuses, and gets a value no count can equal rather than a zero.

### What now shows it repaired

```
cd /root/w47pass
.venv/bin/python -m pytest tests/integration/composition/test_reset_script_refusals.py -q
#   49 passed          (36 before this repair: +13)
grep -cE '^# >>> guard: ' infra/deploy/reset.sh         # 13
```

The suite drives `reset.sh` under a `docker` stub that records every call, plays the dump
through, and reproduces `mc`'s real empty-bucket behaviour (payload on stdout, exit 1). Cases:
the revoke lands **after** `pg_restore` and carries `--everyone`; both commands run
`--entrypoint python api` and carry no `PYTHONPATH`; a default credential coming back exits **0**
and prints the report; a revoke that cannot reach the database exits **0** and prints the
command; a dump with no accounts raises no alarm; a clean restore raises none either; the
register is cleared **before** `DROP SCHEMA`, between `stop web` and `up -d --no-deps web`; a
register that cannot be cleared refuses with no `DROP SCHEMA` and no purge; an empty bucket runs
to the end; `json stat` is not called on an empty bucket and **is** called otherwise.

### Shown able to fail

| mutation | result |
|---|---|
| **M1** the unconditional `mc --json stat` restored | **3 failed** — `…wipe_on_an_empty_bucket_runs_to_the_end`, `…command_that_exits_one…`, `…absent_sidecar…` |
| **M2** `RECORDED="$(grep -c . … \|\| echo 0)"` restored | **3 failed** — `…runs_to_the_end`, `…empty_sidecar_is_the_right_length`, `…absent_sidecar…` |
| **M3** the `revoke --everyone` call deleted | **3 failed** — `…every_restored_credential_is_dead…`, `…runs_inside_the_api_image…`, `…revocation_that_could_not_run…` |
| **M4** the default-credential report made a `refuse` (the inversion `R-52` forbids) | **1 failed** — `…names_by_login_any_account_back_on_its_default_password` |
| **M5** the `sessions-cleared` guard block deleted (in-suite) | the refusal is gone and `DROP SCHEMA` is reached — `TestTheWipeClearsTheSessionRegister::test_that_guard_is_shown_able_to_fail` |

## 2. `D-101` — closed

`src/auditmanager/access/policy.py`. `SHIPPED_DEFAULT_PASSWORD` is a **fourth contextual entry**.
Still context about this deployment and not a stored corpus — no file, no dependency, no licence.
Case-folded like the two beside it, and here the reason is measured rather than symmetric: the
change `W47-JUDGE-X` §1.3 drove off the shipped default was to `"Password"`, one shift key away.

**It is the one blocklist entry with a second copy in the tree** — `SEED_PASSWORD` in
`db/migrations/versions/20260922_0006_app_user.py` — so the test **reads that literal out of the
migration's source** (never imports it) and compares. A deployment that changed the seed and left
this behind would have a blocklist entry that refuses nothing.

`test_the_d101_gap_is_still_open` was **not deleted**. It is `test_the_d101_gap_is_closed` in
`tests/integration/db/test_app_user_repository.py` — the same account, the same two changes, the
second one's expectation turned round — and its docstring carries the old name so a search for it
lands there, and carries what it used to assert.

### What now shows it repaired

```
cd /root/w47pass
.venv/bin/python -m pytest tests/integration/access/test_password_policy.py -q     # 16 passed (11 before)
PYTHONPATH=src .venv/bin/python -c "from auditmanager.access.policy import enforce_password_policy as e; e('password', login='someone')"
#   auditmanager.shared.errors.exceptions.DomainError: a password may not be the password this system ships with
```

The database-backed half (`test_the_d101_gap_is_closed`, `test_the_shipped_default_is_refused_whatever_the_shift_key_did`)
runs in the gate's battery against a real PostgreSQL.

### Shown able to fail

| mutation | result |
|---|---|
| **M5** the entry disabled (`if False and …`) | **2 failed** — `…shipped_default_is_refused`, `…refused_in_any_case` |
| **M6** the entry made case-sensitive | **1 failed** — `…refused_in_any_case` |
| **M7** the constant drifted to `passw0rd` | **2 failed** — `test_the_shipped_default_is_the_one_the_migration_seeds`, `…refused_in_any_case` |

## 3. `Y-G` — the published origin's redirect

`infra/deploy/proxy/nginx.conf` and `infra/deploy/proxy/tls-server.conf` (the body is a deliberate
copy and `test_the_two_server_bodies_do_not_drift` holds it).

* `proxy_set_header Host $host` → **`$http_host`**. `$host` strips the port, so the absolute
  redirect the application builds named **port 80** of whatever the caller typed. `$server_port`
  is not the repair: it is 8080, the container's internal listen port;
* `proxy_redirect ~^(https?://[^/]+)/(.*)$ $1/api/v1/$2;` **inside each of the two `/api/v1`
  blocks**. `proxy_pass http://api:8000/` strips the prefix on the way in — correctly — and
  nothing put it back, so an API path redirected to the **web screen** of the same name.
  `proxy_redirect default` does not reach it: it expands to `http://api:8000/ → /api/v1/`, and
  the Location names the *client's* authority. Inside the blocks and not at `server` level,
  because at `server` level it would rewrite the web tier's own redirects the other way.

The redirect is left as a redirect: removing it means `redirect_slashes=False` on the
application, which is a change to the published surface (every trailing-slash path becomes a 404)
and a decision about the API, not about this file.

### What now shows it repaired

Driven against `nginx:1.27-alpine` with the real file and two stub upstreams that reproduce
Starlette's absolute `Location`. Full log: **`/root/w47fix-yg-probe.log`**.

```
--- BEFORE: infra/deploy/proxy/nginx.conf at 9783e73 ---
/api/v1/dashboard/         Location: http://127.0.0.1/dashboard
/api/v1/projects/          Location: http://127.0.0.1/projects
/api/v1/runs/              Location: http://127.0.0.1/runs
/projects/                 Location: http://127.0.0.1/projects

--- AFTER: the repaired file ---
/api/v1/dashboard/         Location: http://127.0.0.1:58099/api/v1/dashboard
/api/v1/projects/          Location: http://127.0.0.1:58099/api/v1/projects
/api/v1/runs/              Location: http://127.0.0.1:58099/api/v1/runs
/projects/                 Location: http://127.0.0.1:58099/projects

--- and the non-redirecting paths still reach the right upstream ---
/api/v1/dashboard          upstream=api path=/dashboard host=127.0.0.1:58099
/api/v1                    upstream=api path=/ host=127.0.0.1:58099
/dashboard                 upstream=web path=/dashboard host=127.0.0.1:58099
```

The web tier's `/projects/` keeps its port and correctly gains **no** prefix.

The static half is in the gate:

```
.venv/bin/python -m pytest tests/integration/composition/test_proxy_tls_path.py -q   # 14 passed (10 before)
```

### Shown able to fail

| mutation | result |
|---|---|
| **M8** `Host $http_host` → `$host` | **3 failed** — `…forwarded_host_carries_the_port`, `…no_configuration_forwards_the_port_stripped_host`, and the drift check |
| **M9** the `proxy_redirect` dropped from **one** of the two blocks | **2 failed** — `…every_api_location_puts_the_prefix_back…`, and the drift check |
| **M10** the rule moved to `server` level | **3 failed** — including `…web_location_does_not_gain_the_prefix`, which is the control |

## 4. The contract sentence — one reseal

`ChangePasswordRequest.new_password.description`. The brief's wording, **verbatim**, and the
policy is not restated: writing "minimum 8" into the contract would give the transport a second
authority over `policy.py` and make every policy change a reseal. `"no history and no expiry"`
are true of `policy.py`, which enforces neither, and stay.

**One movement, four documents**: `contracts/api/v1/openapi.json`, the byte-identical mirror
`web/openapi/openapi.json`, the regenerated client under `web/src/shared/api/generated/`, and
`web/FRONTEND_LOCK.json`. The sentence lives in no `.md` — checked. **No count moves.**

### What now shows it repaired

```
cd /root/w47pass
python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(d['components']['schemas']['ChangePasswordRequest']['properties']['new_password']['description'])"
sha256sum contracts/api/v1/openapi.json web/openapi/openapi.json
#   f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585  (both)
cd web && node scripts/generate-api-client.mjs --check
#   OK - 20 operations, contract sha256 f043eb6c…
npx vitest run tests/guards/frontend-lock.guard.test.ts tests/contract    # 112 passed
cd .. && .venv/bin/python -m pytest tests/contract/api_v1/ -q             # 145 passed
python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(len(d['paths']), sum(1 for p,i in d['paths'].items() for m in i if m in ('get','post','put','patch','delete')), len(d['components']['schemas']))"
#   17 20 61
```

## 5. The documents

**Every one was measured against the tree, and the command is beside the new sentence in the
document itself.** Where the runbook and the tree disagreed, the runbook changed.

| finding | what changed | the command |
|---|---|---|
| `Y-A` | `DEPLOYMENT_RUNBOOK.md` preamble: `R-4` has **one half open** (who uploads) and **one answered** (`R-41`/`R-42`), with §7 named. Repaired as a sentence, not a deletion — the preamble is where the reader learns which is which | `sed -n '14,28p' docs/program/DEPLOYMENT_RUNBOOK.md` against `:369`'s "Answered by `R-41`" |
| `Y1` | four sites: §1's disk table (three volumes, and what the third holds); §3 (a redeploy no longer signs reviewers out); §5 (`down --volumes` does, and dumps nothing); §10 (both `[session-register]` lines an operator meets) | `grep -c -i session docs/program/DEPLOYMENT_RUNBOOK.md` → **8** (was 0); `grep -c 'down --volumes'` → **4** (was 0) |
| `Y-C` | §7's three commands run inside the `api` image, with the `ModuleNotFoundError` reproduction and one `DC=` line above them | `grep -c 'PYTHONPATH=src python -m auditmanager' docs/program/DEPLOYMENT_RUNBOOK.md` → **0**; `grep -n 'entrypoint python api' infra/deploy/readiness.sh` |
| `Y-F` | §2: the key goes to **two** processes and rides the sign-in exchange forward in an `Authorization` header; the consequence is **not** overstated — X measured it is not a usable bearer (401) and reaches no browser. Stopping `web` from holding it is `R-29` §2, the owner's | `grep -n 'AUDITMANAGER_API_TOKEN' infra/deploy/compose.server.yml` → `:173` api, `:208` web; `grep -n "headers.set('authorization'" web/src/shared/api/credentialed-forward.ts` → `:163` |
| `Y2` | `readiness.sh:185`'s printed finding and its comment say **401**, and that a 200 there is refused | `sed -n '751,772p' infra/deploy/deploy.sh` — *"A 200 here is therefore a REFUSAL"* |
| `Y3` | the same number in `DEPLOYMENT_RUNBOOK.md` §3 and §6 and in `infra/deploy/README.md` twice | as above |
| `Y5` | **fourteen** guards and **eight** before docker, in the runbook and the README, with the eight named and the grep trap recorded | `grep -cE '^# >>> guard: ' infra/deploy/deploy.sh` → **14**; bare `grep -c '# >>> guard:'` → **15**, off `deploy.sh:89` |
| `Y6` | `alpha.env.example:147` no longer tells the operator the browser presents the key as a bearer; it says what the value is and that it reaches no browser | `grep -n Bearer infra/deploy/env/alpha.env.example` — the only hit is the corrected paragraph naming the old sentence |
| `Y9` | `alpha.env.example:48`: **all three** named volumes, with the command that lists them | `docker compose --env-file … config --volumes` → `postgres-data`, `s3-data`, `web-sessions` |
| `Y10` | six sites — runbook ×2, `alpha.env.example` ×2, `deploy.sh` ×2, `compose.server.yml`, `nginx.conf`, `Dockerfile.api`. **The number is not restated where nothing reads it**; the sentence names the command instead | contract → **20**; `deploy.sh` prints `frozen ops : 20` / `served ops : 20` on every run |
| provenance | `W47-LOCK.md:334,336` cited `W47-DISPATCH.md` for `2567 / 1139-in-81`; that file carries `2516 / 1135-in-80` at `:17`. The figures **are** real and were printed by a gate | `sed -n '125p;230,231p;235p' /root/w47-a-merged-gate.log` |

`test_doc_prose_facts.py` and `test_surface_counts_in_prose.py`: **47 passed.**

### Two things I left, deliberately

* **`Y-B`** — the runbook `:501-505` still warns that the rehearsal's total over-reports by
  counting a view. Both judges agree `D-39` closed that (`reset.sh` totals
  `sum(n) FILTER (WHERE kind = 'BASE TABLE')`). **It is not in my brief's §5 table** and I did not
  touch it. It is a live false sentence in a document I was editing; the integrator should decide.
* **`Y4`** — the corrupt-register log window. Also not in the brief. `X` narrowed it to nine
  characters, all of them the public `am2.eyJ` prefix. Untouched.

## 6. `Y7` and `D-118`

### `Y7` — a diagnostic that could not see the state the wave is about

`sessionDurability()` answered `durable: path !== null` — the **configuration** — while its own
sentence promised *which register is in force*. **`X` checked: no test pinned it at all**, so this
is a **new** block of six cases, not an inverted one.

Three questions now, each seeing a state the others cannot: a configured path at all; a **recorded
write failure** (the only one that can see a **full disk**, where permissions are fine and
`ENOSPC` arrives at the moment of writing); and, before anything has been written, a **probe** of
the filesystem (the only one that can see a **restored volume owned by root** on the first request
of a fresh container). It writes nothing.

**On the two shapes the tests use.** The judge drove a read-only directory and a full filesystem.
Neither is drivable from a suite running as **root**, because root bypasses the permission bits —
measured:

```
mkdir -p ro && chmod 500 ro
node -e "require('fs').accessSync('ro', require('fs').constants.W_OK)"   # exit 0 as uid 0
setpriv --reuid=65534 --regid=65534 --clear-groups node -e "…"           # EACCES
```

So the cases use failures the kernel applies to root as well, and each is a real operator shape:
**the parent is a file** (a stale file where the mount point should be — the probe half, answered
before any session exists) and **the register path is a directory** (exactly what mounting the
volume one level too deep produces — the probe passes and the write fails, which is the half only
a recorded failure can see, and it stands in for the full disk).

```
cd /root/w47pass/web && npx vitest run tests/guards/session-durability.guard.test.ts
#   14 passed   (8 before: +6)
```

| mutation | result |
|---|---|
| **M11** `return { durable: path !== null, path }` — the exact pre-repair line | **3 failed** |
| **M12** the recorded-failure branch removed (probe only) | **2 failed** — the full-disk half |
| **M13** the probe removed (recorded failure only) | **1 failed** — the restored-volume half |

### `D-118`, third error — the decision, and why

**The `console.info` stays, on the channel that says what it is, with a narrow named exemption**
(`// eslint-disable-next-line no-console`, one line, reasoned in the function's docstring).

Both named alternatives cost something real, and the deciding argument is the **level**, not the
line:

* **escalate to `warn`** — then *both* branches are warnings and the level carries no information.
  An operator reading `docker compose logs web` could no longer tell a healthy stand from one that
  has silently lost its volume without reading the sentence. The unset branch is a **genuine**
  warning — every reviewer is signed out on the next deploy and somebody must act — and burying it
  beside a notice that fires on every correct deployment is how a warning becomes furniture;
* **delete it** — `R-51` asked for it to be said out loud; it is the cost the owner accepted, in
  the one place an operator meets it, and `infra/deploy/README.md` describes both lines as things
  a reader will see. Deleting a product statement to satisfy a rule about leftover debug logging
  is the tool editing the product.

`info` is what this is: information about a healthy configuration, once per process.

```
npm --prefix web run lint
#   2 problems (2 errors, 0 warnings)     -- was 3
```

The two that remain are **wave 46's** `no-irregular-whitespace` in
`web/tests/guards/dashboard-invalidation.guard.test.ts:17,58` (`2fccac8`). Deliberately left: the
register's own row says a stream that quietly repairs another wave's lint finding hides the fact
that the gate does not look there. **`lint` is not wired into `make gate`** — `D-118`'s structural
half is a non-goal here and stays open.

---

## 7. The gate

`make gate` in `/root/w47pass`, lane `gate-w47b`, at `35523b5` with a clean tree, run alone
(`free -g` checked and no other `make gate` under `/root/w4*`). Not an exit code — the line,
from `/root/w47fix-gate.log:256`:

```
GATE OK: battery, foundation, frontend and whitespace all pass
```

| suite | this gate | baseline (`/root/w47-a2-merge-gate.log`) | delta |
|---|---|---|---|
| battery | **2604 passed / 5 skipped** (4 warnings, 169 subtests, 1466.19 s) | 2581 passed / 5 skipped | **+23** |
| foundation | **35 passed** (27.78 s) | 35 | **0** |
| frontend | **1162 passed in 82 files** (20.89 s) | 1156 in 82 files | **+6 tests, +0 files** |

Lines `122` (battery), `60` (foundation) and `251-252` (frontend). The battery's 1466 s against
the baseline's 663 s is host load: another project's suites ran throughout.

**The +23, by test id.** Every one is new here; nothing was deleted and **the skipped count is
unchanged at 5** — `git diff 9783e73..HEAD -- tests web/tests | grep -E '^\+.*(skip|xfail)'` is
empty.

`tests/integration/composition/test_reset_script_refusals.py` (**13**):
`test_every_restored_credential_is_dead_by_the_time_the_restore_returns`,
`test_it_runs_inside_the_api_image_and_not_on_the_host`,
`test_it_names_by_login_any_account_back_on_its_default_password`,
`test_a_revocation_that_could_not_run_is_reported_and_does_not_refuse`,
`test_a_dump_with_no_accounts_in_it_is_not_reported_as_a_failure`,
`test_a_clean_restore_says_so_and_raises_no_alarm`,
`test_the_register_is_cleared_and_before_anything_is_destroyed`,
`test_a_register_that_cannot_be_cleared_refuses_and_destroys_nothing`,
`TestTheWipeClearsTheSessionRegister::test_that_guard_is_shown_able_to_fail`,
`test_a_wipe_on_an_empty_bucket_runs_to_the_end`,
`test_the_command_that_exits_one_on_empty_is_not_run_on_an_empty_bucket`,
`test_an_empty_sidecar_is_the_right_length_and_not_a_short_one`,
`test_an_absent_sidecar_is_still_refused_on_an_empty_bucket`.

`tests/integration/access/test_password_policy.py` (**5**):
`test_the_shipped_default_is_the_one_the_migration_seeds`,
`TestTheShippedDefaultEntry::test_the_shipped_default_is_refused`,
`::test_it_is_refused_in_any_case`, `::test_a_password_that_merely_contains_it_is_not_refused`,
`::test_the_refusal_is_the_length_one_when_both_would_apply`.

`tests/integration/composition/test_proxy_tls_path.py` (**4**):
`TestTheRedirectStaysOnThisOrigin::test_the_forwarded_host_carries_the_port`,
`::test_no_configuration_forwards_the_port_stripped_host`,
`::test_every_api_location_puts_the_prefix_back_on_the_way_out`,
`::test_the_web_location_does_not_gain_the_prefix`.

`tests/integration/db/test_app_user_repository.py` (**+2 − 1 = +1**):
`test_the_d101_gap_is_closed` and `test_the_shipped_default_is_refused_whatever_the_shift_key_did`
in, `test_the_d101_gap_is_still_open` out — **and that one is a rename, not a deletion**: it is
the same account, the same two changes and the same body, with the second change's expectation
turned round, and its docstring carries the old name. 13 + 5 + 4 + 1 = **23**.

**The +6, one file.** `web/tests/guards/session-durability.guard.test.ts`, 8 → 14, all in the new
`Y7` block: `the control: a configured path it can really write is durable`, `a configured path
whose directory cannot be created is not durable`, `a session opened there really is lost, which
is what durable: false means`, `a write that fails although the path looked writable makes it not
durable`, `a register that starts working is durable again`, `unset is still a configured absence
and not a broken volume`. No file added, so **82 stays 82**.

## 8. The live journey

`npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:56423 --phase all`, against a stand
served from this worktree: API `PYTHONPATH=src .venv/bin/python infra/deploy/serve.py`
(`operations=20`, `127.0.0.1:56421`, health `:56422`, `AUDITMANAGER_PROVIDER_MODE=recorded`), web
`npx next start -p 56423` on a `npm run build` of this tree, with
`AUDITMANAGER_SESSION_STORE=/root/w47fix-sessions/register.json` so `R-51`'s register was live
for the whole run. Log: `/root/w47fix-journey-run2.log`; envelope
`/root/w47fix-journey-out/journey.json`.

**The credential:** a reviewer account of its own, `w47fixreviewer`, created through the
repository (`create_user` writes `is_default_credential = false`). Not a bypass — `R-50` refuses
every operation but the exchange and the change to an account still on the shipped password, an
account still on it would still be refused, and `tests/integration/api/test_authorization.py`
proves that refusal. `admin` was left exactly as it was found. The account is needed because
`W47-LOCK` had already moved `admin` in this lane to a password this session does not hold.

**The first attempt was killed and is not a result.** It reached sign-in, 3/3 write steps and
5 of 16 routes and then took **SIGTERM** (`Terminated`, exit 143), writing no envelope and
reporting no finding, with the host at 2 GB available and another project's suites running. The
run quoted below is the re-run.

```
sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser

write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf

ok  create-project   api=3 {"project_uid":"prj_01M3PKXWBTGDEEKPY95V36PC7X"}
ok  upload-document  api=4 {"project_uid":"prj_01M3PKXWBTGDEEKPY95V36PC7X","version_uid":"ver_01M3PKXZVTKD79NQJBVZZG9FAG"}
ok  start-run        api=5 {"project_uid":"prj_01M3PKXWBTGDEEKPY95V36PC7X","run_id":"run_01M3PKY2NDKTDGFCPQ2XYG4XPE"} terminal=published in 1515ms/150000ms

ok  root           200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  projects       200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  project        200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  document       200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  version        200  api=2 auth=0 console=0 jar=[am_session] w=765/780
ok  comparison     200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  run            200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  review         200  api=5 auth=0 console=0 jar=[am_session] w=765/780
ok  sign-in        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  knowledge-base 200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  change-password 200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  blocks         200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  optimisation   200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  logs           200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  workers        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  dashboard      200  api=1 auth=0 console=0 jar=[am_session] w=765/780

envelope: /root/w47fix-journey-out/journey.json
write steps checked: 3/3
routes checked: 16/16
e2e:pc01 OK
```

**3/3 write steps, 16/16 routes, `auth=0` everywhere, `console=0` everywhere, no route over the
780 px bound.** `Y7`'s repair is on the sign-in path and the register was written normally
throughout — `register.json`, mode `600`, 860 bytes after the run.

## 9. What I stopped on, and what a gate would not show

* **`Y-B` and `Y4` are not in the brief's §5 table and I did not touch them.** `Y-B` is a live
  false sentence — `DEPLOYMENT_RUNBOOK.md:501-505` warns that the rehearsal's total over-reports
  by counting a view, and both judges agree `D-39` closed that (`reset.sh` totals
  `sum(n) FILTER (WHERE kind = 'BASE TABLE')`). It is in a document I was editing and it is one
  paragraph. **The integrator should decide**; I did not take it, because a repair the brief did
  not name is a repair nobody reviewed.
* **`D-118`'s other two errors stay.** `web/tests/guards/dashboard-invalidation.guard.test.ts:17,58`,
  wave 46's, in a file in my `allowed_paths`. The register's own row says a stream that quietly
  repairs another wave's lint finding hides the fact that the gate does not look there.
* **The `Y-G` repair's dynamic proof is not in `make gate`,** and cannot be: the gate has no
  stack and no proxy. What is in the gate is the static half over **both** server bodies; what is
  outside it is `/root/w47fix-yg-probe.log`, taken against `nginx:1.27-alpine` with the real file.
  If the application's redirect behaviour changes, the static guard will not notice.
* **`R-52` and `Y8` were not driven against a deployed stack.** The host has 8.6 GB free against
  §1's 5.5 GB for one clean-clone deploy, another project was building throughout, and a full
  `deploy.sh` plus a wipe plus a restore is the most expensive thing in this repository. The
  evidence is the stub-driven suite, which records every `docker` call and reproduces `mc`'s real
  empty-bucket behaviour — strong about **what the script does** and silent about **whether the
  `api` image can run `auditmanager.access.revoke` in a real deployment**. `readiness.sh` already
  runs `auditmanager.access.check` that exact way on a live stack, which is the nearest thing to
  a proof this repair has; a judge with a stack should drive `--restore` end to end.
* **`compose stop web` / `up -d --no-deps web` was verified against a throwaway compose project,
  not against the alpha stack.** `docker compose stop <svc>` on a service with no container exits
  **0** — measured, `/root/w47fix-probe`. The wipe now leaves `web` running even on a stack where
  it was not; that is stated in `reset.sh`'s comment and is the state the script already assumes.
* **`test_the_d101_gap_is_closed` is a rename**, and a reader grepping the old id finds it only
  through the docstring. If the integrator would rather the id did not move, say so.
