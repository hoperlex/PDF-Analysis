# `W12-DEC` review — the decision ledger, swept by mutation

Session `W12-DEC`. Worktree `/root/w12dec`, branch `agent/w12-dec`.

**`HEAD` on arrival: `3ebe34d`** ("merge: two tests-only streams for wave 12 stage A"),
the tip of `origin/dev`. The dispatch names base `0c3f464` "or later"; `3ebe34d` is later.

Instance `gate-w12d`, `POSTGRES_PORT=55680`, `S3_API_PORT=59280`, `S3_CONSOLE_PORT=59281`,
`POSTGRES_DB=audit_w12d`, bucket `auditmanager-gate-w12d`. Logs in `/root/w12dec-logs/`.

Status: in progress.

---

## Method

`make mutation-copy MUT=/root/w12dec-mut FULL=1`, then every suite run as

```
.venv/bin/pytest <suite> -o pythonpath=/root/w12dec-mut/src -p no:randomly
```

`-o pythonpath=...` **replaces** the `pythonpath = ["src"]` in `pyproject.toml` rather than
adding to it, so the worktree's `src/` is off the path entirely. There is no editable
install and no `.pth` in `.venv/lib/python3.12/site-packages`, so nothing else can shadow
the copy.

**Baselines taken before any red was trusted:**

| baseline | result |
|---|---|
| `tests/integration/decisions` against the unmutated copy | 32 passed |
| `tests/integration/decisions` + `tests/integration/findings` | 107 passed |
| the canonical battery (the `run_battery` scope) against the unmutated copy | **1492 passed / 5 skipped / 163 subtests** |

The battery figure reproduces the dispatch's expected gate exactly, from the mutation copy.

**Liveness control.** Before any real mutation, `raise RuntimeError("MUT-LIVE-CONTROL")`
was inserted at the top of `record_decision` in the copy: 28 failed / 4 passed. The copy
is what pytest imports; a green below is a green against mutated code, not against a
pristine tree.
