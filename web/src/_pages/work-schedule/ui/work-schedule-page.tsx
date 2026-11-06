'use client';

/**
 * `/schedule` — «График работ» (`UI-PARITY-P0P`, rulings `R-150y`, `R-151x`, `R-152a`…`R-152h`).
 *
 * Two tabs, as in the original: «Выполнено», each engineer's documents checked per day of a month against a monthly
 * plan, and «Календарь запаса», the open assignments of «Диспетчер» placed on days. The API decides what each role reads
 * and may change; the roles the route's guard read only decide which controls are drawn. Only the open tab is mounted,
 * so a closed tab reads nothing.
 */

import { useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';

import type { Role } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { ErrorState, LoadingState } from '@/shared/ui';
import { useWorkSchedule, useWorkScheduleReserve } from '@/entities/work-schedule';
import { ReserveCalendarView } from '@/widgets/reserve-calendar';
import { WorkScheduleMonthView } from '@/widgets/work-schedule-month';

import { RESERVE_DAYS, SCHEDULE_TABS, SCHEDULE_TAB_LABELS, scheduleSearch } from '../model/address';
import type { ScheduleAddress, ScheduleTab } from '../model/address';
import styles from './work-schedule-page.module.css';

export interface WorkSchedulePageProps {
  /** The session's roles, as the route's guard read them. */
  readonly roles: readonly Role[];
  /** The tab, month and reserve start the address named. */
  readonly initial: ScheduleAddress;
}

function MonthTab({ month, admin, onMonth }: { readonly month: string; readonly admin: boolean; readonly onMonth: (month: string) => void }) {
  const schedule = useWorkSchedule(month);
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
  return <WorkScheduleMonthView key={schedule.data.month} schedule={schedule.data} admin={admin} onMonth={onMonth} />;
}

function ReserveTab({ start, admin, onStart }: { readonly start: string; readonly admin: boolean; readonly onStart: (start: string) => void }) {
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
  return <ReserveCalendarView reserve={reserve.data} admin={admin} onStart={onStart} />;
}

export function WorkSchedulePage({ roles, initial }: WorkSchedulePageProps) {
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
            <MonthTab month={address.month} admin={admin} onMonth={(month) => go({ ...address, month })} />
          ) : (
            <ReserveTab start={address.start} admin={admin} onStart={(start) => go({ ...address, start })} />
          )}
        </div>
      </div>
    </section>
  );
}
