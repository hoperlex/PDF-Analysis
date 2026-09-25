# Wave 45's judges — one closing sub-stage A, two cross-judging before the final gate

**Everything runs on Sonnet this wave (`R-38`), and the structure does not relax — only the
model changes.** So every question below says **what to measure and how**, and the
falsifications are fixed in advance. A judge that skips one is visible in its own report.

**Why that matters here, measured rather than asserted:** wave 44's cross-judges found **five
false greens inside the integrator's own repairs** — a credential guard that still admitted a
fallback written on the next line, and a capability guard that caught one wording rather than
the claim. **A judge that finds nothing is indistinguishable from a judge with nothing to find**,
which is why these briefs name the probes instead of asking for an opinion.

**All judges repair nothing.** Each owns exactly one report file, reverts anything touched to
measure, and shows `git diff --name-only` proving its branch carries one file. **The owner's
stand `auditmanager-w19a` at `127.0.0.1:31500` is read-only to every judge.**

---

## `W45-JUDGE-A` — the close of sub-stage A, on both branches, before the merge

**worktree** `/root/w45j` · **branch** `agent/w45-judge` · **lane** `gate-w45j`
**report** `docs/program/reviews/W45-JUDGE-A.md`

Subjects: `agent/w45-pos` and `agent/w45-ready`, unmerged. Examine them with `git checkout` in
your own worktree. **Never enter another lane's directory.**

**A1 — `.dockerignore`, in the condition the defect appears in.** Build both images **from the
working tree** with the file and without it. Report the context size each way and whether the
image's `node_modules` is the lockfile's. **A build from a clean clone proves nothing here** —
that is the condition the defect cannot appear in, and it is the trap `D-80` is about.

**A2 — the prose guard, shown red and shown harmless.** Put a stale surface count into
`CURRENT_STATE.md` and require a red that names the file and the number. Then confirm the
guard leaves **wave reports** alone: `docs/program/W30-CERT3.md` names migration head `0005`
and is **correct**, because it records what was true at its wave. A guard that reddens on that
would force this programme to falsify its own history.

**A3 — the blocks operation, driven.** Call it. What does it answer for a version whose run has
produced the artifact, and for one that has not? **Absent and empty must not be the same
answer.** Check the contract description for the field that is always `[]`.

**A4 — the screen, against instruments that now reach it by themselves.** Put English prose on
it and a 1.08:1 border on a really-rendered element; both must redden and name the screen.
**Then check whether the stream edited `SEEDS`** — wave 44 made the screen set derived, so a
stream that had to add itself to a list is a finding.

**A5 — does every new guard bite?** Mutate them. Quote each mutation and its result.

---

## The close of the wave — `W45-JUDGE-X` and `W45-JUDGE-Y`, in parallel, **before** the final gate

This order is wave 43's correction and wave 44's proof: judging before the final testing means
the final testing measures what ships.

### `W45-JUDGE-X` — the instruments and the contract

**worktree** `/root/w45j` · **branch** `agent/w45-judge-x` · **lane** `gate-w45j`
**report** `docs/program/reviews/W45-JUDGE-X.md`

- Re-take `W45-JUDGE-A`'s probes on the **merged** tree, and take them against **the
  integrator's own changes**, which no grant covers — `D-94` makes them your subject by standing
  rule and the integrator will name them.
- **The reseal: four documents or three?** Check `openapi.json`, the generated client, the
  mirror and the sha in `FRONTEND_LOCK.json` all moved in **one** commit, and that the sha was
  recomputed rather than carried.
- Did the merge lose a test? **Do not check by counting** — a renamed test keeps the count.
  Byte-compare every stream file against the merged tree and do set algebra over test names.

### `W45-JUDGE-Y` — the product and the deploy

**worktree** `/root/w45k` · **branch** `agent/w45-judge-y` · **lane** `gate-w45k`
**report** `docs/program/reviews/W45-JUDGE-Y.md`

- **Drive the product in a browser.** Sixteen addresses, both palettes. The gate's frontend
  battery cannot see the journey or a width — recorded properties, not suspicions. The journey
  needs `E2E_PC01_LOGIN` and `E2E_PC01_PASSWORD`; migration `0006_app_user`'s docstring names
  the account.
- **Audit `W45-READY`'s rehearsal checklist by doing it**, on a throwaway instance of your own.
  A checklist nobody has followed is a draft.
- **Is any claim in either stream's report false?** Re-measure, do not re-read.

### Then: cross-examination

Each receives the other's report and answers two questions: **which of the other's findings can
I falsify, or strengthen with a measurement they did not take**, and **where does the other's
method share an assumption with its subject** (`OPERATING_CONSTRAINTS.md` §12)?

**A judge that only agrees has not cross-judged.** In wave 44 each strengthened the other's
findings with measurements the other had not taken, and one narrowed its own in the process.

---

## What a finding is

It names the file and line, states what is false or missing, gives **the command that reproduces
it**, and says what it would cost. **A finding without a reproduction is an opinion.**

**Say plainly where a stream did the right thing**, and especially where it reported a weakness
in its own work — an audit that only names faults teaches sessions to hide them, and this
programme's best measurements have come from streams that volunteered them.

**Report which questions you could not answer, and why.**
