/**
 * The chrome around every screen: product name, instance label, the top-level navigation,
 * and the one control that says whether anybody is signed in.
 *
 * A server component. It reads the cosmetic instance label from configuration and holds
 * no state, so nothing here forces the whole tree into the client bundle — the one control
 * that needs state, the theme toggle, is its own client component.
 *
 * **It is handed the session; it does not read one.** `app/layout.tsx` reads the cookie and
 * the register and passes the answer down. Two reasons, and the second is the load-bearing
 * one: a component that reached for `cookies()` would be an async server component, which
 * every instrument that renders this frame as a *screen* would then have to await — and
 * more importantly it would put a request-scoped read inside the layer whose job is
 * composition. The layout is the framework adapter and the only place in `_app` allowed to
 * know there is a request at all.
 */

import Link from 'next/link';
import type { ReactNode } from 'react';

import { SESSION_CLOSE_PATH } from '@/features/sign-in';
import { getInstanceLabel } from '@/shared/config';

import { ThemeToggle } from './theme-toggle';

/** What the frame is told about the open session. Deliberately a login and nothing else. */
export interface AppFrameSession {
  readonly login: string;
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

export function AppFrame({ children, session }: AppFrameProps) {
  const instance = getInstanceLabel();
  return (
    <div className="am-app">
      <header className="am-app__bar">
        <Link className="am-app__brand" href="/projects">
          AuditManager
        </Link>
        {/*
         * The way back in, and it is not decoration.
         *
         * `JUDGE-CLAIM` measured the state without it: a reviewer whose session expired —
         * or whose web container restarted, since the session register lives in the Node
         * process's memory — met `401` on every call and had no route to the sign-in
         * screen except typing the address. The screen existed and nothing pointed at it.
         *
         * One link in the frame, so the wall of refusals has a door beside it.
         */}
        {/*
         * `R-23` makes the knowledge base required inside the alpha, and it is the first
         * screen in this application that hangs off no project. The link is in the frame
         * for the reason the sign-in link is: a screen nothing points at is a screen a
         * reviewer reaches only by typing the address.
         */}
        <Link className="am-app__nav" href="/knowledge-base">
          База знаний
        </Link>
        {/*
         * `R-26`, `W39-REVOKE`. The password screen is where a reviewer revokes their own
         * credentials, and it is in the frame for the reason the two links above it are: a
         * screen nothing points at is a screen a reviewer reaches only by typing the
         * address, and the one thing an account guard must not be is hard to find. It is
         * shown to everybody rather than only to an open session, because the frame is a
         * server component that reads no cookie and a link that appeared and vanished with
         * a session would be chrome that moves under a reviewer; the screen itself says
         * what to do when there is no session.
         */}
        <Link className="am-app__nav" href="/account/password">
          Смена пароля
        </Link>
        {/*
         * `R-23`'s addendum, `W43-PREP`. Four sections the owner ruled wanted, each
         * prepared on the front end before its vertical lands, under the rule that
         * addendum made general: the front end carries the structure before the back end
         * does, with honest stubs.
         *
         * **The layout decision, and it is a decision rather than four more lines.** The
         * bar is one non-wrapping flex row — `display: flex`, no `flex-wrap`, no
         * breakpoint of its own — and it now carries six links where it carried two. Two
         * alternatives were considered and rejected for reasons that are about this
         * repository rather than about taste:
         *
         *   - a second row, or a grouped/disclosed nav, needs a rule in
         *     `web/src/app/globals.css`. That file is not in this task's `allowed_paths`,
         *     it is the shared global stylesheet `AGENTS.md` §1.5 puts behind ownership,
         *     and `W43-COMPARE` is editing `web/src` in another worktree this same wave —
         *     two lanes in one stylesheet is exactly what §3 forbids;
         *   - declaring the class in a CSS module instead would pass
         *     `styling-layer.test.ts` (it reads globals.css PLUS every `*.module.css`)
         *     and still render nothing, because a module hashes its class names and this
         *     file would be naming the unhashed one. A green guard over a class that
         *     does not apply is worse than no class.
         *
         * So: existing classes only, and the working sections stay first. The cost is
         * reported rather than hidden — six links plus the right-hand cluster will
         * overflow this bar on a narrow viewport, and the repair is one `flex-wrap: wrap`
         * in a file this task does not own.
         *
         * The labels are the screens' own titles. `Журнал выполнения` is not shortened to
         * `Журнал` on purpose: the decision journal is `База знаний`, two links to its
         * left, and two things called the journal in one bar is the confusion this
         * programme keeps paying for.
         */}
        <Link className="am-app__nav" href="/blocks">
          Блоки
        </Link>
        <Link className="am-app__nav" href="/optimisation">
          Оптимизация
        </Link>
        <Link className="am-app__nav" href="/logs">
          Журнал выполнения
        </Link>
        <Link className="am-app__nav" href="/workers">
          Исполнители
        </Link>
        {/*
         * `R-44`/`R-45`. Wave 46 in full, no wait for `R-1`'s deploy: the dashboard is
         * the fourth link this wave adds to a bar that already wraps (`D-93`, above), so
         * the wrap rule this comment sits beside is what keeps a seventh link from
         * reopening the wave-43 regression rather than a new rule here.
         */}
        <Link className="am-app__nav" href="/dashboard">
          Дашборд
        </Link>
        {/*
         * `D-113`, and it is the same journey `R-50` is about.
         *
         * This was an unconditional `<Link href="/login">Вход</Link>`: a signed-in reviewer
         * was invited to sign in, on every screen, with no way to sign out anywhere in the
         * chrome. The way out existed — `/login` renders the sign-out panel when a session
         * is open — and nothing pointed at it, which is the defect the sign-in link itself
         * was added to fix, one state over.
         *
         * Both halves use the same class, so this adds no rule to the global stylesheet and
         * no colour to the census: the rule gained the five declarations that make a
         * `<button>` look like the link beside it, and declares nothing new.
         *
         * The sign-out is a POST to the BFF's own door, exactly as the panel's is: the
         * server deletes the row that holds the credential and clears the cookie in one
         * answer. A `<Link>` that "signed out" would be a GET that changes state.
         */}
        {session === null ? (
          <Link className="am-app__signin" href="/login">
            Вход
          </Link>
        ) : (
          <>
            <span className="am-app__session" data-session-login={session.login}>
              {session.login}
            </span>
            <form method="post" action={SESSION_CLOSE_PATH}>
              <button type="submit" className="am-app__signin">
                Выйти
              </button>
            </form>
          </>
        )}
        {/*
         * `PC-01` stood here and is gone. It is the programme's own checkpoint code — it
         * told a reviewer nothing and it named the thing `R-18` says the alpha must stop
         * looking like. The integrator translated the footer for the same reason
         * (`D-54`, `2e90899`) and stopped at the sentence `R-18` names; this is the other
         * half of the same defect. The instance label below stays: it distinguishes one
         * stand from another and an operator needs it.
         */}
        {instance !== null ? <span className="am-app__instance">{instance}</span> : null}
        {/*
         * The only client component in the frame. `AppFrame` itself stays a server
         * component: the theme control holds the state, so nothing else in the tree is
         * pushed into the client bundle by it.
         */}
        <ThemeToggle />
      </header>
      <main className="am-app__main">{children}</main>
      <footer className="am-app__footer">
        {/*
         * `R-18` names the sentence that stood here as a defect a manual test must not meet:
         * "Local prototype. One reviewer, no authentication, no tenancy." It was English, it
         * was on every page, and it addressed a developer rather than the reviewer reading it.
         *
         * The SUBSTANCE is kept rather than deleted. A reviewer who assumes another
         * reviewer's work is walled off from theirs would be wrong in a way that matters to
         * what they are being asked to judge.
         *
         * AMENDED 2026-09-22 after wave 34: it said "без учётных записей" — WITHOUT ACCOUNTS
         * — and accounts now exist. `W37-CERT4` found it as `W37CERT4-2`: a claim about the
         * system's security posture, rendered to a reviewer on every screen INCLUDING the
         * sign-in screen they had just used, and by then the opposite of true. The half that
         * is still true is the one kept: there is no separation of access BETWEEN accounts.
         */}
        Альфа-версия. Один проверяющий, без разделения доступа между учётными записями.
      </footer>
    </div>
  );
}
