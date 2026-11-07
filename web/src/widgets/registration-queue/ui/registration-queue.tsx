'use client';

/**
 * «Заявки на регистрацию» — the queue of an administrator's decisions (`UI-A-90`, `UI-A-91`).
 *
 * Oldest first, as the server orders it. The chips above the list are the original's tab and its filter in one: «Ожидают
 * решения (N)» carries the server's `pending_total`, which counts the waiting requests whatever the chosen status, so the
 * number does not change when another chip is chosen and is kept on screen while the next page is being read. A waiting
 * request carries its decision controls in the row; a decided one says who it was about, when and why.
 */

import Link from 'next/link';
import { useEffect, useState } from 'react';

import type { RegistrationStatus } from '@/shared/api';
import { REGISTRATION_STATUS_VALUES } from '@/shared/api';
import {
  REGISTRATION_FILTER_LABELS,
  REGISTRATION_PAGE_LIMIT,
  REGISTRATION_STATUS_LABELS,
  REGISTRATION_STATUS_TONES,
  registrationFailure,
  useRegistrationRequests,
} from '@/entities/registration-request';
import { RegistrationDecisionControls } from '@/features/decide-registration';
import { formatInstant, routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import styles from './registration-queue.module.css';

/** The chips in the order the original's filter reads: the work first, then what is done, then everything. */
const FILTERS: readonly (RegistrationStatus | 'all')[] = ['pending', ...REGISTRATION_STATUS_VALUES.filter((value) => value !== 'pending'), 'all'];

const EMPTY_TITLES: Readonly<Record<RegistrationStatus | 'all', string>> = {
  pending: 'Заявок, ожидающих решения, нет.',
  approved: 'Одобренных заявок нет.',
  rejected: 'Отклонённых заявок нет.',
  all: 'Заявок пока нет.',
};

export function RegistrationQueue() {
  const [status, setStatus] = useState<RegistrationStatus | ''>('pending');
  const [cursor, setCursor] = useState<string | undefined>();
  const filters = { limit: REGISTRATION_PAGE_LIMIT, ...(status ? { status } : {}), ...(cursor ? { cursor } : {}) };
  const query = useRegistrationRequests(filters);
  // The count of waiting requests stays drawn while another status or page is being read, instead of vanishing.
  const [keptPending, setKeptPending] = useState<number | null>(null);
  const currentPending = query.isSuccess ? query.data.pending_total : null;
  useEffect(() => {
    if (currentPending !== null) setKeptPending(currentPending);
  }, [currentPending]);
  const pendingTotal = currentPending ?? keptPending;
  const choose = (value: RegistrationStatus | 'all') => { setStatus(value === 'all' ? '' : value); setCursor(undefined); };
  const chosen: RegistrationStatus | 'all' = status === '' ? 'all' : status;

  return (
    <div>
      <nav className={styles.filters} aria-label="Состояние заявок" data-registration-filter={chosen}>
        {FILTERS.map((value) => (
          <button
            key={value}
            type="button"
            className="am-button am-button--quiet am-button--small"
            aria-pressed={chosen === value}
            data-registration-filter-chip={value}
            onClick={() => choose(value)}
          >
            {REGISTRATION_FILTER_LABELS[value]}{value === 'pending' && pendingTotal !== null ? ` (${pendingTotal})` : ''}
          </button>
        ))}
      </nav>
      {query.isPending ? <LoadingState what="заявки на регистрацию" /> : null}
      {query.isError ? (() => { const failure = registrationFailure(query.error); return <div data-registration-list-failure={failure.kind}><ErrorState title="Заявки не загружены" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void query.refetch()} /></div>; })() : null}
      {query.isSuccess ? (
        <div>
          <p className="am-note" data-pending-total={query.data.pending_total}>
            {query.data.pending_total === 0 ? 'Все заявки рассмотрены: ожидающих решения нет.' : `Ожидают решения: ${query.data.pending_total}.`}
          </p>
          {query.data.items.length === 0 ? <EmptyState title={EMPTY_TITLES[chosen]} detail={chosen === 'pending' ? 'Новые заявки появятся здесь сами.' : 'Выберите другое состояние или перейдите к следующей странице.'} /> : (
            <ul className={styles.list}>{query.data.items.map((request) => (
              <li className={styles.item} key={request.request_id} data-registration-status={request.status}>
                <div className={styles.head}>
                  <h2 className={styles.name}>{request.display_label}</h2>
                  <span className={`am-badge am-badge--${REGISTRATION_STATUS_TONES[request.status]}`}>{REGISTRATION_STATUS_LABELS[request.status]}</span>
                </div>
                <dl className={styles.facts}>
                  <dt>Адрес электронной почты</dt><dd className={styles.login}>{request.login}</dd>
                  <dt>Подана</dt><dd>{formatInstant(request.submitted_at)}</dd>
                  {request.decided_at ? <><dt>Решение принято</dt><dd>{formatInstant(request.decided_at)}</dd></> : null}
                  {request.status === 'rejected' && request.rejection_reason ? <><dt>Причина отказа</dt><dd data-registration-reason="">{request.rejection_reason}</dd></> : null}
                </dl>
                {request.status === 'approved' && request.created_user_uid ? <p className={styles.link}><Link href={routes.user(request.created_user_uid)}>Открыть созданную учётную запись</Link></p> : null}
                {request.status === 'pending' ? <RegistrationDecisionControls request={request} /> : null}
              </li>
            ))}</ul>
          )}
          <div className="am-pager">
            {cursor ? <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => setCursor(undefined)}>В начало</button> : null}
            {query.data.page.next_cursor ? <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => setCursor(query.data.page.next_cursor ?? undefined)}>Дальше</button> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
