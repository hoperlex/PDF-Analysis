'use client';

import Link from 'next/link';

import { displayLabelOf, initialsOf, roleLabels, unreadableAccountDetail, useMe } from '@/entities/account';
import { lastSignInText } from '@/entities/user';
import { EditProfileForm } from '@/features/edit-profile';
import { failureMessage } from '@/shared/api/failure-message';
import { CHANGE_PASSWORD_SCREEN } from '@/shared/config';
import { Avatar, ErrorState, LoadingState, PageShell } from '@/shared/ui';
import styles from './account-page.module.css';

export interface AccountPageProps {
  readonly profileComplete: boolean;
  readonly next?: string | null;
}

export function AccountPage({ profileComplete, next }: AccountPageProps) {
  const me = useMe();
  if (me.isPending) return <PageShell title="Профиль"><LoadingState what="профиль" /></PageShell>;
  if (me.isError) {
    // `C-23`: the shared Russian reading, never `error.message` (`"<code>: <English>"`).
    const failure = failureMessage(me.error);
    return (
      <PageShell title="Профиль">
        <div data-account-failure={failure.kind}>
          <ErrorState title="Профиль не загружен" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void me.refetch()} />
        </div>
      </PageShell>
    );
  }

  const account = me.data;
  let label: string;
  let roles: readonly string[];
  try {
    label = displayLabelOf(account);
    roles = roleLabels(account.roles);
  } catch (error) {
    return <PageShell title="Профиль"><ErrorState title="Данные профиля не распознаны" detail={unreadableAccountDetail(error)} /></PageShell>;
  }

  return (
    <PageShell title="Профиль" subtitle={profileComplete || account.profile_complete ? 'Данные вашей учётной записи.' : 'Завершите профиль, чтобы открыть остальные разделы.'} surface="canvas">
      <div className={styles.profile} data-account-profile-complete={account.profile_complete}>
        <header className={styles.identity}>
          <Avatar initials={initialsOf(label)} colourKey={account.user_uid} label={`Аватар: ${label}`} />
          <h2 className={styles.name}>{label}</h2>
        </header>
        <dl className={styles.facts}>
          <dt className="am-form__hint">Адрес входа</dt>
          <dd className={styles.login}>{account.login}</dd>
          <dt className="am-form__hint">Роли</dt>
          <dd data-account-profile-roles="">{roles.length ? roles.join(', ') : 'не назначены'}</dd>
          <dt className="am-form__hint">Последний вход</dt>
          <dd data-account-last-sign-in={account.last_sign_in_at === null ? 'never' : 'at'}>{lastSignInText(account.last_sign_in_at)}</dd>
        </dl>
        <section className={`am-section ${styles.section}`} aria-labelledby="account-profile-heading">
          <h2 id="account-profile-heading">Данные профиля</h2>
          <EditProfileForm account={account} next={next ?? null} />
        </section>
        <p className={styles.leave} data-account-password-link="">
          <Link className="am-button am-button--quiet" href={CHANGE_PASSWORD_SCREEN}>Сменить пароль</Link>
        </p>
      </div>
    </PageShell>
  );
}
