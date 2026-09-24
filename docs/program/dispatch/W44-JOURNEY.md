# W44-JOURNEY — make the browser journey run again, then make it see width

**task_id:** `W44-JOURNEY` · **wave:** 44, sub-stage A · **lane:** `gate-w44a`
**worktree:** `/root/w44jrn` · **branch:** `agent/w44-journey`

Read `docs/program/dispatch/W44-PLAN.md` first. `D-92`, `D-83` and `D-93` are your subject and
all three are in `docs/program/DEBT_REGISTER.md` with their measurements.

## J1 — `D-92`: the journey stops at route 2 of 15, and has since wave 34

```
npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31500 --phase all
→ RED create-project: POST /bff/v1/projects → 401 authentication_required
→ routes checked: 2/15
```

**Three facts make it structural, each deliberate and each in the tree.** Verify all three before
you build on them:

- the BFF answers `401` without a session cookie — wave 34, by design;
- `tests/e2e/pc01/journey/cdp.mjs` gives **every route a fresh browser with an empty profile** —
  `D-16`, **by design, and that property is load-bearing: do not remove it**;
- the manifest has no sign-in step and `write.mjs` knows three verbs — `fill`, `click`,
  `attach_file`.

**The journey is written for an application without authorization, and this one has had
authorization for nine waves.**

**The repair is a design decision and it is yours to take and to argue.** Two shapes were named
when the row was written — a `sign_in` verb in the write half with a way to carry one session
through the walk, or an explicit `--session`. **Neither is prescribed.** What is required:

- **`D-16`'s cold browser per route survives.** It exists because a route that only works after
  the previous one is a route nobody can open from a link, and that is the defect `D-16` was.
  A session carried deliberately is not the same thing as state leaking between routes — **say in
  your report which one you built and how a reader can tell.**
- **The credential never lands in the repository.** The stand seeds an account in migration
  `0006_app_user`; the journey must obtain a session the way a reviewer does, not by carrying a
  secret in a file.
- **A run that cannot sign in must fail loudly**, naming that as the reason. A journey that
  silently walks fewer routes is how this defect survived nine waves.

## J2 — `D-83`: eleven of fifteen sentences are verified by nothing

Once the walk runs, the manifest's `expects_rendered` claims can be driven. `D-61`'s repair made
the static half honest; **eleven sentences live in branches selected by `useState` and a settled
`useMutation`, which no static pass reaches.** A browser reaches them.

Say, per sentence, whether it is now verified in the gate, verified only against a live stand, or
still verified by nothing. **Three honest categories beat one optimistic one.**

## J3 — `D-93`: 1085 frontend tests and not one can express a width

Wave 43 put a horizontal scrollbar on every screen in the product below **839 px** and nothing in
`make gate` could see it, because the frontend battery renders through `renderToStaticMarkup` —
no layout, no box, no viewport. It was found by a judge driving a browser.

`W43-JUDGE-B` proposed the cheap structural answer and it is yours to build: **one assertion in
the journey — `scrollWidth <= innerWidth` at a declared width, on every route.** Then the next
added link reddens by itself.

**Show it failing.** Revert `flex-wrap: wrap` in `.am-app__bar` in a scratch copy, drive the
walk, and quote the route it names and the numbers it reports. A width assertion that has never
been seen red is a width assertion nobody can trust.

## allowed_paths

```
tests/e2e/**
package.json / web/package.json    — ONLY if a script entry is genuinely required; argue it
docs/program/W44-JOURNEY.md
```

## forbidden_hotspots

`web/tests/**` and `web/src/**` — **`W44-SEE` owns both**, live in `/root/w44see` ·
`contracts/**` · `src/auditmanager/**` · `db/**` · `infra/**` · `web/FRONTEND_LOCK.json` ·
`docs/program/DEBT_REGISTER.md` · `docs/program/dispatch/**` · `Makefile` · any container not
named `gate-w44a*` · **the owner's stand `auditmanager-w19a` is read-only to you: drive it over
HTTP, never restart or reconfigure it.**

## Deliverables

1. The three repairs, committed step by step.
2. `docs/program/W44-JOURNEY.md`, opened **before** the first measurement.
3. **The walk's own output, quoted**: how many routes it reaches before and after.
4. Every new assertion **shown failing**, with the mutation and the numbers.
5. Anything outside the grant: reported, not repaired.

## Verification

Lane `gate-w44a` — PostgreSQL `127.0.0.1:56290`, S3 `59890`/`59891`. Provision with
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, `.venv/bin/python -c "import boto3"`,
`npm --prefix web ci`. `make gate > /root/w44a-gate.log 2>&1`, then read the verdict from the
**`GATE OK` line in the log** — never from a status a harness hands you. Wave 43 closed at
battery **2442**, foundation **35**, frontend **1085 in 75 files**.

**A harness has reported `exit code 0` over a failed gate three times in three days on this
programme.** Read the log.

## Discipline

Commit each step. Do not tag, push or merge. A judge runs on your branch before it is merged and
two more judge the merged tree before the final gate.
