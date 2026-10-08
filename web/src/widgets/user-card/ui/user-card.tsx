'use client';

import Link from 'next/link';

import { displayLabelOf, initialsOf, roleLabels } from '@/entities/account';
import { useUser, userFailure } from '@/entities/user';
import { ManageUserControls } from '@/features/manage-user';
import { Avatar, ErrorState, LoadingState } from '@/shared/ui';

export function UserCard({ userUid }: { readonly userUid: string }) {
  const query = useUser(userUid);
  if (query.isPending) return <LoadingState what="учётную запись" />;
  if (query.isError) {
    const failure = userFailure(query.error);
    return <div data-user-detail-failure={failure.kind}><ErrorState title="Учётная запись не загружена" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void query.refetch()} /></div>;
  }
  const account = query.data;
  let label: string;
  let roles: readonly string[];
  try {
    label = displayLabelOf(account);
    roles = roleLabels(account.roles);
  } catch (error) {
    return <ErrorState title="Данные учётной записи не распознаны" detail={error instanceof Error ? error.message : 'Неизвестный ответ сервера.'} />;
  }
  return (
    <div data-user-state={account.archived_at === null ? 'active' : 'archived'}>
      <p><Link href="/admin/users">К списку пользователей</Link></p>
      <Avatar initials={initialsOf(label)} colourKey={account.login} label={`Аватар: ${label}`} />
      <h2>{label}</h2>
      <p className="am-note">Адрес входа: {account.login}</p>
      <p className="am-note">Роли: {roles.join(', ') || 'не назначены'}.</p>
      <p className="am-note">Состояние: {account.archived_at === null ? 'действует' : 'в архиве'}.</p>
      <ManageUserControls account={account} />
    </div>
  );
}
