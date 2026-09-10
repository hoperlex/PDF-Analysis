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
        Local prototype. One reviewer, no authentication, no tenancy.
      </footer>
    </div>
  );
}
