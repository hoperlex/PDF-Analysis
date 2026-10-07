/**
 * The chrome around every screen: product name, the navigation the session may use, the
 * instance label, the theme control, and the account menu — or, for a guest, the way in.
 *
 * A server component. It reads the cosmetic instance label from configuration and holds no
 * state; the parts that need state are client islands of their own — the navigation
 * (`frame-navigation.tsx`, which reads the current page), the account menu's `Menu` and the
 * theme toggle — so nothing here forces the whole tree into the client bundle.
 *
 * **It is handed the session; it does not read one.** `app/layout.tsx` reads the cookie and
 * the register and passes the subject down. A component that reached for `cookies()` would be
 * an async server component, which every instrument that renders this frame as a *screen*
 * would then have to await, and it would put a request-scoped read inside the layer whose job
 * is composition. The layout is the framework adapter and the only place in `_app` allowed to
 * know there is a request at all.
 *
 * **It makes no API call.** Everything it shows comes from the subject the layout passes; a
 * `getMe` here would add an undeclared call to every route of the live journey.
 *
 * **Every address it links comes from the screen registry** (`@/shared/config`): the menu is
 * `buildNavigation`'s, the brand goes to `HOME_SCREEN`, the way in to `SIGN_IN_SCREEN`, and
 * the account menu's items to `PROFILE_SCREEN` and `CHANGE_PASSWORD_SCREEN`.
 * `web/tests/unit/shell/frame-sources.test.ts` refuses a literal address in `_app`.
 */

import Link from 'next/link';
import type { ReactNode } from 'react';

import { HOME_SCREEN, SIGN_IN_SCREEN, getInstanceLabel } from '@/shared/config';

import { AccountMenu } from './account-menu';
import { FrameNavigation } from './frame-navigation';
import { buildNavigation } from './navigation';
import { ThemeToggle } from './theme-toggle';
import styles from './app-frame.module.css';

/**
 * What the frame is told about the open session: the subject `requireScreen` and the register
 * hold, minus the instants. `login` is the e-mail once the profile is complete (the legacy
 * login before); there is no separate e-mail field.
 */
export interface AppFrameSession {
  readonly login: string;
  readonly displayLabel: string;
  readonly initials: string;
  /** A plain string list, so a value this build does not know reaches the frame as a fault. */
  readonly roles: readonly string[];
  readonly isDefaultCredential: boolean;
  readonly profileComplete: boolean;
}

export interface AppFrameProps {
  readonly children: ReactNode;
  /**
   * The open session, or `null` when this browser has none.
   *
   * **Required, with no default.** `D-113`: the bar rendered `Вход` on every screen,
   * including to a reviewer who was signed in and reading the dashboard — measured in a
   * browser, on a screen whose data only loads with a session. A prop with a default would
   * have let a caller keep that defect by omission; a required one makes every renderer of
   * this frame say which of the two states it is rendering.
   */
  readonly session: AppFrameSession | null;
}

/**
 * The footer: what is true of access in this alpha, in the words of `R-60` and of the
 * contract's own `Role` description — `expert` makes product changes, `admin` manages
 * accounts (reading needs no role, so the sentence claims nothing about it). It replaced
 * «Альфа-версия. Один проверяющий, без разделения доступа между учётными записями.», which
 * W49's role set made false; `screen-claims-about-the-system.guard.test.ts` keeps a sentence
 * that denies roles or a separation of access off every rendered screen while the contract
 * declares `Role`.
 */
export const FRAME_FOOTER = 'Альфа-версия. Изменять данные может эксперт, управлять учётными записями — администратор.';

export function AppFrame({ children, session }: AppFrameProps) {
  const instance = getInstanceLabel();
  return (
    <div className="am-app">
      <header className="am-app__bar">
        <Link className="am-app__brand" href={HOME_SCREEN}>
          AuditManager
        </Link>
        {/*
         * The menu holds exactly the rows `screenDecision` opens for this session — the
         * function the guard asks — so a guest, a default credential and an incomplete
         * profile see no group, and the account menu is how the latter two move on.
         */}
        <FrameNavigation navigation={buildNavigation(session)} />
        <div className={styles.end}>
          {/*
           * `PC-01` stood here once and is gone: it was the programme's own checkpoint code
           * and told a reviewer nothing (`R-18`). The instance label stays — it tells one
           * stand from another, and an operator needs that.
           */}
          {instance !== null ? <span className="am-app__instance">{instance}</span> : null}
          <ThemeToggle />
          {/*
           * `D-113`: the bar must reflect the session. A guest gets the way in and nothing
           * else; a session gets the account menu, which also holds the way out — a POST to
           * the session's own door, never a link.
           */}
          {session === null ? (
            <Link className="am-app__signin" href={SIGN_IN_SCREEN}>
              Вход
            </Link>
          ) : (
            <AccountMenu session={session} />
          )}
        </div>
      </header>
      <main className="am-app__main">{children}</main>
      <footer className="am-app__footer">{FRAME_FOOTER}</footer>
    </div>
  );
}
