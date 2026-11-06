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
 * ## The project's sections (`UI-A-04`)
 *
 * Under the current project only, a «Разделы» group follows «Работа»: one link per section of that project that
 * holds documents, with its mark and a count badge, leading to the section page (`section-navigation.ts`). It is
 * the same disclosure as the other groups, closed unless a section page is the one shown. With no project in the
 * address the group is not drawn, and `FrameNavigation` makes no read; with one, `use-section-navigation.ts` reads
 * the dashboard's summary of that project. {@link FrameNavigationView} takes the group's content as data
 * (`sections`), so every state of it is drawn without a query client.
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
import { Fragment, useId, useState } from 'react';
import type { ComponentType, ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { readProjectContext, withProjectParam } from '@/shared/lib';
import type { DisclosureProps } from '@/shared/ui';
import { Disclosure } from '@/shared/ui';
import { looksLikeProjectUid } from '@/entities/project';

import type { CurrentScreen, Navigation, NavigationGroup } from './navigation';
import { currentScreen } from './navigation';
import { NavigationGlyph } from './navigation-glyph';
import type { SectionNavigation } from './section-navigation';
import {
  SECTIONS_EMPTY_NOTE, SECTIONS_FAILED_NOTE, SECTIONS_GROUP_LABEL, SECTIONS_LOADING_NOTE, sectionEntryLabel,
} from './section-navigation';
import { useSectionNavigation } from './use-section-navigation';
import styles from './app-frame.module.css';

export interface FrameNavigationProps {
  readonly navigation: Navigation;
  /**
   * `UI-A-04`: whether this session may open the section page (`offersSectionNavigation`), so whether the current
   * project's «Разделы» group is offered. Absent: it is not.
   */
  readonly offersSections?: boolean | undefined;
}

export interface FrameNavigationViewProps {
  readonly navigation: Navigation;
  /** The browser's pathname; `null` when it is not known, and then nothing is marked. */
  readonly pathname: string | null;
  /** The project the address names (`R-150c`), carried onto the links that may take it. Absent or `null`: none. */
  readonly projectUid?: string | null | undefined;
  /** `UI-A-04`: the «Разделы» group's content for the current project. Absent: the group is not drawn. */
  readonly sections?: SectionNavigation | undefined;
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
  href,
  label,
  tooltipText = label,
  glyph,
  current,
}: {
  readonly href: string;
  /** The link's accessible name. */
  readonly label: string;
  /** What the hover tooltip says when it is not the name. */
  readonly tooltipText?: string | undefined;
  readonly glyph: ReactNode;
  readonly current: boolean;
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
        href={href}
        aria-label={label}
        aria-describedby={tooltip === null ? undefined : id}
        aria-current={current ? 'page' : undefined}
        onMouseEnter={(event) => show(event.currentTarget)}
        onMouseLeave={() => setTooltip(null)}
        onFocus={(event) => show(event.currentTarget)}
        onBlur={() => setTooltip(null)}
        onClick={() => setTooltip(null)}
      >
        {glyph}
      </Link>
      {tooltip !== null && typeof document !== 'undefined'
        ? createPortal(
          <span id={id} role="tooltip" className={tooltipText === label ? styles.railTooltip : `${styles.railTooltip} ${styles.railTooltipWrap}`} style={tooltip}>{tooltipText}</span>,
          document.body,
        )
        : null}
    </>
  );
}

