import { PageShell } from '@/shared/ui';
import { UserCard } from '@/widgets/user-card';

export interface AdminUserPageProps {
  readonly userUid: string;
}

export function AdminUserPage({ userUid }: AdminUserPageProps) {
  return (
    <PageShell title="Пользователь" subtitle="Просмотр и управление учётной записью.">
      <UserCard userUid={userUid} />
    </PageShell>
  );
}
