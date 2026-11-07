'use client';

/**
 * `/admin/users` — «Пользователи» (`UI-A-92`, `UI-A-93`).
 *
 * The original's account page is a list with a card beside it: a click on a row opens the account's settings on the right,
 * and the list stays where it was. This is that arrangement. The list and the card are two widgets that may not import each
 * other, so the page composes them and owns what joins them — the account open in the card, kept in the address as `?user=`
 * (a link to it, Back and a reload all work). A row is still a link to the account's own screen (`/admin/users/<uid>`): a plain
 * click opens the card here, a modified click (a new tab, a copied address) opens the screen. On a narrow screen the card
 * stands under the list and takes the focus when it opens.
 */

import { useEffect, useRef, useState } from 'react';

import { useAddressState } from '@/shared/lib';
import { LoadingState, PageShell } from '@/shared/ui';
import { useMe } from '@/entities/account';
import { AdminAreaTabs } from '@/entities/user';
import { UserCard } from '@/widgets/user-card';
import { UserList } from '@/widgets/user-list';

import { readSelectedUser, writeSelectedUser } from '../model/selected-user';
import styles from './admin-users-page.module.css';

export interface AdminUsersPageProps {
  /** The open account for a render with no address (the static harness); inside the app the address is the only source. */
  readonly initialUserUid?: string | null | undefined;
}

function OpenAccount({ userUid, onClose }: { readonly userUid: string; readonly onClose: () => void }) {
  // The card needs to know which account is the signed-in one, so it offers no «Завершить сеансы» for it.
  const me = useMe();
  if (me.isPending) return <LoadingState what="учётную запись" />;
  return <UserCard userUid={userUid} signedInLogin={me.isSuccess ? me.data.login : null} variant="panel" onClose={onClose} />;
}

export function AdminUsersPage({ initialUserUid = null }: AdminUsersPageProps) {
  const [selected, setSelected] = useAddressState(readSelectedUser, writeSelectedUser, initialUserUid);
  const panel = useRef<HTMLElement>(null);
  const [focusRequested, setFocusRequested] = useState(false);

  const open = (userUid: string) => {
    setSelected(userUid);
    setFocusRequested(true);
  };
  const close = () => setSelected(null);

  useEffect(() => {
    if (!focusRequested || selected === null) return;
    setFocusRequested(false);
    panel.current?.focus();
    panel.current?.scrollIntoView?.({ block: 'nearest' });
  }, [focusRequested, selected]);

  return (
    <PageShell title="Пользователи" subtitle="Учётные записи и их роли. Выберите запись, чтобы управлять ею." surface="canvas">
      <AdminAreaTabs active="users" />
      <div className={styles.split} data-user-split={selected === null ? 'closed' : 'open'}>
        <div className={styles.panel}>
          <UserList selectedUid={selected} onSelect={open} />
        </div>
        <aside
          ref={panel}
          className={styles.detail}
          id="user-detail"
          aria-label="Учётная запись"
          tabIndex={-1}
          onKeyDown={(event) => {
            // Escape closes the card, but not while a field has the focus: there it is the field's, and a half-typed name is not lost to it.
            const typing = event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement;
            if (event.key === 'Escape' && selected !== null && !typing) close();
          }}
        >
          {selected === null ? (
            <p className="am-note" data-user-detail-empty="">
              Нажмите на пользователя в списке, чтобы изменить его имя и роли, сбросить пароль или завершить его сеансы.
            </p>
          ) : (
            <OpenAccount key={selected} userUid={selected} onClose={close} />
          )}
        </aside>
      </div>
    </PageShell>
  );
}
