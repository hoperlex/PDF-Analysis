# Wave 44 — the instruments, in sub-stages, with a judge closing each and two judging across at the end

**Ruled by the owner 2026-09-24:** parallel orchestration; **at least one judge at the close of
each sub-stage**; and **cross-judging by two or more judges at the close of the wave, before the
final testing.**

That last clause changes the order, and it is a correction of wave 43. There the stage-B judge
ran **after** the gate and the tag, drove the stand, and found that the wave had put a horizontal
scrollbar on every screen in the product. The repair then needed a second gate and a second tag.
**Judging before the final testing means the final testing measures the thing that ships.**

## The subject: every open row is the same sentence

Twelve rows are open and most of them say one thing in different words — **the instruments of
this programme cannot see what a reviewer sees.**

| row | what cannot be seen |
|---|---|
| `D-92` | the browser journey has not run since wave 34; it stops at route 2 of 15 |
| `D-88` | the screen list is a literal, so a new screen is invisible to the language guard and the contrast census |
| `D-93` | 1085 frontend tests and not one can express a width |
| `D-82` | three English strings live in branches no instrument renders |
| `D-95` | a guard that fails on Latin words is blind to Cyrillic that is merely wrong |
| `D-83` | eleven journey sentences are verified by nothing inside the gate |
| `D-90`, `D-94` | live conditions and the integrator's own changes, asserted by nothing |

**`D-92` is the keystone.** `D-93`'s repair and `D-83`'s both live in the journey, and the journey
does not run. So one stream restores it and the other repairs what can be repaired without it.

## Sub-stage A — two streams, in parallel

| stream | lane | subject |
|---|---|---|
| `W44-JOURNEY` | `gate-w44a` | `D-92`, then `D-83` and `D-93`'s layout assertion, which become possible once it runs |
| `W44-SEE` | `gate-w44b` | `D-88` (derive the screen set from the route tree), then `D-82`, `D-95`, `D-90`, `D-94` |

The boundary: **`W44-JOURNEY` owns `tests/e2e/**`; `W44-SEE` owns `web/tests/**` and the
`web/src` repairs its newly-sighted instruments require.** Neither touches `contracts/**`,
`src/auditmanager/**`, `db/**` or `infra/**`. **This wave changes no contract.**

## Sub-stage A's judge — `W44-JUDGE-A`, on both branches, before the merge

**The measurement is fixed in advance and it is the same probe wave 43 used**, so the two waves
are comparable: put English prose on a screen and a failing border colour on it, and require that
the repaired instruments **now redden**. In wave 43 the whole suite stayed green over four such
screens. If it stays green again, `D-88`'s repair is a description rather than a repair.

Same for the journey: a route the walk cannot reach must be named by the walk, not by a reader.

## Sub-stage B — integration

The integrator merges both branches and makes whatever changes belong to nobody. **Those changes
are named, in the cross-judges' briefs, as their subject** — `D-94`'s standing rule, earned in
wave 43 when the integration commit turned out to be the only commit no judge was planned
against.

## The close of the wave — two judges across, **before** the final testing

`W44-JUDGE-X` (`gate-w44j`) and `W44-JUDGE-Y` (`gate-w44k`) run **in parallel on the merged
tree**, with different primary angles so they do not duplicate:

- **X — the instruments.** Do the repaired instruments catch what the literals missed? Take the
  wave-43 probes verbatim and require them to fail now. Then look for the next blind spot rather
  than certifying the closed one.
- **Y — the product and the integrator.** Drive the deployed stand and the journey. Audit the
  integrator's own executable changes, which no grant covered.

**Then they cross-examine.** Each is given the other's report and must answer two questions:
**which of the other's findings can I falsify or strengthen**, and **where does the other's method
share an assumption with its subject** (`OPERATING_CONSTRAINTS.md` §12)? A judge that only agrees
has not cross-judged.

**Neither repairs anything.** Each owns one report file.

## Only then, the final testing

`make gate` on the merged tree with the cross-judges' findings repaired, read from the `GATE OK`
line; then the deploy, `verify-deployed.sh`, and the tag. **One gate, one tag.**

## Lanes

`gate-w44a`, `gate-w44b`, `gate-w44j`, `gate-w44k` — recorded in `PORT_REGISTRY.md` in the commit
that dispatches this wave.
