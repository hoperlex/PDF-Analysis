# W56A-INT-PROFILE-CONTENT-01 — reviewed AR v2 source corpus

**Decision:** integrate offline content preparation on `origin/dev`. This is
not `W56A-PROFILES-01`: no v2 profile ID, response schema, stage plan or
runtime consumer exists. `W56A-MODEL-PIN-01` still stops at the two-gateway
identity precondition; `P02_LOCK.json` is unchanged.

## Source review and exclusions

All six source bytes were rechecked against `W56A-LEGACY-SOURCE-01.md` §1 on
the clean legacy checkout `16ba8e5d`. The six reviewed files carry the exact
legacy path and SHA-256. Only the marked prompt block is loadable; source
provenance and review notes stay outside it.

| Source | Kept in prompt | Excluded or rewritten |
| --- | --- | --- |
| `role.md` | Lines 1, 5–11 as AR context and comparison subject names | Lines 2–3 demand norm compliance and clause citations; lines 12–16 are specialist norm topics without supplied verification evidence. |
| `finding_categories.md` | Subject cues at lines 3, 4, 8, 9, 13; two v1 names come from the W56a contract | The norm-minimum phrase on line 3 and categories at lines 5, 6, 7, 10, 11, 12, 14. No eighth category or normative-ref verdict. |
| `drawing_types.md` | All 19 labels at lines 3–21 as vocabulary | Every implication that a labelled sheet exists or is required. No drawing recognition is claimed. |
| `project_params.md` | Field names at lines 15–33 and subject names at 2–11 | Example zero/empty values, the sample building class and all examples at 37–58 as defaults, missing-value evidence or norm conclusions. |
| `backend/.../AR.md` | Conditional supplied-set cues and anti-speculation rules | All mandatory, recommended, cross-discipline and severity claims; the `applies=` matrix is not in this source set. |

The 46 bullet items in legacy `checklist.md` are individually accounted for
by their source lines below. `X` means excluded as an external minimum,
obligation or unsupported inference; `R` means rewritten into a comparison
of two explicit supplied statements; `C` means context vocabulary only,
which cannot itself produce a finding.

| Disposition | Individual source bullet lines | Reason |
| --- | --- | --- |
| X | 3, 4, 5, 6, 7, 10, 12, 13, 14, 15, 16, 19, 20, 21, 22, 23, 24, 25, 33, 34, 37, 38, 39, 40, 41, 42 | Normative minima, ratios, required presence, egress, fire, accessibility or performance claims. |
| R | 2, 29, 30, 53 | Area, height, wall construction or opening type may be compared only when a second supplied project statement exists; balcony coefficients, independent thermal compliance and norm clauses are removed. |
| R | 28, 31, 51, 52, 54 | Plan/section marks, vitrages, material marks, quantities and finish schedules are cross-document comparison cues only. |
| C | 11, 32, 45, 46, 47, 48, 57, 58, 59, 60, 61 | Descriptive nouns. They do not assert mandatory presence or an external rule. |

The 23 `problem_class` items in legacy `backend/.../AR.md` are accounted
for separately. `C` is a cue only when the supplied project explicitly
promises an artefact or contains contradictory statements; `X` cannot become
a W56a text-consistency rule.

| Disposition | Individual source item lines | Reason |
| --- | --- | --- |
| C | 9, 13, 16, 19, 38, 44, 47, 50, 56, 80, 95, 98 | Possible names of provided sheets, schedules, indicators or details; no unconditional missing-item finding. |
| X | 22, 25, 28, 34, 59, 65, 68, 74, 83, 86, 92 | Norm-grounded or cross-discipline obligations require later verification and scope. |

The anti-patterns at legacy lines 104–114 and 118–119 become general guards
against uncited speculation, phantom norm clauses and duplicate observations.
Lines 115–117's norm-specific severity example is excluded. No legacy
severity value is carried into the prompt; proposed and decided severity
remain the sealed W56a contract's separate fields.

## Implementation and checks

`content.py` pins the six reviewed-resource digests, validates each
provenance header and unique prompt-marker pair, and returns only their
marked text. Its combined full-resource hash is
`0b560e485a07f96af511e3879740d1db0a0fc3f15fc013ab63507d609e3870ee`.
Any edit to a resource requires a deliberate new digest and therefore a
new prompt/profile identity when the later consumer binds the hash.

- Six legacy `sha256sum` values matched the frozen manifest.
- Focused `test_ar_v2_profile_content.py`: **3 passed**. The test compares
  category names with the sealed OpenAPI enum, rejects norm thresholds and
  sample defaults in loadable text, and proves tamper/missing-file refusal.
- New module `compileall`: passed. Direct task governance: no findings.
- `git diff --check`: passed. No full local gate, paid call, service-backed
  acceptance or `origin/main` publication was run.

## Integration handoff

Changed paths are exactly the new `analysis/profiles/**` package and six
resources, one focused test, this report/task and the top status in
`CURRENT_STATE.md`. No shared contract, migration, provider lock, existing
runtime module, dependency, composition root, style, `VERSION`, recording,
stand state or release ref changed. Revert this additive commit before
runtime wiring, or correct forward after a profile binds its hash.

`W56A-PROFILES-01` must consume the reviewed content only under its own
fresh grant, bind the hash to the immutable v2 profile/prompt bundle, add the
seven-category response schema and stage plan, and preserve v1 byte identity.
The MODEL-PIN/PROVIDER order still governs activation. The available stand
config selects a stub and exposes no verified Opus route; the distinct
recording route remains unidentified. This report makes no beta quality or
norm-validity claim.
