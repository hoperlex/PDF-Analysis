# Task REVIEW-INDICATION-SWITCH-01 — one switch for the two "no human review" indications of the beta

task_id: REVIEW-INDICATION-SWITCH-01
status: in progress (lane `agent/review-indication-switch-01`, base `05f4584d`; nothing pushed, merged or tagged)

## Outcome

One exported constant, `SHOW_REVIEW_INDICATION` (`web/src/shared/config/review-indication.ts`), default `false` for the beta, decides whether the screens tell the user that a human did not review a result. With it `false`: the profile status `reviewed` shows the neutral contract word «проверен» (no claim about who), and the AR v3 result views drop the wording that a citation is provisional and awaits the expert. With it `true`: every one of those screens is byte-identical to the tree at `05f4584d`. Restoring the wording is one edit of one value (and the pin test that names it). `R-146ba`, accepted risks `A-10` and `A-11`.

Not behind the switch, by the integrator's rule: the label above the version-comparison summary «Сводка подготовлена моделью, проверка человеком не проводилась» (it separates model text from document facts, `AGENTS.md` section 4); the attestation record of the sealed pack as «Настройки анализа» shows it; every statement that a verdict is the expert's own decision.

Also: the sentence of `run-progress.tsx:134` «Канонические находки здесь не публикуются.» is false for an AR v3 Run that published findings (`AR-V3-DECISIONS-01`); it is replaced for such a Run and kept for a Run that publishes none. The `0.9.0` release note (revision 2) no longer says that a screen shows the profile label.

## Depends on

- `AR-V3-DECISIONS-01` — completed (merged `eb5dcf1e`); supplies the findings panel and the replacement wording of its integration note 6.
- `RELEASE-0-9-0-DEV-01` — completed; the `0.9.0` note has not reached `main`, so its revision may be raised.
- `SMALL-HARDENING-02` part (c) is this task (`docs/program/dispatch/PRODUCTION-WAVE-PW5.md` section 4).

## Frozen inputs

- domain contract: unchanged
- API contract: `1.8.0`, unchanged (no field, no enum, no operation)
- analysis/comparison/event contract: unchanged
- migration head: `0036_cite_partition_v3`, unchanged
- product version: `0.9.0` (`release-notes/0.9.0.json` raised from revision 1 to 2)
- base commit: `05f4584d` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the strings to gate, the strings that stay, the places that pin them, the shared/config idiom, the release-note pins and the stale sentence are exactly as listed below (captured on the base before any edit)

### P-01 — the base and the lane
- captured_at: 2026-10-27
- command: `git rev-parse --short HEAD; git branch --show-current; git merge-base HEAD integration/ar-close-1026 | python3 -c "import sys;[print(l.rstrip(chr(10))[:8]) for l in sys.stdin]"; git status --short -- . :!docs/program/tasks/REVIEW-INDICATION-SWITCH-01.md | wc -l`
- captured_output:
  ```text
  05f4584d
  agent/review-indication-switch-01
  05f4584d
  0
  ```
- interpretation: The lane starts on the integration tip with a clean tree.

