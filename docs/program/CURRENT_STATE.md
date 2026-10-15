# Current state

**W57b local designation coverage, 2026-10-15.**
`W57B-INT-CATALOGUE-SLUG-AUDIT-01` parses ГОСТ IEC/ISO and ГОСТ Р ИСО/МЭК
subseries. Against the unchanged 674-document source manifest, 617 slugs
parse and 57 remain in a digest-pinned, unreviewed local candidate. The
candidate is not a promoted catalogue or a runtime allowlist; W54 capacity,
snapshot and owner review remain ahead.

**Code-first parallel preparation, 2026-10-15.**
`CFB-INT-PARALLEL-01` integrates five bounded slices: W56a ledger/finding
decided severity and two appended CSV columns; W57a deterministic retrieval
set/catalogue bytes; W57b pure normative-reference resolution and a
deterministic two-sheet XLSX writer. The focused no-DB suite passes. The DB
severity/CSV tests could not run without `DATABASE_URL`; the contract suite
needs this worktree's missing bootstrap interpreter, and the local `soffice`
probe exited before conversion. These are development preparations, not
runtime activation, corpus qualification, a complete gate or beta acceptance.

**W57a bounded-range correction, 2026-10-15.**
`W57A-INT-RETRIEVAL-RANGE-BOUND-FIX-01` rejects impossible target/window
ordinal spans before expansion. Fifteen focused selector/resolver tests pass.
No runtime or corpus activation changes.

**AR v2 response pipeline preparation, 2026-10-15.**
`W56A-INT-RESPONSE-PIPELINE-PREP-01` joins typed model response parsing,
PDF-only proposal grounding and dense merge preparation in one pure step.
Ten focused tests pass. No recorded runtime stage, provider call or finding
publication is active.

**W57a target resolution preparation, 2026-10-15.**
`W57A-INT-TARGET-RESOLUTION-PREP-01` adds pure clause, table and explicit
range resolution over canonical paragraphs, splitting around unreliable text.
Fourteen combined resolver/ranking tests pass. Edition selection, promotion
DB access and owner map review remain ahead.

**W57a retrieval ranking preparation, 2026-10-15.**
`W57A-INT-RETRIEVAL-RANK-PREP-01` adds pure float32 window ranking, reliable
paragraph resolution and deterministic prompt-part reduction to 22,000
characters. Seven focused tests pass. No reviewed map, verified set, custody
publication, active v3 profile or runtime switch exists yet.

**W57a pure citation preparation, 2026-10-15.**
`W57A-INT-CITATION-PREP-01` adds `norm-quote-v1` raw-offset grounding,
`norm-value-v1` tokenization and an all-or-nothing citation/value guard.
Seventeen focused tests pass. No active v3 stage, promoted set, runtime wiring
or normative decision is claimed; those remain with W57a's later tasks.

**W59 section-route preparation, 2026-10-15.**
`W59-INT-SECTION-ROUTE-PREP-01` adds a pure guard for a version-bound
confirmed section and an available section-specific profile. It refuses
missing or mismatched confirmation and has no AR fallback. Persistence,
expert authorization, W59 API/DB reseal and runtime wiring remain ahead.

**Normative corpus readiness, 2026-10-15.**
`W54-INT-CORPUS-READINESS-01` pins the local 674-document source and the
W54/W55 operation order. Source sums, promotion snapshot, repairs, complete
embedding build and verified bundle are still absent. Current disk and
available memory fail W54's heavy-step floor; production import awaits the
bundle, capacity, P3 compatibility and the owner's downtime window.

**AR v2 merge-input preparation, 2026-10-15.**
`W56A-INT-MERGE-INPUT-PREP-01` connects fully grounded proposals to the
deterministic merge rule with dense artifact ordinals and an explicit source
ordinal map. Rejected proposals contribute no merge member. This is pure
preparation; runtime wiring and live calls remain blocked by their grants.

**W59–W62 profile vocabulary preparation, 2026-10-15.**
`W59-INT-PROFILE-METADATA-PREP-01` captures the 14 legacy sections' 162
category codes and 201 sheet types as digest-pinned, read-only candidates.
Four focused tests pass. No prompt, normative claim or section profile is
active; `PB` remains to be authored. No full local gate or acceptance ran.

