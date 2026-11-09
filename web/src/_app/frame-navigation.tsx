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
 * ## «Проект» or «Проекты», first in «Работа» (`R-153h`)
 *
 * The first item of «Работа» depends on the project the address names: «Проект», linking to that project's page, when
 * one is current, and «Проекты», linking to the list, when none is. It is not a registry row of the menu (the registry
 * holds both screens with `inMenu: false`; the top strip's selector is unchanged): `buildNavigation` carries it as the
 * navigation's `projectEntry`, decided by `screenDecision` like every row, and {@link FrameNavigationView} turns it into
 * an item with `withProjectEntry` from the `projectUid` it is given — so the bar, the compact rail and the stacked menu
 * draw the same first item, and it is `aria-current="page"` on the page it leads to. Like a required target it takes no
 * `?project=`; the list takes the parameter it is given, as the other global screens do.
 *
 * ## The project's sections (`UI-A-04`, `R-153g`)
 *
 * Under the current project only, a «Разделы» group follows «Работа»: one link per section of that project, the ones
 * with no document too (a muted 0, no red badge), with its mark and a count badge, leading to the section page (`section-navigation.ts`). It is
 * the same disclosure as the other groups, closed unless a section page is the one shown. Its button carries the group's own counters (`D-360`): the red sum of the sections' «не проверено экспертом» and, in grey,
 * the documents it lists, through the `Disclosure`'s `badge` slot, so they are seen while it is folded. With no project in the
 * address the group is not drawn, and `FrameNavigation` makes no read; with one, `use-section-navigation.ts` reads
 * the dashboard's summary of that project. {@link FrameNavigationView} takes the group's content as data
 * (`sections`), so every state of it is drawn without a query client.
 *
 * ## Counters beside the items (`UI-A-05`, `UI-A-06`, `UI-A-91`)
 *
 * An item may carry a small number (`menu-badges.ts`): the unchecked documents of a section in red, the jobs of
 * «Очередь» and, in red, those of the last day that ended in an error, the decisions on findings in «База знаний» (of the address's
 * project when it names one), the pending «Заявки на регистрацию». {@link FrameNavigationView} takes them as
 * data (`badges`, by item address; the sections carry theirs in `sections`), so every state is drawn without a query
 * client; `FrameNavigation` reads them (`use-menu-badges.ts`) only for the items the session's navigation holds, and only
 * where there is a query client. A group with a badged item hands the shared `Disclosure` its list as content
 * (`BadgedLinks`), since `links` has no place for a counter; the rail draws the number on the glyph's corner and the
 * link's name and tooltip say what it counts.
 *
 * ## The current page
 *
 * Read here, from `usePathname`, and matched against the registry's address shapes
 * (`currentScreen`): the frame is a server component that is handed a session and never a
 * request, and the pathname changes on every client-side navigation without the frame
 * rendering again. {@link FrameNavigationView} is the pure half, so the marking is tested with
 * any pathname without a router.
 */

import { QueryClientContext } from '@tanstack/react-query';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { Fragment, useContext, useId, useState } from 'react';
import type { ComponentType, ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { readProjectContext, withProjectParam } from '@/shared/lib';
import type { DisclosureBadge, DisclosureProps } from '@/shared/ui';
import { Disclosure } from '@/shared/ui';
import { looksLikeProjectUid } from '@/entities/project';

import type { MenuBadge, MenuBadgeSource, MenuBadges } from './menu-badges';
import { badgeSourceAt, badgeSourcesOf, itemLabelWithBadges, uncheckedBadges, uncheckedClause } from './menu-badges';
import type { CurrentScreen, Navigation, NavigationGroup } from './navigation';
import { currentScreen, itemIsCurrent, withProjectEntry } from './navigation';
import { BadgedLinks, ItemBadges, RailBadges } from './navigation-badges';
import { NavigationGlyph } from './navigation-glyph';
import type { SectionNavigation } from './section-navigation';
import {
  SECTIONS_DOCUMENTS_LABEL, SECTIONS_FAILED_NOTE, SECTIONS_GROUP_LABEL, SECTIONS_LOADING_NOTE, sectionEntryLabel,
  sectionsSummary, sectionsSummaryLabel,
} from './section-navigation';
import { useMenuBadges } from './use-menu-badges';
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
   * `UI-A-06`, `UI-A-91`: the counters beside the items, by the item's address. Absent: this render is not told of any,
   * and a group draws its links as the shared `Disclosure` does. Present (even empty): a group with an item that can
   * carry one draws its list itself, so the number appears in place when the read answers.
   */
  readonly badges?: MenuBadges | undefined;
  /**
   * What draws «Меню» and each group. In the shell it is the `Disclosure` island, which holds its
   * own open state. An instrument that renders one static pass cannot click, so it passes a
   * view drawn open instead — the contrast census does — and measures the same tree.
   */
  readonly disclosure?: ComponentType<DisclosureProps> | undefined;
}

const NO_BADGES: readonly MenuBadge[] = [];
const NO_SOURCES: ReadonlySet<MenuBadgeSource> = new Set();

function links(group: NavigationGroup, current: CurrentScreen | null, projectUid: string | null) {
  return group.items.map((item) => ({
    href: withProjectParam(item.address, projectUid),
    label: item.label,
    icon: <NavigationGlyph label={item.label} />,
    current: itemIsCurrent(item, current),
  }));
}

type GroupCommon = Omit<DisclosureProps, 'links' | 'children'>;

/**
 * One group's disclosure. With `badges` told and an item that can carry a counter, the group's list is
 * {@link BadgedLinks}; otherwise it is the plain `links` the shared `Disclosure` draws itself.
 */
function groupOf(
  Group: ComponentType<DisclosureProps>,
  common: GroupCommon,
  group: NavigationGroup,
  current: CurrentScreen | null,
  projectUid: string | null,
  badges: MenuBadges | undefined,
): ReactNode {
  if (badges !== undefined && group.items.some((item) => badgeSourceAt(item.address) !== null)) {
    return (
      <Group {...common}>
        <BadgedLinks group={group} current={current} projectUid={projectUid} badges={badges} />
      </Group>
    );
  }
  return <Group {...common} links={links(group, current, projectUid)} />;
}

function RailLink({
  href,
  label,
  tooltipText = label,
  wrapTooltip = tooltipText !== label,
  glyph,
  badges,
  current,
}: {
  readonly href: string;
  /** The link's accessible name. */
  readonly label: string;
  /** What the hover tooltip says when it is not the name. */
  readonly tooltipText?: string | undefined;
  /** The tooltip wraps instead of running on: it says more than the item's name. */
  readonly wrapTooltip?: boolean | undefined;
  readonly glyph: ReactNode;
  /** The counters on the glyph's corner. */
  readonly badges?: readonly MenuBadge[] | undefined;
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
        <RailBadges badges={badges ?? NO_BADGES} />
      </Link>
      {tooltip !== null && typeof document !== 'undefined'
        ? createPortal(
          <span id={id} role="tooltip" className={wrapTooltip ? `${styles.railTooltip} ${styles.railTooltipWrap}` : styles.railTooltip} style={tooltip}>{tooltipText}</span>,
          document.body,
        )
        : null}
    </>
  );
}

/**
 * What a «Разделы» group holds: the list, or the sentence that says why there is none. The list is every section of
 * the project (`R-153g`); one with no document shows a muted 0, no red badge, and links to its page like the others.
 */
function SectionsPanel({ sections }: { readonly sections: SectionNavigation }) {
  if (sections.status === 'loading' || sections.status === 'failed') {
    return (
      <p className={styles.sectionNote} data-section-nav-status={sections.status}>
        {sections.status === 'loading' ? SECTIONS_LOADING_NOTE : SECTIONS_FAILED_NOTE}
      </p>
    );
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
            <ItemBadges badges={uncheckedBadges(entry.awaitingDecision)}>
              <span className={entry.count === 0 ? `${styles.sectionCount} ${styles.sectionCountEmpty}` : styles.sectionCount}>{entry.count}</span>
            </ItemBadges>
          </Link>
        </li>
      ))}
    </ul>
  );
}

