'use client';

/**
 * One account: who it is, what it may do, when it last signed in and the controls to change it (`UI-A-92`, `UI-A-93`).
 *
 * It stands in two places. As the account's own screen (`variant="page"`, `/admin/users/<uid>`) it carries the way back to the
 * list. As the card beside the list (`variant="panel"`, `/admin/users`) it carries the way to its own screen and «Закрыть»,
 * and nothing that leaves the list. The facts are the same in both: the sign-in address, the roles, the standing, the last
 * sign-in and, while the account still has a temporary password, that it is waiting for the person to set their own.
 */

import Link from 'next/link';

import { displayLabelOf, initialsOf, roleLabels, unreadableAccountDetail } from '@/entities/account';
import { lastSignInText, useUser, userFailure } from '@/entities/user';
import { ManageUserControls } from '@/features/manage-user';
import { routes } from '@/shared/lib';
import { Avatar, ErrorState, LoadingState } from '@/shared/ui';

import styles from './user-card.module.css';

export interface UserCardProps {
  readonly userUid: string;
  /** The signed-in account's login, so a change to one's own account refreshes the frame. */
  readonly signedInLogin?: string | null | undefined;
  /** Where the card stands: its own screen, or beside the list. */
  readonly variant?: 'page' | 'panel' | undefined;
  /** «Закрыть» of the panel variant. */
  readonly onClose?: (() => void) | undefined;
}

export function UserCard({ userUid, signedInLogin = null, variant = 'page', onClose }: UserCardProps) {
  const query = useUser(userUid);
  const bar = variant === 'panel' ? (
    <div className={styles.bar}>
      <Link className="am-button am-button--quiet am-button--small" href={routes.user(userUid)}>Открыть отдельным экраном</Link>
      {onClose === undefined ? null : <button type="button" className="am-button am-button--quiet am-button--small" onClick={onClose}>Закрыть</button>}
    </div>
  ) : <p><Link href={routes.users()}>К списку пользователей</Link></p>;
  if (query.isPending) return <div>{bar}<LoadingState what="учётную запись" /></div>;
  if (query.isError) {
    const failure = userFailure(query.error);
    return <div data-user-detail-failure={failure.kind}>{bar}<ErrorState title="Учётная запись не загружена" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void query.refetch()} /></div>;
  }
  const account = query.data;
  let label: string;
  let roles: readonly string[];
  try {
    label = displayLabelOf(account);
    roles = roleLabels(account.roles);
  } catch (error) {
    return <ErrorState title="Данные учётной записи не распознаны" detail={unreadableAccountDetail(error)} />;
  }
  const archived = account.archived_at !== null;
  const isSelf = signedInLogin !== null && account.login === signedInLogin;
  return (
    <div data-user-state={archived ? 'archived' : 'active'}>
      {bar}
      <header className={styles.identity}>
        <Avatar initials={initialsOf(label)} colourKey={account.user_uid} label={`Аватар: ${label}`} />
        <h2 className={styles.name}>{label}{isSelf ? ' (это вы)' : ''}</h2>
        {archived ? <span className="am-badge am-badge--inert">В архиве</span> : <span className="am-badge am-badge--ok">Действует</span>}
      </header>
      <dl className={styles.facts}>
        <dt>Адрес входа</dt>
        <dd className={styles.login}>{account.login}</dd>
        <dt>Роли</dt>
        <dd>{roles.join(', ') || 'не назначены'}</dd>
        <dt>Последний вход</dt>
        <dd data-user-last-sign-in={account.last_sign_in_at === null ? 'never' : 'at'}>{lastSignInText(account.last_sign_in_at)}</dd>
        {account.is_default_credential ? <><dt>Пароль</dt><dd data-user-default-credential="">Временный: при следующем входе пользователь задаст свой</dd></> : null}
        {account.profile_complete ? null : <><dt>Профиль</dt><dd data-user-profile-incomplete="">Не заполнен: фамилия, имя и адрес почты ещё не указаны</dd></>}
      </dl>
      <ManageUserControls account={account} isSelf={isSelf} />
    </div>
  );
}
