'use client';

/**
 * The tabs of the administration area (`UI-A-90`, `UI-A-91`): «Заявки (N)» · «Пользователи» · «Журнал входов».
 *
 * The original keeps the three on one page and switches between them without leaving it; here each is a screen with its own
 * address, so a tab is a link and the open one says `aria-current="page"`. The waiting-request count is the frame menu's own
 * read (`listRegistrations`, `{ status: 'pending', limit: 1 }`, one cache entry), so the strip asks the server nothing the
 * frame does not already ask. A count that is still loading or failed is no count, never a zero.
 */

import Link from 'next/link';

import { useRegistrationRequests } from '@/entities/registration-request';

import type { AdminArea } from '../model/admin-areas';
import { ADMIN_AREAS, ADMIN_AREA_LABELS, adminAreaHref } from '../model/admin-areas';
import styles from './admin-area-tabs.module.css';

const PENDING_PROBE = { status: 'pending', limit: 1 } as const;

export interface AdminAreaTabsViewProps {
  readonly active: AdminArea;
  /** Requests waiting for a decision, or `null` while not known. */
  readonly pendingTotal: number | null;
}

/** The strip from a count already in hand. Rendered by the static harness. */
export function AdminAreaTabsView({ active, pendingTotal }: AdminAreaTabsViewProps) {
  return (
    <nav className={styles.tabs} aria-label="Разделы администрирования" data-admin-areas="">
      {ADMIN_AREAS.map((area) => (
        <Link
          key={area}
          href={adminAreaHref(area)}
          className={styles.tab}
          aria-current={area === active ? 'page' : undefined}
          data-admin-area={area}
        >
          {ADMIN_AREA_LABELS[area]}
          {area === 'registrations' && pendingTotal !== null && pendingTotal > 0 ? (
            <span className="am-badge am-badge--degraded" data-admin-pending={pendingTotal}>{pendingTotal}</span>
          ) : null}
        </Link>
      ))}
    </nav>
  );
}

export function AdminAreaTabs({ active }: { readonly active: AdminArea }) {
  const pending = useRegistrationRequests(PENDING_PROBE);
  return <AdminAreaTabsView active={active} pendingTotal={pending.isSuccess ? pending.data.pending_total : null} />;
}
