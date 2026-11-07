/**
 * «Журнал входов» (contract 1.36.0, `UI-A-94`): the registry entry, the wording of each kind of line, and what the
 * list draws from a seeded page.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { AdminAuthEventsPage } from '@/_pages/admin-auth-events';
import type { AuthEvent, AuthEventPage, ErrorEnvelope } from '@/shared/api';
import { ApiError, AUTH_EVENT_TYPE_VALUES, queryKeys } from '@/shared/api';
import { SCREEN_REGISTRY } from '@/shared/config/screen-registry';
import { AUTH_EVENT_LABELS, AUTH_EVENT_PAGE_LIMIT, authEventDetails, authEventFailure } from '@/entities/auth-event';
import { AuthEventRows } from '@/widgets/auth-event-list';

import { newClient, renderScreen } from '../screens/harness';

const ADMIN = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8A';
const OTHER = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

function event(type: AuthEvent['event_type'], over: Partial<AuthEvent> = {}): AuthEvent {
  return {
    event_id: `evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8${type.length}`,
    event_type: type,
    occurred_at: '2026-11-05T09:30:15Z',
    subject_user_uid: OTHER,
    subject_label: 'Экспертова Д. Д.',
    actor_user_uid: null,
    actor_label: null,
    source: 'api',
    role: null,
    failures: null,
    default_credential: null,
    ...over,
  };
}

describe('the screen', () => {
  it('is an administrator-only item of the administration menu, after «Заявки на регистрацию»', () => {
    const admin = SCREEN_REGISTRY.filter((row) => row.group === 'admin' && row.inMenu);
    expect(admin.map((row) => row.address)).toEqual(['/admin/users', '/admin/registrations', '/admin/auth-events']);
    const row = SCREEN_REGISTRY.find((entry) => entry.address === '/admin/auth-events');
    expect(row).toMatchObject({ label: 'Журнал входов', access: 'session', roles: ['admin'], projectScope: 'global' });
  });

  it('is a project-independent title and a panel around the journal', () => {
    const markup = renderScreen(newClient(), createElement(AdminAuthEventsPage));
    expect(markup).toContain('Журнал входов');
  });
});

describe('the wording', () => {
  it('has a sentence for every kind the contract declares, and no other', () => {
    expect(Object.keys(AUTH_EVENT_LABELS).sort()).toEqual([...AUTH_EVENT_TYPE_VALUES].sort());
  });

  it('builds the facts a line carries from the closed fields and nothing else', () => {
    expect(authEventDetails(event('sign_in_succeeded'))).toEqual([]);
    expect(authEventDetails(event('sign_in_succeeded', { default_credential: true }))).toEqual(['С исходным или временным паролем']);
    expect(authEventDetails(event('sign_in_succeeded', { default_credential: false }))).toEqual([]);
    expect(authEventDetails(event('sign_in_blocked', { failures: 5 }))).toEqual(['Неудачных попыток подряд: 5']);
    expect(authEventDetails(event('role_granted', { role: 'admin', source: 'host_cli' }))).toEqual(['Роль: Администратор', 'Выполнено на сервере']);
    // a role this build does not know is printed as the code the server sent, never dropped
    expect(authEventDetails({ ...event('role_revoked'), role: 'auditor' as never })).toEqual(['Роль: auditor']);
  });

  it('says who is refused to read the journal', () => {
    const envelope: ErrorEnvelope = {
      contract_version: '1.38.0', error_code: 'permission_denied', message: 'Refused', correlation_id: 'cid-ae-1', retryable: false,
    };
    const failure = authEventFailure(new ApiError(403, envelope, 'cid-ae-1'));
    expect(failure.kind).toBe('permission_denied');
    expect(failure.detail).toBe('Журнал входов доступен только администратору.');
    expect(failure.correlationId).toBe('cid-ae-1');
  });
});

describe('the list', () => {
  const page: AuthEventPage = {
    items: [
      event('sessions_ended', { actor_user_uid: ADMIN, actor_label: 'Админова О. С.' }),
      event('sign_in_succeeded', { default_credential: true }),
      event('password_reset', { subject_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', subject_label: null, actor_user_uid: ADMIN, actor_label: 'Админова О. С.' }),
    ],
    page: { next_cursor: 'cursor-next-1' },
  };

  it('draws each line with its time, its kind, the account and the administrator who acted', () => {
    const markup = renderScreen(newClient(), createElement(AuthEventRows, { items: page.items }));
    expect(markup).toContain('data-auth-event="sessions_ended"');
    expect(markup).toContain('2026-11-05 09:30:15 UTC');
    expect(markup).toContain('Сеансы завершены администратором');
    expect(markup).toContain('Вход');
    expect(markup).toContain(`/admin/users/${OTHER}`);
    expect(markup).toContain('Админова О. С.');
    expect(markup).toContain('С исходным или временным паролем');
    // an account that is gone keeps its line, without a link
    expect(markup).toContain('Учётная запись удалена');
    expect(markup).not.toContain('/admin/users/usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C');
    // no actor: a dash, not a made-up name
    expect(markup).toContain('—');
  });

  it('reads the first page under the journal key and offers the server\'s next one', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.authEvents({ limit: AUTH_EVENT_PAGE_LIMIT }), page);
    const markup = renderScreen(client, createElement(AdminAuthEventsPage));
    expect(markup).toContain('data-auth-event="sign_in_succeeded"');
    expect(markup).toContain('Дальше');
    expect(markup).not.toContain('В начало');
  });

  it('says so when the journal is empty, and has no pager', () => {
    const client = newClient();
    client.setQueryData(queryKeys.users.authEvents({ limit: AUTH_EVENT_PAGE_LIMIT }), { items: [], page: { next_cursor: null } });
    const markup = renderScreen(client, createElement(AdminAuthEventsPage));
    expect(markup).toContain('В журнале пока нет событий.');
    expect(markup).not.toContain('Дальше');
  });

  it('is invalidated with the accounts, so ending sessions refreshes it', () => {
    expect(queryKeys.users.authEvents({ limit: 50 }).slice(0, 1)).toEqual(queryKeys.users.all());
  });
});
