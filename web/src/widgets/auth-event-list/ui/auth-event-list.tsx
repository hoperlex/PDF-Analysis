'use client';

/**
 * «Журнал входов» — the access journal, newest first, a page at a time (contract 1.36.0, `UI-A-94`).
 *
 * The rows are the server's and so is their order; the pager follows the server's cursor. A line names the account
 * it is about and, when an administrator acted, the administrator, by the labels the server resolved; an account
 * that has since been deleted keeps its line with «Учётная запись удалена». Nothing here prints a login, an address
 * or a password: the journal does not hold them.
 */

import Link from 'next/link';
import { useState } from 'react';

import type { AuthEvent } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { AUTH_EVENT_LABELS, AUTH_EVENT_PAGE_LIMIT, authEventDetails, authEventFailure, useAuthEvents } from '@/entities/auth-event';

import styles from './auth-event-list.module.css';

const DELETED_ACCOUNT = 'Учётная запись удалена';

function Person({ uid, label }: { readonly uid: string; readonly label: string | null }) {
  return label === null ? <>{DELETED_ACCOUNT}</> : <Link href={routes.user(uid)}>{label}</Link>;
}

/** The rows of one page, already in hand. */
export function AuthEventRows({ items }: { readonly items: readonly AuthEvent[] }) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table} data-auth-events="">
        <thead>
          <tr>
            <th scope="col">Время</th>
            <th scope="col">Событие</th>
            <th scope="col">Учётная запись</th>
            <th scope="col">Кто выполнил</th>
          </tr>
        </thead>
        <tbody>
          {items.map((event) => {
            const details = authEventDetails(event);
            return (
              <tr key={event.event_id} data-auth-event={event.event_type}>
                <td className={styles.when}>{formatInstant(event.occurred_at)}</td>
                <td>
                  {AUTH_EVENT_LABELS[event.event_type]}
                  {details.map((detail) => <small key={detail} className={styles.detail}>{detail}</small>)}
                </td>
                <td><Person uid={event.subject_user_uid} label={event.subject_label} /></td>
                <td>
                  {event.actor_user_uid === null ? '—' : <Person uid={event.actor_user_uid} label={event.actor_label} />}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function AuthEventList() {
  const [cursor, setCursor] = useState<string | undefined>();
  const query = useAuthEvents({ limit: AUTH_EVENT_PAGE_LIMIT, ...(cursor ? { cursor } : {}) });
  return (
    <div>
      {query.isPending ? <LoadingState what="журнал входов" /> : null}
      {query.isError ? (() => {
        const failure = authEventFailure(query.error);
        return (
          <div data-auth-events-failure={failure.kind}>
            <ErrorState title="Журнал входов не загружен" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void query.refetch()} />
          </div>
        );
      })() : null}
      {query.isSuccess ? (
        query.data.items.length === 0 ? (
          <EmptyState title="В журнале пока нет событий." detail="Здесь появятся входы, смена паролей и ролей и завершение сеансов." />
        ) : (
          <div>
            <AuthEventRows items={query.data.items} />
            <div className="am-pager">
              {cursor ? <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => setCursor(undefined)}>В начало</button> : null}
              {query.data.page.next_cursor ? <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => setCursor(query.data.page.next_cursor ?? undefined)}>Дальше</button> : null}
            </div>
          </div>
        )
      ) : null}
    </div>
  );
}
