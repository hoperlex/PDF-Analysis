'use client';

/**
 * «Проекты ▾» — the project selector in the frame's top strip (`R-150b`, `UI-PARITY-01` wave 1).
 *
 * It replaces the «Проекты» item of the sidebar. The button shows the project the address names
 * (or «Все проекты»), and opens the APG menu button from `@/shared/ui` (`Menu`): one row per
 * project with its two figures, then «Все проекты» and «Новый проект». The project that is open carries a ✓ (`D-363`). Every row is a link, so a
 * choice is an ordinary navigation to an address and needs no router and no state of its own;
 * the address stays the only source of the project (`R-150c`).
 *
 * ## It asks the server as little as it can
 *
 * The frame is on every screen, and the live journey (`tests/e2e/pc01/journey/manifest.json`)
 * fails on a request no route declares. So the project list is read only when something needs it:
 *
 *   - the address names a project, and the button needs its name;
 *   - the reader showed intent: pointer over the selector, focus on it, a press.
 *
 * A screen with no project in its address, and nobody reaching for the selector, makes no request.
 * `Menu` keeps its own open state and exposes none, so intent is read from the events that
 * precede an opening rather than from the opening.
 *
 * ## The object it names, and the command a choice is (`UIP-G-06`)
 *
 * On an `optional` screen whose address names no object the button names the account's last object (`getMe`'s
 * `last_project_uid`, read through `useLastProject`: only there, so no other screen asks for it), and a click on a project's row
 * also asks the server to keep it (`useRememberProject`, `setMyLastProject`). The click itself is the link's: the
 * address is already the chosen object's, and a refusal of the command never stops it. The refusal is said beside the button
 * (`data-switcher-remember-failure`), not inside the closed list. `Menu` takes no handler for a link, so the widget reads the
 * click off the wrapper and asks the model which object the link chose (`chosenProject`). «Все объекты» is `?project=all`
 * and is not sent.
 *
 * ## Two layers, and a mount gate
 *
 * {@link ProjectSwitcherView} is pure markup from a {@link SwitcherModel}; the instruments that
 * cannot click draw it open through `menu`. {@link ProjectSwitcher} is the island. Its first
 * render, the server's and the hydration's, is the closed selector with no list and no query
 * client; the part that reads the list mounts after hydration, as the release notices do
 * (`_app/release-notices.tsx`), so a render of the frame with no client stays request-free.
 */

