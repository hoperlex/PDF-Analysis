# W49-FIX — report

Task: `docs/program/tasks/W49-FIX.md` as it reads at `62eb0c9` (Parts A–C; D and E added at
`631794c` for `R-62`/`R-63`; F added at `e47b9ed` for `R-65` and narrowed at `49f606c`). Branch
`agent/w49-fix`, worktree `.local/worktrees/w49-fix`: created from `c4e94e5`, fast-forwarded to
`631794c` before any commit, and `integration/w49` at `62eb0c9` merged in at `fb81888` (docs
only; it carries the `CURRENT_STATE.md` restructure that `alpha-w48` required). Lane
`gate-w49fix`: ports `56630`, `60230`, `60231`, found free with `ss -ltn` before `make up` and
before each stand.

| Part | Result |
|---|---|
| A — F-1 | **Partly done.** The two enums and the new gate-resident test are done, with every mutation red. **The two sentences of `contracts/domain/v1/README.md` (lines 8–10 and 753) are NOT edited**: this session's permission system refused my read of that file, and I did not route around the refusal. Open question 1. |
| B — B-1 | Done. Repair by **restart on stale**, not recreate and not directory mount (reasons in §B). Both halves of `W49-JUDGE-X`'s measurement reproduced on real containers: red on the unrepaired scripts, green after; the restart-removed mutation red on the stand and in the gate. |
| C — P02_SEAMS §7 | Done. |
| D — `R-62` | Done; regressions red on the restored old code. |
| E — `R-63` | Done; regressions red on the restored old code. |
| F — `R-65` | Done as narrowed at `49f606c`: one Russian sentence at A04 of `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`. No code change; none of `verify-acceptance.mjs`, `test_alpha_acceptance_command.py`, `manual-alpha-check.sh` was ever edited in this branch, so nothing had to be reverted. |

**Gate.** `make gate` on the code head `49187a4` (clean tree, no other `make` on the host,
4 GB available), log `.local/w49fix-logs/gate-49187a4.log`, read from the log, not from a wrapper:

```text
============================= 35 passed in 31.27s ==============================      (foundation)
3178 passed, 6 skipped, 6 warnings, 298 subtests passed in 1563.05s (0:26:03)        (battery)
      Tests  1296 passed (1296)                                                       (frontend)
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
make gate exit=0
```

The gate measured the code commit `49187a4`. The commit that adds this report follows it and
changes `docs/program/W49-FIX.md` only.

## 1. Changed files

```text
$ git diff --name-only 62eb0c9..49187a4
contracts/domain/v1/identifiers.schema.json
docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md
docs/program/P02_SEAMS.md
infra/deploy/README.md
infra/deploy/deploy.sh
infra/deploy/reload-proxy.sh
infra/deploy/verify-deployed.sh
src/auditmanager/access/accounts.py
src/auditmanager/access/registrations.py
src/auditmanager/access/repository.py
tests/contract/test_domain_identifiers_schema.py
tests/integration/access/test_account_management.py
tests/integration/access/test_registrations.py
tests/integration/api/qa_w49/test_qa_w49_status_read.py
tests/integration/api/test_registration_flow.py
tests/integration/api/test_user_management.py
tests/integration/composition/test_deployed_stack_probe.py
tests/integration/composition/test_proxy_config_follows_checkout.py
```

Against the original dispatch base `c4e94e5` the list is the same plus the five documents the
`integration/w49` commits brought in (`docs/program/CURRENT_STATE.md`,
`docs/program/OWNER_RULINGS_2026-09-17.md`, `docs/program/W48-INT-MAIN-01.md`,
`docs/program/dispatch/W49-PLAN.md`, `docs/program/tasks/W49-FIX.md`), none of them edited here.
Every path above is in `allowed_paths` (Parts A–F, and for
`tests/integration/api/qa_w49/test_qa_w49_status_read.py` the superseded-assertion clause).

The report commit that follows adds `docs/program/W49-FIX.md` and nothing else (§6).

## 2. What was done, part by part, and the checks

### A — F-1

`contracts/domain/v1/identifiers.schema.json`: `user_uid` and `request_id` appended to
`/properties/entities/additionalProperties/enum` and
`/properties/distinct_identities/items/properties/identifiers/items/enum`, after
`erasure_request_id`. The order convention: both arrays were, before the edit, the first 27
names of `identifiers.json` `identifiers` in the catalog's order (measured:
`e == list(catalog['identifiers'])[:len(e)]` → `True` for both), and the catalog's next two
names are `user_uid`, `request_id`. Nothing else in `contracts/**` moved; `candidate_revision`
stays 9.

