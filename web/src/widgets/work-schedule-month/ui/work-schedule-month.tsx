'use client';

/**
 * «Выполнено» of «График работ» (`UI-PARITY-P0P`, `R-151x`, `R-152a`…`R-152d`), as the original lays it out: the month's
 * tiles, the engineers × days grid of documents checked, and the plan and fact table under it.
 *
 * A document counts on the day it became «Проверено экспертом», for the author of its last verdict — the server's rule;
 * this only draws it. An administrator edits the plans (and the default plan and time zone) in one mode, and the days off
 * and the absences in another: a click on a day's heading makes it a day off or a working day, a click on a cell marks
 * the engineer absent or present. An expert reads their own row and edits nothing.
 *
 * `D-319`: an administrator narrows the grid, the table and the tiles to one engineer, and a fourth tile, «Просрочки»,
 * counts the open assignments of «Диспетчер» planned before today; the page reads them and passes the number.
 */

import Link from 'next/link';
import { useEffect, useState } from 'react';

import type { WorkScheduleDay, WorkScheduleDoneDocument, WorkScheduleEngineer, WorkScheduleMonth } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import type { EngineerFilter, OverdueRead } from '@/entities/work-schedule';
import {
  EngineerFilterSelect,
  dayOfMonth,
  doneByDay,
  initialsOf,
  monthLabel,
  narrowEngineers,
  percentTone,
  planPercent,
  scheduleTotals,
  shiftMonth,
  todayIso,
  weekdayLabel,
} from '@/entities/work-schedule';
import { useSetAbsences, useSetCalendarDays, useSetPlans, useSetScheduleSettings } from '@/features/edit-work-schedule';

import styles from './work-schedule-month.module.css';

export interface WorkScheduleMonthViewProps {
  readonly schedule: WorkScheduleMonth;
  /** The session holds `admin`: the edit modes are drawn. */
  readonly admin: boolean;
  readonly onMonth: (month: string) => void;
  /** The engineer the rows are narrowed to, resolved against the engineers of this read. */
  readonly filter: EngineerFilter;
  readonly onEngineer: (engineer: string | null) => void;
  /** «Просрочки»: the late open assignments the page counted, or why there is no number. */
  readonly overdue: OverdueRead;
  /** Today, `YYYY-MM-DD`; a test passes a fixed one. */
  readonly today?: string;
  /** The mode and the open cell to start in; a static render (the style census) seeds them, a reader clicks. */
  readonly initialMode?: WorkScheduleMode;
  readonly initialPopover?: string | null;
}

export type WorkScheduleMode = 'view' | 'plan' | 'calendar';
type Mode = WorkScheduleMode;

function documentHref(item: WorkScheduleDoneDocument): string {
  return `/projects/${item.project_uid}/documents/${item.document_uid}`;
}

function weekend(day: string): boolean {
  const label = weekdayLabel(day);
  return label === 'Сб' || label === 'Вс';
}

/** The kind that flips a day: a day off becomes a working day, a working day a day off; the week's rule is `default`. */
function flipKind(day: WorkScheduleDay): 'day_off' | 'workday' | 'default' {
  if (day.day_off) return weekend(day.day) ? 'workday' : 'default';
  return weekend(day.day) ? 'default' : 'day_off';
}

function Percent({ value }: { readonly value: number | null }) {
  const tone = percentTone(value);
  return (
    <span className={styles.percent} data-tone={tone}>
      <span className={styles.percentNumber}>{value === null ? '—' : `${value}%`}</span>
      <span className={styles.bar} aria-hidden="true">
        <span className={styles.barFill} style={{ width: `${Math.min(100, value ?? 0)}%` }} />
      </span>
    </span>
  );
}

const OVERDUE_TITLE =
  'Открытые назначения «Диспетчера», у которых плановая дата раньше сегодняшнего дня. Работа без даты не считается.';

