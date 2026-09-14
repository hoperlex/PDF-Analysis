# PC-02 validation session protocol

**Version `PC-02_PROTOCOL/1`.** Corpus: `fixtures/validation/PC-02/`.
Recording schema: `fixtures/validation/PC-02/session_record.schema.json`.

## 1. What this measures, and the one thing it must not do

PC-01 was accepted on 2026-09-14. A live `claude-opus-5` run found all three seeded
issues in a single eight-page document and flagged none of its six near-miss controls.
That establishes that the machinery works and that the model can do the task. It
establishes nothing about whether the findings are *professionally useful*, and the PC-01
report says so in as many words: "not established and not claimable here".

P04 asks that question. This protocol is how it gets asked without the asking changing
the answer.

The failure mode that would waste the whole checkpoint is not a low score. It is two
moderators producing two datasets that cannot be pooled — one who asked "that's a real
contradiction, isn't it?" and one who asked "which of the three labels fits?". Every rule
below exists to close one specific way that happens. **A protocol that lets one moderator
lead and another not produces two numbers that look like one.**

## 2. Roles, and who is blind

| Role | Sees the corpus manifest? | What they do |
| --- | --- | --- |
| **Expert** | No | Reviews finding lists as they would at work |
| **Moderator** | **No** | Runs the script, records, never evaluates |
| **Analyst** | Yes, afterwards | Scores records against ground truth, computes agreement |

The moderator being blind is not a courtesy, it is the mechanism. A moderator who knows
that page 5 contradicts page 2 cannot un-know it while choosing how to phrase a question,
and every unconscious emphasis lands on exactly the finding that matters most. It also
makes the one deflection line in §6 literally true, which is the only reason it works.

Nobody opens `corpus_manifest.json`, `pc02_corpus/content.py`, the seeded-issue list or
the control list before or during a session. The session record asserts this in
`session.ground_truth_withheld`; recording `false` there means the session is not pooled.

## 3. Materials and setup

- The 14 measurable documents in `fixtures/validation/PC-02/documents/`.
- The 4 negative-envelope documents in `fixtures/validation/PC-02/negative/`, used only
  for the refusal pass in §8 and **excluded from every finding denominator**.
- A calibration document: `fixtures/synthetic/ar/ar_baseline.pdf`, the frozen PC-01
  acceptance fixture. It is deliberately *not* from this corpus.
- The application at a recorded commit; `session.build_commit` is required.

Before the session, verify the corpus is intact:

```
.venv/bin/python tools/validation/corpus_check.py \
    fixtures/validation/PC-02/corpus_manifest.json
```

Exit `0` is a precondition for running a session at all. A session run against a corpus
that does not match its manifest measures the corpus, not the product.

## 4. Pre-registered document order

Document order is fixed in advance, not chosen by the moderator. Order effects — fatigue,
learning, drifting standards — then land the same way in every session instead of being
confounded with who ran it.

Index the corpus in this fixed order:

| # | Label | # | Label | # | Label |
| --- | --- | --- | --- | --- | --- |
| 1 | `PC02-S01` | 6 | `PC02-C03` | 11 | `PC02-C06` |
| 2 | `PC02-C01` | 7 | `PC02-C04` | 12 | `PC02-C07` |
| 3 | `PC02-S02` | 8 | `PC02-S04` | 13 | `PC02-C08` |
| 4 | `PC02-C02` | 9 | `PC02-C05` | 14 | `PC02-C09` |
| 5 | `PC02-S03` | 10 | `PC02-S05` | | |

A **block** is four sessions. Each session covers seven measurable documents; each
document is seen exactly twice per block, once by each moderator.

| Session | Moderator | Documents (by index) | Negative-envelope pass |
| --- | --- | --- | --- |
| 1 | A | 1, 2, 3, 4, 5, 6, 7 | `PC02-N01`, `PC02-N02` |
| 2 | A | 8, 9, 10, 11, 12, 13, 14 | `PC02-N03`, `PC02-N04` |
| 3 | B | 1, 3, 5, 7, 9, 11, 13 | `PC02-N02`, `PC02-N03` |
| 4 | B | 2, 4, 6, 8, 10, 12, 14 | `PC02-N04`, `PC02-N01` |

Odd-numbered sessions present their documents in the listed order; even-numbered sessions
present them reversed. Each session therefore mixes seeded and control documents — 3 and
4, or 2 and 5 — and no session is all of one kind, which would be visible to the expert
within twenty minutes.

Record the order actually used in `session.document_order`.

## 5. Running one document

Per-document time box: **10 minutes**, excluding interruptions. When it is reached, stop,
record `time_box_reached: true`, and keep the labels already given. A timed-out document
is reported separately and never silently averaged in.

1. Start the run. Record `run_id`.
2. Read **D1** verbatim. Start the clock.
3. For each published finding, in the order the application lists them, run **F1**–**F5**.
4. After the last finding, read **D2**, **D3**, **D4**. Stop the clock.
5. Fill one `document_record` and one `finding_record` per finding.

If the application publishes no findings for a document, that is a result: record
`findings_returned: 0` and go straight to D2. Do not prompt, re-run, or say anything
about it.

