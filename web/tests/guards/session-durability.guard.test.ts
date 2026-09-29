/**
 * Guard: `R-47`/`R-51`'s invariants, restated where a repair could break them — and, since
 * wave 47, the repair itself.
 *
 * `D-65`. `web/src/app/bff/session/store.ts` held every open session in a `Map` on
 * `globalThis`, so a web-container restart signed every reviewer out — on every deploy, not
 * on a rare crash (`OWNER_RULINGS_2026-09-17.md` §3.16 `R-47`). `W47-PASS` investigated the
 * mechanisms and stopped, because every honest one crossed a boundary it did not own; the
 * owner then ruled `R-51` (§3.17): **a named docker volume, mounted by the web container and
 * by nothing else**, over a database connection for the web tier and over a new contract
 * operation.
 *
 * **The block at the bottom of this file used to be the gap, characterized.** It asserted
 * that a process restart loses every open session, and said in its own comment: *"This test
 * is expected to go red the day a genuine durable mechanism lands ... the assertions above
 * invert and this `describe` block should be replaced by that assertion, not kept alongside
 * it as a second, contradictory guard."* That day is this wave, and this is that
 * replacement. It is written the way the note asked: the same event, the opposite
 * expectation, and the memory-only deployment kept as its own named case rather than
 * deleted — because a deployment that sets no store really does still lose them, and a
 * guard that pretended otherwise would be describing a configuration nobody runs.
 *
 * **Two of the three older invariants already have guards**, in
 * `web/tests/unit/session/session-store.test.ts`, and are not duplicated here:
 *
 *   - `'hands the credential to the forwarder and to nothing else'` — `subjectOf`'s shape
 *     carries no `credential` field, checked by name, not by absence of a symptom.
 *   - `'ends a session on request, and the identifier then opens nothing'` — after
 *     `closeSession`, `credentialOf` returns `null`.
 *
 * The API-side half of revocation — a forwarded request under a stale `token_epoch`
 * answering `401` — is `tests/integration/auth/test_revocation.py::
 * test_a_credential_stops_being_accepted_the_moment_the_account_is_revoked`, on the backend
 * and out of this file's reach.
 *
 * **What this file holds** is the third invariant — the *cookie itself* carries none of the
 * credential's bytes — and `R-51`'s durability, driven against a real file.
 */

import { mkdtempSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SESSION_STORE_VARIABLE } from '@/shared/config/session-store';
import {
  closeSession,
  credentialOf,
  dropTheInMemoryRegister,
  forgetEverySession,
  openSession,
  sessionCookie,
  sessionDurability,
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

describe('R-51: a session survives the container being recreated', () => {
  let directory: string;

  beforeEach(() => {
    directory = mkdtempSync(join(tmpdir(), 'w47lock-register-'));
    process.env[SESSION_STORE_VARIABLE] = join(directory, 'register.json');
    dropTheInMemoryRegister();
    forgetEverySession();
  });

  afterEach(() => {
    delete process.env[SESSION_STORE_VARIABLE];
    dropTheInMemoryRegister();
    rmSync(directory, { recursive: true, force: true });
  });

  it('reports which register is in force rather than leaving it to be discovered', () => {
    expect(sessionDurability().durable).toBe(true);
    delete process.env[SESSION_STORE_VARIABLE];
    expect(sessionDurability()).toEqual({ durable: false, path: null });
  });

  it('finds the session again in a process that has never seen it', () => {
    const id = openSession(LOGIN, CREDENTIAL, HOUR, true);
    expect(credentialOf(id)).toBe(CREDENTIAL);

    // What a restart loses: this process's knowledge of the register, and nothing on the
    // volume. It is the same event the block this replaces simulated, asserted the other
    // way round.
    dropTheInMemoryRegister();

    const after = subjectOf(id);
    expect(after).not.toBeNull();
    expect(after?.login).toBe(LOGIN);
    // `R-50`'s field survives too: a reviewer who was being sent to the change screen
    // before the deploy is still being sent there after it.
    expect(after?.isDefaultCredential).toBe(true);
    expect(credentialOf(id)).toBe(CREDENTIAL);
  });

  it('keeps the credential in a file only this process reads, and not in the cookie', () => {
    const id = openSession(LOGIN, CREDENTIAL, HOUR, false);
    const path = sessionDurability().path as string;
    // The cost `R-51` states, asserted so that it is a known property and not a surprise:
    // the credential IS on the volume. What must stay true is that it is not in the cookie
    // and that the file is not world-readable.
    const mode = statSync(path).mode & 0o777;
    expect(mode & 0o077).toBe(0);
    expect(sessionCookie(id, HOUR, false)).not.toContain(CREDENTIAL);
  });

  it('does not resurrect a session that was closed, or one that expired while it was down', () => {
    const closed = openSession(LOGIN, CREDENTIAL, HOUR, false);
    expect(closeSession(closed)).toBe(true);

    const opened = 1_000_000;
    const shortLived = openSession(LOGIN, `${CREDENTIAL}-short`, 60, false, opened);

    dropTheInMemoryRegister();

    expect(subjectOf(closed)).toBeNull();
    expect(credentialOf(closed)).toBeNull();
    // Read at an instant after its expiry, which is what a container recreated an hour
    // later would find.
    expect(credentialOf(shortLived, opened + 61_000)).toBeNull();
  });

  it('reports a register it cannot read and serves no session, rather than throwing', () => {
    const path = sessionDurability().path as string;
    writeFileSync(path, 'this is not the register', 'utf8');
    dropTheInMemoryRegister();
    const complaint = vi.spyOn(console, 'error').mockImplementation(() => {});
    try {
      expect(subjectOf('0'.repeat(64))).toBeNull();
      expect(complaint).toHaveBeenCalled();
      expect(String(complaint.mock.calls[0]?.[0])).toContain(path);
    } finally {
      complaint.mockRestore();
    }
    // And it recovers: the next sign-in rewrites the file rather than refusing for ever.
    const id = openSession(LOGIN, CREDENTIAL, HOUR, false);
    dropTheInMemoryRegister();
    expect(credentialOf(id)).toBe(CREDENTIAL);
  });
});

describe('R-51: a deployment that names no store still loses them, and says so', () => {
  it('holds sessions in this process only, exactly as it did before wave 47', () => {
    // NOT the old characterization dressed up: this is the behaviour of a deployment that
    // has configured no volume -- `next dev`, and this suite. It is asserted so that the
    // difference between the two configurations is a property somebody wrote down rather
    // than a surprise on the day a compose file loses a line.
    delete process.env[SESSION_STORE_VARIABLE];
    dropTheInMemoryRegister();
    forgetEverySession();
    expect(sessionDurability().durable).toBe(false);

    const id = openSession(LOGIN, CREDENTIAL, HOUR, false);
    expect(credentialOf(id)).toBe(CREDENTIAL);
    dropTheInMemoryRegister();
    expect(subjectOf(id)).toBeNull();
    expect(credentialOf(id)).toBeNull();
    expect(closeSession(id)).toBe(false);
  });
});
