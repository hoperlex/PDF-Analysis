/**
 * The chrome around every screen: product name, instance label, and the top-level
 * navigation the four PC-01 routes hang off.
 *
 * A server component. It reads the cosmetic instance label from configuration and holds
 * no state, so nothing here forces the whole tree into the client bundle — the one control
 * that needs state, the theme toggle, is its own client component.
 */

import Link from 'next/link';
import type { ReactNode } from 'react';

import { getInstanceLabel } from '@/shared/config';

import { ThemeToggle } from './theme-toggle';

export interface AppFrameProps {
  readonly children: ReactNode;
}

export function AppFrame({ children }: AppFrameProps) {
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
        <Link className="am-app__signin" href="/login">
          Вход
        </Link>
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
