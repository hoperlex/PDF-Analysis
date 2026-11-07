import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import type { Account, ErrorEnvelope } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { confirmedTemporaryPassword, refreshManagedUser } from '@/features/manage-user';
import { userFailure } from '@/entities/user';
import { UserCard } from '@/widgets/user-card';
import { UserList } from '@/widgets/user-list';

import { WEB_ROOT } from '../../guards/lib/repo';
import { newClient, renderScreen } from '../screens/harness';

const ACCOUNT: Account = {
  archived_at: null,
  display_label: 'Петрова А. С.',
  first_name: 'Анна',
  is_default_credential: false,
  last_name: 'Петрова',
  last_sign_in_at: '2026-11-05T09:30:15Z',
  login: 'petrova@example.org',
  middle_name: 'Сергеевна',
  profile_complete: true,
  roles: ['admin', 'expert'],
  user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
};

function refusal(code: ErrorEnvelope['error_code'], reason: string): ApiError {
  return new ApiError(409, {
    contract_version: '1.40.0',
    error_code: code,
    message: 'Refused',
    correlation_id: 'cid-user-1',
    retryable: false,
    details: { conflict_reason: reason },
  }, 'cid-user-1');
}

describe('administrator account screens', () => {
  it('lists a user by opaque identity and declares a current-page role filter', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.list({ includeArchived: false, limit: 50 }), {
      items: [ACCOUNT], page: { next_cursor: null },
    });
    const markup = renderScreen(client, createElement(UserList));
    expect(markup).toContain(`/admin/users/${ACCOUNT.user_uid}`);
    expect(markup).toContain('Роль на текущей странице');
    expect(markup).toContain('Администратор');
  });

  it('shows names, roles, reset and archive controls but never purge for an active account', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.detail(ACCOUNT.user_uid), ACCOUNT);
    const markup = renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid }));
    expect(markup).toContain('Адрес входа:');
    expect(markup).toContain('Сохранить роли');
    expect(markup).toContain('Архивировать учётную запись');
    expect(markup).toContain('type="password"');
    expect(markup).not.toContain('Удалить навсегда');
  });

  it('offers irreversible purge confirmation only for an archived account', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.detail(ACCOUNT.user_uid), { ...ACCOUNT, archived_at: '2026-10-08T00:00:00Z' });
    const markup = renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid }));
    expect(markup).toContain('Восстановить учётную запись');
    expect(markup).toContain('Удалить навсегда');
    expect(markup).not.toContain('Сбросить пароль');
  });

  it('shows «Последний вход» as a column of the list and says so when there was none (`UI-A-92`)', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.list({ includeArchived: false, limit: 50 }), {
      items: [ACCOUNT, { ...ACCOUNT, user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', login: 'new@example.org', last_sign_in_at: null }],
      page: { next_cursor: null },
    });
    const markup = renderScreen(client, createElement(UserList));
    expect(markup).toContain('Последний вход</th>');
    expect(markup).toContain('2026-11-05 09:30:15 UTC');
    expect(markup).toContain('data-user-last-sign-in="at"');
    expect(markup).toContain('data-user-last-sign-in="never"');
    expect(markup).toContain('Входов не было');
  });

  it('shows «Последний вход» on the card (`UI-A-92`)', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.detail(ACCOUNT.user_uid), ACCOUNT);
    expect(renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid }))).toContain('Последний вход: 2026-11-05 09:30:15 UTC.');
    client.setQueryData(queryKeys.users.detail(ACCOUNT.user_uid), { ...ACCOUNT, last_sign_in_at: null });
    expect(renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid }))).toContain('Последний вход: Входов не было.');
  });

  it('offers «Завершить сеансы» for another active account, behind a confirmation, and never for oneself or an archived one (`UI-A-93`)', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.detail(ACCOUNT.user_uid), ACCOUNT);
    const other = renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid }));
    expect(other).toContain('Завершить сеансы');
    // nothing is sent, and the confirmation is not drawn, until the button is pressed
    expect(other).not.toContain('Подтвердить завершение сеансов');
    const own = renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid, signedInLogin: ACCOUNT.login }));
    expect(own).not.toContain('Завершить сеансы');
    client.setQueryData(queryKeys.users.detail(ACCOUNT.user_uid), { ...ACCOUNT, archived_at: '2026-10-08T00:00:00Z' });
    expect(renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid }))).not.toContain('Завершить сеансы');
  });

  it('keeps 60-character names from widening the list', () => {
    const css = readFileSync(join(WEB_ROOT, 'src/widgets/user-list/ui/user-list.module.css'), 'utf8');
    expect(css).toContain('table-layout: fixed');
    expect(css).toContain('overflow-wrap: anywhere');
  });
});

describe('account actions', () => {
  it('requires matching password entries before a reset command can be made', () => {
    expect(confirmedTemporaryPassword('new-password', 'different')).toBeNull();
    expect(confirmedTemporaryPassword('', '')).toBeNull();
    expect(confirmedTemporaryPassword('new-password', 'new-password')).toBe('new-password');
  });

  it.each([
    ['conflict', 'last_admin', 'last_admin'],
    ['conflict', 'account_referenced', 'account_referenced'],
    ['conflict', 'login_taken', 'login_taken'],
    ['permission_denied', '', 'permission_denied'],
    ['state_transition_not_allowed', '', 'state_transition_not_allowed'],
  ] as const)('maps %s/%s to a typed refusal', (code, reason, kind) => {
    expect(userFailure(refusal(code, reason)).kind).toBe(kind);
  });

  it('refreshes the users namespace and the changed account view', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), ACCOUNT);
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    const updated = { ...ACCOUNT, first_name: 'Мария' };
    refreshManagedUser(client, updated);
    expect(client.getQueryData(queryKeys.users.detail(ACCOUNT.user_uid))).toEqual(updated);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.users.all() });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.account.me() });
  });
});
