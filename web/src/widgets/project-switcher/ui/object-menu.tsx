'use client';

/**
 * The menu button of the object selector (`UIP-G-08`): the APG *menu button* of `Menu` (`@/shared/ui`), with the one thing
 * `Menu` cannot draw — a row that carries the two figures of an object as badges.
 *
 * `Menu` takes a plain string for an item's label (`MenuItem.label`), and the badges are markup, a colour and a tooltip each.
 * `shared/ui` is not this widget's to change, so the widget draws its own menu from the pieces `shared/ui` publishes: the
 * keyboard and open/close rules are `menuTransition` (`menu-state.ts`, one pure function, tested on its own), and the markup
 * is the one `Menu` has, class for class, so the global `am-menu*` rules (the popup, the row, the ✓ cell of `D-363`) draw it
 * and the shell's tests that read the markup read this one. What is added here is only what an object's row needs: the name
 * and the badges, and a title on the button.
 *
 * Two layers, as `Menu` has: {@link ObjectMenuView} is pure markup from props and a `MenuState`, which the contrast census
 * draws open; {@link ObjectMenu} is the island that holds the state and turns browser events into `menuTransition` calls.
 * Its server render is the view's closed state.
 *
 * ## A row with figures
 *
 * `name` · the two badges · the ✓ cell. The badges are `am-badge` in the two colours of meaning the dashboard already gives these
 * numbers (`degraded` for «не запускались», `active` for «нет решений эксперта»); each has the words in its `title`, and the
 * row's accessible name (`aria-label`) says the name and both figures with their words, so the badges are hidden from assistive
 * technology: «2» alone would mean nothing. A row without figures is its name as plain text, as in `Menu`.
 */

import Link from 'next/link';
import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent, ReactNode, Ref } from 'react';

import { MENU_CLOSED, menuTransition } from '@/shared/ui';
import type { MenuEvent, MenuFocus, MenuState, MenuTransition } from '@/shared/ui';

import type { RowFigure } from '../model/switcher';
import styles from './project-switcher.module.css';

export type ObjectMenuItem =
  | {
      readonly kind: 'link';
      /** The name as drawn. */
      readonly label: string;
      readonly href: string;
      /** `D-363`: this link is a choice, and `true` marks the choice made. Absent: the link is not a choice. */
      readonly current?: boolean | undefined;
      /** This row is an object: it takes the picker's row step. The fixed rows («Все объекты», «Новый объект») do not. */
      readonly object?: boolean | undefined;
      /** The two figures, drawn as badges after the name. Absent: no badge. */
      readonly figures?: readonly [RowFigure, RowFigure] | undefined;
      /** The row's accessible name where the badges would make the text say less than the row means. */
      readonly name?: string | undefined;
    }
  | { readonly kind: 'action'; readonly label: string; readonly onChoose?: (() => void) | undefined };

export interface ObjectMenuProps {
  /** The button's accessible name. */
  readonly label: string;
  /** The button's tooltip. */
  readonly title?: string | undefined;
  /** What the button shows. */
  readonly trigger: ReactNode;
  /** Shown above the items, outside the menu role. */
  readonly header?: ReactNode | undefined;
  /** At least one: a menu with nothing in it cannot take focus. */
  readonly items: readonly [ObjectMenuItem, ...ObjectMenuItem[]];
}

/** What the island attaches to the view. A static render passes none. */
export interface ObjectMenuBindings {
  readonly rootRef?: Ref<HTMLDivElement> | undefined;
  readonly triggerRef?: Ref<HTMLButtonElement> | undefined;
  readonly itemRef?: ((index: number) => (element: HTMLElement | null) => void) | undefined;
  readonly onTriggerClick?: (() => void) | undefined;
  readonly onTriggerKeyDown?: ((event: KeyboardEvent<HTMLButtonElement>) => void) | undefined;
  readonly onMenuKeyDown?: ((event: KeyboardEvent<HTMLUListElement>) => void) | undefined;
  readonly onItemFocus?: ((index: number) => void) | undefined;
  readonly onItemChosen?: (() => void) | undefined;
}

export type ObjectMenuViewProps = ObjectMenuProps & {
  readonly state: MenuState;
  /** The button's `id`, which labels the menu. */
  readonly triggerId: string;
  /** The menu's `id`, which the button's `aria-controls` names. */
  readonly menuId: string;
  readonly bindings?: ObjectMenuBindings | undefined;
};

function Badges({ figures }: { readonly figures: readonly [RowFigure, RowFigure] }) {
  return (
    <span className={styles.figures} data-object-figures="">
      {figures.map((figure) => (
        <span
          className={`am-badge ${figure.key === 'not_run' ? 'am-badge--degraded' : 'am-badge--active'} ${styles.figure}`}
          title={figure.title}
          aria-hidden="true"
          data-object-figure={figure.key}
          key={figure.key}
        >
          {figure.count}
        </span>
      ))}
    </span>
  );
}

