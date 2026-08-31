# Legacy behavior baseline

Этот документ фиксирует **что следует извлечь и доказать**, а не что следует копировать.

## 1. Наблюдаемая legacy-поверхность

Рабочий проект содержит FastAPI backend, Vue frontend, filesystem/JSON project state, большой `PipelineManager`, stage runners, knowledge base, findings/review, comparison и distributed-worker исследования/реализации. Масштаб и смешение обязанностей — одна из причин greenfield-подхода.

## 2. Бизнес-поведение, которое следует сохранить/переосмыслить

### Ingest
Legacy поддерживает PDF плюс сопутствующие `*_results.md`, `*_results.html`, optional `*_blocks.json`, а также ZIP-транспорт. Новый ingest должен нормализовать разные transport-формы в единый immutable `InputManifest`; transport не становится domain identity.

### Audit stages
Legacy содержит подготовку документа, crop/context, text analysis, block/visual analysis, merge/review, norm verification, optimization/report и вспомогательные quality stages. Порядок/названия в legacy встречаются в нескольких местах и не должны переноситься как распределённая истина. В новом приложении stage registry — один versioned contract.

### Finding identity
Отображаемый `F-NNN` не подходит как identity: при rerun порядок/состав findings меняется. В новой модели разделяются устойчивый `finding_uid` и run-specific `finding_observation_id`; expert decision привязывается к устойчивому finding, а evidence — к observation/run.

### Norm verification
Проверка нормативов не должна полагаться на память LLM. Для опубликованного run фиксируется `NormsSnapshot`; недоступность обязательного authoritative snapshot/tool даёт явный failure/partial state согласно policy, а не silent pass.

### Expert decisions
Решение эксперта — business event, а не mutable поле JSON. Новое решение создаёт событие; current verdict и KB — rebuildable projections.

### Comparison
Нужно сохранить следующие инварианты:
- automatic sheet-match suggestions rebuildable;
- user-approved `sheet_links` — отдельное авторитетное состояние и не перезаписывается recompute;
- deterministic raw comparison evidence immutable;
- AI review/synthesis additive, не мутирует raw evidence;
- automatic repair имеет proof/audit и undo;
- viewer может использовать previews/tiles вместо передачи исходного object key клиенту.

### Distributed execution
Нужно сохранить:
- heartbeat loss не означает kill running work;
- `run_id`, `job_id`, `attempt_id` различны;
- каждый attempt имеет fencing/execution token;
- повтор events/uploads idempotent;
- stale attempt не может опубликовать result;
- result package публикуется только после schema/checksum/manifest validation;
- worker не пишет canonical metadata напрямую.

## 3. Characterization backlog

До CP-00 команда должна выбрать 3–5 обезличенных/синтетических golden journeys и зафиксировать:

1. normalized input manifest;
2. ожидаемые stage-level structural outputs;
3. finding identity mapping policy;
4. evidence coordinates/page references;
5. expert-decision transitions;
6. export structure;
7. comparison raw evidence для минимум одной пары;
8. failure cases: malformed input, missing norm source, provider timeout, restart/resume.

Live LLM output не используется как побайтовый golden oracle. Для deterministic replay используются записанные обезличенные provider responses.
