# BLOCK5-RUNTIME-1030 — source handback

Свежая вложенная global_cross_window_policy даёт отдельный виртуальный проход после локальных окон и до итогового свода. Builder передаёт реальные два пакета текста; закрытый parser требует точных цитат минимум из двух разных window_id и полного совпадения source_ids с процитированными источниками. Исходные наблюдения с пакетами/диапазонами сохраняются отдельно; norm/critic/corrector используют имеющиеся ограниченные helpers и corpus, без создания новой нормативной авторитетности.

Пределы8/8/8/8 относятся ко всему прогону. Вызовы используют существующие durable _call/journal/request SHA, сохранённые ответы, stop/cancel/денежный потолок и запрет повтора неизвестного эффекта. Отсутствие новой политики не разрешает дополнительные обращения. Новые helper-реализации входят в frozen rules bundle. Локальные оригиналы не заменяются; глобальные записи добавляются один раз, с отдельными исходными и аннотированными списками.

Интегратор завершил оставшиеся после interruption детали: инициализацию/завершение global report, skipped-состояния при раннем отказе, bounded ordinal платного вызова и явный failed report. Глобальные состояния и coverage.truncated влияют на частичный итог; semantic completeness всегда false. Предыдущий terminal global receipt повторно используется без нового расхода.

Изменённые области: src/auditmanager/analysis/extended/{core.py,workflow.py,cross_window_review.py}; src/auditmanager/runs/extended_review.py; этот отчёт. Exact grant — соответствующий task, а завершение интегратором — tasks/BLOCK5-INT-1030.md, раздел Integration takeover.

Все три delegated-сессии прекратились по usage-limit до итогового handback. Отчёт составлен интегратором по оставленному исходному коду, без приписывания агентам завершённых проверок. Root принял исключительное владение, завершил недостающий код и заморозил область для публикации.

**UNVERIFIED:** тесты, build/compile/import, lint/typecheck, браузер, DB/worker и model/provider checks не выполнялись. Не затронуты contracts/API/generated, migrations, root dependencies/locks, composition root, global styles, tests/fixtures или синтетика. API1.14.0/migration0043 неизменны. Риски: исполнение/восстановление, модельная схема, полнота отбора/контекста, большие ответы и UI/download поведение не подтверждены; всё D-290. Root публикует dev, владелец deploys.

