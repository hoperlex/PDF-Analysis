/**
 * `entities/account` (`W50-PLAN.md` §3.6): the Russian role labels, the name and the avatar's
 * letters, and the `account.me` query.
 *
 * The rule this file is mostly about is the one `AGENTS.md` §4 calls a silent fallback: a
 * role value outside the contract set must be a typed fault, never a generic label and never
 * dropped. Each such case is driven with a value that really is outside the set.
 */

import { QueryClient } from '@tanstack/react-query';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  MalformedAccountError,
  ROLE_LABELS,
  UnknownRoleError,
  displayLabelOf,
  initialsOf,
  meQueryOptions,
  roleLabel,
  roleLabels,
} from '@/entities/account';
import { initialsOf as sessionInitialsOf } from '@/app/bff/session/subject';
import { ROLE_VALUES, queryKeys } from '@/shared/api';

describe('role labels', () => {
  it('names both contract roles in Russian', () => {
    expect(roleLabel('expert')).toBe('Эксперт');
    expect(roleLabel('admin')).toBe('Администратор');
    // Keyed by the contract's own set: a role added to it without a label does not compile,
    // and this asserts the two sets are the same at run time as well.
    expect(Object.keys(ROLE_LABELS).sort()).toEqual([...ROLE_VALUES].sort());
  });

  it('is a typed fault for a value outside the set, never a fallback label', () => {
    for (const unknown of ['superuser', 'Admin', '', null, 1]) {
      expect(() => roleLabel(unknown)).toThrow(UnknownRoleError);
    }
    const fault = (() => {
      try {
        roleLabel('superuser');
        return null;
      } catch (error) {
        return error;
      }
    })();
    expect(fault).toBeInstanceOf(UnknownRoleError);
    expect((fault as UnknownRoleError).value).toBe('superuser');
  });

  it('labels a set in the contract order, once each, and refuses it whole for one unknown member', () => {
    expect(roleLabels(['admin', 'expert'])).toEqual(['Эксперт', 'Администратор']);
    expect(roleLabels([])).toEqual([]);
    expect(() => roleLabels(['expert', 'superuser'])).toThrow(UnknownRoleError);
  });
});

describe('the name and the avatar letters', () => {
  it('shows the server-resolved label and refuses an empty one', () => {
    expect(displayLabelOf({ display_label: 'Петрова А. С.' })).toBe('Петрова А. С.');
    expect(() => displayLabelOf({ display_label: '   ' })).toThrow(MalformedAccountError);
  });

  it('derives the same letters the session records, for every shape of label', () => {
    for (const label of ['Петрова А.', 'Смирнов Б. И.', 'admin', 'reviewer@example.org', '— 1 —', '  ']) {
      expect(initialsOf(label), label).toBe(sessionInitialsOf(label));
    }
    expect(initialsOf('Петрова А. С.')).toBe('ПА');
  });
});

describe('the account.me query', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  function stubMe(body: unknown) {
    // The generated client refuses to run without a base URL (no localhost default); the
    // browser's is the BFF mount on its own origin.
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'http://web.test/bff/v1');
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );
  }

  const ACCOUNT = {
    archived_at: null,
    display_label: 'Петрова А. С.',
    first_name: 'Анна',
    is_default_credential: false,
    last_name: 'Петрова',
    login: 'petrova@example.org',
    middle_name: 'Сергеевна',
    profile_complete: true,
    roles: ['expert'],
    user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  };

  it('is filed under account.me', () => {
    expect(meQueryOptions().queryKey).toEqual(queryKeys.account.me());
    expect(queryKeys.account.me()).toEqual(['account', 'me']);
  });

  it('reads getMe and hands back the account', async () => {
    stubMe(ACCOUNT);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    expect(await client.fetchQuery(meQueryOptions())).toEqual(ACCOUNT);
  });

  it('fails with a typed fault when getMe lists a role outside the contract set', async () => {
    stubMe({ ...ACCOUNT, roles: ['expert', 'superuser'] });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await expect(client.fetchQuery(meQueryOptions())).rejects.toBeInstanceOf(UnknownRoleError);
  });
});