function overdueValue(overdue: OverdueRead): string {
  if (overdue.kind === 'ready') return String(overdue.count);
  return overdue.kind === 'pending' ? '…' : '—';
}

function OverdueTile({ overdue }: { readonly overdue: OverdueRead }) {
  const late = overdue.kind === 'ready' && overdue.count > 0;
  return (
    <div className={late ? `${styles.tile} ${styles.tileLate}` : styles.tile} title={OVERDUE_TITLE} data-schedule-overdue={overdue.kind}>
      <span className={styles.tileLabel}>Просрочки</span>
      <span className={styles.tileValue}>{overdueValue(overdue)}</span>
      <span className={styles.tileSub}>
        {overdue.kind === 'failed' ? 'Назначения не загружены' : 'Назначения с прошедшей датой'}
      </span>
    </div>
  );
}

function Tiles({ engineers, overdue }: { readonly engineers: readonly WorkScheduleEngineer[]; readonly overdue: OverdueRead }) {
  const totals = scheduleTotals(engineers);
  const tone = percentTone(totals.percent);
  const ring = Math.min(100, totals.percent ?? 0);
  return (
    <div className={styles.tiles} data-schedule-tiles="">
      <div className={styles.tile}>
        <span className={styles.tileLabel}>Инженеров в работе</span>
        <span className={styles.tileValue}>{totals.engineers}</span>
        <span className={styles.tileSub}>Действующие эксперты</span>
      </div>
      <div className={styles.tile}>
        <span className={styles.tileLabel}>Отчётов за месяц</span>
        <span className={styles.tileValue}>{totals.fact}</span>
        <span className={styles.tileSub}>Проверено экспертом</span>
      </div>
      <div className={`${styles.tile} ${styles.tileRing}`} data-tone={tone}>
        <svg className={styles.ring} viewBox="0 0 40 40" aria-hidden="true">
          <circle className={styles.ringTrack} cx="20" cy="20" r="16" />
          <circle className={styles.ringFill} cx="20" cy="20" r="16" strokeDasharray={`${(ring / 100) * 100.53} 100.53`} />
        </svg>
        <span className={styles.tileLabel}>Выполнение плана</span>
        <span className={styles.tileValue}>{totals.percent === null ? '—' : `${totals.percent}%`}</span>
        <span className={styles.tileSub}>
          {totals.fact} из {totals.plan} отчётов
        </span>
      </div>
      <OverdueTile overdue={overdue} />
    </div>
  );
}

interface CellProps {
  readonly engineer: WorkScheduleEngineer;
  readonly day: WorkScheduleDay;
  readonly items: readonly WorkScheduleDoneDocument[];
  readonly absent: boolean;
  readonly today: boolean;
  readonly calendarMode: boolean;
  readonly open: boolean;
  readonly onOpen: (open: boolean) => void;
  readonly onAbsence: () => void;
}

function Cell({ engineer, day, items, absent, today, calendarMode, open, onOpen, onAbsence }: CellProps) {
  const label = `${engineer.label} · ${weekdayLabel(day.day)} ${dayOfMonth(day.day)}`;
  return (
    <td
      className={styles.cell}
      data-day-off={day.day_off ? '' : undefined}
      data-today={today ? '' : undefined}
      data-absent={absent ? '' : undefined}
      title={absent ? `${label}: отсутствует` : undefined}
    >
      {calendarMode ? (
        <button
          type="button"
          className={styles.absenceToggle}
          aria-pressed={absent}
          aria-label={`${label}: ${absent ? 'отсутствует — отметить присутствие' : 'отметить отсутствие'}`}
          onClick={onAbsence}
        >
          {absent ? 'отс.' : ''}
        </button>
      ) : null}
      {items.length > 0 ? (
        <div className={styles.stack}>
          {items.slice(0, 2).map((item) => (
            <Link key={item.document_uid} href={documentHref(item)} className={styles.chip} title={`${item.project_name} · ${item.document_title}`}>
              {item.document_title}
            </Link>
          ))}
          {items.length > 2 ? (
            <button
              type="button"
              className={styles.more}
              data-schedule-more=""
              aria-expanded={open}
              title={`Ещё ${items.length - 2} — показать все`}
              onClick={() => onOpen(!open)}
            >
              +{items.length - 2}
            </button>
          ) : null}
        </div>
      ) : null}
      {open ? (
        <div className={styles.popover} role="dialog" aria-label={label}>
          <div className={styles.popoverHead}>{label}</div>
          {items.map((item) => (
            <Link key={item.document_uid} href={documentHref(item)} className={styles.popoverItem}>
              <span className={styles.popoverProject}>{item.project_name}</span>
              <span>{item.document_title}</span>
            </Link>
          ))}
        </div>
      ) : null}
    </td>
  );
}

