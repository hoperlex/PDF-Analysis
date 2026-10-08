/**
 * `/login` — the route file for the sign-in screen.
 *
 * The guard and three reads, then a delegation, which is all a route file is allowed to be
 * here:
 *
 *   1. `requireScreen('/login', …)` — the registry's row is `public`, so a guest passes and
 *      a browser that already holds a session is sent to `/` (`W50-PLAN.md` §3.2, decision
 *      five). It answers who the session belongs to through `subjectOf` — **never the
 *      credential it holds**;
 *   2. the refusal code the exchange redirected back with, validated against the feature's
 *      closed set; an unknown value renders an explicit fault;
 *   3. the `next` address the guard sent a guest here with, passed through the screen
 *      registry's `safeReturnPath`, so only an address of this application reaches the form's
 *      hidden field and an invalid one is dropped without being echoed.
 *
 * `credentialOf` is the only function that returns the token and it is called by the
 * forwarder alone, so nothing that renders can reach a credential even by mistake. A screen
 * that received one would put it in the RSC payload, and the payload is bytes the browser
 * holds.
 *
 * Dynamic by construction — it reads a cookie — and declared so rather than inferred,
 * because a sign-in screen served from a cache is a sign-in screen showing someone else's
 * session.
 */

import { SignInPage } from '@/_pages/sign-in';
import { SIGN_IN_REFUSAL_PARAM, isSignInRefusal } from '@/features/sign-in';
import { NEXT_PARAM, safeReturnPath } from '@/shared/config';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function LoginRoute({ params, searchParams }: ScreenRouteProps) {
  const subject = await requireScreen('/login', { params, searchParams });

  const query = searchParams === undefined ? {} : await searchParams;
  const raw = query[SIGN_IN_REFUSAL_PARAM];
  const candidate = Array.isArray(raw) ? raw[0] : raw;
  const asked = query[NEXT_PARAM];

  return (
    <SignInPage
      login={subject === null ? null : subject.login}
      refusal={isSignInRefusal(candidate) ? candidate : null}
      unknownRefusal={candidate !== undefined && !isSignInRefusal(candidate)}
      next={safeReturnPath(Array.isArray(asked) ? asked[0] : asked)}
    />
  );
}
