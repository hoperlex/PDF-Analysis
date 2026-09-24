# W43-COMPARE — the stage-comparison skeleton

**task_id:** `W43-COMPARE` · **wave:** 43, stage A · **lane:** `gate-w43a`
**worktree:** `/root/w43comp` · **branch:** `agent/w43-compare`

`R-23`: *«Сравнение стадий — очень важно; хотя бы скелет с заглушками сейчас, реализация по ходу
альфы.»* Read `docs/program/dispatch/W43-PLAN.md` first — it says what the judge will ask you.

## C1 — the screen

Legacy compares what two runs of the same document produced, stage by stage. **We have one
analysis stage that a reviewer sees (`text_analysis`) and four scheduled in `PC01_STAGE_IDS`**,
so a real comparison has little to compare today. That is precisely why the owner asked for a
skeleton.

**Build the navigation and the shape, not a mechanism.** An address, a place in the frame, a
screen that says what it will do, and — where the contract already carries the data — **real
numbers rather than stubs.**

**What the contract already gives you, and you must check each one yourself before using it:**
`listRuns` over a version, `getRunStatus` with its stages, `published_finding_count`,
`diagnostic_observation_count`, `cost_micros`, `model_call_count`, `state`, `terminal_reason`,
and since wave 42 **`terminal_detail`**. Two runs of one version can therefore be put side by
side for real on several of those.

**Where you must not invent:** anything the contract does not carry. `R-23`'s addendum is
explicit — *no invented numbers; an empty screen is more honest than a plausible one.*

## C2 — say what is missing and why, without explaining the transport

The screen is allowed to say that deeper comparison arrives later. It is **not** allowed to
explain our transport to a reviewer (`R-18`, and `D-58` closed by deletion for exactly that).
The difference is the audience: *"полное сравнение этапов появится позже"* is for a reviewer;
*"операция listRuns не отдаёт X"* is for you, and belongs in a comment.

## C3 — the stage vocabulary is already translated, and must stay so

`web/src/shared/ui/stage-label.ts` carries `STAGE_LABELS`, and
`web/tests/guards/stage-vocabulary.guard.test.ts` and `rendered-language.guard.test.ts` will both
have opinions. **Wave 41 made the language guard's coverage a contract-derived assertion.** If
your screen introduces a state the matrix does not seed, the honest move is to seed it — and to
say in your report that you had to, because that is the measurement this wave is.

## allowed_paths

```
web/src/_pages/stage-comparison/**      (new)
web/src/widgets/stage-comparison/**     (new)
web/src/app/projects/[project_uid]/versions/[version_uid]/comparison/**   (new)
web/src/entities/audit-run/**
web/src/shared/ui/**
web/tests/**
docs/program/W43-COMPARE.md
```

## forbidden_hotspots

`web/src/_app/app-frame.tsx` — **`W43-PREP` owns the frame this wave**; if you need a link in it,
say so in your report and the integrator adds it · `contracts/**` · `src/auditmanager/**` ·
`db/**` · `infra/**` · `web/FRONTEND_LOCK.json` · `web/src/shared/api/generated/**` ·
`docs/program/DEBT_REGISTER.md` · `docs/program/dispatch/**` · `Makefile` · any container not
named `gate-w43a*`.

## Deliverables

1. The screen, committed step by step.
2. `docs/program/W43-COMPARE.md`, opened **before** the first measurement.
3. **Every guard you add shown to fail** — mutate, red, revert, green, with the mutation quoted.
4. A plain statement of **which of the two instruments reached your screen without being told to**
   (the language guard, the contrast census) and which had to be pointed at it. The judge will
   check this independently; a stream that reports it honestly and a stream that does not are
   distinguishable, and the second is the expensive kind.
5. Anything outside the grant: reported, not repaired.

## Verification

```
cd /root/w43comp
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12
.venv/bin/python -c "import boto3"
npm --prefix web ci
npm --prefix web run typecheck
npm --prefix web run test -- --run          # the WHOLE suite, not the tests you were thinking of
make gate > /root/w43a-gate.log 2>&1; echo "exit=$?"
grep -c 'GATE OK' /root/w43a-gate.log
```

`alpha-w42` closed at battery **2442**, foundation **35**, frontend **1032 in 72 files**. Report
yours with the commit each was taken at, read from the `GATE OK` line.

## Discipline

Commit each step. Do not tag, push or merge. A judge runs on your branch before it is merged —
**its findings are the point of this wave, not a hazard to you.**