### P-02 — every user-visible string of the kind, in the files of the brief (with the neighbouring stage label and the comparison summary, to show what is in and out)
- captured_at: 2026-10-27
- command: `grep -rnE "предварительн|Предварительн|проверк[а-я]* эксперт|проверка человеком|проверки человеком|экспертной проверки|Канонические находки" web/src/widgets/ar-v3-beta-review web/src/widgets/ar-v3-beta-pack web/src/widgets/ar-v3-beta-status web/src/widgets/run-progress web/src/features/start-ar-v3-group web/src/entities/analysis-profile web/src/shared/ui/stage-label.ts web/src/entities/version-comparison/ui/comparison-summary.tsx`
- captured_output:
  ```text
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:33:    case 'available': return 'Предварительный разбор доступен';
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:39:  if (mode === 'provisional_citation') return 'Предварительная ссылка';
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:59:            <p><strong>Только предварительные ссылки.</strong> Каждая тема и цитата требует проверки эксперта. Числовой или правовой вывод здесь не утверждён.</p>
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:64:                  <strong>{topic.item_id}</strong> — {topicModeLabel(topic.mode)}; требует проверки эксперта.
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:70:            <h3>Предварительные цитаты</h3>
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:71:            {member.review.provisional_citations.length === 0 ? <p>Предварительных цитат нет.</p> : (
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:75:                    <p>Предложение {proposal.proposal_ordinal + 1}; требуется проверка эксперта.</p>
  web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:113:      <p>Введите идентификатор группы из ответа запуска. Здесь видны все шесть прогонов и только предварительные нормативные ссылки.</p>
  web/src/widgets/ar-v3-beta-pack/model/pack-presentation.ts:28:  'остаются предварительными и требуют проверки эксперта.';
  web/src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx:30:    ? 'Предварительная ссылка — требуется проверка эксперта'
  web/src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx:31:    : 'Только контекст — требуется проверка эксперта';
  web/src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx:39:      <h2 id="ar-v3-beta-title">АР v3: предварительная карта норм</h2>
  web/src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx:46:        Тем: {policy.items.length}; предварительные ссылки: {provisional}; только контекст: {contextOnly}.
  web/src/widgets/ar-v3-beta-status/ui/ar-v3-beta-status.tsx:47:        Все пункты требуют проверки эксперта.
  web/src/widgets/run-progress/ui/run-progress.tsx:133:          <p>Прогон завершён. Предварительный нормативный разбор АР v3 сохранён.</p>
  web/src/widgets/run-progress/ui/run-progress.tsx:134:          <p>Канонические находки здесь не публикуются. Каждая тема и цитата требует проверки эксперта; числовой или правовой вывод не утверждён.</p>
  web/src/widgets/run-progress/ui/run-progress.tsx:152:          <p>Предварительный нормативный разбор АР v3 завершился частично. Полный проверенный результат не подтверждён.</p>
  web/src/widgets/run-progress/ui/run-progress.tsx:153:          <p>Канонические находки не публикуются; требуется проверка эксперта.</p>
  web/src/widgets/run-progress/ui/run-progress.tsx:410:          title="Предварительный разбор АР v3"
  web/src/features/start-ar-v3-group/ui/start-ar-v3-group-control.tsx:64:          Шесть отдельных прогонов; результат — предварительные цитаты для проверки экспертом,
  web/src/entities/analysis-profile/model/presentation.ts:16:  draft: 'черновик, требует экспертной проверки',
  web/src/entities/analysis-profile/model/presentation.ts:17:  reviewed: 'рабочая версия, проверка человеком не проводилась',
  web/src/shared/ui/stage-label.ts:66:  ar_v3_citation_review: 'Предварительная проверка нормативных ссылок АР v3',
  web/src/entities/version-comparison/ui/comparison-summary.tsx:101:            заменяет и не меняет различия; проверка человеком не проводится. Повторный запрос по
  ```
- interpretation: The decision of this task per line. GATED (hidden while the switch is off): ar-v3-beta-review.tsx 33, 39, 59, 64, 70, 71, 75, 113; ar-v3-beta-status.tsx 30, 31, 39, 46, 47; run-progress.tsx 133, 134 (also rewritten for a Run that published), 152, 153, 410; start-ar-v3-group-control.tsx 64; presentation.ts 17 (the profile label). NOT gated: pack-presentation.ts 28 (the pack attestation, integrator rule); comparison-summary.tsx 101 (the summary label, integrator rule, and a forbidden path); presentation.ts 16 (the label of a draft: the owner removed the label of a reviewed profile only); stage-label.ts 66 (the name of a stage, outside the allowed paths: reported to the integrator, a stage name is not a statement about review).

### P-03 — the statements about the expert's own decision, which stay
- captured_at: 2026-10-27
- command: `grep -rnE "Формулировка модели|Решение записывает эксперт|Находки и решения эксперта|решённая экспертом|Предложение модели" web/src/widgets/ar-v3-beta-review`
- captured_output:
  ```text
  web/src/widgets/ar-v3-beta-review/ui/run-findings.tsx:56:          <> Важность, решённая экспертом: <SeverityBadge severity={finding.decided_severity} /></>
  web/src/widgets/ar-v3-beta-review/ui/run-findings.tsx:75:      <p><strong>Формулировка модели, не решение эксперта.</strong></p>
  web/src/widgets/ar-v3-beta-review/ui/run-findings.tsx:80:          Предложение модели о важности: <SeverityBadge severity={proposed} />
  web/src/widgets/ar-v3-beta-review/ui/run-findings.tsx:83:      {!mayDecide ? <p>Решение записывает эксперт.</p> : (
  web/src/widgets/ar-v3-beta-review/ui/run-findings.tsx:153:      <h3>Находки и решения эксперта</h3>
  ```