export function WorkScheduleMonthView({
  schedule,
  admin,
  onMonth,
  filter,
  onEngineer,
  overdue,
  today = todayIso(),
  initialMode = 'view',
  initialPopover = null,
}: WorkScheduleMonthViewProps) {
  const [mode, setMode] = useState<Mode>(admin ? initialMode : 'view');
  const [drafts, setDrafts] = useState<Readonly<Record<string, string>>>({});
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [settingsDraft, setSettingsDraft] = useState({
    plan: String(schedule.settings.default_monthly_plan),
    zone: schedule.settings.time_zone,
  });
  const [popover, setPopover] = useState<string | null>(initialPopover);
  // As the original's popover: Esc or a press outside it (and outside the «+N» that opens it) closes it.
  useEffect(() => {
    if (popover === null) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setPopover(null);
    };
    const onPress = (event: MouseEvent) => {
      const target = event.target;
      if (target instanceof Element && target.closest('[role="dialog"], [data-schedule-more]') !== null) return;
      setPopover(null);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onPress);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onPress);
    };
  }, [popover]);
  const plans = useSetPlans();
  const settings = useSetScheduleSettings();
  const calendar = useSetCalendarDays();
  const absences = useSetAbsences();
  const failure = [plans, settings, calendar, absences].find((command) => command.isError)?.error;
  const busy = plans.isPending || settings.isPending || calendar.isPending || absences.isPending;

  const startPlanEdit = () => {
    setDrafts(Object.fromEntries(schedule.engineers.map((engineer) => [engineer.user_uid, String(engineer.plan)])));
    setTouched(new Set());
    setSettingsDraft({ plan: String(schedule.settings.default_monthly_plan), zone: schedule.settings.time_zone });
    setMode('plan');
  };

  const savePlans = async () => {
    const changed = schedule.engineers
      .map((engineer) => ({ engineer, planned: Number(drafts[engineer.user_uid] ?? engineer.plan) }))
      // A plan typed for the month is stored even when it equals the default: the month then has its own plan.
      .filter(({ engineer, planned }) => planned !== engineer.plan || (engineer.plan_is_default && drafts[engineer.user_uid] !== undefined && touched.has(engineer.user_uid)));
    const defaultPlan = Number(settingsDraft.plan);
    const settingsChanged = defaultPlan !== schedule.settings.default_monthly_plan
      || settingsDraft.zone.trim() !== schedule.settings.time_zone;
    try {
      if (settingsChanged) {
        await settings.mutateAsync({ default_monthly_plan: defaultPlan, time_zone: settingsDraft.zone.trim() });
      }
      if (changed.length > 0) {
        await plans.mutateAsync({
          month: schedule.month,
          plans: changed.map(({ engineer, planned }) => ({ userUid: engineer.user_uid, planned })),
        });
      }
      setMode('view');
    } catch {
      // The failure is drawn from the command's state below; the edit mode stays open with the drafts.
    }
  };

  // The drafts and the save above work on every engineer of the read; only the rows, the tiles and the total are narrowed.
  const visible = narrowEngineers(schedule.engineers, filter);
  const totals = scheduleTotals(visible);
  const message = failure === undefined ? null : failureMessage(failure, {
    validation_failed: 'Сервер не принял значения: план — целое от 0 до 999, часовой пояс — имя IANA (например, Europe/Moscow).',
  });

  return (
    <div className={styles.month} data-schedule-month={schedule.month}>
      <div className={styles.toolbar}>
        <div className={styles.nav}>
          <button type="button" className="am-button am-button--quiet am-button--small" title="Предыдущий месяц" onClick={() => onMonth(shiftMonth(schedule.month, -1))}>
            ‹
          </button>
          <span className={styles.period}>{monthLabel(schedule.month)}</span>
          <button type="button" className="am-button am-button--quiet am-button--small" title="Следующий месяц" onClick={() => onMonth(shiftMonth(schedule.month, 1))}>
            ›
          </button>
        </div>
        {admin ? <EngineerFilterSelect engineers={schedule.engineers} filter={filter} onChange={onEngineer} /> : null}
        {admin ? (
          <div className={styles.actions}>
            {mode === 'plan' ? (
              <>
                <button type="button" className="am-button am-button--small" disabled={busy} onClick={() => void savePlans()}>
                  {busy ? 'Сохранение…' : 'Сохранить'}
                </button>
                <button type="button" className="am-button am-button--quiet am-button--small" disabled={busy} onClick={() => setMode('view')}>
                  Отмена
                </button>
              </>
            ) : (
              <button type="button" className="am-button am-button--quiet am-button--small" disabled={mode === 'calendar'} onClick={startPlanEdit}>
                Изменить план
              </button>
            )}
            <button
              type="button"
              className="am-button am-button--quiet am-button--small"
              aria-pressed={mode === 'calendar'}
              disabled={mode === 'plan'}
              onClick={() => setMode(mode === 'calendar' ? 'view' : 'calendar')}
            >
              {mode === 'calendar' ? 'Готово' : 'Выходные и отсутствия'}
            </button>
          </div>
        ) : null}
      </div>

      <Tiles engineers={visible} overdue={overdue} />

      {mode === 'calendar' ? (
        <p className="am-note" data-schedule-hint="calendar">
          Нажмите на заголовок дня, чтобы сделать его выходным или рабочим; на клетку — чтобы отметить отсутствие инженера.
        </p>
      ) : null}
      {mode === 'plan' ? (
        <div className={styles.settings} data-schedule-settings="">
          <label className={styles.setting}>
            План по умолчанию
            <input
              type="number"
              min={0}
              max={999}
              value={settingsDraft.plan}
              onChange={(event) => setSettingsDraft({ ...settingsDraft, plan: event.target.value })}
            />
          </label>
          <label className={styles.setting}>
            Часовой пояс
            <input
              type="text"
              value={settingsDraft.zone}
              onChange={(event) => setSettingsDraft({ ...settingsDraft, zone: event.target.value })}
            />
          </label>
          <span className="am-note">Факт считается по дню последнего решения эксперта в этом поясе.</span>
        </div>
      ) : null}
      {message !== null ? (
        <p className="am-note" role="alert" data-schedule-failure={message.kind}>
          {message.detail}
        </p>
      ) : null}

      <div className={styles.gridWrap}>
        <table className={styles.grid} aria-label={`Выполнено за ${monthLabel(schedule.month)}`}>
          <thead>
            <tr>
              <th className={styles.engineerColumn} scope="col">
                Инженер
              </th>
              {schedule.days.map((day) => (
                <th
                  key={day.day}
                  scope="col"
                  className={styles.dayColumn}
                  data-day-off={day.day_off ? '' : undefined}
                  data-today={day.day === today ? '' : undefined}
                  data-override={day.override}
                >
                  {mode === 'calendar' ? (
                    <button
                      type="button"
                      className={styles.dayToggle}
                      disabled={calendar.isPending}
                      title={day.day_off ? 'Сделать рабочим днём' : 'Сделать выходным'}
                      onClick={() => calendar.mutate([{ day: day.day, kind: flipKind(day) }])}
                    >
                      <span className={styles.weekday}>{weekdayLabel(day.day)}</span>
                      <span className={styles.dayNumber}>{dayOfMonth(day.day)}</span>
                    </button>
                  ) : (
                    <>
                      <span className={styles.weekday}>{weekdayLabel(day.day)}</span>
                      <span className={styles.dayNumber}>{dayOfMonth(day.day)}</span>
                    </>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((engineer) => {
              const done = doneByDay(engineer);
              const absent = new Set(engineer.absences);
              return (
                <tr key={engineer.user_uid}>
                  <th scope="row" className={`${styles.engineerColumn} ${styles.engineer}`}>
                    <span className={styles.avatar} aria-hidden="true">
                      {initialsOf(engineer.label)}
                    </span>
                    <span className={styles.engineerName}>{engineer.label}</span>
                  </th>
                  {schedule.days.map((day) => {
                    const key = `${engineer.user_uid}|${day.day}`;
                    return (
                      <Cell
                        key={day.day}
                        engineer={engineer}
                        day={day}
                        items={done.get(day.day) ?? []}
                        absent={absent.has(day.day)}
                        today={day.day === today}
                        calendarMode={mode === 'calendar'}
                        open={popover === key}
                        onOpen={(open) => setPopover(open ? key : null)}
                        onAbsence={() => absences.mutate({
                          userUid: engineer.user_uid,
                          days: [{ day: day.day, absent: !absent.has(day.day) }],
                        })}
                      />
                    );
                  })}
                </tr>
              );
            })}
            {visible.length === 0 ? (
              <tr>
                <td className={styles.empty} colSpan={schedule.days.length + 1}>
                  Нет действующих экспертов.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className={styles.statsWrap}>
        <table className={styles.stats} data-schedule-stats="">
          <thead>
            <tr>
              <th scope="col" className={styles.statsName}>
                Инженер
              </th>
              <th scope="col">Факт</th>
              <th scope="col">Осталось</th>
              <th scope="col">План</th>
              <th scope="col" className={styles.statsPercent}>
                Выполнение
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((engineer) => {
              const remaining = Math.max(0, engineer.plan - engineer.fact);
              return (
                <tr key={engineer.user_uid}>
                  <th scope="row" className={styles.statsName}>
                    {engineer.label}
                  </th>
                  <td>
                    <b>{engineer.fact}</b>
                  </td>
                  <td data-low={remaining > 0 ? '' : undefined}>{remaining}</td>
                  <td>
                    {mode === 'plan' ? (
                      <input
                        className={styles.planInput}
                        type="number"
                        min={0}
                        max={999}
                        aria-label={`План: ${engineer.label}`}
                        value={drafts[engineer.user_uid] ?? String(engineer.plan)}
                        onChange={(event) => {
                          setDrafts({ ...drafts, [engineer.user_uid]: event.target.value });
                          setTouched(new Set(touched).add(engineer.user_uid));
                        }}
                      />
                    ) : (
                      <span title={engineer.plan_is_default ? 'План по умолчанию' : undefined} data-default={engineer.plan_is_default ? '' : undefined}>
                        {engineer.plan}
                      </span>
                    )}
                  </td>
                  <td className={styles.statsPercent}>
                    <Percent value={planPercent(engineer.fact, engineer.plan)} />
                  </td>
                </tr>
              );
            })}
            <tr className={styles.total}>
              <th scope="row" className={styles.statsName}>
                Всего по инженерам ({totals.engineers})
              </th>
              <td>
                <b>{totals.fact}</b>
              </td>
              <td data-low={totals.remaining > 0 ? '' : undefined}>{totals.remaining}</td>
              <td>{totals.plan}</td>
              <td className={styles.statsPercent}>
                <Percent value={totals.percent} />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