/**
 * `D-360`: the group's own counters, drawn on its button so they are seen while it is folded (the original's parent row):
 * the red «не проверено экспертом» sum and, in grey, the documents the group lists. None while the list is loading or
 * failed: a figure that was not read is no badge. A project with no document at all reads 0, muted like an empty section.
 */
function sectionsBadge(sections: SectionNavigation): DisclosureBadge | undefined {
  if (sections.status !== 'ready') return undefined;
  const summary = sectionsSummary(sections.entries);
  return {
    label: sectionsSummaryLabel(summary),
    content: (
      <ItemBadges badges={uncheckedBadges(summary.awaitingDecision)}>
        <span
          className={summary.documents === 0 ? `${styles.sectionCount} ${styles.sectionCountEmpty}` : styles.sectionCount}
          title={`${SECTIONS_DOCUMENTS_LABEL}: ${summary.documents}`}
          data-section-nav-total={summary.documents}
        >
          {summary.documents}
        </span>
      </ItemBadges>
    ),
  };
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
      badge={sectionsBadge(sections)}
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
  badges,
  disclosure = Disclosure,
}: FrameNavigationViewProps) {
  const Group = disclosure;
  // `R-153h`: «Проект» or «Проекты» is the first item of «Работа», by the project the address names. One navigation for the
  // bar, the compact rail and the stacked menu, so the item is in all three.
  const { groups } = withProjectEntry(navigation, projectUid);
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
            {groupOf(Group, { label: group.label, current: inGroup(group), layout: 'inline', defaultOpen: true, closeOnNavigate: false, closeOnOutside: false }, group, current, projectUid, badges)}
            {sections !== undefined && afterGroup(group) ? sectionsGroup(Group, sections, true) : null}
          </Fragment>
        ))}
      </div>
      <div className={styles.rail} data-nav-state="rail">
        {groups.map((group) => (
          <Fragment key={group.group}>
            <div className={styles.railGroup} role="group" aria-label={group.label} data-current-group={inGroup(group) ? 'true' : undefined}>
              {group.items.map((item) => {
                const own = badges?.[item.address] ?? NO_BADGES;
                return (
                  <RailLink
                    key={item.address}
                    href={withProjectParam(item.address, projectUid)}
                    label={itemLabelWithBadges(item.label, own)}
                    wrapTooltip={own.length > 0}
                    glyph={<NavigationGlyph label={item.label} />}
                    badges={own}
                    current={itemIsCurrent(item, current)}
                  />
                );
              })}
            </div>
            {railSections.length > 0 && afterGroup(group) ? (
              <div className={styles.railGroup} role="group" aria-label={SECTIONS_GROUP_LABEL} data-current-group={railSections.some((entry) => entry.current) ? 'true' : undefined}>
                {railSections.map((entry) => {
                  const unchecked = uncheckedClause(entry.awaitingDecision);
                  return (
                    <RailLink
                      key={entry.code}
                      href={entry.href}
                      label={sectionEntryLabel(entry)}
                      tooltipText={`${entry.name}: ${entry.count}${unchecked === null ? '' : `, ${unchecked}`}`}
                      glyph={<span data-nav-glyph="section" aria-hidden="true">{entry.abbr}</span>}
                      badges={uncheckedBadges(entry.awaitingDecision)}
                      current={entry.current}
                    />
                  );
                })}
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
                  {groupOf(Group, { label: group.label, layout: 'inline', current: inGroup(group), closeOnNavigate: false }, group, current, projectUid, badges)}
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

interface ConnectedProps {
  readonly navigation: Navigation;
  readonly pathname: string | null;
  readonly projectUid: string | null;
  /** The reads the menu's counters need (`badgeSourcesOf`); never empty here. */
  readonly sources: ReadonlySet<MenuBadgeSource>;
  readonly sections?: SectionNavigation | undefined;
}

/** The frame's navigation with its counters read: mounted only where there is a query client and an item that carries one. */
function FrameNavigationWithBadges({ navigation, pathname, projectUid, sources, sections }: ConnectedProps) {
  // `R-150c`: «База знаний» follows the header's project, which the address names; the other counters are global.
  const badges = useMenuBadges(sources, projectUid);
  return <FrameNavigationView navigation={navigation} pathname={pathname} projectUid={projectUid} sections={sections} badges={badges} />;
}

/** The frame's navigation with the project's «Разделы» read: mounted only where the group is offered. */
function FrameNavigationWithSections({
  navigation,
  pathname,
  projectUid,
  sources,
}: Omit<ConnectedProps, 'pathname' | 'projectUid' | 'sections'> & { readonly pathname: string; readonly projectUid: string }) {
  const sections = useSectionNavigation(projectUid, pathname);
  return sources.size === 0
    ? <FrameNavigationView navigation={navigation} pathname={pathname} projectUid={projectUid} sections={sections} />
    : <FrameNavigationWithBadges navigation={navigation} pathname={pathname} projectUid={projectUid} sections={sections} sources={sources} />;
}

export function FrameNavigation({ navigation, offersSections = false }: FrameNavigationProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const projectUid = pathname === null ? null : readProjectContext(pathname, searchParams).projectUid;
  // The counters are read only where there is a query client (the application's root layout always has one; a bare
  // render of the frame, as the shell's tests make, does not) and only for the items this session's menu holds.
  const client = useContext(QueryClientContext);
  const sources = client === undefined ? NO_SOURCES : badgeSourcesOf(navigation);
  // The group needs a current project the section pages can name; a malformed uid is the page's own refusal to say.
  if (offersSections && pathname !== null && projectUid !== null && looksLikeProjectUid(projectUid)) {
    return <FrameNavigationWithSections navigation={navigation} pathname={pathname} projectUid={projectUid} sources={sources} />;
  }
  return sources.size === 0
    ? <FrameNavigationView navigation={navigation} pathname={pathname} projectUid={projectUid} />
    : <FrameNavigationWithBadges navigation={navigation} pathname={pathname} projectUid={projectUid} sources={sources} />;
}
