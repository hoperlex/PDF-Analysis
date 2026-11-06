'use client';

/**
 * `/schedule` — «График работ» (`UI-PARITY-P0P`, rulings `R-150y`, `R-151x`, `R-152a`…`R-152h`).
 *
 * Two tabs, as in the original: «Выполнено», each engineer's documents checked per day of a month against a monthly
 * plan, and «Календарь запаса», the open assignments of «Диспетчер» placed on days. The API decides what each role reads
 * and may change; the roles the route's guard read only decide which controls are drawn. Only the open tab is mounted,
 * so a closed tab reads nothing.
 *
 * `D-319`: an administrator can narrow both tabs to one engineer (`?engineer=`), and «Выполнено» also reads the reserve
 * — the open assignments of «Диспетчер» — for its «Просрочки» tile.
 */

import { useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';

import type { Role } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { ErrorState, LoadingState } from '@/shared/ui';
import type { OverdueRead } from '@/entities/work-schedule';
import { overdueCount, resolveEngineerFilter, todayIso, useWorkSchedule, useWorkScheduleReserve } from '@/entities/work-schedule';
import { ReserveCalendarView } from '@/widgets/reserve-calendar';
import { WorkScheduleMonthView } from '@/widgets/work-schedule-month';

import { RESERVE_DAYS, SCHEDULE_TABS, SCHEDULE_TAB_LABELS, scheduleSearch } from '../model/address';
import type { ScheduleAddress, ScheduleTab } from '../model/address';
import styles from './work-schedule-page.module.css';

export interface WorkSchedulePageProps {
  /** The session's roles, as the route's guard read them. */
  readonly roles: readonly Role[];
  /** The tab, month, reserve start and engineer the address named. */
  readonly initial: ScheduleAddress;
  /** Today, `YYYY-MM-DD`: the day «Просрочки» counts back from; a test passes a fixed one. */
  readonly today?: string;
}

interface TabProps {
  readonly admin: boolean;
  /** The engineer the address named; only an administrator's screen applies it. */
  readonly engineer: string | null;
  readonly onEngineer: (engineer: string | null) => void;
}

function MonthTab({ month, today, admin, engineer, onMonth, onEngineer }: TabProps & {
  readonly month: string;
  readonly today: string;
  readonly onMonth: (month: string) => void;
}) {
  const schedule = useWorkSchedule(month);
  // The reserve carries every open assignment of «Диспетчер» whatever its window, so one day from today is enough to count
  // the late ones; a failed read leaves the tile saying so and the month undisturbed.
  const assignments = useWorkScheduleReserve(today, 1);
  if (schedule.isPending) return <LoadingState what="график за месяц" />;
  if (schedule.isError) {
    const message = failureMessage(schedule.error);
    return (
      <ErrorState
        title="График не загружен"
        detail={message.detail}
        correlationId={message.correlationId}
        onRetry={() => void schedule.refetch()}
      />
    );
  }
  const filter = resolveEngineerFilter(schedule.data.engineers, admin ? engineer : null);
  let overdue: OverdueRead = { kind: 'pending' };
  if (assignments.isError) overdue = { kind: 'failed' };
  else if (assignments.isSuccess) overdue = { kind: 'ready', count: overdueCount(assignments.data.engineers, today, filter) };
  return (
    <WorkScheduleMonthView
      key={schedule.data.month}
      schedule={schedule.data}
      admin={admin}
      today={today}
      filter={filter}
      overdue={overdue}
      onMonth={onMonth}
      onEngineer={onEngineer}
    />
  );
}

function ReserveTab({ start, today, admin, engineer, onStart, onEngineer }: TabProps & {
  readonly start: string;
  readonly today: string;
  readonly onStart: (start: string) => void;
}) {
  const reserve = useWorkScheduleReserve(start, RESERVE_DAYS);
  if (reserve.isPending) return <LoadingState what="календарь запаса" />;
  if (reserve.isError) {
    const message = failureMessage(reserve.error);
    return (
      <ErrorState
        title="Календарь запаса не загружен"
        detail={message.detail}
        correlationId={message.correlationId}
        onRetry={() => void reserve.refetch()}
      />
    );
  }
  const filter = resolveEngineerFilter(reserve.data.engineers, admin ? engineer : null);
  return <ReserveCalendarView reserve={reserve.data} admin={admin} today={today} filter={filter} onStart={onStart} onEngineer={onEngineer} />;
}

export function WorkSchedulePage({ roles, initial, today = todayIso() }: WorkSchedulePageProps) {
  const [address, setAddress] = useState<ScheduleAddress>(initial);
  const base = useId();
  const buttons = useRef<Partial<Record<ScheduleTab, HTMLButtonElement | null>>>({});
  const admin = roles.includes('admin');

  const go = (next: ScheduleAddress) => {
    setAddress(next);
    if (typeof window !== 'undefined') window.history.replaceState(null, '', scheduleSearch(next));
  };

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
    event.preventDefault();
    const next: ScheduleTab = address.tab === 'completed' ? 'reserve' : 'completed';
    go({ ...address, tab: next });
    buttons.current[next]?.focus();
  };

  return (
    <section className="am-page" data-screen="work-schedule">
      <header className="am-page__header">
        <h1 className="am-page__title">График работ</h1>
        <p className="am-page__subtitle">
          {admin
            ? 'Проверенные документы по инженерам и дням против месячного плана; работа «Диспетчера» по датам.'
            : 'Ваши проверенные документы по дням против плана месяца и ваша работа по датам.'}
        </p>
      </header>
      <div className="am-page__body am-page__body--canvas">
        <div role="tablist" aria-label="Представление работ" className={styles.tablist}>
          {SCHEDULE_TABS.map((tab) => (
            <button
              key={tab}
              ref={(element) => {
                buttons.current[tab] = element;
              }}
              type="button"
              role="tab"
              id={`${base}-tab-${tab}`}
              aria-selected={tab === address.tab}
              aria-controls={`${base}-panel`}
              tabIndex={tab === address.tab ? 0 : -1}
              className={styles.tab}
              data-schedule-tab={tab}
              onClick={() => go({ ...address, tab })}
              onKeyDown={onKeyDown}
            >
              {SCHEDULE_TAB_LABELS[tab]}
            </button>
          ))}
        </div>
        <div role="tabpanel" id={`${base}-panel`} aria-labelledby={`${base}-tab-${address.tab}`} className={styles.panel}>
          {address.tab === 'completed' ? (
            <MonthTab
              month={address.month}
              today={today}
              admin={admin}
              engineer={address.engineer}
              onMonth={(month) => go({ ...address, month })}
              onEngineer={(engineer) => go({ ...address, engineer })}
            />
          ) : (
            <ReserveTab
              start={address.start}
              today={today}
              admin={admin}
              engineer={address.engineer}
              onStart={(start) => go({ ...address, start })}
              onEngineer={(engineer) => go({ ...address, engineer })}
            />
          )}
        </div>
      </div>
    </section>
  );
}
