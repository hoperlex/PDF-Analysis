'use client';

/**
 * `Menu` — the account menu: a menu button (the WAI-ARIA *menu button* pattern; the keys
 * and what each does are in `menu-state.ts`).
 *
 * Two layers, as `Disclosure` has:
 *
 * - `MenuView` is pure markup from props and a `MenuState`. The contrast census renders it
 *   open (`web/tests/unit/styles/screens.ts`), and the unit tests read the attributes the
 *   pattern requires off it.
 * - `Menu` is the client island: it holds the state, turns browser events into
 *   `menuTransition` calls and applies the answer, moving focus itself. Its server render is
 *   the view's closed state, and a unit test holds the two equal.
 *
 * ## Items
 *
 * An item is a link or a form-submit control. `Выйти` must stay a POST to the session's own
 * door — a link that "signed out" would be a GET that changes state — so the submit item is a
 * `<button type="submit">` inside its own `<form method="post">`, and it is the button, not the
 * form, that carries `role="menuitem"`. Every item has `tabindex="-1"`: focus reaches items
 * by the arrow keys, and Tab leaves the menu instead of walking it.
 *
 * ## The trigger
 *
 * Its content is the caller's — the avatar, for the account menu — and its accessible name is
 * `label`, because an avatar is a pair of letters and not a name. The menu itself is labelled
 * by the trigger. An optional `header` sits above the items and outside `role="menu"`, since a
 * menu may hold only items: that is where the account's name, address and roles go.
 */

import Link from 'next/link';
import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent, ReactNode, Ref } from 'react';

import type { MenuEvent, MenuFocus, MenuState, MenuTransition } from './menu-state';
import { MENU_CLOSED, menuTransition } from './menu-state';

export type MenuItem =
  | { readonly kind: 'link'; readonly label: string; readonly href: string }
  /** A POST to `action`, from a submit control of its own form. */
  | { readonly kind: 'submit'; readonly label: string; readonly action: string };

export interface MenuProps {
  /** The trigger's accessible name, e.g. the account's name. */
  readonly label: string;
  /** What the trigger shows: the avatar, for the account menu. */
  readonly trigger: ReactNode;
  /** Shown above the items, outside the menu role. */
  readonly header?: ReactNode | undefined;
  /** At least one: a menu with nothing in it cannot take focus. */
  readonly items: readonly [MenuItem, ...MenuItem[]];
}

/** What the island attaches to the view. A static render passes none. */
export interface MenuBindings {
  readonly rootRef?: Ref<HTMLDivElement> | undefined;
  readonly triggerRef?: Ref<HTMLButtonElement> | undefined;
  readonly itemRef?: ((index: number) => (element: HTMLElement | null) => void) | undefined;
  readonly onTriggerClick?: (() => void) | undefined;
  readonly onTriggerKeyDown?: ((event: KeyboardEvent<HTMLButtonElement>) => void) | undefined;
  readonly onMenuKeyDown?: ((event: KeyboardEvent<HTMLUListElement>) => void) | undefined;
  readonly onItemFocus?: ((index: number) => void) | undefined;
  readonly onItemChosen?: (() => void) | undefined;
}

export type MenuViewProps = MenuProps & {
  readonly state: MenuState;
  /** The trigger's `id`, which labels the menu. */
  readonly triggerId: string;
  /** The menu's `id`, which the trigger's `aria-controls` names. */
  readonly menuId: string;
  readonly bindings?: MenuBindings | undefined;
};

export function MenuView({
  label,
  trigger,
  header,
  items,
  state,
  triggerId,
  menuId,
  bindings,
}: MenuViewProps) {
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
        onClick={bindings?.onTriggerClick}
        onKeyDown={bindings?.onTriggerKeyDown}
      >
        {trigger}
      </button>
      <div className="am-menu__popup" hidden={!state.open}>
        {header !== undefined ? <div className="am-menu__header">{header}</div> : null}
        <ul
          className="am-menu__list"
          role="menu"
          id={menuId}
          aria-labelledby={triggerId}
          onKeyDown={bindings?.onMenuKeyDown}
        >
          {items.map((item, index) => (
            <li className="am-menu__entry" role="none" key={`${item.kind}:${item.label}`}>
              {item.kind === 'link' ? (
                <Link
                  className="am-menu__item"
                  role="menuitem"
                  tabIndex={-1}
                  href={item.href}
                  ref={bindings?.itemRef?.(index)}
                  onFocus={() => bindings?.onItemFocus?.(index)}
                  onClick={() => bindings?.onItemChosen?.()}
                >
                  {item.label}
                </Link>
              ) : (
                <form className="am-menu__form" method="post" action={item.action}>
                  <button
                    type="submit"
                    className="am-menu__item"
                    role="menuitem"
                    tabIndex={-1}
                    ref={bindings?.itemRef?.(index)}
                    onFocus={() => bindings?.onItemFocus?.(index)}
                    onClick={bindings?.onItemChosen}
                  >
                    {item.label}
                  </button>
                </form>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function Menu(props: MenuProps) {
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
    <MenuView
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
