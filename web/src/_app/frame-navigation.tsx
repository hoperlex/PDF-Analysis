'use client';

/**
 * The navigation in the bar — `W50-PLAN.md` §3.5.
 *
 * Each group the session may open (`buildNavigation`) is a `Disclosure`
 * — the APG disclosure pattern from `@/shared/ui`, because its items are links and not menu
 * items. The group holding the page being shown carries `aria-current="true"`, and the item
 * that is that page `aria-current="page"`.
 *
 * ## Three states, one at a time
 *
 * Wide, the groups stay open in the sidebar, and a reader may collapse any of them. The
 * compact desktop rail keeps each destination as a labelled link. Below the frame's
 * breakpoint they collapse into one stacked list behind a «Меню» disclosure.
 * All three are in the markup and the frame's CSS module shows exactly one
 * (`app-frame.module.css`), so none depends on script to exist and an instrument that
 * renders the frame once sees all three. A hidden state is `display: none`, which also takes it
 * out of the accessibility tree and the tab order.
 *
 * ## The project is carried (`R-150c`)
 *
 * The project the address names (`?project=` on an optional or global screen, the path on a
 * required one) rides on every link whose target may take it: `withProjectParam` adds it to an
 * optional or global screen and leaves a required one alone. The address stays the only source
 * of the project; the links are rewritten from it on each render, so the choice outlives a click.
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
import { usePathname, useSearchParams } from 'next/navigation';
import { useId, useState } from 'react';
import type { ComponentType } from 'react';
import { createPortal } from 'react-dom';

import { readProjectContext, withProjectParam } from '@/shared/lib';
import type { DisclosureProps } from '@/shared/ui';
import { Disclosure } from '@/shared/ui';

import type { CurrentScreen, Navigation, NavigationGroup, NavigationItem } from './navigation';
import { currentScreen } from './navigation';
import { NavigationGlyph } from './navigation-glyph';
import styles from './app-frame.module.css';

export interface FrameNavigationProps {
  readonly navigation: Navigation;
}

export interface FrameNavigationViewProps extends FrameNavigationProps {
  /** The browser's pathname; `null` when it is not known, and then nothing is marked. */
  readonly pathname: string | null;
  /** The project the address names (`R-150c`), carried onto the links that may take it. Absent or `null`: none. */
  readonly projectUid?: string | null | undefined;
  /**
   * What draws «Меню» and each group. In the shell it is the `Disclosure` island, which holds its
   * own open state. An instrument that renders one static pass cannot click, so it passes a
   * view drawn open instead — the contrast census does — and measures the same tree.
   */
  readonly disclosure?: ComponentType<DisclosureProps> | undefined;
}

function links(group: NavigationGroup, current: CurrentScreen | null, projectUid: string | null) {
  return group.items.map((item) => ({
    href: withProjectParam(item.address, projectUid),
    label: item.label,
    icon: <NavigationGlyph label={item.label} />,
    current: current?.address === item.address,
  }));
}

function RailLink({
  item,
  current,
  projectUid,
}: {
  readonly item: NavigationItem;
  readonly current: boolean;
  readonly projectUid: string | null;
}) {
  const id = useId();
  const [tooltip, setTooltip] = useState<{ readonly left: number; readonly top: number } | null>(null);

  const show = (target: HTMLAnchorElement) => {
    const box = target.getBoundingClientRect();
    setTooltip({ left: box.right + 12, top: Math.max(8, Math.min(box.top + box.height / 2 - 17, window.innerHeight - 42)) });
  };

  return (
    <>
      <Link
        className={styles.railLink}
        href={withProjectParam(item.address, projectUid)}
        aria-label={item.label}
        aria-describedby={tooltip === null ? undefined : id}
        aria-current={current ? 'page' : undefined}
        onMouseEnter={(event) => show(event.currentTarget)}
        onMouseLeave={() => setTooltip(null)}
        onFocus={(event) => show(event.currentTarget)}
        onBlur={() => setTooltip(null)}
        onClick={() => setTooltip(null)}
      >
        <NavigationGlyph label={item.label} />
      </Link>
      {tooltip !== null && typeof document !== 'undefined'
        ? createPortal(<span id={id} role="tooltip" className={styles.railTooltip} style={tooltip}>{item.label}</span>, document.body)
        : null}
    </>
  );
}

export function FrameNavigationView({
  navigation,
  pathname,
  projectUid = null,
  disclosure = Disclosure,
}: FrameNavigationViewProps) {
  const Group = disclosure;
  const { groups } = navigation;
  if (groups.length === 0) return null;
  const current = currentScreen(pathname);
  const inGroup = (group: NavigationGroup): boolean => current?.group === group.group;
  return (
    <nav className={styles.nav} aria-label="Разделы">
      <div className={styles.row} data-nav-state="row">
        {groups.map((group) => (
          <Group key={group.group} label={group.label} current={inGroup(group)} links={links(group, current, projectUid)} layout="inline" defaultOpen closeOnNavigate={false} closeOnOutside={false} />
        ))}
      </div>
      <div className={styles.rail} data-nav-state="rail">
        {groups.map((group) => (
          <div className={styles.railGroup} key={group.group} role="group" aria-label={group.label} data-current-group={inGroup(group) ? 'true' : undefined}>
            {group.items.map((item) => <RailLink key={item.address} item={item} current={current?.address === item.address} projectUid={projectUid} />)}
          </div>
        ))}
      </div>
      <div className={styles.stacked} data-nav-state="stacked">
        <Group label="Меню" current={current !== null && groups.some(inGroup)} closeOnNavigate={false}>
          <ul className={styles.stackedList}>
            {groups.map((group) => (
              <li className={styles.stackedItem} key={group.group}>
                <Group label={group.label} layout="inline" current={inGroup(group)} links={links(group, current, projectUid)} closeOnNavigate={false} />
              </li>
            ))}
          </ul>
        </Group>
      </div>
    </nav>
  );
}

const NO_PARAMS = new URLSearchParams();

export function FrameNavigation({ navigation }: FrameNavigationProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const projectUid = pathname === null ? null : readProjectContext(pathname, searchParams).projectUid;
  return <FrameNavigationView navigation={navigation} pathname={pathname} projectUid={projectUid} />;
}
