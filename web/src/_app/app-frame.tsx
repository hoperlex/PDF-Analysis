/**
 * The chrome around every screen: product name, instance label, and the top-level
 * navigation the four PC-01 routes hang off.
 *
 * A server component. It reads the cosmetic instance label from configuration and holds
 * no state, so nothing here forces the whole tree into the client bundle.
 */

import Link from 'next/link';
import type { ReactNode } from 'react';

import { getInstanceLabel } from '@/shared/config';

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
        <span className="am-app__context">PC-01</span>
        {instance !== null ? <span className="am-app__instance">{instance}</span> : null}
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
