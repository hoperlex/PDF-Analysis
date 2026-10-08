import { PageShell } from '@/shared/ui';
import { UserList } from '@/widgets/user-list';

export function AdminUsersPage() {
  return (
    <PageShell title="Пользователи" subtitle="Учётные записи и их роли. Откройте запись для управления.">
      <UserList />
    </PageShell>
  );
}
