# Task ERASE-WRAP-01 — the operator's erase wrapper, the offline copy of the key ring, and log rotation with a memory-limit mechanism

task_id: ERASE-WRAP-01
status: completed in the development candidate (nothing run against a docker daemon, a host or a real compose project; see the report)

## Outcome

Three items of `PRODUCTION-READINESS-PLAN-01`, one lane of wave `PW3` (`D-232`): (1) `PROD-07`, second half: `infra/deploy/erase-project.sh`, the operator's door to `scripts/recovery/project_erase.py`, exactly as `PROD-07A-PROJECT-ERASE-CORE-01.md` section 8 lists it, with refusal tests in the composition idiom and a mutation proof for every guard, and its runbook section; (2) `PROD-08`: the runbook section of the offline copy of the key ring as `ADR-0022` section 6 defines it, a numbered procedure with the expected output of each step (the lane does not make the copy); (3) `PROD-05b`, the logging half: `json-file` rotation for every long-running service in `compose.server.yml` and a mechanism for per-service memory limits read from environment variables that default to no limit (no number is invented: `PROD-05a` has not been measured), with a test that the file renders with and without the variables.

## Depends on

- `PROD-07A-PROJECT-ERASE-CORE-01` (the tool; its report section 8 is this task's specification), `PROD-04-DB-ROLES-01` (the owner's url the wrapper hands the tool; both merged into the base).
- `ADR-0022` sections 3 and 6, `ADR-0021` section 4 and row 8; `R-146c`, `R-146o`, `R-146aj`, `R-146n` items 2 and 7, `R-146ad`; register rows `D-166`, `D-232`.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.6.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged (`0033_ar_v3_cite_stage_id`)
- base commit: `9cdad4551719a9893bddce93e5006fe73c67fe30` (`integration/ar-close-1026`), branch `agent/erase-wrap-01`

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/integration/composition/test_compose_log_and_memory_limits.py
- enumerator_owner: ERASE-WRAP-01 (the lane owns the logging and memory blocks of `compose.server.yml` in wave PW3; `HARDEN-01` edits other blocks of the same file)
- totality_query: `PYTHONPATH=src:$BS python -c "import sys;sys.path.insert(0,'tests/integration/composition');import test_compose_log_and_memory_limits as t;print(t.problems(t._compose(),t._example()))"` prints `[]`

The set is the long-running services of `compose.server.yml` (`LONG_RUNNING`, six) against the one-shots (`ONE_SHOT`, three): a service added to the file that is in neither list turns the test red, so a later lane must decide its log and memory limits. The wrapper's guards are a second maintained set, pinned by `test_every_guard_in_the_script_has_a_case_here` (23 marked blocks, each with a case).

## Captured premise evidence

- premise: ten reads (P-01 to P-10) of the base, run on 2026-10-27; all present, none differs from the brief. The ones that shaped the build: P-03 (four single-file mounts are the tool's whole import closure), P-04 (six long-running services, three one-shots, no `logging:` or `mem_limit` at the base), P-05 (row 8 reads rendered output, so only the owner's values can make it print `[]`).

### P-01 — the model wrapper: 16 marked guards, the two helpers that hand the owner's url to the tool
- captured_at: 2026-10-27
- command: `git show 9cdad4551719a9893bddce93e5006fe73c67fe30:infra/deploy/purge-product-data.sh | grep -c '^# >>> guard:' ; git show 9cdad4551719a9893bddce93e5006fe73c67fe30:infra/deploy/purge-product-data.sh | grep -n 'DATABASE_URL="$MIGRATOR_URL" compose run'`
- captured_output:
  ```text
  16
  249:    DATABASE_URL="$MIGRATOR_URL" compose run --rm --no-deps -T --user root -e PYTHONPATH=/app/src:/purge \
  255:    DATABASE_URL="$MIGRATOR_URL" compose run --rm --no-deps -T --user root -e PYTHONPATH=/app/src:/purge \
  ```
- interpretation: The purge wrapper is the model: 16 guard blocks, and the owner's url goes in the environment of the `docker compose` process at both helpers (never in a command line). The erase wrapper repeats that and adds its own guards.

