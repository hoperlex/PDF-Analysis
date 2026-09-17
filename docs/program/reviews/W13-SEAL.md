# W13-SEAL — the contract reseal

Session `W13-SEAL`, wave 13 stage 0b. Branch `agent/w13-seal`, worktree `/root/w13seal`.

- **HEAD on arrival:** `876e095c81bb49948a894aa69e3298df020d2f86` — see §0, which records why
  this is not the commit the brief named.
- **Instance:** `gate-w13b`, PostgreSQL `55700`, S3 `59300`/`59301`, database `audit_w13b`,
  bucket `auditmanager-gate-w13b`.
- **Started:** 2026-09-18T00:14:48+05:00.

## 0. The base commit, and why it is not `origin/dev`

The brief says `git worktree add /root/w13seal -b agent/w13-seal origin/dev`. I did that and
landed on `7399d65`, where `tests/characterization/` holds a `README.md` and nothing else:
**the response baseline this brief requires me to update is not on `dev`.** `W13-BASE`'s merge
`876e095` has never been pushed; it exists only on the local branch `agent/w13-pin`.

`git merge-base --is-ancestor 876e095 origin/dev` → false.
`git merge-base --is-ancestor origin/dev 876e095` → true.

So `876e095` is `dev` plus the baseline, and it is the tree the brief's own gate expectation
describes: 1543 / 5 / 167 is `W13-BASE`'s recorded figure, the 1505 of `dev` plus that
session's 38. I reset the worktree to `876e095` and worked there. I did **not** take
`agent/w13-pin`'s tip `b12c4d0` (`feat(pins)`), which is stage 0a's in-flight work and not
mine to carry.

*(sections follow as the work lands)*
