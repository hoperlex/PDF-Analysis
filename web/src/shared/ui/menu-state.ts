/**
 * The keyboard and open/close logic of `Menu`, as one pure function.
 *
 * The client island in `menu.tsx` turns a browser event into a `MenuEvent`, asks
 * `menuTransition` what follows, and applies the answer: the new state, where focus goes, and
 * whether the key's own default action must be suppressed. Every rule of the pattern lives
 * here, so the node test environment, which has no DOM, drives each of them
 * (`web/tests/unit/ui/menu.test.ts`).
 *
 * ## The pattern
 *
 * The WAI-ARIA Authoring Practices *menu button*: a `<button aria-haspopup="menu"
 * aria-expanded aria-controls>` that opens a `role="menu"` of `role="menuitem"` entries.
 * The account menu is one — Профиль, Сменить пароль, Выйти — and unlike the navigation
 * groups it is a set of COMMANDS, which is what `role="menu"` is for.
 *
 * On the trigger:
 *   click                   closed → open, focus on the first item; open → closed, focus on the trigger
 *   Enter, Space, ArrowDown open, focus on the first item
 *   ArrowUp                 open, focus on the last item
 *   Escape                  (open) closed, focus on the trigger
 *
 * On an item:
 *   ArrowDown / ArrowUp     next / previous item, wrapping at either end
 *   Home / End              first / last item
 *   Escape                  closed, focus back on the trigger
 *   Tab, Shift+Tab          closed, and the browser moves focus on as it would anyway
 *   Enter                   the item's own activation (a link follows, a submit button posts),
 *                           which arrives as `chosen`
 *
 * And anywhere: an item chosen closes the menu and returns focus to the trigger; a pointer
 * pressed or focus arriving outside the menu closes it without moving focus.
 *
 * NOT IMPLEMENTED, and named so nobody reads it as an oversight: type-ahead (a printable
 * character moving to the next item that starts with it), which the pattern marks optional
 * and which a three-item menu does not need; and Space as an activation key on a LINK item,
 * also optional — Space on the submit item activates it natively.
 */

import { assertNever } from '@/shared/lib';

export interface MenuState {
  readonly open: boolean;
  /** The index of the item that holds focus while the menu is open; `null` when closed. */
  readonly active: number | null;
}

export const MENU_CLOSED: MenuState = { open: false, active: null };

/** Where focus goes after the event, or `null` for nowhere new. */
export type MenuFocus =
  | { readonly target: 'trigger' }
  | { readonly target: 'item'; readonly index: number }
  | null;

export type MenuEvent =
  /** The trigger was clicked. Enter and Space are handled as keys first, so this is a pointer. */
  | { readonly type: 'trigger-click' }
  /** A key went down on the trigger. */
  | { readonly type: 'trigger-key'; readonly key: string }
  /** A key went down on the item that holds focus. */
  | { readonly type: 'item-key'; readonly key: string }
  /** An item received focus by some other road than the arrow keys (a pointer, a script). */
  | { readonly type: 'item-focus'; readonly index: number }
  /** An item was activated: a link was followed or the submit item was pressed. */
  | { readonly type: 'chosen' }
  /** A pointer went down, or focus arrived, outside the menu. */
  | { readonly type: 'outside' };

export interface MenuTransition {
  readonly state: MenuState;
  readonly focus: MenuFocus;
  /**
   * The island calls `preventDefault`: the key's own action must not also run — an arrow key
   * would scroll the page, and Enter or Space on the trigger would arrive a second time as a
   * click and close the menu it had just opened.
   */
  readonly preventDefault: boolean;
}

const TRIGGER: MenuFocus = { target: 'trigger' };

function openAt(index: number): MenuTransition {
  return {
    state: { open: true, active: index },
    focus: { target: 'item', index },
    preventDefault: true,
  };
}

function closed(focus: MenuFocus, preventDefault: boolean): MenuTransition {
  return { state: MENU_CLOSED, focus, preventDefault };
}

function unchanged(state: MenuState): MenuTransition {
  return { state, focus: null, preventDefault: false };
}

/**
 * The next state of a menu of `count` items.
 *
 * A menu with no items cannot be opened: there would be nothing to put focus on. The island's
 * props make that unrepresentable; this keeps the function total anyway.
 */
export function menuTransition(state: MenuState, event: MenuEvent, count: number): MenuTransition {
  if (count < 1) return unchanged(MENU_CLOSED);
  const last = count - 1;

  switch (event.type) {
    case 'trigger-click':
      if (state.open) return closed(TRIGGER, false);
      return { ...openAt(0), preventDefault: false };

    case 'trigger-key':
      switch (event.key) {
        case 'Enter':
        case ' ':
        case 'ArrowDown':
          return openAt(0);
        case 'ArrowUp':
          return openAt(last);
        case 'Escape':
          return state.open ? closed(TRIGGER, true) : unchanged(state);
        default:
          return unchanged(state);
      }

    case 'item-key': {
      if (!state.open) return unchanged(state);
      const current = state.active ?? 0;
      switch (event.key) {
        case 'ArrowDown':
          return openAt(current === last ? 0 : current + 1);
        case 'ArrowUp':
          return openAt(current === 0 ? last : current - 1);
        case 'Home':
          return openAt(0);
        case 'End':
          return openAt(last);
        case 'Escape':
          return closed(TRIGGER, true);
        case 'Tab':
          return closed(null, false);
        default:
          return unchanged(state);
      }
    }

    case 'item-focus':
      if (!state.open || event.index < 0 || event.index > last) return unchanged(state);
      return { state: { open: true, active: event.index }, focus: null, preventDefault: false };

    case 'chosen':
      return closed(TRIGGER, false);

    case 'outside':
      return state.open ? closed(null, false) : unchanged(state);

    default:
      return assertNever(event, 'menuTransition');
  }
}
