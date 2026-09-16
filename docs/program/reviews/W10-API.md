# `W10-API` review — mutation sweep of the API boundary and the shared kernel

Session `W10-API`. Worktree `/root/w10api`, branch `agent/w10-api`.

## Provisioning

`HEAD` on arrival: **`e08da85`** — *docs: the wave 10 dispatch — five parallel sweeps of
the rule surface*, the tip of `origin/dev`. The brief names `fb30e96` as the base; `e08da85`
is its child and carries only the dispatch documents, so the `src/` and `tests/` surface is
identical to the stated base. Not a discrepancy that changes anything, but recorded.

Surface read: `src/auditmanager/api/**`, `src/auditmanager/shared/**`,
`src/auditmanager/bootstrap/**` — 5 209 lines by `wc -l`, exactly as the brief states.

Instance `gate-w10c`, `POSTGRES_PORT=55610`, `S3_API_PORT=59210`, `S3_CONSOLE_PORT=59211`,
`POSTGRES_DB=audit_w10c`, bucket `auditmanager-gate-w10c`. `.env` copied from `.env.example`
and set to exactly that instance; never committed.

## Baseline

`make gate` on arrival, worktree clean: the canonical battery reports **816 passed, 5 skipped,
116 subtests passed** in 192 s. Exactly the figure the brief states. Measured with

```
cd /root/w10api && set -a && . ./.env && set +a
.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q tests \
  --ignore=tests/contract --ignore=tests/checkpoint
```

against tree `6c2c49f` with no working-tree modifications.

A first attempt to read this figure out of `make gate` reported *3 failed, 813 passed*. That
was not this worktree. The five wave-10 streams are subagents of one parent session and so
share one scratchpad directory; `W10-RUN` had written its own `gate-baseline.log` over mine.
The surviving lines named instance `gate-w10d`, ports `55620`/`59220` and `rootdir:
/root/w10run`. **No stream should redirect a log to the shared scratchpad under a generic
name.** This session's own logs live in `/root/w10api-work/`.

## Method

`src/` is copied to `/root/w10api-mut/`, with `contracts/`, `docs/`, `fixtures/` and `db/`
symlinked in — `analysis.text.lock` resolves `docs/program/P02_LOCK.json` from `parents[4]`
of its own module file, so a copy without `docs/` fails before reaching any assertion. Each
mutation is applied to a freshly re-copied `src/`, and every run collects
`/root/w10api-work/probe_test.py` first:

```python
assert auditmanager.__file__.startswith("/root/w10api-mut/"), auditmanager.__file__
```

so a result from a run that imported the worktree's own `src/` is a failure, not a false
green. The worktree's `src/` is never written.

Before any run, all 77 mutations were checked to apply exactly once and to change the file
text — the `frozenset() or frozenset({...})` mistake, which evaluates to the real set and
mutates nothing — and each was read back against its intended meaning.

*(sweep in progress)*
