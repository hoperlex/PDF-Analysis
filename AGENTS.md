# AGENTS — правила работы AI-агентов

Этот файл обязателен для любого coding agent.

## 1. Перед задачей

1. Прочитать `docs/program/CURRENT_STATE.md`.
2. Прочитать task-файл/описание и все `depends_on`.
3. Проверить frozen contract set текущей волны.
4. Работать только в `allowed_paths` задачи.
5. Не менять `contracts/**`, migration head, root dependency/lock files, composition root и global styles без владения соответствующим integration/contract slot.

## 2. Формат задачи

Каждая задача обязана иметь:

- `task_id`;
- результат, проверяемый пользователем или тестом;
- frozen inputs / contract versions;
- `allowed_paths` и `forbidden_hotspots`;
- non-goals;
- deliverables;
- команды проверки;
- integration contract;
- rollback/feature-flag policy, если меняется поведение;
- `depends_on` только на завершённые task IDs.

Шаблон: `docs/templates/TASK_TEMPLATE.md`.

## 3. Владение

Один shared contract / migration head / root lockfile / composition root — один владелец на волну. Два агента не должны править один hotspot параллельно.

## 4. Архитектурные запреты

Запрещено:

- direct SQL/S3/filesystem из router или React component;
- бизнес-логика в ORM/Pydantic/transport schema/UI;
- deep imports во внутренности другого bounded context;
- generic repository/base service/global utils без доказанной семантики;
- состояние jobs только в памяти;
- path/filename/display number как identity;
- dual-write DB + external side effect без outbox/reconciliation;
- silent fallback;
- LLM output как каноническое решение эксперта;
- изменение raw deterministic comparison evidence AI-слоем.

## 5. Завершение задачи

Агент возвращает:

1. список изменённых файлов;
2. выполненные проверки и их результаты;
3. новые/изменённые contracts;
4. риски/known limitations;
5. инструкцию интегратору;
6. доказательство, что forbidden hotspots не затронуты, либо ссылка на разрешающий task.

Не создавать checkpoint/tag самостоятельно, если задача не является `W*-INT-*`.