- interpretation: None of these is an indication that no human reviewed: each says who decides or whose text it is (AGENTS.md section 4). They stay, in both states of the switch, and a test says so.

### P-04 — wording that claims an expert checked the installed pack (not an indication of absence)
- captured_at: 2026-10-27
- command: `grep -rn "проверенный экспертом" web/src`
- captured_output:
  ```text
  web/src/features/classify-version/ui/classify-version-form.tsx:211:            проверенный экспертом набор.
  web/src/entities/analysis-profile/model/presentation.ts:39:  'становится доступной, когда на сервере установлен проверенный экспертом набор; состояние ' +
  ```
- interpretation: AR_START_NOTE and a hint of the classification form say «проверенный экспертом набор». That is a claim, not an indication that no one reviewed; it is outside the owner decision, the form is outside the allowed paths, and `A-11` says no subject-matter expert took part in the pack. Left as it is and reported to the integrator.

### P-05 — the tests that pin the wording today
- captured_at: 2026-10-27
- command: `grep -rnE "проверка человеком не проводилась|проверки эксперта|проверка эксперта|предварительн|Предварительн|Канонические находки|проверки экспертом" web/tests | grep -v comparison-summary`
- captured_output:
  ```text
  web/tests/unit/analysis-settings/ar-v3-beta-pack-status.test.ts:308:        'предварительными и требуют проверки эксперта.',
  web/tests/unit/analysis-settings/ar-v3-beta-pack-status.test.ts:312:        'предварительными и требуют проверки эксперта.',
  web/tests/unit/analysis-settings/ar-v3-group-start-failure.test.ts:176:    expect(markup).toContain('Шесть отдельных прогонов; результат — предварительные цитаты для проверки экспертом, без числовых выводов.');
  web/tests/unit/analysis-settings/analysis-settings.test.ts:282:    expect(row(table(withProfile('POS', { status: 'reviewed' })), 'POS')).toContain('проверка человеком не проводилась');
  web/tests/unit/analysis-settings/analysis-settings.test.ts:366:    expect(markup).toContain('предварительные ссылки: 14; только контекст: 8');
  web/tests/unit/analysis-settings/analysis-settings.test.ts:374:    expect(markup).toContain('Только контекст — требуется проверка эксперта');
  web/tests/unit/screens/run-progress.test.ts:329:    expect(markup).toContain('Каждая тема и цитата требует проверки эксперта');
  web/tests/unit/run/stage-rows.test.ts:135:    expect(markup).toContain('Предварительная проверка нормативных ссылок АР v3');
  ```
- interpretation: These assertions describe the switch-on screen. Each file that must keep asserting the old text pins the switch on explicitly (see the report); the new test files assert both states. comparison-summary.test.ts is not touched.

### P-06 — the live journey manifest names the profile label (outside the allowed paths)
- captured_at: 2026-10-27
- command: `grep -n "рабочая версия, проверка человеком не проводилась" tests/e2e/pc01/journey/manifest.json`
- captured_output:
  ```text
  2184:            "text_contains": "рабочая версия, проверка человеком не проводилась"
  2188:            "text_contains": "рабочая версия, проверка человеком не проводилась"
  ```