`tests/contract/test_domain_identifiers_schema.py` (new, standard library only: `json`,
`collections.abc`, `pathlib`). It walks the schema for every string `enum`, keeps those that
share a member with the catalog's names (found by content, not path), asserts the set of such
enums is exactly the two pointers above, asserts totality both ways and no repeats, and asserts
the schema's `candidate_revision` `const` equals the catalog's. Collected by the gate's battery:

```text
$ .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q --collect-only tests --ignore=tests/checkpoint --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py | grep -c "test_domain_identifiers_schema.py::"
5
```

Mutations — each a copy of the schema, catalog, test and `pyproject.toml` under the
worktree's ignored `.local/w49fix-mut-a/<case>/`, run by
`.venv/bin/python .local/w49fix-logs/mutate_a.py` (exit 0; every red names the copy's path):

```text
=== A0-unmutated: exit 0
    5 passed in 0.01s
=== A-base-c4e94e5-schema: exit 1
    E       AssertionError: identifiers.schema.json enums lack names identifiers.json declares: {'/properties/entities/additionalProperties': ['user_uid', 'request_id'], '/properties/distinct_identities/items/properties/identifiers/items': ['user_uid', 'request_id']}
=== A1-entities-without-user_uid: exit 1
    E       AssertionError: identifiers.schema.json enums lack names identifiers.json declares: {'/properties/entities/additionalProperties': ['user_uid']}
=== A2-distinct-without-request_id: exit 1
    E       AssertionError: identifiers.schema.json enums lack names identifiers.json declares: {'/properties/distinct_identities/items/properties/identifiers/items': ['request_id']}
=== A3-entities-without-request_id: exit 1
    E       AssertionError: identifiers.schema.json enums lack names identifiers.json declares: {'/properties/entities/additionalProperties': ['request_id']}
=== A4-distinct-without-user_uid: exit 1
    E       AssertionError: identifiers.schema.json enums lack names identifiers.json declares: {'/properties/distinct_identities/items/properties/identifiers/items': ['user_uid']}
=== A5-candidate_revision-pin-8: exit 1
    E       AssertionError: identifiers.schema.json pins candidate_revision 8; identifiers.json declares 9
=== A6-entities-admits-undeclared-name: exit 1
    E       AssertionError: identifiers.schema.json enums admit names identifiers.json does not declare: {'/properties/entities/additionalProperties': ['ghost_id']}
```

Stop condition checked: after the edit, `tests/contract` minus the gate's three ignored files
ran `1 failed, 471 passed` — the one red was
`test_alpha_acceptance_command.py::test_release_command_cannot_turn_skips_recorded_mode_or_outage_into_pass`
refusing an uncommitted checkout (`FAIL: checkout содержит незакоммиченные изменения`), which is
that test's precondition and not a guard on Part A; it is green in the gate on the committed
tree. No digest, pin or prose guard turned red.

### B — B-1

**The choice: restart the proxy when what it reads differs from the checkout.** Rejected:

- *a directory mount* — `proxy/` cannot be mounted over `conf.d/` (nginx would load
  `tls-server.conf` unconditionally, the failure `infra/deploy/README.md` §TLS describes), and
  the TLS overlay `proxy/compose.tls.yml` (forbidden: `proxy/**`) mounts two more single files
  that would still pin inodes;
- *`docker compose up --force-recreate proxy`* from `reload-proxy.sh` — it would rebuild the
  container from `compose.server.yml` alone and silently drop an overlay the proxy was created
  with. `docker restart` re-resolves every bind mount by path (`W49-JUDGE-X` §7.4 measured
  "after docker restart: version-B") and keeps the container id, its ports and every mount.

`infra/deploy/reload-proxy.sh` now:

1. reads the running proxy's bind mounts from the container (`docker inspect`, so an overlay is
   seen); a mount from outside this checkout's `infra/deploy/proxy/`, a vanished source, or no
   mount of `proxy/nginx.conf` → exit **6**, named, nothing restarted (a restart would re-read
   the same paths), with the recreate command;
2. compares the SHA-256 of each single-file mount's host file with the SHA-256 inside the
   container; equal → `nginx -t` and `nginx -s reload` as before, **no restart**;
