'use client';

import { useState } from 'react';
import { BatchProgress } from './batch-progress';
import { ObservationList } from './observation-list';
import { SourceInspector, sourcePage } from './source-inspector';
import styles from './extended-review.module.css';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function objects(value: unknown): RecordValue[] { return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : []; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
const STATUS: Readonly<Record<string, string>> = { queued: 'Запланировано', running: 'Выполняется', completed: 'Завершено в рамках плана', partial: 'Частичное покрытие', failed: 'Ошибка', unavailable: 'Недоступно', skipped: 'Пропущено' };
const PHASE: Readonly<Record<string, string>> = { comprehensive_analysis: 'Сверка источников между окнами', norm_verification: 'Нормативные цитаты', finding_review: 'Машинная критика', finding_correction: 'Предложения уточнения' };
const COVERAGE: Readonly<Record<string, string>> = {
  pages_known: 'Страниц в известных исходных записях', source_pages_compared: 'Страниц в выполненных сопоставлениях',
  windows_in_plan: 'Локальных окон в принятом плане', windows_indexed: 'Окон с индексированным текстом', windows_selected: 'Окон в отобранных сочетаниях',
  characters_total_known: 'Известный исходный текст, символов', characters_indexed: 'Проиндексировано символов', characters_selected: 'Символов в отобранных фрагментах',
  pieces_total_known: 'Известных текстовых фрагментов', pieces_indexed: 'Проиндексировано фрагментов', pieces_selected: 'Отобрано фрагментов', pieces_not_selected: 'Фрагментов вне выбранных сопоставлений',
  candidate_pairs_considered: 'Кандидатных пар рассмотрено отбором', candidate_pairs_eligible: 'Кандидатных пар под условия отбора',
  planned_pairs: 'Пар в принятом плане', completed_pairs: 'Пар обработано', remaining_pairs: 'Известных пар не обработано', pairs_pending: 'Кандидатных пар вне выбранного плана',
  pairs_selected: 'Пар отобрано для обработки', pairs_completed: 'Пар обработано', pairs_remaining: 'Известных пар не обработано', windows_compared: 'Окон в выполненных сопоставлениях',
};
const REASON: Readonly<Record<string, string>> = {
  no_cross_window_candidates: 'Кандидаты по условиям этого отбора не найдены. Это не доказывает отсутствие расхождений между остальными страницами.',
  approved_global_phase_call_limit: 'Достигнут принятый лимит обращений межоконного прохода. Остаток не обработан.',
  approved_global_phase_call_limit_or_source_selection: 'Часть источников или кандидатных пар не вошла в принятый набор сопоставлений.',
  approved_phase_call_limit: 'Достигнут принятый лимит последующей процедуры; часть наблюдений не проверена.',
  accepted_pair_call_limit: 'Кандидатная пара находится за пределами принятого лимита сопоставлений.',
  context_window_truncated: 'Контекст обращения ограничен; полнота сверки не подтверждена.',
  corpus_unavailable: 'Нормативный корпус недоступен; нормативная сверка не выполнена.',
  candidate_context_unavailable: 'Нет подходящих нормативных цитат для модельной сверки.',
  provider_outcome_unknown: 'Результат обращения неизвестен; автоматический повтор не подтверждён.',
};

function MetadataRecords({ value, title, sourceIndex, fallbackVersion, onSource }: { readonly value: unknown; readonly title: string;
  readonly sourceIndex: ReadonlyMap<string, RecordValue>; readonly fallbackVersion: string; readonly onSource: (source: RecordValue) => void }) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(0);
  const records = Array.isArray(value) ? value : [];
  const pages = Math.max(1, Math.ceil(records.length / 25));
  const current = Math.min(page, pages - 1);
  return records.length === 0 ? null : <details onToggle={(event) => setOpen(event.currentTarget.open)}><summary>{title} · {records.length}</summary>{open ? <>
    <ol start={current * 25 + 1}>{records.slice(current * 25, (current + 1) * 25).map((value, index) => {
      const record = object(value);
      const source = sourceIndex.get(text(record?.source_id)) ?? record;
      return <li key={text(record?.batch_key) || text(record?.pair_id) || text(record?.source_id) || index}>
        {text(record?.reason) ? <p>{REASON[text(record?.reason)] ?? 'Сохранена причина ограничения или пропуска; её точный код приведён в записи ниже. Пропуск не означает проверку.'}</p> : null}
        {source !== null && sourcePage(source) !== null && (text(source.version_uid) || fallbackVersion) ? <button type="button" className="am-button am-button--quiet" onClick={() => onSource(source)}>Открыть исходную страницу {sourcePage(source)}</button> : null}
        <pre>{JSON.stringify(value, null, 2)}</pre>
      </li>;
    })}</ol>
    {records.length > 25 ? <nav className={styles.toolbar} aria-label={`Страницы: ${title}`}><button type="button" className="am-button am-button--quiet" disabled={current === 0} onClick={() => setPage(current - 1)}>Предыдущие записи</button><span>{current + 1} из {pages}</span><button type="button" className="am-button am-button--quiet" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}>Следующие записи</button></nav> : null}
  </> : null}</details>;
}

