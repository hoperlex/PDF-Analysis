# W43-JUDGE-A — the stage-A judge, on both branches, before the merge

**task_id:** `W43-JUDGE-A` · **wave:** 43, stage A · **lane:** `gate-w43j`
**worktree:** `/root/w43judge` · **branch:** `agent/w43-judge`

**You repair nothing.** You own one file: `docs/program/reviews/W43-JUDGE-A.md`. Everything else
you touch, you touch to measure it, and you put it back.

Your subjects are two branches the integrator has **not merged yet**:

| branch | worktree it was built in | brief |
|---|---|---|
| `agent/w43-compare` | `/root/w43comp` | `docs/program/dispatch/W43-COMPARE.md` |
| `agent/w43-prep` | `/root/w43prep` | `docs/program/dispatch/W43-PREP.md` |

Work in **your own worktree** `/root/w43judge` on **your own branch**. To examine a stream's work,
`git checkout` its branch **in your worktree** or read it with `git show` — **never enter another
lane's directory and never run anything in it.**

## Why this programme has judges, stated once

Every stream reports its own work, and a stream's report is written by the party with the
strongest reason for it to be true. This programme has seven consecutive waves in which a guard
was sound and blind, four register rows that named a path nobody opened, and — last wave — a
dispatch brief whose central premise was false and would have produced a green gate over an open
door. **None of those were caught by the session that made them.**

## The five questions, in the order they matter

### J1 — do the instruments reach the new screens, without being told to?

**This is the wave's real measurement and you are the only one who can take it honestly**, because
a stream that knows it is measured on coverage seeds its own screens.

Wave 41 made `web/tests/guards/rendered-language.guard.test.ts` derive its coverage from the
contract. Wave 42 widened `web/tests/unit/styles/contrast.test.ts` from 25 screens to 49 and gave
every border a 3:1 floor. **Five new screens are the first test of both on screens written after
the repair.**

Take it as a measurement, not an opinion:

- On each branch, **put an English word on a new screen** and see whether the language guard
  reddens. If it does not, the screen is outside the guard's reach and `D-69` is reopening.
- **Change a border on a new screen to a failing colour** and see whether the census reddens.
- Then look at **how** each screen came to be reached: automatically, or because the stream added
  it to a list. A screen reached because somebody remembered to add it is a screen the next
  author will forget.

Report the answer per screen, not per branch.

### J2 — are `W43-PREP`'s four data-shape notes true?

`W43-PREP`'s third deliverable is a written claim, per screen, about what it would show and which
contract fields exist. **Check every claim against `contracts/api/v1/openapi.json` and, for
blocks, against the corpus itself** (`.local/`, invisible to git; `corpus/MANIFEST.json` orients).

The brief told that stream four things it must verify rather than copy: the corpus's
`coords_norm` and `polygon_points`, the one visible analysis stage, the absence of a log-reading
operation among the 18, and `PROTOTYPE_PROFILE.md` §7's exclusion of workers. **Re-measure all
four yourself.** A note that is wrong is worse than no note, because the next wave budgets
against it.

### J3 — is any number on these screens invented?

`R-23`'s addendum: *no invented numbers; an empty screen is more honest than a plausible one.*
Drive the screens and look. A plausible zero is also an invented number if nothing computed it.

### J4 — does any stub promise something nobody decided to build?

`R-18` and `D-58`: a finished application does not explain its own transport, and a promise is a
claim about the programme. Workers are excluded by `PROTOTYPE_PROFILE.md` §7 — a screen promising
them is promising something that was ruled out.

### J5 — does each new guard bite?

Mutate every guard either stream added. **A guard added with a screen and never shown to fail is
the thing seven waves were spent learning about.** Quote the mutation and the result.

## What a finding looks like

A finding names the file and line, states what is false or missing, gives **the command that
shows it**, and says what it would cost. A finding without a reproduction is an opinion.

**Say plainly when a stream did the right thing**, and especially when it reported a weakness in
its own work. That is the behaviour this programme wants and an audit that only names faults
teaches sessions to hide them.

## allowed_paths

```
docs/program/reviews/W43-JUDGE-A.md
```

Anything else you edit is a measurement you must revert; your branch's diff against the base must
be **that one file**, and your report must show `git diff --name-only` proving it.

## Verification

Your lane is `gate-w43j` — PostgreSQL `127.0.0.1:56280`, S3 `59880`/`59881`; `.env` is written.
Provision with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, `.venv/bin/python -c
"import boto3"`, `npm --prefix web ci`. Never touch a container not named `gate-w43j*`.

Read every verdict from the log, never from a status a harness hands you.

## Return

Your findings, most severe first, each with its reproduction. Then, explicitly: **which of the
five questions you could not answer, and why** — an unanswerable question reported is worth more
than a confident guess, and this programme has a row (`D-79`) about the opposite.
