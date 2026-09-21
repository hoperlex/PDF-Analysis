# Branch inventory, 2026-09-21

Determined by the integrator at `9b8c77a`, by asking git rather than by reading names.
Every claim here has the command that produced it.

## The policy, as it is actually applied

| ref | role |
|---|---|
| `origin/main` | what has been **gated and certified**. Fast-forward only, tagged at each advance: `alpha-w18`, `alpha-w25`. |
| `origin/dev` | the working tip. Every wave merges here, is gated here, and is pushed here **before** any dependent session is dispatched. |
| `planning/prototype-roadmap` | the integrator's local branch, pushed to both of the above. **It carries nothing they do not** — `git merge-base --is-ancestor` confirms containment in `dev` in both directions today. |

`origin/integration/W0.3` was **retired on 2026-09-21**: merged into `dev` and last touched
2026-09-01.

## Abandoned, and what that means for each

**23 `worktree-agent-<hex>` branches, all dated 2026-09-01 — deleted.** Harness artefacts
from a tooling that names a branch per worktree. Every one was an ancestor of `origin/dev`,
checked individually before deletion, so nothing was lost.

**`agent/w20-code` — superseded, kept.** It built `R-8`, proved it over a socket, and was
reverted by `R-11` when a catalog code turned out to also be a frontend reseal. `W25-SEAL`
reinstated it under `R-13`, and the substance is now on `dev`: both trees declare **22 codes
and the symmetric difference of the two sets is empty**. Its review was landed separately on
`dev` because `R-11` and `D-18` both cite it and **both pointers dangled**.

Kept rather than deleted because it is the only place the *reverted* state exists, and two
rulings narrate it.

**`prep/W1` — abandoned in fact, kept.** Eight commits, sixteen files, all under
`docs/program/tasks/`, last touched **2026-09-04**. They are `W1-*` task files for a wave
numbering the programme passed long ago — it is at wave 26. Never merged, and nothing since
has depended on it.

**Not deleted**, because unlike the harness branches its content exists nowhere else, and
deciding that seventeen-day-old planning is worthless is the owner's call rather than a
tidy-up. Its worktree is `/root/projects/PDF-Analysis-W1prep`.

## The `agent/w*` branches of merged waves

Roughly a hundred, all ancestors of `origin/dev`. **Kept deliberately.** Each is the tip a
review cites, and several reviews name a commit on their own branch as evidence — `W20-CODE`
is the case that proves the point, since `R-11` reverted its code and its branch is now the
only record of what was reverted.

Check: `git branch --format='%(refname:short)' | while read b; do git merge-base --is-ancestor "$b" origin/dev && echo "merged $b"; done`

## Worktrees are not branches, and sixteen of them were removed — 2026-09-21

A *branch* is a name and a commit; a *worktree* is a full checkout with its own `node_modules`
and `.venv`. This host was carrying **eighteen** worktrees and **13 GB** of them, for waves
merged as long ago as wave 3. Disk reached 100% twice in this programme, and each time it cost
a rebuild rather than a measurement.

Removed: `w22e2e`, `w22ops`, `w22web`, `w23deploy`, `w23partial`, `w24cert2`, `w24idem`,
`w28live`, `w29retry`, `w29say`, `w3`, `w5adv`, `w5cert`, `w6cert`, `b3conv`, `w20code`.
Kept: the integrator's own tree, and `PDF-Analysis-W1prep` for the reason §3 records.

**Every branch survived.** `git worktree remove` removes the checkout, not the ref, so the
inventory above is unchanged and every review's cited commit is still reachable. This was
checked before removing rather than assumed: each branch was tested individually with
`git merge-base --is-ancestor "$b" HEAD`, and `w3`'s **detached** head — the one case where a
worktree can hold commits no branch names — was tested the same way and found to be an
ancestor.

**One did not pass that test and was still removed, deliberately.** `agent/w20-code` is nine
commits ahead of `HEAD`: it is `R-11`'s reverted work, and §4 above is the reason it is kept.
Its *worktree* holds nothing its *branch* does not, so the checkout went and the ref stayed.

Check: `git worktree list` — **two permanent entries** (the integrator's tree and `W1prep`)
plus one per live session of the current wave; at the time of writing, wave 30's `w30cert3`
and `w30lists`, which go the same way when the wave merges. `git branch --list 'agent/*' |
wc -l` → **119**, and that figure does not move when a worktree is removed, which is the
whole point of this section.

**Removing a wave's worktrees is now part of closing it**, alongside the merge, the gate and
the push. Leaving them is how eighteen accumulated.
