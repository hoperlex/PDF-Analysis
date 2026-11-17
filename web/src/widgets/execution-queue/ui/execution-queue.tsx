'use client';

import Link from 'next/link';
import { useEffect, useId, useRef, useState } from 'react';

import type { ExecutionQueueItem, Role, RunId } from '@/shared/api';
import { formatInstant, formatInstantUtc, routes } from '@/shared/lib';
import {
  JobStateBadge, RunWorkerLine, canCancel, canExecute, canReaudit, jobHoldsLease, jobStateLabel, queueAgeLabel, queueItemError,
} from '@/entities/execution';
import type { RunWorker } from '@/entities/execution';
import { QueueItemWaiting } from '@/entities/audit-run';
import { EmptyState, ErrorState } from '@/shared/ui';

import { keyboardTarget, planReorder, reorderRefusalText } from '../model/reorder';
import { queueTiming } from '../model/timing';

import styles from './execution-queue.module.css';

export interface ExecutionQueueProps {
  readonly items: readonly ExecutionQueueItem[];
  readonly roles: readonly Role[];
  readonly asOf: number | null;
  readonly busy: boolean;
  /**
   * True while a state filter narrows the list. An empty answer then says that no job matches, not that
   * the queue is empty.
   */
  readonly filtered?: boolean;
  /**
   * Who holds a run (`W54-WORKERS-WEB`), asked only for a row whose Job holds a Lease
   * (`leased`, `running`); a queued or finished Job has no worker to name.
   */
  readonly workerOf: (runId: RunId) => RunWorker;
  readonly onCancel: (item: ExecutionQueueItem) => void;
  readonly onReaudit: (item: ExecutionQueueItem) => void;
  readonly onPriority: (item: ExecutionQueueItem, priority: number) => void;
  /**
   * `UI-B-52`: the original's drag of a waiting job to another place. One call per move, with the one priority that puts the job
   * there (`planReorder`) and the place it is meant to take; the page sends the priority command and answers in `reorderNote`.
   * Absent, the rows carry no handle. Offered only to the roles that may set a priority.
   */
  readonly onReorder?: ((item: ExecutionQueueItem, priority: number, place: number | null) => void) | undefined;
  /** What the last move came to, said in the polite live region under the list: moving, moved, or the server's refusal. */
  readonly reorderNote?: string | null | undefined;
  readonly onNext: (() => void) | null;
  readonly onPrevious: (() => void) | null;
}

/**
 * The original's queue line «ЧЧ:ММ → ЧЧ:ММ · длительность» (the reader's local time). A job that never started and
 * never finished prints nothing: its place and age say the rest. The exact instants, in UTC, are in the tooltips.
 */
function QueueTimingLine({ item, asOf }: { readonly item: ExecutionQueueItem; readonly asOf: number | null }) {
  const timing = queueTiming(item, asOf);
  if (timing === null) return null;
  return (
    <span className={styles.timing} data-queue-timing={timing.duration ?? ''}>
      {item.started_at === undefined
        ? '—'
        : <time dateTime={item.started_at} title={`Начат: ${formatInstantUtc(item.started_at)}`} data-queue-started>{timing.start}</time>}
      {' → '}
      {item.finished_at === undefined
        ? <span data-queue-finished="">…</span>
        : <time dateTime={item.finished_at} title={`Завершён: ${formatInstantUtc(item.finished_at)}`} data-queue-finished>{timing.end}</time>}
      {timing.duration === null ? null : ` · ${timing.duration}`}
    </span>
  );
}

