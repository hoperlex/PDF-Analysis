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
import type { ComponentType } from 'react';

import type { MenuItem, MenuProps } from '@/shared/ui';
import { Menu } from '@/shared/ui';
import { useProjectList } from '@/entities/project';

import { SWITCHER_CAPTION, buildSwitcherModel, switcherContext, switcherListOf } from '../model/switcher';
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
}

export function ProjectSwitcherView({ model, onRetry, onIntent, menu = Menu }: ProjectSwitcherViewProps) {
  const Drawn = menu;
  return (
    <div
      className={model.scope === 'global' ? `${styles.switcher} ${styles.muted}` : styles.switcher}
      data-project-switcher=""
      data-project-scope={model.scope ?? 'unregistered'}
      onPointerEnter={onIntent}
      onPointerDownCapture={onIntent}
      onFocusCapture={onIntent}
    >
      <Drawn {...switcherMenuProps(model, onRetry)} />
    </div>
  );
}

/** The part that reads the list. Mounted in the browser only; exported for the instruments that seed a cache. */
export function ProjectSwitcherLive({ address }: { readonly address: SwitcherAddress }) {
  const [reached, setReached] = useState(false);
  const needsName = switcherContext(address).projectUid !== null;
  const query = useProjectList(undefined, { enabled: needsName || reached });
  const model = buildSwitcherModel(address, switcherListOf(query.data, query.error));
  return (
    <ProjectSwitcherView
      model={model}
      onRetry={() => {
        void query.refetch();
      }}
      onIntent={() => setReached(true)}
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
    <ProjectSwitcherView model={buildSwitcherModel(address, { kind: 'loading' })} onRetry={NOTHING} />
  );
}
