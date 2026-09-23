# W42-LOOK — every border to 3:1, and two defects a widened census can now see

**task_id:** `W42-LOOK` · **wave:** 42 (the fix wave) · **lane:** `gate-w42b`
**worktree:** `/root/w42look` · **branch:** `agent/w42-look`

Ruled by the owner 2026-09-23 — read `docs/program/OWNER_RULINGS_2026-09-17.md` §3.13 (`R-33`)
before you start.

## L1 — `R-33` / `D-81`: every border rises to 3:1

Measured, and reproduced twice by two different sessions:

| palette | tokens | measured | WCAG 1.4.11 requires |
|---|---|---|---|
| light | `--am-line` `#d9dde3` on `--am-paper` `#ffffff` | **1.36:1** | 3:1 |
| dark | `--am-line` `#27323f` on `--am-paper` `#151d28` | **1.30:1** | 3:1 |

This is not decoration: it is **the only boundary under every finding row** on the review
screen, under every project and run row on hover, and around the theme control.

**The owner ruled for the product-wide change, explicitly over the targeted one.** So:

- **You are not protecting the old look.** `W32-CONTRAST` §3 and `W33-THEME` each looked at this
  and declined because every rule in the product becomes a hard line. The owner has now chosen
  that. Make it look deliberate rather than minimal — a 3:1 border on every surface is a visual
  decision, and half-doing it will read as a bug.
- **Both palettes.** Dark is the one at 1.30:1 and it is the harder one to keep pleasant.
- **`--am-surface` carries four related rows in the register.** Read them: if the same scale
  decision resolves them, say so and resolve them; if it does not, say why in one line.

**The census must enforce the floor from here.** `web/tests/unit/styles/contrast.test.ts` was
widened last wave from 25 screens to 49 and from a literal component list to the derived
question *every colour-bearing rule must be reached*. Add the assertion that a border pair
reaching a screen meets 3:1, **and show it red against today's tokens before you change them** —
that ordering is the deliverable, because a guard written after the fix is a guard nobody has
seen fail.

## L2 — `D-84`: a typed refusal widened to `string`

`web/src/widgets/decision-panel/ui/decision-panel.tsx:41` declares
`readonly refusal?: string | null | undefined` and renders on `refusal === 'empty'`.

The feature feeding it is typed properly: `CommentRefusal` is exported from
`features/append-comment` and `useAppendComment` returns `CommentRefusal | null`. The widget
throws the type away at its own boundary and matches a magic literal.

**Today `CommentRefusal = 'empty'`, one member, so the screen is correct.** Add a second refusal
— an over-long comment, whitespace only — and the reviewer's comment is refused while **the
screen says nothing at all**. That is the silent fallback `AGENTS.md` §4 forbids by name, and
`tsc` cannot catch it because `string` accepts every new member.

**The correct pattern is eight files away**: `features/sign-in/ui/sign-in-form.tsx:23` declares
`SignInRefusal` and renders on presence. Repair is one word plus rendering the refusal instead
of testing it for a value.

**Prove it the way that matters:** add a second member to `CommentRefusal` in a scratch copy and
show that the widget **stops compiling**. That is the property, not the string.

## L3 — `D-85` and the census residue

Three dead things, reported by `W41-BLIND`: `.am-evidence__none` is unreachable on every input
(the active page is chosen from pages derived from the evidence itself), and `hr` and
`.am-app__context` are dead CSS.

**The row is not really about three items.** After last wave's repair the census still reports
**11 colour-bearing rules reaching no screen**, down from 31 — and a rule no screen reaches is
either a missing seed (the `D-69` defect) or a rule nobody needs. **From the census's side the
two are indistinguishable**, which is why the 11 must be **named individually** rather than
counted down. Name all eleven. Say which are which. Delete what is dead; seed what is missing.

## allowed_paths

```
web/src/**          EXCEPT web/src/shared/api/generated/**
web/tests/**
docs/program/W42-LOOK.md
```

## forbidden_hotspots

`web/src/shared/api/generated/**` and `web/openapi/**` and `web/FRONTEND_LOCK.json` — **`W42-SEAL`
is reselling the contract right now in `/root/w42seal` and those are its files** ·
`contracts/**` · `src/auditmanager/**` · `tests/**` (the Python tree) · `db/migrations/**` ·
`Makefile` · `package.json` · `package-lock.json` · `docs/program/DEBT_REGISTER.md` ·
`docs/program/dispatch/**` · any container not named `gate-w42b*`.

**One file of yours is being written by the other stream:** `web/src/shared/api/generated/`.
Expect it to change under you at merge. Nothing else of theirs touches `web/src`.

## Deliverables

1. The three pieces, each committed as you finish it.
2. `docs/program/W42-LOOK.md`, opened **before** the first measurement.
3. **Screenshots or rendered evidence of both palettes after L1.** A contrast ruling verified
   only by arithmetic is half verified — the number can be right and the screen ugly, and the
   owner chose this change to be seen.
4. Every guard shown to fail, with the mutation quoted. `D-84`'s proof is a **compile** failure,
   not a test failure; say so plainly and show the compiler's words.
5. Anything outside the grant: reported, not repaired.

## Verification

```
cd /root/w42look
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12
.venv/bin/python -c "import boto3"
npm --prefix web ci
npm --prefix web run typecheck          # in the gate since wave 37; fast, run it often
make gate > /root/w42b-gate.log 2>&1; echo "exit=$?"
grep -c 'GATE OK' /root/w42b-gate.log
```

Read the verdict from the **`GATE OK` line in the log**. Wave 41 closed at **2361 / 35 / 1022 in
72 files**; report yours with the commit each was taken at.

## Discipline

**Commit each step as you finish it.** Do not tag, do not push, do not merge.
