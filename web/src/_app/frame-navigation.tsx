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
 * ## The object is carried (`R-150c`, `UIP-G-06`)
 *
 * The object the address names (`?project=` on an optional or global screen, the path on a required one) rides on every link
 * whose target may take it: `withProjectParam` adds it to an optional or global screen and leaves a required one alone. The
 * explicit «Все объекты» (`?project=all`) rides the same way, so the choice outlives a click instead of letting the
 * account's last object come back on the next screen. The account's last object (`useCurrentProject`, on a screen that
 * follows the object) is **not** carried: it is the next screen's own default, and writing it into every link would turn a
 * default into a choice. The address stays the only source of an explicit choice; the links are rewritten from it on each
 * render, so the choice outlives a click.
 *
 * ## «Объект» or «Объекты», third in «Работа» (`R-153h`, `UIP-G-07`)
 *
 * «Работа» opens with «Главная» and «Дашборд»; the item after them depends on the object that is current: «Объект», linking to
 * that object's page, when one is, and «Объекты», linking to the list, when none is. It is not a registry row of the menu (the
 * registry holds both screens with `inMenu: false`; the top strip's selector is unchanged): `buildNavigation` carries it as the
 * navigation's `projectEntry`, decided by `screenDecision` like every row, and {@link FrameNavigationView} turns it into
 * an item with `withProjectEntry` from the `projectUid` it is given — so the bar, the compact rail and the stacked menu
 * draw the same item, and it is `aria-current="page"` on the page it leads to. Like a required target it takes no
 * `?project=`; the list takes the parameter it is given, as the other global screens do.
 *
 * ## The object's sections (`UI-A-04`, `R-153g`, `UIP-G-07`)
 *
 * A «Разделы» group follows «Работа» **always** (for a session that may open the section page): one link per section of the
 * current object, the ones with no document too (a muted 0, no red badge), each with the dot of its colour (`SectionDot`), its
 * code and its counters, leading to the section page (`section-navigation.ts`). It is the same disclosure as the other groups,
 * closed unless a section page is the one shown. Its button carries the group's own counters (`D-360`): the red sum of the
 * sections' «не проверено экспертом» and, in grey, the documents it lists, through the `Disclosure`'s `badge` slot, so they are
 * seen while it is folded. The object is the one `useCurrentProject` names: the address's, or on a screen that follows the
 * object the account's last one. With none («Все объекты», chosen or not) the group has one row, «Выберите объект», and no
 * sections; with one, `use-section-navigation.ts` reads the dashboard's summary of it. {@link FrameNavigationView} takes the
 * group's content as data (`sections`), so every state of it is drawn without a query client.
 *
 * Without a query client (a bare render of the frame) nothing can be read, neither the account nor the sections: the object is
 * the address's alone, and the group is drawn only for the state that needs no read.
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

import { HOME_SCREEN } from '@/shared/config';
import { ALL_PROJECTS_PARAM, readProjectContext, withProjectParam } from '@/shared/lib';
import type { ProjectSource } from '@/shared/lib';
import type { DisclosureBadge, DisclosureProps } from '@/shared/ui';
import { Disclosure } from '@/shared/ui';
import { SectionDot, looksLikeProjectUid, useCurrentProject } from '@/entities/project';

