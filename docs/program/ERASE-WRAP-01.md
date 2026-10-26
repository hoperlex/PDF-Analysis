# ERASE-WRAP-01 — report

Task file: [`tasks/ERASE-WRAP-01.md`](tasks/ERASE-WRAP-01.md). Base `9cdad4551719a9893bddce93e5006fe73c67fe30` (`integration/ar-close-1026`), branch `agent/erase-wrap-01`. Plan items `PROD-07` (second half), `PROD-08`, `PROD-05b` (logging half and the memory mechanism); `ADR-0022` sections 3 and 6, `ADR-0021` section 4; `R-146c`, `R-146o`, `R-146aj`, `R-146n` items 2 and 7, `R-146ad`; register rows `D-166`, `D-232`.

**Status.** Built and verified in the tree with a stub in place of `docker` and no network. **No docker command was run, nothing touched a host or a compose project, and the wrapper has never run against the tool.** The wrapper's tests drive its order, arguments and exit codes; the tool's own tests (`PROD-07A`) drive the database and the bucket. Their first meeting is the rehearsal on a restored copy (`PROD-17`).

## 1. Result

1. `infra/deploy/erase-project.sh` — the operator's door to `scripts/recovery/project_erase.py`, as `PROD-07A` section 8 lists it. Dry run by default; `--apply` needs the project id, the actor, the reason, the owner-permission reference and the digest, and then makes the operator **retype the project id and the digest**; `--resume era_...` finishes a stopped erase. It takes **no `pg_dump` and no mirror**. 23 marked guards. Runbook section 17.
2. `DEPLOYMENT_RUNBOOK.md` section 18 — the offline copy of the key ring as `ADR-0022` section 6 defines it: eight numbered steps with the expected output of each (checked with `gpg` on a dummy file), the rotation rule, and a restore note. The lane did not make the copy.
3. `compose.server.yml` — a `json-file` `logging:` block (`max-size` 10m, `max-file` 5) and `mem_limit: ${ALPHA_MEM_LIMIT_<SERVICE>:-0}` on each of the six long-running services; six empty variables in `alpha.env.example`; runbook section 19 (what is set, how the owner measures with `capacity-probe.sh` and `docker stats`, how to set and verify, how to read an out-of-memory kill). **No memory number is invented.**

## 2. Files

| path | change |
| --- | --- |
| `infra/deploy/erase-project.sh` | new (executable; 23 guard blocks; `shellcheck -S warning` clean) |
| `tests/integration/composition/test_erase_project_script.py` | new: 129 tests |
| `infra/deploy/compose.server.yml` | header paragraph; six `mem_limit:` lines and six `logging:` blocks, each directly after the service's `restart: unless-stopped` |
| `infra/deploy/env/alpha.env.example` | six empty `ALPHA_MEM_LIMIT_*` variables with their comment |
| `tests/integration/composition/test_compose_log_and_memory_limits.py` | new: 60 tests |
| `docs/program/DEPLOYMENT_RUNBOOK.md` | sections 17, 18, 19 appended; two sentences of section 16 (the erase now exists) |
| `docs/program/tasks/ERASE-WRAP-01.md`, this file | new |

No existing test was modified or weakened (**before and after of modified tests: none**).

## 3. How the wrapper works