**W59 section-suggestion preparation, 2026-10-15.**
`W59-INT-SECTION-SUGGESTION-PREP-01` adds a pure 15-section suggestion
registry from the local legacy source plus owner-retained `PB`; `PS` is
«Пояснительная записка». Thirteen focused tests pass. No section is
auto-confirmed, no API/DB/route changes are active, and the W59 framework
reseal remains ahead. No full local gate or acceptance was run.

**AR v2 proposal grounding preparation, 2026-10-15.**
`W56A-INT-PROPOSAL-GROUNDING-PREP-01` joins parsed proposals to PDF-only
quotation grounding in a pure module. Any failed item rejects the whole
proposal while retaining every diagnostic; runtime wiring remains blocked by
MODEL-PIN and PROVIDER. Focused tests pass; no full local gate was run.

**Reconciled 2026-10-15 on the W56a development line.** This file is the short entry point for
coding agents. The exact task base, frozen inputs and permitted paths come from the assigned task
file and freeze; verify them against Git. The complete earlier state is preserved verbatim in
[the 2026-10-15 archive](history/CURRENT_STATE_2026-10-15_ccfb9735.md). Earlier wave reports,
rulings and evidence remain at their original paths.

## Current development boundary

W56a has integrated a recorded-only AR v2 contract and migration, a deterministic synthetic
corpus, a pure grounded merge core and an offline seeded matcher on `origin/dev`. Reviewed AR v2
profile content, a response schema and parser, marked uncitable OCR context, deterministic
prompt material, a one-call offline identity probe and OCR-only quote grounding are prepared. The matcher still has
no measured baseline or threshold. The gateway model identity and price have not been
verified; no runtime v2 execution or provider call is activated. The code-first work order and entry conditions are in
[`CODE-FIRST-TO-BETA.md`](dispatch/CODE-FIRST-TO-BETA.md); the next block needs its own exact
freeze and task files.

The development API surface is **47 paths / 54 operations / 124 schemas**. The error catalog
has **25** codes, the domain candidate is revision **13** with **32** opaque identities, and the
migration head is **`0022_findings_v2`**. `VERSION` is `0.6.0`. These are claims about this
checkout, checked against the frozen artifacts; they are not a deployment claim.

W55b is the latest closed development baseline. Its full gate completed under `R-125` on an
exact clean candidate after infrastructure failures, without printing the literal `GATE OK`;
see `W55B-INT-CLOSE.md` for the evidence and limitation. `v0.5.0` is the last published release
recorded in this tree. The deployed tree must be checked with
`infra/deploy/verify-deployed.sh`, not inferred from this file.

`R-135` moves the complete gate for development-only W56a–W63 to the end of the planned beta
code series. Each intermediate task runs its named focused checks and records what it deferred.
A development merge or `origin/dev` publication does not claim beta acceptance. A separate
owner instruction for the exact candidate, a complete gate and the auto-deploy policy still
govern any `origin/main` publication. See `AGENTS.md` §6–§8 and
`docs/program/MAIN_AUTODEPLOY_POLICY.md`.

## Open gates and pointers

- D-137–D-140 retain identity browser/QA and full-gate evidence that development closeouts did
  not supply. Later code-only work carries its own deferred checks under `R-135`.
- The gateway model identity and price block provider activation; no unverified provider or
  tariff may be silently substituted. The W56a probe and review reports carry the evidence.
- Normative corpus promotion and served retrieval still require their separate custody,
  corpus and validation tasks; storage plumbing alone is not a live normative claim.
- `docs/program/dispatch/CODE-FIRST-TO-BETA.md`, the applicable wave plan, the assigned task
  file, its completed `depends_on` and the frozen contract set determine the next action.
- `docs/program/DEBT_REGISTER.md` is the open-work register; dated reports in the archive are
  evidence of what was measured then, not instructions to replay old work.

## Previous release state — wave 48 (historical record)

The full previous state, including this wave-48 section and the older CP-00 history, is stored
verbatim in [the dated archive](history/CURRENT_STATE_2026-10-15_ccfb9735.md). The archive is a
point-in-time record of the base tree; it is not the live development status.
