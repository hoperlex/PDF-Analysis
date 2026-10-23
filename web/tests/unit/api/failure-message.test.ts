/**
 * `C-23` — one Russian reading of a failed request, used by the identity screens.
 *
 * Before it the account page and the user card printed `error.message` — for an `ApiError`
 * that is `"<error_code>: <the API's English message>"` — and two of four mappers reported a
 * value that was not a request failure at all as a transport failure. These cases hold the
 * mapper and the screens that now use it to: Russian by `error_code`, the screen's own
 * sentence where it has one, an unexpected error for anything else, and never a thrown message.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { AccountPage } from '@/_pages/account';
import { MalformedAccountError, UnknownRoleError, unreadableAccountDetail } from '@/entities/account';
import { registrationFailure } from '@/entities/registration-request';
import { userFailure } from '@/entities/user';
import type { Account, ErrorEnvelope } from '@/shared/api';
import {
  AUTHENTICATION_REQUIRED_DETAIL,
  ApiError,
  TransportError,
  UnrecognizedApiError,
  catalogMessage,
  queryKeys,
} from '@/shared/api';
import { TRANSPORT_FAILURE_DETAIL, UNEXPECTED_FAILURE_DETAIL, failureMessage } from '@/shared/api/failure-message';
import { UserCard } from '@/widgets/user-card';

import { newClient, renderScreen, seedError } from '../screens/harness';

const ENGLISH = 'The upstream said something in English';

function apiError(code: ErrorEnvelope['error_code'], details: Record<string, string> = {}): ApiError {
  return new ApiError(409, {
    contract_version: '1.3.0',
    error_code: code,
    message: ENGLISH,
    correlation_id: 'cid-c23',
    retryable: false,
    details,
  }, 'cid-c23');
}

const USER_UID = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

describe('failureMessage', () => {
  it('words an ApiError by its code, in Russian, never with its own message', () => {
    const failure = failureMessage(apiError('not_found'));
    expect(failure).toMatchObject({ kind: 'not_found', errorCode: 'not_found', correlationId: 'cid-c23' });
    expect(failure.detail).toBe(catalogMessage('not_found'));
    expect(failure.detail).not.toContain(ENGLISH);
    expect(failure.detail).not.toContain('not_found');
    expect(failureMessage(apiError('authentication_required')).detail).toBe(AUTHENTICATION_REQUIRED_DETAIL);
  });

  it('lets a screen say more for a code it knows, and only for that code', () => {
    const wording = { validation_failed: 'Проверьте поля.' };
    expect(failureMessage(apiError('validation_failed'), wording).detail).toBe('Проверьте поля.');
    expect(failureMessage(apiError('conflict'), wording).detail).toBe(catalogMessage('conflict'));
  });

  it('reports a value that is not a request failure as unexpected, not as transport, and prints nothing of it', () => {
    for (const thrown of [new Error(ENGLISH), new TypeError(ENGLISH), ENGLISH, null]) {
      const failure = failureMessage(thrown);
      expect(failure.kind).toBe('unexpected');
      expect(failure.detail).toBe(UNEXPECTED_FAILURE_DETAIL);
      expect(failure.detail).toMatch(/^Непредвиденная ошибка/);
      expect(failure.correlationId).toBeNull();
    }
  });

  it('keeps a transport failure a transport failure, and names an unknown code as unknown', () => {
    const transport = failureMessage(new TransportError('Запрос getMe вернул HTTP 502 с нечитаемым JSON в теле.'));
    expect(transport).toMatchObject({ kind: 'transport', detail: TRANSPORT_FAILURE_DETAIL });
    expect(transport.detail).not.toContain('getMe');
    const unknown = failureMessage(new UnrecognizedApiError(503, 'later_code', ENGLISH, 'cid-u'));
    expect(unknown).toMatchObject({ kind: 'unrecognized', correlationId: 'cid-u' });
    expect(unknown.detail).toContain('«later_code»');
    expect(unknown.detail).not.toContain(ENGLISH);
  });
});

describe('the entity mappers agree with it', () => {
  it('a thrown non-request value is unexpected for users and registrations alike', () => {
    expect(userFailure(new Error(ENGLISH))).toEqual({ kind: 'unexpected', detail: UNEXPECTED_FAILURE_DETAIL, correlationId: null });
    expect(registrationFailure(new Error(ENGLISH))).toEqual({ kind: 'unexpected', detail: UNEXPECTED_FAILURE_DETAIL, correlationId: null });
  });

  it('they keep their own sentences: conflict reasons, and the two refusals they word', () => {
    expect(userFailure(apiError('conflict', { conflict_reason: 'last_admin' })).kind).toBe('last_admin');
    expect(userFailure(apiError('permission_denied')).detail).toContain('не может архивировать себя');
    expect(registrationFailure(apiError('state_transition_not_allowed')).detail).toContain('уже принято');
    // An unknown conflict reason is the plain conflict, worded by the catalog.
    expect(userFailure(apiError('conflict', { conflict_reason: 'later' }))).toMatchObject({
      kind: 'conflict', detail: catalogMessage('conflict'),
    });
  });

  it('an unreadable account is said in a fixed sentence, never the thrown one', () => {
    expect(unreadableAccountDetail(new UnknownRoleError('auditor'))).toContain('роль');
    expect(unreadableAccountDetail(new MalformedAccountError('отображаемое имя'))).not.toContain('отображаемое имя');
    expect(unreadableAccountDetail(new Error(ENGLISH))).not.toContain(ENGLISH);
  });
});

describe('the account page and the user card render it, not error.message', () => {
  it('the account page', () => {
    for (const [thrown, kind] of [[apiError('dependency_unavailable'), 'dependency_unavailable'], [new Error(ENGLISH), 'unexpected']] as const) {
      const client = newClient();
      seedError(client, queryKeys.account.me(), thrown);
      const markup = renderScreen(client, createElement(AccountPage, { profileComplete: true }));
      expect(markup).toContain('Профиль не загружен');
      expect(markup).toContain(`data-account-failure="${kind}"`);
      expect(markup).not.toContain(ENGLISH);
      expect(markup).not.toContain(`${'dependency_unavailable'}:`);
    }
  });

  it('the account page with an account it cannot show', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), { display_label: '  ', roles: [], login: 'x@example.org' } as unknown as Account);
    const markup = renderScreen(client, createElement(AccountPage, { profileComplete: true }));
    expect(markup).toContain('Данные профиля не распознаны');
    expect(markup).not.toContain('поле отображаемое имя');
  });

  it('the user card', () => {
    const client = newClient();
    seedError(client, queryKeys.users.detail(USER_UID), new Error(ENGLISH));
    const markup = renderScreen(client, createElement(UserCard, { userUid: USER_UID }));
    expect(markup).toContain('data-user-detail-failure="unexpected"');
    expect(markup).not.toContain(ENGLISH);
    expect(markup).not.toContain('Ответ сервера получить не удалось');
  });
});
