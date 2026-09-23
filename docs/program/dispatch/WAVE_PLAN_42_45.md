# Waves 42–45, planned 2026-09-23 under `R-29`

**Successor to `WAVE_PLAN_39_42.md`, which ran out at 42.** Written into the tree for the same
reason as its predecessor: wave 33 was laid out in a session that died before dispatching, and
left three branches nobody could account for.

`R-29` lets the integrator run these without asking. **It stops at two things: spending above
about $5 in a wave, and anything that changes who can reach the system or exposes what was not
exposed.** Each wave below names which of its parts could hit either.

---

## What this plan corrected before it was written

`WAVE_PLAN_39_42.md` would have put the **knowledge base** in wave 42, because `R-23` ruled it
*"required, and must work inside the alpha"* and `R-24` ruled it gets a listing operation in the
contract rather than a client-side walk.

**It is already built.** `listDecisions GET /decisions` is in the frozen surface, and
`web/src/widgets/knowledge-base/`, `web/src/_pages/knowledge-base/`,
`web/src/app/knowledge-base/page.tsx`, `entities/expert-decision/api/use-decision-journal.ts` and
a link in the application frame are all in the tree. Wave 38 did it — `docs/program/W38-KB.md`,
and the `KB` in that stream name is what it stands for.

**Recorded here because a plan that re-commissions finished work is the expensive kind of wrong**,
and because the reason it nearly happened is the one this programme keeps paying for: the ruling
was read, and the tree was not. Every wave below was derived by listing the nine addresses that
exist (`find web/src/app -name page.tsx`) against the ten screens `R-23` sorted.

**Ruled and genuinely unbuilt**, which is what 42 and 43 are made of:

| | ruled | state |
|---|---|---|
| stage comparison | `R-23` — *"very important; a stub skeleton now"* | **no address, no component** |
| blocks, optimisation, logs, workers | `R-23` addendum — preparation may be done now | **no address, no component** |
| dashboard | `R-23`, then deferred by the owner the same day | `D-63`, waits |
| dispatcher | `R-23` — after rights, users, actions, personal account | waits on users |
| queue, work schedule | `R-23` — deferred | waits |
| the 13 remaining sections | `R-25` — ПОС, ТХ, ПБ first, by textuality | sequenced after the first deploy |

## W42 — the screens the owner ruled and nobody built

**Pure front end. No contract, no migration, no reseal, no spend.** Both streams are `R-29`-clean:
nothing here changes who can reach anything.

| stream | owns | content |
|---|---|---|
| `W42-COMPARE` | `web/src/{_pages,widgets,app}/**` under its own routes | the stage-comparison skeleton. `R-23` asked for a skeleton with honest stubs, not a mechanism |
| `W42-PREP` | its own four routes, `web/src/shared/ui/route-placeholder*` | blocks, optimisation, logs, workers — the four-part preparation `R-23`'s addendum defines |

**The addendum defines "preparation" and it is worth quoting rather than paraphrasing**: a place
in the navigation; a `RoutePlaceholder` carrying a `promise` — *what will be here*, never
*"not implemented"*; **the data shape written down and checked against the contract**, so a future
reseal is seen now rather than at the end of a wave; and **no invented numbers**.

**The third of those four is the one with lasting value and the one a stream will skip if the
brief lets it.** Each of the four screens is a future reseal or is not, and which is which is
knowable today: blocks needs geometry the data does not have (`coords_norm` is `[0,0,1,1]` on all
28 249 corpus blocks, `polygon_points` empty); logs need a read operation the contract has no
trace of; optimisation has one visible analysis stage to tune against legacy's seventeen; workers
are excluded outright by `PROTOTYPE_PROFILE.md` §7. **A brief that asks for four stubs gets four
stubs. This one asks for four stubs and four data-shape notes.**

**The language guard covers this wave by construction** — four new screens are four new sets of
strings, and `rendered-language.guard.test.ts` fails on one English word. Whether it *reaches*
them is exactly `D-69`, which wave 41 is repairing; **W42 is the first wave that will test
wave 41's repair on screens written after it.** That is a deliberate ordering.

