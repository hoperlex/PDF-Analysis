# BLOCK5-EXPERIENCE-1030 — source handback

Отдельная панель показывает реальные глобальные лимиты на весь прогон, состояния, страницы/окна/фрагменты/пары, квитанции, отложенные пары и ресурсные пропуски. Новые source pieces открывают реальные защищённые страницы PDF; распознанный слой и Unicode-диапазоны записи не называются native/PDF-координатами. Сокращённые манифесты явно отличаются от полных счётчиков. Полнота всех сочетаний не утверждается.

Глобальный status/procedures участвуют в определении завершённого чтения. Фильтр происхождения и карточки сохраняют exact source_evidence и исходные window/batch IDs. MD/HTML содержат глобальное покрытие/квитанции/оригиналы и полный raw snapshot. Технический XLSX добавляет lossless GlobalCrossWindow JSON chunks, сохраняя полный исходный ответ независимо от фильтра.

Интегратор согласовал финальные producer-ключи pairs_selected/pairs_completed/pairs_remaining/windows_compared с UI после прерывания lane. Текущие v2/v3/no-policy результаты сохраняют свой путь; новых model calls из чтения/экспорта нет.

Изменённые области: web/src/widgets/extended-review/**; web/src/entities/audit-run/lib/{extended-report.ts,extended-xlsx.ts}; этот отчёт. Exact grant — соответствующий task, а завершение интегратором — tasks/BLOCK5-INT-1030.md, раздел Integration takeover.

Все три delegated-сессии прекратились по usage-limit до итогового handback. Отчёт составлен интегратором по оставленному исходному коду, без приписывания агентам завершённых проверок. Root принял исключительное владение, завершил недостающий код и заморозил область для публикации.

**UNVERIFIED:** тесты, build/compile/import, lint/typecheck, браузер, DB/worker и model/provider checks не выполнялись. Не затронуты contracts/API/generated, migrations, root dependencies/locks, composition root, global styles, tests/fixtures или синтетика. API1.14.0/migration0043 неизменны. Риски: исполнение/восстановление, модельная схема, полнота отбора/контекста, большие ответы и UI/download поведение не подтверждены; всё D-290. Root публикует dev, владелец deploys.

