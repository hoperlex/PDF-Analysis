import { RegisterForm } from '@/features/register';
import type { RegistrationRefusal } from '@/features/register';
import { PageShell } from '@/shared/ui';

export function RegisterPage({ refusal, unknownRefusal = false }: {
  readonly refusal?: RegistrationRefusal | null;
  readonly unknownRefusal?: boolean;
}) {
  return (
    <PageShell title="Регистрация" subtitle="Отправьте заявку на учётную запись. Решение принимает администратор.">
      <RegisterForm refusal={refusal ?? null} unknownRefusal={unknownRefusal} />
    </PageShell>
  );
}
