import Link from 'next/link';

import { PageShell } from '@/shared/ui';

export function RegisterSubmittedPage() {
  return (
    <PageShell title="Заявка на регистрацию" subtitle="Если форма была успешно отправлена, заявка ожидает решения администратора.">
      <p className="am-note">На этом экране не показываются данные заявки или её решение. Письмо не отправляется. После одобрения войдите с указанными адресом электронной почты и паролем; пока заявка ожидает решения, при входе будет показано состояние ожидания.</p>
      <Link href="/login">Перейти ко входу</Link>
    </PageShell>
  );
}
