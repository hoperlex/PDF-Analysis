# AR-V3-PROMPT-REDO-01 — coherent draft prompt for section АР

**Base:** `origin/dev` at `3bc7dae1a62ccd871ed42fc364ffa139cc2313f3`.
**Task:** [AR-V3-PROMPT-REDO-01](tasks/AR-V3-PROMPT-REDO-01.md).

The previous draft joined all six reviewed AR v2 sections after v3 rules.
Two sections contradicted v3: `role.md` prohibited external normative checks,
and `finding_categories.md` allowed exactly seven categories. The renderer now
reuses the four common checklist, drawing, parameter and AR checklist sections,
and supplies v3-specific role, twelve-category and evidence instructions.

The prompt separates internal contradictions from normative comparisons, names
all categories in the response schema, requires one object and characteristic
for an internal comparison, and requires stated project evidence, an applicable
quoted requirement and an actual disagreement for a normative proposal. It
keeps PDF quotes tied to a page, marks OCR as context, confines citations to
selected N labels, preserves table separators, and treats all supplied text as
data. It neither chooses the applicable legal edition nor makes an expert
decision. V2 reviewed resources and material digest remain byte-identical.

## Checks

- Focused v3 prompt, request and response tests plus program governance:
  **64 passed**.
- `py_compile` of the changed Python files: passed.
- `git diff --check`: passed.
- Changed paths from the frozen base: exactly the prompt renderer, its focused
  test, this report and its task file. No forbidden hotspot changed.

## Integration and limits

No public or shared contract changed. This is still an unserved draft prompt:
there is no qualified reviewed normative map/set, sealed v3 profile or live
CAP-01 evidence. A later PROFILE owner must inspect and seal these exact bytes
with the Run-pinned set and full provider budget. The user's 128,000-character
and $1.50 choices concern a separate cap/cost implementation; this prompt
packet does not change either enforcement boundary. Roll back by reverting
this four-file packet.
