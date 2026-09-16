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

## 7. There is one battery command, and it is this one

`GATE_C_DEFERRED.md` claims the backend suites run under "one battery command". No document
named it, so the three Gate W2 sessions each invented their own and reported three different
totals — 708, 718 and 729 — none of them comparable with another. Each said so in its report,
which is the only reason it was noticed.

The canonical command is:

```
.venv/bin/pytest tests --ignore=tests/contract --ignore=tests/checkpoint
```

**Since wave 7 it is also `make gate`, and that is the one to prefer.** The battery is one
of four things a wave must pass, and until wave 7 only `make foundation` was a target while
the other three lived here, as prose. The frontend suite went four waves without being run
because nothing named it. `make gate` runs all four and fails if any fails, so the
composition is reviewable in a diff rather than recalled from this paragraph.

The literal command above is kept for the case where one half is wanted alone — a session
whose brief covers only backend paths, say — and because a document that only says "run the
target" cannot be checked against the target. **If the two ever disagree, the Makefile is
the authority and this paragraph is the defect.**

Prefer the negative form over naming the suites positively. It picks up a directory a later wave adds, and
it excludes exactly the two quarantined trees named in `PROTOTYPE_PROFILE.md` §6.3 and
nothing else. A positive list silently stops covering whatever is created after it is
written.

Quote the count with the command that produced it and the commit it ran on. A bare test
count is not a measurement.

## 8. Freeze the tree before the battery, not during it

`tests/integration/foundation/conftest.py` carries an autouse session-scoped guard from
`P1-QA-00` that snapshots the tracked checkout before the suite and compares it afterwards,
failing if they differ — "a test that writes into the repository belongs in a `tmp_path`".

It does what it was built for, and it also fires when **you** edit a tracked file while a
run is in flight. `W2-PROV` lost two battery runs that way and both were green once re-run
against a committed tree. Commit first, then run. A red from this guard names the checkout
diff, so it is distinguishable from a real failure if you read it.

## 9. §6 is about residue, not about population

§6 tells you to report a cross-suite failure as interference rather than as a code defect.
That is right, and it is narrower than it looks.

The database is long-lived and the schema is append-only by design, so rows accumulate
across sessions and days: at the Gate W2 convergence the shared instance held 495 projects
that no suite in that run had created. A test that assumes a small table fails against that
population **on its own**, with nothing else running, and that is a defect in the test, not
interference.

The way to tell them apart costs one command: run your suite alone against the same
database. If it still fails, §6 does not cover it.

## 10. The mutation copy is a command, and the prose recipe was wrong

Every anti-vacuity proof here runs against a copy of `src/` outside the worktree, so that no
tracked file is ever edited to mutate. From wave 3 to wave 10 the recipe for building that
copy was carried as prose in dispatch briefs:

> symlink `contracts/`, `docs/` and `fixtures/` into that copy

**It was incomplete, and incompleteness here does not merely lose coverage — it manufactures
reds.** `db/` and `tools/` are also resolved from the copy's root, and a copy without
`tools/` fails four `tests/integration/p02_journey` tests **unmutated**. A sweep that went
straight to mutating would have filed four guards over a tree it never broke. Found by
`W10-FND` in wave 10 and reproduced independently by the integrator.

Since wave 10:

```
make mutation-copy MUT=/root/<name>-mut
```

It builds the copy, refuses a destination under `/tmp` (snap-confined docker cannot see it)
or inside the worktree, links all five directories, and **proves the copy is the tree that
will be imported** by printing `auditmanager.__file__` and asserting it resolves under the
copy. Shown to catch the old recipe: against a copy carrying only the three, it exits 1 with
`unreachable from the copy: ['db', 'tools']`.

Each link is derived from the tree, not from a brief:

| Directory | Why the copy needs it |
|---|---|
| `contracts/` | `exports/policy.py`, `documents/models.py`, `shared/errors/catalog.py`, `analysis/engine/registry.py` all resolve it from `parents[3]`/`[4]` |
| `docs/` | `analysis/text/lock.py` → `docs/program/P02_LOCK.json` |
| `fixtures/` | `analysis/text/recorded.py` → `fixtures/recorded/text_analysis` |
| `db/` | `shared/db/migrations.py` → `db/migrations/alembic.ini` |
| `tools/` | resolved **test-side** from `auditmanager.__file__` on purpose, so a mutation run gets the copy's ledger tool rather than silently reading the pristine one |

**The part that matters more than the list:** run your suites against the **unmutated** copy
and confirm they are green before you trust a single red. The target prints that instruction
and it is not decoration — a red from a copy you never baselined is not evidence. No list of
directories is safe against the next path someone resolves from the root; a baseline is.

