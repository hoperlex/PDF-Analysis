# W13-BASE — the pre-FastAPI response baseline

Session `W13-BASE`, wave 13 stage 1. **The branch is `agent/w13-gold` and the worktree is
`/root/w13gold`**: the session was dispatched as `W13-GOLD` and renamed to `W13-BASE` after
launch, because the owner's direction to carry the normative document corpus into PostgreSQL
would have made "golden corpus" name two different things in one programme (`D-1.6`, `D-8`).
The branch keeps the old name deliberately — renaming a branch mid-run risks the commits and
buys nothing. Everything this session writes is named "response baseline".

- **HEAD on arrival:** `85aaa248043b16348d54f6d3f08b0660baa7c7c3` (`85aaa24`, `origin/dev`).
- **Instance:** `gate-w13a`, PostgreSQL `55690`, S3 `59290`/`59291`, database `audit_w13a`,
  bucket `auditmanager-gate-w13a`.
- **Scope:** `tests/**` and this file. Nothing under `src/`, `db/`, `contracts/`, `web/`.
  No new dependency, no bytes added under `fixtures/`.

## 1. Where the baseline lives, and why

`tests/characterization/w13_baseline/`.

`tests/characterization/` already exists in the tree and holds a README and nothing else:
*"Behavior/golden evidence extracted from legacy and product requirements."* That is exactly
what this is — evidence of what a surface does, captured before it is rewritten — and it is
the only top-level suite directory whose stated purpose is that and not "cross-boundary
evidence of a thing being built". It is under `tests/**`, which this session owns, so nothing
here needs another writer's tree.

It is not under `tests/integration/api/`, because those suites assert *rules*; this asserts
*bytes*, it is deleted the moment wave 13 ends, and mixing the two would leave a reader unsure
which failures are contract failures.

