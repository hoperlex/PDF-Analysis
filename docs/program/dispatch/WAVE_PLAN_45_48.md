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

## W45 — the second section vertical, and the readiness that shortens the host wave

**`R-25` ruled the order and the reason is measured**: the sections whose answers live in prose
and tables reuse the AR vertical almost entirely; the ones whose answers live in drawings reuse
none of it, because `PC-01` does no visual detection. **ПОС, ТХ, ПБ first.**

**And `R-25`'s own warning is the design constraint:** *«вертикаль одна и обобщать было не на
чем — второй раздел покажет швы»*. `AGENTS.md` §4 forbids a generic without proven semantics, so
**W45 does not extract one.** It builds the second instance and **measures** the seams.

**The seams, located rather than guessed** (`alpha-w44`):

| what is hard-coded to AR | where |
|---|---|
| `DISCIPLINE: Final[str] = "AR"` | `src/auditmanager/analysis/text/profile.py:35` |
| `CATEGORIES = ("internal_contradiction", "explicit_placeholder")` | `analysis/text/prompt.py:41` |
| `PROMPT_BUNDLE_ID` — one module constant | `analysis/text/prompt.py:46` |
| the bundle's `content_sha256`, which enters **every request checksum** | `prompt.py:192` |

The AR vertical is **5 175 lines** in `src/auditmanager/analysis/`. A second bundle is a second
identity, not a parameter.

| stream | subject |
|---|---|
| `W45-POS` | ПОС as a real second vertical: bundle, categories, fixtures, acceptance. **Stops hard at `D-70`** — it can be built and cannot be shown to work, and simulating around that is the silent fallback `AGENTS.md` §4 forbids by name |
| `W45-READY` | what must be true before the host arrives: `D-80`'s `.dockerignore` **verified by a real build**, `D-79`'s structural repair so the gate reads `docs/`, and a deploy rehearsal from a clean clone |

**`W45-READY` is the wave's leverage.** Every hour it spends is an hour the host wave does not,
and the host wave is the only thing that moves a certification criterion.

## W46 — the extraction, with two instances to argue from

Only after W45 exists is there a proof of semantics. W46 extracts what the two verticals share
and **leaves what they do not** — and the register row it must answer to is that this programme
forbids a base service written from one example.

## W47 — the debt wave, on cadence

`D-97` (six renderer copies against one contract), `D-87`, `D-89`'s rule, `D-96`'s discipline,
`D-74`, and whatever W45 and W46 leave. Named now so it is not invented at the end.

## W48 — ТХ, or the host wave if it has arrived

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