export function ExecutionQueue({
  items, roles, asOf, busy, filtered = false, workerOf, onCancel, onReaudit, onPriority, onReorder, reorderNote, onNext, onPrevious,
}: ExecutionQueueProps) {
  const hintId = useId();
  const [dragging, setDragging] = useState<string | null>(null);
  const [over, setOver] = useState<string | null>(null);
  const [localNote, setLocalNote] = useState<string | null>(null);
  // `UIP-S13-01`: the rows whose «Подробнее ▾» is open; a row is closed until the reader opens it, and a read of the list keeps what is open.
  const [openRows, setOpenRows] = useState<ReadonlySet<string>>(() => new Set());
  const handles = useRef(new Map<string, HTMLElement>());
  const refocus = useRef<string | null>(null);
  // The row whose drag has begun and not ended; the mark on the screen follows it a turn later.
  const dragLive = useRef<string | null>(null);
  // A moved row is a different element after the list is read again; the key that moved it gets its handle back.
  useEffect(() => {
    if (refocus.current === null) return;
    handles.current.get(refocus.current)?.focus();
    refocus.current = null;
  }, [items]);
  const queued = items.filter((item) => item.state === 'queued');
  const mayReorder = onReorder !== undefined && canExecute(roles, 'priority') && queued.length > 1;

  /** One move: the slot `toIndex` among the queued rows in view, as one priority command or a sentence saying why not. */
  function move(item: ExecutionQueueItem, toIndex: number, byKey: boolean) {
    if (onReorder === undefined || busy) return;
    const plan = planReorder(queued, item.job_id, toIndex, { top: onPrevious === null, bottom: onNext === null });
    if (plan.kind === 'refused') {
      setLocalNote(reorderRefusalText(plan.reason));
      return;
    }
    if (plan.kind === 'keep') {
      setLocalNote('Задача уже стоит на этом месте.');
      return;
    }
    setLocalNote(null);
    refocus.current = byKey ? item.job_id : null;
    onReorder(item, plan.priority, queued[Math.max(0, Math.min(queued.length - 1, toIndex))]?.queue_position ?? null);
  }

  if (items.some((item) => jobStateLabel(item.state) === null)) {
    return <ErrorState title="Неизвестное состояние задачи" detail="Очередь содержит состояние вне набора, который умеет показывать это приложение." />;
  }
  if (items.length === 0 && onPrevious === null) {
    return filtered
      ? <EmptyState title="Задач в этом состоянии нет" detail="Выберите другое состояние или период, либо покажите все задачи." />
      : <EmptyState title="Очередь пуста" detail="Принятые прогоны появятся здесь." />;
  }
  return (
    <section aria-label="Задачи выполнения" className={styles.list}>
      {items.length === 0 ? <EmptyState title="На этой странице задач нет" detail="Вернитесь к предыдущей странице." /> : null}
      {mayReorder ? (
        <p id={hintId} className="am-note" data-queue-reorder-hint="">
          Порядок ожидающих задач можно менять: перетащите ручку «⋮⋮» строки на новое место или нажмите на ручке Alt+↑ либо Alt+↓.
          Меняется приоритет этой задачи, порядок определяет сервер.
        </p>
      ) : null}
      <ol>
        {items.map((item) => {
          const error = queueItemError(item);
          const mayCancel = canExecute(roles, 'cancel') && canCancel(item);
          const mayReaudit = canExecute(roles, 'reaudit') && canReaudit(item);
          const mayPrioritise = canExecute(roles, 'priority') && item.state === 'queued';
          const opened = openRows.has(item.job_id);
          const panelId = `${hintId}-more-${item.job_id}`;
          return (
          <li
            key={item.job_id}
            className={over === item.job_id && dragging !== item.job_id ? `${styles.row} ${styles.dropOver}` : styles.row}
            data-queue-row={item.state}
            data-queue-drop-over={over === item.job_id && dragging !== item.job_id ? '' : undefined}
            data-queue-moving={dragging === item.job_id ? '' : undefined}
            onDragOver={mayReorder && dragging !== null && item.state === 'queued' ? (event) => {
              event.preventDefault();
              event.dataTransfer.dropEffect = 'move';
              if (over !== item.job_id) setOver(item.job_id);
            } : undefined}
            onDrop={mayReorder && dragging !== null && item.state === 'queued' ? (event) => {
              event.preventDefault();
              const moving = queued.find((candidate) => candidate.job_id === dragging);
              dragLive.current = null;
              setDragging(null);
              setOver(null);
              if (moving !== undefined) move(moving, queued.findIndex((candidate) => candidate.job_id === item.job_id), false);
            } : undefined}
          >
            {/*
              * `UIP-S13-01`: one line as the original's queue item -- «⋮⋮ · № · объект · документ · версия · время → время · длительность ·
              * состояние · Отменить» -- and «Подробнее ▾» at its end. The identities, the times of acceptance and the rest are in the panel it opens.
              */}
            <div className={styles.line} data-queue-line="">
              {mayReorder && item.state === 'queued' ? (
                // The original's six-dot handle: the drag source, and the focus the keyboard moves the row from.
                <span
                  ref={(element) => {
                    if (element === null) handles.current.delete(item.job_id);
                    else handles.current.set(item.job_id, element);
                  }}
                  role="button"
                  tabIndex={0}
                  draggable={!busy}
                  className={styles.handle}
                  data-queue-handle=""
                  aria-label={`Переместить задачу: ${item.document_name}, версия ${item.version_ordinal}`}
                  aria-describedby={hintId}
                  title="Перетащите, чтобы изменить порядок; Alt+↑ и Alt+↓ — на место выше и ниже"
                  onDragStart={(event) => {
                    event.dataTransfer.effectAllowed = 'move';
                    event.dataTransfer.setData('text/plain', item.job_id);
                    const row = event.currentTarget.closest('li');
                    if (row !== null) event.dataTransfer.setDragImage(row, 0, 0);
                    setLocalNote(null);
                    // Marked on the next turn: a change of the dragged row's markup inside `dragstart` can end the drag at once.
                    dragLive.current = item.job_id;
                    window.setTimeout(() => {
                      if (dragLive.current === item.job_id) setDragging(item.job_id);
                    }, 0);
                  }}
                  onDragEnd={() => {
                    dragLive.current = null;
                    setDragging(null);
                    setOver(null);
                  }}
                  onKeyDown={(event) => {
                    const target = keyboardTarget(queued, item.job_id, event.key, event.altKey);
                    if (target === null) return;
                    event.preventDefault();
                    move(item, target, true);
                  }}
                >
                  ⋮⋮
                </span>
              ) : null}
              {/* `UI-PARITY-P0M`: a queued job's place in the dispatcher's order, as the original numbers its queue. */}
              {item.queue_position === undefined ? null : (
                <span className={styles.place} data-queue-position={item.queue_position} title={`Место в очереди: ${item.queue_position}`}>
                  № {item.queue_position}
                </span>
              )}
              {/* `UI-PARITY-QUEUE-A`: what the job executes, read from the server and never from a screen's memory. */}
              <span className={styles.work} data-queue-work>
                <Link href={routes.project(item.project_uid)}>{item.project_name}</Link>
                {' · '}
                <Link href={routes.document(item.project_uid, item.document_uid)}>{item.document_name}</Link>
                {' · '}
                <Link href={routes.version(item.project_uid, item.version_uid)}>{`Версия ${item.version_ordinal}`}</Link>
              </span>
              <QueueTimingLine item={item} asOf={asOf} />
              <JobStateBadge state={item.state} />
              {mayCancel ? (
                <button className="am-button am-button--quiet am-button--small" type="button" disabled={busy} onClick={() => onCancel(item)}>Отменить прогон</button>
              ) : null}
              {mayReaudit ? (
                <button className="am-button am-button--quiet am-button--small" type="button" disabled={busy} onClick={() => onReaudit(item)}>Повторный аудит</button>
              ) : null}
              <button
                type="button"
                className={`am-button am-button--quiet am-button--small ${styles.moreToggle}`}
                aria-expanded={opened}
                aria-controls={panelId}
                // The glyph is part of the label's text (the journey presses «Подробнее ▾» by it, and `rendered-language` reads it as the
                // element's text), so the name a screen reader gets is said once, without the glyph.
                aria-label="Подробнее"
                data-queue-more-toggle=""
                onClick={() => setOpenRows((current) => {
                  const next = new Set(current);
                  if (next.has(item.job_id)) next.delete(item.job_id);
                  else next.add(item.job_id);
                  return next;
                })}
              >
                {`Подробнее ${opened ? '▴' : '▾'}`}
              </button>
            </div>
            {/* What a reader needs at once to act on a row stays in it: why it waits, why it failed, why it was interrupted. */}
            <QueueItemWaiting item={item} />
            {error === null ? null : (
              <p role="status" data-queue-error={error.code}>
                Ошибка: <code>{error.code}</code>{error.sentence === null ? null : <> — {error.sentence}</>}
              </p>
            )}
            {item.interrupted_reason === undefined ? null : (
              <p data-queue-interrupted={item.interrupted_reason}>
                Прогон был прерван: <code>{item.interrupted_reason}</code>
              </p>
            )}
            {/*
              * «Подробнее ▾»: the job's identities and times as one running line of facts, the worker that holds it and the priority field.
              * Always in the markup (closed it is `hidden`), so the ids are text a reader selects and copies from here.
              */}
            <div id={panelId} hidden={!opened} className={styles.more} data-queue-more="">
              {jobHoldsLease(item.state) ? <div className={styles.identity}><RunWorkerLine worker={workerOf(item.run_id)} /></div> : null}
              <p className={styles.facts}>
                <span className={styles.identity}>
                  Прогон <a href={routes.logs(item.run_id)}><code>{item.run_id}</code></a>
                  {' '}(<Link href={routes.run(item.project_uid, item.run_id)}>Открыть прогон</Link>)
                </span>
                <span className={styles.identity}>Задача <code>{item.job_id}</code></span>
                <span>Принята: <time dateTime={item.created_at}>{formatInstant(item.created_at)}</time></span>
                {/* `R-151v`: who started the run, as the original's queue says; older runs do not know. */}
                <span data-queue-started-by>Запустил: {item.started_by_label ?? 'неизвестно'}</span>
                <span>Возраст: {queueAgeLabel(item.created_at, asOf)}</span>
                {item.attempt_count === undefined ? null : <span data-queue-attempts={item.attempt_count}>Попыток: {item.attempt_count}</span>}
                <span>Доступна: <time dateTime={item.available_at}>{formatInstant(item.available_at)}</time></span>
                <span>Приоритет: {item.priority}</span>
                {item.estimated_finish_at === undefined ? null : (
                  // `R-151u`: from similar past runs; never shown without enough history.
                  <span data-queue-eta>
                    Ожидаемое завершение: ≈ <time dateTime={item.estimated_finish_at}>{formatInstant(item.estimated_finish_at)}</time>
                  </span>
                )}
              </p>
              {mayPrioritise ? (
                <form
                  className={styles.priorityForm}
                  onSubmit={(event) => {
                    event.preventDefault();
                    const value = Number(new FormData(event.currentTarget).get('priority'));
                    if (Number.isInteger(value) && value >= -100 && value <= 100) onPriority(item, value);
                  }}
                >
                  <label>Приоритет
                    <input name="priority" type="number" min="-100" max="100" step="1" defaultValue={item.priority} required />
                  </label>
                  <button className="am-button am-button--quiet am-button--small" type="submit" disabled={busy}>Изменить</button>
                </form>
              ) : null}
            </div>
          </li>
          );
        })}
      </ol>
      {/* `UI-B-52`: what a move came to, said where a screen reader hears it; mounted whenever a move is possible. */}
      {mayReorder || localNote !== null || (reorderNote ?? null) !== null ? (
        <p role="status" aria-live="polite" className="am-note" data-queue-reorder-note="">
          {localNote ?? reorderNote ?? ''}
        </p>
      ) : null}
      <nav aria-label="Страницы очереди" className={styles.actions}>
        <button type="button" className="am-button am-button--quiet" disabled={onPrevious === null} onClick={onPrevious ?? undefined}>Назад</button>
        <button type="button" className="am-button am-button--quiet" disabled={onNext === null} onClick={onNext ?? undefined}>Далее</button>
      </nav>
    </section>
  );
}