import type { MenuBadge, MenuBadgeSource, MenuBadges } from './menu-badges';
import { badgeSourceAt, badgeSourcesOf, itemLabelWithBadges, uncheckedBadges, uncheckedClause } from './menu-badges';
import type { CurrentScreen, Navigation, NavigationGroup } from './navigation';
import { currentScreen, itemIsCurrent, withProjectEntry } from './navigation';
import { BadgedLinks, ItemBadges, RailBadges } from './navigation-badges';
import { NavigationGlyph } from './navigation-glyph';
import type { SectionNavigation } from './section-navigation';
import {
  SECTIONS_DOCUMENTS_LABEL, SECTIONS_FAILED_NOTE, SECTIONS_GROUP_LABEL, SECTIONS_LOADING_NOTE, SECTIONS_NO_OBJECT_NOTE,
  sectionEntryLabel, sectionsSummary, sectionsSummaryLabel,
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
  /**
   * The object that is current (`R-150c`, `UIP-G-06`): the address's, or on a screen that follows the object the account's
   * last one. The project entry and the counters of «База знаний» follow it; it is carried onto the links that may take it
   * unless `carriedProject` says otherwise. Absent or `null`: none.
   */
  readonly projectUid?: string | null | undefined;
  /**
   * What rides on the links as `?project=`: an object's uid, {@link ALL_PROJECTS_PARAM} for the explicit «Все объекты»
   * (`UIP-G-07`), `null` for nothing. Absent: `projectUid`. It differs from `projectUid` when the object is only the
   * account's last one, which the next screen defaults to by itself, or when the address chose «Все объекты».
   */
  readonly carriedProject?: string | null | undefined;
  /** `UI-A-04`, `UIP-G-07`: the «Разделы» group's content for the current object. Absent: the group is not drawn. */
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

function links(group: NavigationGroup, current: CurrentScreen | null, carried: string | null) {
  return group.items.map((item) => ({
    href: withProjectParam(item.address, carried),
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
  carried: string | null,
  badges: MenuBadges | undefined,
): ReactNode {
  if (badges !== undefined && group.items.some((item) => badgeSourceAt(item.address) !== null)) {
    return (
      <Group {...common}>
        <BadgedLinks group={group} current={current} projectUid={carried} badges={badges} />
      </Group>
    );
  }
  return <Group {...common} links={links(group, current, carried)} />;
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

/** The sentence a group with no list says: why there is none (`UIP-G-07`: no object; still reading; could not be read whole). */
const SECTIONS_NOTES = {
  none: SECTIONS_NO_OBJECT_NOTE,
  loading: SECTIONS_LOADING_NOTE,
  failed: SECTIONS_FAILED_NOTE,
} as const;

/**
 * What a «Разделы» group holds: the list, or the sentence that says why there is none. The list is every section of
 * the object (`R-153g`); one with no document shows a muted 0, no red badge, and links to its page like the others. Each
 * link is the dot of the section's colour (`UIP-G-17`), its code, the red count of documents no expert has checked and the
 * count of documents.
 */
function SectionsPanel({ sections }: { readonly sections: SectionNavigation }) {
  if (sections.status !== 'ready') {
    return (
      <p className={styles.sectionNote} data-section-nav-status={sections.status}>
        {SECTIONS_NOTES[sections.status]}
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
            <SectionDot code={entry.code} />
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
  carriedProject = projectUid,
  sections,
  badges,
  disclosure = Disclosure,
}: FrameNavigationViewProps) {
  const Group = disclosure;
  // `R-153h`, `UIP-G-07`: «Объект» or «Объекты» is the third item of «Работа», by the object that is current. One navigation
  // for the bar, the compact rail and the stacked menu, so the item is in all three.
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
            {groupOf(Group, { label: group.label, current: inGroup(group), layout: 'inline', defaultOpen: true, closeOnNavigate: false, closeOnOutside: false }, group, current, carriedProject, badges)}
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
                    href={withProjectParam(item.address, carriedProject)}
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
                      glyph={<span className={styles.railSection} data-nav-glyph="section" aria-hidden="true"><SectionDot code={entry.code} />{entry.abbr}</span>}
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
                  {groupOf(Group, { label: group.label, layout: 'inline', current: inGroup(group), closeOnNavigate: false }, group, current, carriedProject, badges)}
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

/**
 * What the frame knows of the object that is current: its uid (`null` for «Все объекты»), where it came from, and whether
 * the account's last object, which the address's silence leaves to `getMe`, is still on its way.
 */
interface CurrentObject {
  readonly projectUid: string | null;
  readonly source: ProjectSource;
  readonly pending: boolean;
}

const NO_OBJECT: CurrentObject = { projectUid: null, source: 'none', pending: false };

/**
 * What rides on the links (`R-150c`, `UIP-G-07`): the object the address names (`path`, `query`), or the explicit «Все объекты»
 * as {@link ALL_PROJECTS_PARAM}; never the account's last object, which is the next screen's own default.
 */
function carriedOf(object: CurrentObject): string | null {
  if (object.source === 'all') return ALL_PROJECTS_PARAM;
  return object.source === 'path' || object.source === 'query' ? object.projectUid : null;
}

/** The navigation as it is drawn, less the counters: what every connected layer below passes on to the view. */
interface ViewData {
  readonly navigation: Navigation;
  readonly pathname: string | null;
  readonly projectUid: string | null;
  readonly carriedProject: string | null;
  readonly sections?: SectionNavigation | undefined;
}

/** The reads the menu's counters need (`badgeSourcesOf`); never empty where {@link FrameNavigationWithBadges} is mounted. */
interface WithSources extends ViewData {
  readonly sources: ReadonlySet<MenuBadgeSource>;
}

/** The frame's navigation with its counters read: mounted only where there is a query client and an item that carries one. */
function FrameNavigationWithBadges({ sources, ...view }: WithSources) {
  // `R-150c`: «База знаний» follows the header's object (the one the screen shows), the other counters are global.
  const badges = useMenuBadges(sources, view.projectUid);
  return <FrameNavigationView {...view} badges={badges} />;
}

/** The view, with the counters read when the session's menu holds an item that carries one. */
function FrameNavigationCounted({ sources, ...view }: WithSources) {
  return sources.size === 0
    ? <FrameNavigationView {...view} />
    : <FrameNavigationWithBadges sources={sources} {...view} />;
}

/** The frame's navigation with the object's «Разделы» read: mounted only where the group is offered and the object is one. */
function FrameNavigationWithSections({ projectUid, ...rest }: Omit<WithSources, 'projectUid'> & { readonly projectUid: string }) {
  const sections = useSectionNavigation(projectUid, rest.pathname);
  return <FrameNavigationCounted {...rest} projectUid={projectUid} sections={sections} />;
}

interface ConnectedProps {
  readonly navigation: Navigation;
  readonly pathname: string | null;
  readonly object: CurrentObject;
  readonly offersSections: boolean;
  /** Whether there is a query client: the counters, the account's last object and the sections are read only where there is. */
  readonly connected: boolean;
}

/** One navigation for one current object: decides what the «Разделы» group has to say, and mounts the reads it needs. */
function FrameNavigationOfObject({ navigation, pathname, object, offersSections, connected }: ConnectedProps) {
  const { projectUid } = object;
  const view: WithSources = {
    navigation,
    pathname,
    projectUid,
    carriedProject: carriedOf(object),
    sources: connected ? badgeSourcesOf(navigation) : NO_SOURCES,
  };
  if (!offersSections) return <FrameNavigationCounted {...view} />;
  // An object the address spells as no uid has no sections the group could name; the page itself says so. The account's last
  // object is still on its way: say so, and read nothing.
  if (object.pending) return <FrameNavigationCounted {...view} sections={{ status: 'loading' }} />;
  if (projectUid === null || !looksLikeProjectUid(projectUid)) return <FrameNavigationCounted {...view} sections={{ status: 'none' }} />;
  // The sections are read from the dashboard's summary, which needs a query client; without one the group has nothing to say.
  return connected
    ? <FrameNavigationWithSections {...view} projectUid={projectUid} />
    : <FrameNavigationCounted {...view} />;
}

/** No query client (a bare render of the frame): the object is the address's alone, and nothing is read. */
function FrameNavigationOfAddress({ navigation, offersSections }: Omit<FrameNavigationProps, 'offersSections'> & { readonly offersSections: boolean }) {
  const pathname = usePathname();
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const object: CurrentObject = pathname === null ? NO_OBJECT : { ...readProjectContext(pathname, searchParams), pending: false };
  return <FrameNavigationOfObject navigation={navigation} pathname={pathname} object={object} offersSections={offersSections} connected={false} />;
}

/** With a query client: the object is `useCurrentProject`'s, the address's or, on a screen that follows the object, the account's last. */
function FrameNavigationOfCurrentProject({ navigation, offersSections }: Omit<FrameNavigationProps, 'offersSections'> & { readonly offersSections: boolean }) {
  const pathname = usePathname();
  const current = useCurrentProject(HOME_SCREEN);
  // A frame that does not know its address (a render outside the app router) names no object.
  const object: CurrentObject = pathname === null ? NO_OBJECT : current;
  return <FrameNavigationOfObject navigation={navigation} pathname={pathname} object={object} offersSections={offersSections} connected />;
}

export function FrameNavigation({ navigation, offersSections = false }: FrameNavigationProps) {
  // The reads are made only where there is a query client (the application's root layout always has one; a bare render of
  // the frame, as the shell's tests make, does not) and the counters only for the items this session's menu holds.
  const client = useContext(QueryClientContext);
  // A session with no menu (a guest, a default credential, an incomplete profile, an account with no role) draws nothing and
  // so asks for nothing: not the account's last object, not a counter.
  if (navigation.groups.length === 0 && navigation.projectEntry === undefined) return null;
  return client === undefined
    ? <FrameNavigationOfAddress navigation={navigation} offersSections={offersSections} />
    : <FrameNavigationOfCurrentProject navigation={navigation} offersSections={offersSections} />;
}
