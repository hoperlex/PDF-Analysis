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
 *
 * **The one inline script in the application is here** (`P7-1`): a blocking `<script>` in
 * `<head>` that applies a stored light/dark choice to `<html data-theme>` before the first
 * paint, so a visitor who chose the opposite of their system's theme no longer sees one frame
 * of the system's (`shared/lib/theme-boot-script.ts` says what it does and what it never
 * does). Its text is fixed by three constants and carries nothing of the request, so every
 * response has the same bytes in that place.
 *
 * `suppressHydrationWarning` is on `<html>` and nowhere else, and only because of that
 * script: the server cannot render `data-theme`, the script adds it before React hydrates,
 * and React would otherwise report the attribute as a mismatch. The flag silences attribute
 * differences on this one element and does not reach its children, so the `D-329` rule — no
 * server markup the client disagrees with — still holds for everything inside `<body>`;
 * `ThemeToggle` still starts at `system` on both sides and moves in an effect.
 */

import type { Metadata } from 'next';
import { cookies } from 'next/headers';
import type { ReactNode } from 'react';

import { AppFrame, AppProviders, THEME_ATTRIBUTE, THEME_CHOICES, THEME_STORAGE_KEY } from '@/_app';
import { themeBootScript } from '@/shared/lib/theme-boot-script';

import { SESSION_COOKIE, subjectOf } from './bff/session/store';

import './globals.css';

export const metadata: Metadata = {
  title: 'AuditManager — PC-01',
  description: 'Локальный разбор одного PDF: прогон, находки, решения, выгрузка CSV.',
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const jar = await cookies();
  const subject = subjectOf(jar.get(SESSION_COOKIE)?.value ?? null);
  // The whole subject the frame renders from (`W50-SHELL-FRAME`): who the account is, its
  // roles, and the two states that decide what its menu offers. Named field by field, so the
  // register's instants — and anything a later row gains — do not ride into the chrome.
  const session =
    subject === null
      ? null
      : {
          login: subject.login,
          displayLabel: subject.displayLabel,
          initials: subject.initials,
          roles: subject.roles,
          isDefaultCredential: subject.isDefaultCredential,
          profileComplete: subject.profileComplete,
        };
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        <script
          // The text is `themeBootScript` over three module constants: no request data.
          dangerouslySetInnerHTML={{
            __html: themeBootScript({
              storageKey: THEME_STORAGE_KEY,
              attribute: THEME_ATTRIBUTE,
              choices: THEME_CHOICES,
            }),
          }}
        />
      </head>
      <body>
        <AppProviders>
          <AppFrame session={session}>{children}</AppFrame>
        </AppProviders>
      </body>
    </html>
  );
}
