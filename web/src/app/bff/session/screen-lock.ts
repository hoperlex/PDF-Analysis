/**
 * `requireScreen` — the server guard every route file calls (`W50-PLAN.md` §3.2). It
 * replaces `R-50`'s `requireAChangedPassword()`, which decided one of these five things.
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
 * So each `page.tsx` under `web/src/app` calls `requireScreen` with **its own address** and
 * its own `params` and `searchParams`, and the address is a row of the screen registry
 * (`web/src/shared/config/screen-registry.ts`). `web/tests/guards/screen-guard.guard.test.ts`
 * reads every route file and is red **naming the address** of one that does not, and
 * `web/tests/guards/screen-registry.guard.test.ts` is red for a page with no row or a row
 * with no page: the sweep is what makes "no unregistered screen opens" a property of the
 * application rather than of whoever remembered.
 *
 * ## The five decisions, in order
 *
 * Each is a redirect or a normal return, never a thrown framework error:
 *
 *   1. no session, and the screen is not `public` → `/login?next=<the address asked for>`;
 *   2. a session on a default credential, on a `session` screen → `/account/password`;
 *   3. a session whose profile is incomplete, on a `session` screen → `/account`;
 *   4. a session holding none of the screen's roles → `/403?from=<the address asked for>`;
 *   5. a session visiting `/login` → `/`.
 *
 * `next` and `from` are the concrete path and its query string, passed through the registry's
 * one validator; a value it refuses is dropped, never echoed. The fragment never reaches the
 * server and is not preserved. No cycle exists: `/login` and `/403` are `public`,
 * `/account/password` and `/account` are `open-to-default-credential`, and `/` is `session`.
 *
 * A stale session — a cookie the register no longer holds, because an upstream `401` closed
 * it — is no session here: `subjectOf` answers `null` for it.
 *
 * ## What it does not do
 *
 * It does not authorize anything. The API refuses every operation on its own evidence
 * (`auditmanager.api.security`), so a browser that skipped these screens entirely would still
 * get nowhere. This function decides where a reviewer is *sent*. It reads the cookie and the
 * register through `subjectOf` and nothing else — never `credentialOf`, which is the
 * forwarder's alone — and what it returns is the subject, which carries no credential.
 */

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

import type { RouteParams, ScreenAccessOf, ScreenAddress, ScreenEntry } from '@/shared/config';
import {
  CHANGE_PASSWORD_SCREEN,
  FORBIDDEN_SCREEN,
  FROM_PARAM,
  HOME_SCREEN,
  NEXT_PARAM,
  PROFILE_SCREEN,
  SIGN_IN_SCREEN,
  concreteAddress,
  safeReturnPath,
  screenAt,
  screenDecision,
} from '@/shared/config';

import type { SessionAccount } from './store';
import { SESSION_COOKIE, subjectOf } from './store';

export { CHANGE_PASSWORD_SCREEN };

/** What Next hands every route file. Both are promises in Next 15; both may be absent in a test. */
export interface ScreenRouteProps {
  readonly params?: Promise<RouteParams> | undefined;
  readonly searchParams?: Promise<RouteParams> | undefined;
}

/** Who the guard let through: the subject on every screen that needs a session, else maybe none. */
export type ScreenSubject<A extends ScreenAddress> =
  ScreenAccessOf<A> extends 'public' ? SessionAccount | null : SessionAccount;

/** A route file named an address the registry does not have. A defect in the tree, not a state. */
export class UnregisteredScreenError extends Error {
  constructor(address: string) {
    super(`requireScreen: ${address} is not a row of the screen registry`);
    this.name = 'UnregisteredScreenError';
  }
}

/**
 * Guard one route file. Returns the session's subject (or `null` for a guest on a `public`
 * screen) when the screen may render; redirects otherwise.
 */
export async function requireScreen<A extends ScreenAddress>(
  address: A,
  props: ScreenRouteProps,
): Promise<ScreenSubject<A>> {
  const screen = screenAt(address);
  // Unreachable from the tree: `ScreenAddress` is the registry's own set, so a route file
  // naming another address does not compile. Kept so a cast cannot turn it into an open door.
  if (screen === undefined) throw new UnregisteredScreenError(address);
  return (await enforceScreen(screen, props)) as ScreenSubject<A>;
}

/**
 * The five decisions for one registry row. Exported for the guard's own tests, which drive a
 * role-gated row W50's registry does not have (`R-60`); route files call `requireScreen`.
 */
export async function enforceScreen(
  screen: ScreenEntry,
  props: ScreenRouteProps,
): Promise<SessionAccount | null> {
  const jar = await cookies();
  const subject = subjectOf(jar.get(SESSION_COOKIE)?.value ?? null);

  // Decisions 1–4 are `screenDecision`'s, in its order (`@/shared/config`): the frame's menu
  // asks the same function, so it offers exactly the screens this guard opens. Each answer
  // here has one redirect.
  const decision = screenDecision(screen, subject);

  // 1. A guest, on anything but a public screen.
  if (decision === 'sign-in') {
    const next = await askedFor(screen, props);
    redirect(next === null ? SIGN_IN_SCREEN : `${SIGN_IN_SCREEN}?${NEXT_PARAM}=${encodeURIComponent(next)}`);
  }
  // 2. `R-50`: a default credential opens nothing but the screens that change it.
  if (decision === 'change-password') redirect(CHANGE_PASSWORD_SCREEN);
  // 3. `R-59`: an incomplete profile opens nothing but the screens that complete it.
  if (decision === 'complete-profile') redirect(PROFILE_SCREEN);
  // 4. Any one of the row's roles; a role value this tier does not know matches no row.
  if (decision === 'forbidden') {
    const from = await askedFor(screen, props);
    redirect(
      from === null ? FORBIDDEN_SCREEN : `${FORBIDDEN_SCREEN}?${FROM_PARAM}=${encodeURIComponent(from)}`,
    );
  }

  // The decision let the request through: a guest got here only on a public screen.
  if (subject === null) return null;

  // 5. A session has nothing to do on the sign-in screen; the frame carries the way out.
  if (screen.address === SIGN_IN_SCREEN) redirect(HOME_SCREEN);

  return {
    login: subject.login,
    displayLabel: subject.displayLabel,
    initials: subject.initials,
    roles: subject.roles,
    isDefaultCredential: subject.isDefaultCredential,
    profileComplete: subject.profileComplete,
  };
}

/**
 * The validated address this request asked for, or `null` when it cannot be carried.
 *
 * Validated against the one row being enforced: the address asked for *is* this screen, so
 * its path must have this row's shape, and the registry's validator decides the rest (the
 * length, the leading slash, the query's characters). The BFF validates the same value again
 * against the whole registry before it redirects to it.
 */
async function askedFor(screen: ScreenEntry, props: ScreenRouteProps): Promise<string | null> {
  const params = props.params === undefined ? {} : await props.params;
  const searchParams = props.searchParams === undefined ? {} : await props.searchParams;
  return safeReturnPath(concreteAddress(screen.address, params, searchParams), [screen]);
}
