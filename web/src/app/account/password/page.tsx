/**
 * `/account/password` — the route file for the password-change screen.
 *
 * The guard and one read, then a delegation, which is all a route file is allowed to be
 * here:
 *
 *   1. `requireScreen('/account/password', …)` — the screen registry's row is
 *      `open-to-default-credential`: a session is required (a guest is sent to sign in and
 *      comes back here), and a session still on its seeded or reset password **may open it**.
 *      The guard answers who the session belongs to through `subjectOf` — the narrow reader
 *      that **never returns the credential it holds**;
 *   2. the outcome the seam redirected back with, validated against the feature's closed
 *      set so a hand-typed query string renders no sentence at all.
 *
 * `credentialOf` is not called here and must not be: it is the only function that returns
 * the token, the forwarder is its only caller, and a screen that received one would put it
 * in the RSC payload — which is bytes the browser holds.
 *
 * Dynamic by construction, and declared so rather than inferred: it reads a cookie, and a
 * password screen served from a cache is a password screen showing someone else's session.
 *
 * **Its row is open to a default credential, and that is the point of it.** `R-50` sends a
 * default credential here; a screen that refused one would be a deployment in which the
 * only way out of the refusal is barred by the refusal.
 */

import { ChangePasswordPage } from '@/_pages/change-password';
import { CHANGE_PASSWORD_OUTCOME_PARAM, isChangePasswordOutcome } from '@/features/change-password';
import { NEXT_PARAM, safeReturnPath } from '@/shared/config';

import type { ScreenRouteProps } from '../../bff/session/screen-lock';
import { requireScreen } from '../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function ChangePasswordRoute({ params, searchParams }: ScreenRouteProps) {
  const subject = await requireScreen('/account/password', { params, searchParams });

  const query = searchParams === undefined ? {} : await searchParams;
  const raw = query[CHANGE_PASSWORD_OUTCOME_PARAM];
  const candidate = Array.isArray(raw) ? raw[0] : raw;
  const asked = query[NEXT_PARAM];

  return (
    <ChangePasswordPage
      login={subject.login}
      outcome={isChangePasswordOutcome(candidate) ? candidate : null}
      next={safeReturnPath(Array.isArray(asked) ? asked[0] : asked)}
      // `R-50`. The register's answer, which the API gave it at sign-in. This screen is the
      // one a default credential is sent to, and this prop is what lets it say so.
      mustChange={subject.isDefaultCredential}
    />
  );
}