### P-02 — the tool's command line, exit codes and the lines the wrapper parses
- captured_at: 2026-10-27
- command: `git show 9cdad4551719a9893bddce93e5006fe73c67fe30:scripts/recovery/project_erase.py | grep -n 'EXIT_OK, EXIT_USAGE\|REASON_CODES = \|"erase-id: \|plan-sha256: {\|manifest-sha256: {\|could not lock\|--resume", metavar\|--dump-dir", type'`
- captured_output:
  ```text
  94:EXIT_OK, EXIT_USAGE, EXIT_REFUSED, EXIT_FAILED = 0, 2, 3, 4
  103:REASON_CODES = ("client_request", "end_of_engagement", "test_data", "other")
  951:    out.append(f"plan-sha256: {plan.sha256}")
  1095:                    raise EraseRefused(f"could not lock the tables within {LOCK_TIMEOUT}: something is still writing. "
  1320:    print(f"erase-id: {committed.erase_id}", file=out, flush=True)
  1495:           f"manifest-sha256: {committed.manifest_sha256}", f"manifest: {committed.directory / 'manifest.json'}",
  1496:           f"plan-sha256: {committed.plan_sha256}", f"rows-deleted: {committed.rows_deleted}", "",
  1512:    mode.add_argument("--resume", metavar="era_ID", help="finish an erase that committed and did not complete")
  1518:    parser.add_argument("--dump-dir", type=Path, help="where <era_ID>/plan.json and manifest.json are written")
  1551:            print(f"erase-id: {committed.erase_id}", file=out, flush=True)
  ```
- interpretation: The flags are `--database --bucket --project --dry-run|--apply|--resume --plan-sha256 --actor --reason --owner-permission-ref --dump-dir`; exit 0/2/3/4; `erase-id:` is printed right after the commit; `manifest-sha256:` and `plan-sha256:` are the lines to parse; `could not lock` is the refusal the `--stop-worker` hint answers. Nothing in the tool is edited by this lane.

### P-03 — the four modules the tool imports, and nothing else of scripts/recovery
- captured_at: 2026-10-27
- command: `for f in project_erase product_purge schema_coverage blob_reference_audit; do echo "== $f"; git show 9cdad4551719a9893bddce93e5006fe73c67fe30:scripts/recovery/$f.py | grep -n '^from scripts\|^import scripts'; done; git ls-tree --name-only 9cdad4551719a9893bddce93e5006fe73c67fe30 scripts/__init__.py scripts/recovery/__init__.py | wc -l`
- captured_output:
  ```text
  == project_erase
  90:from scripts.recovery import product_purge as purge
  91:from scripts.recovery.blob_reference_audit import _CATALOG, _CATALOG_EXPECTED
  92:from scripts.recovery.schema_coverage import HEAD, VIEWS
  == product_purge
  73:from scripts.recovery.blob_reference_audit import _CATALOG, _CATALOG_EXPECTED
  74:from scripts.recovery.schema_coverage import EXEMPT_FROM_FINGERPRINT, TABLES, TRIGGERS, VIEWS
  == schema_coverage
  == blob_reference_audit
  18:from scripts.recovery.schema_coverage import HEAD as _HEAD
  0
  ```
- interpretation: `project_erase` imports the other three and they import only each other; `scripts` and `scripts/recovery` have no `__init__.py` (namespace packages), so four single-file read-only mounts under `/purge/scripts/recovery` with `PYTHONPATH=/app/src:/purge` are the whole closure (PROD-07A section 8 item 1).

### P-04 — the services of the base compose file, and that none carries a log or memory setting
- captured_at: 2026-10-27
- command: `git show 9cdad4551719a9893bddce93e5006fe73c67fe30:infra/deploy/compose.server.yml | grep -n '^  [a-z0-9-]*:$' | sed -n '4,20p' ; echo "--- logging/mem_limit occurrences: $(git show 9cdad4551719a9893bddce93e5006fe73c67fe30:infra/deploy/compose.server.yml | grep -c 'logging:\|mem_limit')"; git show 9cdad4551719a9893bddce93e5006fe73c67fe30:infra/deploy/compose.server.yml | grep -n 'restart:'`
- captured_output:
  ```text
  66:  web-sessions:
  70:  postgres:
  107:  s3:
  135:  s3-init:
  157:  migrate:
  175:  release-notes:
  190:  api:
  265:  worker:
  336:  web:
  376:  proxy:
  --- logging/mem_limit occurrences: 0
  78:    restart: unless-stopped
  114:    restart: unless-stopped
  153:    restart: "no"
  171:    restart: "no"
  188:    restart: "no"
  196:    restart: unless-stopped
  271:    restart: unless-stopped
  368:    restart: unless-stopped
  379:    restart: unless-stopped
  ```
- interpretation: Nine services; the six with `restart: unless-stopped` (postgres, s3, api, worker, web, proxy) are long-running, the three with `restart: "no"` (s3-init, migrate, release-notes) are one-shots; the file has no `logging:` and no `mem_limit` (`D-166` is still open at the base).

