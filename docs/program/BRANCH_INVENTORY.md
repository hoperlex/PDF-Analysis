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