## W43 — the second section, and the seams it exposes

`R-25` ordered the thirteen remaining sections **by how textual they are — ПОС, ТХ, ПБ first** —
and the reason was measured, not aesthetic: the AR vertical is **5 148 lines plus a content-hashed
prompt bundle plus 16 fixtures**, and a section whose answers live in drawings reuses none of it.

**The owner sequenced the sections after the first deploy.** That deploy is `R-1` and has been
blocked on the owner for six waves. **This plan does not reorder that ruling; it fills the wait**,
and the moment the host arrives W43 yields to the host wave below.

**And the owner's own draft names the trap in advance:** *"вынести то, что у АР сейчас зашито в
единственную вертикаль, в форму, которую переиспользует вторая… Сегодня этого не видно, потому что
вертикаль одна и обобщать было не на чем — второй раздел покажет швы."*

**So this wave does not extract a generic.** `AGENTS.md` §4 forbids a base service or a generic
repository without proven semantics, and one vertical is not a proof. It builds **ПОС as a second
real vertical** and lets the seams appear; the extraction is W45's, with two instances to argue
from.

**Where this wave stops, and it stops hard:** validating a vertical means running it against a
provider, and **`D-70` means there is no provider.** ПОС can be built to fixtures, prompt bundle,
categories and acceptance; it cannot be *shown to work*. The brief must say so at the top, and the
stream must not simulate around it — `AGENTS.md` §4 forbids a silent fallback, and an LLM output
standing in for an expert's decision is the specific case it forbids by name.

## W44 — the debt wave

Cadence: 41 was debt, 42 and 43 build, 44 closes. Candidates in register order, and this list is
written now so it is not invented at the end:

`D-46` (a failed run cannot say *which* dependency — a reseal either way, and the cheaper of its
two shapes, `RunStatus.terminal_detail`, is the integrator's to pick under `R-29`) · `D-50` ·
`D-58`'s remaining clause, which is a deletion · `D-60`'s token count with a real tokeniser
**before anything is embedded** · `D-68`'s selector, which cannot close until a certification runs ·
and whatever wave 41 leaves standing.

**`D-46` is the one to batch a reseal around**, on `R-24`'s own note: if `D-56`'s per-section
verdict field has been ruled by then, the two go in one reseal. `R-11` reverted an entire wave over
a reseal found at the end rather than planned at the start.

## W45 — the host wave, and it pre-empts

**Whenever the host arrives, it takes the next wave, whatever that wave was going to be.** It does
not queue behind 42, 43 or 44.

The reason is arithmetic, not enthusiasm: `PA-01` criteria 1 and 2 have read **`cannot be
established`** through four certifications, and both close on the first deploy from a clean clone
with a certificate. Nothing else in this plan moves a certification criterion at all. `W26-HOST`
left nothing to author — the TLS block is inert until a certificate appears and the runbook is
written — so the wave is execution, not design.

It carries, in this order: deploy from a clean clone · the certificate and TLS · the **fifth**
`PA-01` certification, with `D-68`'s corrected selector `span.am-badge[data-run-state]` · then the
owner's manual pass, which `R-9` makes the gate on the corpus work and which **`D-70` still blocks
until a real provider key is on the host.**

If the host arrives and `D-70` does not clear with it, **the deploy and the certification still
run** — they do not need a provider — and the manual pass waits alone.

## What is owner-blocked across all four, so no wave is designed around a ruling that never comes

`R-1` the host · `D-70` a provider key · `D-73` the four unauthenticated routes · `D-75` the
published account and the lockout aimed at it · `D-71` the corpus defect's true size · `D-56`'s
per-section half · `D-63` the dashboard · `R-4`'s wipe.

**Five of those eight are `R-29` clause 2 by name.** None of the four waves above needs any of
them to start.

## Lanes

`PORT_REGISTRY.md`, a row per stream, in the commit that dispatches it. `561xx` with S3 at `597xx`
and `598xx`. Wave 41 holds `56220` and `56230`; waves 39 and 40 are released.
