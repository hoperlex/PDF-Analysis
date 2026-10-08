'use client';

import Link from 'next/link';
import { useState } from 'react';

import type { RegistrationStatus } from '@/shared/api';
import { REGISTRATION_STATUS_VALUES } from '@/shared/api';
import { REGISTRATION_PAGE_LIMIT, REGISTRATION_STATUS_LABELS, registrationFailure, useRegistrationRequests } from '@/entities/registration-request';
import { RegistrationDecisionControls } from '@/features/decide-registration';
import { routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import styles from './registration-queue.module.css';

export function RegistrationQueue() {
  const [status, setStatus] = useState<RegistrationStatus | ''>('pending');
  const [cursor, setCursor] = useState<string | undefined>();
  const filters = { limit: REGISTRATION_PAGE_LIMIT, ...(status ? { status } : {}), ...(cursor ? { cursor } : {}) };
  const query = useRegistrationRequests(filters);

  return (
    <div>
      <div className={styles.filters}>
        <label>Состояние{' '}
          <select value={status} onChange={(event) => { setStatus(event.target.value as RegistrationStatus | ''); setCursor(undefined); }}>
            <option value="">Все заявки</option>
            {REGISTRATION_STATUS_VALUES.map((value) => <option key={value} value={value}>{REGISTRATION_STATUS_LABELS[value]}</option>)}
          </select>
        </label>
      </div>
      {query.isPending ? <LoadingState what="заявки на регистрацию" /> : null}
      {query.isError ? (() => { const failure = registrationFailure(query.error); return <div data-registration-list-failure={failure.kind}><ErrorState title="Заявки не загружены" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void query.refetch()} /></div>; })() : null}
      {query.isSuccess ? (
        <div>
          <p className="am-note" data-pending-total={query.data.pending_total}>Ожидают решения: {query.data.pending_total}.</p>
          {query.data.items.length === 0 ? <EmptyState title="Заявок с этим состоянием нет." detail="Выберите другое состояние или перейдите к следующей странице." /> : (
            <ul className={styles.list}>{query.data.items.map((request) => (
              <li className={styles.item} key={request.request_id} data-registration-status={request.status}>
                <h2>{request.display_label}</h2>
                <p className="am-note">Адрес электронной почты: {request.login}</p>
                <p className="am-note">Состояние: {REGISTRATION_STATUS_LABELS[request.status]}.</p>
                <p className="am-note">Подана: {new Date(request.submitted_at).toLocaleString('ru-RU')}.</p>
                {request.decided_at ? <p className="am-note">Решение принято: {new Date(request.decided_at).toLocaleString('ru-RU')}.</p> : null}
                {request.status === 'rejected' && request.rejection_reason ? <p className="am-note">Причина отказа: {request.rejection_reason}</p> : null}
                {request.status === 'approved' && request.created_user_uid ? <p><Link href={routes.user(request.created_user_uid)}>Открыть созданную учётную запись</Link></p> : null}
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
