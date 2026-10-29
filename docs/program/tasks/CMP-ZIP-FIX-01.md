# Task CMP-ZIP-FIX-01 — close the Unicode Path alias of the ZIP service-directory rule

## Outcome
The comparison ZIP-set reader refuses an exact `__MACOSX/` prefix in either the raw member name or the decoded Info-ZIP Unicode Path display name, with the same `comparison_zip_member_kind` constraint. A regression test first reproduces the bypass and then passes with the fix. The portal-bundle reader's default policy stays unchanged. First use of ZIP sets remains gated by caller controls in D-262.

## Depends on
- CMP-ZIP-SEC-01

## Frozen inputs
- domain contract: ADR-0025 decision 12; the owner's code-review and `__MACOSX/` choices; `CMP-ZIP-SEC-01`
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- analysis/comparison/event contract: unchanged from `CMP-SEAL-C2`
- migration head: `0040_comparison_ai_reports`
- base commit: `80f89946cd4d2f9bacc4fbae4283ce8a1fd7f7ce`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: focused ZIP-set and portal-policy tests

## Captured premise evidence
- premise: P-01 and P-02 establish the clean completed review and the exact raw/display policy gap before source edit.

### P-01 — reviewed base and frozen contract
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; git status --short; python3 -c 'import json;x=json.load(open("contracts/api/v1/openapi.json"));print(x["info"]["version"],len(x["paths"]),sum(k in {"get","post","put","patch","delete","head","options","trace"} for p in x["paths"].values() for k in p),len(x["components"]["schemas"]))'; ls db/migrations/versions | tail -n 1`
- captured_output:
  ```text
  80f89946cd4d2f9bacc4fbae4283ce8a1fd7f7ce
  1.11.0 176 198 517
  20261029_0040_comparison_ai_reports.py
  ```
- interpretation: the review task is committed; no C2 or C3 contract/migration moved in this source-repair worktree.

### P-02 — raw prefix checked, displayed prefix unchecked
- captured_at: 2026-10-29
- command: `rg -n 'name.startswith|decode_display_name|is_unsafe_name.shown' src/auditmanager/ingest/comparison_zip/policy.py`
- captured_output:
  ```text
  60:    decode_display_name,
  171:            if name.startswith(b"__MACOSX/"):
  175:            shown = decode_display_name(name, entry.flags, entry.extra)
  176:            if is_unsafe_name(shown.encode("utf-8")):
  ```
- interpretation: a valid Unicode Path alias can show the service prefix while the raw header does not; the review record identifies this as a first-use blocker.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/ingest/comparison_zip/policy.py`
- `tests/unit/ingest/comparison_zip/test_adversarial_archives.py`
- `docs/program/tasks/CMP-ZIP-FIX-01.md`
- `docs/program/CMP-ZIP-FIX-01.md`
- `docs/program/DEBT_REGISTER.md` (D-262 row only)

## Forbidden hotspots
- `src/auditmanager/ingest/bundle_archive.py`, portal reader and portal tests, all other application source and tests
- `contracts/**`, `db/migrations/**`, root dependencies/lockfiles, composition root, global styles, infrastructure, remote refs
- every debt row other than D-262

## Non-goals
- no new ZIP feature, case-folded service-directory policy, upload caller, archive transport or PDF-envelope change
- no API or migration change, and no C2 publication from this task

## Deliverables
- a regression test covering a harmless raw `ordinary.pdf` with a CRC-valid Unicode Path `__MACOSX/._ordinary.pdf`, also inside one permitted nested ZIP
- the smallest policy repair that applies the selected prefix rule to both names and retains the existing refusal code
- report of red-before/green-after tests, unchanged portal policy, remaining caller conditions, exact diff scope

## Required tests
- focused red regression before source edit
- focused `tests/unit/ingest/comparison_zip/` after the edit, including the portal-policy differential tests
- `git diff --check`, governance and forbidden-hotspot proof

## Integration contract
Merge after C2 publication and the review record. `CMP-STAGE-PAIR-01` must cite this repair and meet the remaining D-262 caller controls before invoking `extract_pdf_set`. The default `AUDITMANAGER_COMPARISON_MODULES=none` remains the operational stop.

## Failure/idempotency/security cases
- a display-name-only service prefix must never be accepted as a PDF or a directory hint
- raw-prefix rejection remains in force when Unicode Path shows a harmless alias
- malformed Unicode Path handling and traversal refusals keep their existing constraints

## Rollback / feature flag
Revert the scoped policy commit if it causes a regression; keep the comparison module disabled until an equivalent safe policy is restored. No data migration occurs.

## Handoff
- changed files: `src/auditmanager/ingest/comparison_zip/policy.py`, `tests/unit/ingest/comparison_zip/test_adversarial_archives.py`, this task, `docs/program/CMP-ZIP-FIX-01.md`, and the D-262 row of `docs/program/DEBT_REGISTER.md` only.
- commands/results: two new outer/nested Unicode Path cases failed before the source edit because the archive was accepted; full focused ZIP reader suite then passed 185/185 in 4.76 s, including portal-policy differential tests; governance 16 passed and `git diff --check` clean.
- contracts: unchanged; API `1.11.0` (176/198/517), migration head `0040_comparison_ai_reports`.
- known limits: no first-use caller, live upload or fuzzing; D-262 stays open until raw-upload/admission/disk/PDF checks are implemented at the C3 caller. The owner chose exact `__MACOSX/` rejection; case variants are outside this task.
- integration notes: merge after C2 publication, preserving the review record and the first-use block for `CMP-STAGE-PAIR-01`. No remote publication is authorized here. Forbidden portal/shared parser, contracts, migrations, root dependencies, composition root, styles and infrastructure were untouched.
