import { PageShell } from '@/shared/ui';
import { AuthEventList } from '@/widgets/auth-event-list';
import styles from './admin-auth-events-page.module.css';

export function AdminAuthEventsPage() {
  return (
    <PageShell title="Журнал входов" subtitle="Входы, смена паролей и ролей и завершение сеансов, от новых событий к старым.">
      <div className={styles.panel}><AuthEventList /></div>
    </PageShell>
  );
}
