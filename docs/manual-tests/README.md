# Manual checkpoint tests

Manual runbook — обязательная часть checkpoint evidence. Его выполняют **после automated gates** из clean checkout/clean local state по возможности другим агентом/тестировщиком, чем автор основной реализации.

## Общий порядок

1. Checkout exact checkpoint candidate commit.
2. Записать commit SHA, contract versions, migration head, tool/runtime versions.
3. Очистить/создать отдельный local test namespace; не использовать случайно накопленную author DB.
4. Запустить documented bootstrap/dev commands.
5. Выполнить runbook сверху вниз.
6. Для каждого шага записать `PASS/FAIL/BLOCKED`, фактический результат и безопасное evidence reference.
7. После теста выполнить stop/cleanup согласно runbook.
8. Сохранить отчёт по `MANUAL_TEST_REPORT_TEMPLATE.md`.

## Правила evidence

- в git — только synthetic/anonymized fixtures;
- не коммитить tokens, cookies, presigned URLs, production documents или raw provider payloads;
- screenshot допустим только без sensitive data;
- для async failures указывать `correlation_id`, `run_id/job_id/attempt_id`, но не секреты;
- manual success не может компенсировать red automated gate.

## Expected command surface after CP-01

Точные команды выбираются/фиксируются в `W1-INT-00`, но интерфейс должен оставаться семантически стабильным, например:

```text
make bootstrap
make dev
make test
make test-contract
make test-integration
make test-e2e
make stop
```

Runbooks используют смысл этих команд; если выбран другой task runner, документация обновляется в CP-01 одним owner.
