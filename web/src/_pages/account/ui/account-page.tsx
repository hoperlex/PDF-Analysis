'use client';

import Link from 'next/link';

import { displayLabelOf, initialsOf, roleLabels, useMe } from '@/entities/account';
import { EditProfileForm } from '@/features/edit-profile';
import { ApiError } from '@/shared/api';
import { Avatar, ErrorState, LoadingState, PageShell } from '@/shared/ui';

export interface AccountPageProps {
  readonly profileComplete: boolean;
  readonly next?: string | null;
}

export function AccountPage({ profileComplete, next }: AccountPageProps) {
  const me = useMe();
  if (me.isPending) return <PageShell title="Профиль"><LoadingState what="профиль" /></PageShell>;
  if (me.isError) return (
    <PageShell title="Профиль">
      <ErrorState title="Профиль не загружен" detail={me.error instanceof Error ? me.error.message : 'Неизвестный ответ сервера.'} correlationId={me.error instanceof ApiError ? me.error.correlationId : null} onRetry={() => void me.refetch()} />
    </PageShell>
  );

  const account = me.data;
  let label: string;
  let roles: readonly string[];
  try {
    label = displayLabelOf(account);
    roles = roleLabels(account.roles);
  } catch (error) {
    return <PageShell title="Профиль"><ErrorState title="Данные профиля не распознаны" detail={error instanceof Error ? error.message : 'Неизвестный ответ сервера.'} /></PageShell>;
  }

  return (
    <PageShell title="Профиль" subtitle={profileComplete || account.profile_complete ? 'Данные вашей учётной записи.' : 'Завершите профиль, чтобы открыть остальные разделы.'}>
      <div data-account-profile-complete={account.profile_complete}>
        <Avatar initials={initialsOf(label)} colourKey={account.login} label={`Аватар: ${label}`} />
        <p className="am-note"><strong>{label}</strong></p>
        <p className="am-note">Роли: {roles.length ? roles.join(', ') : 'не назначены'}.</p>
        <EditProfileForm account={account} next={next ?? null} />
        <p className="am-note"><Link href="/account/password">Сменить пароль</Link></p>
      </div>
    </PageShell>
  );
}
