# Wave 4 closure: clearing the two obligations that did not need the owner

Written 2026-09-15 by the integrator. Convergence at `4d0f01c`, base `ea3c8f3`; the gate is
green: **793 passed, 5 skipped, 116 subtests** under the canonical battery, `make foundation`
35 passed, `git diff --check` clean, working tree unchanged by the battery.

**The test count is unchanged from wave 3, and that is the correct result.** Wave 4 added no
product code and no guards. A wave that moved the number here would have been a wave that
changed behaviour, which was not the work.

No dispatched sessions. Led personally in `/root/w3` on branch `agent/w4`, reusing the
`gate-w3` instance rather than standing up a fourth, since nothing here touches runtime
behaviour.

## 1. Why this wave, and how it was chosen

Gates A, B and C are closed and PC-01 is accepted. What the roadmap has left — `P4-BHV-01`,
then P05 — is blocked on `OD-18`. So the question was what remains that is *not* the
owner's.

The answer was found by checking the registers against the tree rather than reading them,
and the first thing that check produced was a finding about the registers themselves (§3).

## 2. `P4-QA-01`'s second-reader pass — done

`P4-QA-01` shipped the PC-02 corpus, checker and protocol and recorded one item as
**Outstanding**: the manual second-reader check asking whether each seeded contradiction is
professionally plausible and whether any was derived from observed model behaviour. By
construction the authoring session could not clear it. It is not owner-blocked; it only
needed someone who authored none of it.

Recorded in full at `docs/program/reviews/P4-QA-01-SECOND-READER.md`. **Verdict: pass, with
two reviewer notes recommending no corpus change.**

- **The independence half is verified, not judged.** None of the nine PC-02 attributes is
  one of PC-01's three. The two nearest approaches are named rather than left implicit,
  because "no repeat" is a weaker claim than "nothing adjacent". Every `why_seeded` was also
  searched for any citation of what the model did; the two hits are recorded and ruled
  clean, so a later reader who greps finds them already disposed of.
- **Every distractor a `why_seeded` claims is present was checked against the controls**
  rather than taken on trust. All are there — including the 2 + 1 lift trap and the
  `этажность` / `количество этажей` distinction, which is applied *correctly*, and that is
  what makes the trap fair rather than a gotcha.
- **The other manual check was re-run too**, although the register said it was done: a
  manual check recorded by the session that wrote the material is the same class of claim
  as the one being cleared. The protocol holds.
- **The limit is stated in the review rather than implied.** §3 is an integrator's reading
  of AR-volume practice, not a licensed architect's sign-off. It clears the item as
  `P4-QA-01` framed it — a second reviewer who did not author the material — and the review
  names the natural place for a domain sign-off if the owner wants one.

The mechanical side was re-run first, and it is worth recording what it showed:
`corpus_check.py --self-test` demonstrates **23 of 24 checks both red and green**, and names
the twenty-fourth as an environment assertion no mutation of the corpus can arrange rather
than counting it as covered. That is the discipline this programme asks for, applied by a
session to its own work unprompted.

## 3. The open-item register had been entirely obsolete

`GATE_B2_CLOSURE.md` §5.3 "Carried forward" listed six open items. **All six were closed**,
and had been for some time, while the block still read as the list of what is open.

This matters more than the six lines. `W2_CLOSURE.md` §2 recorded two wave-2 briefs built
from stale records and called the failure mode systemic. §5.3 is the register that class of
mistake comes from — and `80ff9d8`, the commit written specifically to reconcile closure
records against the tree, did not reach it.

It nearly caught this wave too. §5.3 was the first candidate list for wave 4; four items had
been verified closed before the pattern was obvious enough to check the remaining two.

The items are struck through with their disposition and evidence, not deleted. A register
that is silently emptied teaches nothing about how long it stayed wrong.

Also corrected: `P2-API-01` declared two allowed paths that were never created. The
delivered code put both under `routers/`, inside a glob the same line already allowed.

## 4. The checker I did not build, and why

The obvious response to §3 is a guard that fails when a document references code that does
not exist. I measured it before building it, and it is the wrong tool.

- Of 77 code references in the programme docs, 6 do not resolve — and **5 of the 6 are cited
  precisely because they do not exist** ("the non-existent `tests/checkpoint/…`",
  "placeholders in prose"). A machine cannot tell that sentence from rot.
- Of 401 paths declared in task *Allowed paths* blocks — structural, not prose — 100 do not
  resolve, and nearly all are the deferred navigation layer and P04/P05 outputs that do not
  exist yet and correctly should not.

Either guard needs a large allowlist. **An allowlist is another register, and registers are
the thing that just rotted.** Building one would have manufactured the appearance of a
mechanical fix while adding a second artifact to keep reconciled.

What does work is the narrow, mechanical version wave 2 already used: pin the specific
figures that drift into a test, so a reader gets a failure rather than a stale sentence
(`W2-QA` did this for the journey figures). That generalises by being applied case by case
to figures, not by being generalised to prose.

Recorded because "I considered a guard here and decided against it" is the kind of judgement
that otherwise looks like an omission.

## 5. Version fixation

`origin/dev` advances to the wave-4 merge. **`origin/main` stays at `6d3c0f3`**, the PC-01
acceptance. Wave 4 changes no behaviour, so it does not add to the re-certification debt
wave 3 created — but it does not discharge it either, and main does not move until PC-01 is
re-run. That is the owner's call, per `VERSION_FIXATION.md`.

## 6. What is left, and who owns it

Nothing actionable remains that is not the owner's. The next wave needs a decision first.

- **`OD-18`** — three to five named experts, at least two independent of the build team,
  with committed slots. `P4-BHV-01` is blocked on this **alone** now that §2 is cleared.
- **`OD-17`** — the next corpus shape. PC-02's precision evidence is saturated
  (`P4_CLOSURE.md` §6): zero findings across nine controls and an empty third group, so
  further runs against this corpus cannot discover a new failure mode. Evidence that
  generalises needs documents of a different shape — tables, drawings, multi-column text —
  not more near-miss statements of the same twelve archetypes.
- **The 21st error code** — the catalog is a frozen 20-member enum with no code for "usable
  output over a strict subset of the input". Adding a member to a frozen catalog is an owner
  decision, not an integrator one.
- **PC-01 re-certification** — wave 3 changed `terminal_reason` values and listing order,
  both observable in the artifacts PC-01 scored. Whether to re-run is the owner's.