import { useSearchParams, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import type { ComponentType, MouseEvent } from 'react';

import type { MenuItem, MenuProps } from '@/shared/ui';
import { Menu } from '@/shared/ui';
import { useLastProject, useRememberProject } from '@/entities/account';
import type { RememberProjectFailure } from '@/entities/account';
import { useProjectList } from '@/entities/project';

import { SWITCHER_CAPTION, buildSwitcherModel, chosenProject, switcherContext, switcherListOf } from '../model/switcher';
import type { SwitcherAddress, SwitcherEntry, SwitcherModel, SwitcherNote } from '../model/switcher';
import styles from './project-switcher.module.css';

const NO_PARAMS = new URLSearchParams();

function Notes({ notes }: { readonly notes: readonly SwitcherNote[] }) {
  if (notes.length === 0) return null;
  return (
    <div className={styles.notes}>
      {notes.map((note) => (
        <p
          className={note.tone === 'alert' ? styles.noteAlert : styles.note}
          role={note.tone === 'alert' ? 'alert' : 'status'}
          data-switcher-note=""
          key={note.text}
        >
          {note.text}
          {note.detail === undefined ? null : <span className={styles.noteDetail}>{note.detail}</span>}
          {note.correlationId === undefined ? null : (
            <span className={styles.noteDetail}>Код обращения: {note.correlationId}</span>
          )}
        </p>
      ))}
    </div>
  );
}

/**
 * The props of the selector's `Menu` for `model`. Exported so the instruments that render the
 * menu OPEN (the contrast census) render what the frame holds, not a copy.
 */
export function switcherMenuProps(model: SwitcherModel, onRetry: () => void): MenuProps {
  const items = model.entries.map(
    (entry: SwitcherEntry): MenuItem =>
      entry.kind === 'link'
        ? { kind: 'link', label: entry.label, href: entry.href, ...(entry.current === undefined ? {} : { current: entry.current }) }
        : { kind: 'action', label: entry.label, onChoose: onRetry },
  );
  const [first, ...rest] = items;
  return {
    label: model.triggerLabel,
    trigger: (
      <span className={styles.face}>
        <span className={styles.caption}>
          {model.hint === null ? SWITCHER_CAPTION : <>{SWITCHER_CAPTION}<span className={styles.hint}> · {model.hint}</span></>}
        </span>
        <span className={styles.value}>{model.value}</span>
        <span className={styles.caret} aria-hidden="true">▾</span>
      </span>
    ),
    header: model.notes.length === 0 ? undefined : <Notes notes={model.notes} />,
    items: [first as MenuItem, ...rest],
  };
}

export interface ProjectSwitcherViewProps {
  readonly model: SwitcherModel;
  readonly onRetry: () => void;
  /** The reader reached for the selector: pointer over it, focus on it, a press. */
  readonly onIntent?: (() => void) | undefined;
  /**
   * What draws the menu. In the shell it is `Menu`, which holds its own open state. An
   * instrument that renders one static pass cannot click, so it passes a view drawn open instead.
   */
  readonly menu?: ComponentType<MenuProps> | undefined;
  /** The reader followed a link of the menu: the object it chose, or `null` for a link that chose none (`chosenProject`). */
  readonly onNavigate?: ((projectUid: string | null) => void) | undefined;
  /** The last choice of an object could not be kept on the server; said beside the button. */
  readonly rememberFailure?: RememberProjectFailure | null | undefined;
}

export function ProjectSwitcherView({ model, onRetry, onIntent, menu = Menu, onNavigate, rememberFailure }: ProjectSwitcherViewProps) {
  const Drawn = menu;
  // The click reaches the wrapper from a link of the menu (`Menu` takes no handler for a link). Read off the target, not `instanceof`:
  // the target is whatever the click landed on, and only an element can be asked for the link around it.
  const followed = (event: MouseEvent<HTMLDivElement>) => {
    const target = event.target as Partial<Pick<Element, 'closest'>> | null;
    if (onNavigate === undefined || typeof target?.closest !== 'function') return;
    const link = target.closest('a[href]');
    if (link !== null) onNavigate(chosenProject(model, link.getAttribute('href')));
  };
  return (
    <div
      className={model.scope === 'global' ? `${styles.switcher} ${styles.muted}` : styles.switcher}
      data-project-switcher=""
      data-project-scope={model.scope ?? 'unregistered'}
      onPointerEnter={onIntent}
      onPointerDownCapture={onIntent}
      onFocusCapture={onIntent}
      onClick={followed}
    >
      <Drawn {...switcherMenuProps(model, onRetry)} />
      {rememberFailure === null || rememberFailure === undefined ? null : (
        <span className={`${styles.noteAlert} ${styles.rememberFailure}`} role="alert" data-switcher-remember-failure="">
          Объект открыт, но не запомнен: {rememberFailure.detail}
          {rememberFailure.correlationId === null ? null : ` Код обращения: ${rememberFailure.correlationId}`}
        </span>
      )}
    </div>
  );
}

/**
 * The part that reads the list and the account's last object, and keeps a choice. Mounted in the browser only; exported for
 * the instruments that seed a cache (the account's answer is read from the cache too: seed `queryKeys.account.me()`).
 */
export function ProjectSwitcherLive({ address }: { readonly address: Pick<SwitcherAddress, 'pathname' | 'searchParams'> }) {
  const [reached, setReached] = useState(false);
  // The account is asked for only where its answer changes what the button says: an `optional` screen with a silent address.
  const own = switcherContext(address);
  const last = useLastProject({ enabled: own.scope === 'optional' && own.source === 'none' });
  const resolved: SwitcherAddress = { ...address, remembered: last.projectUid, rememberedPending: last.pending };
  const needsName = switcherContext(resolved).projectUid !== null;
  const query = useProjectList(undefined, { enabled: needsName || reached });
  const model = buildSwitcherModel(resolved, switcherListOf(query.data, query.error));
  const { remember, failure, reset } = useRememberProject();
  return (
    <ProjectSwitcherView
      model={model}
      onRetry={() => {
        void query.refetch();
      }}
      onIntent={() => setReached(true)}
      onNavigate={(projectUid) => {
        // A choice of one object is kept; any other link clears the last refusal, which was about an earlier choice.
        if (projectUid === null) reset();
        else if (projectUid !== last.projectUid) remember(projectUid);
      }}
      rememberFailure={failure}
    />
  );
}

const NOTHING = (): void => undefined;

export function ProjectSwitcher() {
  const pathname = usePathname();
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const address: SwitcherAddress = { pathname, searchParams };
  return mounted ? (
    <ProjectSwitcherLive address={address} />
  ) : (
    // The first render knows nothing of the account yet: an `optional` screen with a silent address says so, not «Все объекты».
    <ProjectSwitcherView model={buildSwitcherModel({ ...address, rememberedPending: true }, { kind: 'loading' })} onRetry={NOTHING} />
  );
}