Guards first, none of which touches docker (shape of every option, `--stop-worker` and options of another mode refused, the typed names equal the configured ones, the owner's url present, the compose file and the **four** modules present, the dump directory writable). Then, inside the `api` image through `docker compose run --rm --no-deps -T`:

1. **the plan** (read-only): printed; its `plan-sha256` must be a digest, or the answer must be `nothing to do` (a finished erase: exit 0, nothing asked);
2. for `--apply`: the digest must equal the `--plan-sha256` the operator passed (`plan-approved`), then **two answers typed on stdin** (`retyped-confirmation`);
3. optionally (`--stop-worker`) the `worker` is stopped, and **started again on every path** by an `EXIT` trap;
4. **the erase**; then `manifest.json` on the host is hashed and compared with the `manifest-sha256` the tool printed (`manifest-verified`), and the report is printed: where the plan and manifest are, the three rest-state queries, and that no dump was taken so every existing dump, mirror and copy still holds the project.

Every call runs as `DATABASE_URL="$MIGRATOR_URL" docker compose run ...` (the owner's url in the environment of the compose process, never in an argument), as the operator's uid (`--user $(id -u):$(id -g)`), with the four modules mounted read-only one file each at `/purge/scripts/recovery/` under `PYTHONPATH=/app/src:/purge`, the dump directory `infra/deploy/dumps/erasures/` (0700, created by the wrapper) mounted at `/dump`, **stdin from `/dev/null`**, and no `PG*` variable.

## 4. Decided by the lane

- **D1** *Four single-file read-only mounts*, not the whole `scripts/recovery` directory the purge mounts: the brief names four modules and P-03 shows they are the tool's whole import closure (namespace packages, no `__init__.py`). Docker creates the missing mount-point directories; this is the one choice not exercised by an existing wrapper (see section 8).
- **D2** *The container runs as the operator's uid*, the dump directory is created 0700 by the wrapper, and `ALPHA_DUMP_ROOT` moves it (as for the purge). `ALPHA_ERASE_MODULE_DIR` moves the module directory (the purge's `ALPHA_PURGE_MODULE_DIR`), for tests.
- **D3** *No mode option is the dry run*; an option that belongs to another mode is **refused** (`options-match-the-mode`), not ignored; `--stop-worker` in a dry run is refused. A silent ignore would let an operator believe an erase had been asked for.
- **D4** *The wrapper reads the plan itself before it asks anything* and compares the digest with the one on the command line; the tool compares again (`plan-unchanged`). A changed plan costs the operator no keystrokes.
- **D5** *The answers come from stdin*, and docker is given `/dev/null`: `docker compose run` forwards stdin to the container, which would eat a piped answer. A test makes the stub read its stdin and shows that without the redirect the confirmation fails.
- **D6** *A stop after the commit is exit 4, never 3*, whatever status the tool chose: the tool prints `erase-id:` immediately after its commit, and 3 promises that nothing was changed. The text names the erase id and prints the `--resume` command, shell-quoted, with `ALPHA_DUMP_ROOT` if it was set; a test runs the printed command back through the wrapper.
- **D7** *`--stop-worker`* is the "offer the trap" of `PROD-07A` section 8 item 6: on `could not lock` the wrapper prints the option; if it was already given, it prints the commands that stop and start `api` and `web` (it does not run them).
- **D8** *`--resume` asks nothing and needs no digest*: it finishes an erase the operator already approved; it needs the actor and the permission reference, like the tool.
- **D9** *`manifest-verified`* is the wrapper's own addition: the tool wrote the manifest as the only record of what was erased, and a file that does not hash to the journalled digest is reported as a failure of an erase that otherwise completed.
- **D10** *Log numbers are literals*: `max-size` 10m and `max-file` 5 (50 MB per service, 300 MB for the stack) in each block, not variables; changing them is a reviewed change. They are the lane's, not the owner's; the owner can overrule them in review.
- **D11** *The memory variable defaults to `0`, not to empty*, because an empty string is not a size Compose can read (Docker's size grammar has no empty form) and Docker reads `0` as no limit. `alpha.env.example` ships the six variables empty, so "default to empty" holds where the owner edits.
- **D12** *The one-shot services carry neither*; a test refuses a limit on them.
- **D13** *Runbook sections 17 to 19 are appended at the end* of the file (`HARDEN-01` may add text too; the integrator renumbers on merge).
- **D14** *The wrapper does not join the copy key's file list* (section 13): it is interactive and needs a person; an unattended key must not be able to reach it. `test_the_copy_key_file_list_does_not_gain_this_script` pins the list at five files and the runbook states the reason.
- **D15** The tool's stderr is held in a `mktemp` file (removed by the trap) so the wrapper can recognise `could not lock` and `--resume era_...` in it and still show it.

## 5. Mutation proofs

### 5.1 The 23 guards of the wrapper, each deleted from a copy of the script

`test_deleting_the_guard_removes_the_refusal` runs the copy without the block: the refusal text is gone and, where the guard stands before the stack is touched, the copy goes on to call it (`reaches`). Where two guards stand in a row the first is also shown to reach the harm with the next removed (the `preflight-ran` case removes `plan-approved` and `retyped-confirmation` as well: it ends in an `--apply` call on a plan nobody read). A marker-count test fails if a guard has no case.

| guard | made true by | the copy without it |
| --- | --- | --- |
| `known-options` | `--dryrun`; `--project` with no value | the option is not parsed, the next guard refuses differently |
| `one-mode` | `--apply --dry-run`; `--resume ... --apply` | goes on in one of the modes |
| `stop-worker-needs-a-write-mode` | `--stop-worker` on a dry run | runs the dry run; the operator believes the worker was stopped |
| `options-match-the-mode` | `--reason`, `--plan-sha256`, `--actor` on a dry run; `--plan-sha256`, `--reason` on a resume | runs a dry run / a resume that ignores them |
| `names-required` | no `--database` | the next guard refuses differently |
| `project-identity-shape` | a name; lower case; none; `--project` with `--resume` | the name reaches the stack |
| `erase-identity-shape` | `era_nope`; a `prj_` id | the id reaches the stack |
| `actor-required` | none; empty; two words | reaches the stack |
| `reason-closed-list` | free text; none | the text reaches the stack |
| `owner-permission-ref` | none; blank; 201 characters; a newline; on a resume | an erase with no permission recorded |
| `plan-digest-shape` | none; upper case; 63 characters | reaches the stack |
| `env-file-present`, `instance-configured` | a missing file; one line of the file | the next guard refuses differently |
| `migrator-url-configured` | absent, empty, wrong scheme, not a url | the tool would refuse after a connection |
| `database-matches`, `bucket-matches` | another name | goes on against the configured one |
| `compose-file-present` | no file | no target check |
| `modules-present` | each of the four files absent in turn | goes on with a mount that is missing |
| `dump-dir-writable` | `erasures` is a regular file (a mode bit would prove nothing to a root-run test) | the erase starts although nothing can be recorded |
| `preflight-ran` | plan refused; failed; printed no digest | with the two guards after it also removed, an `--apply` call |
| `plan-approved` | the plan's digest differs from the passed one | an `--apply` call carrying a digest the project no longer has |
| `retyped-confirmation` | nothing; the digest only; another project; another digest; swapped; a trailing space; blank lines | an `--apply` call on an answer nobody gave |
| `manifest-verified` | the printed digest differs; the file differs; no digest | "verified against the file" is printed for a file compared with nothing |

### 5.2 The behaviour that is not a guard (an edit of the script, the test file run, the file restored — `cmp` clean)

| # | the edit | result |
| --- | --- | --- |
| M1 | no `--user` | red (`test_the_directory_is_the_operators_0700_and_the_container_runs_as_the_operators_uid`) |
| M2 | `--user root` | red (same) |
| M3 | `blob_reference_audit` not mounted | red (`modules-present` and the mount test) |
| M4 | modules mounted writable | red (`test_the_four_modules_are_mounted_read_only_...`) |
| M5 | docker may read stdin | red (`test_docker_never_reads_the_answers_...` and the dump-directory case) |
| M6 | the owner's url not handed over | red (`test_the_python_half_is_handed_the_owners_url_...`) |
| M7 | a `PG*` variable passed with `-e` | red (same) |
| M8 | no restart trap | red (`test_the_worker_is_stopped_for_the_apply_only_...`) |
| M9 | a stop after the commit is not special | red (the exit-4 and resume-command test) |
| M10 | the apply sent without `--dump-dir` | red (`test_the_order_is_plan_then_retype_then_apply_...`) |
| M11 | the apply sent with the fresh digest instead of the passed one | **green: an equivalent mutant** — after `plan-approved` the two are equal; removing that guard is §5.1 |
| M12 | container paths shown to the operator | red |
| M13 | the directory created with the default umask | red (mode 0700) |
| M14 | no `--no-deps` | red |
| M15 | a dry run falls through to the apply | red |
| M16 | the worker stopped before the plan is read | red |
| M17 | a resume prints no manifest report | red |
| M18 | a 3 after the commit passes as 3 | red |
| M19 | no rest-state queries | red |
| M20 | a refusal exits 1 | red (every refusal case) |

Test-level mutations (the script text edited inside the test): the resume command removed from the failure text; a `pg_dump` call inserted before the erase (the call recorder sees it and the healthy script has none); `trap cleanup EXIT` removed (a refusal leaves the worker stopped); the `</dev/null` removed; the owner-url prefix removed; a `-e PGHOST=` added.

### 5.3 The compose mechanism, edits of the real files (restored, `cmp` clean) and of copies inside the tests

| # | the edit | result |
| --- | --- | --- |
| C1 | the worker loses its `logging:` block | red |
| C2 | the proxy's default becomes `512m` | red |
| C3 | the web loses its `mem_limit:` | red |
| C4 | a default that is empty | red |
| C5 | a one-shot (`s3-init`) gets a `mem_limit:` | red |
| C6 | the example ships `ALPHA_MEM_LIMIT_WORKER=2g` | red |
| C7 | the example forgets a variable | red |
| C8 | `s3` logs with the `local` driver | red |

Inside the tests, the same family on copies: a limit read from another service's variable, a new service in neither list, a missing service, a malformed `max-size`/`max-file`/`options`, a duplicated or extra variable in the example. The variable interpolation the test reimplements (`${V:-d}`, `${V-d}`, `${V:?m}`, `${V?m}`, `$$`) and Docker's size grammar are themselves tested against their documented behaviour, and six unreadable values (`lots`, `1.5.5g`, `-1g`, ...) are shown rejected.

## 6. Premise result

Ten reads (task file P-01 to P-10) against the base; **all present, none differs from the brief.** Three facts shaped the build: the tool's closure is four files (P-03), the six/three split of the services (P-04), and that `ADR-0021` row 8 reads rendered output (P-05, section 8).

## 7. Tests and counts

| command (from the lane worktree, `BS` and the docker stub as in the dispatch) | result |
| --- | --- |
| `pytest tests/integration/composition/test_erase_project_script.py tests/integration/composition/test_compose_log_and_memory_limits.py` | **189 passed** (129 + 60) in 7.6 s |
| the neighbours that read the same files, in two runs: `test_acme_overlay`, `test_acme_deploy_guards`, `test_db_roles_deploy_guards`, `test_session_register_volume`, `test_deploy_script_refusals`, `test_pgvector_image_contract`, `test_minio_image_contract`, `test_api_token_channel`, `test_exposure_text_is_current`, `test_proxy_tls_path`, `test_purge_product_data_script`, `test_deploy_image_identity`, `test_apply_grants_script`, `test_reset_script_refusals`, `test_default_credential_gate` | 685 passed, 5 red only for want of the lane's `.env` (`test_api_token_channel`; 10 of 10 pass with it loaded) |
| `test_exposure_text_is_current`, `test_real_client_address_at_the_edge`, `test_stand_copy_refusals`, `test_readiness_command`, `test_proxy_config_follows_checkout`, `test_composition_root`, `test_settings_defaults`, `tests/integration/workers/test_worker_composition.py`, the two new files, `test_purge_product_data_script`, `test_deploy_script_refusals`, `test_db_roles_deploy_guards`, `test_acme_overlay`, `test_session_register_volume`, `test_api_token_channel` (with `.env`) | 886 passed, 2 skipped, **8 red, all in `test_real_client_address_at_the_edge.py`**: its tests that run `docker run` / `docker compose config` get the harmless stub's empty answer; they need a real daemon and do not read the lines this lane changed |
| `shellcheck -S warning infra/deploy/erase-project.sh` | exit 0 (also 0 for `purge-product-data.sh`) |
| the governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | RESULT-C |

`test_api_token_channel.py` needs the lane's `.env` loaded (it asserts so); with it copied and loaded all 10 pass. The `.env` is untracked and ignored.

## 8. Limits, and what was not verified

- **Nothing ran against docker.** Unverified, in order of how much they matter: (a) that real Docker accepts four single-file bind mounts under a mount-point directory the image does not have (D1; it creates missing mount points); (b) that the `api` image runs as an arbitrary uid with no passwd entry and no `HOME` (the tool imports `boto3` and `psycopg`, which do not need either; `PYTHONDONTWRITEBYTECODE=1` is set in the image); (c) that Compose accepts `mem_limit: 0` and does not reject it (Docker's size grammar reads `0` as a number; an empty string would not parse, which is why the default is `0`); (d) that `docker compose config` renders or omits a zero limit (the runbook says either is possible); (e) that the first deploy recreates all six containers, `postgres` and `s3` included.
- **`ADR-0021` row 8 is not closed by this lane.** The file declares both settings for every long-running service; the command reads rendered output and prints `[]` only when the owner's values are in force. Row 8 stays open until `PROD-05a` and the values.
- **`PROD-07` is not closed either**: the rehearsal on a restored copy (`PROD-17`) must precede the first real erase.
- **The `acme` service** (`infra/acme/compose.acme.yml`) is long-running and unrotated; it is outside this lane's paths. The proxy's 443 overlay only adds a port.
- No CPU, process-count or filesystem limit (`EXPOSURE-REVIEW-02` F-21); no secure wipe; no legal-hold check; a versioned bucket and a project with a non-`available` Blob are refused by the tool, not handled.
- The key-ring section was checked only for the `gpg` round trip on a dummy file; the restore note has not been rehearsed.
- `infra/deploy/README.md` indexes the scripts of the directory and does not list `erase-project.sh`; it is outside the grant.

## 9. Integration notes

- Merge `--no-ff`. `compose.server.yml` is shared with `HARDEN-01`: this lane's hunks are the header paragraph and the lines after each service's `restart: unless-stopped`; `HARDEN-01`'s are the `web` environment block, `server_tokens`/ciphers and `verify-deployed.sh`. If git reports a conflict in `compose.server.yml` it will be adjacent lines of the `web` service; keep both.
- The runbook gains sections 17, 18, 19 at the end; renumber if `HARDEN-01` appended too. Section 16's two edited sentences are the only change to existing text.
- The first deploy of the merged tree recreates the six long-running containers (new log and memory configuration). The old containers' logs go with them.
- Register: `D-166` (memory and log limits) is partly addressed (logs done, memory mechanism done, numbers wait for `PROD-05a`); `D-232`; `PROD-07` (wrapper built, rehearsal owed), `PROD-08` (procedure written, copy owed).
- Owner steps recorded, not done: the key-ring copy (section 18), the memory measurement and values (section 19), the rehearsal and the first erase (section 17).
- `infra/deploy/README.md` and `infra/acme/compose.acme.yml` are the two follow-ups outside this lane.

## 10. Forbidden paths untouched

RESULT-D
