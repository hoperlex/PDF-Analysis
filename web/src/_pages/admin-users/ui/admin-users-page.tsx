import { PageShell } from '@/shared/ui';
import { UserList } from '@/widgets/user-list';
import styles from './admin-users-page.module.css';

export function AdminUsersPage() {
  return (
    <PageShell title="Пользователи" subtitle="Учётные записи и их роли. Откройте запись для управления.">
      <div className={styles.panel}><UserList /></div>
    </PageShell>
  );
}
