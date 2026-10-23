# V2-FINDING-MERGE-READ-01 — grouped v2 findings on the served read path

Task: `docs/program/tasks/V2-FINDING-MERGE-READ-01.md`. Base: `9dfa2691c8bfe0f33f206bdabc736aab96ae0f2c` on `origin/dev`.

## Result

The existing recorded v2 executor already persists `finding_merge` and publishes every accepted observation under one `finding_uid`, with `finding.canonical_observation_id`. The served `FindingAdapter` had still rendered one `FindingView` per observation. It now groups raw rows by persisted finding identity, shows the exact canonical member, attaches the others through `merged_observations`, and includes each observation's proposed severity and evidence. List and detail agree. The published finding count now counts distinct finding identities. The raw `published_findings` read stays member-level for comparison/export consumers.

A malformed canonical ID, duplicate member or inconsistent group refuses the read. The old v1 publisher's exact single-member shape with a null canonical ID remains readable only when its severity is absent and its profile is neither the recorded v2 nor beta v3 profile. That compatibility branch is explicit in both list grouping and detail SQL.

`D-201` is closed at the code level. Its original verdict/comment isolation and language guard items were completed by `WEB-HOOKS-PER-FINDING-01`; history severity was completed by `WEB-HISTORY-SEVERITY-FAULT-01`. The v2 merge publisher was already served; this task connects its grouped rows to the user-facing read.

## Changed files

- `src/auditmanager/findings/queries.py`, `src/auditmanager/findings/__init__.py`: canonical/member read projection, proposed severity, identity count and explicit v1 compatibility.
- `src/auditmanager/bootstrap/adapters.py`: list/detail transport mapping of the grouped read. This task owns that one composition integration slot.
- `tests/integration/findings/test_v2_merged_read_projection.py`: real SQL over a bounded in-memory schema through the shipped adapter, including a grouped v2 finding, corrupt canonical refusal and legacy v1 member.
- `docs/program/DEBT_REGISTER.md`, this report and the task file.

## Checks

- Failing first: the new list/detail test saw 2 items for one v2 `finding_uid` (1 red); after the implementation, 21 focused tests passed across the new read regression, merge publication plan and v2 severity semantics. The regression also covers both missing canonical forms and the legacy v1 row.
- `git diff --check`: passed.
- Task governance: no findings. Exact allowed-path inventory: all 7 staged paths match the task allowlist.

## Contracts and limits

No contract, route, migration, root dependency/lockfile, other composition file or global style changed. No live PostgreSQL or stand journey was run; the SQL behavior was checked with an in-memory relational fixture and the existing recorded merge tests. The full beta gate remains deferred under `R-135`.

## Integration

The adapter's list returns one view per `finding_uid`, and `get_finding` returns the same canonical/merged partition. `published_findings` remains the raw observation reader. Revert this commit to roll back; no flag is needed. Publication to `origin/main` requires separate authority and is not part of this task.
