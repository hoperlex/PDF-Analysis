# W26-OPS — the deploy stops sending the operator to the wrong file, and the rehearsal stops counting a view

> **Opened before the first edit**, as the dispatch requires. Every figure below is
> measured on this host and carries the command that produced it.

`D-38` and `D-39`, both found by `W24-CERT2` and both about what a screen tells an operator.
Neither is a wrong exit code: one script refuses with the wrong diagnosis, the other
over-reports a total. Both are repaired, each with a case shown able to fail.

**Where the work was done.** Worktree `/root/w26ops`, branch `agent/w26-ops` from
`origin/dev` at `7535a17`. The instance driven is `auditmanager-w26a` on port **31526**,
database `auditmanager_w26a`, bucket `auditmanager-w26a`, brought up by this tree's own
`deploy.sh` and torn down at the end with `down --volumes`. **`31500` was not touched.**
The gate lane is `gate-w26a`: `POSTGRES_PORT=55980`, `S3_API_PORT=59580`,
`S3_CONSOLE_PORT=59581`, `POSTGRES_DB=audit_w26a`, bucket `auditmanager-gate-w26a`.

---

## 1. `D-38` reproduced, and the register's own check command does not reproduce it

### 1.1 What the dispatch says to run, run first, and it exits 0

Both `DEBT_REGISTER.md` `D-38` and this dispatch give the check as *"stop one service of a
running instance, re-run `deploy.sh`, read `$?` and the last ten lines"*. Driven, on a
healthy `auditmanager-w26a`:

```
$ docker stop 7fb0b68353fa          # the api container, by id
$ infra/deploy/deploy.sh --env-file infra/deploy/env/w26a.env ; echo $?
...
deploy.sh: auditmanager-w26a is up at http://127.0.0.1:31526
0
```

**A stopped service is not a failed `up`.** `compose up -d` starts the container it finds
stopped, every guard passes, and the script exits 0 — correctly. The check command in the
register **cannot produce the defect it is attached to**; it is the one false thing found in
the dispatch (§8).

### 1.2 What does reproduce it

`W24-CERT2`'s own measurement names the mechanism: `s3-init` exited 1 (its host was out of
disk), so **`api` was never created**, while a `proxy` from an earlier run kept running.
Reproduced here deliberately, in two steps that between them are that state:

```
$ docker rm -f $(compose ps --quiet api)        # api is gone, proxy still serving
$ sed 's/^S3_BUCKET=.*/S3_BUCKET=Invalid_W26A_Bucket/' w26a.env > w26a-broken.env
$ infra/deploy/deploy.sh --env-file infra/deploy/env/w26a-broken.env ; echo $?
```

`s3-init` refuses the bucket name and exits 1, so `up` aborts before `api` is created — the
same shape, on demand. **Exit 5**, and the last lines:

```
 Container auditmanager-w26a-s3-init-1 Error service "s3-init" didn't complete successfully: exit 1
service "s3-init" didn't complete successfully: exit 1
deploy.sh: `compose up -d` exited 1; the guards below decide.

-- reloading the proxy --
2026/09/21 07:02:05 [emerg] 69#69: host not found in upstream "api" in /etc/nginx/conf.d/default.conf:85
nginx: [emerg] host not found in upstream "api" in /etc/nginx/conf.d/default.conf:85
nginx: configuration file /etc/nginx/nginx.conf test failed

reload-proxy.sh: the proxy configuration is not valid.
  Nothing was reloaded and the old workers are still serving. Fix
  proxy/nginx.conf; a reload would have been refused anyway.
```

`D-38`, verbatim: *"the guards below decide"*, and then no guard decided anything.
`proxy/nginx.conf` is correct — it cannot resolve `api` because there is no `api`.

### 1.3 A second face, found by the test rather than by the stack

The suite's `docker` stub can hold the five long-running services healthy while `up`
returns non-zero, which is what happens when only a one-shot service fails. Against the
script as it was, **that run exits 0** and prints *"auditmanager-… is up"*. So the old
order had two failure modes, not one: the wrong diagnosis when the consequence is visible,
and **no diagnosis at all** when it is not. Both are gone.

---

## 2. The repair to `deploy.sh`

Two changes, both inside the existing `services-healthy` guard block and its position.

1. **The guard moved above the proxy reload.** The order is now `up` → the pin comes off →
   `services-healthy` → reload → `migrations-at-head` → `proxy-answers` →
   `schema-conforms`. A reload that fails *after* `services-healthy` has passed really is
   about the proxy's own configuration, which is what `reload-proxy.sh`'s message says, so
   that script is unchanged and still exits 5 on a genuinely broken `nginx.conf`.
