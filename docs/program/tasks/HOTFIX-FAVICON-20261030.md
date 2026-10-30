# Task HOTFIX-FAVICON-20261030 — favicon AuditManager

## Outcome

The browser tab for every Next.js screen shows a recognizable AuditManager icon.

## Depends on

- None.

## Frozen inputs

- Domain contract: unchanged at `e8567a19`.
- API contract: `1.10.0`, 131 paths / 148 operations / 432 schemas.
- Analysis/comparison/event contract: unchanged at `e8567a19`.
- Migration head: `0039_comparison_core`.
- Base commit: `e8567a1981cbe35cf66bae4ce79b2877224df1be` (`origin/dev` when dispatched).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/app/icon.svg`
- `docs/program/tasks/HOTFIX-FAVICON-20261030.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and lock files.
- `src/auditmanager/bootstrap/**`, `web/src/app/globals.css`, `web/src/app/layout.tsx`.

## Non-goals

- Changing the wordmark, theme, routes, or product metadata.

## Deliverables

- A self-contained SVG favicon in the Next.js app directory.

## Required tests

- `python3 -c 'import xml.etree.ElementTree as ET; ET.parse("web/src/app/icon.svg")'` — exit 0.
- `python3` whitespace/newline check for the two allowed files — exit 0.

## Integration contract

Next.js serves `/icon.svg` from the app directory. No API, state, or navigation behavior changes.

## Failure/idempotency/security cases

- The SVG has no external references, scripts, or dynamic data.

## Rollback / feature flag

Remove `web/src/app/icon.svg`; no state migration or flag is needed.

## Handoff

- changed files: `web/src/app/icon.svg`, this task file.
- commands/results: SVG XML parse and two-file whitespace/newline check passed.
- known limits: browser favicon cache may delay a visible update.
- integration notes: include these two paths in the shared hotfix commit; no separate publication.