- interpretation: The manifest expects the label on the /analysis-settings screen at these two lines; with the switch off the screen says «проверен». tests/e2e/** is not in this task's allowed paths: the two `text_contains` values must become `проверен` under the integrator (it is the live journey, which only the gate catches).

### P-07 — the idiom of shared/config: the only place for a deploy-level setting, an index that re-exports
- captured_at: 2026-10-27
- command: `ls web/src/shared/config; sed -n 1,9p web/src/shared/config/index.ts`
- captured_output:
  ```text
  env.ts
  index.ts
  polling.ts
  proxy-trust.ts
  screen-registry.ts
  server-env.ts
  session-store.ts
  /**
   * Public API of `shared/config`.
   *
   * This is the only module in `web/` that reads `process.env`. A guard test enforces it,
   * because an environment lookup scattered through a slice is how a localhost default
   * gets reintroduced.
   */

  export { MissingConfigurationError, getApiBaseUrl, getInstanceLabel, getWebBuildId, hasApiBaseUrl } from './env';
  ```
- interpretation: A new module in the same directory, exported from the index, follows the idiom (polling.ts is the precedent for a frozen constant fixed in one place).

### P-08 — the pins of the 0.9.0 revision
- captured_at: 2026-10-27
- command: `grep -n "\"revision\"" release-notes/0.9.0.json; grep -n "\"0.9.0\": 1" tests/contract/release_notes/test_release_notes_form.py; grep -n "\"0.9.0\"" tests/integration/releases/test_release_loader.py; grep -n "revision 1" docs/program/RELEASES.md docs/program/RELEASE-0-9-0-DEV-01.md | python3 -c "import sys;[print(l.rstrip(chr(10))[:110]) for l in sys.stdin]"`
- captured_output:
  ```text
  3:  "revision": 1,
  161:        "0.9.0": 1, "0.8.2": 1, "0.8.1": 1, "0.8.0": 1, "0.7.0": 2, "0.6.0": 2, "0.5.1": 1, "0.5.0": 1,
  69:        "0.9.0",
  docs/program/RELEASES.md:20:Prepared by `RELEASE-0-9-0-DEV-01` on `origin/dev` only: `VERSION=0.9.0` and `rele
  docs/program/RELEASES.md:24:Prepared by the parallel-runs slices (`EXEC-PAR-START-01`, `EXEC-PAR-QUEUE-01`, `E
  docs/program/RELEASES.md:28:Prepared by `RELEASE-0-8-1-DEV-01` on `origin/dev` only: `VERSION=0.8.1` and `rele
  docs/program/RELEASE-0-9-0-DEV-01.md:7:`VERSION` is `0.9.0`. [`release-notes/0.9.0.json`](../../release-notes/
  ```
- interpretation: The revision map in the form test is the one numeric pin; the loader test only lists the version; the two documents say revision 1 in prose. They move with the note to revision 2.

### P-09 — the owner ruling and the accepted risks
- captured_at: 2026-10-27
- command: `grep -n "R-146ba" docs/program/OWNER_RULINGS_2026-09-17.md | python3 -c "import sys;[print(l.rstrip(chr(10))[:90]) for l in sys.stdin]"; grep -n "^| A-10\|^| A-11" docs/program/PRODUCTION-READINESS-PLAN-01.md | python3 -c "import sys;[print(l.rstrip(chr(10))[:230]) for l in sys.stdin]"`
- captured_output:
  ```text
  1811:| `R-146ba` | *Human review of the sections and of АР v3 during the beta.* The owner
  1813:| `R-146bc` | *Order of the next window.* Chosen: «АР: решения по цитатам + отчёт нор
  245:| A-10 | During the beta no screen says that a profile or a citation was not reviewed by a human (`A-7` stays true). | `R-146ba` | the label switch is restored by one edit; or the first expert review |
  246:| A-11 | АР v3 is activated on decisions taken by the AI integrator under the owner's delegation; the reviewer attestation says so; no subject-matter expert took part. | `R-146ba` | a qualified expert's review of C01–C22 and t
  ```
- interpretation: The ruling removes the two indications for the duration of the beta, with one switch and one edit to restore; A-10 and A-11 are accepted risks of exactly that.

### P-10 — the stale sentence and the wording AR-V3-DECISIONS-01 proposes
- captured_at: 2026-10-27
- command: `sed -n 134p web/src/widgets/run-progress/ui/run-progress.tsx; grep -n "Suggested wording" docs/program/AR-V3-DECISIONS-01.md | python3 -c "import sys;[print(l.rstrip(chr(10))[:520]) for l in sys.stdin]"`
- captured_output:
  ```text
            <p>Канонические находки здесь не публикуются. Каждая тема и цитата требует проверки эксперта; числовой или правовой вывод не утверждён.</p>
  206:6. **A false sentence on a screen, outside the grant:** `web/src/widgets/run-progress/ui/run-progress.tsx` line 134 says «Канонические находки здесь не публикуются.» for a published AR v3 Run; it now publishes findings (when a proposal is provisional). Suggested wording: «Находки с предварительными нормативными ссылками опубликованы; решение по каждой записывает эксперт.», with the existing tests of that widget moved with it. Also the prose of `docs/program/AR-V3-BETA-*.md` that says «review-only» describes his
  ```
- interpretation: The sentence says no finding is published for a published AR v3 Run; the terminal now publishes one finding per provisional proposal that passed both gates.