### P-05 — the ADR-0021 row 8 check this mechanism must satisfy
- captured_at: 2026-10-27
- command: `git show 9cdad4551719a9893bddce93e5006fe73c67fe30:docs/architecture/adr/ADR-0021-production-topology-and-operations.md | grep -n '^| 8 |' | cut -c1-420`
- captured_output:
  ```text
  313:| 8 | Memory and log limits on every long-running service (`R-146n` item 2) | `$DC config --no-env-resolution --format json \| python3 -I -c "import json,sys;c=json.load(sys.stdin)['services'];print(sorted(k for k,v in c.items() if k not in ('migrate','release-notes','s3-init') and not ((v.get('mem_limit') or v.get('deploy',{}).get('resources',{}).get('limits',{}).get('memory')) and v.get('logging',{}).get('optio
  ```
- interpretation: The row's check prints the services that are not one-shots and lack `mem_limit` (or the `deploy` memory limit) or a `logging.options.max-size`; the check runs on rendered output, so it is the owner's values that make it print `[]`: with every variable empty the rendered limit is `0`, which Compose may omit. This lane declares the structure and does not claim row 8 closed; the runbook says so.

### P-06 — capacity-probe.sh exists, is read-only and prints the RAM and disk facts the owner measures with
- captured_at: 2026-10-27
- command: `infra/deploy/capacity-probe.sh --path root=/ ; echo "exit $?"; grep -c 'docker' infra/deploy/capacity-probe.sh`
- captured_output:
  ```text
  path root: / filesystem=/dev/vda3 mount=/ avail_bytes=2252062720 size_bytes=126828056576
  ram_available_bytes: 8131997696
  swap_total_bytes: 17179865088
  swap_free_bytes: 13516705792
  load: 1.61 1.94 1.91
  exit 0
  2
  ```
- interpretation: It prints `path`, `ram_available_bytes`, `swap_*` and `load` lines and exits 0 (the values above are this development host's, not the VPS's); the only `docker` words in it are in comments (`never calls docker`).

### P-07 — the key-ring facts of the runbook procedure: where the ring lives, its variable, the rotation steps
- captured_at: 2026-10-27
- command: `git show 9cdad4551719a9893bddce93e5006fe73c67fe30:infra/deploy/env/provider.env.example | grep -n 'AUDITMANAGER_SECRETS_KEYS' ; git show 9cdad4551719a9893bddce93e5006fe73c67fe30:docs/program/DEPLOYMENT_RUNBOOK.md | grep -n 'AUDITMANAGER_SECRETS_KEYS=<kid>:<private>\|^### Rotation\|rewrap'`
- captured_output:
  ```text
  104:#AUDITMANAGER_SECRETS_KEYS=
  1580:* `provider.env` (`chmod 600`, the worker alone): `AUDITMANAGER_SECRETS_KEYS=<kid>:<private>`.
  1662:### Rotation
  1671:  `docker compose ... exec worker python -m auditmanager.executors rewrap` (it re-seals every
  ```
- interpretation: The ring is one line `AUDITMANAGER_SECRETS_KEYS=kid:base64[,kid:base64]` in `provider.env` (commented out in the example), section 14 already has the rotation steps the copy must follow, and `gpg` was exercised on a dummy file in the scratchpad to produce the expected outputs of the procedure.

### P-08 — the copy key's file list in runbook section 13, and that copy-serve.sh knows nothing of an erase
- captured_at: 2026-10-27
- command: `git show 9cdad4551719a9893bddce93e5006fe73c67fe30:docs/program/DEPLOYMENT_RUNBOOK.md | grep -n 'for f in copy-serve.sh' ; git show 9cdad4551719a9893bddce93e5006fe73c67fe30:infra/deploy/copy-serve.sh | grep -c 'erase'`
- captured_output:
  ```text
  1337:   for f in copy-serve.sh capacity-probe.sh apply-grants.sh lib/forced-command.sh lib/proxy-listeners.sh; do
  0
  ```
- interpretation: Five files; none is an erase script and `copy-serve.sh` does not mention one. The wrapper does not join the list: it is interactive and needs a person; the reason is in runbook section 17 and a test pins the list.

### P-09 — the environment: no PyYAML, so compose is read by indentation as the neighbours do; the venv has pytest
- captured_at: 2026-10-27
- command: `/root/projects/PDF-Analysis/.venv/bin/python -c 'import yaml' 2>&1 | tail -1; /root/projects/PDF-Analysis/.venv/bin/python -m pytest --version`
- captured_output:
  ```text
  ModuleNotFoundError: No module named 'yaml'
  pytest 9.1.1
  ```
- interpretation: Without a YAML parser the new compose test reads the file by indentation (the idiom of `test_acme_overlay.py`) and implements compose's variable rules itself, then tests that implementation against their documented behaviour.

### P-10 — the migration head and the tool's declared head (nothing here moves them)
- captured_at: 2026-10-27
- command: `git show 9cdad4551719a9893bddce93e5006fe73c67fe30:scripts/recovery/schema_coverage.py | grep -n '^HEAD' ; git ls-tree --name-only 9cdad4551719a9893bddce93e5006fe73c67fe30 db/migrations/versions/ | tail -1`
- captured_output:
  ```text
  41:HEAD = "0033_ar_v3_cite_stage_id"
  db/migrations/versions/20261026_0033_ar_v3_cite_stage_id.py
  ```
- interpretation: Head `0033_ar_v3_cite_stage_id`; this lane adds no migration and the tool's `head-is-declared` guard is unchanged.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane does not push, tag or touch `origin/main`; the integrator merges `agent/erase-wrap-01`.

## Allowed paths

- `infra/deploy/erase-project.sh`
- `infra/deploy/compose.server.yml`
- `infra/deploy/env/alpha.env.example`
- `tests/integration/composition/**`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/tasks/ERASE-WRAP-01.md`
- `docs/program/ERASE-WRAP-01.md`

`compose.server.yml` is edited in the logging and memory blocks only (the header comment and, per long-running service, the lines directly after `restart: unless-stopped`).

## Forbidden hotspots

- `src/**`, `scripts/recovery/**` (the tool core is frozen for this lane), `contracts/**`, `db/migrations/**`
- `infra/deploy/{deploy.sh,reset.sh,copy-serve.sh}` (the premise proved no pin needs a line), `infra/deploy/proxy/**`, `infra/acme/**`, `.github/**`, lock files
- `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals

- Running the wrapper against docker, the memory measurement `PROD-05a`, the first real erase, the rehearsal on a restored copy (`PROD-17`), making the key-ring copy.
- A memory number, a CPU or process limit, rotation of the `acme` service (another directory).
- Any change to the tool, to `deploy.sh`, `reset.sh` or `copy-serve.sh`; adding the wrapper to the copy key's file list.

## Deliverables

- `infra/deploy/erase-project.sh` (23 guard blocks), `tests/integration/composition/test_erase_project_script.py`.
- `compose.server.yml` (six `logging:` blocks, six `mem_limit:` lines, a header paragraph), `alpha.env.example` (six empty variables), `tests/integration/composition/test_compose_log_and_memory_limits.py`.
- `DEPLOYMENT_RUNBOOK.md` sections 17 (the erase), 18 (the key-ring copy), 19 (log rotation and memory limits) and two sentences of section 16.
- This file and `docs/program/ERASE-WRAP-01.md` (files, decisions, mutation tables, counts, limits).

## Required tests

- command: `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/composition/test_erase_project_script.py tests/integration/composition/test_compose_log_and_memory_limits.py`
- expected: all pass (counts in the report); then the neighbours that read the same files (the report lists them) and `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check`.

## Integration contract

- The wrapper takes the same `--database`/`--bucket` as the purge and the same `alpha.env`; it needs `MIGRATOR_DATABASE_URL`. Exit codes: 0, 2, 3 (nothing changed), 4 (including every stop after the commit, with the erase id and the exact `--resume` command). It writes `infra/deploy/dumps/erasures/<era_id>/` (0700) and nothing else, takes no dump, and checks `manifest.json` against the digest the tool printed.
- `compose.server.yml`: the first deploy recreates the six long-running containers (the configuration changed). `ALPHA_MEM_LIMIT_<SERVICE>` empty or unset renders `mem_limit: 0` (no limit). `HARDEN-01` edits other lines of the same file; the two lanes' hunks are disjoint (the lines after `restart:` and the header, against the `web` environment block).
- The runbook gains sections 17 to 19 at the end of the file; a lane that also appends sections renumbers on merge.

## Failure/idempotency/security cases

- The wrapper: a second apply of an erased project is `nothing to do` and asks nothing; a changed plan is refused before any question; an end of input is no answer; a stop after the commit is exit 4 with the resume command; the worker is restarted on every path; the owner's url is in the environment of the compose process only, never in an argument; no `PG*` variable is passed; the container never reads the operator's keystrokes.
- The compose mechanism: an empty variable is no limit; a variable Docker cannot read is seen by the test (and by `docker compose config`, step 5 of runbook section 19); a new service must decide.

## Rollback / feature flag

Empty the `ALPHA_MEM_LIMIT_*` variables for the memory side (they ship empty). The log blocks and the wrapper leave with a revert; the wrapper is a new file nothing else calls.

## Handoff

- changed files: see the report, section 2.
- commands/results: see the report, section 7.
- known limits: nothing ran against docker; first real run is the rehearsal `PROD-17`.
- integration notes: see the report, section 9.
