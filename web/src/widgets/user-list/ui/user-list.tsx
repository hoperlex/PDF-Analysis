'use client';

/**
 * The account list of the administration area (`UI-A-92`).
 *
 * One row per account: the name and the login, the roles, the standing and the last sign-in. A row is a link to the
 * account's own screen; where a page gives `onSelect` (the page that shows the card beside the list), a plain click on a row
 * selects the account there instead and a modified click still follows the link. What the server filters is `include_archived`
 * alone; the standing, the role and the text search narrow the page already read, and the line above the table says how many of
 * the page they leave, so a short list is never mistaken for a short account book.
 */

import Link from 'next/link';
import { useState } from 'react';
import type { KeyboardEvent, MouseEvent } from 'react';

import type { Role } from '@/shared/api';
import { ROLE_VALUES } from '@/shared/api';
import { routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { roleLabels } from '@/entities/account';
import { USER_PAGE_LIMIT, lastSignInText, useUsers, userFailure } from '@/entities/user';

import type { UserScope } from '../model/filter-users';
import { USER_SCOPES, USER_SCOPE_LABELS, filterUsers, includesArchived, isArchived } from '../model/filter-users';
import styles from './user-list.module.css';

export interface UserListProps {
  /** The account open beside the list, or `null`; absent where the list stands alone. */
  readonly selectedUid?: string | null | undefined;
  /** Where a page shows the card beside the list: called with the account a plain click chose. */
  readonly onSelect?: ((userUid: string) => void) | undefined;
}

function isPlainClick(event: MouseEvent): boolean {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

/** ArrowUp and ArrowDown move between the rows' links, so the list can be walked without the Tab key. */
function walkRows(event: KeyboardEvent<HTMLTableSectionElement>): void {
  if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
  const links = Array.from(event.currentTarget.querySelectorAll<HTMLAnchorElement>('a[data-user-link]'));
  const at = links.findIndex((link) => link === document.activeElement);
  if (at < 0) return;
  const next = links[event.key === 'ArrowDown' ? at + 1 : at - 1];
  if (next === undefined) return;
  event.preventDefault();
  next.focus();
}

export function UserList({ selectedUid = null, onSelect }: UserListProps) {
  const [scope, setScope] = useState<UserScope>('active');
  const [role, setRole] = useState<Role | ''>('');
  const [text, setText] = useState('');
  const [cursor, setCursor] = useState<string | undefined>();
  const query = useUsers({ includeArchived: includesArchived(scope), limit: USER_PAGE_LIMIT, ...(cursor ? { cursor } : {}) });
  const changeScope = (value: UserScope) => { setScope(value); setCursor(undefined); };
  const changeRole = (value: Role | '') => { setRole(value); setCursor(undefined); };
  const filtered = text.trim() !== '' || role !== '' || scope === 'archived';

  return (
    <div>
      <div className={styles.filters} role="group" aria-label="Фильтры списка">
        <div className={styles.scopes} data-user-scope={scope}>
          {USER_SCOPES.map((value) => (
            <button
              key={value}
              type="button"
              className="am-button am-button--quiet am-button--small"
              aria-pressed={scope === value}
              data-user-scope-chip={value}
              onClick={() => changeScope(value)}
            >
              {USER_SCOPE_LABELS[value]}
            </button>
          ))}
        </div>
        <label className={styles.filter}>Найти на странице{' '}
          <input
            type="search"
            value={text}
            placeholder="Имя или адрес"
            maxLength={120}
            autoComplete="off"
            data-user-search=""
            onChange={(event) => setText(event.target.value)}
          />
        </label>
        <label className={styles.filter}>Роль на текущей странице{' '}
          <select value={role} onChange={(event) => changeRole(event.target.value as Role | '')}>
            <option value="">Все роли</option>
            {ROLE_VALUES.map((value) => <option key={value} value={value}>{roleLabels([value])[0]}</option>)}
          </select>
        </label>
      </div>
      {query.isPending ? <LoadingState what="пользователи" /> : null}
      {query.isError ? (() => { const failure = userFailure(query.error); return <div data-user-list-failure={failure.kind}><ErrorState title="Пользователи не загружены" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void query.refetch()} /></div>; })() : null}
      {query.isSuccess ? (() => {
        const items = filterUsers(query.data.items, { scope, role, text });
        const pager = (
          <div className="am-pager">
            {cursor ? <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => setCursor(undefined)}>В начало</button> : null}
            {query.data.page.next_cursor ? <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => setCursor(query.data.page.next_cursor ?? undefined)}>Дальше</button> : null}
          </div>
        );
        if (items.length === 0) {
          return (
            <div>
              <EmptyState
                title={filtered ? 'На этой странице подходящих пользователей нет.' : 'Учётных записей пока нет.'}
                detail={filtered ? 'Измените фильтр или перейдите к следующей странице.' : 'Здесь появятся записи, как только заявки будут одобрены.'}
                action={filtered ? <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => { setText(''); changeRole(''); changeScope('active'); }}>Сбросить фильтры</button> : undefined}
              />
              {pager}
            </div>
          );
        }
        return (
          <div>
            <p className="am-note" aria-live="polite" data-user-count={items.length} data-user-page-size={query.data.items.length}>
              {filtered ? `Показано ${items.length} из ${query.data.items.length} на этой странице.` : `На странице: ${items.length}.`}
            </p>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th scope="col">Пользователь</th><th scope="col">Роли</th><th scope="col">Состояние</th><th scope="col">Последний вход</th></tr></thead>
                <tbody onKeyDown={walkRows}>{items.map((account) => {
                  const selected = selectedUid === account.user_uid;
                  return (
                    <tr
                      key={account.user_uid}
                      className={styles.row}
                      data-user-row={account.user_uid}
                      data-selected={selected}
                      onClick={onSelect === undefined ? undefined : (event) => {
                        // A click on a control inside the row is that control's; the rest of the row opens the account.
                        if (event.target instanceof Element && event.target.closest('a, button, input, select') !== null) return;
                        onSelect(account.user_uid);
                      }}
                    >
                      <td className={styles.name}>
                        <Link
                          href={routes.user(account.user_uid)}
                          aria-current={selected ? 'true' : undefined}
                          data-user-link=""
                          {...(onSelect === undefined ? {} : {
                            onClick: (event: MouseEvent<HTMLAnchorElement>) => {
                              if (!isPlainClick(event)) return;
                              event.preventDefault();
                              onSelect(account.user_uid);
                            },
                          })}
                        >{account.display_label}</Link><br /><small>{account.login}</small>
                      </td>
                      <td>{roleLabels(account.roles).join(', ') || 'Не назначены'}</td>
                      <td>
                        {isArchived(account) ? <span className="am-badge am-badge--inert">В архиве</span> : <span className="am-badge am-badge--ok">Действует</span>}
                        {/* What an administrator has to chase: a temporary password nobody has replaced, a profile nobody has filled. */}
                        {account.is_default_credential ? <><br /><span className="am-note" data-user-default-credential="">Пароль временный</span></> : null}
                        {account.profile_complete ? null : <><br /><span className="am-note" data-user-profile-incomplete="">Профиль не заполнен</span></>}
                      </td>
                      <td data-user-last-sign-in={account.last_sign_in_at === null ? 'never' : 'at'}>{lastSignInText(account.last_sign_in_at)}</td>
                    </tr>
                  );
                })}</tbody>
              </table>
            </div>
            {pager}
          </div>
        );
      })() : null}
    </div>
  );
}
