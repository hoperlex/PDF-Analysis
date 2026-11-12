# Task ONE-LIST-COMPLETE-01 — finish the one-list review journey

## Outcome and owner
Owner: this implementation session, assigned directly by the owner on 2026-11-12 after
`.local/reports/v2-candidates-to-findings-2026-11-12.md`. Adopt the completed F8 web patch
at `c4b2cd9581f8a6fa19d0df51492c3fb2fd0690bc` in an isolated checkout and finish the journey.
Follow PDF-proverka's dense findings table, severity chips, source expansion and row decisions.
Historical candidates are readable on Review; new block-grounded findings take ordinary
expert decisions and carry separately labelled severity/action proposals.

## Depends on
- F8-PUBLISH — merged in development.
- V2-QUALITY-HOTFIX-01 — accepted and merged in development.

## Frozen inputs
- Development base: `f09275a7e81e06b858488c5b6291a569bea70f80`.
- API/domain/analysis: 1.54.0; migration head `0067_precedents_wave5`.
- ADR-0029 decision 7; R-153al; R-151j (human severity remains separate).
- Reference: PDF-proverka `3c99481719218b9cfa7560886529916646c61939`.
- Owner archive: `.local/analysis-run_01M75JWVA0NTBXMXAV9FCZQ289.zip`, read-only.

## Allowed paths
- `src/auditmanager/analysis/extended/finding_proposals.py`, `src/auditmanager/analysis/public.py`.
- `src/auditmanager/runs/{preflight,cost_policy,extended_review,v2_quality,executor}.py`.
- `src/auditmanager/findings/{publication,artifacts,queries,terminal}.py`.
- `src/auditmanager/precedents/settings.py`, `src/auditmanager/dashboard/audit_state.py`.
- `src/auditmanager/exports/**`.
- The 27 web source/test paths of the adopted F8-WEB patch; `web/src/_pages/review/**`,
  `web/src/widgets/{extended-review,finding-list}/**`, `web/src/entities/{finding,finding-observation}/**`,
  `web/src/_pages/portal-blocks/**`, `web/tests/unit/{review,analysis-extended,styles}/**`.
- `web/src/entities/document-version/model/audit-state.ts`, `web/tests/unit/document-audit/**`.
- Focused tests in `tests/unit/{analysis_extended,runs,findings,precedents,dashboard}/**`,
  `tests/integration/{findings,runs,decisions,exports,dashboard}/**`.
- This task, `docs/program/P02_SEAMS.md`, the relevant D-683/D-686 register rows.
- Release metadata: `VERSION`, `release-notes/0.26.0.json`, its version pins in
  `tests/contract/release_notes/test_release_notes_form.py`,
  `tests/integration/releases/test_release_loader.py`, `docs/program/CURRENT_STATE.md`.
- Ignored task evidence and previews under `.local/`.

## Forbidden hotspots / non-goals
No contracts, migrations, root dependencies/locks, composition roots or global styles.
No production access, main publication, model calls, full analysis runs or full gate.
No rewriting old artifacts/decisions, machine expert verdicts, speculative native anchors,
new canonical normative-certification claims or unrelated precedents work.

## Deliverables and checks
Proposal schema behind a new frozen consent marker; unchanged old quality bundle/requests;
publisher propagation; block-aware review; paged read-only historical candidates; readable
warnings; consistent CSV/XLSX evidence coverage; persistent unread-publication degradation.
Focused pytest and Vitest, touched ESLint and TypeScript, read-only owner-archive projection,
light/dark 1280/390 previews with DOM facts, diff and hotspot checks. Reuse installed tools;
run heavy checks sequentially under the shared host lock.

## Integration contract / rollback
Reuse sealed Finding fields and block gate. New optional proposal policy applies only to
fresh consents; old accepted quality policies keep their exact request/policy bundle.
The readiness guard opens only after the web/export/persistence seams are verified. The
administrator's journalled one_list switch remains the activation control for new planned
runs; no live setting is changed here. Historical text_only runs keep their counts and
decisions. A block reference proves location, never engineering truth. Native-only candidates
without exact text evidence stay visible for reading. Roll back the switch for future runs;
retain readers for already-published block findings. Any needed contract/migration change
must be assigned its own slot before editing.

## Delivered candidate and verification
- Version 0.26.0; API 1.54.0 and migration 0067 unchanged. Adopted F8-WEB source
  and completed historical reading, proposal binding, ordinary block decisions and exports.
- New one-list runs default to the dense table. A primary text candidate links back to
  its existing finding; already represented raw members do not appear twice. Remaining
  candidates are read-only, with 25-row paging, search, origins and proposal filters.
- New proposals use the existing substantive critic call and a separately frozen consent
  marker. Old quality bundle files are byte-identical. Norm candidates remain unverified.
- Unread publication is stored in scalar stage metrics and yields a partial terminal.
  The existing four audit states retain their contract meaning; partial chips and the
  empty Review state explicitly describe incomplete coverage.
- Focused backend suite: 237 passed; public-analysis/P02 seams: 21 passed.
  Web review, extended review, document audit, styling and indication/language guards:
  760 passed. The partial-group representative edge case also passed (8 focused tests).
  TypeScript and touched ESLint: exit 0. No full gate, live model call or analysis run.
- Owner archive: 171 raw observations -> 139 linked groups, raw records unchanged.
  28 static browser views (light/dark, 1280/390): no page overflow or integrity faults;
  block frame placement differs by at most 0.1 px from the viewer's own geometry.
  New findings/drawings in previews are fixtures; historical candidates are from the
  supplied archive. This is component/browser evidence, not a deployed production journey.

Full logs, the exact changed-file list and previews are in
`.local/evidence/one-list-complete-1112/` of this worktree (`change-manifest.json`,
`archive-projection-facts.json`, `backend-final.log`, `seam-checks.log`, `web-final.log`,
`typecheck.log`, `eslint.log`, `preview/facts.json`). The initial read-only investigation
remains at the root worktree's `.local/reports/v2-candidates-to-findings-2026-11-12.md`.

## Integration action and limits
Integrate this branch as one candidate on development, including its version note.
No shared contract, migration, dependency/lock, composition-root or global-style file
was changed; `change-manifest.json` records the empty hotspot intersection. No tag,
main push or deployment is part of this task.

After normal integration/deployment, an administrator can explicitly enable new planned
runs through the existing keyed `POST /api/v1/precedent-settings` command:
`{"setting_name":"one_list","value":{"enabled":true}}`. No live setting was changed
here. A new estimate/consent is needed for severity/action proposals; historical consents
keep their old requests. Roll back with the same command and `enabled:false` for future
runs, retaining block readers for already published findings.

Native-only candidates without exact source spans remain read-only. Old runs do not gain
invented severity or recommendations. Grounding proves location, and every engineering
verdict remains the expert's.