2. **The guard widened to read the one-shot services' exit codes, and only on a run where
   `up` was non-zero.** `s3-init` and `migrate` leave an exit code behind and nothing in the
   script had ever looked at it. `compose ps --all --quiet <service>` — `--all`, because a
   one-shot container is not running by the time it matters — then
   `docker inspect --format '{{.State.Status}}/{{.State.ExitCode}}'`.

`reload-proxy.sh`, `infra/deploy/proxy/**` and `infra/deploy/README.md` are **not touched**;
the last two are `W26-HOST`'s (§7).

---

## 3. `D-38` after the repair — the same invocation, the same broken instance

```
$ infra/deploy/deploy.sh --env-file infra/deploy/env/w26a-broken.env ; echo $?
...
service "s3-init" didn't complete successfully: exit 1
deploy.sh: `compose up -d` exited 1; the guards below decide.

deploy.sh: REFUSED: `compose up` failed, and the 's3-init' service of auditmanager-w26a is exited/1.
    container: b23d735c692eaca92e333c93093aa5a52678df7131ffff8ba84d45e97d948571
  That is the step that did not complete. Whatever is missing or stale
  below follows from it, and the proxy has not been touched. Logs:
    docker compose logs s3-init
3
```

**Exit 5 → exit 3**, which is `refuse()`'s code and the one every other refusal in both
scripts uses. It still refuses — the half `W24-CERT2` called the important one — and the
file it names is now the one that is actually wrong. `nginx` is not mentioned at all.

---

## 4. `D-39` reproduced, repaired, and re-measured

The register's check command for this row **does** reproduce, on a database this session
wrote. Four rows in `finding`, reached through the project → document → version → run
chain, make `finding_current_verdict` project four:

```
$ reset.sh --env-file …/w26a.env --database auditmanager_w26a --bucket auditmanager-w26a --dry-run
  finding  (4 rows)
  finding_current_verdict  (4 rows)
  total: 37 rows in 17 tables
```

against, in the same database:

```
select table_type, count(*) from information_schema.tables where table_schema='public' group by 1
VIEW|1
BASE TABLE|16
base rows: 33
```

**37 over 33, 17 over 16.** After the repair, the same command:

```
  finding  (4 rows)
  finding_current_verdict  (4 rows, view: these rows are counted above)
  total: 33 rows in 16 base tables (and 1 view listed above, projecting rows already in that number)
```

Three decisions worth stating:

* **the view keeps its own exact line.** `DROP SCHEMA public CASCADE` destroys it too, so
  leaving it off the list would be a second untruth pointing the other way. It is marked
  instead;
* **the total says `base tables`.** `17 tables` was true of nothing; a scope that names
  itself cannot be read as "everything in the schema";
* **the views it did not add are named** on the same line, so the arithmetic is checkable
  from the screen.

`information_schema.tables` is the authority for which name is which — the same read the
register's check command makes.

---

## 5. Which test reddened for each repair

Redness was measured by restoring the pre-repair script into this tree and re-running:
`git checkout <commit>^ -- infra/deploy/<script>`, run, restore.

**`D-38` — `tests/integration/composition/test_deploy_script_refusals.py`.** The defect is an
ORDER, so the cases assert *when*: the staged `reload-proxy.sh` now records that it ran, and
`_reloaded(log)` reads that mark. New class `TestAFailedUpIsDiagnosedBeforeTheProxyIsTouched`,
four cases. Against `6f492cc` (the tree before the repair):

| case | against the old script |
|---|---|
| `test_an_unhealthy_service_is_named_before_the_proxy_is_reloaded` | **FAILED** — the refusal still arrives, one step after the proxy was reloaded |
| `test_a_failed_up_names_the_one_shot_service_that_failed` | **FAILED** — `assert 0 == 3`: the old script exited **0** and called it a deployment |
| `test_a_good_up_does_not_read_the_one_shot_exit_codes` | passes both ways, by design — it is the control that keeps the widening from refusing honest second deployments |
| `test_that_guard_is_shown_able_to_fail` | passes both ways, by design — it deletes the guard and requires the reload to be reached |

**`D-39` — new module
`tests/integration/composition/test_reset_rehearsal_counts_base_tables.py`.** The arithmetic
cannot be settled by the no-stack stub, and an assertion about the characters of a SQL
statement would pass the moment somebody wrote a different wrong one. So this module
**extracts `COUNT_ROWS_SQL` from `reset.sh`** and runs it against the lane's real PostgreSQL
through psycopg's own cursor — SQLAlchemy's `exec_driver_sql` passes an empty parameter set
and psycopg then reads the `%I` inside `format(...)` as a placeholder and refuses the query,
which would have meant transforming the text under test. A probe table of three rows and a
view over it live inside **one transaction that always rolls back**, so the over-count bites
on any lane database whatever it holds, and nothing is created. Against `a228e46^`:

