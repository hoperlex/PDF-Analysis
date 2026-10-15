# Task W56A-LEGACY-SOURCE-01 — verify the recovered legacy АР source

task_id: W56A-LEGACY-SOURCE-01

## Outcome

The W56a freeze owner receives a reproducible six-file legacy source manifest and a
source-line review map. It identifies the norm-dependent statements that the text-only
АР v2 profile must not turn into findings without W57's norm work.

## Depends on

- `W56A-PREFREEZE-01` — completed at `5bac83533b482c5635da5baa20edab35aaddea50`.
- `W55B-FIX` — completed on the underlying W55b candidate.

`W55B-INT-CLOSE` is pending. This is a source inventory, not a freeze or code lane.

## Frozen inputs

- base commit: `5bac83533b482c5635da5baa20edab35aaddea50`, based on W55b candidate `8c5a109bd98302b64fb47b364d4c639ff63c0eda`.
- domain contract: candidate revision 12; error catalogue SHA-256 `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16`.
- API contract: 47 paths / 54 operations / 123 schemas; OpenAPI SHA-256 `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`.
- analysis contract: stage registry SHA-256 `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`.
- migration head: `0021_portal_bundles`.
- W56a design: `docs/program/dispatch/W56-PLAN.md` §A3.2, §A3.4, §A4 on the base.
- external read-only source: `/root/projects/PDF-proverka`, HEAD `16ba8e5d23e4782550e79355002fde1365f682b7`; historical source commit `32b9d903792b30506048a1d42b0e6b2d07aee403`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the downloaded legacy checkout contains all six АР files unchanged
  from the historical source commit.

### P-01 — the six files are present and unchanged from the historical source commit

- captured_at: 2026-10-14
- command: `git -C /root/projects/PDF-proverka status --short --branch; git -C /root/projects/PDF-proverka rev-parse HEAD; git -C /root/projects/PDF-proverka merge-base --is-ancestor 32b9d903792b30506048a1d42b0e6b2d07aee403 HEAD; git -C /root/projects/PDF-proverka diff --exit-code 32b9d903792b30506048a1d42b0e6b2d07aee403 HEAD -- prompts/disciplines/AR/finding_categories.md prompts/disciplines/AR/checklist.md prompts/disciplines/AR/role.md prompts/disciplines/AR/drawing_types.md prompts/disciplines/AR/project_params.md backend/app/data/discipline_checklists/AR.md`
- captured_output:
  ```text
  ## main...origin/main
  16ba8e5d23e4782550e79355002fde1365f682b7
  ```
- exit_status: 0 for all commands; ancestry and six-file diff are silent on success.
- interpretation: the downloaded checkout is clean and the six named files have the same
  tracked bytes at the historical commit and HEAD. This says nothing about the correctness
  or current validity of the legacy norm claims.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W56A-PREFREEZE-01.md` §1/§3 (source absent on 2026-10-14 when measured)
- addendum_path: `docs/program/W56A-LEGACY-SOURCE-01.md`

The old absence observation remains an accurate historical measurement. This new report
records the later download and its provenance without rewriting the old report.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W56A-LEGACY-SOURCE-01.md`
- `docs/program/W56A-LEGACY-SOURCE-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies/lockfiles, composition roots, global styles
- `AGENTS.md`, `CURRENT_STATE.md`, `OWNER_RULINGS_*.md`, plans, and prior task/review evidence
- all paths in `/root/projects/PDF-proverka`, W55b worktrees/refs, stand, credentials and private exports

## Non-goals

- Porting prompts into `src/`, deciding any norm's validity, an exhaustive product-profile
  review, W56a freeze, gateway probes, paid calls, or W55b acceptance/publication.

## Deliverables

- Task file and source addendum with exact Git and SHA-256 provenance, a six-file content
  disposition, an item-level norm-exclusion index, and a handoff to `W56A-FREEZE-01` and
  `W56A-PROFILES-01`.

## Required tests

- command: `git -C /root/projects/PDF-proverka diff --exit-code 32b9d903792b30506048a1d42b0e6b2d07aee403 HEAD -- <six source paths>`
- expected: exit 0, no diff.
- command: `sha256sum <six source paths>` from `/root/projects/PDF-proverka`.
- expected: match all six digests in the report.
- command: `git diff --check` and `git diff --name-only 5bac83533b482c5635da5baa20edab35aaddea50..HEAD` after commit.
- expected: exit 0 and exactly the two allowed paths.

## Integration contract

The freeze owner may cite the six digests and corrected source path after checking the
source again on the accepted W55b SHA. The profiles lane uses the line map as review input,
then records its own item-by-item decisions in its lane report. No legacy claim or severity
is automatically promoted into a contract or prompt.

## Failure/idempotency/security cases

- A missing or changed source file stops the port until its provenance is reviewed; no
  silent replacement from another checkout.
- Legacy zero-valued sample fields, normative thresholds and document-type applicability
  labels are treated as source text, not verified product facts.
- The source checkout remains read-only. No secret, private export or paid gateway is used.

## Rollback / feature flag

Revert this document-only commit. No runtime or data rollback and no feature flag.

## Handoff

- changed files: see Allowed paths.
- commands/results: report §1 and §4.
- known limits: report §3.
- integration notes: report §5.
