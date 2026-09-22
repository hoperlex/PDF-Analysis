/**
 * `/login` — the route file for the sign-in screen.
 *
 * Three reads and a delegation, which is all a route file is allowed to be here:
 *
 *   1. the session cookie, from the request;
 *   2. the register, for who that cookie names — **never for the credential it holds**;
 *   3. the refusal code the exchange redirected back with, validated against the feature's
 *      closed set so a hand-typed query string renders no sentence at all.
 *
 * `subjectOf` is the narrow reader on purpose: `credentialOf` is the only function that
 * returns the token and it is called by the forwarder alone, so nothing that renders can
 * reach a credential even by mistake. A screen that received one would put it in the RSC
 * payload, and the payload is bytes the browser holds.
 *
 * Dynamic by construction — it reads a cookie — and declared so rather than inferred,
 * because a sign-in screen served from a cache is a sign-in screen showing someone else's
 * session.
 */

import { cookies } from 'next/headers';

import { SignInPage } from '@/_pages/sign-in';
import { SIGN_IN_REFUSAL_PARAM, isSignInRefusal } from '@/features/sign-in';

import { SESSION_COOKIE, subjectOf } from '../bff/session/store';

export const dynamic = 'force-dynamic';

interface LoginRouteProps {
  /** Next 15 hands the query string as a promise. */
  readonly searchParams?: Promise<Record<string, string | string[] | undefined>> | undefined;
}

export default async function LoginRoute({ searchParams }: LoginRouteProps) {
  const jar = await cookies();
  const subject = subjectOf(jar.get(SESSION_COOKIE)?.value ?? null);

  const query = searchParams === undefined ? {} : await searchParams;
  const raw = query[SIGN_IN_REFUSAL_PARAM];
  const candidate = Array.isArray(raw) ? raw[0] : raw;

  return (
    <SignInPage
      login={subject === null ? null : subject.login}
      refusal={isSignInRefusal(candidate) ? candidate : null}
    />
  );
}
