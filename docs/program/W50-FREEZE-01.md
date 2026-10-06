# W50-FREEZE-01 — completion report

## Result

**DONE.** W50 (the shell) is frozen on code base `ead639f848b040491f1db7d4da3803216c82bd75`, the W49
closure published to `origin/dev`. Every lane starts from the commit that carries this report on
`integration/w50`, which is fast-forwarded to `origin/dev` before the first dispatch.

```yaml
wave_id: W50
contract_set:
  domain: 1.0.0-draft.1 revision 9, 29 opaque identities
  api: 27 paths / 34 operations / 77 schemas
  error_catalog: 23
migration_head: 0015_accounts_roles_registration
frozen_code_base: ead639f848b040491f1db7d4da3803216c82bd75
rulings: R-66 (OWNER_RULINGS §3.22), on top of R-55 … R-65
frozen_by: W50-FREEZE-01
```

W50 changes no contract, migration, backend file or root lock (`W50-PLAN.md` §6).

## Entry conditions

- `W49-INT-CLOSE` done and on `origin/dev` (`ead639f`).
- Gate evidence for the base: `W49-FIX`'s full gate on `49187a4` — literal `GATE OK`, exit 0;
  foundation 35; backend 3178 passed / 6 skipped / 298 subtests; frontend 1296 — and
  `git diff --name-only 49187a4 ead639f` names only six Markdown files (the two W49 reports, the
  register, the live state, the port registry and `contracts/domain/v1/README.md`), whose guards
  (`tests/contract/program`, `test_doc_prose_facts.py`, `test_surface_counts_in_prose.py`,
  `test_domain_identifiers_schema.py`) pass on `ead639f`: 90 passed. The full gate on the exact
  SHA `ead639f` waits for host headroom (load 20–37 and about 1 GB available for hours, from other
  projects' suites); the owner ordered W50 not to wait for it. Its result is appended here when it
  runs.
- Session subject carries `roles`, `displayLabel`, `initials`, `profileComplete`
  (`web/src/app/bff/session/subject.ts`, `store.ts`); the generated client exposes `getMe` and
  `listRegistrations` (`operations.gen.ts`).

## Rulings and plan amendments

- `R-66` (§3.22): the A-6 navigation amendment — four honest stubs (`/section-optimisation`,
  `/norms`, `/analysis-settings`, `/queue`), `/optimisation` hidden until W59, and the stub
  wording (a promise whose "when" is an event in words, never a number). `W50-PLAN.md` §3.1
  amended to match.
- `W50-PLAN.md` §6: `DEBT_REGISTER.md` added to `W50-INT-CLOSE`'s row (the planning session's
  finding: W50 had no owner for registering its own debts).
- `W50-PLAN.md` "Grants widened at `W50-FREEZE-01`": four task grants go beyond §4, each for a
  file the task's own change makes false.
- `DEBT_REGISTER.md` `D-70`: the stand runs `proxy` since 2026-10-06; the re-acceptance that would
  close the row is deferred by the owner while the proxy's availability is investigated.

## Task files

`W50-REGISTRY-01`, `W50-SHELL-UI`, `W50-HOME-01`, `W50-LAZY-01`, `W50-SHELL-FRAME`, `W50-QA-01`,
`W50-JUDGE-X`, `W50-JUDGE-Y` — generated from `W50-PLAN.md` §4 and
`docs/templates/TASK_TEMPLATE.md`; every premise measured read-only on `ead639f` on 2026-10-06;
`REGISTRY-01` lists every pin the new routes and the landing change move, with path:line.

## Baselines

- Frontend tests at the base: 1296 (the `49187a4` gate); per-file counts are taken by each lane
  from its own base with `npm --prefix web test -- --run`, as the plan's §2 asks.
- The `next build` route table (first-load JS per route) is **not** measured here: a production
  build under the present host load would measure the load. `W50-LAZY-01` compares against its own
  base, the Stage-A merge, measured on that lane before any change — the "before" that matters
  for lazy loading, since `REGISTRY-01` adds six routes.

## Ports

`PORT_REGISTRY.md` rows `56640` … `56720` / `60240` … `60321`, measured free with `ss -ltn` and
unregistered before allocation; the integration lane is `56720` so it never shares a database with
the pending `ead639f` gate on `56540`.

## Checks

- `tests/contract/program/test_wave_governance.py`, `test_doc_prose_facts.py`,
  `test_surface_counts_in_prose.py` — green on this commit
- `git diff --check` — clean

## Forbidden-hotspot proof

Only task files, this report, `OWNER_RULINGS_2026-09-17.md` §3.22, `W50-PLAN.md` (§3.1, §6 and the
grant note), the `D-70` note and `PORT_REGISTRY.md` change.
