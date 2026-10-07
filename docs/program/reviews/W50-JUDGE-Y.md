# W50-JUDGE-Y — независимый архитектурный вердикт

**Subject:** `92001f7852266f39ef1f9ab9dd4562c982823a7a` (`integration/w50` = `origin/dev` при начале прохода).
**Дата:** 2026-10-07. **Ветка:** `agent/w50-judge-y`.
**Первичный вердикт:** **PASS с двумя register-находками по прозе**. Release-blocking и must-fix-before-merge находок нет. Первичный проход и этот вердикт выполнены без чтения отчётов лейнов, QA или Judge X.

## Границы и среда

Прочитаны `AGENTS.md`, `docs/program/CURRENT_STATE.md`, `docs/program/tasks/W50-JUDGE-Y.md`, его `depends_on` (`W50-QA-01.md`), `docs/program/dispatch/W50-PLAN.md`, `docs/program/W50-FREEZE-01.md` и `docs/program/dispatch/W48-JUDGES.md`. Контрольный SHA совпал с `HEAD` и `origin/dev`. Проверены frozen inputs: `git ls-tree HEAD web/package.json web/package-lock.json web/FRONTEND_LOCK.json` дал P-01 blobs `3ea4aede04af84823821e115f8312c545faec30e`, `3b986e543b1be7fc654d94aee17963382f664143`, `14fc4b48026640a195f8dd1e66a09a6ff7251666`; `git diff --name-only ead639f HEAD -- contracts db/migrations web/src/_app/providers.tsx web/package.json web/package-lock.json web/FRONTEND_LOCK.json` пуст. Новых contracts нет; head остаётся `0015_accounts_roles_registration`.

Node `v22.23.1`, Next `15.5.25`. Измерения сделаны в одном временном clone `.local/w50-jy-build` с одним `npm ci --offline` и чистой `web/.next` перед каждым checkout/build. До каждого build `df -B1` показывал более 3 GB available (19–21 GB в ходе прохода), `ps` не находил `make gate`; каждый `next build` выполнялся под `flock -x .local/w50-stage-e-build.lock`. Полный `make gate` здесь не запускался по `AGENTS.md` §8. Никаких stand-сервисов и портов не создавалось. Ни одной credential/cookie/session value в доказательствах нет.

## Архитектурная проверка

- `web/tests/guards/eslint-boundary.guard.test.ts` проверяет deep import, upward import, raw fetch и контрольный разрешённый import. Я дополнительно вставил в **копию** `web/src/entities/account/model/account.ts` импорт `@/widgets/dashboard`: `npm --prefix web run lint -- --quiet` вышел 1 с `no-restricted-imports`, текстом `FSD boundary: entities may not import widgets`. После восстановления lint вышел 0. `transport-boundary.guard.test.ts` прошёл; прямой `fetch` вне `shared/api` в копии frame сделал его красным (ниже).
- `rg -n 'href=' web/src/_app` на subject находит только `HOME_SCREEN`, `SIGN_IN_SCREEN`, `home.address`, `item.href`; `frame-sources.test.ts` дополнительно парсит литералы всех `_app` TS/TSX. Единственный адрес выхода из frame — `SESSION_CLOSE_PATH` из feature. Смена `href={HOME_SCREEN}` на `href="/projects"` в копии дала ожидаемый red.
- Registry, `page.tsx`, journey manifest и `SEEDS` в `route-screens.ts` покрывают одно множество из **23** экранов. Для каждой страницы `screen-guard.guard.test.ts` проверяет ожидаемый `await requireScreen('<own address>', { params, searchParams })`; `requireAChangedPassword` отсутствует в исполняемом `web/src`. Однострочные drift-пробы для каждого из четырёх источников дали red с адресом `/queue` или `/dashboard` (см. ниже). Static guards проверяют и реальный вызов, и guest/default/profile/role решения; текущий registry имеет только `any`, поэтому роль-гейт проверяется fixture, как требует `R-60`.
- `R-66`: `SCREEN_REGISTRY` имеет группы и порядок `Работа: /projects, /dashboard, /section-optimisation`; `Знания: /knowledge-base, /blocks, /norms`; `Система: /logs, /workers, /analysis-settings, /queue`. `/optimisation` — `hidden`, `inMenu: false`, `session` и доступен по прямому адресу. Четыре новых stub имеют `session`/`any` и рендерят `RoutePlaceholder` без выдуманных чисел. Соответствующие registry и QA тесты зелёные.
- Пять lazy wrappers используют `next/dynamic` и объявляют typed loading. `lazy-boundary.guard.test.ts` сканирует статические import edges из `_pages`, запрещает production-provider eager seam и проверяет каждый виджет в census markup. Прямой замер в копии с временным `console.log`: **90 screens / 171 light pairs / 171 dark pairs**, выше frozen baseline **80 / 150 / 150**. Удаление одного eager provider дало red на dashboard. `rendered-language.guard.test.ts` и `screen-claims-about-the-system.guard.test.ts` прошли.
- `styling-layer.test.ts` подтвердил правила для всех именованных `am-` классов; удаление `.am-app__brand` в копии дало red. Тест avatar palette подтвердил **14 пар × 2 темы**, контраст текста ≥4.5:1 и круга к page/bar ≥3:1; замена первого light background на белый дала red. `Avatar` принимает `colourKey={session.login}` (e-mail), не `displayLabel`; `entities/account` выдаёт `UnknownRoleError` для неизвестной роли, frame/home показывают явный fault, а BFF отказывает malformed `getMe`/session row. Просмотр нового кода не обнаружил бизнес-логики в UI, deep imports или silent fallback.

