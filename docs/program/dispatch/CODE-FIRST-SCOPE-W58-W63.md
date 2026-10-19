# W58–W63 — кодовый объём для последующих freeze

**Статус:** карта объёма от 2026-10-15 по `CODE-FIRST-SCOPE-01`, база
`origin/dev=88c83b22`. Это не write grant. Исторический слой W58–W63
в `ROADMAP-TO-BETA.md` §8 остаётся unadopted; R-135 и
`CODE-FIRST-TO-BETA.md` принимают его функциональный объём в кодовую очередь,
но требуют отдельного freeze каждого блока от актуального dev-кандидата.

Названия строк ниже — **кандидаты будущих задач**, а не task IDs для
`depends_on`. Каждый будущий task-файл фиксирует закрытых предшественников,
точные входные SHA, `allowed_paths` и единственного владельца hotspot.

| Блок / кандидат | Кодовый результат | Адресное доказательство | Вход для freeze |
| --- | --- | --- | --- |
| W58 / DEBT-CODE | Устранены требующие кода долги W53–W57 из актуального debt register; у каждого есть владелец. | Регрессия на каждый исправленный дефект и честный перечень оставшихся долгов. | W56b code close. |
| W58 / RECOVERY-CODE | Инструменты согласованного backup/restore DB и Blob, инструкция и отказные сценарии на изолированных данных. | Восстановление тестового набора, ссылочная целостность и безопасный повтор; стендовый drill остаётся B6. | W56b code close; один storage/DB owner. |
| W59 / SECTION-SEAL | Один владелец контракта и миграции вводит 15 разделов, стадию П/Р на версии, подтверждение раздела до анализа и явный отказ неизвестного профиля. | Полнота реестра, forward upgrade с данными, отказ без подтверждения, отсутствие АР fallback. | W58-code close; свежие API/migration pins. |
| W59 / PROFILES-A | АИ, ПЗ, ПОС, ТХ работают через подтверждённый section routing и свои профили. | Recorded cases каждого профиля, citation provenance и отрицательный тест чужого профиля. | SECTION-SEAL merge. |
| W59 / VERSION-COMPARE | Версии комплекта: pairing, детерминированный raw text diff, AI summary, matching findings, подтверждаемое наследование решений. | AI не изменяет raw evidence; перенос только после подтверждения; fixed findings помечены resolved. | SECTION-SEAL merge; один comparison owner. |
| W60 / PROFILES-B | КЖ, КМ, ОВ, ВК, ПТ добавлены в тот же registry/routing. | Recorded cases пяти профилей и явный отказ другого профиля. | W59 code close. |
| W60 / PROJECT-OPT | Для АР есть отдельные proposals, проектная вкладка, решения, export/counts; цены только из проектного Excel/CSV, vendor list по разделу с override и версией. | Нет суммы без цены; считают только matched positions; исходные findings не переписаны. | W59 code close; optimization contract/migration owner. |
| W61 / DEBT-CODE | Исправлены кодовые дефекты из адресных проверок W59–W60. | Регрессии и список открытого; без заявления об экспертной приёмке. | W60 code close. |
| W61 / DISPATCHER | Назначение проекта/документа эксперту, статусы и «мои задачи» работают по ролям. | Recorded assign → status → own tasks, защита чужих задач и повтор без дублей. | W60 code close; placement ruling Q-2. |
| W62 / PROFILES-C | ЭОМ, СС, ИТП, ГП, ПБ добавлены в registry/routing. | Recorded cases пяти профилей, цитаты и отказ недоступного раздела. | W61 code close. |
| W62 / STAGE-COMPARE | Сравнение П/Р одного объекта использует sheet pairing и неизменяемый deterministic diff под AI summary. | Стадии/версии не смешиваются; AI не заменяет raw evidence. | W61 code close; comparison owner. |
| W63 / SECTION-OPT | «Оптимизация разделов» и проектная оптимизация остальных разделов работают с отдельными proposals и экспертным решением. | Recorded positive/negative cases по разрешённым разделам; нет суммы без цены. | W62 code close; optimization owner. |
| W63 / MENU-CLOSE | Все видимые beta пункты и account actions имеют действие и результат по роли; финальные API/error enum и статическая матрица B1–B12 покрывают код. | Screen/operation totality, no-stub checks, reseal и отдельно отмеченная отложенная стендовая часть B1–B12. | Все W63 code slices; один final seal owner. |

Профили после АР идут в порядке S-5. ПЗ (`PS`) и ПБ (`PB`) входят в 15;
имена берутся из S-3. Сравнение версий предшествует сравнению стадий.
Диспетчер предложен в W61 по Q-2; конфликт с таблицей roadmap §4 требует
письменного placement ruling до grant. «Настройки анализа» остаются в W56b,
проектная оптимизация — в W60, оптимизация разделов — в W63; конфликт A-7
с таблицей §4 фиксируется до каждого затронутого freeze.

## Протокол каждого будущего freeze

1. Прочитать текущий `CURRENT_STATE.md`, закрывающий task и зависимости;
   снять exact `origin/dev` SHA, API/domain/error/stage digests, migration head,
   screen/route enumerators и pin sweep нужного reseal.
2. Записать проверяемый результат, `depends_on` только на завершённые IDs,
   точные `allowed_paths`, `forbidden_hotspots`, non-goals, rollback/flag и
   integration contract. Один owner на contract, migration head, lockfile,
   composition root и global styles; пересечения разрешить до dispatch.
3. Назначить адресные проверки и миграционный upgrade; не запускать полный
   локальный gate между блоками по R-135. Принятый срез публиковать только в
   `origin/dev` по собственному integration slot.
4. После последнего среза выбрать чистый точный кандидат и выполнить полные
   гейты в выделенной среде. Стендовая/экспертная приёмка и `origin/main`
   остаются за пределами кодовой очереди.
5. Нарезать блок по `CODE-FIRST-TO-BETA.md` §2.1 (указание владельца
   2026-10-19): вертикальные срезы, enabling-срез только для единого seal
   контракта и миграции, одна заморозка и один integration-record на срез или
   группу срезов блока. Строки таблицы выше — кандидаты именно таких срезов:
   заготовка без потребителя в том же срезе отдельным candidate не
   открывается. Параллельные линии открывать только при выполнении условия по
   хосту из §2.2 того же плана.

**Исполнимый вход сейчас:** `W56A-SEAL-01` и
`W56A-GENERATOR-PREP-01` на recorded-only freeze. Gateway identity probe
остаётся FAIL; MODEL-PIN и live activation не подменяются этой картой.
W57a/b и W56b предшествуют W58, поэтому здесь нет фиктивных frozen SHA или
прав на исходники.
