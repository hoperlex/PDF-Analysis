# Wave 46, sub-stage B: the join repaired, then cross-judged

Written 2026-09-28 by the integrator, `pdf-analysis-4f [73faf8]`, after `W46-JUDGE-A`
(`docs/program/reviews/W46-JUDGE-A.md`, merged at `2ffca8c`).

**The owner's rule for this wave, polled 2026-09-28:** the integrator lock is split by wave.
This session closes wave 46: repair, judges, final gate and a local tag. Wave 47 goes to
`pdf-analysis-4f [826d91]` only after that, based on the wave-46 tag. **Nothing is pushed
without the owner:** a push to `dev` was refused by the permission classifier on 2026-09-28.

## Why a sub-stage B exists

Sub-stage A merged a sealed aggregate read, `getDashboardSummary`, and a dashboard that does
not call it. Each stream did what its grant allowed. The gap is at the join (`F-3b`). The join
also made two captions false (`F-3`) and exposed a zero labelled *measured* over no provider
calls (`F-1`). Two properties the wave promised have no guard that can fail (`F-5`), and the
live journey is red by construction (`F-4`). Gate red #5 was ruled by the judge as a rule that
shared an assumption with its subject (`F-2`). **Integrator's ruling: the fix is in the test,
with no reseal for #5.**

## Two streams, in parallel

| stream | lane | worktree / branch | owns |
|---|---|---|---|
| `W46-SPEND` | `gate-w46a` | `/root/w46seal` · `agent/w46-spend` | the reseal (`F-1`), `F-2`, backend guards `F-5a` and `F-5c` |
| `W46-WIRE` | `gate-w46b` | `/root/w46dash` · `agent/w46-wire` | four panels on one read (`F-3b`), `F-3`, `F-5b`, the journey (`F-4`) |

**The single coupling is the shape of `run_activity.spend`.** After `W46-SPEND`, `spend` is
optional: absent when the deployment has no `model_call` rows, and present with all three
fields otherwise. `W46-WIRE` codes to that shape against today's client, where `spend` is
still required, so either merge order typechecks. The integrator merges `W46-SPEND` first and
runs `npm --prefix web run typecheck` on the join before anything else.

## Then the cross-judges, before the final gate

Two judges run independently on the merged tree: `W46-JUDGE-X` on `gate-w46j` and
`W46-JUDGE-Y` on `gate-w46k`. When both have reported, each reads the other's report and rules
on every finding in it: *upheld*, *narrowed* or *falsified*, each with evidence. This is both
sub-stage B's judge and the wave's cross-judging. Only then does the final `make gate` run,
followed by the tag `alpha-w46`.

## What goes to the register instead of into this stage

| row | finding | why it is not repaired here |
|---|---|---|
| `D-106` | the whole surface ignores undeclared query parameters (`F-2a`) | a decision for twenty operations and every client, so the owner's |
| `D-107` | the product cannot set a document's section | a feature; the owner decides whether and when |
| `D-108` | the live journey is not in `make gate` | wave 48's audit; this stage runs it by hand |
| `D-109` | *контракт* / *операция* on screen (`R-39`) | the owner's line; `W46-WIRE` avoids both words, which satisfies either reading |
