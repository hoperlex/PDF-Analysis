# Task WEB-SECTION-COPY-01 — the dashboard sections panel and the section catalogue say what is true after W59 and PROD-11

task_id: WEB-SECTION-COPY-01
status: in progress in lane `agent/web-section-copy-01` (wave PW4, lane WC; nothing pushed, merged or tagged)

## Outcome

The dashboard sections panel stops saying that the row «Без раздела» comes from the upload form, and says what the server counts: a document stands in the section an expert confirmed for its current version, and a document whose current version is not confirmed stands in «Без раздела». `PROJECT_SECTIONS` stops marking only АР as «analysed»: every one of the fifteen sections carries the route that analyses it (`analysedBy`: fourteen by their text profile, АР by the six-Run group), and a unit test holds the fourteen to the profile packages the server loads. Every sentence a user reads stays Russian, plain and free of internal identifiers and of invented numbers.

## Depends on

- `W59-SECTION-UI-01` — completed; the version classification panel and the project structure the new sentence points to.
- `W59-SECTION-SEAL-01` — completed; the registry of fourteen text profiles and the dashboard breakdown by confirmed classification.
- `PROD-11-AR-V1-V2-REMOVAL-01` — completed; АР has no text profile and is analysed by the six-Run group only.
- `ROADMAP-GAP-2026-10-27` — completed document; step 16 names the stale copy.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.7.0`, unchanged (`contracts/**`, `web/openapi/**`, the generated client and `web/FRONTEND_LOCK.json` are not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id`, unchanged
- base commit: `6075df889beef40084d337f03d2a072349fc9620`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the dashboard panel blames the upload form for «Без раздела» although the server counts by the expert-confirmed classification, and `PROJECT_SECTIONS.analysed` is true for АР only although fourteen sections have a text profile and АР is analysed by the six-Run group

### P-01 — the stale strings and the field that is true for one section only

- captured_at: 2026-10-27
- command: `grep -rnE "Без раздела|analysed|загрузки" web/src/widgets/dashboard web/src/entities/project web/src/_pages`
- captured_output:
  ```text
  web/src/widgets/dashboard/ui/sections-panel.tsx:62:        загрузке. Форма загрузки в этом продукте раздел не предлагает, поэтому документ,
  web/src/widgets/dashboard/ui/sections-panel.tsx:63:        отправленный через неё, остаётся без раздела — вот откуда строка «Без раздела» ниже,
  web/src/widgets/dashboard/ui/sections-panel.tsx:68:          <li key={section.code} data-section={section.code} data-analysed={section.analysed}>
  web/src/widgets/dashboard/ui/sections-panel.tsx:74:          Без раздела: <strong>{summary.unclassifiedCount}</strong>
  web/src/entities/project/model/section.ts:28: * unclassified at the storage layer that now exists to record one. `analysed` below still
  web/src/entities/project/model/section.ts:41: * section can run is the API's `SectionReviewOption.executable`, not the `analysed` flag
  web/src/entities/project/model/section.ts:96:  readonly analysed: boolean;
  web/src/entities/project/model/section.ts:103:  { code: 'AR', abbr: 'АР', name: 'Архитектурные решения', analysed: true },
  web/src/entities/project/model/section.ts:104:  { code: 'AI', abbr: 'АИ', name: 'Архитектурные решения (интерьер)', analysed: false },
  web/src/entities/project/model/section.ts:105:  { code: 'KM', abbr: 'КМ', name: 'Конструкции металлические', analysed: false },
  web/src/entities/project/model/section.ts:106:  { code: 'KJ', abbr: 'КЖ', name: 'Конструкции железобетонные', analysed: false },
  web/src/entities/project/model/section.ts:107:  { code: 'OV', abbr: 'ОВ', name: 'Отопление, вентиляция и кондиционирование', analysed: false },
  web/src/entities/project/model/section.ts:108:  { code: 'EOM', abbr: 'ЭОМ', name: 'Электроснабжение и электрооборудование', analysed: false },
  web/src/entities/project/model/section.ts:109:  { code: 'VK', abbr: 'ВК', name: 'Водоснабжение и канализация', analysed: false },
  web/src/entities/project/model/section.ts:110:  { code: 'PT', abbr: 'ПТ', name: 'Противопожарный водопровод', analysed: false },
  web/src/entities/project/model/section.ts:111:  { code: 'PB', abbr: 'ПБ', name: 'Пожарная безопасность', analysed: false },
  web/src/entities/project/model/section.ts:112:  { code: 'SS', abbr: 'СС', name: 'Слаботочные системы', analysed: false },
  web/src/entities/project/model/section.ts:113:  { code: 'ITP', abbr: 'ИТП', name: 'Индивидуальный тепловой пункт', analysed: false },
  web/src/entities/project/model/section.ts:114:  { code: 'GP', abbr: 'ГП', name: 'Генеральный план', analysed: false },
  web/src/entities/project/model/section.ts:115:  { code: 'TX', abbr: 'ТХ', name: 'Технологические решения', analysed: false },
  web/src/entities/project/model/section.ts:116:  { code: 'POS', abbr: 'ПОС', name: 'Проект организации строительства', analysed: false },
  web/src/entities/project/model/section.ts:117:  { code: 'PS', abbr: 'ПЗ', name: 'Пояснительная записка', analysed: false },
  ```
- interpretation: Two stale places named by the brief. (1) `sections-panel.tsx:61-64` blames the upload form for the row «Без раздела» (the form «does not offer a section», so a document sent through it «stays without a section»). (2) `section.ts:96-117` types `analysed` as a boolean that is `true` for АР and `false` for the other fourteen. `section.ts:28` and `:41` are the comments that define it. Nothing else under `web/src/_pages` matches.

### P-02 — who reads `analysed`, `ANALYSED_SECTION_CODE` and `data-analysed`

- captured_at: 2026-10-27
- command: `grep -rnE '\.analysed\b|analysed:|ANALYSED_SECTION_CODE|data-analysed' web/src web/tests tests/e2e --exclude-dir=generated --exclude-dir=node_modules`
- captured_output:
  ```text
  web/src/widgets/section-specification/ui/section-specification-section.tsx:24:import { ANALYSED_SECTION_CODE, projectSectionTitle, sectionsInStructureOrder } from '@/entities/project';
  web/src/widgets/section-specification/ui/section-specification-section.tsx:63:  const [sectionCode, setSectionCode] = useState<ContractProjectSection>(ANALYSED_SECTION_CODE);
  web/src/widgets/dashboard/ui/sections-panel.tsx:68:          <li key={section.code} data-section={section.code} data-analysed={section.analysed}>
  web/src/entities/project/model/section.ts:96:  readonly analysed: boolean;
  web/src/entities/project/model/section.ts:100:export const ANALYSED_SECTION_CODE: ProjectSectionCode = 'AR';
  web/src/entities/project/model/section.ts:103:  { code: 'AR', abbr: 'АР', name: 'Архитектурные решения', analysed: true },
  web/src/entities/project/model/section.ts:104:  { code: 'AI', abbr: 'АИ', name: 'Архитектурные решения (интерьер)', analysed: false },
  web/src/entities/project/model/section.ts:105:  { code: 'KM', abbr: 'КМ', name: 'Конструкции металлические', analysed: false },
  web/src/entities/project/model/section.ts:106:  { code: 'KJ', abbr: 'КЖ', name: 'Конструкции железобетонные', analysed: false },
  web/src/entities/project/model/section.ts:107:  { code: 'OV', abbr: 'ОВ', name: 'Отопление, вентиляция и кондиционирование', analysed: false },
  web/src/entities/project/model/section.ts:108:  { code: 'EOM', abbr: 'ЭОМ', name: 'Электроснабжение и электрооборудование', analysed: false },
  web/src/entities/project/model/section.ts:109:  { code: 'VK', abbr: 'ВК', name: 'Водоснабжение и канализация', analysed: false },
  web/src/entities/project/model/section.ts:110:  { code: 'PT', abbr: 'ПТ', name: 'Противопожарный водопровод', analysed: false },
  web/src/entities/project/model/section.ts:111:  { code: 'PB', abbr: 'ПБ', name: 'Пожарная безопасность', analysed: false },
  web/src/entities/project/model/section.ts:112:  { code: 'SS', abbr: 'СС', name: 'Слаботочные системы', analysed: false },
  web/src/entities/project/model/section.ts:113:  { code: 'ITP', abbr: 'ИТП', name: 'Индивидуальный тепловой пункт', analysed: false },
  web/src/entities/project/model/section.ts:114:  { code: 'GP', abbr: 'ГП', name: 'Генеральный план', analysed: false },
  web/src/entities/project/model/section.ts:115:  { code: 'TX', abbr: 'ТХ', name: 'Технологические решения', analysed: false },
  web/src/entities/project/model/section.ts:116:  { code: 'POS', abbr: 'ПОС', name: 'Проект организации строительства', analysed: false },
  web/src/entities/project/model/section.ts:117:  { code: 'PS', abbr: 'ПЗ', name: 'Пояснительная записка', analysed: false },
  web/src/entities/project/index.ts:20:  ANALYSED_SECTION_CODE,
  web/tests/unit/projects/project-sections.test.ts:22:  ANALYSED_SECTION_CODE,
  web/tests/unit/projects/project-sections.test.ts:94:    expect(PROJECT_SECTIONS.filter((section) => section.analysed).map((s) => s.code))
  web/tests/unit/projects/project-sections.test.ts:95:      .toEqual([ANALYSED_SECTION_CODE]);
  web/tests/unit/projects/project-sections.test.ts:96:    expect(ANALYSED_SECTION_CODE).toBe('AR');
  web/tests/unit/projects/project-sections.test.ts:100:    expect(findProjectSection(ANALYSED_SECTION_CODE)?.analysed).toBe(true);
  ```
- interpretation: Only three consumers exist outside the registry: the dashboard panel writes `data-analysed` (no test, no journey step and no stylesheet reads that attribute), the unit test `project-sections.test.ts` pins the field, and `widgets/section-specification` imports `ANALYSED_SECTION_CODE` as the initial choice of its section picker (`section-specification-section.tsx:63`). That widget belongs to another owner, so the export stays and keeps its value `'AR'`; only its comment changes. The picker carries no copy about «analysed», so it is not touched.

### P-03 — the stale paragraph and the row markup as they are today

- captured_at: 2026-10-27
- command: `sed -n 56,79p web/src/widgets/dashboard/ui/sections-panel.tsx`
- captured_output:
  ```text
    const { summary } = result;

    return (
      <div data-panel="per-section-breakdown">
        <p className="am-state__correlation">
          Раздел документа сохраняется и проверяется на сервере, когда его называют при
          загрузке. Форма загрузки в этом продукте раздел не предлагает, поэтому документ,
          отправленный через неё, остаётся без раздела — вот откуда строка «Без раздела» ниже,
          а не из пропуска в подсчёте.
        </p>
        <ul data-section-count={PROJECT_SECTIONS.length}>
          {PROJECT_SECTIONS.map((section) => (
            <li key={section.code} data-section={section.code} data-analysed={section.analysed}>
              {projectSectionTitle(section)}
              : <strong>{summary.byCode[section.code]}</strong>
            </li>
          ))}
          <li data-section="unclassified">
            Без раздела: <strong>{summary.unclassifiedCount}</strong>
          </li>
        </ul>
      </div>
    );
  }
  ```
- interpretation: The sentence to replace is the `<p className="am-state__correlation">` block. The `<ul data-section-count>`, the `<li data-section=…>` rows and `<li data-section="unclassified">` with `<strong>` are what the unit test and the browser journey (`dashboard-sections-panel`, `li[data-section="PB"] strong`) address; they stay.

### P-04 — what the number «Без раздела» really counts (server)

- captured_at: 2026-10-27
- command: `sed -n 112,127p src/auditmanager/dashboard/repository.py`
- captured_output:
  ```text
  )

  #: Published documents by the section their **current version** is confirmed in
  #: (`SECTION-READ-MODEL-01`, `W59-SECTION-IDENTITY-DECISION-01`). ``document.current_version_uid``
  #: selects the version -- the same join ``DocumentRepository._LIST_PROJECTS`` counts through,
  #: so "a document" means one with a published current version here as in every other count
  #: this contract publishes -- and that version's row in ``version_classification_current`` is
  #: its confirmed section: the latest revision, so a section an expert corrected
  #: (`CLASSIFICATION-CORRECTION-01`) counts under the corrected one and never under the original.
  #: The ``LEFT JOIN`` is the unclassified rule: a current version no
  #: expert has classified has no row, so ``section_code`` is NULL and ``GROUP BY`` puts every
  #: such document in one NULL group, which SQL already groups together, rather than this query
  #: having to special-case it. The legacy ``document.section`` is **not read at all**: it is
  #: the old document-level label, not an expert's confirmation, and an older version's
  #: classification never counts for the set whose head moved on.
  _DOCUMENTS_BY_SECTION = text(
  ```
- interpretation: The count is of documents with a published current version, placed by the expert-confirmed classification of that version; the unclassified bucket is a current version no expert has classified. The legacy `document.section` is not read, and the upload does not enter it. So the stale sentence is false twice: the cause is not the upload form, and the section is not «named at upload» but confirmed by an expert on the version screen (`W59-SECTION-UI-01`, `D-180` closed).

### P-05 — the fourteen text-profile packages the server loads

- captured_at: 2026-10-27
- command: `grep -rn '"section_code"' src/auditmanager/analysis/text/profiles --include=profile.json`
- captured_output:
  ```text
  src/auditmanager/analysis/text/profiles/pos/profile.json:3:  "section_code": "POS",
  src/auditmanager/analysis/text/profiles/ov/profile.json:3:  "section_code": "OV",
  src/auditmanager/analysis/text/profiles/itp/profile.json:3:  "section_code": "ITP",
  src/auditmanager/analysis/text/profiles/ss/profile.json:3:  "section_code": "SS",
  src/auditmanager/analysis/text/profiles/tx/profile.json:3:  "section_code": "TX",
  src/auditmanager/analysis/text/profiles/kj/profile.json:3:  "section_code": "KJ",
  src/auditmanager/analysis/text/profiles/km/profile.json:3:  "section_code": "KM",
  src/auditmanager/analysis/text/profiles/pt/profile.json:3:  "section_code": "PT",
  src/auditmanager/analysis/text/profiles/ai/profile.json:3:  "section_code": "AI",
  src/auditmanager/analysis/text/profiles/ps/profile.json:3:  "section_code": "PS",
  src/auditmanager/analysis/text/profiles/pb/profile.json:3:  "section_code": "PB",
  src/auditmanager/analysis/text/profiles/eom/profile.json:3:  "section_code": "EOM",
  src/auditmanager/analysis/text/profiles/gp/profile.json:3:  "section_code": "GP",
  src/auditmanager/analysis/text/profiles/vk/profile.json:3:  "section_code": "VK",
  ```
- interpretation: Fourteen packages, one per section other than АР: AI EOM GP ITP KJ KM OV PB POS PS PT SS TX VK. This is the set `analysedBy: 'text_profile'` must equal; the new unit test reads these files so that a package added or removed fails the registry test instead of leaving the screen stale again.

### P-06 — АР has no text profile and is analysed by the six-Run group (server)

- captured_at: 2026-10-27
- command: `sed -n 1,12p src/auditmanager/analysis/text/profile_registry.py`
- captured_output:
  ```text
  """The section-keyed text-profile registry (`W59-SECTION-SEAL-01`).

  Run start routes a version's **persisted, expert-confirmed** section to the analysis profile
  registered here; the executor resolves the run's pinned profile through the same registry so
  every v1-style text run executes with its own prompt bundle. A section with no entry is
  refused at run start -- there is no AR fallback.

  **АР is not registered** (`PROD-11-AR-V1-V2-REMOVAL-01`, `ADR-0024` section 2, `AD-12`): the АР
  analysis path of production is the six-Run v3 group, not a text profile. The AR v1 constants were
  this registry's first entry until that task; they are gone, so ``startRun`` and ``reauditRun`` on
  a version classified АР answer ``section_profile_unavailable`` and ``listAnalysisProfiles`` answers
  ``profile: null`` for АР. There is no ``profiles/ar/`` package and one is refused (a package may
  ```
- interpretation: `profile_registry.py` states it: АР is not registered, run start answers `section_profile_unavailable` for it, `listAnalysisProfiles` answers `profile: null`, and a package for АР is refused. The production АР path is the six-Run v3 group. `analysed: true` for АР and `false` for the rest therefore says the opposite of the server.

### P-07 — the Russian wording the product already uses for the АР path

- captured_at: 2026-10-27
- command: `grep -n "шести проверок" web/src/entities/analysis-profile/model/presentation.ts web/src/widgets/version-classification/ui/version-classification.tsx`
- captured_output:
  ```text
  web/src/entities/analysis-profile/model/presentation.ts:34:  'Версия АР анализируется группой из шести проверок АР v3; обычный прогон по ней будет отклонён.';
  web/src/entities/analysis-profile/model/presentation.ts:38:  'Версия АР анализируется группой из шести проверок АР v3, а не обычным прогоном. Группа ' +
  web/src/widgets/version-classification/ui/version-classification.tsx:117:                отклонён. Версия АР анализируется группой из шести проверок АР v3.
  ```
- interpretation: The product says «группой из шести проверок АР v3» (`presentation.ts`, `version-classification.tsx`). The catalogue uses the same route names; a unit test for the new field reads no user text, so no new Russian sentence about the АР path is needed on the dashboard.

### P-08 — the tests that pin this copy

- captured_at: 2026-10-27
- command: `grep -rnE 'Без раздела|sections-panel|ANALYSED_SECTION_CODE|\.analysed\b' web/tests tests/e2e/pc01/journey/manifest.json --exclude-dir=node_modules`
- captured_output:
  ```text
  web/tests/unit/widgets/dashboard.test.ts:27: *   2. the unclassified `<li>` deleted from `sections-panel.tsx` — caught by
  web/tests/unit/widgets/dashboard.test.ts:333:    expect(visible(markup)).toContain(`Без раздела: ${PROJECT_SECTIONS.length + 1}`);
  web/tests/unit/widgets/dashboard.test.ts:335:    // `<li data-section="unclassified">` block from `sections-panel.tsx` drops both
  web/tests/unit/widgets/dashboard.test.ts:416: *   1. Y's M5 — `sections-panel.tsx` reading `PROJECT_SECTIONS[(i + 1) % length]`'s code
  web/tests/unit/projects/project-sections.test.ts:22:  ANALYSED_SECTION_CODE,
  web/tests/unit/projects/project-sections.test.ts:94:    expect(PROJECT_SECTIONS.filter((section) => section.analysed).map((s) => s.code))
  web/tests/unit/projects/project-sections.test.ts:95:      .toEqual([ANALYSED_SECTION_CODE]);
  web/tests/unit/projects/project-sections.test.ts:96:    expect(ANALYSED_SECTION_CODE).toBe('AR');
  web/tests/unit/projects/project-sections.test.ts:100:    expect(findProjectSection(ANALYSED_SECTION_CODE)?.analysed).toBe(true);
  tests/e2e/pc01/journey/manifest.json:5958:        "name": "dashboard-sections-panel",
  tests/e2e/pc01/journey/manifest.json:5961:        "control_module": "web/src/widgets/dashboard/ui/sections-panel.tsx",
  ```
- interpretation: `project-sections.test.ts:92-101` is the only test that pins the field (`filter(section => section.analysed)` equals `['AR']`, `ANALYSED_SECTION_CODE` is `'AR'`, the code is in the registry and `.analysed` is `true`). No test and no journey step pins the stale sentence; `dashboard.test.ts:333` pins the row «Без раздела: N», which stays. The journey manifest names `sections-panel.tsx` only as a control module for `li[data-section="PB"] strong`.

### P-09 — the dashboard digit guard: new copy must carry no digit

- captured_at: 2026-10-27
- command: `sed -n 264,271p web/tests/unit/widgets/dashboard.test.ts`
- captured_output:
  ```text
  describe('every number the dashboard renders is the fixture, and nothing else is a number', () => {
    it('renders exactly the fixture’s numbers, nothing invented', () => {
      const markup = render(SUMMARY);
      const expected = expectedNumberTokens(SUMMARY);
      const rendered = renderedNumberTokens(markup);
      const invented = rendered.filter((token) => !expected.has(token));
      expect(invented, `rendered numbers not in the fixture: ${invented.join(', ')}`).toEqual([]);
    });
  ```
- interpretation: `renders exactly the fixture's numbers, nothing invented` fails on any digit token in the visible text that is not a fixture count. The new sentence therefore says «каждый раздел» and does not write «15» or «14».

### P-10 — other places that still say АР-only or promise a profile for АР (second-place search)

- captured_at: 2026-10-27
- command: `grep -rnE "строятся только для АР|комплектов раздела АР|вендор-листа раздела АР|профиль раздела появится" web/src --exclude-dir=generated`
- captured_output:
  ```text
  web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx:78:        title="В проекте нет комплектов раздела АР"
  web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx:254:        измерения и валюты от поставщика из вендор-листа раздела АР. Цены берутся только из
  web/src/widgets/specification-prices/ui/specification-prices-section.tsx:56:        title="В проекте нет комплектов раздела АР"
  web/src/entities/audit-run/model/routing-refusal.ts:43:    'возможен, когда профиль раздела появится.',
  web/src/entities/optimisation-proposal/model/failure.ts:21:    'Текущая версия комплекта подтверждена не как раздел АР: предложения строятся только для АР.',
  web/src/shared/api/catalog-message.ts:136:    'профиль раздела появится.',
  ```
- interpretation: Five more stale statements, none in this lane's allowed paths: the two optimisation screens and `entities/optimisation-proposal` (АР-only, owned by `OPT-PROJECT-ALL-SECTIONS-01`), and `entities/audit-run/model/routing-refusal.ts:38-45` with `shared/api/catalog-message.ts:133-136`, whose refusal sentence promises that the run becomes possible «когда профиль раздела появится» (true for a section with a missing profile, false for АР, which never gets one). `run-list.tsx` avoids showing that sentence for an АР version whose section is known; it can still appear for a press made before the version is read. Listed in the report, not edited.

### P-11 — the stale operation text of `uploadDocument` (contract owner)

- captured_at: 2026-10-27
- command: `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));ops=[o for p in d['paths'].values() for o in p.values() if isinstance(o,dict) and o.get('operationId')=='uploadDocument'];t=ops[0]['description'];i=t.index('The analysis is built');print(t[i:i+205])"`
- captured_output:
  ```text
  The analysis is built for AR (architectural solutions) text and is applied to any uploaded document; a stated `section` is stored and counted but neither selects nor refuses the analysis (D-110).

  A third 
  ```
- interpretation: This sentence in `contracts/api/v1/openapi.json` (mirrored in `web/openapi/openapi.json` and the generated client) describes the pre-W59 state. It is the contract owner's (`OPT-PROJECT-ALL-SECTIONS-01` reseals the contract in this wave) and is not edited here.

### P-12 — baseline of the tests this lane touches, before any edit

- captured_at: 2026-10-27
- command: `cd web && npx vitest run --reporter=dot tests/unit/widgets/dashboard.test.ts tests/unit/projects/project-sections.test.ts tests/unit/projects/section-catalogue.test.ts tests/guards/rendered-language.guard.test.ts`
- captured_output:
  ```text

   RUN  v3.2.7 /root/projects/PDF-Analysis/.local/worktrees/web-section-copy-01/web

  ·····························································

   Test Files  4 passed (4)
        Tests  61 passed (61)
     Start at  02:08:25
     Duration  82.74s (transform 1.91s, setup 0ms, collect 37.47s, tests 44.99s, environment 0ms, prepare 46ms)
  ```
- interpretation: Four files, 61 tests, all green on the base `6075df88` with `web/node_modules` symlinked from the gate-night worktree: `rendered-language.guard` 26, `dashboard` 19, `project-sections` 8, `section-catalogue` 8.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/widgets/dashboard/**`
- `web/src/entities/project/**`
- `web/tests/unit/widgets/dashboard.test.ts`
- `web/tests/unit/projects/project-sections.test.ts`
- `docs/program/tasks/WEB-SECTION-COPY-01.md`
- `docs/program/WEB-SECTION-COPY-01.md`

## Forbidden hotspots

- `contracts/**`, `web/openapi/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`
- `src/**`, `db/**`, `infra/**`, `fixtures/**`
- every other widget, entity, feature and page (the optimisation screens, `entities/audit-run`, `entities/optimisation-proposal`, `shared/api`), global styles, `web/package*.json`, the root lock files
- `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals

- A section picker on the upload form (`D-107`); the upload form needs none, because the expert confirms the section on the version screen.
- A visible per-section «how it is analysed» label on the dashboard; the field is data, not a new screen element.
- The AR-only wording of the optimisation screens, the refusal sentence that promises a profile for АР, and the `uploadDocument` operation text: listed in the report for their owners.
- Renaming the `ANALYSED_SECTION_CODE` export (another widget imports it).
- The section picker widget `web/src/widgets/section-specification/**`: it carries no copy about «analysed» (P-02), so it is not in the allowed paths; `web/tests/guards/rendered-language.guard.test.ts` and `web/tests/unit/projects/section-catalogue.test.ts` are read and run, not edited.
- The base commit is the tip of `integration/ar-close-1026`.

## Deliverables

- the new sentence in `web/src/widgets/dashboard/ui/sections-panel.tsx` and the rewritten comments that described the removed behaviour;
- `PROJECT_SECTIONS[i].analysedBy` (`'text_profile'` for fourteen, `'six_run_group'` for АР) replacing the boolean `analysed`; `data-analysed-by` replacing `data-analysed`;
- tests: the rewritten registry test, new dashboard cases, each with a quoted mutation;
- `docs/program/WEB-SECTION-COPY-01.md`.

## Required tests

- command: `cd web && npx vitest run tests/unit/widgets/dashboard.test.ts tests/unit/projects tests/guards/rendered-language.guard.test.ts`
- expected: green; the new cases fail under the quoted mutations in the report
- command: `cd web && npx tsc --noEmit` and `cd web && npx eslint` on the changed files
- expected: no output
- command: the governance one-liner for this file prints `[]`; `tests/contract/program`, `tests/contract/api_v1/test_doc_prose_facts.py`, `tests/contract/api_v1/test_surface_counts_in_prose.py` and `tests/e2e/test_pc01_journey_conformance.py` pass on the committed tree

## Integration contract

- `PROJECT_SECTIONS[i].analysed` (boolean) no longer exists; the integrator can rely on `analysedBy`. No file outside this lane reads the old field (P-02). If a lane merged later adds a reader of `.analysed`, `tsc` fails on the merge.
- `ANALYSED_SECTION_CODE` is still exported with the value `'AR'`; it is now documented as the default choice of section pickers.
- The panel keeps `data-panel="per-section-breakdown"`, `data-section-count`, `li[data-section=…]` with `<strong>` and `li[data-section="unclassified"]`, which the unit test and the browser journey address.
- No contract, route, error code, migration or screen is added.

## Failure/idempotency/security cases

- A breakdown that is not the closed vocabulary still renders the fault and no numbers (unchanged, existing cases).
- The new sentence contains no digit, so the «no invented number» guard stays meaningful.
- The registry test fails when a text profile package is added or removed without the catalogue changing, and when АР is given a text profile.

## Rollback / feature flag

Not applicable: a copy and data-shape change inside the web bundle, reverted by reverting the lane's commits. No flag, no data, no contract.

## Handoff

- changed files: see `docs/program/WEB-SECTION-COPY-01.md`
- commands/results: see `docs/program/WEB-SECTION-COPY-01.md`
- known limits: see `docs/program/WEB-SECTION-COPY-01.md`
- integration notes: see `docs/program/WEB-SECTION-COPY-01.md`
