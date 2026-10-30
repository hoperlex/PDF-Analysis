import Link from 'next/link';

import { SIGN_IN_SCREEN } from '@/shared/config';
import { PageShell } from '@/shared/ui';
import styles from './register-submitted-page.module.css';

export function RegisterSubmittedPage() {
  return (
    <PageShell title="Заявка на регистрацию" subtitle="Если форма была успешно отправлена, заявка ожидает решения администратора.">
      <div className={styles.card}>
        <p className="am-note">На этом экране не показываются данные заявки или её решение. Письмо не отправляется. После одобрения войдите с указанными адресом электронной почты и паролем; пока заявка ожидает решения, при входе будет показано состояние ожидания.</p>
        <Link className="am-button" href={SIGN_IN_SCREEN}>Перейти ко входу</Link>
      </div>
    </PageShell>
  );
}
