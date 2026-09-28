# W46-JUDGE-Z — sub-stage C closed, on the merged tree, before the final gate

**worktree** `/root/w46j` · **branch** `agent/w46-judge-z` · **lane** `gate-w46j`
(PostgreSQL `56390`, S3 `59990/59991`, API `56391`, Next `56393`)
**report** `docs/program/reviews/W46-JUDGE-Z.md`

Written 2026-09-29 by the integrator. The subject is the tip that merges `W46-GUARD` and
`W46-CLIENT` (the integrator names it in the dispatch). The cross-judging this wave owes has
happened: X and Y, each ruling on the other (`docs/program/reviews/W46-JUDGE-X.md`,
`W46-JUDGE-Y.md`, final sections). **You close sub-stage C alone.** You repair nothing, you own
one file, and you revert every probe.

## Z1 — the gate, literally

Run `make gate > /root/w46z-gate.log 2>&1` and take the verdict from the `GATE OK` line. Account
for every count difference against X's `d5c9be5` numbers (battery 2504, frontend 1118 in 79) by
test id, not by arithmetic. Check `free -g` first. **Exit 137 is the OOM killer, not a result.**

## Z2 — both judges' reproductions, re-taken against the repair

For every finding sub-stage C claims to repair (see `docs/program/dispatch/W46-STAGE-C.md`), run
the **judge's own reproduction**, not the stream's. Each one must now fail where it passed:

- X-1, with both X's `spend` mutation and Y's `comment` 4000 → 400;
- X-2 / Y's "everything counts as KM" and the run-state counts;
- X-3 / Y5-a through the **full stack**, as Y did: a mutated server sends an omitted row and an
  unknown `escalated` value, and the screen must show a fault and no numbers;
- Y5 M5 / M6;
- X-4, with the code-fence mutation and with Y's plain-heading mutation;
- X-6 / Y6-a, the 30-second staleness after creating a project;
- X-7, both the cookie and a correlation-id header name in different case;
- Y2-a, whether every sentence about the analysed section is now true against a stored `KM`
  document with a published run;
- X-11, whether the contract's description of an absent `spend` is present, and whether the
  generated types kept their shape.

A repair that the stream's own mutation fails but a judge's mutation passes is **not a repair.**

## Z3 — did the stage break what the wave had?

The live journey (`npm --prefix web run e2e:pc01 -- --origin <your Next> --phase all`), `/dashboard`
at 780 px in both palettes with data, and one reseal check: recompute the lock's digests yourself
and run `api:verify`.

## Z4 — off the trail

Go to at least three places this brief does not point at, and give each one a row: where, why the
trail does not lead there, and what came back. A place that returned nothing still gets its row.

## What a finding is

It names the file and line, states what is false, and gives the command that reproduces it.
**A finding without a reproduction is an opinion.** Say plainly where a stream did the right
thing, and say which questions you could not answer.

## Discipline

Open the report before the first measurement and commit after each section. **Kill only by PID,
and only processes confirmed to be your own descendants.** The owner's stand at `:31500` is
read-only. Touch no container except `gate-w46j*`. Stop your API and Next by PID when you finish.
Do not tag, push or merge.
