/**
 * Root layout. A framework adapter: it wires the providers and the frame from `_app` and
 * contains no domain logic of its own.
 *
 * **It is the one place in the chrome that reads the request**, and that is the adapter's
 * job rather than a widening of it. `D-113`: the bar offered `Вход` to a reviewer who was
 * already signed in, because the frame was a pure component with nothing to reflect. The
 * cookie is read here, resolved through the register's narrow reader — `subjectOf`, never
 * `credentialOf`, which is the forwarder's alone — and the answer is passed down as a prop,
 * so `AppFrame` stays a pure server component every instrument can render synchronously.
 *
 * Reading a cookie makes every screen dynamic, which they are anyway: this application has
 * no page whose bytes are the same for two reviewers.
 */

import type { Metadata } from 'next';
import { cookies } from 'next/headers';
import type { ReactNode } from 'react';

import { AppFrame, AppProviders } from '@/_app';

import { SESSION_COOKIE, subjectOf } from './bff/session/store';

import './globals.css';

export const metadata: Metadata = {
  title: 'AuditManager — PC-01',
  description: 'Локальный разбор одного PDF: прогон, находки, решения, выгрузка CSV.',
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const jar = await cookies();
  const subject = subjectOf(jar.get(SESSION_COOKIE)?.value ?? null);
  return (
    <html lang="ru">
      <body>
        <AppProviders>
          <AppFrame session={subject === null ? null : { login: subject.login }}>
            {children}
          </AppFrame>
        </AppProviders>
      </body>
    </html>
  );
}
