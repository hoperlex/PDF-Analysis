import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import type { Account, ErrorEnvelope } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { confirmedTemporaryPassword, refreshManagedUser, roleChangeConfirmation, userCommandDone } from '@/features/manage-user';
import { AdminUsersPage, readSelectedUser, writeSelectedUser } from '@/_pages/admin-users';
import { AdminAreaTabsView, userFailure } from '@/entities/user';
import { UserCard } from '@/widgets/user-card';
import { UserList, filterUsers } from '@/widgets/user-list';

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
    contract_version: '1.43.0',
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
    expect(markup).toContain('Адрес входа</dt>');
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
    expect(renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid }))).toContain('data-user-last-sign-in="at">2026-11-05 09:30:15 UTC</dd>');
    client.setQueryData(queryKeys.users.detail(ACCOUNT.user_uid), { ...ACCOUNT, last_sign_in_at: null });
    expect(renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid }))).toContain('data-user-last-sign-in="never">Входов не было</dd>');
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

describe('the account list beside its card (`UI-A-92`, `UI-A-93`)', () => {
  const OTHER: Account = { ...ACCOUNT, user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', login: 'ivanov@example.org', display_label: 'Иванов И. И.', first_name: 'Иван', last_name: 'Иванов', middle_name: 'Иванович', roles: ['expert'], archived_at: '2026-10-08T00:00:00Z' };

  it('narrows a page by standing, role and the words of a name, in any case and order', () => {
    const items = [ACCOUNT, OTHER];
    const all = { scope: 'all', role: '', text: '' } as const;
    expect(filterUsers(items, all)).toEqual(items);
    expect(filterUsers(items, { ...all, scope: 'archived' })).toEqual([OTHER]);
    expect(filterUsers(items, { ...all, scope: 'active' })).toEqual(items);
    expect(filterUsers(items, { ...all, role: 'admin' })).toEqual([ACCOUNT]);
    expect(filterUsers(items, { ...all, text: 'ИВАН иванов' })).toEqual([OTHER]);
    expect(filterUsers(items, { ...all, text: 'petrova@' })).toEqual([ACCOUNT]);
    expect(filterUsers(items, { ...all, text: 'никого такого' })).toEqual([]);
  });

  it('reads the open account from the address only when it is shaped like an account identity', () => {
    expect(readSelectedUser(new URLSearchParams(`user=${ACCOUNT.user_uid}`))).toBe(ACCOUNT.user_uid);
    expect(readSelectedUser(new URLSearchParams('user=../../etc'))).toBeNull();
    expect(readSelectedUser(new URLSearchParams(''))).toBeNull();
    expect(writeSelectedUser(new URLSearchParams('a=1'), ACCOUNT.user_uid).toString()).toBe(`a=1&user=${ACCOUNT.user_uid}`);
    expect(writeSelectedUser(new URLSearchParams(`a=1&user=${ACCOUNT.user_uid}`), null).toString()).toBe('a=1');
  });

  it('draws the page with the list on the left and a placeholder, or the open account\'s card, on the right', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.list({ includeArchived: false, limit: 50 }), { items: [ACCOUNT], page: { next_cursor: null } });
    const closed = renderScreen(client, createElement(AdminUsersPage));
    expect(closed).toContain('data-user-split="closed"');
    expect(closed).toContain('data-user-detail-empty=""');
    expect(closed).toContain('data-admin-area="registrations"');
    expect(closed).toContain('aria-current="page"');
    client.setQueryData(queryKeys.users.detail(ACCOUNT.user_uid), ACCOUNT);
    client.setQueryData(queryKeys.account.me(), { ...ACCOUNT, user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', login: 'admin@example.org' });
    const open = renderScreen(client, createElement(AdminUsersPage, { initialUserUid: ACCOUNT.user_uid }));
    expect(open).toContain('data-user-split="open"');
    expect(open).toContain('Открыть отдельным экраном');
    expect(open).toContain('Закрыть');
    expect(open).not.toContain('К списку пользователей');
    expect(open).toContain('data-selected="true"');
  });

  it('shows the strip of the administration area, with the waiting count only when it is known and above zero', () => {
    const open = renderScreen(newClient(), createElement(AdminAreaTabsView, { active: 'users', pendingTotal: 3 }));
    expect(open).toContain('href="/admin/registrations"');
    expect(open).toContain('href="/admin/users"');
    expect(open).toContain('href="/admin/auth-events"');
    expect(open).toContain('data-admin-pending="3"');
    expect(open.match(/aria-current="page"/g)).toHaveLength(1);
    expect(renderScreen(newClient(), createElement(AdminAreaTabsView, { active: 'events', pendingTotal: 0 }))).not.toContain('data-admin-pending');
    expect(renderScreen(newClient(), createElement(AdminAreaTabsView, { active: 'events', pendingTotal: null }))).not.toContain('data-admin-pending');
  });

  it('asks before an account is made an administrator and before an administrator gives up their own role', () => {
    expect(roleChangeConfirmation(['expert'], ['expert', 'admin'], false)).toBe('grant-admin');
    expect(roleChangeConfirmation(['admin'], ['admin', 'expert'], false)).toBeNull();
    expect(roleChangeConfirmation(['admin', 'expert'], ['expert'], true)).toBe('drop-own-admin');
    expect(roleChangeConfirmation(['admin', 'expert'], ['expert'], false)).toBeNull();
    expect(roleChangeConfirmation(['expert'], ['expert'], true)).toBeNull();
  });

  it('answers every command that stays on the screen in the words of what it did', () => {
    for (const kind of ['names', 'roles', 'archive', 'end-sessions', 'restore', 'reset-password', 'purge'] as const) {
      expect(userCommandDone(kind).length).toBeGreaterThan(10);
    }
    expect(userCommandDone('roles')).toContain('Прежние пропуска отозваны');
    expect(userCommandDone('end-sessions')).toContain('Сеансы завершены');
  });

  it('flags in the list an account that still has a temporary password or an unfilled profile', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.list({ includeArchived: false, limit: 50 }), {
      items: [ACCOUNT, { ...ACCOUNT, user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8E', is_default_credential: true, profile_complete: false }], page: { next_cursor: null },
    });
    const markup = renderScreen(client, createElement(UserList));
    expect(markup.match(/data-user-default-credential=""/g)).toHaveLength(1);
    expect(markup.match(/data-user-profile-incomplete=""/g)).toHaveLength(1);
  });

  it('says that the account is still on its temporary password, and that the profile is not filled', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.detail(ACCOUNT.user_uid), { ...ACCOUNT, is_default_credential: true, profile_complete: false });
    const markup = renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid }));
    expect(markup).toContain('data-user-default-credential=""');
    expect(markup).toContain('data-user-profile-incomplete=""');
    client.setQueryData(queryKeys.users.detail(ACCOUNT.user_uid), ACCOUNT);
    const plain = renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid }));
    expect(plain).not.toContain('data-user-default-credential');
    expect(plain).not.toContain('(это вы)');
    expect(renderScreen(client, createElement(UserCard, { userUid: ACCOUNT.user_uid, signedInLogin: ACCOUNT.login }))).toContain('(это вы)');
  });
});
