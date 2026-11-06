'use client';

/**
 * «Календарь запаса» of «График работ» (`UI-PARITY-P0P`, `R-150y`, `R-152e`…`R-152h`): each active expert's open
 * assignments of «Диспетчер» on the days they are planned for, and a «Без даты» column for the rest. No daily limit.
 *
 * An administrator moves work as in the original: drag an assignment (or the selection it belongs to) to another day or
 * another engineer's row; Ctrl/Cmd+click adds to the selection; «Раньше» and «Позже» move the selection a working day.
 * Every move is one keyed `scheduleAssignments` command and an event of the assignment's history; a move to another
 * expert is a reassignment in «Диспетчер». An expert reads their own row and moves nothing.
 */

import { useState } from 'react';
import type { DragEvent, MouseEvent } from 'react';

import type { WorkScheduleDay, WorkScheduleReserve, WorkScheduleReserveItem } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { ASSIGNMENT_STATUS_LABELS } from '@/entities/assignment';
import { addDays, dayOfMonth, initialsOf, shortDayLabel, todayIso, weekdayLabel } from '@/entities/work-schedule';
import type { AssignmentPlacement } from '@/features/edit-work-schedule';
import { useMoveAssignments } from '@/features/edit-work-schedule';

import styles from './reserve-calendar.module.css';

export interface ReserveCalendarViewProps {
  readonly reserve: WorkScheduleReserve;
  /** The session holds `admin`: work can be selected and moved. */
  readonly admin: boolean;
  readonly onStart: (start: string) => void;
  /** Today, `YYYY-MM-DD`; a test passes a fixed one. */
  readonly today?: string;
  /** The selection and the drop target to start with; a static render (the style census) seeds them. */
  readonly initialSelection?: readonly string[];
  readonly initialOver?: string | null;
}

interface Placed {
  readonly item: WorkScheduleReserveItem;
  readonly engineerUid: string;
}

const UNDATED = 'none';

function itemLabel(item: WorkScheduleReserveItem): string {
  return item.document_title ?? item.project_name;
}

function itemTitle(item: WorkScheduleReserveItem): string {
  const where = item.document_title === undefined ? item.project_name : `${item.project_name} · ${item.document_title}`;
  const when = item.planned_on === undefined ? 'без даты' : shortDayLabel(item.planned_on);
  return `${where} — ${ASSIGNMENT_STATUS_LABELS[item.status]}, ${when}`;
}

/** The next working day from `day` in `direction`, by the calendar the reserve was read with; past it, a plain day. */
export function nextWorkingDay(day: string, direction: 1 | -1, days: readonly WorkScheduleDay[]): string {
  const off = new Set(days.filter((entry) => entry.day_off).map((entry) => entry.day));
  let next = addDays(day, direction);
  for (let guard = 0; guard < 14 && off.has(next); guard += 1) next = addDays(next, direction);
  return next;
}

