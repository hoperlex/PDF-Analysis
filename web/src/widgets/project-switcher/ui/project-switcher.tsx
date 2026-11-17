'use client';

/**
 * The object selector in the frame's top strip (`R-150b`, `UI-PARITY-01` wave 1; its look is `UIP-G-08`).
 *
 * It replaces the «Проекты» item of the sidebar. The button is the name of the object the address names (or «Все объекты») and a
 * ▾, with no caption and no frame, as the original's is; its accessible name is «Объект: <название>» (or «Все объекты»), and on a
 * global screen «экран общий» is said in its tooltip and its accessible name. It opens the menu button of `./object-menu`: one
 * row per object with its two figures as small badges (the words in the tooltip and in the row's accessible name), then «Все
 * объекты» and «Новый объект». The object that is open carries a ✓ (`D-363`). Every row is a link, so a
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
 * The menu keeps its own open state and exposes none, so intent is read from the events that
 * precede an opening rather than from the opening.
 *
 * ## The object it names, and the command a choice is (`UIP-G-06`)
 *
 * On an `optional` screen whose address names no object the button names the account's last object (`getMe`'s
 * `last_project_uid`, read through `useLastProject`: only there, so no other screen asks for it), and a click on a project's row
 * also asks the server to keep it (`useRememberProject`, `setMyLastProject`). The click itself is the link's: the
 * address is already the chosen object's, and a refusal of the command never stops it. The refusal is said beside the button
 * (`data-switcher-remember-failure`), not inside the closed list. The menu takes no handler for a link, so the widget reads the
 * click off the wrapper and asks the model which object the link chose (`chosenProject`). «Все объекты» is `?project=all`
 * and is not sent.
 *
 * ## «Новый объект» (`UIP-S03-01`)
 *
 * Once the island is live, the last row of the menu is an action: it opens the window «Новый объект» (`./new-object-dialog`, the
 * shared window with the page's own create form in it), and when the object has been made it becomes the open one as a click on
 * its row does (`afterObjectCreated`: the choice is kept, the address is rewritten). The row is a link to the list's form until
 * then (the first render, and a render with no island), and it is not offered at all to an account known not to be an expert
 * (`R-150e`). Whether the account is an expert is read from the cache only: the selector asks the server for the account
 * nowhere but where it has always asked, and an account not known yet leaves the row drawn.
 *
 * ## Two layers, and a mount gate
 *
 * {@link ProjectSwitcherView} is pure markup from a {@link SwitcherModel}; the instruments that
 * cannot click draw it open through `menu`. {@link ProjectSwitcher} is the island. Its first
 * render, the server's and the hydration's, is the closed selector with no list and no query
 * client; the part that reads the list mounts after hydration, as the release notices do
 * (`_app/release-notices.tsx`), so a render of the frame with no client stays request-free.
 */

import { useQuery } from '@tanstack/react-query';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import type { ComponentType, MouseEvent } from 'react';

import type { Account } from '@/shared/api';
import { mayActAsExpert, meQueryOptions, useLastProject, useRememberProject } from '@/entities/account';
import type { RememberProjectFailure } from '@/entities/account';
import { useProjectList } from '@/entities/project';

import { afterObjectCreated, buildSwitcherModel, chosenProject, switcherContext, switcherListOf } from '../model/switcher';
import type { SwitcherAddress, SwitcherEntry, SwitcherModel, SwitcherNote } from '../model/switcher';
import { NewObjectDialog } from './new-object-dialog';
import { ObjectMenu } from './object-menu';
import type { ObjectMenuItem, ObjectMenuProps } from './object-menu';
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
 * The props of the selector's menu for `model`. Exported so the instruments that render the
 * menu OPEN (the contrast census) render what the frame holds, not a copy. `onCreate` (`UIP-S03-01`): the island's way to open the
 * window «Новый объект»; without it the row stays the link to the list's form.
 */