## Bundle: точные gzip-9 bytes

Метод: для каждого `.../page` в `.next/app-build-manifest.json` сумма `zlib.gzipSync(file, {level: 9}).length` для перечисленных `.js`; CSS не входит. Все четыре build (`96a1653`, `d0d71ad`, `d8112cb`, subject) завершились exit 0; повторные clean build `d8112cb` и subject дали byte-identical route totals. В таблице первый delta — Stage-A→LAZY, второй — Stage-B→subject.

Для последнего delta `F` означает общий webpack chunk **−4 B** плюс изменённый client/frame chunk `4229` **+730 B** (= **+726 B**), вследствие Stage-C `_app` navigation/account islands и переноса `screenDecision` в shared config. `N` добавляет **+23 B** в shared chunk `4327` на маршрутах, которые его перечисляют. Дополнительные изменения в `page`, `1423` и `3543` указаны точно; это rebundle существующих page/shared chunks после тех же Stage-C imports, а не код другого lane. `/_not-found` перечисляет только изменённый webpack chunk. `git diff --name-only d8112cb 92001f7852266f39ef1f9ab9dd4562c982823a7a -- web/src` ограничен `_app/*`, `app/layout.tsx`, `app/bff/session/screen-lock.ts`, `shared/config/*`, что исключает необъяснённый product delta.

| Route | Stage A | LAZY | Δ A→L | Stage B | Subject | Δ B→S | Причина B→S |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `/` | 111388 | 112120 | +732 | 135351 | 136099 | +748 | F+N; page −1 |
| `/403` | 123327 | 124064 | +737 | 126880 | 127606 | +726 | F |
| `/_not-found` | 102681 | 103417 | +736 | 103403 | 103399 | −4 | webpack −4 |
| `/account` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/account/password` | 114756 | 115493 | +737 | 118306 | 119032 | +726 | F |
| `/analysis-settings` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/blocks` | 135389 | 136120 | +731 | 137808 | 138558 | +750 | F+N; 1423 +1 |
| `/dashboard` | 142653 | 117579 | **−25074** | 122651 | 123400 | +749 | F+N |
| `/knowledge-base` | 129496 | 127144 | **−2352** | 132209 | 132953 | +744 | F+N; page −5 |
| `/login` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/logs` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/norms` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/optimisation` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/projects` | 133074 | 133717 | +643 | 135407 | 136156 | +749 | F+N |
| `/projects/[project_uid]` | 138987 | 139719 | +732 | 141408 | 142180 | +772 | F+N; 1423 +1, page +22 |
| `/projects/[project_uid]/documents/[document_uid]` | 134675 | 135407 | +732 | 137096 | 137846 | +750 | F+N; 1423 +1 |
| `/projects/[project_uid]/runs/[run_id]` | 139365 | 131583 | **−7782** | 133285 | 134034 | +749 | F+N |
| `/projects/[project_uid]/runs/[run_id]/review` | 145215 | 146585 | +1370 | 148283 | 149030 | +747 | F+N; 3543 −1, page −1 |
| `/projects/[project_uid]/versions/[version_uid]` | 146274 | 147308 | +1034 | 148997 | 149766 | +769 | F+N; 3543 −1, 1423 +1, page +20 |
| `/projects/[project_uid]/versions/[version_uid]/comparison` | 145911 | 136045 | **−9866** | 137733 | 138483 | +750 | F+N; 1423 +1 |
| `/queue` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/section-optimisation` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/workers` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |

§3.4 на нормативной паре выполнен: четыре маршрута, где widget был на first load, уменьшились; у остальных максимум **+1370 B**, меньше **1536 B**. Evidence-viewer на `/review` не был first-load widget: его route +1370 B относится к разрешённому runtime cost.

## Проверки и красные пробы

На чистом subject в disposable clone:

| Команда | Результат |
| --- | --- |
| `npm --prefix web ci --offline --no-audit --no-fund` | exit 0, 184 packages, lock без изменений |
| `npm --prefix web run lint -- --quiet` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `npm --prefix web test -- --run` | exit 0, **105 files / 1660 tests passed** |
| `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/e2e/test_pc01_journey_conformance.py tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/program/test_wave_governance.py` | exit 0, **163 passed** |
| `git diff --check` | exit 0 |

