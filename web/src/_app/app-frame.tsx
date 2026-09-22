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
         * The SUBSTANCE is kept rather than deleted. It is true, and a reviewer who assumes
         * their verdicts are attributed to a named account, or that someone else's work is
         * walled off from theirs, would be wrong in a way that matters to what they are being
         * asked to judge. What changed is who it is written for.
         */}
        Альфа-версия. Один проверяющий, без учётных записей и разделения доступа.
      </footer>
    </div>
  );
}
