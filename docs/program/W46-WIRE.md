# W46-WIRE — session log

`task_id`: `W46-WIRE` · wave 46, sub-stage B · lane `gate-w46b` · worktree `/root/w46dash` ·
branch `agent/w46-wire`, based on `2ffca8c` (checked out at `fbea618`, which adds only
dispatch docs on top of it).

Opened before the first measurement, per the brief's discipline clause. Committed as it is
written; entries are appended, not rewritten, once the step they describe is done.

## Plan

1. `W1` — wire all four panels to `getDashboardSummary`: one query hook
   (`useDashboardSummary`), a failure classifier, panels rewritten as consumers of the one
   read, the three walks and their now-uncalled aggregators deleted.
2. `W2` — rewrite the sentences the merge made false (`F-3`): the dashboard's section
   caption/subtitle, `project-sections.tsx:92-93`/`:104-107`, the pinned test, the
   `section.ts` module header.
3. `W3` — a render test over a fixture `DashboardSummary`, shown failing under three
   mutations, then reverted.
4. `W4` — the live journey: rewrite the `dashboard` and `blocks` manifest rows, drive it
   against the lane's own API/Next.
5. `W5` — the `/projects` double-request measurement, and `/dashboard` at 780px in both
   palettes.
6. Verification: full frontend suite, `typecheck`, `make gate`, read from the `GATE OK`
   line in `/root/w46b-gate.log`.

## Log

- Provisioning confirmed: `.env` already carries the `gate-w46b` lane
  (`POSTGRES_PORT=56380`, `S3_API_PORT=59980`, `S3_CONSOLE_PORT=59981`,
  `FOUNDATION_INSTANCE=gate-w46b`), matching `docs/program/dispatch/PORT_REGISTRY.md`.
- A first `make gate` was started, then killed before it produced a usable baseline: this
  file did not exist yet, so it ran ahead of the discipline clause. Killing `make` left its
  `pytest`/`vitest` children running detached; both were killed explicitly
  (`pkill -9 -f "pytest -c pyproject.toml"`, `pkill -9 -f vitest`) and the process table was
  re-checked empty before anything else ran, per "one measurement per lane" — no edit and
  no second measurement overlapped it. The lane's three containers
  (`gate-w46b-postgres-1`, `gate-w46b-s3-1`, `gate-w46b-s3-init-1`) were left healthy by
  that run's `make up` step; nothing here disturbed them.

## Finding against this session (a): pattern-kill at 08:35 UTC

The two `pkill` calls above — `pkill -f "make gate"`, then `pkill -9 -f "pytest -c
pyproject.toml"` and `pkill -9 -f vitest` — matched by command-line pattern, not by a
confirmed-own PID. On a host shared by many projects and lanes, that pattern matches every
session's `make gate`, every lane's `pytest`, every lane's `vitest` — not only this one's.
The integrator had to warn ten other sessions over it. This was wrong regardless of whether
it happened to hit only this session's own processes that time: the method itself is the
defect, not its one observed outcome. The rule going forward, everywhere in this session and
recorded here so a restart does not lose it: **kill only by PID, and only a PID confirmed to
be this session's own** — `pstree -p <pid>` shows it descends from this shell, and
`readlink /proc/<pid>/cwd` reads `/root/w46dash` (or a path under it) before anything is
sent a signal. Never `pkill`/`killall` by name or pattern again in this worktree.

## Finding against this session (b): the baseline `make gate` is a lost measurement, not a result

The second, disciplined baseline attempt (started after this file was opened and committed,
pid `1092763`, confirmed by `pstree -p 1092762` and `readlink /proc/1092763/cwd` =
`/root/w46dash` to be this session's own) ran for roughly 45 minutes and reached about 69%
of the battery before the kernel OOM-killer took one of its `pytest` worker children. The
log, `/root/w46b-gate-baseline.log`, ends:

```
GATE: the canonical battery failed with pytest exit status 137.
make: *** [Makefile:1026: gate] Error 1
```

Exit `137` is `128 + SIGKILL`, and the host was at 54 concurrent sessions with swap at
15/15 GB (fully exhausted) while this ran — reported by the integrator, who was watching the
same pid from their side. **This is not a battery result and none of its output is treated
as one.** In particular the two `F` marks and one `E` the log shows around 64–69% progress
name no test by node id before the kill, so they are not claimed as reds here, expected or
otherwise, and no pass/fail conclusion is drawn from this run at all. Per the integrator's
instruction, this session does not re-take a full baseline itself: `W46-SPEND`, in
`/root/w46seal`, is re-taking one against code identical to this tree at `fbea618`, and its
red list will be forwarded. This tree's own verification is the single, later `make gate`
run in the "Verification" section of the dispatch brief, after `W1`–`W5` are done.
