import styles from './extended-review.module.css';
import { MachineAdvice } from './machine-advice';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function objects(value: unknown): RecordValue[] { return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : []; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
const STATUS: Readonly<Record<string, string>> = { queued: 'Запланировано', running: 'Выполняется', completed: 'Завершено', partial: 'Частично', failed: 'Ошибка', skipped: 'Пропущено', unavailable: 'Недоступно' };

export function WindowProgress({ windows: value, progress: reading }: { readonly windows: unknown; readonly progress: unknown }) {
  const windows = objects(value);
  const progress = object(reading);
  return <section aria-label="Окна анализа раздела" className={styles.windows} data-extended-windows="">
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
          <ol>{objects(window.procedures).map((procedure, number) => <li key={text(procedure.id) || number} data-window-procedure={text(procedure.id)}>
            {text(procedure.title) || 'Название не передано'} · {STATUS[text(procedure.status)] ?? 'Состояние не передано'}
            {text(procedure.reason) ? <p>{text(procedure.reason)}</p> : null}
          </li>)}</ol>
          <p>Сохранённых наблюдений окна: {objects(window.observations).length}. Все записи доступны в выгрузке, включая рекомендации и исправленные кандидаты.</p>
          {objects(window.observations).length === 0 ? null : <details><summary>Наблюдения этого окна</summary><ol>{objects(window.observations).map((item, number) => <li key={text(item.observation_id) || number}>
            <strong>{text(item.title)}</strong><p>{text(item.description)}</p>
            <MachineAdvice review={item.review ?? item.critic} correction={item.correction} reviewStatus={item.review_status} reviewReason={item.review_reason} />
            {Array.isArray(item.source_ids) ? <p>Идентификаторы источников: {item.source_ids.filter((source): source is string => typeof source === 'string').join(', ')}</p> : null}
          </li>)}</ol></details>}
          {[window.reviews, window.critiques, window.corrections].some((items) => Array.isArray(items) && items.length > 0) ? <p>Полные сохранённые рекомендации и исправленные кандидаты этого окна доступны в выгрузке. Исходные наблюдения сохранены; машинная рекомендация не является решением эксперта.</p> : null}
        </details>
      </li>;
    })}</ol>}
  </section>;
}
