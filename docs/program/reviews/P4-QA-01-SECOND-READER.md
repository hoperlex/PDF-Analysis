# P4-QA-01 — second-reader plausibility pass

Performed 2026-09-15 by the integrator, who authored no part of the PC-02 corpus, the
checker or the protocol. This closes the one item `P4-QA-01` recorded as **Outstanding**:
the manual check in its *Required tests* asking a second reviewer to confirm that each
seeded contradiction is professionally plausible and that no seeded item was derived from
observed model behaviour.

Read at `ea3c8f3` against `fixtures/validation/PC-02/corpus_manifest.json`.

**Verdict: pass, with two reviewer notes that change nothing in the corpus.** The
independence half is *verified*, not judged. The plausibility half is a judgement and §4
states whose judgement it is.

## 1. What was checked, and against what

Judgements below are taken from the manifest's own evidence quotations and control
statements, not from its summaries. Three mechanical checks were re-run first, so the
material being read is the material the task shipped:

| Check | Result |
|---|---|
| `corpus_check.py fixtures/validation/PC-02/corpus_manifest.json` | exit `0` — 14 measurable documents (5 seeded, 9 control), 9 seeded issues, 64 control statements, 4 negative-envelope documents; 86 ground-truth quotations resolved at their declared page and offset, each confirmed independently by pdfplumber 0.11.10 |
| `corpus_check.py --self-test` | exit `0` — **23 of 24 checks shown both red and green**. The exception, `CHK-INDEPENDENT-AVAILABLE`, is an environment assertion that fires when pdfplumber is absent, which no mutation of the corpus can arrange. The checker names it rather than counting it as covered |
| `git diff --check` | exit `0` |

The *other* manual check in *Required tests* — "the protocol contains no leading question
and no label outside the three fixed ones" — was recorded as done by the authoring
session. It was re-checked here rather than taken from the register, because a manual
check recorded by the session that wrote the material is the same class of claim as the
one being cleared. It holds: `docs/program/validation/PC-02_PROTOCOL.md` fixes exactly
`useful | incorrect | unclear`, matching the manifest's `finding_labels`; `F3` names all
three in the same order every time; `F5` and `D4` offer "yes, no, or unsure" explicitly;
and §6 carries a table of forbidden phrasings — "So you'd call that useful?", "Most
reviewers say this one is useful." — each mapped to what the moderator says instead.

## 2. No seeded item was derived from observed model behaviour — verified

This half does not rest on judgement.

**PC-01's three seeded attributes** (`fixtures/synthetic/ar/expected_issues.json`) are
`степень огнестойкости здания`, `количество эвакуационных выходов из надземной части` and
`тип заполнения оконных проёмов`. **None of the nine PC-02 attributes is any of them.**

The two nearest approaches are worth naming, because "no repeat" is a weaker statement
than "nothing adjacent":

- `PC02-S01-I1` (`класс конструктивной пожарной опасности`) shares the fire-code domain
  with `SI-01` but is a different regulatory attribute — ФЗ-123 art. 31's С0–С3 scale,
  not the fire-resistance degree. They are separately stated and separately wrong.
- `PC02-S04-I2` (`количество пассажирских лифтов`) shares the shape "count of a building
  element" with `SI-02` but not the element.

Neither is a repeat, and neither is close enough that a rate measured on PC-02 would be
measuring PC-01 again.

**Every `why_seeded` was also searched for any citation of what the model did.** Two
mention `PC-01` or measurement vocabulary; both were read and both are clean:

- `PC02-S01-I2` — "*the placeholder PC-01 did not use*". This cites what PC-01's
  **corpus** contained, not what the model did with it. It is a statement about avoiding
  fixture overlap, which strengthens independence rather than compromising it.
- `PC02-S05-I2` — "*both the recall and the precision sides … are exercised*". This
  describes what the document is built to exercise, not an observed rate.

No `why_seeded` refers to a finding the model produced, a rate it achieved, or a failure
it exhibited. The condition holds.

## 3. Each seeded contradiction is professionally plausible

All nine are plausible as AR-volume defects. Seven are strong; two carry a note.

Every distractor a `why_seeded` claims is present was checked against the control
statements rather than taken on trust, and **all of them are there**. A sample of what
that means in practice:

- `PC02-S04-I2` says a goods lift "offers the obvious wrong reconciliation — two plus
  one". `PC02-S04-K2` is `В корпусе 4 предусмотрен один грузопассажирский лифт`. The
  arithmetic trap is real: 2 + 1 = 3, and 3 is the false value.
- `PC02-S05-I1` says the contradiction sits beside the legitimate Russian distinction
  between `этажность` and `количество этажей`. `PC02-S05-K1` is `Количество этажей
  корпуса 5, включая подземные, — 13` and `K6` is `Помещения подвала в этажность здания
  не включаются`. Storey count 12 and total-including-underground 13 are mutually
  consistent; only the page-9 value of 14 contradicts. The distinction is correctly
  applied, which is what makes the trap fair.
- `PC02-S02-I1` says the correct value is restated in a different notation.
  `PC02-S02-K6` is `Общая площадь здания корпуса 2 составляет 4812,5 кв. м` — the same
  quantity, different notation, and not a contradiction.

The strongest three, on professional grounds:

- `PC02-S02-I1` — `4 812,5` against `4 218,5 м²`. A transposed digit pair is the most
  common way a real area disagrees with itself and the hardest to catch by skimming.
- `PC02-S04-I1` — datum `143,60` against `143,80`. Two hundred millimetres is small
  enough to survive review and expensive enough to matter on site, and the document also
  carries a neighbouring block's datum and a third value it explicitly withdraws.
- `PC02-S05-I1` — as above; the only item that requires the reader to apply a real
  domain rule correctly in order to avoid a false positive.

### Reviewer note 1 — `PC02-S03-I1` is the coarsest of the nine

`Кровля корпуса 3 — плоская` against `скатная` is a flat-versus-pitched contradiction.
It is genuinely possible in a multi-block volume where one section retains a superseded
solution, and the manifest is right that it is the one categorical case and the one with
the largest professional consequence. But it is the least subtle item in the set: a
discrepancy of that magnitude would usually be caught before an expert review.

**No change recommended.** A corpus that measures only subtle cases cannot show that the
obvious ones are caught either, and this is the only non-numeric contradiction — the
`why_seeded` argument that a rate measured only on numbers would not generalise is
correct. Recorded so that a later reader does not mistake an easy item for a
representative one when interpreting recall.

### Reviewer note 2 — `PC02-S01-I2` uses `TBD`, the least idiomatic of the placeholder forms

`Марка фасадных кассет корпуса 1 — TBD.` is a Latin token in a Russian AR volume. Russian
design documentation more often carries `уточняется`, `по заданию`, a dash, or a blank.

**No change recommended**, for two reasons that are stronger than the idiom: the form is
named explicitly by `PROTOTYPE_PROFILE.md` §7.1, so it is traceable to a specification
rather than chosen here; and the corpus already exercises the two more idiomatic forms —
`PC02-S03-I2` uses a blank rule (`— ___ мм`) and `PC02-S05-I2` uses `не определено`. The
three together cover the placeholder category better than three instances of the most
common form would. Recorded because a reader encountering `TBD` alone might read it as
carelessness rather than as spread.

## 4. The limit of this pass, stated rather than implied

§2 is verification and stands on its own. §3 is judgement, and the judgement is an
integrator's reading of AR-volume practice, not a licensed architect's. It is sufficient
to clear the item as `P4-QA-01` framed it — *a second reviewer who did not author the
material* — and it is not a professional-liability sign-off.

If the owner wants the plausibility half certified by a domain expert, the natural place
is the `OD-18` expert cohort, whose first session could carry this as a five-minute
preliminary rather than as a separate engagement. That is an owner decision; nothing in
`P4-BHV-01` is blocked on it, because the item `P4-QA-01` recorded as outstanding is the
one cleared here.

## 5. What this does and does not unblock

- **Cleared:** `P4-QA-01`'s Outstanding item. Its *Required tests* are now complete.
- **Still blocking `P4-BHV-01`:** `OD-18` — three to five named experts, at least two
  independent of the build team, with committed slots. That is unchanged and is the
  owner's.
- **Still open beside it:** `OD-17` (the next corpus shape; PC-02's precision evidence is
  saturated per `P4_CLOSURE.md` §6) and the 21st error code.