## 6. The closed question set

**The moderator may ask nothing that is not on this list.** Questions are read verbatim.
The moderator may repeat a question word-for-word, and may once say "in your own words".
Anything else — any rephrasing, any follow-up, any clarification invented on the spot —
is recorded in `deviations` with the documents it touched.

**Per document, before:**

> **D1.** "Here is the next document and the findings the system produced for it. Please
> review them the way you would at work. Tell me when you have finished."

**Per finding:**

> **F1.** "Please read this finding, then tell me what it is claiming."
>
> **F2.** "Please open its evidence. Is the quoted text where the finding says it is?"
>
> **F3.** "Which of the three labels fits: useful, incorrect, or unclear?"
>
> **F4.** "Why?"
>
> **F5.** "Reviewing this document yourself, would you have raised this? Yes, no, or
> unsure."

**Per document, after:**

> **D2.** "Is there anything in this document you think should have been reported and was
> not? If so, on which page?"
>
> **D3.** "Was there anything about getting from a finding to its place in the document
> that slowed you down?"
>
> **D4.** "Would you have used this finding list on a real document of this kind? Yes, no,
> or unsure."

**Post-session** — §9.

### The three labels are always read aloud, always in the same order

F3 names all three, every time, in the order **useful, incorrect, unclear**. Never
"so, useful?" — that supplies the answer. Never "useful or incorrect?" — that deletes the
third option, and `unclear` is the label that carries the most information about a
product that is not yet usable.

### When the expert asks the moderator whether something is right

There is one permitted answer, verbatim:

> "I can't say — I don't know the answer either. What is your reading?"

This is true, because of §2. If the moderator has seen ground truth, they must not run the
session.

### Phrasings that void a finding record

Each of these has ended a record's usability in usability work generally, and each has an
allowed replacement.

| Do not say | Say instead |
| --- | --- |
| "That's a real contradiction, isn't it?" | F3, verbatim |
| "So you'd call that useful?" | F3, verbatim |
| "Is this one of the planted problems?" | nothing; the moderator does not know |
| "The system found four here, so there should be four." | nothing |
| "Most reviewers say this one is useful." | nothing |
| "Take your time, this one is obviously wrong." | nothing |
| "You said it's wrong — so, incorrect?" | F3, verbatim |
| "Do you mean the page is wrong, or the quote?" | F2, verbatim |

If one is said anyway, record it in `deviations` naming the document, and the analyst
excludes that record rather than the session.

## 7. Assigning the label

Exactly three labels exist: `useful`, `incorrect`, `unclear`. `PROTOTYPE_PROFILE.md` §9
fixes them and there is no fourth. Apply these tests **in this order** — the order is what
makes two moderators agree:

1. **Could the expert tell what the finding is claiming, and decide it from this
   document alone?** If not — the wording is ambiguous, or deciding would need a drawing,
   a norm, or another volume — the label is **`unclear`**. Stop.
2. **Is the claim the finding makes about this document false?** The cited statements do
   not actually conflict; they describe different objects, different floors or different
   scopes; the quotation is not what the document says; the "placeholder" is a decision
   already made. Then the label is **`incorrect`**. Stop.
3. Otherwise the label is **`useful`**.

### The rule that stops the two moderators diverging

A finding can be **correct and still not worth raising**. Under step 3 that finding is
labelled `useful`, because the three labels are fixed and none of them means "true but
trivial". The professional judgement is captured by **F5**
(`expert_would_have_raised_it`), which is asked and recorded separately.

Without this rule one moderator records `useful` and the other records `incorrect` for
the same finding, and the two are indistinguishable afterwards. With it, "the model is
right about things nobody cares about" shows up as a high `useful` rate beside a low F5
rate — which is a finding about the product, and exactly what PC-01 could not see.

`evidence_location_correct` is recorded from **F2** and never inferred from the label. A
finding may be correct in substance and cite the wrong page; those are different defects
and §10 counts them separately.

## 8. The negative-envelope pass

Two per session, from the table in §4. These are **not** measurable documents. They are
excluded from every finding denominator and from every gate that counts measurable
documents, G4 included.

For each: attempt the upload and run, then record one `envelope_refusal_record`. The only
observation is whether the product refuses explicitly and **names the rule**. Quote the
message verbatim; a moderator's summary of an error message cannot be compared with
another moderator's summary.

If a negative-envelope document is accepted, or silently OCR'd, or partially read, that is
a **defect**, recorded as such (`ocr_silently_substituted`) and reported. `ENV-TEXT` in
particular: `PROTOTYPE_PROFILE.md` §7.1 forbids substituting OCR silently.

No F-question is asked about these documents. The expert is not asked to judge a refusal.

## 9. Post-session

Asked once, after the last document, in this order. The first four are closed-choice with
a reason; the fifth is the only open question in the whole protocol, and it is last so it
cannot contaminate any label.

