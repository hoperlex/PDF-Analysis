# Wave 57 — split: W57a norms in the analysis with verified citations; W57b the project's own references and Excel

**Status:** revision 3 with the fix round, 2026-10-12, on `plan/corpus-chain`. Round 2 (the last) was judged
on `33fe3f7`; its findings and this revision's dispositions are recorded in
`reviews/W54-W57-CHAIN-JUDGING.md`, and the history of every earlier finding is in
`reviews/W57-PLAN-JUDGING.md` and `reviews/W54-W57-CHAIN-REVIEW.md` (CD-1…CD-21 binding; CD-20).
**Controlling answers:** `ROADMAP-TO-BETA.md` §10.15 (I-1…I-12) as amended by §10.16 (K-2, K-5, K-6, K-10),
§10.13 (G-5, G-6, G-11), §10.14 (H-3, H-5, H-6, H-8, H-9); rulings R-79, R-80, R-82, R-86. Research:
`reviews/W57-RESEARCH.md`.
**Frame (one line each):** releases are targets under §8.4 and R-86 (W57a `v0.8.0`, W57b `v0.8.1`; W53 is
released as `v0.4.0`); migration slots per CD-2 (`0023`, `0024`, re-assigned by `pin_sweep migration`);
check levels per R-70/R-84 (CD-10), the full gate before every `main`; pins measured on `origin/dev`
`4fe7615` and re-swept at each freeze; rules recorded by each `*-RULE-01` under the next free number at
its freeze (≥ R-120); `contract_version` does not move (additive changes only).
**The wave is two waves (I-9)**, each with its own rule, freeze, seal, judges, close and budget. **Order
(I-12):** W56a → **W57a → W57b** → W56b → W58.

**Technical choices** (not owner questions):

- the model cites **only paragraphs it was given**, by label, with a verbatim quote and the requirement's
  value, so a phantom clause cannot be cited;
- citations are grounded by the **central gate before the merge**; the gate stays a pure function, since
  the set artefact carries the full reliable text of every mapped document;
- quotes are compared after one declared normalisation, numbers by one declared tokeniser (§A3.4); the
  stored quote is mapped back to raw offsets;
- **any** failed citation withholds the observation; two or more rebinding candidates withhold it;
- the set is **document-independent and reproducible**: exact inner products in pure Python
  (`math.fsum`), no index, a stable tie-break, a fixed prompt-part ceiling;
- the set and the snapshot's **catalogue** are published through **R-76 custody bindings** (CD-4, CD-19);
  only a row **verified** against the committed digests ever pins (CD-18);
- the stand build is a **separate act after the deployment**, through a forced-command verb; the profile
  switch is an **owner act** (CD-17);
- a **re-audit** runs on the current configuration, snapshot and set, or is refused (R-82, CD-6);
- a rule-made observation carries `ObservationProvenance.rule_id`; `ProviderMode` is never widened;
- Excel is written by a standard-library writer (`ZIP_STORED`, no new dependency).

---

## Part A — W57a: norms in the analysis with verified citations

### A1. Objective

- **Profile АР v3** = v2 (W56a) plus five normative categories (K-2, CD-5): evacuation, fire safety,
  accessibility for МГН, thermal protection, sound insulation — each "the value the document states
  against the norm's requirement", without calculation (I-4).
  - **Fire safety** maps to every fire-safety clause the corpus holds: Федеральный закон N 123-ФЗ,
    СП 54.13330.2022 §6.2, СП 118.13330.2022's fire-safety sections, СП 1.13130.2020 and the relevant
    parts of СП 3.13130.2009 and СП 7.13130.2013, and the fire-equipment ГОСТ documents.
  - **Excluded and listed:** clauses that defer to the absent СП 2.13130 or СП 4.13130; СП 112.13330.2011
    (the actualised СНиП 21-01-97*, whose provisions the СП 1–4.13130 series replaced; the corpus holds no
    status data to say which applies, I-3, and its fire-resistance and fire-spread clauses are the absent
    codes' subject); insolation (after beta, K-2).
- **Every normative finding carries verified citations:** document, clause, a quote found in a canonical
  paragraph of the pinned snapshot (G-6, NORM-Q01), the requirement's value found in the quote, the
  stated value found in the document evidence. A failed citation withholds the finding, counted on the
  run (I-1, I-5).
- **The map** is reviewed once by the owner against a pinned snapshot (I-8).
- **The set reaches the stand** by a verified, reversible act (CD-3 P5).
- One paid call per run (I-1); no BGE on the stand (I-2); v1 and v2 byte-identical; the CSV unchanged;
  live spend ≤ $8 (K-10).

### A2. Where it starts

Measured on `origin/dev` `4fe7615`; "moves" marks pins a predecessor edits before W57a's freeze.

| Fact | Source | Consumer |
| --- | --- | --- |
| `norm_verification` declared (leaf, model-routed, `remote_eligible`, inputs `findings.merged`, `norms.snapshot`); `text_analysis` reads `prepared.text_layer`, `context.document_graph`; PD-02; FS-04 | `contracts/analysis/v1/stage-registry.json:658-708, 886-891, 167-177` (moves, W56a) | SEAL, NORMREFS |
| the gate: one declared normalisation, no offset search, no database; five reasons by a `0003` CHECK, six after W56a | `findings/grounding.py:1-31, 48-55`; `0003:73-87` (moves, W56a) | CITE, SEAL |
| `kind` body/heading/table_row; `clause_number` only on a paragraph opening with digits (`А.2.1` unmatched); a markdown table is **one** paragraph; corpus text carries `**`, `######` captions and LaTeX (СП 50.13330.2024: 231 LaTeX lines; 5.2 opens with `R_o^{\text{норм}}`) | `norms/segmentation.py:37-39, 135-148, 196-246`; `0012:138-171` | MAP, CITE |
| windows record document ordinals `paragraph_ordinal_first/_last`; chunks average 1,072 characters and have an `ordinal`; `norm_embedding_pk`, `norm_chunk_pk` are identity columns | `0013:121-161`; `0012:202-242`; `norms/chunking.py:3-5` | RETRIEVAL |
| `required_norm_unavailable` (422, not retryable; safe key `reference_kind`) is the frozen `created → queued` refusal; its message names three reference kinds | `state-machines.json:343-350`; `error-codes.json:311-325`; `web/src/shared/api/catalog-message.ts:125-128` | PROFILE, SEAL |
| the NormsSnapshot clause is recorded **unevaluated** | `runs/scope.py:36-55`; `P02_SEAMS.md:756-777` (§9.2), `:790-817` (§9.4); `tests/contract/domain_p02/test_seam_register.py:251-273` | PROFILE |
| re-audit: current profile, bundle and mode (R-82) but the **source's** `norms_snapshot_id` (`:426`; W55a's PIN replaces it) | `runs/commands.py:352-432` (moves, W55a) | PROFILE |
| the frozen-column trigger is recreated per migration | `0017:22-36, 110-114` | SEAL |
| custody tables `norm_custody_admission`/`_binding` with `role`, CHECK `ck_norm_custody_role_shape`, registry `norms/custody/roles.py`, `publish_bindings(role, target)` | `W54-PLAN.md` §3.1; CD-19 | SEAL, RETRIEVAL |
| proxy timeout 200 s against a ≈ 190 s deadline; a reset, timeout, 504 or foreign 503 is `outcome_unknown`, never re-spent (R-79); `MAX_OUTPUT_TOKENS` 16,000 is a bundle property; measured 746 output tokens in 10.49 s | `analysis/text/proxy.py:62, 183-240, 309-327`; `analysis/text/prompt.py:151, 183-217`; `artifacts/checkpoints/PC-01/recertification-c0d7daf.json` (moves, W56a) | CAP, PROFILE |
| `ProviderMode` (`live`, `recorded`) is shared by `StartRunRequest`, `RunStatus`, `ObservationProvenance`; four CHECKs; written out in `_ENUM_VALUES` | `0002:142, 694-696, 841-842, 947-948`; `0014:268`; `api/routers/handlers.py:155-160` | W57b SEAL |
| `findings/artifacts.py` hard-codes the role `analysis.text_observations` | `findings/artifacts.py:36, 61-64` | NORMREFS |
| role register: an unlisted operation is refused to all; `listRunFindings` `_ANY_ROLE`, `exportRunCsv` `_EXPERT` | `api/security.py:312-362`; `tests/integration/api/test_role_register.py` | SEAL |
| corpus: СП 54.13330.2022, СП 118.13330.2022, СП 1.13130.2020, СП 3.13130.2009, СП 7.13130.2013, СП 112.13330.2011, 123-ФЗ, СП 59.13330.2020, СП 50.13330.2024, СП 51.13330.2011 with Изменение N 3, fire-equipment ГОСТ Р; no СанПиН 1.2.3685-21, ГОСТ Р 57795, СП 2.13130, СП 4.13130 | `.local/norms/corpus/MANIFEST.json` | MAP |
| legacy АР checklist thresholds and phantom clauses | legacy `prompts/disciplines/AR/checklist.md:1-7` (`c0771b2e`) | MAP |
| W55a: pinning, the setter `norms/current_snapshot.py`, `page_label`, `norm_designation_tokens`, `textless_pages`, G-11; W56a: profile registry, `AUDITMANAGER_ANALYSIS_PROFILE_ID`, merge, generator, matcher, ledger; W54: `embed-texts`, the dispatchers | `W55-PLAN.md` §C7; `W56-PLAN.md` §A3.1–§A3.8; `W54-PLAN.md` §3.4–§3.5 | all |