export function ObjectMenuView({ label, title, trigger, header, items, state, triggerId, menuId, bindings }: ObjectMenuViewProps) {
  return (
    <div className="am-menu" ref={bindings?.rootRef}>
      <button
        type="button"
        className="am-menu__trigger"
        id={triggerId}
        ref={bindings?.triggerRef}
        aria-haspopup="menu"
        aria-expanded={state.open}
        aria-controls={menuId}
        aria-label={label}
        title={title}
        onClick={bindings?.onTriggerClick}
        onKeyDown={bindings?.onTriggerKeyDown}
      >
        {trigger}
      </button>
      <div className="am-menu__popup" hidden={!state.open}>
        {header !== undefined ? <div className="am-menu__header">{header}</div> : null}
        <ul className="am-menu__list" role="menu" id={menuId} aria-labelledby={triggerId} onKeyDown={bindings?.onMenuKeyDown}>
          {items.map((item, index) => (
            <li className="am-menu__entry" role="none" key={`${item.kind}:${item.kind === 'link' ? item.href : ''}:${item.label}`}>
              {item.kind === 'link' ? (
                <Link
                  className={item.object === true ? `am-menu__item ${styles.object}` : 'am-menu__item'}
                  role="menuitem"
                  tabIndex={-1}
                  href={item.href}
                  aria-current={item.current === true ? 'true' : undefined}
                  aria-label={item.figures === undefined ? undefined : item.name}
                  ref={bindings?.itemRef?.(index)}
                  onFocus={() => bindings?.onItemFocus?.(index)}
                  onClick={() => bindings?.onItemChosen?.()}
                >
                  {item.figures === undefined ? (
                    item.label
                  ) : (
                    <>
                      <span className={styles.name}>{item.label}</span>
                      <Badges figures={item.figures} />
                    </>
                  )}
                  {item.current === undefined ? null : (
                    <span className="am-menu__check" aria-hidden="true">{item.current ? '✓' : ''}</span>
                  )}
                </Link>
              ) : (
                <button
                  type="button"
                  className="am-menu__item"
                  role="menuitem"
                  tabIndex={-1}
                  ref={bindings?.itemRef?.(index)}
                  onFocus={() => bindings?.onItemFocus?.(index)}
                  onClick={() => {
                    bindings?.onItemChosen?.();
                    item.onChoose?.();
                  }}
                >
                  {item.label}
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function ObjectMenu(props: ObjectMenuProps) {
  const id = useId();
  const triggerId = `${id}trigger`;
  const menuId = `${id}menu`;
  const [state, setState] = useState<MenuState>(MENU_CLOSED);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<(HTMLElement | null)[]>([]);
  // Focus asked for by the event that OPENED the menu: its items are `hidden` until that
  // render commits, and a hidden element cannot take focus.
  const pendingFocus = useRef<MenuFocus>(null);
  const count = props.items.length;

  const focusNow = (focus: MenuFocus): void => {
    if (focus === null) return;
    if (focus.target === 'trigger') triggerRef.current?.focus();
    else itemRefs.current[focus.index]?.focus();
  };

  const apply = (transition: MenuTransition, native?: { preventDefault(): void }): void => {
    if (transition.preventDefault && native !== undefined) native.preventDefault();
    if (transition.state.open && !state.open) pendingFocus.current = transition.focus;
    else focusNow(transition.focus);
    setState(transition.state);
  };

  const dispatch = (event: MenuEvent, native?: { preventDefault(): void }): void =>
    apply(menuTransition(state, event, count), native);

  useEffect(() => {
    if (!state.open) return undefined;
    focusNow(pendingFocus.current);
    pendingFocus.current = null;
    // While open, a pointer pressed or focus arriving anywhere outside closes it.
    const onOutside = (event: Event): void => {
      const root = rootRef.current;
      if (root !== null && event.target instanceof Node && !root.contains(event.target)) {
        setState(menuTransition({ open: true, active: null }, { type: 'outside' }, count).state);
      }
    };
    document.addEventListener('pointerdown', onOutside);
    document.addEventListener('focusin', onOutside);
    return () => {
      document.removeEventListener('pointerdown', onOutside);
      document.removeEventListener('focusin', onOutside);
    };
    // `focusNow` reads refs only; re-subscribing on every render would buy nothing.
  }, [state.open, count]);

  return (
    <ObjectMenuView
      {...props}
      state={state}
      triggerId={triggerId}
      menuId={menuId}
      bindings={{
        rootRef,
        triggerRef,
        itemRef: (index) => (element: HTMLElement | null) => {
          itemRefs.current[index] = element;
        },
        onTriggerClick: () => dispatch({ type: 'trigger-click' }),
        onTriggerKeyDown: (event) => dispatch({ type: 'trigger-key', key: event.key }, event),
        onMenuKeyDown: (event) => dispatch({ type: 'item-key', key: event.key }, event),
        onItemFocus: (index) => dispatch({ type: 'item-focus', index }),
        onItemChosen: () => dispatch({ type: 'chosen' }),
      }}
    />
  );
}
