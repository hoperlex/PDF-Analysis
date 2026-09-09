# Task P1-INT-00 — pin the early foundation toolchain and command surface

> **Status: remediated on branch `agent/p1-int-00` as `P1-INT-00-R2`;
> READY_FOR_PRIMARY_REVIEW.** R2 closes the remaining blocker classes: the six reserved
> provider paths and the interpreters could still be redirected from the call site;
> `.env` accepted any name, a repeated name and an unmatched quote; `PYTEST_ADDOPTS`
> could turn a failing foundation suite green; and the governance environment was never
> checked for a distribution the lock does not name. R1 had closed four earlier classes:
> image pins overridable from the call site and from `.env`; literal provider `pytest`
> commands unable to import `src/`; the success sentinel accepted anywhere in the output
> instead of last; and a bare `make bootstrap` writing to the user's uv cache.
> Executed from the `FF-01 ACCEPTED` commit `0b01a3eefe0e6724f6570ccebb9154daf1fdbaec`.
> This task is **not accepted**: `P1-INF-01`, `P1-DB-01` and `P1-STO-01` stay blocked
> until an independent review accepts the pins and the command surface, and until the
> integrator records the resulting `P1_INT_SHA`.

## Outcome

One reproducible Python toolchain, environment contract and root command surface that
the three PostgreSQL/S3 provider lanes consume without modifying.

## Depends on

- `P0-FND-00` — completed with `FF-01 ACCEPTED`

## Frozen inputs

- `docs/program/PROTOTYPE_FOUNDATION_FREEZE.md` at the accepted commit
- CP-00 domain/analysis/event contracts: read only
- migration head: `none`
- base commit: exact `P0-FND-00` integration commit, pinned by the integrator at dispatch

## Allowed paths

- `.python-version`, `pyproject.toml`, `uv.lock`
- `Makefile`, `.env.example`
- `docs/program/FOUNDATION_LOCK.json`
- foundation command sections in `README.md`
- `docs/program/tasks/P1-INT-00.md` status/handoff

## Forbidden hotspots

- runtime provider code, `infra/local/**`, `db/migrations/**`, `tests/**`, `web/**`
- every contract, CP-00 artifact and Git tag

## Non-goals

- No PostgreSQL/MinIO service, migration, storage adapter or product code.
- No frontend toolchain and no dependency needed only by a later stage.

## Deliverables

- exact supported Python, `uv`, runtime/test dependency and container-image pins
- reproducible lock; no floating dependency or image reference
- `.env.example` with all service, application and lane-isolation names frozen by FF-01
  and disposable local values
- the nine literal `make` targets frozen by FF-01
- stable forwarders for the later INF, DB, storage and QA implementations at the exact
  paths reserved by FF-01; missing implementations fail explicitly rather than falling
  back to a substitute
- machine-readable `FOUNDATION_LOCK.json` containing pins, paths and commands

## Required tests

- Command: `make bootstrap`
  Expected: exit `0`; `.venv/bootstrap/bin/python` and `.venv/bin/python` both execute
  their locked smoke probes, and a second run changes no lock or tracked file.
- Command: `make -n up down check-services migrate check-db check-storage test-foundation foundation`
  Expected: exit `0`; all required targets exist.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Provider lanes may rely on exact locked dependencies, environment names and commands.
They may not add or upgrade a root dependency or change the command surface.
Each lane must override the disposable defaults with a unique `FOUNDATION_INSTANCE`,
ports, database and bucket before it starts live services.

## Failure/idempotency/security cases

- Bootstrap fails when a required lock is missing; it never regenerates silently.
- No real credential or secret is stored in tracked files.
- Repeated bootstrap is idempotent.

## Rollback / feature flag

Revert before provider integration. A later pin change is a new single-owner task.

## Handoff

Delivered on `agent/p1-int-00` from base `0b01a3eefe0e6724f6570ccebb9154daf1fdbaec`.

**Changed files.** `.python-version`, `pyproject.toml`, `uv.lock`, `Makefile`,
`.env.example`, `docs/program/FOUNDATION_LOCK.json`, the foundation command section of
`README.md`, and this status/handoff. Nothing else is touched.

