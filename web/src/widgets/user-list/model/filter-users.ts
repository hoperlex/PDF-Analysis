import type { Account, Role } from '@/shared/api';

/**
 * Which accounts of the page the list shows: «Действуют», «В архиве» or «Все». The server filters one thing only
 * (`include_archived`), so «В архиве» asks for everything and keeps the archived ones here.
 */
export const USER_SCOPES = ['active', 'archived', 'all'] as const;

export type UserScope = (typeof USER_SCOPES)[number];

export const USER_SCOPE_LABELS: Readonly<Record<UserScope, string>> = {
  active: 'Действуют',
  archived: 'В архиве',
  all: 'Все',
};

/** What the server is asked: archived accounts are read for every scope but the first. */
export function includesArchived(scope: UserScope): boolean {
  return scope !== 'active';
}

/** Whether `account` is archived, by the contract's own field. */
export function isArchived(account: Pick<Account, 'archived_at'>): boolean {
  return account.archived_at !== null;
}

export interface UserFilter {
  readonly scope: UserScope;
  readonly role: Role | '';
  /** What the administrator typed; empty is no filter. */
  readonly text: string;
}

function normal(value: string | null | undefined): string {
  return (value ?? '').toLocaleLowerCase('ru-RU');
}

/**
 * The accounts of one page that pass the filter. Text matches the login and every part of the name, in any case; the
 * words of a query all have to be found, in any order, so «петрова анна» finds «Петрова А. С.» by its names.
 */
export function filterUsers(items: readonly Account[], filter: UserFilter): readonly Account[] {
  const words = normal(filter.text).split(/\s+/).filter((word) => word !== '');
  return items.filter((account) => {
    if (filter.scope === 'archived' && !isArchived(account)) return false;
    if (filter.role !== '' && !account.roles.includes(filter.role)) return false;
    if (words.length === 0) return true;
    const haystack = [account.login, account.display_label, account.last_name, account.first_name, account.middle_name]
      .map(normal)
      .join(' ');
    return words.every((word) => haystack.includes(word));
  });
}
