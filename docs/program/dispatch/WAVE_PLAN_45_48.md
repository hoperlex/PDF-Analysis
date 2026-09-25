# Waves 45–48, planned 2026-09-24

**Successor to `WAVE_PLAN_42_45.md`.** Written into the tree because a session that restarts
loses its plan, and this programme has lost one that way.

## What is true at `alpha-w44` (`d6ebe3a`), measured

`make gate` → **`GATE OK`**: battery **2466**, foundation **35**, frontend **1110 in 78 files**.
All four refs equal; the stand is deployed and `verify-deployed.sh` reports it byte-identical.
Contract **15 paths / 18 operations / 51 schemas**, migration head **`0010`**, catalog **22 codes**.

**Twelve rows open. Five of them are the owner's** — `D-56`, `D-63`, `D-70`, `D-75`, `D-91` —
and one of those, `D-70`, blocks every path that needs a model.

## The constraint that shapes this plan, stated first

**`R-1`'s host has not arrived and `D-70`'s provider key has not arrived.** Together they block:
a live analysis, the owner's manual pass, `R-9`'s corpus work, `R-34`/`R-35`'s re-recognition,
and `PA-01` criteria 1 and 2 — which have read *cannot be established* through **four**
certifications.

**So these waves are chosen to be the work that is not waiting on either**, and to make the
host wave short when it comes rather than to substitute for it.

## W45 — the day the key arrives, and the one product advance that does not need it

> **Redesigned 2026-09-25, and this is the second withdrawal in this section.** The first
> version planned a second section vertical (ПОС) and was withdrawn an hour later because
> `PROTOTYPE_PROFILE.md` §7.2 defers a second discipline and `R-25` sequenced the thirteen
> sections **after the first deploy**. The second version kept `W45-BLOCKS` on a premise that
> was still unchecked: *where the geometry goes*. It goes to the **blob store** as two
> artifacts, and one of them — `ROLE_PAGE_CROPS` — is published **empty** (`crops=[]`). That
> does not kill the stream; it changes what the screen can honestly show, and finding it before
> dispatch rather than after is the whole of `D-96`'s discipline.

### The situation this wave is shaped by, stated once

**Nothing that demonstrates the product can be done without the owner.** The stand runs in
`recorded` mode (`R-30`) because `D-70`'s stub has no host; a real document has no recording, so
**the alpha cannot be driven end-to-end on a real PDF at all** until a provider key exists. The
host (`R-1`) is the other half, and together they hold `PA-01` criteria 1 and 2, unestablishable
through **four** certifications.

**So the wave is not chosen by what is most valuable in the abstract — it is chosen by what is
still possible.** Two streams, and they are honestly different in kind rather than pretending to
one theme:

| stream | why it is in this wave |
|---|---|
| `W45-READY` | **it shortens the blocked path.** Every hour here is an hour the host wave does not spend, and the host wave is the only thing that moves a certification criterion |
| `W45-BLOCKS` | **it advances the product without the blocked resource.** `page_geometry_extraction` carries no adapter, no model and no provider reference, so it produces its artifacts in `recorded` mode exactly as in `live` |

### `W45-READY` — the deploy stops being a hope

1. **`D-80`** — a `.dockerignore`, **verified by a real build and not by inspection.** The build
   context is **6.1 GB**, of which 5.3 GB is `.local/`, and `Dockerfile.web` runs `npm ci` and
   then `COPY web/ ./` over it, so the image's dependency tree is the build host's rather than
   the lockfile's. `PA-01` criterion 1 is *deploy from a clean clone*, where none of those
   directories exist — **the certification passes in the one condition where the defect cannot
   appear.**
2. **`D-79`** — the gate reads `docs/`. Every count the gate checks is a count in code; the
   surface, the migration head and the tagged tip in prose are unchecked, and this file's own
   orientation document went stale twice.
3. **A clean-clone rehearsal, timed.** Not to establish criterion 1 — this host has run
   `deploy.sh` — but to turn the host wave into a checklist with measured steps.

### `W45-BLOCKS` — the block markup a reviewer can open

`R-23` asked for *«постраничная разметка документа, векторный граф блока»*. **The first half
exists in the data and the second does not**, and the stream says which is which on screen
rather than implying both.

A reseal: one operation returning the block index for a version, its client, the mirror and
`FRONTEND_LOCK.json`. Under `R-29` the shape is the integrator's. **`R-39` now permits the screen
to say, in the words of the subject, what it cannot yet show.**

## W46 — the logs read operation, or the debt wave

The second of the three reseals `W43-PREP` put on paper: an execution journal a reviewer can
read. **Its note needs re-reading first** — `audit_event` is never written by `src/`; what exists
is `stage_result`, `model_call`, `contract_state_transition` and `command_record`, so the
operation's subject is a decision before it is a schema.

If that decision is not ready, W46 becomes the debt wave and W47 moves up.

## W47 — the debt wave, on cadence

`D-97` (six renderer copies against one contract), `D-87`, `D-89`'s rule, `D-96`'s discipline,
`D-74`, and whatever W45 and W46 leave. Named now so it is not invented at the end.

## W48 — the host wave if it has arrived, and otherwise the optimisation view

**The thirteen section verticals are not in this plan at all**, and that is deliberate: `R-25`
placed them after the first deploy, and `PROTOTYPE_PROFILE.md` §7.2 defers a second discipline.
**They start when the owner's host does.**

**The host wave pre-empts whichever wave it lands in.** It does not queue.

## Judging, per the owner's standing instruction

Every wave: **parallel streams, one judge at the close of each sub-stage, and two or more judges
cross-judging at the close — before the final testing.** Wave 44 is the evidence that the order
matters: its cross-judges found **five false greens in the integrator's own repairs**, including
a credential guard that admitted a fallback on the next line, and they were repaired **before**
the final gate rather than after a tag, which is what wave 43 had to do.

**And the cross-examination is not a formality.** In wave 44 each judge *strengthened* the
other's findings with measurements the other had not taken, and one narrowed its own finding in
the process.
