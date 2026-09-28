# Wave 47's judges: one closing sub-stage A, two cross-judging from different entry points

Written 2026-09-29 by the integrator. **Every judge repairs nothing, owns exactly one report
file, reverts every probe, and ends with `git diff --name-only <tip>..HEAD` showing that one
file.** The owner's stand at `127.0.0.1:31500` and its `infra/deploy/env/*.env` files are
read-only. **Kill only by PID, and only your own descendants. Run one full gate on the host at
a time. Exit 137 is the OOM killer, not a result** (`W47-DISPATCH.md`).

**This wave is about who can get in.** A wrong green here is worse than in any wave before it: a
password policy that admits what it claims to refuse, a forced change the client can skip, or a
session register that leaks the token would each be read as *safe to publish.* **So every judge
attacks, and none of them confirms.**

---

## `W47-JUDGE-A` — sub-stage A's close, on both branches, before the merge

**worktree** `/root/w47j` · **branch** `agent/w47-judge` · **lane** `gate-w47j`
**report** `docs/program/reviews/W47-JUDGE-A.md`

The subjects are `agent/w47-gate` and `agent/w47-pass`, unmerged. Check each one out in your
own worktree.

- **A1 — the policy, attacked.** Try a password of 7 characters, the login, the login in another
  case, the product name inside a longer string, and the current password at the forced change.
  Try Unicode that normalises to one of those, surrounding whitespace, and 8 characters of which
  some are combining marks. **Each attempt is either refused or named in the report as
  admitted.** Admitted cases are findings unless `R-48` or `D-101` names them.
- **A2 — the forced change, bypassed.** With the seeded account on its default password, reach any
  screen other than the change screen. Reach any API operation other than the ones the change
  needs: through the BFF, directly against the API with the token, and by calling the operation
  a screen would call. **If `W47-PASS` stopped and reported instead of building, judge the
  options it named and their stated cost.**
- **A3 — the session register, from the browser's side.** Restart the web process and check the
  session survives. Then look for the token everywhere the browser can reach: cookies, responses,
  HTML, JS bundles, `localStorage`, and any file the web process can serve. Revoke the credential
  (`token_epoch`) and check the next request fails **at once**, not at the next restart.
- **A4 — the readiness command, fed configurations built to fail.** Use every check it claims,
  plus one it does not: HTTP left open behind TLS. Then the `D-103` reproduction exactly as the
  brief states it.
- **A5 — every new guard, mutated by you**, not by the stream.

## `W47-JUDGE-X` and `W47-JUDGE-Y` — the close of the wave, in parallel, before the final gate

The same rules. **Different entry points on purpose:** two judges who start from the same commit
trail check the same places.

### X starts from the attacker

**worktree** `/root/w47j` · **branch** `agent/w47-judge-x` · **lane** `gate-w47j`
**report** `docs/program/reviews/W47-JUDGE-X.md`

Begin with **no knowledge of the diff.** On the merged tree, bring up the stack and treat it as a
system you are trying to get into with the seeded account's default password. Read the commits
only after you have tried. **Then** run `make gate` literally and account for the counts against
`W47-DISPATCH.md`'s baseline by test id.

### Y starts from the operator

**worktree** `/root/w47k` · **branch** `agent/w47-judge-y` · **lane** `gate-w47k`
**report** `docs/program/reviews/W47-JUDGE-Y.md`

Begin with **the integrator's runbook** (`docs/program/DEPLOYMENT_RUNBOOK.md`), as the owner would
on the day. Follow it on a throwaway instance of your own and time each step. Where the runbook
and the tree disagree, the runbook is the finding. Then check that every value the runbook says
the owner must supply is really asked for, and that nothing else is.

### Then: cross-examination

Each judge gets the other's report. For every finding, answer **upheld**, **narrowed** or
**falsified**, each with a measurement the other did not take. Then answer where the other's
method shares an assumption with its subject (`OPERATING_CONSTRAINTS.md` §12).

## What a finding is

It names the file and line, states what is false, and gives the command that reproduces it.
**A finding without a reproduction is an opinion.** Say where a stream did the right thing, and
say which questions you could not answer.
