# Wave 44's judges — one closing sub-stage A, two judging across at the close

**The owner's instruction, 2026-09-24:** at least one judge at the close of each sub-stage, and
**cross-judging by two or more judges at the close of the wave, before the final testing.**

**All judges repair nothing.** Each owns exactly one report file. Anything touched to measure is
reverted, and each report shows `git diff --name-only` proving the branch carries one file.

**The owner's stand `auditmanager-w19a` at `127.0.0.1:31500` is read-only to every judge:** drive
it over HTTP and with a browser, never restart or reconfigure it.

---

## `W44-JUDGE-A` — the close of sub-stage A, on both branches, before the merge

**worktree** `/root/w44judge` · **branch** `agent/w44-judge` · **lane** `gate-w44j`
**report** `docs/program/reviews/W44-JUDGE-A.md`

Subjects: `agent/w44-journey` and `agent/w44-see`, unmerged. Examine them by `git checkout` in
your own worktree — never enter another lane's directory.

**A1 — the fixed probe, so two waves are comparable.** Wave 43's measurement, verbatim: English
prose on a screen, and a 1.08:1 border on a really-rendered element. **In wave 43 the whole suite
stayed green over four such screens.** If it stays green now, `D-88`'s repair is a description
and not a repair. Run it on **each** of the fourteen addresses, not a sample: the wave-43 result
was that four of five were invisible, so a sample can miss the survivors.

**A2 — does the derived set actually derive?** Add a screen to `web/src/app` that no list
mentions and see whether the instruments render it. That is the difference between a glob and a
longer literal.

**A3 — the journey, driven.** How many routes does the walk reach on that branch? Does a route it
cannot reach get **named by the walk** rather than by a reader? And does `D-16`'s cold browser
per route survive — is a session carried deliberately, or is state leaking between routes? Those
look the same in a passing run and are opposite properties.

**A4 — is the width assertion real?** Revert `flex-wrap: wrap` in `.am-app__bar` and require the
walk to name the route and the numbers.

**A5 — does every new guard bite?** Mutate them. A guard never shown to fail is what seven
consecutive waves were spent learning about.

---

## The close of the wave — `W44-JUDGE-X` and `W44-JUDGE-Y`, in parallel, **before** the final gate

This order is a correction of wave 43, where the closing judge ran after the gate and the tag,
found a product-wide regression, and cost the wave a second gate and a second tag. **Judging
before the final testing means the final testing measures what ships.**

Both run on the **merged tree**, which the integrator will name. They have different primary
angles so they do not duplicate — and then they cross-examine.

### `W44-JUDGE-X` — the instruments

**worktree** `/root/w44judge` · **branch** `agent/w44-judge-x` · **lane** `gate-w44j`
**report** `docs/program/reviews/W44-JUDGE-X.md`

- Take `W44-JUDGE-A`'s probes again on the **merged** tree: a finding repaired in one branch can
  be reintroduced by the other.
- **Then stop certifying the closed blind spot and look for the next one.** Every instrument in
  this programme derives its subject from something. Name what each one's subject is derived
  from, and find the one that is still a literal. `D-88` was found that way and so was `D-69`.
- Did the merge lose a test? **Do not check by counting** — a renamed or replaced test keeps the
  count. `W43-JUDGE-B` checked by byte-comparing every stream file and by set algebra over test
  names, and that is the standard now.

### `W44-JUDGE-Y` — the product and the integrator

**worktree** `/root/w44judge2` · **branch** `agent/w44-judge-y` · **lane** `gate-w44k`
**report** `docs/program/reviews/W44-JUDGE-Y.md`

- **Drive the deployed stand in a browser.** Fourteen addresses, both palettes. `make gate`'s
  frontend battery cannot see the journey or a width — recorded properties, not suspicions.
- **Audit the integrator's own executable changes**, which the integrator will name. `D-94` is
  the standing rule: they are the only changes no grant covers, and in wave 43 both of them were
  asserted by nothing.
- Is any claim in either stream's report false? Re-measure, do not re-read.

### Then: cross-examination

When both have reported, each receives the other's report and answers two questions:

1. **Which of the other's findings can I falsify, or strengthen with a measurement they did not
   take?**
2. **Where does the other's method share an assumption with its subject** (`OPERATING_CONSTRAINTS.md`
   §12)? A judge whose instrument agrees with the thing it measures has not measured it.

**A judge that only agrees has not cross-judged.** `W43-JUDGE-B` caught its own near-miss that
way — a scripted theme switch left a CSS shorthand stale and produced a false contrast violation,
and the tell was that the browser's number disagreed with the arithmetic. **That is the standard
of self-scrutiny expected here, applied to somebody else's work.**

---

## What a finding is

A finding names the file and line, states what is false or missing, gives **the command that
reproduces it**, and says what it would cost. A finding without a reproduction is an opinion.

**Say plainly where a stream did the right thing**, and especially where it reported a weakness
in its own work rather than tidying it away. An audit that only names faults teaches sessions to
hide them, and this programme's best measurements have come from streams that volunteered them.

**Report which questions you could not answer, and why.** An unanswerable question reported is
worth more than a confident guess.