3. different → tests the checkout's configuration in a throwaway `docker run --rm` (same image
   id, network and mounts, read-only, the image's own entrypoint) — invalid → exit **5**, the
   running proxy untouched; valid → `docker restart`, in a block marked
   `# >>> step: restart-on-stale`, then compares again — still different → exit **6** (it no
   longer reports success on a stale inode) — then `nginx -t` and a bounded reload loop.

`infra/deploy/verify-deployed.sh` gains section 3: the proxy's mounts read from the container,
every tracked file under each source compared by SHA-256 inside the container; a difference,
a missing file, an untracked mounted file, a mount from another checkout or no
`proxy/nginx.conf` mount → exit **6** with *the running proxy is NOT serving this tree's
configuration*. It sends no request burst (a test pins one `curl` invocation and no
`registrations` in its code). `infra/deploy/deploy.sh`: only the comment at the reload call.
`infra/deploy/README.md`: one paragraph in *A rebuild is not finished when the images are*, one
in *Is the deployed stack this repository?*. `compose.server.yml` is not changed.

**Reproduction on a disposable stand, real containers.** The stand is a git clone whose proxy is
`compose.server.yml`'s (same pinned image, same single-file mount line) and whose api, web,
postgres and s3 are stand-ins built from that image; the stand-in api answers `deploy.sh`'s
database and conformance checks with their success lines (no application is claimed).
Configuration A is the tree's `nginx.conf` minus its `limit_req` line; B is the tree's. Instance
`gate-w49fix-unrep`, port 60231, driven by `.local/w49fix-logs/stand_unrepaired.py` (exit 0)
with `c4e94e5`'s `deploy.sh` and `reload-proxy.sh`:

```text
== 1. UNREPAIRED deploy.sh at A ==          deploy exit 0; new probe exit 0
burst of 12: [401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 401]
== 2. git checkout --detach B: inode 2114944 -> 2115050
== 3. UNREPAIRED deploy.sh at B (what the auto-deploy runs next) ==
reload-proxy.sh: the proxy re-resolved its upstreams.
deploy.sh: gate-w49fix-unrep is up at http://127.0.0.1:60231
unrepaired deploy exit 0
proxy restarted? False
proxy reads 8c387e4d4fa3ce4a checkout holds 753e57f82e234449
burst of 12: [401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 401]
== 4. the NEW probe on the unrepaired deployment ==
  /etc/nginx/conf.d/default.conf  DIFFERENT BYTES
      tree  753e57f82e234449712f96c015ef8787cbe32b2c5e17349dc32d5e074025f1e3
      proxy 8c387e4d4fa3ce4ab2c0e8ddbf661316601deed53087bd370d2833bdbe03cfce
verify-deployed.sh: the running proxy is NOT serving this tree's configuration -- 1 file(s) disagree.
new probe exit 6
== 5. the OLD probe on the same deployment ==
verify-deployed.sh: the deployed stack IS this tree (740f5a4 ...).
old probe exit 0
== 6. the REPAIRED scripts swapped in, deploy.sh again ==
reload-proxy.sh: the proxy was restarted so that it reads this checkout's files.
repaired deploy exit 0
proxy reads 753e57f82e234449 checkout holds 753e57f82e234449
new probe exit 0
burst of 12: [401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 429]
```

Both halves of B-1 are there: the checkout gave the file a new inode, and after the unrepaired
reload the running proxy still read A — the throttle absent behind a green deploy and a green
old probe.