**Pins.** Python `3.12.3`; `uv 0.12.11` installed from a sha256-verified artifact set;
`psycopg[binary]==3.3.5`, `SQLAlchemy==2.0.52`, `alembic==1.19.2`, `boto3==1.43.90`,
`pytest==9.1.1` (group `test`). `uv.lock` holds 23 `[[package]]` entries: 22 third-party
packages plus the virtual root, of which 20 install on linux/x86_64 (`colorama` and
`tzdata` are `sys_platform == 'win32'`). Images are pinned by
tag **and** multi-arch index digest: `postgres:17.11-trixie`,
`minio/minio:RELEASE.2025-09-07T16-13-09Z`, `minio/mc:RELEASE.2025-08-13T08-35-41Z`.
No floating tag and no `latest` reference exists. Exact digests, lock hashes and the
literal invocation of every target are in `docs/program/FOUNDATION_LOCK.json`.

**Bootstrap.** `make bootstrap` builds `.venv/bootstrap` from
`requirements/validation.lock` with `--require-hashes` and `.venv` from `uv.lock` with
`uv sync --frozen`, then probes both against their own locks. It never writes a lock: a
missing `uv.lock` is a hard, explicit failure. A second run installs nothing and leaves
every tracked file and both locks byte-identical.

**Host prerequisites.** CPython exactly `3.12.3` as a base interpreter (an active
virtualenv is refused, not silently used); Docker with the `compose` plugin for the
service targets; network to PyPI and the container registry on first use. Where
`python3.12` is not on `PATH`, pass `FOUNDATION_PYTHON=<path>`.

**Commit for the provider lanes.** Lanes must not branch from `agent/p1-int-00`. They
branch from the integrator's P1-INT-00 integration commit (`P1_INT_SHA`), recorded by
the integrator after this task is accepted, and each lane must first give itself a
unique `FOUNDATION_INSTANCE`, `POSTGRES_PORT`, `S3_API_PORT`, `S3_CONSOLE_PORT`,
`POSTGRES_DB` and `S3_BUCKET` in its own `.env`.

**Evidence contract for the provider lanes.** `check-services`, `check-db` and
`check-storage` must each print `FOUNDATION-CHECK OK <target>` as their last actual
output line, after their assertions pass. `make` refuses a zero exit status without that
line, visible output after it, and a reserved path that exists but is zero bytes. Colour
codes, CR and surrounding whitespace are normalised; trailing blank lines are ignored.
The checker runs with `PYTHONUNBUFFERED=1` so the captured order is the order the checker
actually wrote in, not an artefact of stdout buffering. This is a P1-INT-00 addition to
the command contract, not an FF-01 requirement: an exit code alone is not evidence, and
without it a stub checker would make `make foundation` report success having proved
nothing. Reject it in review if the program does not want it — it is a deliberate
constraint on three lanes.

**Import contract.** Two root-owned mechanisms, no lane-local `sys.path` work:
`PYTHONPATH=src` for module invocations, and `pythonpath = ["src"]` under
`[tool.pytest.ini_options]` so that a literal `.venv/bin/pytest tests/integration/db` (or
`.../storage`) imports foundation code from `src/` with no environment override. The
config also sets `--import-mode=importlib`, so two lanes naming a test file identically do
not collide when their directories are collected together. Because `pyproject.toml` is now
a pytest configfile, this applies to every `pytest` run in the repository — including the
historical `tests/contract` and `tests/checkpoint` suites, which may not be run from this
checkout, so that effect is unverified here.

**Image immutability.** The effective image reference is read from the Makefile's own
`override FOUNDATION_*_IMAGE :=` lines at run time, so it survives a target-scoped make
assignment (`--eval`, including via `MAKEFLAGS`/`GNUMAKEFLAGS`) and a second `-f`
makefile — a make variable can be shadowed, the file's bytes cannot. `.env` is parsed as
data and refused outright if it names one of the three.

