import { RegisterForm } from '@/features/register';
import type { RegistrationRefusal } from '@/features/register';
import { PageShell } from '@/shared/ui';
import styles from './register-page.module.css';

export function RegisterPage({ refusal, unknownRefusal = false }: {
  readonly refusal?: RegistrationRefusal | null;
  readonly unknownRefusal?: boolean;
}) {
  return (
    <PageShell title="Регистрация" subtitle="Отправьте заявку на учётную запись. Решение принимает администратор.">
      <div className={styles.card}>
        <RegisterForm refusal={refusal ?? null} unknownRefusal={unknownRefusal} />
      </div>
    </PageShell>
  );
}
