/**
 * The account menu at the top right of the bar — `W50-PLAN.md` §3.5.
 *
 * A generated avatar opens it; its header names the account (`displayLabel`), its e-mail —
 * the session subject's `login`, which is the e-mail once the profile is complete and the
 * legacy login before — and its roles; its items are the profile, the password, release
 * history and the way out. The keyboard, focus and outside-click behaviour are `Menu`'s (`@/shared/ui`, the APG
 * menu button), and this module only decides what it holds.
 *
 * A client component: it computes the props and hosts the history panel beside `Menu`.
 * {@link accountMenuProps} is exported so the instruments that render the menu OPEN (the
 * contrast census, the language guard) render exactly what the bar holds, not a copy.
 *
 * ## The roles line
 *
 * The role labels are `entities/account`'s. A role value outside the contract's set throws
 * `UnknownRoleError` there, and here that is a typed fault in place of the line: no role is
 * named, neither the unknown one nor a generic word for it. An empty set says so in the
 * words the home page uses, «Роли не назначены.», because it is a fact about this account and
 * not a claim about the system.
 *
 * ## The way out
 *
 * `Выйти` is a POST to the session's own door (`SESSION_CLOSE_PATH`), exactly as it was in
 * the bar before: the server deletes the row that holds the credential and clears the cookie in
 * one answer. A link that "signed out" would be a GET that changes state.
 */

'use client';

import { useRef, useState } from 'react';
import type { ReactNode } from 'react';

import { SESSION_CLOSE_PATH } from '@/features/sign-in';
import { CHANGE_PASSWORD_SCREEN, PROFILE_SCREEN, screenAt } from '@/shared/config';
import type { MenuProps } from '@/shared/ui';
import { Avatar, Menu } from '@/shared/ui';
import { UnknownRoleError, roleLabels } from '@/entities/account';
import { VersionHistory } from '@/widgets/version-history';

import styles from './app-frame.module.css';

/** What the account menu is told about the open session. */
export interface AccountMenuSession {
  readonly login: string;
  readonly displayLabel: string;
  readonly initials: string;
  readonly roles: readonly string[];
}

/** The account's roles in words, or `null` when the set holds a value this build cannot name. */
function rolesLine(roles: readonly string[]): string | null {
  try {
    const labels = roleLabels(roles);
    return labels.length === 0 ? 'Роли не назначены.' : `Роли: ${labels.join(', ')}.`;
  } catch (error) {
    if (error instanceof UnknownRoleError) return null;
    throw error;
  }
}

/** The fault in place of the roles line. Neither the unknown value nor a guess at it. */
export const UNKNOWN_ROLE_LINE = 'Роли учётной записи не распознаны.';

/** «Профиль»: the registry's own label for the screen. */
function profileLabel(): string {
  const screen = screenAt(PROFILE_SCREEN);
  if (screen === undefined) throw new Error(`account menu: ${PROFILE_SCREEN} is not a registry row`);
  return screen.label;
}

function header(session: AccountMenuSession): ReactNode {
  const roles = rolesLine(session.roles);
  return (
    <div className={styles.account}>
      <p className={styles.accountName} data-account-name="">
        {session.displayLabel}
      </p>
      <p className={styles.accountLogin} data-account-login="">
        {session.login}
      </p>
      {roles === null ? (
        <p className={styles.accountRoles} data-account-fault="closed-vocabulary">
          {UNKNOWN_ROLE_LINE}
        </p>
      ) : (
        <p className={styles.accountRoles} data-account-roles="">
          {roles}
        </p>
      )}
    </div>
  );
}

/**
 * The props of the account menu for `session`. The item addresses are the registry's; the
 * avatar's colour is keyed by the e-mail (`login`), never by the name, so a corrected name
 * keeps its colour.
 */
export function accountMenuProps(session: AccountMenuSession, onHistory?: () => void): MenuProps {
  return {
    label: `Учётная запись: ${session.displayLabel}`,
    trigger: <Avatar initials={session.initials} colourKey={session.login} />,
    header: header(session),
    items: [
      { kind: 'link', label: profileLabel(), href: PROFILE_SCREEN },
      { kind: 'link', label: 'Сменить пароль', href: CHANGE_PASSWORD_SCREEN },
      { kind: 'action', label: 'История версий', onChoose: onHistory },
      { kind: 'submit', label: 'Выйти', action: SESSION_CLOSE_PATH },
    ],
  };
}

export function AccountMenu({ session }: { readonly session: AccountMenuSession }) {
  const [historyOpen, setHistoryOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const closeHistory = () => {
    setHistoryOpen(false);
    root.current?.querySelector<HTMLButtonElement>('button[aria-haspopup="menu"]')?.focus();
  };
  return (
    <div className={styles.accountMenu} data-account-menu="" ref={root}>
      <Menu {...accountMenuProps(session, () => setHistoryOpen(true))} />
      {historyOpen ? <VersionHistory onClose={closeHistory} /> : null}
    </div>
  );
}
