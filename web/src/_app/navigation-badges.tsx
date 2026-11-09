/**
 * The markup of the counters beside the side menu's items (`menu-badges.ts` says what each number is).
 *
 * `ItemBadges` sits at the right end of a link of the bar and of the stacked «Меню»; `RailBadges` rides the corner of a
 * compact rail's glyph. Both draw the same pill. Neither says anything of its own: the link they sit in carries the
 * accessible name (`itemLabelWithBadges`), and the pill's tooltip repeats what the number counts for a pointer.
 *
 * `BadgedLinks` is the group's list when some of its items carry a badge. The shared `Disclosure` takes links as
 * `{ href, label, icon, current }` and has no place for a counter, so a group with one hands it this list as its
 * content instead, in the very markup `DisclosureView` draws for links. (The `badge` slot `Disclosure` has since learnt is
 * on a group's own button, `D-360`; a link in `links` still has no place for a counter, so this list stays.)
 */

import Link from 'next/link';
import type { ReactNode } from 'react';

import { withProjectParam } from '@/shared/lib';

import type { MenuBadge, MenuBadges } from './menu-badges';
import { badgeText, itemLabelWithBadges } from './menu-badges';
import type { CurrentScreen, NavigationGroup } from './navigation';
import { itemIsCurrent } from './navigation';
import { NavigationGlyph } from './navigation-glyph';
import styles from './app-frame.module.css';

const NO_BADGES: readonly MenuBadge[] = [];

/** One pill: the number, in the tone of the badge, with what it counts as its tooltip. */
export function MenuBadgePill({ badge }: { readonly badge: MenuBadge }) {
  return (
    <span
      className={`${styles.badge} ${badge.tone === 'alert' ? styles.badgeAlert : styles.badgeCount}`}
      title={badge.title ?? badge.label}
      data-menu-badge={badge.tone}
    >
      {badgeText(badge.count)}
    </span>
  );
}

/** The counters at the right end of an inline link; nothing when there are none. */
export function ItemBadges({ badges, children }: { readonly badges: readonly MenuBadge[]; readonly children?: ReactNode }) {
  if (badges.length === 0 && children === undefined) return null;
  return (
    <span className={styles.itemBadges}>
      {badges.map((badge) => <MenuBadgePill key={badge.label} badge={badge} />)}
      {children}
    </span>
  );
}

/** The counters on the corner of a rail link's glyph; nothing when there are none. */
export function RailBadges({ badges }: { readonly badges: readonly MenuBadge[] }) {
  if (badges.length === 0) return null;
  return (
    <span className={styles.railBadges} aria-hidden="true">
      {badges.map((badge) => <MenuBadgePill key={badge.label} badge={badge} />)}
    </span>
  );
}

/** A group's links with their counters, in the markup `DisclosureView` draws for `links`. */
export function BadgedLinks({
  group,
  current,
  projectUid,
  badges,
}: {
  readonly group: NavigationGroup;
  readonly current: CurrentScreen | null;
  readonly projectUid: string | null;
  readonly badges: MenuBadges;
}) {
  return (
    <ul className="am-disclosure__list">
      {group.items.map((item) => {
        const href = withProjectParam(item.address, projectUid);
        const own = badges[item.address] ?? NO_BADGES;
        return (
          <li className="am-disclosure__item" key={href}>
            <Link
              className="am-disclosure__link"
              href={href}
              aria-label={own.length === 0 ? undefined : itemLabelWithBadges(item.label, own)}
              aria-current={itemIsCurrent(item, current) ? 'page' : undefined}
            >
              <span className="am-disclosure__icon" aria-hidden="true"><NavigationGlyph label={item.label} /></span>
              {item.label}
              <ItemBadges badges={own} />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
