# Operating constraints on this host

Sixteen dispatched sessions have run in this programme. Several lost time to the same six
environment traps, each rediscovering them alone. They are recorded here once, as
instructions rather than as history, and every brief points at this file.

Each is reproducible on this host. None is a defect in the tree; do not open one against
the code.

## 1. Docker cannot see `/tmp`

Docker on this host is a snap package, so `/tmp` is not the `/tmp` the daemon sees. A
worktree or scratch tree under `/tmp` makes `make up` fail with a path error naming
`/var/lib/snapd/void/...`, which reads like a broken compose file and is not one.

Put your worktree, and any scratch directory that needs live services, outside `/tmp`.
`/root/<something>-scratch` works. Reported by `B-III`, which spent its first pass
debugging compose.

## 2. `pyproject.toml` overrides an exported `PYTHONPATH`

`[tool.pytest.ini_options]` sets `pythonpath = ["src"]`, relative to rootdir. An exported
`PYTHONPATH` does not displace it. A mutation applied to a scratch copy of `src/`
therefore never reaches the run: pytest imports the original tree and reports green, and
that green looks exactly like a guard that does not fire.

Point pytest at the copy explicitly:

```
.venv/bin/pytest -o pythonpath=<copy>/src <tests>
```

and **prove the copy was imported before believing any mutation result** — print the
loaded module's `__file__` and confirm it resolves under `<copy>`:

```
.venv/bin/python -c "import sys; sys.path.insert(0, '<copy>/src'); \
    import auditmanager.<module> as m; print(m.__file__)"
```

A mutation run without that proof is not evidence. Reported independently by `B6` and by
the integrator, who fell into it twice.

## 3. A copy of `src/` alone will not import

Two modules read repository data files resolved from their own location, four parents up
from the module — that is, from the directory that contains `src/`:

- `auditmanager.shared.errors.catalog` reads `contracts/domain/v1/error-codes.json`
- `auditmanager.analysis.text.lock` reads `docs/program/P02_LOCK.json`

A scratch tree holding only `src/` fails at import, well before any assertion runs.
Symlink **both** into the copy, beside `src/`:

```
ln -s "$REPO/contracts" "$COPY/contracts"
ln -s "$REPO/docs"      "$COPY/docs"
```

Reported by `B-III` and by the integrator.

## 4. The session scratchpad is not isolated between sessions

Concurrent sessions share it. `B1` and `B8` each had a mutation tree overwritten mid-run
by a peer working under the same name, and each first read the result as a failure of its
own guard.

Name your scratch directory for your session — `<session-id>-scratch`, never a shared
`mutation/` or `scratch/`.

## 5. `make bootstrap` needs an explicit base interpreter

When the ambient interpreter is an active virtualenv, run:

```
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12
```

The bare form is refused, by design: the foundation is never built from an ambient
environment. **That refusal is the guard working.** Do not report it as a defect and do
not work around it.

## 6. The integration suites share one database

Some of them assert global state, so a suite can fail because of what another suite left
behind. Run only your own suite.

If you must run several, expect cross-suite interference and say so in your report rather
than filing a failure as a code defect. This is a known open item, not news.
