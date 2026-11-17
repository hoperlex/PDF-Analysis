/**
 * The expert in the address of «Назначения» (`UIP-S14-03`): `?expert=<номер учётной записи>` opens the form «Назначить
 * работу» with that expert chosen. The value is read when it is an account identifier and applied only when that account is
 * among the active experts the screen has loaded; until then no choice is made and «Назначить» stays off. Any other value is
 * dropped and drawn nowhere. An expert, who has no form, has the parameter ignored.
 */

import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';

import { DispatcherPage } from '@/_pages/dispatcher';
import type { Account, Role } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { routes } from '@/shared/lib';
import { EXPERT_PARAM, parseExpertAddress, resolveExpertChoice } from '@/entities/assignment';
import { USER_PAGE_LIMIT } from '@/entities/user';

import { newClient, renderScreen } from '../screens/harness';

const ADMIN = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8A';
const EXPERT_A = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const EXPERT_B = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
const NOBODY = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z';
const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

function account(uid: string, label: string, roles: Role[], over: Partial<Account> = {}): Account {
  return {
    user_uid: uid, login: `${label}@example.test`, display_label: label, last_name: label, first_name: 'Имя', middle_name: null,
    roles, profile_complete: true, is_default_credential: false, archived_at: null, last_sign_in_at: null, ...over,
  };
}

/** The active experts the screen reads through `listUsers`; an archived expert and an administrator are not among its choices. */
const USERS = [
  account(EXPERT_A, 'Иванова А. А.', ['expert']),
  account(EXPERT_B, 'Петров Б. Б.', ['expert']),
  account(NOBODY, 'Архипов В. В.', ['expert'], { archived_at: '2026-10-01T00:00:00Z' }),
  account(ADMIN, 'Админов Г. Г.', ['admin']),
];

type Users = 'loaded' | 'pending';

function atAddress(query: string, element: ReactElement): ReactElement {
  return createElement(
    PathnameContext.Provider,
    { value: '/dispatcher' },
    createElement(SearchParamsContext.Provider, { value: new URLSearchParams(query) }, element),
  );
}

function screen(roles: Role[], query: string, users: Users = 'loaded'): string {
  const client = newClient();
  client.setQueryData(queryKeys.account.me(), account(ADMIN, 'Админов Г. Г.', roles));
  if (users === 'loaded') {
    client.setQueryData(queryKeys.users.list({ includeArchived: false, limit: USER_PAGE_LIMIT }), { items: USERS, page: { next_cursor: null } });
  }
  return renderScreen(client, atAddress(query, createElement(DispatcherPage, { roles })));
}

/** The form's expert select, with its options. */
const expertSelect = (html: string): string => /Эксперт\s*<select[\s\S]*?<\/select>/.exec(html)?.[0] ?? '';
const chosenOption = (html: string): string | null => /<option value="(usr_[^"]*)" selected="">/.exec(expertSelect(html))?.[1] ?? null;
const submit = (html: string): string => /<button[^>]*data-create-assignment-submit[^>]*>/.exec(html)?.[0] ?? '';

describe('the expert the address names', () => {
  it('is read only when it is an account identifier', () => {
    expect(parseExpertAddress(EXPERT_A)).toBe(EXPERT_A);
    expect(parseExpertAddress('')).toBeNull();
    expect(parseExpertAddress('Иванова А. А.')).toBeNull();
    expect(parseExpertAddress('usr_short')).toBeNull();
    expect(parseExpertAddress(`${EXPERT_A} `)).toBeNull();
    expect(parseExpertAddress('prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B')).toBeNull();
    expect(parseExpertAddress(undefined)).toBeNull();
    expect(parseExpertAddress(null)).toBeNull();
  });

  it('is applied only when the loaded experts include them, and never before they are loaded', () => {
    const experts = [{ userUid: EXPERT_A }, { userUid: EXPERT_B }];
    expect(resolveExpertChoice(experts, EXPERT_B)).toBe(EXPERT_B);
    expect(resolveExpertChoice(experts, NOBODY)).toBeNull();
    expect(resolveExpertChoice(experts, null)).toBeNull();
    expect(resolveExpertChoice([], EXPERT_B)).toBeNull();
  });
});

