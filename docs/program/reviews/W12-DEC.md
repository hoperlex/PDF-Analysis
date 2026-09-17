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

---

## 1. Every rule mutated, and what reddened

All mutations were applied to `/root/w12dec-mut` and run against
`tests/integration/decisions` (32 tests at arrival, 42 after this stream). Every line was
printed back after mutation and read for **meaning**, not text; the `frozenset() or
frozenset({...})` class of non-mutation is why. Greens marked **GAP** are the yield.

| # | rule mutated | mutation | result |
|---|---|---|---|
| — | control | `raise RuntimeError` at the top of `record_decision` | 28 failed / 4 passed — the copy is live |
| M1 | `record_decision`: the dedicated `revoke` refusal | whole `if` block deleted | **GREEN — GAP** |
| M2 | `record_decision`: `event_type not in PC01_EVENT_TYPES` | block deleted | red (`KeyError` on `VERDICT_FOR_EVENT`) |
| M3 | `record_decision`: a comment event must carry a comment | block deleted | red (code becomes `CONFLICT`) |
| M4 | `record_decision`: `author_label` must not be empty | block deleted | red (`DID NOT RAISE`) |
| M5 | `CurrentVerdict.comparable()` | narrowed to `(self.finding_uid,)` | **GREEN — GAP** |
| M6 | fold: PD-01, never walk back past a revocation | skip `pending` verdicts | red |
| M7 | fold: `latest_comment` from an event of any type | restricted to `comment` events | red |
| M8 | fold: `latest_decision_id` / `decision_recorded_at` from an event of any type | restricted to verdict-bearing events | **GREEN — GAP** |
| M9 | fold: `_RAW_STREAM` order | `sequence_no` → `recorded_at` | green, **discarded as a non-mutation**: `recorded_at` is `clock_timestamp()` and strictly increasing, so the two orders coincide. Not a finding. |
| M9b | fold: `_RAW_STREAM` order | `sequence_no` → `sequence_no DESC` | red (2 tests) |
| M10 | `append_decision_under_key`: `CommandRepository().succeed(...)` | call deleted | red |
| M11 | `record_decision`: the pre-read before the insert | block deleted | red (1 test) |
| M12 | `record_decision`: the recovery after `IntegrityError` | block deleted | red (1 test) |
| M13 | `append_decision_under_key`: the fingerprint inputs | `event_type` and `comment` dropped | red |
| M14 | `record_decision`: `finding_exists` | block deleted | **GREEN — GAP** |
| M15 | `record_decision`: `observation_belongs_to_finding` | block deleted | red (2 tests) |
| M16 | `record_decision`: `_translate` on the `DBAPIError` arm | replaced with a fixed `INTERNAL_ERROR` | **GREEN — unreddenable by construction, §4** |
| M17 | `append_decision_under_key`: stale arm 1 (outcome carries no `decision_id`) | block deleted | **GREEN — GAP** |
| M18 | `append_decision_under_key`: stale arm 2 (no event under the command) | block deleted | **GREEN — GAP** |
| M19 | `publish_gate_result`: `FindingUid.new()` per grounded verdict | hoisted out of the loop | red, **loudly** (5 failed + 31 errors) |
| M20 | `PC01_EVENT_TYPES` | `comment` removed | red (5 tests at arrival) |
| M21 | `CONFIGURED_AUTHOR_LABEL` | `"local-reviewer"` → `"someone-else"` | **GREEN — deliberately not pinned, §4** |
| M22 | `decision_history`: `_EVENTS_FOR_FINDING` order | `sequence_no` → `sequence_no DESC` | red (3 tests) |
| M23 | `VERDICT_FOR_EVENT["revoke"]` | `"pending"` → `"rejected"` | **GREEN — GAP** |
| M24 | `record_decision`: the `SAVEPOINT` around the insert | `nested_transaction` removed | red (1 test) |
| M25 | `_EVENT_BY_COMMAND` predicate | `WHERE command_id = :command_id OR TRUE` | red (6 tests at arrival) |

M1 was additionally run against the **whole canonical battery**: 65 failed / 1713 passed /
126 errors / 582 subtests, **byte-identical to the same battery unmutated** (the run was
`pytest tests` unscoped, which includes the CP-00 material the gate ignores; the point is
that the two runs are indistinguishable). M5, M8, M17, M18 and M23 need no such run:
`rebuild_current_verdict`, `comparable()` and `append_decision_under_key`'s stale arms have
no consumer outside `tests/integration/decisions` — verified by grep across the tree.

## 2. Verdict on `W10-FND`'s two reading-only claims

**Claim 1 — "the projection's agreement with the raw stream *is* asserted, at
`test_decision_ledger.py` lines 157 and 304." — TRUE, and the line numbers are right, but
the assertion is narrower than the claim.**

The two comparisons are real and not circular: `rebuild_current_verdict` folds
`expert_decision_event` in Python, `finding_current_verdict` is computed by PostgreSQL, and
mutating the fold reddens them (M6, M7, M9b). `W10-FND` could not have known two things it
could only have learned by mutating:

* both sides of both comparisons call **one** accessor, `CurrentVerdict.comparable()`.
  Narrowing it to a single field (M5) leaves the whole suite green, because the claim
  narrows on both sides at once. Nothing pinned its field set.
* both comparison scenarios run a stream that **ends on a verdict-bearing event** —
  `accept, comment, reject, comment, accept` and `accept, reject, revoke`. So the clause
  "`latest_decision_id` and `decision_recorded_at` describe the most recent event of *any*
  type" is never put to the fold at all (M8). That clause is criterion 6's "a comment
  appended later and visible", and it *is* asserted against the view — by
  `test_appending_a_comment_after_a_verdict_does_not_overwrite_history` — but not against
  the rebuild.

So: asserted, yes; load-bearing across the projection's whole shape, no. Both gaps are now
closed (§3).

**Claim 2 — "`finding_uid` freshness is caught by the `finding` primary key plus 25
tests." — TRUE, and comfortably.** Hoisting `FindingUid.new()` out of the per-verdict loop
in `publish_gate_result` (M19) — the exact shape a freshness bug takes — produces **5
failures and 31 errors** across `tests/integration/decisions` and
`tests/integration/findings` alone. The primary key is the enforcement, exactly as claimed,
and it fires before anything else can paper over it. **No guard needed; none written.**

`W10-FND` read the tree correctly on both counts. The one thing reading could not give it
was how *wide* the first claim is, which is the difference the brief asked me to measure.
