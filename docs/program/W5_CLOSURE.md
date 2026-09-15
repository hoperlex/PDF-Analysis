# Wave 5 closure: PC-01 re-certified, and six defects neither session was allowed to fix

Written 2026-09-15 by the integrator. Convergence at `aa54fd1`; the gate is green: **797
passed, 5 skipped, 116 subtests** under the canonical battery, `make foundation` 35 passed,
`tests/e2e/pc01` 49 passed / 5 skipped, `git diff --check` clean.

Two independent sessions in parallel, ~21 and ~30 minutes. Neither authored the code it
examined; neither repaired anything. **Between them they corrected the integrator five
times.**

## 1. The verdict

**`W5-CERT`: PC-01 holds at `beaa7f7`.** Ten criteria proved from a clean checkout on a
dedicated instance, each one shown able to fail — not one rests on an environment assertion.
The live run through the proxy found **3 of 3 seeded issues and flagged 0 of 6 controls**,
identical product numbers to the original acceptance, at **USD 0.038** against the USD 1.00
ceiling.

Both accepted criterion-10 limits were re-established from scratch rather than inherited,
and both still hold. `checksum_mismatch`: the twelve operations were enumerated from the
frozen OpenAPI and **no write operation accepts a digest field at all**, so a caller cannot
declare one. `ungrounded_model_item`: proved by mutation against an isolated `src/` copy —
forcing every quotation unresolvable turned 3 findings into 0 with zero observation rows,
and **zero `grounded = false` rows** appeared in a database holding 89 observations.

**Criterion 10 is stronger than at `6d3c0f3`, not weaker.** The exhausted-retry path now
names `dependency_unavailable` instead of the generic `analysis_failed`, and `RetryPolicy`
refuses by construction any code the frozen catalog marks not-retryable, so a retry cannot
launder a bad answer into a good one. That is better conformance to §8's "no fallback".

## 2. The two sessions agreed, which is worth as much as a disagreement would have been

Both briefs sent their session at the same seam from opposite sides and said that a
disagreement between the two answers would be the most valuable thing the wave could
produce. They agree exactly: the exhausted-budget run row says `dependency_unavailable`,
`attempts` 3, backoff `(2.0, 8.0)`, nothing published. `W5-CERT` measured 10.41 s of real
wall clock from outside; `W5-ADV` measured the same ladder from inside.

That is a genuine cross-check, because neither could see the other's work.

## 3. Five corrections to my own record, each verified before being accepted

A subagent's report is a claim like any other. **I reproduced every correction below myself
before writing it down**, and one of them I initially doubted.

- **My brief's central premise was false.** I wrote that the wave-3 guard reached the
  unreachable-provider case "by a different route". It does not: `RecordedAdapter` over a
  missing recording raises `dependency_unavailable`, which is retryable, so it takes exactly
  the exhausted-budget route. What was missing was not the assertion but the *statement of
  the route* — nothing said the guard depends on that code staying retryable.
- **M2 is reddenable; `W3_CLOSURE.md` §1 said it was not.** I had generalised
  "unreddenable" from a two-row case. At 20 observations tied under one `finding_uid`,
  inserted in descending id order, the listing and the CSV disagree. Reproduced on a copy
  with `auditmanager.__file__` proven under it: **red 3 of 3, green on revert.** The lesson
  is about test design, not mutation: `W5-ADV`'s guard pins no sequence, it compares two
  live queries, so only a total order on both sides keeps them agreeing.
- **M3's result stands but my reason for it was false.** The database collation is
  `en_US.utf8`, measured — so `COLLATE "C"` is an active override today, not insurance
  against a future change. It is unreddenable because a CHECK pins ids to the Crockford
  alphabet, over whose 1024 pairs the two collations disagree **zero** times. My original
  wording invited a later reader to delete the `COLLATE` on the grounds the database is C.
- **"The runbook is current" was half right.** I checked that it expected
  `provider_mode=proxy` and did not check its migration head, which still said
  `0003_open_items`. The head is now `0005_truncated_call_status`.
- **"The second limit is a claim about exactly that code" was wrong in the specific.**
  `stage.py` and `provenance.py` moved, but `_ground` is byte-identical to `6d3c0f3` and
  `findings/grounding.py` is unchanged; the wave 2–3 edits there are additive provenance.
  The re-check was still worth ordering — inheriting it would have been wrong — but my
  stated reason overclaimed.

Both closure records are corrected in place, struck through rather than replaced.

