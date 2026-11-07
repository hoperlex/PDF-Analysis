/**
 * `/account/password` — the screen that changes a password and, by doing so, revokes every
 * credential minted under the old one.
 *
 * Composition only, like every other page slice: the frame from `shared/ui`, the form from
 * the `change-password` feature. No query, no mutation, no domain rule and — the point of
 * the design this inherits from the sign-in screen — no client JavaScript that could hold a
 * password (the form's one island, `SubmitLock`, reads no field). The route above reads the
 * cookie, asks the register who the session belongs to, and hands the answer down as a prop.
 *
 * Only a session sees this screen: its registry row is `open-to-default-credential`, so the
 * route's guard sends a guest to sign in before this renders (`C-25` removed the guest shape
 * that could not be reached).
 */

import Link from 'next/link';

import { PROFILE_SCREEN } from '@/shared/config';
import { PageShell } from '@/shared/ui';
import type { ChangePasswordOutcome } from '@/features/change-password';
import { ChangePasswordForm, isChangePasswordSuccess } from '@/features/change-password';
import { SESSION_CLOSE_PATH, SIGN_IN_LANDING_PATH } from '@/features/sign-in';
import styles from './change-password-page.module.css';

export interface ChangePasswordPageProps {
  /**
   * The login of the open session. Unused since `C-25` — the guard admits only a session —
   * and still accepted because the route file passes it.
   */
  readonly login?: string | null | undefined;
  /** How the last attempt ended, if there was one. */
  readonly outcome?: ChangePasswordOutcome | null | undefined;
  /**
   * `R-50`. Whether this session is still on the password the deployment was seeded with.
   *
   * It changes one thing on this screen: the sentence at the top, which says why the
   * reviewer is here. A redirect with no explanation is a screen that appears to have
   * refused something without saying what, and a reviewer who cannot tell a lock from a
   * fault reports a fault.
   */
  readonly mustChange?: boolean | undefined;
  readonly next?: string | null | undefined;
}

export function ChangePasswordPage({ outcome, mustChange, next }: ChangePasswordPageProps) {
  return (
    <PageShell
      title="Смена пароля"
      subtitle="Смена пароля отзывает все ранее выданные пропуска этой учётной записи."
      surface="canvas"
    >
      <div className={styles.card}>
        {mustChange === true ? (
          <p className="am-note" data-change-password-required="true">
            Пока пароль этой учётной записи остаётся тем, с которым система была развёрнута,
            остальные разделы закрыты: сервер отвечает отказом на любую операцию, кроме входа
            и смены пароля. Смените пароль здесь — и остальное откроется сразу.
          </p>
        ) : null}
        <ChangePasswordForm outcome={outcome} next={next} />
        <p className="am-note">
          Оба пароля уходят на сервер этого приложения и дальше — на сервер учётных записей.
          Эта страница не хранит ни пароль, ни пропуск и не обращается к хранилищу браузера.
          Новый пропуск выдаётся сразу после смены и остаётся на сервере: в браузер
          возвращается только непрозрачный номер сеанса.
        </p>
        {mustChange === true ? (
          // The original's page ends with «Выйти»: an account that is shut out of every other screen until it changes its
          // password can still leave. A POST to the session's own door, as the frame's menu does; no script.
          <form method="post" action={SESSION_CLOSE_PATH} className={styles.leave} data-change-password-leave="">
            <button type="submit" className="am-button am-button--quiet">Выйти</button>
          </form>
        ) : outcome !== null && outcome !== undefined && isChangePasswordSuccess(outcome) ? (
          // The original sends the person on after a change; here the outcome stays readable and the way on is a link.
          <p className={styles.leave} data-change-password-onward=""><Link href={SIGN_IN_LANDING_PATH}>Перейти на главную</Link></p>
        ) : (
          <p className={styles.leave} data-change-password-back=""><Link href={PROFILE_SCREEN}>Вернуться к профилю</Link></p>
        )}
      </div>
    </PageShell>
  );
}