### P-11 — where the finding count of a Run comes from on the screen
- captured_at: 2026-10-27
- command: `sed -n 195,197p web/src/entities/audit-run/model/run-presentation.ts; grep -n "published_finding_count" web/src/shared/api/generated/types.gen.ts`
- captured_output:
  ```text
      case 'published':
        return { kind: 'published', findingCount: status.published_finding_count ?? null };
      case 'partial':
  2784:  published_finding_count?: number;
  ```
- interpretation: The screen knows the count (null when the server did not report it). A v3 Run that published at least one finding gets the new sentence; a count of zero or an unreported count keeps the old one.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/shared/config/**`
- `web/src/entities/analysis-profile/**`
- `web/src/widgets/ar-v3-beta-review/**`
- `web/src/widgets/ar-v3-beta-pack/**`
- `web/src/widgets/ar-v3-beta-status/**`
- `web/src/widgets/run-progress/**`
- `web/src/features/start-ar-v3-group/**`
- `web/tests/**`
- `release-notes/0.9.0.json`
- `tests/contract/release_notes/**`
- `tests/integration/releases/**`
- `docs/program/RELEASES.md`
- `docs/program/RELEASE-0-9-0-DEV-01.md`
- `docs/program/REVIEW-INDICATION-SWITCH-01.md`
- `docs/program/tasks/REVIEW-INDICATION-SWITCH-01.md`

The files of the findings panel that `AR-V3-DECISIONS-01` added are `web/src/widgets/ar-v3-beta-review/ui/run-findings.tsx` and `web/src/widgets/ar-v3-beta-review/model/may-decide.ts`, already inside the directory above. `tests/integration/releases/**` is for pins only.

## Forbidden hotspots

- `contracts/**`, `src/**`, `db/migrations/**`, `infra/**`, `tests/e2e/**`
- root dependency/lock files, composition root, global styles
- `web/src/entities/version-comparison/**` (the label above the comparison summary) and the pack attestation sentence
- `web/src/shared/ui/**` (the stage label stays; reported)

## Non-goals

- No change to `AR_START_NOTE`, to the classification hint «проверенный экспертом набор», to the draft label or to the stage label (reported, not decided here).
- No change to what the server sends or to any contract.
- No removal of any statement that a verdict is the expert's own decision.

## Deliverables

- `web/src/shared/config/review-indication.ts` and its export from the index.
- The gated strings of P-02 behind the constant (the neutral wording named in the report).
- The rewritten sentence for an AR v3 Run that published findings.
- Tests: one per state of the switch for each gated string, a static guard over the listed files, a test that the summary label and the pack attestation are not gated, and the default pin.
- `release-notes/0.9.0.json` revision 2 and its pins; `RELEASES.md` and `RELEASE-0-9-0-DEV-01.md` rows.
- `docs/program/REVIEW-INDICATION-SWITCH-01.md` (files, mutation table, before/after of modified tests, commands and counts, integration notes, limits).

## Required tests

- command: `cd web && npx vitest run <the touched files>`, then the whole web suite once at the end, `npx tsc --noEmit`, `npx eslint --quiet .`
- expected: green
- command: `pytest -q tests/contract/release_notes tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `tests/integration/releases` on a private database, `git diff --check`
- expected: green

## Integration contract

The integrator can rely on: (1) `SHOW_REVIEW_INDICATION` is the only reader-controlled input; no other flag, no environment variable; (2) with it `true` the markup of every screen of P-02 equals the base's (proved by tests that pin the old text); (3) the live journey manifest needs two edits outside this task (P-06); (4) `0.9.0` is revision 2 and still dated 2026-10-28.

## Failure/idempotency/security cases

- A constant ignored by a presentation function (always on, or always off) is caught by the per-state tests (mutation table in the report).
- A gated string that reaches a view without the switch is caught by the static guard (mutation: remove the condition around one string).
- The summary label and the pack attestation must stay present in both states (a test fails if either is gated).

## Rollback / feature flag

This task is the feature flag: restoring the wording is `SHOW_REVIEW_INDICATION = true` and, in the same commit, the pin test `review-indication-default.test.ts`, which names the beta default.

## Handoff

- changed files: see `docs/program/REVIEW-INDICATION-SWITCH-01.md`
- commands/results: see the same report
- known limits: see the same report
- integration notes: see the same report
