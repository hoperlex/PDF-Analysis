# W43-JUDGE-B — the stage-B judge, on the merged and gated tree

**task_id:** `W43-JUDGE-B` · **wave:** 43, stage B · **lane:** `gate-w43j`
**worktree:** `/root/w43judge` · **branch:** `agent/w43-judge-b`

**You repair nothing.** You own `docs/program/reviews/W43-JUDGE-B.md` and nothing else.

Your subject is the tree **after** the integrator merged both stage-A branches and after
`make gate` reported `GATE OK` on it. The integrator will give you the commit and the gate log.

## Your subject is what a merge and a green gate cannot tell you

A green gate says every test that ran, passed. It does not say which tests ran.

### K1 — did the merge lose anything?

Two branches editing `web/src` and `web/tests` can drop a file, a test, or half of a test list
without a conflict and without a red. `alpha-w42` closed at **1032 frontend tests in 72 files**
and battery **2442**. The merged tree must carry that **plus** what each stream added — and each
stream's report states its own numbers with the commit they were taken at.

**Check the arithmetic and check the file list.** A count that matches by coincidence is not a
match; name what is present.

### K2 — does the browser journey still pass?

**`make gate`'s frontend battery cannot see the journey.** That is a recorded property of this
programme, not a suspicion: `npm test` has been green while the browser journey was broken, and
only the make target catches it. Five new addresses is exactly the change that breaks navigation.

Drive it. Say what you drove and how.

### K3 — are the five new addresses real on the deployed stand?

The stand is `auditmanager-w19a` at `127.0.0.1:31500`, in `recorded` mode since `R-30`. The
integrator will redeploy before you start; confirm with `infra/deploy/verify-deployed.sh` that
the deployed stack **is** the tree you are judging, and then drive the addresses.

For each: does it answer, does it render in Russian, and do its borders meet the 3:1 floor
`R-33` ruled? **A screen that passes in the test harness and 404s on the stand is the defect this
question exists for.**

### K4 — do `W43-JUDGE-A`'s findings still hold?

Read `docs/program/reviews/W43-JUDGE-A.md`. A finding repaired in one branch can be reintroduced
by the other, and a finding both streams thought the other would handle is still open. **Say,
per finding, whether it survived the merge.**

### K5 — the one nobody assigned you

Having seen the whole wave, say what you would look at next and why. `D-69`, `D-77`, `D-79`,
`D-80`, `D-84` and `D-87` all entered this register because somebody looked past their task.

## allowed_paths

```
docs/program/reviews/W43-JUDGE-B.md
```

Your branch's diff against its base must be that one file, and your report must show
`git diff --name-only` proving it.

## Verification

Lane `gate-w43j` (`56280`, `59880`/`59881`). Read every verdict from a log, never from a status a
harness returns. **Do not run `make gate` for its own sake** — the integrator has already run it
on this tree and the log is yours to read; §12 is about queries that share an assumption with
their subject, and re-running the same command is not an independent check. If you want an
independent one, drive the product.

## Return

Findings, most severe first, each with a reproduction. Then which questions you could not answer
and why.
