'use client';

import Link from 'next/link';

import { displayLabelOf, initialsOf, roleLabels, unreadableAccountDetail, useMe } from '@/entities/account';
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
    <PageShell title="Профиль" subtitle={profileComplete || account.profile_complete ? 'Данные вашей учётной записи.' : 'Завершите профиль, чтобы открыть остальные разделы.'}>
      <div className={styles.profile} data-account-profile-complete={account.profile_complete}>
        <Avatar initials={initialsOf(label)} colourKey={account.login} label={`Аватар: ${label}`} />
        <p className="am-note"><strong>{label}</strong></p>
        <p className="am-note">Роли: {roles.length ? roles.join(', ') : 'не назначены'}.</p>
        <EditProfileForm account={account} next={next ?? null} />
        <p className="am-note"><Link href={CHANGE_PASSWORD_SCREEN}>Сменить пароль</Link></p>
      </div>
    </PageShell>
  );
}