/** What a «Разделы» group holds: the list, or the sentence that says why there is none. */
function SectionsPanel({ sections }: { readonly sections: SectionNavigation }) {
  if (sections.status === 'loading' || sections.status === 'failed') {
    return (
      <p className={styles.sectionNote} data-section-nav-status={sections.status}>
        {sections.status === 'loading' ? SECTIONS_LOADING_NOTE : SECTIONS_FAILED_NOTE}
      </p>
    );
  }
  if (sections.entries.length === 0) {
    return <p className={styles.sectionNote} data-section-nav-status="empty">{SECTIONS_EMPTY_NOTE}</p>;
  }
  return (
    <ul className="am-disclosure__list" data-section-nav={sections.entries.length}>
      {sections.entries.map((entry) => (
        <li className="am-disclosure__item" key={entry.code} data-section-nav-item={entry.code}>
          <Link
            className="am-disclosure__link"
            href={entry.href}
            aria-label={sectionEntryLabel(entry)}
            aria-current={entry.current ? 'page' : undefined}
            title={entry.name}
          >
            <span className={styles.sectionMark}>{entry.abbr}</span>
            <span className={styles.sectionCount}>{entry.count}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

/**
 * The «Разделы» disclosure. Keyed by the section page being shown, so arriving on one opens the group and leaving
 * it starts closed again; a reader's own toggling lasts until the next such change.
 */
function sectionsGroup(Group: ComponentType<DisclosureProps>, sections: SectionNavigation, open: boolean): ReactNode {
  const active = sections.status === 'ready' ? sections.entries.find((entry) => entry.current) : undefined;
  return (
    <Group
      key={`sections-${active?.code ?? 'none'}`}
      label={SECTIONS_GROUP_LABEL}
      current={active !== undefined}
      layout="inline"
      defaultOpen={open && active !== undefined}
      closeOnNavigate={false}
      closeOnOutside={open ? false : undefined}
    >
      <SectionsPanel sections={sections} />
    </Group>
  );
}

export function FrameNavigationView({
  navigation,
  pathname,
  projectUid = null,
  sections,
  disclosure = Disclosure,
}: FrameNavigationViewProps) {
  const Group = disclosure;
  const { groups } = navigation;
  if (groups.length === 0) return null;
  const current = currentScreen(pathname);
  const inGroup = (group: NavigationGroup): boolean => current?.group === group.group;
  // `UI-A-04`: the project's sections follow «Работа», the group of the screens that work on a project.
  const afterGroup = (group: NavigationGroup): boolean => group.group === 'work';
  const railSections = sections?.status === 'ready' ? sections.entries : [];
  return (
    <nav className={styles.nav} aria-label="Разделы">
      <div className={styles.row} data-nav-state="row">
        {groups.map((group) => (
          <Fragment key={group.group}>
            <Group label={group.label} current={inGroup(group)} links={links(group, current, projectUid)} layout="inline" defaultOpen closeOnNavigate={false} closeOnOutside={false} />
            {sections !== undefined && afterGroup(group) ? sectionsGroup(Group, sections, true) : null}
          </Fragment>
        ))}
      </div>
      <div className={styles.rail} data-nav-state="rail">
        {groups.map((group) => (
          <Fragment key={group.group}>
            <div className={styles.railGroup} role="group" aria-label={group.label} data-current-group={inGroup(group) ? 'true' : undefined}>
              {group.items.map((item) => (
                <RailLink
                  key={item.address}
                  href={withProjectParam(item.address, projectUid)}
                  label={item.label}
                  glyph={<NavigationGlyph label={item.label} />}
                  current={current?.address === item.address}
                />
              ))}
            </div>
            {railSections.length > 0 && afterGroup(group) ? (
              <div className={styles.railGroup} role="group" aria-label={SECTIONS_GROUP_LABEL} data-current-group={railSections.some((entry) => entry.current) ? 'true' : undefined}>
                {railSections.map((entry) => (
                  <RailLink
                    key={entry.code}
                    href={entry.href}
                    label={sectionEntryLabel(entry)}
                    tooltipText={`${entry.name}: ${entry.count}`}
                    glyph={<span data-nav-glyph="section" aria-hidden="true">{entry.abbr}</span>}
                    current={entry.current}
                  />
                ))}
              </div>
            ) : null}
          </Fragment>
        ))}
      </div>
      <div className={styles.stacked} data-nav-state="stacked">
        <Group label="Меню" current={current !== null && groups.some(inGroup)} closeOnNavigate={false}>
          <ul className={styles.stackedList}>
            {groups.map((group) => (
              <Fragment key={group.group}>
                <li className={styles.stackedItem}>
                  <Group label={group.label} layout="inline" current={inGroup(group)} links={links(group, current, projectUid)} closeOnNavigate={false} />
                </li>
                {sections !== undefined && afterGroup(group) ? <li className={styles.stackedItem}>{sectionsGroup(Group, sections, false)}</li> : null}
              </Fragment>
            ))}
          </ul>
        </Group>
      </div>
    </nav>
  );
}

const NO_PARAMS = new URLSearchParams();

/** The frame's navigation with the project's «Разделы» read: mounted only where the group is offered. */
function FrameNavigationWithSections({
  navigation,
  pathname,
  projectUid,
}: {
  readonly navigation: Navigation;
  readonly pathname: string;
  readonly projectUid: string;
}) {
  const sections = useSectionNavigation(projectUid, pathname);
  return <FrameNavigationView navigation={navigation} pathname={pathname} projectUid={projectUid} sections={sections} />;
}

export function FrameNavigation({ navigation, offersSections = false }: FrameNavigationProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const projectUid = pathname === null ? null : readProjectContext(pathname, searchParams).projectUid;
  // The group needs a current project the section pages can name; a malformed uid is the page's own refusal to say.
  if (offersSections && pathname !== null && projectUid !== null && looksLikeProjectUid(projectUid)) {
    return <FrameNavigationWithSections navigation={navigation} pathname={pathname} projectUid={projectUid} />;
  }
  return <FrameNavigationView navigation={navigation} pathname={pathname} projectUid={projectUid} />;
}
