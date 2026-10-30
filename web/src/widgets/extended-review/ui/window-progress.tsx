'use client';

import { useState } from 'react';
import styles from './extended-review.module.css';
import { ObservationList } from './observation-list';
import { BatchProgress } from './batch-progress';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function objects(value: unknown): RecordValue[] { return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : []; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
const STATUS: Readonly<Record<string, string>> = { queued: 'Запланировано', running: 'Выполняется', completed: 'Завершено', partial: 'Частично', failed: 'Ошибка', skipped: 'Пропущено', unavailable: 'Недоступно' };

function WindowObservations({ window, fallbackVersion, projectUid }: { readonly window: RecordValue; readonly fallbackVersion: string; readonly projectUid?: string }) {
  const [open, setOpen] = useState(false);
  return <details onToggle={(event) => setOpen(event.currentTarget.open)}><summary>Наблюдения этого окна</summary>{open ? <ObservationList observations={objects(window.observations)} sources={objects(window.sources)} fallbackVersion={text(window.version_uid) || fallbackVersion} anchorId={`extended-window-${text(window.window_id)}-observations`} {...(projectUid === undefined ? {} : { projectUid })} /> : null}</details>;
}
function WindowBatches({ window, number }: { readonly window: RecordValue; readonly number: number }) {
  const [open, setOpen] = useState(false);
  return objects(window.batches).length === 0 && object(window.phase_coverage) === null ? null : <details onToggle={(event) => setOpen(event.currentTarget.open)}><summary>Квитанции пакетов этого окна</summary>{open ? <BatchProgress batches={window.batches} coverage={window.phase_coverage} title={`Пакеты окна ${number}`} /> : null}</details>;
}

export function WindowProgress({ windows: value, progress: reading, fallbackVersion = '', projectUid }: {
  readonly windows: unknown; readonly progress: unknown; readonly fallbackVersion?: string; readonly projectUid?: string;
}) {
  const windows = objects(value);
  const progress = object(reading);
  return <section id="extended-window-progress" aria-label="Окна анализа раздела" className={styles.windows} data-extended-windows="">
    <h3>Окна анализа</h3>
    <p>Объём и число окон определяются принятым серверным планом. Размер окна: до {count(progress?.window_size)} источников. Выполняется только объём принятой оценки; непроверенные источники не считаются исследованными.</p>
    <p>Окон с итоговым состоянием: {count(progress?.completed)} из {count(progress?.total)}.</p>
    {typeof progress?.visual_completed === 'number' ? <p>Визуальный проход сохранён для окон: {count(progress.visual_completed)}. Это ещё не завершение всей проверки окна.</p> : null}
    {typeof progress?.current === 'string' ? <p>Текущее окно: <code>{progress.current}</code>.</p> : null}
    {windows.length === 0 ? <p>План отдельных окон ещё не получен.</p> : <ol className={styles.windowList}>{windows.map((window, index) => {
      const coverage = object(window.coverage);
      return <li key={text(window.window_id) || index} data-extended-window={text(window.window_id)} data-window-status={text(window.status)}>
        <details open={window.status === 'running' || window.status === 'failed' || window.status === 'partial'}>
          <summary>Окно {typeof window.index === 'number' ? window.index + 1 : index + 1} · {STATUS[text(window.status)] ?? 'Состояние не передано'}</summary>
          {window.visual_phase_complete === true && window.status === 'running' ? <p>Визуальный проход сохранён; ожидаются оставшиеся процедуры окна.</p> : null}
          {coverage === null ? null : <p>Исследовано источников: {count(coverage.blocks_processed)} из {count(coverage.blocks_selected ?? coverage.blocks_total)}.</p>}
          {text(window.reason) ? <p>Ограничение: {text(window.reason)}.</p> : null}
          <WindowBatches window={window} number={typeof window.index === 'number' ? window.index + 1 : index + 1} />
          <ol>{objects(window.procedures).map((procedure, number) => <li key={text(procedure.id) || number} data-window-procedure={text(procedure.id)}>
            {text(procedure.title) || 'Название не передано'} · {STATUS[text(procedure.status)] ?? 'Состояние не передано'}
            {text(procedure.reason) ? <p>{text(procedure.reason)}</p> : null}
          </li>)}</ol>
          <p>Сохранённых наблюдений окна: {objects(window.observations).length}. Все записи доступны в выгрузке, включая рекомендации и исправленные кандидаты.</p>
          {objects(window.observations).length === 0 ? null : <WindowObservations window={window} fallbackVersion={fallbackVersion} {...(projectUid === undefined ? {} : { projectUid })} />}
          {[window.reviews, window.critiques, window.corrections].some((items) => Array.isArray(items) && items.length > 0) ? <p>Полные сохранённые рекомендации и исправленные кандидаты этого окна доступны в выгрузке. Исходные наблюдения сохранены; машинная рекомендация не является решением эксперта.</p> : null}
        </details>
      </li>;
    })}</ol>}
  </section>;
}
