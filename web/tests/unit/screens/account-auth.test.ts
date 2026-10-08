import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { AccountPage } from '@/_pages/account';
import type { Account } from '@/shared/api';
import { queryKeys } from '@/shared/api';

import { newClient, renderScreen } from './harness';

const ACCOUNT: Account = {
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

function accountMarkup(account: Account): string {
  const client = newClient();
  client.setQueryData(queryKeys.account.me(), account);
  return renderScreen(client, createElement(AccountPage, { profileComplete: account.profile_complete }));
}

describe('account profile', () => {
  it('shows the generated avatar, names, locked e-mail and read-only roles', () => {
    const markup = accountMarkup(ACCOUNT);
    expect(markup).toContain('data-avatar-pair=');
    expect(markup).toContain('Петрова А. С.');
    expect(markup).toContain('Роли: Эксперт');
    expect(markup).toMatch(/<input[^>]*disabled[^>]*name="email"/);
    expect(markup).toContain('/account/password');
  });

  it('requires e-mail together with names for incomplete legacy profiles', () => {
    const markup = accountMarkup({ ...ACCOUNT, login: 'legacy-admin', profile_complete: false, first_name: null, last_name: null });
    expect(markup).toContain('data-account-profile-complete="false"');
    expect(markup).toMatch(/<input[^>]*required[^>]*name="email"/);
    expect(markup).not.toMatch(/<input[^>]*disabled[^>]*name="email"/);
  });

  it('renders an unknown role as a typed fault', () => {
    const markup = accountMarkup({ ...ACCOUNT, roles: ['future_role' as Account['roles'][number]] });
    expect(markup).toContain('Данные профиля не распознаны');
    expect(markup).not.toContain('name="email"');
  });
});