> **P1.** "What is the single thing missing that would stop you using this on real work?"
> — record the closest option in `blocking_capability.choice`, and the expert's own words
> verbatim in `in_own_words`. Read the options aloud only if the expert asks.
>
> **P2.** "If one thing could be built next — going deeper on a single document, or
> comparing documents against each other — which is worth more?" — forced choice into
> `next_investment.choice`, plus the reason.
>
> **P3.** "Did anything fail or go wrong during the session?" — one entry per failure in
> `failures_observed`, each with its `remedy`.
>
> **P4.** "Was there anything that slowed you down getting around the tool?" —
> `navigation_friction_incidents`.
>
> **P5.** "Anything else?" — verbatim into `expert_closing_comment`.

Ground truth is **not** revealed at the end of the session. The expert may take part in a
later session in the same block, and an expert who has been told which documents were
seeded cannot review the rest of the corpus cold.

## 10. The recording schema

Every session produces one JSON document validating against
`fixtures/validation/PC-02/session_record.schema.json` (`pc02-session-record/1`). A record
that does not validate is not pooled: a field one moderator invented is a field the other
did not fill.

Four record types, and what each is for:

| Record | One per | Carries |
| --- | --- | --- |
| `finding_record` | published finding | label, rationale, evidence-location correctness, F5, seconds, navigation steps |
| `document_record` | measurable document | run id, review seconds, findings returned, time-box flag, issues the expert thinks were missed, D4 |
| `envelope_refusal_record` | negative-envelope document | whether refused, whether the rule was named, the message verbatim |
| `post_session_record` | session | P1–P5 |

Plus `session` (identity, blinding assertions, pre-registered order) and `deviations`,
which is required and may be empty — empty asserts there were none, not that nobody
looked.

`document_record.expert_suspected_issues` is captured from **D2 before any ground truth
exists in the room**. It is the only false-negative evidence a session produces from the
expert's side; the manifest supplies the rest afterwards.

## 11. Scoring, done by the analyst afterwards

### Matching findings to ground truth

A new run allocates new `finding_uid`s and PC-01 implements no cross-run matching, so
findings cannot be matched between sessions by id. The analyst matches **mechanically**,
by content, and reports what did not match rather than dropping it:

- A published finding **matches a seeded issue** when it cites the same document, carries
  the same `category`, and at least one of its evidence quotations is on a page the
  seeded issue declares and either contains or is contained by the seeded quotation on
  that page.
- A published finding **matches a declared control** by the same rule against the
  control's quotation and pages.
- Two findings from **different runs are the same item** when they share the document,
  the category, and one evidence quotation string exactly. This is the pairing used for
  inter-moderator agreement.
- Findings matching neither a seeded issue nor a declared control are reported as a third
  group with their quotations. They are the corpus's blind spot, and the honest place to
  see it.

### Metrics

Denominators count **measurable documents only**.

| From `PROTOTYPE_PROFILE.md` §9 | Computed as |
| --- | --- |
| % findings useful / incorrect / unclear | over all `finding_record`s on measurable documents |
| evidence-location correctness | `correct` ÷ (`correct` + `wrong_page` + `wrong_quotation`); `not_checked` excluded and reported |
| recall against ground truth | seeded issues matched ÷ 9 |
| false-positive pressure | findings on the 9 control documents, and findings matching a declared control, broken down by the control's `archetype` |
| expert review time | median `review_seconds`, and per page |
| navigation friction | `navigation_steps`, D3 and P4 incidents |
| blocking capability / next investment | tallies of P1 and P2, always beside the free text |
| provider latency, cost, failure distribution | **not** from these records — from the run ledger, owned by `P4-OPS-01` |

Report the F5 rate (`expert_would_have_raised_it`) beside the `useful` rate, always.
Separating them is the point of §7.

### Before any rate is reported

- **Agreement.** Compute Cohen's κ on the three labels over items paired between
  moderators. If κ < 0.60, the two moderators' data are **reported separately and not
  pooled**, and the protocol is revised before more sessions are run. A pooled number
  from two moderators who disagree is worse than two honest numbers.
- **Sample.** If fewer than 12 measurable documents reached a terminal state, the sample
  statement in the execution plan is recomputed at the surviving count first.
- **Excluded records.** Every record dropped for a deviation is listed with its reason.

## 12. What this protocol does not establish

- The corpus is synthetic (owner decision `OD-17`). Its seeded issues are unambiguous by
  construction; real documents contain borderline cases it does not represent, so a good
  score here is not evidence of real-world accuracy.
- Its 64 control statements cover 12 anticipated near-miss archetypes. They bound
  precision against *those*. They cannot bound it against a failure mode nobody thought
  of, which is why unmatched findings are reported as their own group in §11.
- Layout is plain single-column text: no tables, stamps, drawings, rotated pages or
  multi-column text. Text extraction is exercised; layout reconstruction is not.
- The calibration document is the PC-01 baseline, whose seeded attributes — fire-resistance
  degree, evacuation-exit count, the literal `уточнить` — appear in **no** PC-02 document.
  That keeps it from leaking answers, but it may prime an expert toward those attributes
  specifically. The effect is identical in every session, so it does not distort
  comparisons between them; it may distort the absolute recall figure.
- One language, one discipline, one country's drafting conventions.