The committed opt-in stand test (`TestOnADisposableStand`, the tree's own scripts) on the code
commit `49187a4`, instance `gate-w49fix-stand`, port 60231 — deploy at A, burst, checkout B,
an explicit `nginx -s reload` (still A, no 429), **the restart-removed mutant** (deploy exit 6,
probe exit 6 naming `default.conf`), the repaired deploy (restart, probe 0, 429 at the twelfth),
and a third deploy that restarts nothing (same container id and `StartedAt`, every service's
container id unchanged):

```text
$ AUDITMANAGER_PROXY_STAND=1 AUDITMANAGER_PROXY_STAND_DIR=<worktree>/.local/w49fix-stand AUDITMANAGER_PROXY_STAND_PORT=60231 AUDITMANAGER_PROXY_STAND_INSTANCE=gate-w49fix-stand .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider -s tests/integration/composition/test_proxy_config_follows_checkout.py -k TestOnADisposableStand
$ deploy.sh  -> exit 0
$ verify-deployed.sh  -> exit 0
burst of 12: [401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 401]
inode at A 2115041, after the checkout of B 2115128
burst of 12: [401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 401]
$ deploy.sh  -> exit 6
$ verify-deployed.sh  -> exit 6
$ deploy.sh  -> exit 0
$ verify-deployed.sh  -> exit 0
burst of 12: [401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 429]
$ deploy.sh  -> exit 0
$ verify-deployed.sh  -> exit 0
1 passed, 13 deselected in 46.28s
```

The mutant's own words on the stand: `reload-proxy.sh: the proxy still does not read this
checkout's configuration.` / `/etc/nginx/conf.d/default.conf  the proxy reads other bytes than
the checkout holds`.

**Gate-resident model** (`test_proxy_config_follows_checkout.py`, 13 cases + the opt-in one):
real git and filesystem; the `docker` stub holds the proxy's view of each mounted file as a hard
link taken at (re)start — the inode — so a checkout that replaces the file leaves the view on the
old bytes, and only `restart` re-links. It asserts the git half (inode changes), the docker half
(a reload leaves the view on A), the new probe red then green, the restart-removed mutant red
(`test_without_the_restart_step_the_reload_fails_and_the_probe_stays_red`), idempotence (no
`restart`, no throwaway `run`, start count unchanged; a second run after a repair restarts
nothing; an in-place write needs no restart), a broken configuration refused before any restart,
and that `deploy.sh` still hands the proxy to `reload-proxy.sh`. `test_deployed_stack_probe.py`
gains 10 cases for the new section and the new refusals (28 total).

Idempotence of a repeated `deploy.sh` with unchanged proxy files: proved on real containers by
the third deploy above, and in the model by
`TestAnUnchangedConfigurationRestartsNothing`.

### C — P02_SEAMS §7

The bullet names the operations whose `security` is `[]` in the sealed contract —
`issueToken`, `submitRegistration`, `readRegistrationStatus` — with the command that lists them
(run: `['issueToken', 'readRegistrationStatus', 'submitRegistration']`) and their code home
(`UNAUTHENTICATED_OPERATIONS`), and replaces the `T-6` clause with `R-55` (role set from
`expert`, `admin`), `R-60` (what each reaches, per `OPERATION_ROLES`), the administrator
operations that raise the credential generation, the self-action and last-administrator rules
(`W49-PLAN.md` §3.2), and the operator's `access.revoke`. No count is stated; the surface prose
guard and the seam register stay green:
`tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/domain_p02/test_seam_register.py` → `53 passed`.

### D — `R-62`

`AccountRepository.update_names` and `set_roles`: `if current is None or current.archived:
raise _no_such_account()`, as `reset_password`; in `set_roles` the now-redundant
`and not current.archived` beside the last-administrator check is dropped. Regressions:
`test_account_management.py::TestAnArchivedAccountIsNotChanged` (names; roles grant / swap /
remove-all; after restore both succeed) and
`test_user_management.py::TestAnArchivedAccountIsNotChanged` (four `updateUser` bodies → 404
`not_found` and every writable column and the role set unchanged; after `restoreUser` the
refused change had not come back and the same call succeeds).

### E — `R-63`

`UserRepository.authenticate`, `credential is None` branch: one `spend_a_verification`, nothing
written; `_NOTE_A_FAILED_REQUEST_ATTEMPT` removed (no other user:
`git grep -n _NOTE_A_FAILED_REQUEST_ATTEMPT` → none). `registrations.py`: the module-docstring
sentence "Every failed attempt of either kind is counted on the request's own throttle columns"
replaced. Regressions: `test_registrations.py::TestAPendingApplicantSigningIn` and
`test_registration_flow.py::TestAPendingApplicantSigningIn` — `FAILED_SIGN_IN_ALLOWANCE + 2`
correct BFF-shaped sign-ins, the counter 0 after every refused exchange and every status read
`pending`; `ALLOWANCE − 1` wrong sign-ins leave the counter at `ALLOWANCE − 1`, Q-1's correct
sign-in then answers `pending`, and `ALLOWANCE` wrong status reads still shut it; through the
served path each half of a sign-in costs one derivation for a pending login (right or wrong
password) and for a login with no request.

### Mutations for D and E (restore the old code → red)

`make mutation-copy MUT=/root/w49fix-mut` (exit 0, `MUTATION-COPY OK`); driver
`.local/w49fix-logs/mutate_de.sh <case>` copies the worktree's two files into the copy, then for
the case restores `631794c`'s file there, prints which copy files differ and proves the import,
and runs the regressions with `-o pythonpath=/root/w49fix-mut/src`, `PYTHONDONTWRITEBYTECODE=1`,
`__pycache__` cleared:

```text
== case baseline: copy differs from the worktree in:
imported /root/w49fix-mut/src/auditmanager/access/accounts.py /root/w49fix-mut/src/auditmanager/access/repository.py
17 passed, 1 warning in 23.58s
pytest exit=0

== case D: copy differs from the worktree in:
   src/auditmanager/access/accounts.py
E       Failed: DID NOT RAISE DomainError            (x4, the no-router class)
E       assert 200 == 404                           (x5, the served class)
9 failed, 1 passed, 1 warning in 7.47s
pytest exit=1

== case E: copy differs from the worktree in:
   src/auditmanager/access/repository.py
E           assert (1, None) == (0, None)            the refused exchange was counted
E       AssertionError: assert (5, datetime....y='Etc/UTC'))) == (4, None)
E       assert (1, None) == (0, None)                test_a_failed_exchange_counts_against_the_request
E           assert (1, False) == (0, False)
E       assert (5, True) == (4, False)               Q-1, through the served path
E       assert 4 == 2                                qa_w49 status-read throttle
6 failed, 1 passed, 1 warning in 7.98s
pytest exit=1
```

The one green in D is the no-router *after restore* case, green on the old code too by design;
the one green in E is the served derivation-count case, which asserts constant work is
unchanged.

### Tests changed because a ruling superseded what they asserted

| Test | Ruling | What changed |
|---|---|---|
| `tests/integration/access/test_registrations.py::TestTheStatusRead::test_a_failed_exchange_counts_against_the_request` | `R-63` | asserted `failed_sign_ins == 1` after a failed exchange; now `(0, None)`. Name kept: `W49-ACCESS-01c.md` M01c-14 cites it; the docstring says so. |
| `tests/integration/api/qa_w49/test_qa_w49_status_read.py::test_five_refused_attempts_of_either_kind_brake_the_request` | `R-63` | count after two reads + two exchanges `4` → `2`; after three exchanges + two reads the request is asserted open at `2`, and three more wrong reads are added before the unchanged final assertions (shut; right pair refused exactly like an unknown pair). Name kept: `W49-QA-01.md` item 8 cites it; the module docstring notes the amendment. |

Nothing in `test_roles.py`, `access/qa_w49/**`, the other `api/qa_w49/**` files or
`web/tests/unit/qa_w49/**` asserted superseded behaviour: the touched-suite run below was green
without changing them.

### Suites run (lane database, `.env` exported, exit 0 each)

```text
tests/integration/access/test_account_management.py tests/integration/access/test_registrations.py   81 passed in 88.14s
tests/integration/api/test_user_management.py tests/integration/api/test_registration_flow.py tests/integration/api/qa_w49 tests/integration/access/qa_w49 tests/integration/access/test_roles.py   128 passed, 2 warnings in 96.11s
tests/integration/composition   330 passed, 2 skipped, 1 warning in 150.02s
  skipped: test_router_answers.py:358 "this database holds no failed stage to render" (pre-existing); the opt-in stand
git diff --check   (clean)
```

### F — `R-65`

A04 gains one sentence: a run through the model proxy (`AUDITMANAGER_PROVIDER_MODE=proxy`)
also records `live`, because the field records provenance, not transport; `recorded` stays
FAIL. Checked before writing it: `src/auditmanager/bootstrap/composition.py:183`
`_provenance_mode` returns `"recorded" if transport == "recorded" else "live"`, and
`db/migrations/versions/20261002_0014_durable_analysis_effects.py:268` constrains
`provider_mode IN ('live', 'recorded')`. The sentence carries no migration-head or surface
number; `tests/contract/api_v1` and `test_alpha_acceptance_command.py` on the committed tree →
green (`58 passed` for the acceptance, prose-facts and identifier files together).

## 3. Contracts

- `contracts/domain/v1/identifiers.schema.json`: the two identifier-name enums gain `user_uid`,
  `request_id`. `candidate_revision` stays 9; `identifiers.json` is unchanged.
- No API contract change (`R-62`'s 404 is already declared for `updateUser`); error catalog
  unchanged; migration head unchanged.

## 4. Risks and known limitations

1. **`contracts/domain/v1/README.md` lines 8–10 and 753 still say the family schemas pin
   revision 8** — not edited (permission refusal, see the table above).
2. The schema's `identifiers.required` and `entities.required` lists still name only the 27
   pre-W49 names, while the schema's description says map-shaped catalogs "pin the complete
   current key set". Not a validation failure (`required` is a minimum), and outside Part A's
   grant (the two enums only).
3. A proxy restart drops its open connections for the moment it takes (`docker restart`,
   default 10 s stop timeout). It happens only on a deploy that changed a mounted file.
4. `deploy.sh` brings the stack up with `compose.server.yml` alone, so on a host that runs the
   TLS overlay its `up -d` already recreates the proxy without the overlay (pre-existing). The
   repair itself preserves an overlay; the deploy path's handling of the overlay is unchanged.
5. `verify-deployed.sh` proves the bytes the proxy reads, not the configuration nginx has
   loaded in memory; `reload-proxy.sh` reloads after any restart, so on the deploy path the two
   coincide.
6. `src/auditmanager/access/revoke.py`'s docstring still says "this system has no roles" — stale
   since `R-55`, outside every granted path.
7. The stand's api is a stand-in; the stand proves the proxy path only.

## 4a. The gate that this report does not rest on

A full `make gate` on the earlier head `c53fabe` (before Part F and the `62eb0c9` merge) ended
`5 failed, 3120 passed, 6 skipped, 3 warnings, 53 errors, 298 subtests passed in 1259.09s` /
`GATE: the canonical battery failed with pytest exit status 1.` / `make gate exit=2`. Every
failure and error was in `tests/integration/runs` (11 files), each a `StorageUnavailableError`
raised from a `BotoCoreError`/`OSError` transport failure to the lane's MinIO, after the
battery's own `test_restart_persistence.py` had run `make down`/`make up` (the lane's
containers carried a creation time of 09:54:40Z, mid-run). Run alone on the same clean tree
right after: `tests/integration/runs` → `118 passed, 3 warnings in 46.28s`, exit 0. The host
load average reached 17.8 in that window. Read as `OPERATING_CONSTRAINTS.md` §4.6's contention
shape, not a code defect; it was superseded anyway by the integrator's extension, and the gate
recorded above was run on the final head after waiting for another session's
`make alpha-acceptance` (not a gate) to finish.

## 5. For the integrator

- Merge `agent/w49-fix` (code commit `49187a4`, report commit after it) into
  `integration/w49`; the final gate on the merged candidate is yours.
- To re-drive the stand (needs a free port the lane owns; it removes what it creates):
  `AUDITMANAGER_PROXY_STAND=1 AUDITMANAGER_PROXY_STAND_DIR=<dir the daemon sees, not /tmp> AUDITMANAGER_PROXY_STAND_PORT=<port> AUDITMANAGER_PROXY_STAND_INSTANCE=<name> .venv/bin/pytest tests/integration/composition/test_proxy_config_follows_checkout.py -s -k TestOnADisposableStand`.
- On the live host the first deploy carrying this change will restart the proxy once (its
  `nginx.conf` has been stale since the proxy was created), which is the repair taking effect.

## 6. Containment

```text
$ git status --porcelain -uall          # at 49187a4, before and after the gate
                                        # (empty)
$ git diff --name-only 62eb0c9..49187a4 -- contracts/api infra/deploy/proxy .github \
    infra/deploy/compose.server.yml db/migrations uv.lock web/package-lock.json \
    docs/program/CURRENT_STATE.md docs/program/DEBT_REGISTER.md 'docs/program/OWNER_RULINGS_*' \
    docs/program/dispatch/PORT_REGISTRY.md | wc -l
0
$ git diff 62eb0c9..49187a4 --stat -- contracts | tail -1
 1 file changed, 6 insertions(+), 2 deletions(-)       (identifiers.schema.json, the two enums)
```

`src/**` changes are only `access/accounts.py` (D), `access/repository.py` and
`access/registrations.py` (E); `web/**` is untouched. No ref was pushed, no tag created, nothing
merged into `integration/*`. Stand containers, network and images (`gate-w49fix-stand`,
`gate-w49fix-unrep`) were removed by exact name by the stand's own teardown; the lane's
services are taken down with `make down` after this report and its volumes removed by exact
name (`gate-w49fix-postgres-data`, `gate-w49fix-s3-data`).
