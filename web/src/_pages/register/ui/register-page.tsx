import Link from 'next/link';

import { RegisterForm } from '@/features/register';
import type { RegistrationRefusal } from '@/features/register';
import { SIGN_IN_SCREEN } from '@/shared/config';
import { PageShell } from '@/shared/ui';
import styles from './register-page.module.css';

export function RegisterPage({ refusal, unknownRefusal = false }: {
  readonly refusal?: RegistrationRefusal | null;
  readonly unknownRefusal?: boolean;
}) {
  return (
    <PageShell title="Регистрация" subtitle="Отправьте заявку на учётную запись. Решение принимает администратор." surface="canvas">
      <div className={styles.card}>
        <RegisterForm refusal={refusal ?? null} unknownRefusal={unknownRefusal} />
        {/* The original's form ends with «Вернуться ко входу»: an applicant who already has an account leaves from here. */}
        <p className="am-note" data-register-back="">Уже есть учётная запись? <Link href={SIGN_IN_SCREEN}>Вернуться ко входу</Link></p>
      </div>
    </PageShell>
  );
}
