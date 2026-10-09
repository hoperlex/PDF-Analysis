import { describe, expect, it } from 'vitest';

import type { ScreenDecision, ScreenDecisionSubject } from '@/shared/config';
import { screenAt, screenDecision } from '@/shared/config';

// W51-PLAN §4: the three registration screens are public, the two account
// escape routes need a session, and the three administration screens need admin.
const PUBLIC = ['/login', '/register', '/register/submitted'] as const;
const ACCOUNT = ['/account', '/account/password'] as const;
const ADMIN = ['/admin/users', '/admin/users/[user_uid]', '/admin/registrations'] as const;

const complete = (roles: readonly string[]): ScreenDecisionSubject => ({
  roles, isDefaultCredential: false, profileComplete: true,
});
const states: readonly { name: string; subject: ScreenDecisionSubject | null; admin: ScreenDecision }[] = [
  { name: 'guest', subject: null, admin: 'sign-in' },
  { name: 'default password', subject: { ...complete(['admin']), isDefaultCredential: true }, admin: 'change-password' },
  { name: 'incomplete profile', subject: { ...complete(['admin']), profileComplete: false }, admin: 'complete-profile' },
  { name: 'no roles', subject: complete([]), admin: 'forbidden' },
  { name: 'expert', subject: complete(['expert']), admin: 'forbidden' },
  { name: 'admin', subject: complete(['admin']), admin: 'open' },
  { name: 'both roles', subject: complete(['expert', 'admin']), admin: 'open' },
];

describe('W51 screen access for each standing', () => {
  it('keeps the eight W51 addresses and their independent access classes', () => {
    for (const address of PUBLIC) {
      const row = screenAt(address);
      expect(row, address).toMatchObject({ address, access: 'public', roles: 'any' });
    }
    for (const address of ACCOUNT) {
      const row = screenAt(address);
      expect(row, address).toMatchObject({ address, access: 'open-to-default-credential', roles: 'any' });
    }
    for (const address of ADMIN) {
      const row = screenAt(address);
      expect(row, address).toMatchObject({ address, access: 'session', roles: ['admin'] });
    }
  });

  it('answers every W51 screen for guest, default, incomplete and each role set', () => {
    for (const { name, subject, admin } of states) {
      for (const address of PUBLIC) {
        const row = screenAt(address);
        if (!row) throw new Error(`missing ${address}`);
        expect(screenDecision(row, subject), `${name} ${address}`).toBe('open');
      }
      for (const address of ACCOUNT) {
        const row = screenAt(address);
        if (!row) throw new Error(`missing ${address}`);
        expect(screenDecision(row, subject), `${name} ${address}`).toBe(subject === null ? 'sign-in' : 'open');
      }
      for (const address of ADMIN) {
        const row = screenAt(address);
        if (!row) throw new Error(`missing ${address}`);
        expect(screenDecision(row, subject), `${name} ${address}`).toBe(admin);
      }
    }
  });
});
