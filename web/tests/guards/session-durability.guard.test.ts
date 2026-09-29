/**
 * Guard: `R-47`'s two invariants, restated where a repair could break them, and the gap
 * itself stated as a passing characterization rather than left implicit.
 *
 * `D-65`'s one remaining live item. `web/src/app/bff/session/store.ts` holds every open
 * session in a `Map` on `globalThis`, so a web-container restart signs every reviewer out
 * — on every deploy, not on a rare crash (`OWNER_RULINGS_2026-09-17.md` §3.16 `R-47`).
 *
 * **`W47-PASS` investigated a durable mechanism and did not build one.** Every honest
 * option found needs either `infra/**` (giving the web container a database connection or
 * a volume — `W47-GATE`'s hotspot for this stream) plus a root lockfile change, or a new
 * `contracts/api/v1/openapi.json` operation (the same reseal-avoidance rule `P2` is
 * stopped by). `docs/program/W47-PASS.md` §3 records the mechanisms checked and why each
 * was refused; this file is the other half — what a *future* repair, whichever mechanism
 * the owner picks, must not break.
 *
 * **Two of the three invariants already have guards**, in
 * `web/tests/unit/session/session-store.test.ts`, and are not duplicated here:
 *
 *   - `'hands the credential to the forwarder and to nothing else'` is the register-side
 *     half of "the credential never reaches the browser" — `subjectOf`'s shape carries no
 *     `credential` field, checked by name (`Object.keys(...).sort()`), not by absence of a
 *     symptom. Verified capable of catching a regression: mutating `subjectOf` to also
 *     return `row.credential` reddens it (checked by hand, reverted, not committed).
 *   - `'ends a session on request, and the identifier then opens nothing'` is the
 *     register-side half of "a revoked credential stops working at once" — after
 *     `closeSession`, `credentialOf` returns `null`. Verified the same way: mutating
 *     `closeSession` to a no-op reddens it.
 *
 * The API-side half of revocation — a forwarded request under a stale `token_epoch`
 * answering `401` — is `tests/integration/auth/test_revocation.py::
 * test_a_credential_stops_being_accepted_the_moment_the_account_is_revoked`, on the backend
 * and out of this file's reach; re-run, unchanged, as part of this stream's own gate.
 *
 * **What is new here** is the third invariant this wave adds: the *cookie itself* — what a
 * browser actually receives, not the register's internal shape — carries none of the
 * credential's bytes, plus the durability gap, characterized rather than assumed.
 */

import { beforeEach, describe, expect, it } from 'vitest';

import {
  closeSession,
  credentialOf,
  forgetEverySession,
  openSession,
  sessionCookie,
  subjectOf,
} from '@/app/bff/session/store';

const HOUR = 3600;
const LOGIN = 'проверяющий';

/** Long and structurally distinctive, so a substring or an encoding of it is easy to spot. */
const CREDENTIAL = 'am2.eyJzdWIiOiJ1c3JfZGlzdGluY3RpdmUtY3JlZGVudGlhbC1ieXRlcy0xMjM0NTY3ODkw.tag-9f3c1a';

beforeEach(() => {
  forgetEverySession();
});

describe('the cookie a browser receives carries none of the credential', () => {
  it('the Set-Cookie value contains no substring of the minted credential', () => {
    const id = openSession(LOGIN, CREDENTIAL, HOUR, false);
    const cookie = sessionCookie(id, HOUR, false);
    expect(cookie).not.toContain(CREDENTIAL);
    // Not just the whole string: no long substring of it either, which would catch a
    // repair that truncated or partially re-encoded the credential into the cookie.
    for (let start = 0; start + 16 <= CREDENTIAL.length; start += 8) {
      const slice = CREDENTIAL.slice(start, start + 16);
      expect(cookie.includes(slice), `cookie contains a slice of the credential: ${slice}`).toBe(
        false,
      );
    }
  });

  it('the cookie does not decode to the credential under base64 or hex', () => {
    const id = openSession(LOGIN, CREDENTIAL, HOUR, false);
    const cookie = sessionCookie(id, HOUR, false);
    const value = (cookie.split(';')[0] ?? '').split('=')[1] ?? '';
    let base64Decoded = '';
    try {
      base64Decoded = Buffer.from(value, 'base64').toString('utf8');
    } catch {
      // not base64 -- fine, the assertion below still holds on the empty string
    }
    expect(base64Decoded).not.toBe(CREDENTIAL);
    expect(value).not.toBe(Buffer.from(CREDENTIAL).toString('hex'));
  });
});

describe('R-47: the durability gap, characterized rather than left implicit', () => {
  it('a process restart loses every open session, exactly as it does today', () => {
    // `forgetEverySession` is the test double for what a fresh process finds: an empty
    // `globalThis` registry, because a real restart starts a new process with nothing in
    // it. This does not simulate a restart's *side effects* (an HTTP round-trip, a new
    // container) -- it simulates the one fact that matters here, that the Map is gone.
    const id = openSession(LOGIN, CREDENTIAL, HOUR, false);
    expect(subjectOf(id)).not.toBeNull();
    expect(credentialOf(id)).toBe(CREDENTIAL);

    forgetEverySession(); // stands in for a restart: a fresh process, an empty registry

    expect(subjectOf(id)).toBeNull();
    expect(credentialOf(id)).toBeNull();
    expect(closeSession(id)).toBe(false); // there is nothing left to close, either
  });

  // **This test is expected to go red the day a genuine durable mechanism lands** —
  // `R-47`, `D-65`. That is the point of writing it as a passing assertion now: whatever
  // mechanism the owner rules for the repair, session state must then survive exactly the
  // event this test simulates. When it does, the assertions above invert (a session opened
  // before the simulated restart must still be found after it) and this `describe` block
  // should be replaced by that assertion, not kept alongside it as a second, contradictory
  // guard. Recorded so that day the change reads as the fix landing, not as an unexplained
  // regression.
});
