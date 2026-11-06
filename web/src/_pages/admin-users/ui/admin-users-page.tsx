import Link from 'next/link';

import { routes } from '@/shared/lib';
import { PageShell } from '@/shared/ui';
import { UserList } from '@/widgets/user-list';
import styles from './admin-users-page.module.css';

export function AdminUsersPage() {
  return (
    <PageShell title="Пользователи" subtitle="Учётные записи и их роли. Откройте запись для управления.">
      <p className="am-note"><Link href={routes.authEvents()}>Журнал входов</Link></p>
      <div className={styles.panel}><UserList /></div>
    </PageShell>
  );
}
