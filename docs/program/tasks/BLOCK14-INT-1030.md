# BLOCK14-INT-1030 — dense native pages with exact piece citations

task_id: BLOCK14-INT-1030

## Outcome

Fresh ordinary section runs can process native PDF-page text larger than one model window through durable bounded pieces, retaining original physical pages and document-global Unicode quote ranges.

## Depends on

- BLOCK13-INT-1030

## Frozen inputs

- Dev `6f907ece3f747214bbcba265974b2d0df779ebe3`, API1.14.0/migration0044.
- Existing immutable prepared.text_layer, ModelRequest/schema, page/quote evidence, saved window journal/cost/unknown guards.
- Source-only owner authorization; no check/model/synthetic execution. Root sole integration owner.

## Allowed paths

- `src/auditmanager/analysis/text/page_pieces.py`
- `src/auditmanager/analysis/text/windows.py`
- `src/auditmanager/analysis/text/windowed.py`
- `src/auditmanager/analysis/text/config.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/cost_policy.py`
- `src/auditmanager/runs/executor.py`
- `docs/program/**`

## Forbidden hotspots

Legacy window_anchor/window_cohort, source text/evidence contracts, trusted AR-v3 machinery, API/generated/contracts, routers/composition root, migrations, dependencies/locks, global styles, tests/fixtures, all other paths, main/deployment. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No OCR/recognised-block splitting, new source normalization, fabricated physical pages, legacy-consent expansion, weaker canonical evidence, cross-piece absence inference, expert action or beta-quality claim.

## Deliverables

Independent fresh native_page_piece_policy binds actual helper/window/runtime hashes and is quoted in accepted ordinary-run cost authority. Conservative complete call/input/output bound may exceed page_count; old missing-policy authority keeps old plan. Validate actual policy before early paid visual work. Dense native source uses bounded gapless/nonoverlapping pieces with real physical pages, source text and original global ranges; fitting recognised blocks remain whole and oversized ones still refuse. Separate pure binder validates complete source coverage and resolves citations only inside the piece actually supplied. Partial-page omission proposals are not canonical evidence. Existing window hashes/custody retain paid replies and unknown-outcome discipline. Count a physical page fully analysed only when every one of its pieces has an untruncated answer; retain explicit metrics/limitations.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate; citation-rule execution/independent review D-290.

## Integration contract

Root owns the named executor/cost integration slots. No frozen transport/analysis contract or existing evidence-rule edit. Normal clean origin/dev publication/read-back with incoming owner changes preserved; deployment remains owner-only.

## Rollback / feature flag

AUDITMANAGER_NATIVE_PAGE_PIECES=0 excludes fresh piece authority and pricing. Accepted plans pin helper hashes; old missing-field runs retain whole-page refusal, source/request bytes and saved history.

## Handoff

Changed paths, no-check status, unchanged contracts, native-only/partial-page omission/coverage limits and D-290.
