import { PageShell } from '@/shared/ui';
import { UserCard } from '@/widgets/user-card';

export interface AdminUserPageProps {
  readonly userUid: string;
  /** The signed-in account's login, from the route's guard; `C-20`'s self-refresh needs it. */
  readonly signedInLogin?: string | null | undefined;
}

export function AdminUserPage({ userUid, signedInLogin = null }: AdminUserPageProps) {
  return (
    <PageShell title="Пользователь" subtitle="Просмотр и управление учётной записью.">
      <UserCard userUid={userUid} signedInLogin={signedInLogin} />
    </PageShell>
  );
}
