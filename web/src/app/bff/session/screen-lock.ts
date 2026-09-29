/**
 * `R-50`, the screens' half: while a session is on the password this deployment was seeded
 * with, **no screen but the change screen opens.**
 *
 * ## Why this is a call in every route file rather than one check somewhere central
 *
 * A layout cannot do it. `app/layout.tsx` renders on every route and is a server component,
 * and a server component is not told which address it is rendering — so a layout that
 * redirected would redirect the change screen to itself, for ever. Middleware cannot do it
 * either: the register lives in this Node process's memory (and, since `R-51`, on a file
 * beside it), and middleware runs in its own runtime with its own module graph, so it can
 * read the *address* and not the *session*. What is left is the route file, which is the
 * one place that has both.
 *
 * So each `page.tsx` under `web/src/app` either calls this, or is named in the register in
 * `web/tests/guards/default-credential-screens.guard.test.ts` as a screen a default
 * credential may open. A new screen that does neither makes that guard red **naming its
 * address**: the sweep is what makes "no other screen opens" a property of the application
 * rather than of whoever remembered.
 *
 * ## What it does not do
 *
 * It does not authorize anything. The API refuses every operation but the exchange and the
 * change for such a credential, independently and on its own evidence
 * (`auditmanager.api.security`), so a browser that skipped these screens entirely would
 * still get nowhere. This function decides where a reviewer is *sent* — and a reviewer sent
 * to the one screen that can help them is the whole of what `R-50`'s field was bought for.
 *
 * A browser with **no** session is not redirected. There is nothing to be on a default
 * credential about; the screen renders and its data calls answer `401`, which is the state
 * the sign-in link in the frame exists for.
 */

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import { SESSION_COOKIE, subjectOf } from './store';

/** The one screen a default credential may open, and the one it is sent to. */
export const CHANGE_PASSWORD_SCREEN = '/account/password';

/**
 * Send this request to the change screen when its session is on a default credential.
 *
 * Reads the cookie and the register and nothing else — never `credentialOf`, which is the
 * forwarder's alone. Returns normally in every other case, including no session at all.
 */
export async function requireAChangedPassword(): Promise<void> {
  const jar = await cookies();
  const subject = subjectOf(jar.get(SESSION_COOKIE)?.value ?? null);
  if (subject === null) return;
  if (!subject.isDefaultCredential) return;
  redirect(CHANGE_PASSWORD_SCREEN);
}
