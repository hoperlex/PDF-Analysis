/**
 * `/login` — the screen that exchanges a login and a password for a session.
 *
 * Composition only, like every other page slice: the credentials card, centred in the shared
 * guest frame, around the form from the `sign-in` feature. No query, no mutation, no domain
 * rule and — the point of the whole design — no client JavaScript that could hold a
 * credential: the form's only script is the `SubmitLock` island, which reads no field (`C-22`).
 *
 * The card is the whole screen (owner, 2026-11-09): the hero copy beside it and the illustrated
 * «Демонстрация сценария» scene are gone, so the card's title is the page's one `h1`. The
 * frame's inert section preview stays beside it; this slice does not draw it.
 *
 * Only a guest sees this screen: the route's guard sends a browser that already holds a
 * session to `/` (`W50-PLAN.md` §3.2, decision five), and the frame's account menu carries
 * the way out. So the screen has one shape, the credentials form, and a link to the
 * registration form for someone who has no account yet (`C-21`).
 */

import Link from 'next/link';

import { REGISTER_SCREEN } from '@/shared/config/screen-registry';
import { ErrorState } from '@/shared/ui';
import type { SessionEndReason, SignInRefusal } from '@/features/sign-in';
import { SignInForm, signInReasonMessage } from '@/features/sign-in';

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
  /**
   * Why there is no session, when the server knows (`expired`, `ended` or `invalid`): said above
   * the form in one sentence. Absent when it does not — a first visit says nothing.
   */
  readonly reason?: SessionEndReason | null | undefined;
}

export function SignInPage({ refusal, next, unknownRefusal = false, reason = null }: SignInPageProps) {
  return (
    <section className={styles.screen} aria-labelledby="sign-in-title">
      <div className={styles.card}>
        <header className={styles.header}>
          <span className={styles.signInMark} aria-hidden="true"><BrandMark /></span>
          <div>
            <p className={styles.cardEyebrow}>Вход в систему</p>
            <h1 className={styles.cardTitle} id="sign-in-title">Продолжить работу</h1>
          </div>
        </header>
        {reason === null ? null : (
          <p className={styles.reason} role="status" data-sign-in-reason={reason}>{signInReasonMessage(reason)}</p>
        )}
        <p className={styles.formLead}>Используйте почту или прежний логин для входа.</p>
        {unknownRefusal ? <div data-sign-in-refusal="unknown"><ErrorState title="Неизвестный ответ входа" detail="Сервер вернул состояние, которое эта версия страницы не понимает." /></div> : null}
        <SignInForm refusal={refusal} next={next} />
        <p className={styles.register} data-sign-in-register="">
          Нет учётной записи? <Link href={REGISTER_SCREEN}>Подать заявку на доступ</Link>
        </p>
        <p className={styles.accessNote}>Доступ к данным — после авторизации</p>
      </div>
    </section>
  );
}

/** The product mark, the same three strokes the frame's brand link draws. */
function BrandMark() {
  return (
    <svg viewBox="0 0 36 36" fill="none" focusable="false">
      <path d="M4.5 24.5 12 10.8a4.1 4.1 0 0 1 7.2 0l7.4 13.7" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M11.6 24.5 19 10.8a4.1 4.1 0 0 1 7.2 0l5.3 9.8" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M8.8 18.3h18.4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}