**`.env` is data, never code.** It is parsed as `NAME=VALUE` lines instead of being
sourced. Sourcing let a lane's `.env` redefine `compose()`, redirect `PATH`, or `exit 0`
out of a target and report success having done nothing. Names are a **strict allowlist of
exactly the 15 names FF-01 section 3 freezes** — a denylist could only refuse the
ambient-behaviour names somebody had thought of, so `PYTEST_ADDOPTS`, `DOCKER_HOST`,
`AWS_*` and every other such name are now refused by one rule. Each of the 15 must appear
exactly once: a missing name and a repeated name are both explicit failures. Quotes are
accepted only as one matching pair wrapping the whole value with no quote of that kind
inside it and no escaping; an unmatched quote is refused rather than kept as an ambiguous
literal. There is no interpolation inside values.

**Reserved paths and interpreters cannot be redirected.** The six FF-01 reserved provider
paths, `RUNTIME_PY`, `BOOTSTRAP_PY` and `VALIDATION_LOCK` are declared `override` with a
literal value and re-read at run time out of the Makefile's own bytes, exactly as the
image pins are. A command-line assignment, `make -e`, a target-scoped `--eval` (including
one carried in `MAKEFLAGS`/`GNUMAKEFLAGS`) and a second `-f` makefile all leave the
forwarders addressing the exact frozen paths. The path values themselves are unchanged:
FF-01 names them, so this task hardened how they are resolved and not what they are. This
also closes `make test-foundation RUNTIME_PY=/bin/true`, which would otherwise have run
`/bin/true -m pytest` and exited 0 having executed nothing.

**The foundation suite runs hermetically.** `test-foundation` scrubs every `PYTEST_*`
variable, the `PYTHON*` names that change interpretation and the loader names
(`LD_AUDIT`, `LD_PRELOAD`, `LD_LIBRARY_PATH`, `OPENSSL_CONF`, `GLIBC_TUNABLES`), sets
`PYTHONNOUSERSITE=1`, pins the pytest config file with `-c pyproject.toml --rootdir=.`,
and refuses pytest exit status 5. The scrub is done by unsetting inside a subshell rather
than through `env`, because an exported bash function named `env` shadows the binary.
`make` is also stopped from handing `BASH_ENV`, `ENV`, `SHELLOPTS` and `BASHOPTS` to the
recipe shell, and `-t` (touch) is refused at parse time.

Measured against a deliberately failing test: the raw pre-R2 command exited 0 under
`PYTEST_ADDOPTS=--collect-only`; through `make test-foundation` that attack and each of
`PYTEST_PLUGINS`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD`, `-k`, `--deselect`, `PYTHONOPTIMIZE=2`,
`BASH_ENV` with an exit-0 trap, an exported `env()` function, and a `pytest.ini` dropped
inside the suite directory all left the assertion executing and the target non-zero.

**What this does not cover, stated rather than implied.** `MAKEFLAGS=-n` is a dry run:
make executes no recipe, so no in-recipe guard can fire. It is not refused because
`make -n` is itself a required check; it is also self-evident, since a dry run prints no
`bootstrap OK` and no pytest summary. A `conftest.py` inside the suite, or a plugin
present in the runtime lock, can still change outcomes — both are inside `P1-QA-00`'s own
deliverable and are reviewed there, not neutralised from here. A `.pth` file written into
`.venv/lib/python3.12/site-packages` executes during interpreter startup, after the scrub
and before pytest reads its environment; `.venv` is git-ignored and its file-level
integrity is not verified.

**The governance environment is exactly its lock.** `pip install --require-hashes` only
adds and upgrades, so `bootstrap` now removes any distribution
`requirements/validation.lock` does not name and then proves the whole set matches. A
`six` installed by hand was reported by the probe and removed by the next bootstrap,
returning the environment to the six locked distributions plus the venv-seeded `pip`.

**Caches.** `UV_CACHE_DIR` is pinned to the git-ignored `.local/uv-cache` and
`PIP_CACHE_DIR` to `.local/pip-cache`, so a bare `make bootstrap` writes no cache under
the user's home and needs no override.

**Known limitations.** No target beyond `bootstrap` has been executed end-to-end, because
every one of them forwards to a provider implementation that does not exist yet; each was
exercised only to the point of its explicit refusal. The full list, including the
`.venv/bootstrap` nesting that FF-01's literal paths require, is in
`docs/program/FOUNDATION_LOCK.json` under `known_limitations`.