## 4. Six defects. One fixed, five routed to wave 6

Neither session could repair; that is what makes their findings citable.

**Fixed here — `W5CERT-DEF-1`, because leaving it blocks the next certification.**
`_provider_file` reached for `REPOSITORY_ROOT.parents[2]`, which assumed one worktree
layout. Under `.claude/worktrees/<agent>` it landed on the repository root by luck; under
`/root/<name>` — **the layout my own dispatch briefs prescribe** — there is no third parent
and it raised `IndexError`, so the suite *errored* rather than skipping and criterion 4's
live step could not be reproduced from a dispatched worktree at all. Both sessions' worktrees
had that shape. Now it asks `git rev-parse --git-common-dir`, which resolves to the main
repository from inside any linked worktree; verified from both sessions' worktrees and the
main checkout. Outside a repository it returns `None`, so a missing credential skips rather
than errors. Test tooling, no certified behaviour touched.

**Routed to wave 6, deliberately unfixed:**

| Defect | Tree | Why it matters |
|---|---|---|
| `W5ADV-D1` | `src/` | `AttemptSummary.budget_exhausted` is `attempts >= budget` and never asks whether the last attempt *failed*. A run that succeeds on attempt 3 **publishes** and records `attempt_budget_exhausted: true`. Any query counting exhausted budgets includes successful runs. Confirmed by reading the code |
| `W5CERT-DEF-2` | `src/` | `composition.py:154` builds provider config from `dict(os.environ)`, not the `environ` handed to `create_app`, so **`AppSettings.run_cost_ceiling_usd` is written and read nowhere**. Confirmed: `create_app` resolves settings from `environ` at line 49, `_build_provider` reaches past it at 154. Not a deployment-level violation — one environment feeds both paths — but it breaks the composition root's stated contract and would make any future ceiling test **silently vacuous**, since `tests/conftest.py` strips the variable |
| `W5ADV-D2` | `db/` | `0004_cost_basis.downgrade()` drops the column; re-upgrading backfills every row to `estimated`, relabelling `measured` calls as derived — what 0004's own comment forbids. Not repairable in place: the immutability trigger refuses UPDATE |
| `W5ADV-D3` | `db/` | `0005`'s docstring justifies its CHECKs as "satisfied vacuously … no row anywhere has `status='truncated'` yet". True when authored, false since it shipped. The migration is correct; the recorded justification has expired |
| `W5ADV-D4` | `tests/` | My own wave-3 guard does not inject `sleep`, so it really sleeps ~20 s per battery proving nothing. `W5-ADV` left it alone despite owning the path, correctly |

**Why they are not fixed now.** Repairing them moves the tree past the commit just
certified, which is precisely the drift that made this wave necessary. Batching them into
one wave means one re-certification debt instead of five, and `W5-CERT`'s verdict stays
attached to a tree that still exists. None of the five is journey-visible, so none weakens
the verdict.

## 5. Version fixation — and the decision that is not mine

`origin/dev` advances to `aa54fd1`.

**`src/` and `db/` are byte-identical between `beaa7f7` and `aa54fd1` — a zero-line diff.**
Everything added since the certified commit is tests, reports, the certification artifact
and corrected records. The certified *behaviour* is exactly the behaviour at the tip.

So `origin/main` can advance, and there are two defensible targets:

- **`aa54fd1`, the tip** — recommended. Identical product behaviour, and it carries the
  certification evidence, the corrected closure records and the fix that makes the
  certification reproducible by the next session.
- **`beaa7f7`, the exact commit certified** — the stricter reading. Note that it would not
  contain its own certification artifact; that is not unprecedented, since PC-01's
  `report.json` is likewise absent from the accepted `6d3c0f3`.

Either way `main` moving is the owner's decision, not the integrator's, and nothing is
tagged.

## 6. A note on the provisioning prediction, so the record is accurate

Both briefs predicted the worktree-seeding defect "will fire", and neither session hit it.
**That is not evidence the defect is gone.** The launch prompts created each worktree from
`origin/dev` explicitly, so the defect was *preempted*, not absent. `origin/main` is still
parked at `6d3c0f3`, and a session provisioned the ordinary way would still land there.

## 7. Still owner-blocked

- **`OD-18`** — three to five named experts with committed slots. `P4-BHV-01` waits on this
  alone.
- **`OD-17`** — the next corpus shape; PC-02's precision evidence is saturated.
- **The 21st error code.**
- **Whether `origin/main` advances**, per §5.
