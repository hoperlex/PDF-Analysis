'use client';

/**
 * The navigation in the bar — `W50-PLAN.md` §3.5.
 *
 * `Главная` is a link; each group the session may open (`buildNavigation`) is a `Disclosure`
 * — the APG disclosure pattern from `@/shared/ui`, because its items are links and not menu
 * items. The group holding the page being shown carries `aria-current="true"`, and the item
 * that is that page `aria-current="page"`.
 *
 * ## Two states, one at a time
 *
 * Wide, the groups sit in the bar in one row. Below the frame's breakpoint they collapse into
 * one stacked list behind a «Меню» disclosure, in which each group is an inline disclosure.
 * Both are in the markup and the frame's CSS module shows exactly one
 * (`app-frame.module.css`), so neither depends on script to exist and an instrument that
 * renders the frame once sees both. A hidden state is `display: none`, which also takes it
 * out of the accessibility tree and the tab order.
 *
 * ## The current page
 *
 * Read here, from `usePathname`, and matched against the registry's address shapes
 * (`currentScreen`): the frame is a server component that is handed a session and never a
 * request, and the pathname changes on every client-side navigation without the frame
 * rendering again. {@link FrameNavigationView} is the pure half, so the marking is tested with
 * any pathname without a router.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ComponentType } from 'react';

import type { DisclosureProps } from '@/shared/ui';
import { Disclosure } from '@/shared/ui';

import type { CurrentScreen, Navigation, NavigationGroup, NavigationItem } from './navigation';
import { currentScreen } from './navigation';
import styles from './app-frame.module.css';

export interface FrameNavigationProps {
  readonly navigation: Navigation;
}

export interface FrameNavigationViewProps extends FrameNavigationProps {
  /** The browser's pathname; `null` when it is not known, and then nothing is marked. */
  readonly pathname: string | null;
  /**
   * What draws «Меню» and each group. In the bar it is the `Disclosure` island, which holds its
   * own open state. An instrument that renders one static pass cannot click, so it passes a
   * view drawn open instead — the contrast census does — and measures the same tree.
   */
  readonly disclosure?: ComponentType<DisclosureProps> | undefined;
}

function links(group: NavigationGroup, current: CurrentScreen | null) {
  return group.items.map((item) => ({
    href: item.address,
    label: item.label,
    current: current?.address === item.address,
  }));
}

function HomeLink({ home, current }: { readonly home: NavigationItem; readonly current: CurrentScreen | null }) {
  return (
    <Link
      className={`am-app__nav ${styles.home}`}
      href={home.address}
      aria-current={current?.address === home.address ? 'page' : undefined}
    >
      {home.label}
    </Link>
  );
}

export function FrameNavigationView({ navigation, pathname, disclosure = Disclosure }: FrameNavigationViewProps) {
  const Group = disclosure;
  const { home, groups } = navigation;
  if (home === null && groups.length === 0) return null;
  const current = currentScreen(pathname);
  const inGroup = (group: NavigationGroup): boolean => current?.group === group.group;
  return (
    <nav className={styles.nav} aria-label="Разделы">
      <div className={styles.row} data-nav-state="row">
        {home !== null ? <HomeLink home={home} current={current} /> : null}
        {groups.map((group) => (
          <Group key={group.group} label={group.label} current={inGroup(group)} links={links(group, current)} />
        ))}
      </div>
      <div className={styles.stacked} data-nav-state="stacked">
        <Group label="Меню" current={current !== null && (current.address === home?.address || groups.some(inGroup))}>
          <ul className={styles.stackedList}>
            {home !== null ? (
              <li className={styles.stackedItem}>
                <HomeLink home={home} current={current} />
              </li>
            ) : null}
            {groups.map((group) => (
              <li className={styles.stackedItem} key={group.group}>
                <Group label={group.label} layout="inline" current={inGroup(group)} links={links(group, current)} />
              </li>
            ))}
          </ul>
        </Group>
      </div>
    </nav>
  );
}

export function FrameNavigation({ navigation }: FrameNavigationProps) {
  return <FrameNavigationView navigation={navigation} pathname={usePathname()} />;
}