export function CrossWindowReview({ value, observations, sources, fallbackVersion, projectUid }: {
  readonly value: unknown; readonly observations: readonly RecordValue[]; readonly sources: readonly RecordValue[];
  readonly fallbackVersion: string; readonly projectUid?: string;
}) {
  const body = object(value);
  const [selectedSource, setSelectedSource] = useState<RecordValue | null>(null);
  const [showObservations, setShowObservations] = useState(false);
  if (body === null) return null;
  const policy = object(body.policy);
  const limits = object(policy?.call_limits);
  const coverage = object(body.coverage);
  const sourceIndex = new Map(sources.map((source) => [text(source.source_id), source] as const));
  const selected = selectedSource === null ? null : sourceIndex.get(text(selectedSource.source_id)) ?? selectedSource;
  const globalObservations = observations.filter((item) => item.origin_scope === 'global_cross_window');
  return <section id="extended-global-cross-window" className={styles.batchPanel} aria-label="Сверка источников между окнами" data-global-cross-window={text(body.status)}>
    <h3>Сверка источников между окнами</h3>
    <p><strong>{STATUS[text(body.status)] ?? 'Состояние ещё не передано'}</strong>. Проверяются выбранные сочетания источников из разных локальных окон. Это отдельный проход по закреплённому плану; он не доказывает проверку всех возможных сочетаний страниц или отсутствие проблем.</p>
    <p>Лимиты ниже относятся к этому проходу <strong>на весь прогон</strong>, а не к каждому локальному окну. Они не расширяют сохранённые согласия исторических запусков.</p>
    {limits === null ? <p>Лимиты межоконного прохода ещё не переданы.</p> : <dl className={styles.coverageGrid}>{Object.entries(limits).filter(([phase]) => PHASE[phase] !== undefined).map(([phase, value]) => <div key={phase}><dt>{PHASE[phase]}</dt><dd>до {count(value)} обращений на прогон</dd></div>)}</dl>}
    {typeof policy?.piece_characters === 'number' ? <p>Граница одного текстового фрагмента принятой политики: {count(policy.piece_characters)} символов.</p> : null}
    {coverage === null ? <p>Покрытие сочетаний источников ещё не получено.</p> : <dl className={styles.coverageGrid}>{Object.entries(coverage).filter(([key, value]) => COVERAGE[key] !== undefined && typeof value === 'number').map(([key, value]) => <div key={key}><dt>{COVERAGE[key]}</dt><dd>{count(value)}</dd></div>)}</dl>}
    {coverage?.all_pairs_complete === false || coverage?.global_semantic_complete === false ? <p>Все возможные сочетания и глобальная смысловая полнота не подтверждены. Необработанные источники и пропуски сохраняются отдельно.</p> : null}
    {coverage?.complete_input_scan === false ? <p>Исходные записи прочитаны не полностью: не просмотрено {count(coverage.source_records_not_scanned)} записей. Известный объём не обозначает весь исходный документ.</p> : null}
    {coverage?.truncated === true ? <p>Отбор ограничен ресурсными границами и принятым числом обращений; часть фрагментов или сочетаний осталась вне сверки.</p> : null}
    {coverage?.pending_manifest_truncated === true || coverage?.omitted_manifest_truncated === true ? <p>Сохранённые списки необработанных сочетаний или пропусков сокращены до границ манифеста. Общие счётчики и признаки ограничения приведены отдельно; показанный список не является полным перечнем всех возможных пропусков.</p> : null}
    {text(body.reason) ? <p role="status">{REASON[text(body.reason)] ?? 'Сервер сохранил ограничение межоконного прохода; полное выполнение не подтверждено.'}</p> : null}
    {objects(body.procedures).length > 0 ? <ol className={styles.procedures} aria-label="Процедуры межоконного прохода">{objects(body.procedures).map((procedure, index) => <li key={text(procedure.id) || index}><strong>{text(procedure.title) || PHASE[text(procedure.id)] || 'Сохранённая процедура'}</strong> · {STATUS[text(procedure.status)] ?? 'Состояние не передано'}{text(procedure.reason) ? <p>{REASON[text(procedure.reason)] ?? 'Есть сохранённое ограничение выполнения.'}</p> : null}</li>)}</ol> : null}
    <details><summary>Политика и происхождение межоконного прохода</summary><p>Версия: <code>{text(body.version) || text(policy?.version) || 'Не передана'}</code>.</p>{text(body.source_sha256) ? <p>SHA256 источника: <code>{text(body.source_sha256)}</code>.</p> : null}{text(body.manifest_sha256) ? <p>SHA256 манифеста: <code>{text(body.manifest_sha256)}</code>.</p> : null}<pre>{JSON.stringify({ policy: body.policy, coverage: body.coverage, reason: body.reason }, null, 2)}</pre></details>
    <BatchProgress batches={body.batches} coverage={body.phase_coverage} title="Квитанции межоконного прохода" />
    {selected === null ? null : <SourceInspector key={`${text(selected.source_id) || text(selected.origin_id)}:${sourcePage(selected)}:${text(selected.version_uid) || fallbackVersion}`} source={selected} fallbackVersion={fallbackVersion} {...(projectUid === undefined ? {} : { projectUid })} onClose={() => setSelectedSource(null)} />}
    <MetadataRecords value={body.pieces} title="Учтённые текстовые фрагменты" sourceIndex={sourceIndex} fallbackVersion={fallbackVersion} onSource={setSelectedSource} />
    <MetadataRecords value={body.pending_batches} title="Необработанные сочетания источников" sourceIndex={sourceIndex} fallbackVersion={fallbackVersion} onSource={setSelectedSource} />
    <MetadataRecords value={body.omitted} title="Пропуски и ограничения плана" sourceIndex={sourceIndex} fallbackVersion={fallbackVersion} onSource={setSelectedSource} />
    <MetadataRecords value={body.original_observations} title="Первоначальные межоконные наблюдения" sourceIndex={sourceIndex} fallbackVersion={fallbackVersion} onSource={setSelectedSource} />
    <details onToggle={(event) => setShowObservations(event.currentTarget.open)}><summary>Сохранённые наблюдения межоконного прохода · {globalObservations.length}</summary><p>Эти исходные наблюдения также входят в общий список. Нормативная сверка, критика и исправления остаются отдельными машинными рекомендациями, а не решениями эксперта.</p>{showObservations ? <ObservationList observations={globalObservations} sources={sources} fallbackVersion={fallbackVersion} anchorId="extended-cross-window-observations" {...(projectUid === undefined ? {} : { projectUid })} /> : null}</details>
  </section>;
}
