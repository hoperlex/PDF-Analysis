import { PageShell } from '@/shared/ui';
import { RegistrationQueue } from '@/widgets/registration-queue';
import styles from './admin-registrations-page.module.css';

export function AdminRegistrationsPage() {
  return (
    <PageShell title="Заявки на регистрацию" subtitle="Рассмотрите ожидающие заявки или прочитайте уже принятые решения.">
      <div className={styles.panel}>
        <RegistrationQueue />
      </div>
    </PageShell>
  );
}
