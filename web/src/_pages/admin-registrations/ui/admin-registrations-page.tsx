import { PageShell } from '@/shared/ui';
import { RegistrationQueue } from '@/widgets/registration-queue';

export function AdminRegistrationsPage() {
  return (
    <PageShell title="Заявки на регистрацию" subtitle="Рассмотрите ожидающие заявки или прочитайте уже принятые решения.">
      <RegistrationQueue />
    </PageShell>
  );
}
