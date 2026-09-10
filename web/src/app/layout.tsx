/**
 * Root layout. A framework adapter: it wires the providers and the frame from `_app` and
 * contains no domain logic of its own.
 */

import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import { AppFrame, AppProviders } from '@/_app';

import './globals.css';

export const metadata: Metadata = {
  title: 'AuditManager — PC-01',
  description: 'Local review of one AR PDF: run, findings, decisions, CSV.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppProviders>
          <AppFrame>{children}</AppFrame>
        </AppProviders>
      </body>
    </html>
  );
}