describe('routes.dispatcher', () => {
  it('builds the address of «Назначения», with the expert when one is named', () => {
    expect(routes.dispatcher()).toBe('/dispatcher');
    expect(routes.dispatcher(EXPERT_B)).toBe(`/dispatcher?expert=${EXPERT_B}`);
    expect(routes.dispatcher(EXPERT_B)).toBe(`/dispatcher?${EXPERT_PARAM}=${EXPERT_B}`);
  });

  it('encodes the value rather than trusting it', () => {
    expect(routes.dispatcher('a b&c')).toBe('/dispatcher?expert=a%20b%26c');
  });
});

describe('the form «Назначить работу» with the expert of the address', () => {
  it('opens with that expert chosen, among the choices, and leaves the others open to the administrator', () => {
    const html = screen(['admin'], `expert=${EXPERT_B}`);
    expect(chosenOption(html)).toBe(EXPERT_B);
    const select = expertSelect(html);
    expect(select).toContain(`<option value="${EXPERT_A}">`);
    expect(select).toContain('>Выберите эксперта</option>');
    // an archived expert and an administrator are not choices
    expect(select).not.toContain(NOBODY);
    expect(select).not.toContain(ADMIN);
  });

  it('chooses nobody without the parameter', () => {
    const html = screen(['admin'], '');
    expect(chosenOption(html)).toBeNull();
    expect(html).toContain('data-create-assignment-hint=""');
  });

  it('chooses nobody and keeps «Назначить» off while the list of experts is not loaded', () => {
    const html = screen(['admin'], `expert=${EXPERT_B}&project=${PROJECT}`, 'pending');
    expect(chosenOption(html)).toBeNull();
    expect(submit(html)).toContain('disabled=""');
    expect(html).toContain('Выберите эксперта, чтобы назначить работу.');
  });

  it('switches «Назначить» on once the expert is chosen and the object is, and not before the object is', () => {
    const ready = screen(['admin'], `expert=${EXPERT_B}&project=${PROJECT}`);
    expect(chosenOption(ready)).toBe(EXPERT_B);
    expect(submit(ready)).not.toContain('disabled');
    expect(ready).not.toContain('data-create-assignment-hint');
    const noObject = screen(['admin'], `expert=${EXPERT_B}&project=all`);
    expect(chosenOption(noObject)).toBe(EXPERT_B);
    expect(submit(noObject)).toContain('disabled=""');
    expect(noObject).toContain('Выберите объект, чтобы назначить работу.');
  });

  it('drops a value that is not an account identifier, and draws it nowhere, the link to every object included', () => {
    const junk = 'Иванов<b>x</b>';
    const html = screen(['admin'], `expert=${encodeURIComponent(junk)}&project=${PROJECT}`);
    expect(chosenOption(html)).toBeNull();
    expect(html).not.toContain('Иванов&lt;b');
    expect(html).not.toContain('Иванов<b>');
    expect(html).not.toContain(encodeURIComponent(junk));
    const link = /<a [^>]*href="([^"]*)"[^>]*>Все объекты<\/a>/.exec(html)?.[1] ?? '';
    expect(link).toBe('/dispatcher?project=all');
  });

  it('chooses nobody for an account that is not among the active experts: an archived one, or an administrator', () => {
    for (const uid of [NOBODY, ADMIN]) {
      const html = screen(['admin'], `expert=${uid}&project=${PROJECT}`);
      expect(chosenOption(html)).toBeNull();
      expect(submit(html)).toContain('disabled=""');
    }
  });

  it('keeps a well-formed expert in the link back to every object', () => {
    const link = /<a [^>]*href="([^"]*)"[^>]*>Все объекты<\/a>/.exec(screen(['admin'], `expert=${EXPERT_B}&project=${PROJECT}`))?.[1] ?? '';
    expect(link).toBe(`/dispatcher?expert=${EXPERT_B}&amp;project=all`);
  });

  it('draws no form for an expert, and the parameter is ignored: it is drawn nowhere and the link does not carry it', () => {
    const html = screen(['expert'], `expert=${EXPERT_B}&project=${PROJECT}`);
    expect(html).not.toContain('data-create-assignment=""');
    expect(html).not.toContain(EXPERT_B);
    expect(html).toContain('Мои назначения');
  });
});
