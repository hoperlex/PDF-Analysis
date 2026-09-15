# Version fixation: what is published, where, and why

Two published lines, one rule each. Written 2026-09-15.

## The two lines

| Ref | Carries | Moves when |
|---|---|---|
| `origin/main` | **accepted checkpoints only** | a checkpoint is accepted by the owner |
| `origin/dev` | the working tip of `planning/prototype-roadmap` | any integrator merge worth publishing |

Both are fast-forward-only. `origin/main` is an ancestor of `origin/dev`, which is an
ancestor of the working line; the prototype line has never diverged from `main`, so no
merge is ever required to publish either.

## Current fixation

- `origin/main` → `6d3c0f3d9b633e2dcd894c28e53bc16a00189544`, **the PC-01 acceptance
  commit**, `merge(c2-repairs): PC-01 passes through the composed application`. Accepted
  2026-09-14; the live run found 3 of 3 seeded issues and flagged 0 of 6 controls.
  Published 2026-09-15, advancing `origin/main` from `43a84d9` — a W0.2-era commit that
  had not moved since before the prototype line began.
- `origin/dev` → the tip at publication time.

## No tag for PC-01, deliberately

`CHECKPOINT_REGISTRY.md` records that PC-01 carries no tag: it is a product checkpoint,
and CP-00 remains unratified on its own line, which this fixation neither advances nor
disturbs. The branch ref is the fixation. Tagging PC-01 would contradict that record and
is an owner decision, not an integrator one.

## What publishing `main` also fixed

`GATE_B1_CLOSURE.md` §6 records an operational defect confirmed by every dispatched
session: **worktrees arrive on the wrong commit** — all five Gate B sessions plus
`A7-FIX` were seeded at `43a84d9`, 178 commits behind their base, and each had to detect
it and branch from the literal SHA. It is why the first rule of every dispatch template
tells a session to check its own `HEAD` before anything else.

The cause was not the briefs. The harness seeds an agent worktree from `origin/main`, and
`origin/main` was `43a84d9`. Measured rather than inferred: all **23** `worktree-agent-*`
branches in this repository point at exactly `43a84d9`, and that is byte-for-byte the
value `origin/main` held until this publication.

Advancing `origin/main` to the PC-01 acceptance commit therefore closes that defect for
every session dispatched from now on: a fresh worktree seeds 240 commits further forward,
at an accepted checkpoint rather than at a W0.2-era tree. The dispatch template's
`HEAD`-check rule stays — it is cheap, and it is what caught this — but it should stop
firing.

## What this fixation does not claim

Publishing a commit is not accepting it. `origin/dev` carries whatever the integrator has
merged, including work no checkpoint has certified. Only `origin/main` carries an accepted
state, and only the owner moves it.