| case | against the old statement |
|---|---|
| `test_the_total_is_the_base_tables_and_not_the_views` | **FAILED** |
| `test_the_total_says_which_tables_it_counted` | **FAILED** |
| `test_every_table_and_every_view_still_has_its_own_exact_line` | **FAILED** — `'these rows are counted above' in 'finding_current_verdict  (0 rows)'` |
| `test_the_total_line_is_still_what_the_rehearsal_counted_guard_reads` | passes both ways, by design — it pins `^  total: `, which `D-24`'s guard greps for, so a reworded total cannot silently remove a guard |
| `test_there_is_no_materialized_view_this_listing_cannot_see` | passes both ways, by design — the named limit, §7 |

---

## 6. Marker counts: **unchanged, 13 and 12**, and that was a constraint rather than a preference

`deploy.sh` has **13** `# >>> guard:` markers and `reset.sh` **12**, exactly as before, and
both meta-tests still assert those numbers unchanged.

The `D-38` repair wanted to be a fourteenth guard — *"a failed `up` must be accounted for by
some service"* is a different claim from *"all five containers are healthy"*. It is instead a
widening of `services-healthy`, because **`infra/deploy/README.md` line 149 says "Thirteen
guards"** and that file is `W26-HOST`'s for this wave. A fourteenth marker would have made
the README wrong in a file this task may not edit. Deleting the `services-healthy` block
still removes both refusals, so the deletion discipline holds over the widened guard;
`test_that_guard_is_shown_able_to_fail` in the new class proves it on the new half.

**If the integrator would rather have the fourteenth guard**, the split is mechanical: move
the `if [ "$UP_STATUS" -ne 0 ]` block into its own marker pair, `13 → 14` in
`test_every_guard_in_the_script_has_a_case_here`, name it in that test's `covered` set, and
change one word in `README.md`. That is a `W26-HOST`-owned edit, not this one.

---

## 7. What an operator sees that is different on a **successful** run

The dispatch asks for this explicitly. Two things change, and nothing else:

1. **the service table moves above the reload**, and now has a heading of its own —
   `-- every service is there, in the state compose knows it to be in --` — where before its
   five lines appeared directly under `-- reloading the proxy --`;
2. **the rehearsal's total line reads differently**: `total: 33 rows in 16 base tables (and
   1 view listed above, projecting rows already in that number)` where it read
   `total: 33 rows in 17 tables`, and a view's own line gains `, view: these rows are
   counted above`.

Exit codes on a successful run are unchanged, and no per-table figure changed.

**The named limit of the `D-39` repair.** A MATERIALIZED view is not in
`information_schema.tables` at all, so it would have **no line on this screen and no place
in the total** — an under-report, the direction `D-24` exists to prevent. There is none in
this schema, and `test_there_is_no_materialized_view_this_listing_cannot_see` reddens if one
is ever added. The same blind spot is in the register's own check command.

---

## 8. What was false in the dispatch, and what was true

**False, one thing, and it is a check command in the frozen input.** `D-38`'s *Check* — and
the dispatch's *"`D-38` reproduced first: stop one service of a running instance, re-run
`deploy.sh`"* — does not reproduce `D-38`. Measured: exit **0**, §1.1. The defect needs a
service that **cannot come back**, not one that is stopped. A register row whose check
command exits 0 on an unrepaired defect is worth a correction; the row's *mechanism* is
exactly right, and `W24-CERT2`'s own log is where the reproducible shape comes from.

**True, and checked rather than assumed:** 13 guards in `deploy.sh` and 12 in `reset.sh`,
each with a deletion case and a meta-count; `exit 5` and the `nginx.conf` message; the
`services-healthy` guard running after the reload; `D-39`'s shape and its direction;
`finding_current_verdict` being a view and a projection of `finding`; and the base gate
figures to the number.

---

## 9. Verification

| | |
|---|---|
| `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | exit 0, `bootstrap OK` |
| `npm --prefix web ci` | exit 0 |
| `make gate` (exit read from `$?` after a redirect, never through a pipe) | **exit 0**, `GATE OK` |
| battery | **1957 passed / 5 skipped / 169 subtests** in 279 s — base 1948 **plus the nine cases added here** |
| foundation | **35 passed** |
| frontend | **706 passed in 48 files** |

Lane `gate-w26a` throughout; one gate run, on a tree with nothing uncommitted, and no edit
while it ran.

**Disk.** `df -h /` was 11G free at the start, 5.8G after building two images, and 6.0G
after `docker builder prune -af` (3.512GB reclaimed) and `compose down --volumes`. The
`auditmanager-w26a` images are removed; one 401MB dangling image on this host belongs to
`auditmanager-w24idem` and was left alone.

**What was driven live rather than read:** the two reproductions, both repairs, the
successful-run control, and the rehearsal against a real database. Three waves have each
found a defect in these scripts that was invisible to reading; the `D-38` check command in
the register is a fourth thing that reads correct and is not.
