# W56A-LEGACY-SOURCE-01 — recovered АР source addendum

**Task:** `tasks/W56A-LEGACY-SOURCE-01.md`. **Candidate base:** `8c5a109bd98302b64fb47b364d4c639ff63c0eda`.
This adds evidence to `W56A-PREFREEZE-01`: that report accurately observed an absent
checkout when it ran; the owner subsequently downloaded it at `/root/projects/PDF-proverka`.
No W56a freeze or implementation is declared here.

## 1. Source identity and immutable manifest

The source checkout is clean (`git status --short --branch` → `## main...origin/main`),
at `16ba8e5d23e4782550e79355002fde1365f682b7`. Historical commit
`32b9d903792b30506048a1d42b0e6b2d07aee403` is its ancestor. A six-path
`git diff --exit-code 32b9d903... HEAD -- <paths>` returns 0 with no output: these
files are byte-identical at the historical commit and downloaded HEAD. The earlier
research path included one extra `PDF-proverka/` component; the actual checkout root
is `/root/projects/PDF-proverka`.

SHA-256, line count and byte count below are from the downloaded files, in the order
used by the W56 plan. All paths are relative to that checkout root.

| Legacy path | SHA-256 | Lines | Bytes |
| --- | --- | ---: | ---: |
| `prompts/disciplines/AR/finding_categories.md` | `e0591c94b2f385a837872f37f5ef32eb057131265c32283e5f732b2c1fa236ce` | 14 | 1,712 |
| `prompts/disciplines/AR/checklist.md` | `eccb7879023a126427fd61a0ed36237eb42bbebd4bec63c4009004247d7f3179` | 61 | 5,362 |
| `prompts/disciplines/AR/role.md` | `fda944f74c4a0bd7cd77339f2c2f8519f55d59e899be03da212f93d2ad432203` | 16 | 1,592 |
| `prompts/disciplines/AR/drawing_types.md` | `38ef910c11c71d03819a37c258933bcf4c851ac2cce31bace2681d8fde8fa45e` | 21 | 2,447 |
| `prompts/disciplines/AR/project_params.md` | `5d827feac80cf85760af4a1d3f8509e15defb0df771c09ea83e475e172a80f35` | 58 | 3,079 |
| `backend/app/data/discipline_checklists/AR.md` | `1fbede99e35e8beadbb014538af76c33fdb54a7860e72616c4a4605ee28e17a9` | 119 | 8,559 |

Total: **289 lines, 22,751 bytes**. This establishes source identity, not normative
validity. The source repository was inspected read-only; it was not edited or tested.

## 2. Review map for the text-only profile

The frozen W56 plan §A3.2/§A3.4 permits seven categories: the existing
`internal_contradiction` and `explicit_placeholder`, plus `dimensions`, `layout`,
`facade`, `roof`, and `documentation`. The source categories file has **12** entries.
Its lines 3, 4, 8, 9, and 13 supply the five *names* and Russian subject cues for the
new categories, but their norm language does not become a test. Lines 5–7, 10–12,
and 14 describe `evacuation`, `fire_safety`, `accessibility`, `insulation`,
`insolation`, `sound`, and `normative_refs`; these seven categories are outside W56a.
Neither of the two existing category names occurs in the legacy table.

The legacy `checklist.md` has **46** bullet items. The partition below covers every
bullet by source line. “Exclude” means no threshold, norm obligation or inferred
missing-item finding in W56a; it does not assert that a norm is wrong.

| Lines | W56a disposition |
| --- | --- |
| 3–7, 10, 12–16, 19–25, 33–34, 37–42 (**26 bullets**) | Exclude normative minima, ratios, required presence, fire/egress, accessibility and performance claims. Norm-grounded evaluation belongs to W57. |
| 2, 29, 30, 53 (**4 bullets**) | Split only after rewrite: compare figures with another supplied project statement or table; exclude balcony coefficients, the “and norms” clause, independent thermal compliance and the ГОСТ clause. |
| 28, 31, 51, 52, 54 (**5 bullets**) | Candidate cross-document consistency checks when the compared plan, schedule or note is actually present and verbatim evidence can be cited. A bare quantity or drawing label is context, not a finding. |
| 11, 32, 45–48, 57–61 (**11 bullets**) | Descriptive context only. Do not infer that a window, entrance, roof detail, responsibility class or other element must exist from the legacy list alone. Compare only an explicit project promise with an actual supplied artefact. |