Первый sandbox `npm ci` вышел 1: `esbuild` child `spawnSync … EPERM`; auto-reviewed escalated повтор вышел 0. Первый sandbox `npm test` вышел 1: 6 fixture failures из-за `spawnSync eslint EPERM` и пустого output дочернего `tsc`; escalated повтор выше прошёл целиком. Это ограничение sandbox subprocess, а не red subject.

Все пробы ниже внесены только в disposable clone и восстановлены побайтово после измерения; его `git status --short` остался пуст. Каждый указанный тест запускался как `npm --prefix web test -- --run <test>` (кроме Python journey и FSD lint).

| Мутация в копии | Красный guard, результат |
| --- | --- |
| Registry `/queue` → `/queue-drift` | `screen-registry.guard.test.ts` exit 1, 4 failures; `unregistered: /queue`, pageless drift и R-66 order |
| Dashboard route удалил `await requireScreen('/dashboard', { params, searchParams })` | `screen-guard.guard.test.ts` exit 1, 2 failures, назван `/dashboard` |
| Frame `href={HOME_SCREEN}` → `href="/projects"` | `frame-sources.test.ts` exit 1, `app-frame.tsx:82: /projects` |
| Статический import dashboard widget из `_pages` | `lazy-boundary.guard.test.ts` exit 1, static edge назван |
| `DashboardEagerSeam.Provider` получил `value: null` | `lazy-boundary.guard.test.ts` exit 1, `dashboard cold does not draw dashboard` |
| `.am-app__brand` rule переименован | `styling-layer.test.ts` exit 1, missing `am-app__brand` |
| Light avatar pair 01 заменён на белый background | `avatar-palette.test.ts` exit 1, 4 contrast failures |
| Footer заменён на «Ролей нет.» | `screen-claims-about-the-system.guard.test.ts` exit 1, 2 failures, включая rendered census |
| `fetch('/api/v1/projects')` вставлен в frame | `transport-boundary.guard.test.ts` exit 1, boundary violation |
| Journey `/queue` → `/queue-drift` | `test_pc01_journey_conformance.py` exit 1, **2 failed / 76 passed**, `/queue` назван |
| Seed `/queue` → `/queue-drift` | `screen-set.guard.test.ts` exit 1, 3 failures, missing `/queue` и orphan `/queue-drift` |
| Upward import `entities/account` → `widgets/dashboard` | `npm --prefix web run lint -- --quiet` exit 1, `no-restricted-imports`: `entities may not import widgets` |

## Находки

**JY-1 — register, неверное пояснение единого решения меню.** `web/src/shared/config/screen-registry.ts:250–254` говорит, что menu не может скрыть экран, который `screenDecision` открывает. `web/src/_app/navigation.ts:74–80` дополнительно фильтрует `inMenu` и допускает только menu groups. В самом registry `/optimisation` (`:180–186`) имеет `session`/`any`, `hidden`, `inMenu: false`: полная сессия открывает прямой URL, menu его правильно скрывает. Последствие — неверное архитектурное обещание в комментарии, способное подтолкнуть к удалению требуемого R-66 hidden route. Воспроизведение: сравнить `screenDecision(screenAt('/optimisation'), completeSubject) === 'open'` с `buildNavigation(completeSubject)`; адреса там нет. Поправка текста — «menu offers open **inMenu rows in visible groups**»; код менять не требуется.

**JY-2 — register, противоречивая численность baseline в controlling plan.** `docs/program/dispatch/W50-PLAN.md:108–115` после amendment требует падения first-load JS у «пяти target routes», но в том же абзаце перечисляет только четыре отрицательных delta. Задача Judge Y уже исправила предмет до «четырёх routes that carry their widget on first load». В измерении `/projects/[project_uid]/runs/[run_id]/review` вырос на **1370 B** в разрешённом пределе, остальные четыре упали. Последствие — будущий судья, читающий только §3.4, может ошибочно отклонить корректную сборку или считать собственный результат исключением без решения владельца. Воспроизведение: четыре отрицательных строки таблицы выше и `/review` +1370 B. Поправка — назвать четыре first-load routes и отдельно оговорить review fallback/runtime cost. Runtime код менять не требуется.

## Ограничения и передача

Этот entry point проверяет topology, source guards, exact bundle и статический render; реальный browser focus, outside click, HTTP status и stand console не проверялись мной и принадлежат black-box Judge X/QA. FSD и transport guard имеют известную границу source scan/ESLint: runtime eval и динамически сгенерированный код ими не доказываются; W50 не вводит такой путь. Сравнение bundle — конкретный Next 15.5.25 build и gzip-9 из manifest, не оценка сетевого кеша.

Интегратору: два register пункта принять как документационные поправки при разрешённом будущем grant; `W50-FIX` по integration contract открывается только для upheld release-blocking, которых этот проход не нашёл. Мой единственный изменённый tracked файл — `docs/program/reviews/W50-JUDGE-Y.md`; contracts, migrations, root manifests/locks, composition root и остальные forbidden hotspots не тронуты. Финальное доказательство после commit: `git diff --name-only 92001f7852266f39ef1f9ab9dd4562c982823a7a..HEAD` должно вывести только этот файл.
