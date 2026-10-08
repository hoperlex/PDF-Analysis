'use client';

import Link from 'next/link';
import { useState } from 'react';

import type { Role } from '@/shared/api';
import { ROLE_VALUES } from '@/shared/api';
import { routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { roleLabels } from '@/entities/account';
import { USER_PAGE_LIMIT, useUsers, userFailure } from '@/entities/user';

import styles from './user-list.module.css';

export function UserList() {
  const [includeArchived, setIncludeArchived] = useState(false);
  const [role, setRole] = useState<Role | ''>('');
  const [cursor, setCursor] = useState<string | undefined>();
  const query = useUsers({ includeArchived, limit: USER_PAGE_LIMIT, ...(cursor ? { cursor } : {}) });
  const changeArchived = (checked: boolean) => { setIncludeArchived(checked); setCursor(undefined); };
  const changeRole = (value: Role | '') => { setRole(value); setCursor(undefined); };

  return (
    <div>
      <div className={styles.filters}>
        <label><input type="checkbox" checked={includeArchived} onChange={(event) => changeArchived(event.target.checked)} /> Включить архивные</label>
        <label>Роль на текущей странице{' '}
          <select value={role} onChange={(event) => changeRole(event.target.value as Role | '')}>
            <option value="">Все роли</option>
            {ROLE_VALUES.map((value) => <option key={value} value={value}>{roleLabels([value])[0]}</option>)}
          </select>
        </label>
      </div>
      {query.isPending ? <LoadingState what="пользователи" /> : null}
      {query.isError ? (() => { const failure = userFailure(query.error); return <div data-user-list-failure={failure.kind}><ErrorState title="Пользователи не загружены" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void query.refetch()} /></div>; })() : null}
      {query.isSuccess ? (() => {
        const items = role === '' ? query.data.items : query.data.items.filter((account) => account.roles.includes(role));
        if (items.length === 0) return <EmptyState title="На этой странице подходящих пользователей нет." detail="Измените фильтр или перейдите к следующей странице." />;
        return (
          <div>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th scope="col">Пользователь</th><th scope="col">Роли</th><th scope="col">Состояние</th></tr></thead>
                <tbody>{items.map((account) => (
                  <tr key={account.user_uid}>
                    <td className={styles.name}><Link href={routes.user(account.user_uid)}>{account.display_label}</Link><br /><small>{account.login}</small></td>
                    <td>{roleLabels(account.roles).join(', ') || 'Не назначены'}</td>
                    <td>{account.archived_at === null ? 'Действует' : 'В архиве'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="am-pager">
              {cursor ? <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => setCursor(undefined)}>В начало</button> : null}
              {query.data.page.next_cursor ? <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => setCursor(query.data.page.next_cursor ?? undefined)}>Дальше</button> : null}
            </div>
          </div>
        );
      })() : null}
    </div>
  );
}
