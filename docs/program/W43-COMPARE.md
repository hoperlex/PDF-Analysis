# W43-COMPARE — the stage-comparison skeleton

**task_id:** `W43-COMPARE` · **wave:** 43, stage A · **lane:** `gate-w43a` ·
**worktree:** `/root/w43comp` · **branch:** `agent/w43-compare` · **base:** `b7d9bc4`

This file is opened **before the first measurement**, per the brief's second deliverable, and
filled as the work proceeds. Everything below that carries a figure carries the commit it was
taken at, because a figure without its tree is not a measurement
(`OPERATING_CONSTRAINTS.md` §4.62, `MEMORY.md` "record measured figures with their method").

## 1. What this screen is

`R-23`: *«Сравнение стадий — очень важно; хотя бы скелет с заглушками сейчас, реализация по ходу
альфы.»* The screen puts **two runs of one published version side by side**, on the facts the
contract already carries, and says plainly which comparison is not here yet.

Address: `/projects/{project_uid}/versions/{version_uid}/comparison`.

## 2. Premises in the brief, checked before use

*(filled in section 6 — every one was verified against `contracts/api/v1/openapi.json` at
`b7d9bc4` before a line of the screen was written.)*

## 3. What the screen may say, and what it may not

`C2`: the screen may tell a reviewer that a deeper stage-by-stage comparison arrives later. It
may **not** explain this programme's transport to a reviewer (`R-18`; `D-58` was closed by
deleting exactly that). Sentences about operations, fields and schemas belong in code comments
and in this file.

`C1`'s addendum: **no invented numbers.** Where the contract carries the figure the screen prints
it; where it does not, the screen prints nothing and says why in a reviewer's words.

## 4. Instrument reach — reported honestly

*(filled once measured. This is the brief's fourth deliverable and the wave's own measurement:
which of the two instruments — the rendered-language guard and the contrast census — reached this
screen **without being told to**, and which had to be pointed at it.)*

## 5. Guards added, each shown to fail

*(filled with the mutation quoted, red, revert, green.)*

## 6. Measurements

*(filled with the commit each was taken at.)*

## 7. Outside the grant

*(filled: reported, not repaired.)*