export function switcherMenuProps(model: SwitcherModel, onRetry: () => void, onCreate?: () => void): ObjectMenuProps {
  const items = model.entries.map((entry: SwitcherEntry): ObjectMenuItem => {
    if (entry.kind === 'retry') return { kind: 'action', label: entry.label, onChoose: onRetry };
    // `UIP-S03-01`: with the island's handler the row that makes an object opens the window; without it, it is the link.
    if (entry.creates === true && onCreate !== undefined) return { kind: 'action', label: entry.label, onChoose: onCreate };
    return {
      kind: 'link',
      label: entry.label,
      href: entry.href,
      ...(entry.current === undefined ? {} : { current: entry.current }),
      ...(entry.projectUid === undefined ? {} : { object: true }),
      ...(entry.figures === undefined ? {} : { figures: entry.figures }),
      ...(entry.name === undefined ? {} : { name: entry.name }),
    };
  });
  const [first, ...rest] = items;
  return {
    label: model.triggerLabel,
    ...(model.title === null ? {} : { title: model.title }),
    trigger: (
      <span className={styles.face}>
        <span className={styles.value}>{model.value}</span>
        <span className={styles.caret} aria-hidden="true">▾</span>
      </span>
    ),
    header: model.notes.length === 0 ? undefined : <Notes notes={model.notes} />,
    items: [first as ObjectMenuItem, ...rest],
  };
}

export interface ProjectSwitcherViewProps {
  readonly model: SwitcherModel;
  readonly onRetry: () => void;
  /** `UIP-S03-01`: opens the window «Новый объект». Absent: the row «Новый объект» is the link to the list's form. */
  readonly onCreate?: (() => void) | undefined;
  /** The reader reached for the selector: pointer over it, focus on it, a press. */
  readonly onIntent?: (() => void) | undefined;
  /**
   * What draws the menu. In the shell it is `ObjectMenu`, which holds its own open state. An
   * instrument that renders one static pass cannot click, so it passes a view drawn open instead.
   */
  readonly menu?: ComponentType<ObjectMenuProps> | undefined;
  /** The reader followed a link of the menu: the object it chose, or `null` for a link that chose none (`chosenProject`). */
  readonly onNavigate?: ((projectUid: string | null) => void) | undefined;
  /** The last choice of an object could not be kept on the server; said beside the button. */
  readonly rememberFailure?: RememberProjectFailure | null | undefined;
}

export function ProjectSwitcherView({ model, onRetry, onCreate, onIntent, menu = ObjectMenu, onNavigate, rememberFailure }: ProjectSwitcherViewProps) {
  const Drawn = menu;
  // The click reaches the wrapper from a link of the menu (the menu takes no handler for a link). Read off the target, not `instanceof`:
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
      <Drawn {...switcherMenuProps(model, onRetry, onCreate)} />
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
  const [creating, setCreating] = useState(false);
  const router = useRouter();
  // The account is asked for only where its answer changes what the button says: an `optional` screen with a silent address.
  const own = switcherContext(address);
  const asksAccount = own.scope === 'optional' && own.source === 'none';
  const last = useLastProject({ enabled: asksAccount });
  // `UIP-S03-01`: whether to offer «Новый объект» is read from the account's one query under the SAME `enabled` as the read above,
  // so it asks for nothing more (a second observer of one query is one request), and an account not known yet leaves the row drawn.
  const mayCreate = mayActAsExpert(useQuery<Account>({ ...meQueryOptions(), enabled: asksAccount }).data?.roles);
  const resolved: SwitcherAddress = { ...address, remembered: last.projectUid, rememberedPending: last.pending };
  const needsName = switcherContext(resolved).projectUid !== null;
  const query = useProjectList(undefined, { enabled: needsName || reached });
  const model = buildSwitcherModel(resolved, switcherListOf(query.data, query.error, query.isFetching), { mayCreate });
  const { remember, failure, reset } = useRememberProject();
  return (
    <>
      <ProjectSwitcherView
        model={model}
        onRetry={() => {
          void query.refetch();
        }}
        onCreate={() => setCreating(true)}
        onIntent={() => setReached(true)}
        onNavigate={(projectUid) => {
          // A choice of one object is kept; any other link clears the last refusal, which was about an earlier choice.
          if (projectUid === null) reset();
          else if (projectUid !== last.projectUid) remember(projectUid);
        }}
        rememberFailure={failure}
      />
      {creating ? (
        <NewObjectDialog
          onClose={() => setCreating(false)}
          onCreated={(project) => {
            afterObjectCreated(resolved, project, {
              remember,
              navigate: (href) => router.push(href),
              close: () => setCreating(false),
            });
          }}
        />
      ) : null}
    </>
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