`role.md` lines 2–3 instruct norm-compliance analysis and clause-backed
recommendations; these instructions are excluded. Its topic list (9–16) is context
for extracting project claims, not authority to assert a violation.
`drawing_types.md` lines 3–21 describe **19** sheet labels. They may help describe
supplied sheets, but do not provide a drawing-recognition capability or prove a sheet
is mandatory. `project_params.md` lines 2–11 and fields 15–33 are an extraction
vocabulary; the sample zero/empty values and `building_class = "Ф1.3"` are examples,
not product defaults, missing-value evidence or a compliance verdict. A normative
reference may be quoted as a project claim, never validated from this source alone.

`backend/app/data/discipline_checklists/AR.md` has **23** `problem_class` items.
Every item is presented as mandatory, recommended or conditional under a named norm,
and its `applies=` values refer to an applicability matrix outside this six-file
bundle. No item is a general missing-item rule for W56a. The following index records
each item so the profiles lane can decide whether an explicit project manifest makes
an intra-set completeness question possible. `C` means *conditional source cue only*;
`N` means *norm/cross-discipline obligation withheld*.

| Source line | Item cue | Disposition |
| ---: | --- | :---: |
| 9 | АР explanatory note | C |
| 13 | floor plans | C |
| 16 | sections | C |
| 19 | facades | C |
| 22 | fire-safety section | N |
| 25 | evacuation section | N |
| 28 | norm-control stamp | N |
| 34 | insolation calculation | N |
| 38 | technical/economic indicators | C |
| 44 | opening schedule | C |
| 47 | finish schedule | C |
| 50 | room schedule | C |
| 56 | characteristic detail drawings | C |
| 59 | evacuation diagram | N |
| 65 | MEP opening coordination | N |
| 68 | structural coordination | N |
| 74 | finish-work acceptance instruction | N |
| 80 | finishes tied to room schedule | C |
| 83 | accessibility solution | N |
| 86 | acoustic characteristics | N |
| 92 | daylight calculation | N |
| 95 | glazing attachment detail | C |
| 98 | roof plan/detail | C |

`C` is not permission to report absence: the product needs an explicit in-scope
project list or supplied-document contradiction, with text-layer evidence. The seven
anti-pattern bullets at lines 104–118 are useful guardrails against speculative or
uncited findings. Their norm-specific severity examples do not set W56a policy; the
W56a severity proposal/decision contract comes from owner ruling H-3.

## 3. Limits and stops

- The six files have provenance, not validated legal/normative content. Current
  applicability, thresholds and clause numbers were not checked; their verification
  is outside this task and the W56a text-consistency scope.
- `checklist_applicability_matrix.md`, other legacy prompts and runtime behavior were
  not part of the six-file grant. The source `applies=` labels cannot stand alone.
- W55b acceptance, the accepted SHA, model gateway identity probes and `W56A-FREEZE-01`
  remain pending. No code lane is dispatched by this report.

## 4. Checks, contracts and changed-path proof

The source ancestry and six-file diff checks returned 0. `sha256sum` matched §1;
`wc -l -c` matched the line and byte columns. A line-marker count found 46 prompt
checklist bullets, 23 metadata checklist items and 7 anti-pattern bullets. The
post-commit `git diff --check` and exact allowed-path proof are recorded in the
handoff; only this report and its task file are changed. No contracts, migrations,
dependencies, composition roots or styles change.

## 5. Integration handoff

`W56A-FREEZE-01` should use `/root/projects/PDF-proverka` and the six digests in §1,
rechecking them when the accepted W55b SHA is known. It should preserve the §A3.4
requirement that the eventual ported files carry legacy path and SHA-256 provenance.
`W56A-PROFILES-01` should review every source item against its seven-category,
text-layer evidence contract, document every excluded norm item in its own lane
report, and avoid treating this preliminary map as implementation approval. A
source change requires a new manifest and review; no silent fallback is allowed.

Rollback is a revert of this document-only commit. There is no runtime feature flag.