### A3. Design

**A3.1 The checklist map (I-2, I-8, K-2, CD-5).**

- **Items** (`analysis/profiles/ar_v3/norm_map/items.json`, ≈ 22–25): id, one of the five categories, the
  Russian item text ported from legacy **with every number and clause reference removed**, a provenance
  header (legacy path, SHA-256), a query text and **targets**.
- **Excluded list:** every excluded legacy item and every out-of-scope fire check, with its reason (§A1).
- **Targets**, resolved by `MAP-01` on the promotion database and recorded as `ndoc_`, designation,
  edition and `npar_` first/last:
  - **clause** (`7.1.4`): from the paragraph whose `clause_number` equals it, onward by `ordinal`, until a
    heading or a paragraph whose `clause_number` is neither it nor a descendant (`7.1.4.` prefix);
    paragraphs with `clause_number` `None` are included;
  - **table** («таблица 5.34»): from the caption paragraph through its table and notes, to the next
    heading or numbered clause;
  - **paragraph range** (`npar_` first/last): for appendix clauses (`А.2.1`), clauses whose number the
    segmenter misses (LaTeX-led, as СП 50's 5.2) and any span the other rules cannot express.
  - Caption and clause detection strip `**`, `__` and leading `#` before matching («**Таблица»,
    «###### Таблица»).
  - Spans exclude unreliable paragraphs (listed). An item whose target spans exceed the prompt-part
    ceiling divided by the item count (≈ 880–1,000 characters, §A3.2) is flagged for the review.
- **Editions:** `MAP-01` picks the newest edition of the target's family and base and records the `ndoc_`;
  the owner reviews it; nothing resolves editions later. An amendment document («Изменение N 3 к
  СП 51.13330.2011») is listed beside its base's targets, never treated as an edition; the owner decides
  whether a clause maps to the amendment's paragraphs.
- **Query vectors:** one per item, by W54's `python -m auditmanager.norms.embedding embed-texts` inside
  W54's BGE image (`bge-m3-dense-v1`, no network), stored in `query_vectors.json` (float32, base64) with
  the profile, model revision and SHA-256. Only changed query texts are re-embedded.
- **Map identity** (`norm_map/map.json`): items and vectors digests, resolved targets, the excluded list,
  and the **reviewed content key, `ns_` id and embedding build**. The map digest is the SHA-256 of its
  canonical JSON.
- **Review:** `MAP-01`'s report prints each item beside its resolved span texts; the owner reviews once;
  a change is a re-run.

**A3.2 The set, the catalogue, pinning and activation.**

- **Identity:** (map digest, `ns_` id, embedding build, `builder_version`). The builder version names the
  algorithm and its constants, so a corrected builder gets a new identity.
- **Prompt part:** per item, its target paragraphs, then the **top windows** among the mapped documents'
  windows by exact inner product with the item's vector, each resolved to the reliable paragraphs from
  `paragraph_ordinal_first` to `_last`. Deduplicated; ordered by item, designation, `ordinal`; each with
  label `N1…Nk`, `ndoc_`, `npar_`, designation, title, `clause_number`, `page_label`, text, SHA-256.
- **Prompt-part ceiling: 10,000 tokens, enforced as 22,000 characters** (W56a's measured ≈ 2.2
  characters per token), derived from $8 with one full re-record (§A3.8). **Reduction order** until under
  it: (1) drop windows whose paragraphs lie inside the item's target span; (2) windows per item 3 → 2 → 1
  → 0, uniformly. Windows average 1,072 characters and tables run 1.5–3.1k, so expect 0–1 windows per
  item. Still above → `CAP-01` stops for a map re-review; never truncated.
- **Rebinding part:** the full reliable text of every mapped document (ids, ordinals, texts), never sent.
  The set records `norm-quote-v1` and the tokeniser version.
- **Exactness:** stored vectors read as float32 (`array('f')`), inner products by `math.fsum` (correctly
  rounded, identical on every host); no SQL ordering by distance, so no index; ties by
  (`norm_document_id`, chunk `ordinal`, `window_ordinal`). Above 50,000 candidate windows is a stop.
- **Catalogue** (`norms.catalogue`, for W57b): every document of the snapshot — `ndoc_`, slug,
  `designation_tokens` as W55a stores them, title, `doc_type`. Built with the set; W57a does not read it.
- **Build** `python -m auditmanager.norms retrieval-set build --profile <v3's ap_ id> --snapshot <ns_>
  --expect <set-sha256> <catalogue-sha256>`:
  - refuses unless the `ns_` id and its content key equal the map's reviewed ones and the snapshot
    qualifies (complete BGE build); it need **not** be current (CD-18);
  - digests differ from the expected → one `rejected` row with the observed digests, no admission, never
    pinnable; the report names the differing items;
  - digests equal → the builder pre-allocates the row's `nrs_` id; custody admissions for both blobs
    carry `target_kind` `norm_retrieval_set` and `target_id` that id; dispatch until idle; then **one
    transaction** inserts the `verified` row under that id and calls `publish_bindings` for both roles,
    which checks that the target row exists and is `verified`;
  - an identical re-run is a replay; an interrupted run continues, or W54's reconciler settles it.
- **Pinning:** a v3 `startRun` reads the **verified** row for (map digest, current snapshot, deployed
  builder version) and writes `audit_run.norm_retrieval_set_id`; none, or no current snapshot →
  `required_norm_unavailable` (`reference_kind`: `norm_retrieval_set` or `norms_snapshot`; CD-19). The
  stored `frozen_input_digest` adds the set digest beside the snapshot; `input_basis_digest` and both
  fingerprints are unchanged; v1 and v2 rows keep NULL.
- **Re-audit (R-82, CD-6):** the current profile, bundle and mode (W53-CLOSE), the **current** snapshot
  (W55a's reader) and, for v3, the **current verified set**; a missing one refuses before any provider
  effect. The run records what it used; the source is linked only by `reaudit_of_run_id`; the fingerprint
  stays keyed to the source.
- **Activation guard** (in `norms/current_snapshot.py`): while the configured profile needs
  a set, `setCurrentNormSnapshot` also requires a verified set and catalogue at the **target** for that
  profile's map and builder version; otherwise `required_norm_unavailable` (`reference_kind`
  `norm_retrieval_set`, safe detail `analysis_profile_id`; SEAL owns both), pointer and history unchanged. With a v1 or v2 profile W55a's
  behaviour is unchanged.
- **Where v3 starts refuse:** only when the configured profile is v3 and no verified row exists for the
  current snapshot — on the stand, between an owner switch made too early and the build (the precheck in
  §A3.9 prevents it), and during a corpus refresh between deploying a re-reviewed map and activating its
  snapshot.
- **Corpus refresh order:** import the new snapshot, not current (P4's pattern) → `MAP-01` re-review on
  the promotion database → publish the new map (a `main` publication) → build and verify the set for the
  new `ns_` (explicit, not current) → activate the new snapshot (the guard passes). Deploy, build and
  activation share one agreed window (K-5), or the owner holds the profile at v2 for it.
- **Registry role:** the set blob is `text_analysis`'s optional `norms.snapshot` input (v3 only),
  *"referenced by blob_id and SHA-256"*, so the stage stays `remote_eligible`. Module `norms/retrieval/**`
  behind `norms/public.py` (ALR-05).

**A3.3 Profile v3, the prompt, the call and the caps (I-1, I-4, CD-13).**

- **Profile** v3 (its `ap_` id named at the seal) in W56a's registry, own prompt bundle; twelve categories (v2's seven plus the five;
  legacy names `evacuation`, `fire_safety`, `accessibility`, `insulation`, `sound`, final at the seal);
  stage plan: three deterministic stages, `text_analysis`, the gate, `finding_merge`, publication. Chosen
  by `AUDITMANAGER_ANALYSIS_PROFILE_ID`.
- **Prompt:** v2's plus «нормы для проверки» (the prompt part under its labels) and the items. Rules: cite
  only given labels; quote ≥ 20 characters verbatim **from one paragraph**, table cells with their `|`;
  `required_value` as written in the quote, `stated_value` as written in the evidence; raise a normative
  finding only for a stated value; apply a norm only when its scope covers the object, else no finding.
- **Response schema:** a normative observation requires `norm_citations` (1–5 `{label, quote}`, quote
  20–1,000 characters), `required_value` and `stated_value` (1–200 each); other categories forbid them.
- **Input budget (G-11):** W55b's budget reserves the 10,000-token prompt part; `startRun` and
  `reauditRun` refuse above it as today.
- **Output cap (CD-13):** v3's bundle sets its own `max_output_tokens`; v1 and v2 keep 16,000.
  *C* = ⌊(170 s − *T*in) × *r*⌋ to a multiple of 500, ≤ 16,000, where *r* = the slowest sample's output
  rate × 0.85 and *T*in = the slowest sample's input time; thinking counts toward *C*; a reply reaching
  *C* ends `partial`, counted. *C* < 6,000 stops for the owner.
- **Samples (`CAP-01`):** at least 3 budget-size calls on the gateway, key and model the stand uses (as
  W56a's identity probe), each with its own `max_output_tokens` ≤ 4,000 so no sample can pass the
  deadline; one asks for a long answer to measure *r*.
- **Latency (R-79):** a 504 or reset after sending is paid and never re-spent, so any recorded latency
  above 170 s stops the wave. The real-prompt check is `CAP-01`'s samples (built with PROFILE's draft
  rules over the actual prompt part) plus every HARNESS recording; no budget-size corpus document is
  recorded, so the spend table prices all 16 as small. The $1 run ceiling holds: ≈ 90k input ($0.45) + *C* ≈ 10k ($0.25).

**A3.4 Citation and value grounding (I-1, I-5).** Document evidence grounds first, unchanged; then each
citation against the pinned set. `grounding.py`'s docstring gains this second declared normalisation,
valid only for norm quotes. The gate runs **before** the final run transaction (D-141); its time at the
budget size is bounded (≤ 5 s, stated at the freeze).

- **Normalisation `norm-quote-v1`, N(s):** every Unicode `White_Space` character (U+00A0, U+2007,
  U+2009, U+202F, line breaks included) → U+0020; delete U+00AD, U+200B, U+FEFF and the sequence `**`;
  collapse runs of U+0020; strip the ends. Nothing else. Set paragraphs must already be NFC (a non-NFC
  paragraph is listed and left out); the model's quote is NFC-converted before N.
- **Raw-offset mapping:** N keeps, per normalised character, the raw index it came from (a collapsed space
  maps to the first raw whitespace of its run); a match [i, j)
  maps to raw [m(i), m(j−1)+1). The stored quote is that raw substring; N(stored) = N(model quote) is
  asserted on every write. A raw span over 4,000 characters is `norm_quote_absent`.
- **Tokeniser `norm-value-v1`, T(s) over N(s):**
  - a number is an ASCII-digit run with one optional `,` or `.` fraction; thousands groups join only as
    1–3 digits then groups of exactly 3 after one space (`1 000`); LaTeX's `{,}` reads as `,`;
  - not a number: a run preceded by a letter (`м2`, `Rw52`), by `^` or `_` (with or without `{`); a token
    with two or more separators (`7.1.4`); superscripts;
  - a sign is `-`, U+2212 or `+` **immediately followed by a digit**, after the start, a space or `(`,
    and **not** after a number token plus optional space; so `1,2-1,5`, `1,2–1,5`, `1,2 - 1,5` and
    `1,2 -1,5` are all the range {1.2, 1.5}, while `−30` and `от -30` are −30;
  - a token is never adjacent to another digit, nor to a separator followed by a digit (`1,4` is not in
    `11,4` or `1,45`);
  - equality by `Decimal` (`1,4` = `1.4` = `1,40`); units and inequality words are not compared.
- **Rules per citation, in order:** label not in the set → `norm_label_unknown`; len(N(quote)) < 20 →
  `norm_quote_too_short`; N(quote) in N(labelled paragraph) → **verified**; else in exactly one other
  reliable paragraph of the same norm document → **rebound** (label kept), two or more →
  `norm_quote_ambiguous`, none → `norm_quote_absent` (a quote crossing a paragraph boundary is absent).
- **Values, after every citation passes:** each number of T(`required_value`) equals a number of T(some
  verified or rebound quote); with no number, N(`required_value`) (≥ 3 characters) is a substring of one →
  else `norm_value_not_in_quote`. `stated_value` likewise against the evidence quotes → else
  `stated_value_not_in_evidence`.
- **Any failure withholds** with the first reason — ungrounded, never merged or published, counted. Six
  reasons take the vocabulary from W56a's six to **twelve**. Publication writes each citation as a
  `finding_observation_norm_citation` row (`npar_`, raw offset and length, raw quote, state).
- **Required cases (CITE):** each bullet above, and NFD input; NBSP inside a number; a soft hyphen; `**`
  inside a quote; a table quote with and without `|`; LaTeX `3{,}5` and `м^{2}`; `м2`; `7.1.4`; `1 000`;
  the four range spellings and `−30`; `1,4` against `11,4`; a match at a paragraph's start and end; a
  quote crossing a paragraph boundary.

**A3.5 The report — `getRunNormVerification`.** Composed at read time: snapshot and set identity; per
published finding its citations (canonical and members) and states; withheld observations by reason;
`textless_pages`, not read. Roles `_ANY_ROLE`, as `listRunFindings` (R-80). A v1 or v2 run → `not_found`;
a v3 run always answers, `partial` with the stage's typed error when a stage failed (FS-04). W57b adds
the references part.

**A3.6 Contract, storage and hand-written lists — `W57A-SEAL-01`.**

- **Contract:** `getRunNormVerification` (`GET /runs/{run_id}/norm-verification`, description states the
  R-80 rule, D-151); `NormCitation` (`norms_snapshot_id`, `norm_document_id`, `norm_paragraph_id`,
  designation, title, `clause_number`, `page_label`, quote ≤ 4,000, `state` `verified|rebound`,
  `source_attribution`, NORM-Q04); `NormVerificationReport` with withheld counts keyed by an
  `UngroundedReason` enum of twelve; `FindingObservation.norm_citations`, `required_value`,
  `stated_value` and the `Finding`/`FindingDetail` restatements, **absent, never null** on v1 and v2;
  `FindingCategory` + 5 (twelve); `RunStatus.norm_retrieval_set_id`; the `nrs_` identifier;
  `setCurrentNormSnapshot` and `reauditRun` may answer `required_norm_unavailable` (with
  `reference_kind` `norm_retrieval_set`). **No new error code.**
- **Registry:** `text_analysis` optional `norms.snapshot`, `stage_version` 1.1.0.
- **Migration `0023_norm_citations`:**
  - `norm_retrieval_set` (`nrs_` id; map digest; reviewed content key; `ns_`; embedding build;
    `builder_version`; state `verified|rejected` with the expected and observed digests; set and catalogue
    blob ids, SHA-256 and sizes; prompt-part characters; UNIQUE (map digest, `ns_`, build,
    `builder_version`) `WHERE state = 'verified'`, so a mistyped `--expect` uses up no identity;
    append-only);
  - custody: `ck_norm_custody_role_shape` replaced so that roles `norm_retrieval_set` and
    `norm_catalogue` map to `target_kind` `norm_retrieval_set` (W54's generic `target_kind`/`target_id`;
    `target_id` an `nrs_` id, checked by `publish_bindings`), with no document anchor;
  - `audit_run.norm_retrieval_set_id` (foreign key), added to the frozen columns (trigger recreated as
    `0017:22-36`);
  - `finding_observation.required_value`, `stated_value` (NULL-able, 1–200, both or neither);
  - `finding_observation_norm_citation` (append-only as `finding_evidence`; quote 20–4,000 characters,
    `char_length = char_length(quote)`);
  - the two category CHECKs (`0002:900, 946`) and the ungrounded-reason CHECK widened by `ALTER`.
- **Custody-role list:** `norms/custody/roles.py` (two entries), `ck_norm_custody_role_shape`,
  `NORM_CORPUS_CUSTODY.md` (roles section), the role-set cases in `tests/integration/norms/custody/**`,
  `infra/deploy/reset.sh` (role rationale) with `tests/integration/composition/test_reset_script_refusals.py`.
- **Category list:** `api/schemas/models.py:363`; `api/routers/handlers.py:157-158` (`_ENUM_VALUES`);
  `web/src/entities/expert-decision/model/category-labels.ts:20-23`;
  `web/src/widgets/finding-list/ui/finding-list.tsx:46`;
  `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx:39-43` (`CATEGORY_CHOICES`);
  `web/tests/guards/rendered-language.guard.test.ts:1698-1709`; the generated client;
  `analysis/text/prompt.py:41` stays two.
- **Reason list:** `0003`, W56a's migration, `0023`; `P02_SEAMS.md` §5.1; `findings/grounding.py`;
  `tests/integration/findings/test_ungrounded_vocabulary_is_enforced.py`;
  `tests/integration/analysis/test_ungrounded_reason_vocabulary.py`;
  `tests/integration/db/test_open_items_migration.py`.
- **Identifier list (`nrs_`):** `contracts/domain/v1/identifiers.json`, `shared/identity/ids.py`,
  `tests/integration/db/test_schema_shape.py` (the identity CHECK).

**A3.7 Screens.** Finding detail: «Норма» — designation and title, «п. {clause}», the quote, «требование» /
«в проекте», «пункт уточнён по цитате» when rebound, the attribution, «Открыть норму» (W55a's norm view,
`#page=<page_label>`). Finding list and knowledge-base filter: the five labels. Run page: «Проверка по
нормам» — set and snapshot identity, withheld by reason, pages not read.

**A3.8 Quality, recordings and spend (H-5, I-10, I-11, K-10).**

- **Generator:** per normative category three archetype families — a violating stated value, a near-miss
  control, an inapplicable-norm control — **15**; ≥ 3 seeded issues per category (**≥ 15**) over ≈ 6
  normative documents; the **v3 corpus** adds W56a's ≈ 10 v2 documents: **≈ 16**.
- **Fixtures (I-11),** produced by RETRIEVAL's command from the promotion database and committed under
  `fixtures/evaluation/ar_v3/`: `retrieval_set.json`, `norm_rows.json`, `catalogue.json` and `DIGESTS`.
  Ceiling 10 MiB uncompressed, else gzip (`mtime=0`). The v3 evaluation fixture loads them into the
  gate's database.
- **Matcher:** any member of a group matching a seeded issue, with a citation of that member resolving
  to the expected document; controls count false positives; withheld and truncated counted; recall per
  category for all twelve.
- **Gate:** `tests/integration/evaluation/test_ar_v3_no_regression.py` beside v2's: v3's aggregate recall
  and false-positive rate against its baseline; the v2 categories under v3 not below v2 (tolerance at the
  freeze).
- **Spend** (`reviews/W57A-SPEND.md`; opus $5/$25 per MTok, `W56-PLAN.md` §A3.8):

  | Item | Estimate |
  | --- | --- |
  | small v3 document: v2's $0.08–0.115 + prompt part ≤ 10k tokens ($0.05) + citation output 0.5–1k ($0.0125–0.025) | $0.1425–0.19 |
  | v3 corpus once, ≈ 16 documents | $2.28–3.04 |
  | `CAP-01`: 3 samples (≈ 90k input, ≤ 4k output each) | ≈ $1.65 |
  | live acceptance (P5b) | ≈ $0.2 |
  | **first pass** | **$4.13–4.89** |
  | one full re-record after FIX | + $2.28–3.04 → **$6.41–7.93** |

  **Ceiling $8 (K-10):** one full re-record fits; a **second re-record is a stop**. The ledger re-projects
  after `CAP-01` and after the corpus pass; a projection above $8 stops for the owner.

**A3.9 The stand (CD-3 P5, CD-16…CD-18).** The build runs through a forced-command verb because the
integrator has no stand shell and a deploy-time or API-driven build would turn a ref push or a request
into a data write.

- **Verbs**, added by `W57A-STANDOPS-01` to W54's inbound dispatcher `infra/deploy/receive-bundle.sh`
  (with `infra/deploy/lib/forced-command.sh`):
  - `^retrieval-set-build (ap_[0-9A-HJKMNP-TV-Z]{26}) (ns_[0-9A-HJKMNP-TV-Z]{26}) ([0-9a-f]{64}) ([0-9a-f]{64}) ([0-9a-f]{64})$`
    (v3's profile id, snapshot, map digest, set and catalogue SHA-256): refuses while an import lock is held or when the
    deployed map digest differs; runs the build command (§A3.2) in a one-shot `api` container and prints
    the report;
  - `^retrieval-set-report (ap_[0-9A-HJKMNP-TV-Z]{26})$` (read-only): every set row (identity, state, digests, binding states)
    and `ready: yes|no` — a verified row for (map digest, current snapshot, deployed builder version).
    Used only after P5a deploys.
- **P5a — `W57A-INT-MAIN-01`** (owner instruction naming the SHA), CD-16's sequence:
  0. **Pre-push check (CD-18):** through an administrator account the owner names, `listNormSnapshots`
     shows the map's reviewed `ns_` with its content key, qualified; else **stop before anything else**.
  1. The exact-SHA full gate (`GATE OK`).
  2. Inside an agreed window (K-5), the K-6 copy through W54's copy key: `dump-db` → `inventory-s3` →
     `fetch` → test restore here at W56a's head →
     `attest <STAMP> <dump-sha256> <restore-report-sha256> publish <sha>` (W54; `deploy.sh` then accepts
     exactly that SHA).
  3. Push `origin/main` (fast-forward).
  4. Workflow and `verify-deployed.sh`.
  5. `resume`. The profile stays v2.
  - Failure: a forward fix, or the owner-ordered `restore-db <STAMP> <sha256>` → a reviewed revert
    (`MAIN_AUTODEPLOY_POLICY.md`) → `resume`. `0023` is forward-only.
- **P5b — `W57A-STAND-SET-01`** (owner instruction naming the deployed SHA and the `DIGESTS` values):
  1. `retrieval-set-build` with the reviewed `ns_`; the report shows a `verified` row and both bindings
     confirmed. A `rejected` row is a stop; v2 keeps serving and the row never pins.
  2. If the reviewed snapshot is not current, an administrator activates it (W55a's setter).
  3. `retrieval-set-report` for v3's `ap_` id shows `ready: yes` — the precheck for the switch.
  4. **Owner act (CD-17):** `AUDITMANAGER_ANALYSIS_PROFILE_ID` set to v3's `ap_` id in the host-owned
     `provider.env`, then an api restart; checked on a new run's `RunStatus` (`analysis_profile_id` v3's,
     `norm_retrieval_set_id` the verified row).
  5. Live acceptance (below).
  - Rollback: the same owner act back to v2's `ap_` id; rows and bindings stay (runs pin them).
  - P5b writes only new blobs and append-only rows: it needs no quiesced stand and no copy, and runs with
    **no open copy record**; no migrating publication runs during it.

### A4. Tasks

**`W57A-RULE-01`** (integrator) records, under the next free numbers (≥ R-120): norms in the same call,
citations by label, quote and value, any failure withholds (I-1, I-5); the reviewed map, offline vectors,
no run-time embedding (I-2, I-8); the five categories with applicability and the fire-safety scope (I-4,
K-2, CD-5); the split and order (I-9, I-12); the $8 ceiling with one re-record (K-10); norm text in
fixtures (I-11); the stand acts, the owner's profile switch and the K-6 copy (CD-3, CD-16, CD-17, K-6).

**`W57A-FREEZE-01`** (integrator): the standard form, plus W56a closed; the base `origin/dev` SHA; the
promotion database's reviewed snapshot (`ns_`, key, build) and, if W55a reached the stand, the stand's;
W54's BGE image digest; the migration slot; `pin_sweep.py reseal-surface migration table error-code` and
`--check` on every task file; a `git grep` of the actual predecessor `VERSION`; the ledger at $8; the
re-measure tolerance; the gate-time bound; ports; the disk and memory peaks here and on the stand (CD-12,
CD-21); the W55b budget-test file name; the two-snapshot fixture. No blanket `norms/**` or `runs/**`
write grant follows from this list.

**Stage A** (from the freeze SHA):

- **`W57A-MAP-01`** (§A3.1; host window; **light acceptance**) — Allowed:
  `src/auditmanager/analysis/profiles/ar_v3/norm_map/**` (new), `tools/norms/query_vectors/**` (new),
  `tests/contract/norm_map/**` (new: shape, provenance digests, no number in an item text, vector
  dimension, unit norm, every target resolved or listed), `docs/program/W57A-MAP-01.md`. Reads the
  promotion database, writes no table. Required: the review list with the excluded items; the vectors
  reproduced by a second run; span sizes and the estimated prompt part.
- **Owner review (I-8):** the integrator hands over the list; a change is a re-run. No review within 5
  working days is a schedule stop.
- **`W57A-SEAL-01`** (§A3.6; **full gate**) — the contract, registry, `0023`, the four hand-written
  lists of §A3.6, the role register (`api/security.py` lines; `tests/integration/api/test_role_register.py`),
  `web/src/shared/api/catalog-message.ts` (the reference-kind sentence),
  `src/auditmanager/api/schemas/findings.py` (`ObservationView`; absent, never null),
  `P02_SEAMS.md` §4, §5.1, §7 with `tests/contract/domain_p02/test_seam_register.py`, every port signature
  the lanes need. Allowed: `W56A-SEAL-01`'s final grant with `<date>_0023_norm_citations.py`, **minus**
  W56a-only items and **minus** `tests/contract/norm_map/**`, plus the files named here and every path
  `pin_sweep.py` prints; `docs/program/W57A-SEAL-01.md`. Not
  `tests/integration/findings/test_ungrounded_vocabulary_is_enforced.py` (CITE's). Required: fresh upgrade;
  upgrade from W56a's head with rows; refused downgrade; v1 and v2 byte-identical.

**Stage B** — sequential, each from the previous merge:

1. **`W57A-RETRIEVAL-01`** (§A3.2; **full gate**) — `src/auditmanager/norms/retrieval/**` (new),
   `src/auditmanager/norms/{public,__init__,__main__}.py` (export lines; the command),
   `src/auditmanager/norms/current_snapshot.py` with `tests/integration/norms/test_current_snapshot.py`
   (the guard; W55a's names, re-swept), `src/auditmanager/bootstrap/{adapters,composition}.py`,
   `fixtures/evaluation/ar_v3/{retrieval_set.json,norm_rows.json,catalogue.json,DIGESTS}` (new),
   `tests/integration/norms/retrieval/**` (new), `docs/program/W57A-RETRIEVAL-01.md`. Required: equal
   input → equal digest, the replay; a mismatch → a `rejected` row that never pins; a new builder version
   → a new identity; fixtures reproduced byte for byte; `math.fsum` ranking and the tie-break; windows
   resolved only to reliable paragraphs; clause, table and range rules with `**`/`#` captions; the
   ceiling and the reduction order; non-NFC listed; unreviewed key or `ns_` refused; a non-current
   qualified `ns_` builds; custody interrupted at each point and settled; the single transaction; the
   guard refusing atomically, then activation with one event; build time and memory measured.
2. **`W57A-CAP-01`** (§A3.3; integrator; **light acceptance**) — the three samples inside the ledger; *C*
   and the document budget; the prompt part's measured tokens ≤ 10,000. Stops: a sample above 170 s;
   *C* < 6,000; a ceiling breach after the reduction order.
3. **`W57A-STANDOPS-01`** (§A3.9; **full gate**) — `infra/deploy/receive-bundle.sh`,
   `infra/deploy/lib/forced-command.sh`, `tests/integration/composition/test_bundle_transport_refusals.py`,
   `docs/program/DEPLOYMENT_RUNBOOK.md` (retrieval-set section), `docs/program/W57A-STANDOPS-01.md`.
   Required: a refusal per guard and grammar violation; the report read-only; the build refused on a map,
   key or lock mismatch; `shellcheck`.
4. **`W57A-PROFILE-01`** (§A3.3; **full gate**) — `src/auditmanager/analysis/profiles/**` (the v3 entry;
   not `norm_map/`), `src/auditmanager/analysis/text/{profile,prompt,response,stage,provenance,artifact,recorded,__init__}.py`,
   `src/auditmanager/analysis/{public,__init__}.py`,
   `src/auditmanager/runs/{executor,commands,repository,scope,public,__init__}.py`,
   `src/auditmanager/bootstrap/{adapters,composition}.py`, `docs/program/P02_SEAMS.md` §9.2 and §9.4 with
   `tests/contract/domain_p02/test_seam_register.py` (`:251-273`), `tests/integration/analysis/profiles/**`,
   `tests/integration/runs/test_input_budget.py` (W55b's, re-swept), `tests/integration/runs/test_v3_start.py`
   (new), `tests/integration/runs/test_v3_reaudit.py` (new), `docs/program/W57A-PROFILE-01.md`. Required:
   only the run's labels in the prompt; the schema's citation rules; v3's bundle carries *C* while v1 and
   v2 bodies stay byte-identical; v3 start refused without a verified set or current snapshot; the pin;
   the budget counting the prompt part; `RunStatus.norm_retrieval_set_id` on v3 only; `UNEVALUATED_GUARDS` and §9.2/§9.4 rewritten (the
   NormsSnapshot clause evaluated for norms-reading profiles; `required_norm_unavailable` has a producer);
   **re-audit:** after a snapshot change it pins the current snapshot and verified set and records them, a
   missing one refuses before dispatch, a v2 source under v3 becomes v3, the fingerprint replays;
   `frozen_input_digest` checked on both paths.
5. **`W57A-CITE-01`** (§A3.4, §A3.5; **full gate**) —
   `src/auditmanager/findings/{grounding,publication,queries,artifacts,public,__init__}.py`,
   `src/auditmanager/runs/executor.py`, `src/auditmanager/norms/{public,__init__}.py`,
   `src/auditmanager/bootstrap/{adapters,composition}.py`, `src/auditmanager/api/routers/runs.py`,
   `tests/integration/findings/**` (with `test_ungrounded_vocabulary_is_enforced.py`, twelve values, and
   `TestTheUngroundedVocabularyIsClosed`, `test_grounding_gate.py:679`),
   `tests/integration/api/test_norm_verification_read.py` (new), `docs/program/W57A-CITE-01.md`. Required:
   §A3.4's cases; one failed citation among three withholds; never merged when withheld; the raw substring
   stored; the report and `partial`; a role-less account refused; the gate-time bound; v1 and v2
   unchanged.
6. **`W57A-GENERATOR-01`** (§A3.8; **light acceptance**) — `tools/fixtures/seeded/**`,
   `fixtures/evaluation/ar_v3/**` (the corpus, not RETRIEVAL's files), `tests/contract/fixtures_seeded/**`,
   `docs/program/W57A-GENERATOR-01.md`. Required: byte-stable regeneration; a mutation self-test per
   archetype.
7. **`W57A-HARNESS-01`** (§A3.8; live inside the ledger; **full gate**, `conftest.py`) —
   `tools/evaluation/**`, `tests/contract/evaluation/**`,
   `tests/integration/evaluation/{test_ar_v3_no_regression.py,conftest.py}`,
   `fixtures/recorded/text_analysis/ar_v3/**` (new), `fixtures/evaluation/ar_v3/baseline.json`,
   `docs/program/reviews/W57A-SPEND.md`, `docs/program/W57A-HARNESS-01.md`. Required: the gate red on a
   lost seeded issue, a one-digit quote change and an inapplicable citation; ≥ 1 rebound and ≥ 1 withheld
   case, recorded or from labelled mutated recordings (`mutated: true`); every latency ≤ 170 s;
   truncations counted; the prompt part's tokens from usage; gate ≤ 2 min.
8. **`W57A-WEB-01`** (§A3.7; **light acceptance** with the live journey) —
   `web/src/widgets/{finding-list,knowledge-base,run-progress}/**`,
   `web/src/entities/{finding,finding-observation,audit-run}/**`, `web/src/_pages/{review,run,knowledge-base}/**`,
   `web/src/shared/api/{query-keys,index}.ts`, `web/tests/unit/{review,run,widgets,screens}/**`,
   `web/tests/guards/{prepared-sections,rendered-language}.guard.test.ts` (entries),
   `web/tests/unit/styles/screens.ts`, `tests/e2e/pc01/journey/manifest.json`, `docs/program/W57A-WEB-01.md`.
   Required: rebound marked; the values; «Открыть норму»; the withheld panel; 780 px with a 4,000-character
   quote; lint and typecheck.

**Stage C:** **`W57A-REHEARSAL-01`** (host window, recorded; **light acceptance**) — a disposable stand
here with the promotion snapshot: P5a's copy steps, P5b's verbs, the build, a `rejected` then a verified
row, the activation guard, the owner-act switch and its rollback, v3 runs over the v3 corpus, a re-audit after a snapshot change;
time, disk and memory measured. Allowed: `scripts/rehearsal/w57a/**`, `docs/program/W57A-REHEARSAL-01.md`.
**`W57A-RELNOTES-01`** (**light acceptance**; §8.4, R-86) — `release-notes/<target>.json`,
`release-notes/dictionary.json`, `VERSION`, the freeze's `VERSION` hits, `docs/program/W57A-RELNOTES-01.md`.

**Stage D:** `W57A-QA-01`, `W57A-JUDGE-X` (security), `W57A-JUDGE-Y` (lineage and reproducibility),
`W57A-NOTES-JUDGE`, `W57A-FIX` (a prompt change re-records inside the ledger; §A3.8's stop). The
JUDGE-X/Y checklists are `33fe3f7:docs/program/dispatch/W57-PLAN.md:705-712`, copied into the task files
at the freeze.

**`W57A-INT-CLOSE`** registers: corpus refresh (§A3.2's order); normative context for drawings and chunks
(W56b); semantic retrieval from document text (D-2.4); insolation after beta; СП 2/4.13130 checks once
those codes join the corpus. **`W57A-INT-MAIN-01`** (P5a) and **`W57A-STAND-SET-01`** (P5b; depends on
P5a), each on its own instruction (§A3.9). Live acceptance in P5b: one seeded normative document under
v3 yields **at least one verified citation**, its report and its screen; rebound and withheld are proven
by HARNESS and the rehearsal. The tag follows §8.4 and R-86.

### A5. Serial hotspots (W57a)

Every path is held by one lane at a time, in this order: `bootstrap/{adapters,composition}.py` SEAL →
RETRIEVAL → PROFILE → CITE; `norms/{public,__init__}.py` RETRIEVAL → CITE; `runs/executor.py` PROFILE →
CITE; `findings/artifacts.py` CITE (W57b: NORMREFS); `P02_SEAMS.md` and `test_seam_register.py` SEAL →
PROFILE; `rendered-language.guard.test.ts` SEAL (seeds) → WEB (entries); refs, tags, the stand acts and
`.local/**` the integrator.

### A6. Estimate (W57a)

Freeze 2.0; MAP 5.0; SEAL 7.0; RETRIEVAL 7.5; CAP 1.5; STANDOPS 3.0; PROFILE 6.0; CITE 7.5; GENERATOR 4.5;
HARNESS 5.0; WEB 4.5; merges 4.5; rehearsal 2.0; release notes 0.5; judging 2.5; FIX 4.0; close 1.0 —
**68 h**, plus 5 h contingency — **≈ 73 h**, P50 ≈ 13.8 working days at ≈ 5.3 active hours a day, **P80 ≈
18.6**. **Outside:** the owner's review, host windows, `R-29` stops, and the stand acts — P5a ≈ 3–4 h
(gate, copy in the window, push, verification, resume), P5b ≈ 1.5 h.

### A7. Stop conditions (W57a)

`W48-PLAN.md` §14, plus: a projection above $8 or a second re-record; a latency above 170 s; *C* < 6,000;
the prompt part above 10,000 tokens after the reduction order; more than 50,000 candidate windows; a
category left without a clause after the review; fixtures not reproduced byte for byte; v1 or v2 not
byte-identical; v3's recall on the v2 categories below v2's; a stored quote other than a raw substring of
canonical text; a `rejected` set row on the stand; the pre-push check failing; the gate time above its
bound.

### A8. Non-goals (W57a)

`normative_refs` and Excel (W57b); a second paid stage; run-time embedding on the stand; calculations;
insolation and the СП 2/4.13130 checks; normative context for drawings or chunks (W56b); absolute quality
thresholds (W58); the owner's export review (W57b).

---

## Part B — W57b: the project's own references and Excel

### B1. Objective

- **`normative_refs`**, the thirteenth category: each norm the document cites is resolved against the
  pinned snapshot's catalogue without a model — «есть в корпусе»; «в корпусе есть более новая редакция:
  …» (a finding); «в корпусе только более ранняя редакция»; «нет в корпусе»; «не сопоставлено» — all but
  the second information (I-3, I-6).
- **Excel** in legacy's layout, export only (I-7); the CSV unchanged.
- No paid stage and no stand data write (the catalogue came with P5b). Spend ≤ $5 (≈ $1.0).
- The owner's export analysed with v3.1 after the close, gating nothing.

### B2. Where it starts

W57a's results and the verified set row's catalogue; `norm_verification` as declared
(`stage-registry.json:658-708`); the CSV export and its download-name rule (`api/routers/export.py`;
`bootstrap/adapters.py:1057` `CsvExportAdapter.export_run_csv`;
`tests/integration/exports/test_the_download_name_has_one_source.py`); the hook
`web/src/features/export-run/model/use-export-run.ts:44-50` with `csvFileName`
(`web/src/shared/api/csv-columns.ts:53`); the BFF forwarding `content-disposition`
(`web/src/shared/api/credentialed-forward.ts:62-66`; moves, W55a); the observation's mode readers
`web/src/widgets/evidence-viewer/ui/evidence-viewer.tsx:123-124` and
`web/src/entities/finding-observation/model/pages.ts:63-72`; law slugs
(`Федеральный_закон_от_22_07_2008_N_123-ФЗ_(ред__от_25_12_2023…`, the dotted `СП_1.13130.2020`); `soffice`
on this host.

### B3. Design

**B3.1 The stage.** `norm_verification` becomes deterministic: `model_routed: false`, still
`remote_eligible`; inputs `prepared.text_layer` (new), `findings.merged` (kept, order only) and
**`norms.catalogue`** (new role, replacing `norms.snapshot` on this stage), resolved by the executor from
the run's pinned set row; outputs `norms.verification_report` and a new observation role (passed through
`findings/artifacts.py`); `stage_version` **2.0.0**; `legacy-stage-map.json` LSD-03 and LSD-20 (`:58,
413`) annotated. **Profile v3.1** (its `ap_` id named at the seal) = v3 plus `norm_verification`, the
**same prompt bundle**, so requests and recordings are byte-identical.

**B3.2 Families, extraction and the twin.**

- **Families** (`norms/references/families.json`): how a designation and its edition are written —
  `СП 54.13330.2022`, `ГОСТ 21.101-2020`, `ГОСТ Р …`, `СНиП 31-01-2003`, `СанПиН 1.2.3685-21`, `ВСН …`;
  laws and acts by number (`123-ФЗ`, `ФЗ-123`, `Федеральный закон № 123-ФЗ`; `ПП РФ № 87`,
  `Постановление Правительства РФ № 87`). **Amendments** («Изменение N 3 к СП 51.13330.2011») parse as
  an amendment of their base, never as an edition. Every catalogue slug parses or is listed.
- **Extraction:** regex over the text layer of pages that have one; each occurrence a span.
- **The twin:** the corpus side uses the catalogue's SQL tokens; the text side a Python twin of
  `norm_designation_tokens`, proven equal in the gate's database on the 674 catalogue slugs and on
  generated designations (dots, NBSP, en and em dashes, «№», `*`, Latin homoglyphs).

**B3.3 Outcomes and provenance.** Per distinct cited designation: the same edition → «есть в корпусе»; a
newer edition (wins over the same) → **one `normative_refs` observation** from the template «Проект
ссылается на {cited}; в корпусе есть более новая редакция: {newest}», evidence the occurrences (≤ 10),
**no proposed severity**; only older → «в корпусе только более ранняя редакция»; family and base absent →
«нет в корпусе»; unparsed → «не сопоставлено». Singleton groups, published after the gate. Provenance:
`stage_id` `norm_verification`; `provider_mode` the run's own; `model_call_id` absent; `prompt_bundle_id`
the profile's; **`rule_id`** `normative_refs.newer_edition/1`.

**B3.4 The report.** `getRunNormVerification` gains the optional `references` part: each designation, its
outcome, occurrences and the pages not read.

**B3.5 Excel (I-7).** `exportRunXlsx` — `GET /runs/{run_id}/export.xlsx`, `exportRunCsv`'s states and role
(`_EXPERT`), the spreadsheet media type, the file name from the CSV's single source. «Сводка»: counts by
the five severities (decided; proposed when undecided) and by category; run identity (project, version,
run, profile, snapshot key, attribution). «Замечания»: № | Лист/стр. | Категория | Замечание |
Рекомендация | Серьёзность (решение эксперта) | Серьёзность (предложение модели) | Норма (документ,
пункт) | Цитата нормы | Решение эксперта | Комментарий — one row per finding, citations one per line,
members as «также найдено» rows, rows coloured by severity, header frozen, widths fixed. Writer
`exports/xlsx/**`: standard library, `ZIP_STORED`, fixed part order and timestamps; XML-forbidden
characters → U+FFFD, counted; no field reaches 32,767 characters; no `<f>` element. Probe: every sheet
through `soffice --headless` under its own `-env:UserInstallation`, compared cell by cell.

**B3.6 Contract, storage and lists — `W57B-SEAL-01`.**

- **Contract:** `exportRunXlsx`; `NormVerificationReport.references`; `FindingCategory` + `normative_refs`
  (thirteen); `ObservationProvenance.rule_id` (optional, absent never null); **`ProviderMode` untouched**.
- **Role register:** `exportRunXlsx: _EXPERT` and its sample.
- **Registry:** §B3.1.
- **Migration `0024_norm_references`:** the category CHECKs widened; `finding_observation.rule_id text
  NULL` with a format CHECK and `CHECK (rule_id IS NULL OR model_call_id IS NULL)`.
- **Category list** (as §A3.6): `api/schemas/models.py:363`; `api/routers/handlers.py:157-158`
  (`_ENUM_VALUES`); `category-labels.ts:20-23`; `finding-list.tsx:46`; `knowledge-base-page.tsx:39-43`
  (`CATEGORY_CHOICES`); `rendered-language.guard.test.ts:1698-1709`; the generated client.
- **No new error code;** a stage failure uses the deterministic stages' code, named at the seal.

**B3.7 Screens.** Run page: the references with five outcomes. Finding detail: cited and newer edition,
«Открыть норму», no «предложено моделью». Evidence viewer: «по правилу» for a rule-made observation, never
«живой вызов» or «из записи»; run-level badges unchanged. Export panel: «Скачать Excel».

**B3.8 Spend.** No recording (v3.1's requests equal v3's). Live acceptance ≈ $0.2, the owner's export
≈ $0.75 — **≈ $1.0** against $5.

### B4. Tasks

**`W57B-RULE-01`** (integrator), under the next free numbers: `normative_refs` by the catalogue only, the
newest edition, five outcomes (I-3, I-6); Excel export only (I-7); rule-made observations by `rule_id`.

**`W57B-FREEZE-01`** (integrator): the standard form, plus the migration slot; `pin_sweep.py
reseal-surface migration error-code`; the actual predecessor `VERSION`; ports; the stand state through
`retrieval-set-report` **if P5b has run, else recorded as pending** (checked again at INT-MAIN).
**depends_on:** `W57A-INT-CLOSE`; INT-MAIN also `W57A-STAND-SET-01`.

**Stage A: `W57B-SEAL-01`** (§B3.6; **full gate**) — `W57A-SEAL-01`'s final grant with
`<date>_0024_norm_references.py`, minus W57a-only items, plus `contracts/analysis/v1/legacy-stage-map.json`,
`src/auditmanager/api/routers/handlers.py`, `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`,
the category list's files, every path `pin_sweep.py` prints, `docs/program/W57B-SEAL-01.md`. Required: as
W57a's seal; `ProviderMode` byte-identical in `openapi.json`.

**Stage B** — sequential:

1. **`W57B-NORMREFS-01`** (§B3.1–§B3.4; **full gate**) —
   `src/auditmanager/analysis/stages/{norm_verification,__init__}.py`,
   `src/auditmanager/analysis/{public,__init__}.py`, `src/auditmanager/analysis/profiles/**` (v3.1),
   `src/auditmanager/norms/references/**` (new), `src/auditmanager/norms/{public,__init__}.py`,
   `src/auditmanager/runs/executor.py`,
   `src/auditmanager/findings/{artifacts,publication,queries,public,__init__}.py` (and `grounding.py` if
   the gate's entry point changes), `src/auditmanager/bootstrap/adapters.py`,
   `src/auditmanager/api/routers/runs.py`, `tests/integration/norms/test_token_twin.py` (new),
   `tests/integration/analysis/norm_verification/**` (new), `tests/integration/findings/**` (singleton
   cases), `docs/program/W57B-NORMREFS-01.md`. Required: every slug parsed or listed; amendments never
   editions; the twin equal; each outcome by a case, the newer edition winning; both law word orders; ≤ 10
   occurrences; no proposed severity; `rule_id` present, `provider_mode` the run's; `partial` on a failed
   stage; v3 unchanged.
2. **`W57B-XLSX-01`** (§B3.5; **full gate**) — `src/auditmanager/exports/xlsx/**` (new),
   `src/auditmanager/exports/{__init__,service,query}.py`, `src/auditmanager/api/routers/export.py`,
   `src/auditmanager/bootstrap/adapters.py`, `tests/integration/exports/xlsx/**` (new),
   `docs/program/W57B-XLSX-01.md`; not `api/routers/ports.py`. Required: equal bytes; no `<f>`; U+FFFD; the
   «также найдено» rows; multi-citation cells; the probe; the CSV byte-identical; the download-name test.
3. **`W57B-WEB-01`** (§B3.7; **light acceptance** with the live journey) —
   `web/src/widgets/{run-progress,export-panel,finding-list,evidence-viewer}/**`,
   `web/src/features/export-run/**`, `web/src/shared/api/{xlsx,index}.ts`,
   `web/tests/guards/dashboard-invalidation.guard.test.ts` (one entry if a hook file is added),
   `web/src/entities/{finding,finding-observation,audit-run}/**`, `web/src/_pages/{review,run}/**`,
   `web/tests/unit/{review,run,export,widgets,screens}/**`, `web/tests/guards/rendered-language.guard.test.ts`
   (entries), `web/tests/unit/styles/screens.ts`, `tests/e2e/pc01/journey/manifest.json`,
   `docs/program/W57B-WEB-01.md`. Not edited: `web/src/shared/ui/run-state-badge.tsx`,
   `web/src/entities/audit-run/model/run-presentation.ts`. Required: «по правилу» and the mode label; lint
   and typecheck.

**Stage C:** `W57B-REHEARSAL-01` (recorded; **light acceptance**) — the v3.1 corpus, references, Excel
through `soffice`; `scripts/rehearsal/w57b/**`, `docs/program/W57B-REHEARSAL-01.md`.
`W57B-RELNOTES-01` (**light acceptance**; §8.4, R-86) — as W57a's.

**Stage D:** `W57B-QA-01`, `W57B-JUDGE-X`, `W57B-JUDGE-Y`, `W57B-NOTES-JUDGE`, `W57B-FIX`; the checklists
are `33fe3f7:docs/program/dispatch/W57-PLAN.md:1003-1006`, copied into the task files at the freeze.

**`W57B-INT-CLOSE`** registers: document status data; Excel re-import; references on raster pages; norm
maps for other sections (W59's S0); no rule marker in the CSV; the precision figure.

**`W57B-INT-MAIN-01`** (owner instruction naming the SHA; depends on `W57A-STAND-SET-01`), CD-16's
sequence: (0) `retrieval-set-report` for v3 shows `ready: yes` with a confirmed catalogue binding, and a
recent run records v3's `ap_` id; (1) the exact-SHA full gate; (2) in an agreed window, the K-6 copy for `0024`
(`dump-db` → `inventory-s3` → `fetch` → test restore here at W57a's head → `attest <STAMP>
<dump-sha256> <restore-report-sha256> publish <sha>`); (3) push; (4)
workflow and `verify-deployed.sh`; (5) `resume`; (6) **owner act:** v3.1's `ap_` id in `provider.env` and an
api restart, checked on a new run's recorded profile; (7) live acceptance — a newer-edition finding, the
five outcomes, the Excel file downloaded and opened. Failure: as P5a; profile rollback by the owner act
back to v3's. The tag follows §8.4 and R-86.

**`W57B-OWNER-REVIEW-01`** (after the close; gates nothing): the owner's export under v3.1, marked by the
owner; precision as `W56-PLAN.md` §A3.7.

### B5. Serial hotspots (W57b)

`bootstrap/adapters.py` SEAL → NORMREFS → XLSX; `findings/**`, `runs/executor.py`, `analysis/**`,
`norms/{public,__init__}.py` NORMREFS; `exports/**` (but `serializer.py`), `api/routers/export.py` XLSX;
web files WEB.

### B6. Estimate (W57b)

Freeze 1.5; SEAL 4.5; NORMREFS 7.5; XLSX 5.5; WEB 4.0; merges 2.5; rehearsal 1.0; release notes 0.5;
judging 2.0; FIX 3.0; close 1.0 — **33 h**, plus 3 h contingency — **≈ 36 h**, P50 ≈ 6.8 working days,
**P80 ≈ 9.2**. **Outside:** INT-MAIN ≈ 3 h (gate, copy in the window, push, resume, switch).

### B7. Stop conditions and non-goals (W57b)

Stops: `W48-PLAN.md` §14, plus the twin disagreeing with the SQL function; any output saying a norm is
cancelled or replaced; the `soffice` probe disagreeing on a cell; v3 runs or the CSV not byte-identical;
`ProviderMode` changed. Non-goals: document status data; Excel re-import; references on raster pages;
calculations; CSV changes.

---

## Common sections

### C1. Integration order

1. `W57A-RULE-01`, `W57A-FREEZE-01`; Stage A: MAP ∥ SEAL; the owner's review; merge SEAL, then MAP.
2. Stage B: RETRIEVAL → CAP → STANDOPS → PROFILE → CITE → GENERATOR → HARNESS → WEB; Stage C; Stage D;
   INT-CLOSE; P5a and P5b, each on its own instruction.
3. `W57B-RULE-01`, `W57B-FREEZE-01` from W57a's close; SEAL; NORMREFS → XLSX → WEB; Stage C; Stage D;
   INT-CLOSE; INT-MAIN after P5b; OWNER-REVIEW.

### C2. Amendments other plans need

- **`W55-PLAN.md`:** a norms-reading profile's refusal is `required_norm_unavailable`, not
  `no_current_norms_snapshot` (CD-19); the guard's extension of `norms/current_snapshot.py` and its
  test file are W57a's (RETRIEVAL).

### C3. Estimate together

W57a ≈ 73 h and W57b ≈ 36 h — **≈ 109 h**, P50 ≈ 20.6 working days, P80 ≈ 27.8, plus ≈ 8 h of stand acts
outside.
