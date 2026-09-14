# Wave `B-I` — closure

> **Status: accepted.** All six sessions landed, plus the two serial ones the integrator ran
> before them. Full acceptance on the merged tree: 18 gate commands, **941 tests**, every one
> exit `0`, including `make foundation`, the whole web suite, and `git diff --check`.

## 1. Measured throughput

| Session | Owns | Wall-clock | Rounds to accept |
|---|---|---:|---:|
| `B-0` pins | root lock, `P02_LOCK.json` | ~25 min | integrator |
| `B-0b` shared kernel | `shared/{errors,statemachine}` | ~30 min | integrator |
| `B1` ingest | `documents`, `ingest`, blob metadata | 37 min | **0** |
| `B2` stages | `analysis/{engine,ports,stages}` | 42 min | **0** |
| `B3` text AI | `analysis/text`, recorded fixtures | 40 min | **0** |
| `B4` findings | `findings`, `decisions` | 35 min | **0** |
| `B7` web project | project, upload, run progress | 26 min | **0** |
| `B8` web review | review, decisions, export | 31 min | **0** |

Six parallel, bounded by `B2` at 42 minutes. **Rounds to accept remains zero**, now across
thirteen implementation sessions. Wave elapsed including both serial sessions and integrator
convergence: about two hours, against `PROTOTYPE_WAVE_PLAN.md` §4's estimate of 1.5–2 hours
for `B-I` alone — the first row of that forecast to land on its own number rather than under it.

## 2. What convergence found that no session could

Three defects existed only in the space between two correct sessions. This is the return on
running the wave rather than one long session.

1. **The JSX runtime under vitest.** `tsconfig` sets `jsx: "preserve"`, correct for Next;
   vitest's esbuild reads the same file and takes it as the *classic* runtime, emitting
   `React.createElement` against a binding nothing imports. Every `shared/ui` component threw
   the moment a test invoked it. `B8` diagnosed it precisely; `B7` hit the same wall from the
   other side and reported it as "no component is render-tested". Reproduced and fixed at
   `92da844`.
2. **A guard reaching into a peer's tree.** `B7`'s no-second-polling-loop guard walked all
   four FSD layers rather than `B7`'s slices within them, and flagged `B8`'s one-shot read of
   run status — which the review screen needs to show whether the findings beside it came
   from a live call or a recording. Repaired without weakening: a direct call site must be
   named, the allowlist is asserted not to rot, and a named site that starts scheduling still
   reddens.
3. **Blob identity against `rejected`.** `A3` chose a content-derived `blob_id` per
   `machines.blob.retry`; `A1` wrote `uq_blob_available_content ... WHERE state = 'available'`
   with the comment "a rejected or erased blob must not block a later good upload". Verified
   by calling `derive_blob_id`: identity is `(sha256, size)` and `blob_id` is the PRIMARY KEY,
   so content uniqueness already holds in every state and the partial index cannot do what its
   comment claims. Neither session could see the other. **Open — item 2 below.**

## 3. Vacuous tests caught by their own owners

Three this wave, on top of the two in Gate A. Each was a test that reported success or failure
without exercising what it named.

* `B4` — the immutability test called `session.rollback()` between its UPDATE and DELETE
  attempts, discarding the row under test, so the DELETE matched zero rows, no row-level
  trigger was consulted, and the test reported that the `AM003` guard had **failed to fire**.
  Now each refusal runs in a savepoint asserting `rowcount == 1` first.
* `B2` — `document_context_build` read the block index's `text_layer_sha256` and never
  compared it, so against a longer document's text layer every span still landed in range and
  resolved to *some* text: a graph published over anchors pointing at the wrong characters,
  reported `succeeded`. Its warning generalises: **a span that resolves is not evidence it
  resolves to the right characters.**
* `B1` — discarded its own first mutation because it produced a collection error rather than a
  guard failure. A mutation that breaks loading proves nothing.

Mutation totals this wave: **11** (`B1`), 7 (`B2`), 7 (`B3`), 7 (`B4`), 6 (`B7`), 10 (`B8`) —
48 demonstrations, none editing a tracked file.

## 4. Open items — reconciled 2026-09-14

**Five of the six are closed.** Each row below was checked against the tree, not against this
document: the constraints were read from `pg_constraint`, the decisions from
`P02_LOCK.json`, and the projection from the dataclass. A list that says "open" about
something already done is the defect that cost the CP-00 line ten acceptance rounds, so it
is reconciled here rather than left to be re-derived.

| # | Item | State |
|---|---|---|
| 1 | `finding_observation.ungrounded_reason` had no CHECK | **closed** — migration `0003_open_items`; the five-value constraint is present. Nothing writes the column, per item 5.2 of the `B-II` closure, and the constraint is there so the vocabulary cannot drift when a producer appears |
| 2 | Blob identity against `rejected` | **closed** — owner ruled accept-the-consequence. The index is **kept**: the first attempt dropped it and two existing tests caught that, because the database does not know `blob_id` is derived. Only the false comment was wrong, and only the comment changed |
| 3 | Extractor divergence | **closed** — `B5` proved the pinned `pdfplumber` reproduces the committed text layer character for character, and `B-III` confirmed it independently. The manifest hashes still differ on all eight pages and the chain uses no manifest offset, so it is a trap for a future session rather than a defect |
| 4 | No public return value carried `display_title` | **closed** — projected through `DocumentVersionRecord`. Foundation invariant 3 names path, object key, filename and display ordinal; a display title is none of them. `source_filename` stays withheld |
| 5 | `OD-03` had no owner-decided ceiling | **closed** — USD 1.00, recorded in `P02_LOCK.json` where `B3`'s guard and `P4-OPS-01`'s measurement both read it |
| 6 | The catalog has no code for **usable output over a strict subset of the input** | **OPEN.** `B3` borrowed `partial_result_not_publishable`, whose intent fits and whose declared safe keys — `run_id`, `missing_stage_count` — describe a missing stage rather than a page subset. Closing it means a twenty-first code in a frozen twenty-code catalog, which propagates to the closed enum in `shared/errors`, the API schema, the generated client and every consumer. **That is an owner decision, not a repair** |

## 5. The historical suite is drifting further, by construction

`B3` confirmed independently in a throwaway clone: `tests/contract` and `tests/checkpoint` at
the wave base are **194 failed, 492 passed**. `test_the_reviewed_delta_is_exactly_what_is_declared`
was already red for `contracts/api/v1/*`, `fixtures/synthetic/ar/*` and `docs/architecture/*`,
and every Gate B session adding a tracked file joins that drift list.

This is not a regression and it blocks nothing: `PROTOTYPE_PROFILE.md` §6.3 puts CP-00
ratification mechanics in the historical class, outside every prototype gate, to be run only
in a disposable clone. But the gap widens with each wave, and closing it means the CP-00
ratification record reaching the Gate B deliverables — work owned by the CP-00 line, not by
this one.

## 6. Two operational defects, both confirmed by multiple sessions

* **Worktrees arrive on the wrong commit.** All five Gate B sessions plus `A7-FIX` were seeded
  at `43a84d9`, a W0.2-era commit 178 commits behind the base. Every one detected it and
  branched from the literal SHA, which is why the dispatch template's first rule exists.
  **The provisioning is the thing to fix, not the briefs.**
* **The scratchpad is not isolated between concurrent sessions.** `B1` and `B8` independently
  found their mutation trees overwritten mid-run by a peer. Both re-namespaced and re-ran.
  Until this is fixed, every brief should require a session-unique scratch directory.
