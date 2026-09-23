# W42-LOOK — every border to 3:1, and two defects a widened census can now see

**task_id:** `W42-LOOK` · **wave:** 42 · **lane:** `gate-w42b` · **branch:** `agent/w42-look`
**base:** `b0a329b` · **opened:** 2026-09-23, **before the first measurement**

This file is opened first and written as the work happens, so the ordering it claims is the
ordering it was written in. Three pieces:

- **L1** — `R-33` / `D-81`: every border rises to 3:1 in both palettes, with the census
  assertion **written and shown red against today's tokens before the tokens move**.
- **L2** — `D-84`: the decision panel's typed refusal, widened to `string` at the widget
  boundary and matched against a magic literal.
- **L3** — `D-85` and the census residue: the eleven colour-bearing rules no rendered screen
  reaches, named individually and each one classified as dead or unseeded.

## 0. Premises in the brief, checked before anything was built on them

`OPERATING_CONSTRAINTS.md` §12 and the previous wave's two false brief premises are why this
section exists. Every premise below was read in the tree at `b0a329b`.

| premise | verdict |
|---|---|
| `decision-panel.tsx:41` declares `readonly refusal?: string \| null \| undefined` | **true**, line 41 exactly |
| the widget renders on `refusal === 'empty'` | **true**, line 118 |
| `CommentRefusal` is exported from `features/append-comment` | **true**, `index.ts:3`, declared `comment-text.ts:15` as `'empty'`, one member |
| `useAppendComment` returns `CommentRefusal \| null` | **true**, `use-append-comment.ts:47` |
| `sign-in-form.tsx:23` declares `SignInRefusal` and renders on presence | **true**, line 23; the presence test is line 71 and the message is `signInRefusalMessage` |
| `--am-line` `#d9dde3` on `--am-paper` `#ffffff` light; `#27323f` on `#151d28` dark | **true**, `globals.css` token blocks |
| the census reports 11 colour-bearing rules reaching no screen | **true**, `UNREACHED_BY_ANY_SCREEN` in `contrast.test.ts` carries exactly 11 entries |
| `--am-surface` carries four related rows in the register | **true**, `-`, `hover`, `focus-visible`, `active`; `--am-paper` carries four more |

No premise in the brief was found false. Anything discovered beyond them is recorded in the
section it belongs to.
