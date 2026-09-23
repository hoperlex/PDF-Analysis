/**
 * `/account/password` — the route file for the password-change screen.
 *
 * Two reads and a delegation, which is all a route file is allowed to be here:
 *
 *   1. the session cookie, from the request, resolved through `subjectOf` — the narrow
 *      reader that returns who the session belongs to and **never the credential it holds**;
 *   2. the outcome the seam redirected back with, validated against the feature's closed
 *      set so a hand-typed query string renders no sentence at all.
 *
 * `credentialOf` is not called here and must not be: it is the only function that returns
 * the token, the forwarder is its only caller, and a screen that received one would put it
 * in the RSC payload — which is bytes the browser holds.
 *
 * Dynamic by construction, and declared so rather than inferred: it reads a cookie, and a
 * password screen served from a cache is a password screen showing someone else's session.
 */

import { cookies } from 'next/headers';

import { ChangePasswordPage } from '@/_pages/change-password';
import { CHANGE_PASSWORD_OUTCOME_PARAM, isChangePasswordOutcome } from '@/features/change-password';

import { SESSION_COOKIE, subjectOf } from '../../bff/session/store';

export const dynamic = 'force-dynamic';

interface ChangePasswordRouteProps {
  /** Next 15 hands the query string as a promise. */
  readonly searchParams?: Promise<Record<string, string | string[] | undefined>> | undefined;
}

export default async function ChangePasswordRoute({ searchParams }: ChangePasswordRouteProps) {
  const jar = await cookies();
  const subject = subjectOf(jar.get(SESSION_COOKIE)?.value ?? null);

  const query = searchParams === undefined ? {} : await searchParams;
  const raw = query[CHANGE_PASSWORD_OUTCOME_PARAM];
  const candidate = Array.isArray(raw) ? raw[0] : raw;

  return (
    <ChangePasswordPage
      login={subject === null ? null : subject.login}
      outcome={isChangePasswordOutcome(candidate) ? candidate : null}
    />
  );
}
