/**
 * `/login` — the screen that exchanges a login and a password for a session.
 *
 * Composition only, like every other page slice: a presentation canvas inside the shared
 * guest frame and the form from the `sign-in`
 * feature. No query, no mutation, no domain rule and — the point of the whole
 * design — no client JavaScript that could hold a credential: the form's only script is the
 * `SubmitLock` island, which reads no field (`C-22`).
 *
 * Only a guest sees this screen: the route's guard sends a browser that already holds a
 * session to `/` (`W50-PLAN.md` §3.2, decision five), and the frame's account menu carries
 * the way out. So the screen has one shape, the credentials form, and a link to the
 * registration form for someone who has no account yet (`C-21`).
 */

import Link from 'next/link';

import { REGISTER_SCREEN } from '@/shared/config/screen-registry';
import { ErrorState } from '@/shared/ui';
import type { SignInRefusal } from '@/features/sign-in';
import { SignInForm } from '@/features/sign-in';

import styles from './sign-in-page.module.css';

export interface SignInPageProps {
  /**
   * Unused since `C-25`: the guard never renders this screen for a session. Still accepted
   * because the route file (`app/login/page.tsx`) passes it; drop it there and here together.
   */
  readonly login?: string | null | undefined;
  /** The refusal the last attempt was redirected back with, if there was one. */
  readonly refusal?: SignInRefusal | null | undefined;
  /** The validated address to return to once signed in (`W50-PLAN.md` §3.2), if any. */
  readonly next?: string | null | undefined;
  readonly unknownRefusal?: boolean | undefined;
}

export function SignInPage({ refusal, next, unknownRefusal = false }: SignInPageProps) {
  return (
    <section className={styles.screen}>
      <div className={styles.copy}>
        <p className={styles.eyebrow}>Анализ проектной документации</p>
        <h1 className={styles.title}>Точность начинается<br />со входа.</h1>
        <p className={styles.lead}>
          Один вход — и вся цепочка проверки перед вами. От файла до объяснимого экспертного решения.
        </p>
        <div className={styles.card}>
          <header className={styles.header}>
            <span className={styles.signInMark} aria-hidden="true"><OrbitMark /></span>
            <div>
              <p className={styles.cardEyebrow}>Вход в систему</p>
              <h2 className={styles.cardTitle}>Продолжить работу</h2>
            </div>
          </header>
          <p className={styles.formLead}>Используйте почту или прежний логин для входа.</p>
          {unknownRefusal ? <div data-sign-in-refusal="unknown"><ErrorState title="Неизвестный ответ входа" detail="Сервер вернул состояние, которое эта версия страницы не понимает." /></div> : null}
          <SignInForm refusal={refusal} next={next} />
          <p className={styles.register} data-sign-in-register="">
            Нет учётной записи? <Link href={REGISTER_SCREEN}>Подать заявку на доступ</Link>
          </p>
          <p className={styles.accessNote}>Доступ к данным — после авторизации</p>
        </div>
      </div>
      <div className={styles.scene} aria-hidden="true">
        <div className={styles.sceneHeader}>
          <p className={styles.sceneEyebrow}>Демонстрация сценария</p>
          <span className={styles.sceneBadge}>Иллюстрация</span>
        </div>
        <p className={styles.sceneTitle}>Проверка как система связей</p>
        <div className={styles.orbit}>
          <span className={styles.orbitGlow} />
          <span className={`${styles.ring} ${styles.ringOuter}`} />
          <span className={`${styles.ring} ${styles.ringDashed}`} />
          <span className={`${styles.ring} ${styles.ringMiddle}`} />
          <span className={`${styles.ring} ${styles.ringInner}`} />
          <span className={styles.orbitArc} />
          <span className={styles.orbitArcSecondary} />
          <span className={styles.orbitCore}><OrbitMark /></span>
          <span className={`${styles.orbitNode} ${styles.nodeDocument}`}><b>01</b><small>Документ</small></span>
          <span className={`${styles.orbitNode} ${styles.nodeAnalysis}`}><b>02</b><small>Анализ</small></span>
          <span className={`${styles.orbitNode} ${styles.nodeExpert}`}><b>03</b><small>Эксперт</small></span>
        </div>
        <p className={styles.sceneFoot}><span />Управляемый процесс · прозрачные этапы</p>
      </div>
    </section>
  );
}

function OrbitMark() {
  return (
    <svg viewBox="0 0 36 36" fill="none" focusable="false">
      <path d="M4.5 24.5 12 10.8a4.1 4.1 0 0 1 7.2 0l7.4 13.7" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M11.6 24.5 19 10.8a4.1 4.1 0 0 1 7.2 0l5.3 9.8" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M8.8 18.3h18.4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}
