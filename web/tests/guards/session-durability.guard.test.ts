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
 *
 * **And, since `W49-BFF-01`, the register's format version 2**: a row carries the subject
 * `getMe` described, the whole subject survives a restart, and a version-1 file is replaced
 * at the first read rather than read — `W49-PLAN.md` §3.5 — which signs everyone out once.
 */

import { mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SESSION_STORE_VARIABLE } from '@/shared/config/session-store';
import type { SessionAccount } from '@/app/bff/session/store';
import {
  REGISTER_FORMAT_VERSION,
  closeSession,
  credentialOf,
  dropTheInMemoryRegister,
  forgetEverySession,
  mintSessionId,
  openSession,
  refreshSubject,
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

describe('Y7: it answers which register is IN FORCE, not how this deployment is configured', () => {
  /**
   * `sessionDurability()` used to answer `durable: path !== null` — the configuration —
   * while its own sentence promised *"which of the two registers is in force"*. On a volume
   * the process cannot write, those are different answers: the register in force is the
   * memory one, every open session dies with the container, and it answered `durable: true`.
   *
   * **This block is new and nothing replaced it**, which is the point. `W47-JUDGE-X` checked
   * the whole tree for a test that pinned this and found none: the file asserted `true` for a
   * *writable* configured directory and `false` for *unset*, and never asked about a
   * configured path the process cannot use. The wrong answer was therefore **uncovered
   * rather than frozen**, which is the cheaper kind of debt and is why this is an addition
   * and not an inversion.
   *
   * **On the two shapes chosen here.** The judge drove a read-only directory and a full
   * filesystem. Neither is drivable from this suite, which runs as **root**: root bypasses
   * the permission bits, so `chmod 0o500` on a directory does not stop it writing and
   * `accessSync(dir, W_OK)` returns success — a test built on `chmod` here would pass for
   * the wrong reason and go red for somebody else. Shown:
   * `mkdir -p ro && chmod 500 ro && node -e "require('fs').accessSync('ro',
   * require('fs').constants.W_OK)"` exits **0** as root; the same line under
   * `setpriv --reuid=65534 --regid=65534 --clear-groups` throws `EACCES`. Measured.
   *
   * So the two cases below use failures the kernel applies to root as well, and each is a
   * real operator shape rather than a contrivance:
   *
   * - **the parent is a file** — a stale file where the mount point should be. The probe
   *   fails at `mkdirSync` and the answer is `false` *before any session exists*, which is
   *   the half a recorded write error can never reach;
   * - **the register path is a directory** — precisely what `- web-sessions:/var/lib/
   *   auditmanager/sessions/register.json` produces, a volume mounted one level too deep.
   *   The probe **passes** (the directory is there and is writable) and the write fails at
   *   `renameSync`, so this is the half that only a recorded failure can see. It stands in
   *   for the full disk for the same reason: permissions are fine and the write is not.
   */

  let directory: string;

  beforeEach(() => {
    directory = mkdtempSync(join(tmpdir(), 'w47fix-durability-'));
    dropTheInMemoryRegister();
  });

  afterEach(() => {
    delete process.env[SESSION_STORE_VARIABLE];
    dropTheInMemoryRegister();
    rmSync(directory, { recursive: true, force: true });
  });

  it('the control: a configured path it can really write is durable', () => {
    process.env[SESSION_STORE_VARIABLE] = join(directory, 'register.json');
    expect(sessionDurability()).toEqual({
      durable: true,
      path: join(directory, 'register.json'),
    });
  });

  it('a configured path whose directory cannot be created is not durable', () => {
    // A file where the mount point should be. `persist()` would die on its `mkdirSync`, so
    // the register in force is memory -- before a single session has been opened.
    const blocked = join(directory, 'sessions');
    writeFileSync(blocked, 'not a directory', 'utf8');
    const path = join(blocked, 'register.json');
    process.env[SESSION_STORE_VARIABLE] = path;

    expect(sessionDurability().durable).toBe(false);
    // And it still names the volume that was meant to hold it: `durable: false` with the
    // configured path beside it is the pair an operator acts on.
    expect(sessionDurability().path).toBe(path);
  });

  it('a session opened there really is lost, which is what durable: false means', () => {
    const blocked = join(directory, 'sessions');
    writeFileSync(blocked, 'not a directory', 'utf8');
    process.env[SESSION_STORE_VARIABLE] = join(blocked, 'register.json');

    const complaint = vi.spyOn(console, 'error').mockImplementation(() => {});
    try {
      // It still serves -- turning a broken volume into "you cannot sign in" would take the
      // stand down for a reason no reviewer can act on.
      const id = openSession(LOGIN, CREDENTIAL, HOUR, false);
      expect(credentialOf(id)).toBe(CREDENTIAL);
      expect(complaint).toHaveBeenCalled();
      dropTheInMemoryRegister();
      // The event `R-51` is about. The session is gone, so `durable: true` would have been
      // a false answer about this exact register.
      expect(subjectOf(id)).toBeNull();
    } finally {
      complaint.mockRestore();
    }
  });

  it('a write that fails although the path looked writable makes it not durable', () => {
    // The directory exists and is writable, and the register path is a directory -- a volume
    // mounted one level too deep. Nothing can see this until a write is attempted: this is
    // the case the permission probe alone would get wrong, and it stands in for a full disk.
    const path = join(directory, 'register.json');
    mkdirSync(path);
    process.env[SESSION_STORE_VARIABLE] = path;

    // Before any write: the probe is satisfied, and honestly so.
    expect(sessionDurability().durable).toBe(true);

    const complaint = vi.spyOn(console, 'error').mockImplementation(() => {});
    try {
      openSession(LOGIN, CREDENTIAL, HOUR, false);
      expect(complaint).toHaveBeenCalled();
    } finally {
      complaint.mockRestore();
    }
    // After the write that failed: it says so, rather than repeating the configuration.
    expect(sessionDurability()).toEqual({ durable: false, path });
  });

  it('a register that starts working is durable again', () => {
    // The control on the line above: a recorded failure must not be sticky, or a deployment
    // that repaired its volume would go on being told it had not.
    const path = join(directory, 'register.json');
    mkdirSync(path);
    process.env[SESSION_STORE_VARIABLE] = path;
    const complaint = vi.spyOn(console, 'error').mockImplementation(() => {});
    try {
      openSession(LOGIN, CREDENTIAL, HOUR, false);
    } finally {
      complaint.mockRestore();
    }
    expect(sessionDurability().durable).toBe(false);

    rmSync(path, { recursive: true, force: true });
    forgetEverySession(); // the next successful write
    expect(sessionDurability()).toEqual({ durable: true, path });
  });

  it('unset is still a configured absence and not a broken volume', () => {
    delete process.env[SESSION_STORE_VARIABLE];
    expect(sessionDurability()).toEqual({ durable: false, path: null });
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

describe('W49: the register is format version 2, and a version-1 file is replaced, not read', () => {
  const ACCOUNT: SessionAccount = {
    login: 'reviewer@example.test',
    displayLabel: 'Проверяющая А. Б.',
    initials: 'ПА',
    roles: ['admin', 'expert'],
    isDefaultCredential: false,
    profileComplete: true,
  };

  let directory: string;
  let path: string;

  beforeEach(() => {
    directory = mkdtempSync(join(tmpdir(), 'w49bff-register-'));
    path = join(directory, 'register.json');
    process.env[SESSION_STORE_VARIABLE] = path;
    dropTheInMemoryRegister();
    forgetEverySession();
  });

  afterEach(() => {
    delete process.env[SESSION_STORE_VARIABLE];
    dropTheInMemoryRegister();
    rmSync(directory, { recursive: true, force: true });
  });

  function onDisk(): { version: unknown; sessions: Record<string, unknown>[] } {
    return JSON.parse(readFileSync(path, 'utf8')) as {
      version: unknown;
      sessions: Record<string, unknown>[];
    };
  }

  it('writes version 2, and the whole subject survives the container being recreated', () => {
    expect(REGISTER_FORMAT_VERSION).toBe(2);
    const id = openSession(ACCOUNT, CREDENTIAL, HOUR);
    expect(onDisk().version).toBe(2);

    dropTheInMemoryRegister();

    expect(subjectOf(id)).toMatchObject(ACCOUNT);
    expect(credentialOf(id)).toBe(CREDENTIAL);
  });

  it('persists a refreshed subject, so a restart does not bring the old one back', () => {
    const id = openSession({ ...ACCOUNT, login: 'admin', profileComplete: false }, CREDENTIAL, HOUR);
    expect(refreshSubject(id, ACCOUNT)).toBe(true);
    dropTheInMemoryRegister();
    expect(subjectOf(id)?.login).toBe(ACCOUNT.login);
    expect(subjectOf(id)?.profileComplete).toBe(true);
  });

  it('replaces a version-1 file at the first read: no session in it opens, and its credentials leave the volume', () => {
    // Exactly what the register wrote before rows carried a subject: a live, well-formed row.
    const id = mintSessionId();
    const now = Date.now();
    writeFileSync(
      path,
      JSON.stringify({
        version: 1,
        sessions: [
          {
            id,
            login: 'проверяющий',
            credential: CREDENTIAL,
            openedAt: now,
            expiresAt: now + HOUR * 1000,
            isDefaultCredential: false,
          },
        ],
      }),
      { encoding: 'utf8', mode: 0o600 },
    );
    dropTheInMemoryRegister();

    const notice = vi.spyOn(console, 'warn').mockImplementation(() => {});
    try {
      expect(subjectOf(id)).toBeNull();
      expect(credentialOf(id)).toBeNull();
      // Said out loud, naming the file: everyone signs in again, once.
      expect(notice.mock.calls.map((call) => String(call[0])).join('\n')).toContain(path);
    } finally {
      notice.mockRestore();
    }
    // Replaced on the spot, not at the next sign-in: version 2, empty, and the old
    // credential's bytes are no longer on the volume.
    expect(onDisk()).toEqual({ version: 2, sessions: [] });
    expect(readFileSync(path, 'utf8')).not.toContain(CREDENTIAL);
    // The replacement is not world-readable either.
    expect(statSync(path).mode & 0o077).toBe(0);
  });

  it('skips a version-2 row with any subject field of the wrong type, and keeps the others', () => {
    const good = openSession(ACCOUNT, CREDENTIAL, HOUR);
    const stored = onDisk();
    const template = stored.sessions[0] as Record<string, unknown>;
    const broken: Record<string, unknown>[] = [
      { roles: ['expert', 'owner'] },
      { roles: 'expert' },
      { profileComplete: 'yes' },
      { isDefaultCredential: undefined },
      { displayLabel: '' },
      { initials: 7 },
      { login: '' },
      { openedAt: 'now' },
    ].map((change) => ({ ...template, ...change, id: mintSessionId() }));
    writeFileSync(path, JSON.stringify({ version: 2, sessions: [template, ...broken] }), 'utf8');
    dropTheInMemoryRegister();

    expect(subjectOf(good)).toMatchObject(ACCOUNT);
    for (const row of broken) expect(subjectOf(row.id as string), JSON.stringify(row)).toBeNull();
  });

  it('reports a version it does not know and serves no session, as for any unreadable file', () => {
    writeFileSync(path, JSON.stringify({ version: 3, sessions: [] }), 'utf8');
    dropTheInMemoryRegister();
    const complaint = vi.spyOn(console, 'error').mockImplementation(() => {});
    try {
      expect(subjectOf('0'.repeat(64))).toBeNull();
      expect(String(complaint.mock.calls[0]?.[0])).toContain('version 3');
    } finally {
      complaint.mockRestore();
    }
  });
});