export function ReserveCalendarView({
  reserve,
  admin,
  onStart,
  today = todayIso(),
  initialSelection = [],
  initialOver = null,
}: ReserveCalendarViewProps) {
  const [selected, setSelected] = useState<readonly string[]>(admin ? initialSelection : []);
  const [moveDate, setMoveDate] = useState('');
  const [over, setOver] = useState<string | null>(initialOver);
  const move = useMoveAssignments();

  const placed = new Map<string, Placed>();
  for (const engineer of reserve.engineers) {
    for (const item of engineer.items) placed.set(item.assignment_uid, { item, engineerUid: engineer.user_uid });
  }
  const chosen = selected.map((uid) => placed.get(uid)).filter((entry): entry is Placed => entry !== undefined);

  const send = (moves: readonly AssignmentPlacement[]) => {
    if (moves.length === 0) return;
    move.mutate(moves, { onSuccess: () => setSelected([]) });
  };

  const placeSelection = (engineerUid: string, day: string | null, dragged: readonly Placed[]) => {
    send(dragged
      .filter(({ item, engineerUid: current }) => current !== engineerUid || (item.planned_on ?? null) !== day)
      .map(({ item, engineerUid: current }) => ({
        assignmentUid: item.assignment_uid,
        plannedOn: day,
        ...(current === engineerUid ? {} : { assigneeUserUid: engineerUid }),
      })));
  };

  const shift = (direction: 1 | -1) => {
    send(chosen
      .filter(({ item }) => item.planned_on !== undefined)
      .map(({ item }) => ({
        assignmentUid: item.assignment_uid,
        plannedOn: nextWorkingDay(item.planned_on as string, direction, reserve.days),
      })));
  };

  const click = (item: WorkScheduleReserveItem, event: MouseEvent<HTMLButtonElement>) => {
    if (!admin) return;
    const uid = item.assignment_uid;
    if (event.ctrlKey || event.metaKey) {
      setSelected(selected.includes(uid) ? selected.filter((entry) => entry !== uid) : [...selected, uid]);
    } else {
      setSelected(selected.length === 1 && selected[0] === uid ? [] : [uid]);
    }
  };

  const dragStart = (item: WorkScheduleReserveItem, event: DragEvent<HTMLButtonElement>) => {
    const uid = item.assignment_uid;
    if (!selected.includes(uid)) setSelected([uid]);
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', uid);
  };

  const drop = (engineerUid: string, day: string | null, event: DragEvent<HTMLTableCellElement>) => {
    event.preventDefault();
    setOver(null);
    const uid = event.dataTransfer.getData('text/plain');
    const dragged = selected.includes(uid) ? chosen : [placed.get(uid)].filter((entry): entry is Placed => entry !== undefined);
    placeSelection(engineerUid, day, dragged);
  };

  const columns: readonly (WorkScheduleDay | null)[] = [null, ...reserve.days];
  const message = move.isError ? failureMessage(move.error) : null;
  const undatedSelected = chosen.some(({ item }) => item.planned_on === undefined);

  return (
    <div className={styles.reserve} data-schedule-reserve={reserve.start}>
      <div className={styles.toolbar}>
        <strong>Очередь по инженерам</strong>
        <div className={styles.actions}>
          <button type="button" className="am-button am-button--quiet am-button--small" title="Неделей раньше" onClick={() => onStart(addDays(reserve.start, -7))}>
            ‹
          </button>
          <label className={styles.start}>
            Начало периода
            <input type="date" value={reserve.start} onChange={(event) => event.target.value !== '' && onStart(event.target.value)} />
          </label>
          <button type="button" className="am-button am-button--quiet am-button--small" title="Неделей позже" onClick={() => onStart(addDays(reserve.start, 7))}>
            ›
          </button>
        </div>
      </div>
      {admin ? (
        <p className="am-note">
          Перетащите работу на другой день или другому инженеру; Ctrl/Cmd + щелчок добавляет к выбору.
        </p>
      ) : null}
      {admin && chosen.length > 0 ? (
        <div className={styles.selection} data-reserve-selection={chosen.length}>
          <span>Выбрано: {chosen.length}</span>
          <button type="button" className="am-button am-button--quiet am-button--small" disabled={move.isPending} onClick={() => shift(-1)}>
            Раньше
          </button>
          <button type="button" className="am-button am-button--quiet am-button--small" disabled={move.isPending} onClick={() => shift(1)}>
            Позже
          </button>
          <input type="date" aria-label="Дата переноса" value={moveDate} onChange={(event) => setMoveDate(event.target.value)} />
          <button
            type="button"
            className="am-button am-button--small"
            disabled={move.isPending || moveDate === ''}
            onClick={() => send(chosen.map(({ item }) => ({ assignmentUid: item.assignment_uid, plannedOn: moveDate })))}
          >
            Перенести на дату
          </button>
          <button
            type="button"
            className="am-button am-button--quiet am-button--small"
            disabled={move.isPending}
            onClick={() => send(chosen
              .filter(({ item }) => item.planned_on !== undefined)
              .map(({ item }) => ({ assignmentUid: item.assignment_uid, plannedOn: null })))}
          >
            Без даты
          </button>
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setSelected([])}>
            Снять выделение
          </button>
          {undatedSelected ? <span className={styles.hint}>«Раньше» и «Позже» не двигают работу без даты.</span> : null}
        </div>
      ) : null}
      {message !== null ? (
        <p className="am-note" role="alert" data-reserve-failure={message.kind}>
          {message.detail}
        </p>
      ) : null}
      <div className={styles.scroll}>
        <table className={styles.grid} aria-label="Очередь работ по инженерам и датам">
          <thead>
            <tr>
              <th scope="col" className={styles.nameColumn}>
                Инженер
              </th>
              {columns.map((day) =>
                day === null ? (
                  <th key={UNDATED} scope="col" className={styles.undatedColumn}>
                    Без даты
                  </th>
                ) : (
                  <th
                    key={day.day}
                    scope="col"
                    title={shortDayLabel(day.day)}
                    className={styles.dayColumn}
                    data-day-off={day.day_off ? '' : undefined}
                    data-today={day.day === today ? '' : undefined}
                  >
                    <span className={styles.dayNumber}>{dayOfMonth(day.day)}</span>
                    <span className={styles.weekday}>{weekdayLabel(day.day)}</span>
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {reserve.engineers.map((engineer) => {
              const byDay = new Map<string, WorkScheduleReserveItem[]>();
              for (const item of engineer.items) {
                const key = item.planned_on ?? UNDATED;
                byDay.set(key, [...(byDay.get(key) ?? []), item]);
              }
              return (
                <tr key={engineer.user_uid}>
                  <th scope="row" className={styles.nameColumn}>
                    <span className={styles.person}>
                      <span className={styles.avatar} aria-hidden="true">
                        {initialsOf(engineer.label)}
                      </span>
                      <span className={styles.name}>{engineer.label}</span>
                      <span className={styles.count}>{engineer.items.length}</span>
                    </span>
                    {admin && chosen.some(({ engineerUid }) => engineerUid !== engineer.user_uid) ? (
                      <button
                        type="button"
                        className={styles.assign}
                        disabled={move.isPending}
                        onClick={() => send(chosen
                          .filter(({ engineerUid }) => engineerUid !== engineer.user_uid)
                          .map(({ item }) => ({
                            assignmentUid: item.assignment_uid,
                            plannedOn: item.planned_on ?? null,
                            assigneeUserUid: engineer.user_uid,
                          })))}
                      >
                        Передать сюда
                      </button>
                    ) : null}
                  </th>
                  {columns.map((day) => {
                    const key = day === null ? UNDATED : day.day;
                    const cellKey = `${engineer.user_uid}|${key}`;
                    const items = byDay.get(key) ?? [];
                    return (
                      <td
                        key={key}
                        className={day === null ? `${styles.cell} ${styles.undated}` : styles.cell}
                        data-day-off={day?.day_off ? '' : undefined}
                        data-today={day?.day === today ? '' : undefined}
                        data-over={over === cellKey ? '' : undefined}
                        onDragOver={admin ? (event) => {
                          event.preventDefault();
                          if (over !== cellKey) setOver(cellKey);
                        } : undefined}
                        onDragLeave={admin ? () => setOver(null) : undefined}
                        onDrop={admin ? (event) => drop(engineer.user_uid, day === null ? null : day.day, event) : undefined}
                      >
                        {items.map((item) => (
                          <button
                            key={item.assignment_uid}
                            type="button"
                            className={styles.point}
                            data-status={item.status}
                            aria-pressed={admin ? selected.includes(item.assignment_uid) : undefined}
                            title={itemTitle(item)}
                            draggable={admin && !move.isPending}
                            onClick={(event) => click(item, event)}
                            onDragStart={(event) => dragStart(item, event)}
                          >
                            {itemLabel(item)}
                          </button>
                        ))}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {reserve.engineers.length === 0 ? (
              <tr>
                <td className={styles.empty} colSpan={columns.length + 1}>
                  Нет действующих экспертов.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <div className={styles.legend}>
        <span className={styles.legendItem} data-status="assigned">
          Назначено
        </span>
        <span className={styles.legendItem} data-status="in_progress">
          В работе
        </span>
        <span className={styles.legendItem} data-status="returned">
          Возвращено
        </span>
      </div>
    </div>
  );
}
