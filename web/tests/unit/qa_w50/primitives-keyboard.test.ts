/**
 * `W50-QA-01`, items 1–3 (node half) — the keyboard paths, the focus return and Escape,
 * through the two primitives' exported logic.
 *
 * `W50-PLAN.md` §3.5: the navigation groups are `Disclosure` (the APG disclosure pattern — a
 * `<button aria-expanded aria-controls>` opening a list of links, not `role="menu"`); the account
 * menu is `Menu` (the APG menu button — `aria-haspopup="menu"`, Escape, Arrow keys, Home/End, Tab
 * leaves, click outside closes, focus returns to the trigger).
 *
 * The node environment has no DOM, so this file drives the pure transition functions the
 * islands apply (`menuTransition`, `disclosureTransition`, both public in `@/shared/ui`) as
 * *paths*: a sequence of key presses from a closed control, with a model of where focus sits
 * after each step that applies a transition exactly as the plan says an island must (focus to
 * the trigger, to an item, or left where the browser puts it). Real focus movement, a real Tab
 * and a real outside click are browser facts; `tests/e2e/pc01/qa_w50/keyboard.mjs` drives the
 * same paths through the real frame.
 *
 * Written by QA from the plan, without the lane reports.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { MenuEvent, MenuState } from '@/shared/ui';
import { Disclosure, MENU_CLOSED, Menu, disclosureTransition, menuTransition } from '@/shared/ui';

// ============================================================================ Menu

/** Where focus is, as the plan's menu button pattern describes it. */
type Where = 'trigger' | `item:${number}` | 'moved-on-by-the-browser';

interface MenuWalk {
  state: MenuState;
  focus: Where;
  /** Whether each step asked the island to suppress the key's default action. */
  readonly prevented: boolean[];
}

/** The account menu has three items: Профиль, Сменить пароль, Выйти. */
const ITEMS = 3;

function startMenu(): MenuWalk {
  return { state: MENU_CLOSED, focus: 'trigger', prevented: [] };
}

/**
 * One key press (or other event) on the focused control, applied the way an island applies a
 * transition: focus moves where the transition says; `null` leaves it where the browser puts
 * it, which for Tab is somewhere after the menu.
 */
function press(walk: MenuWalk, key: string): MenuWalk {
  const event: MenuEvent =
    walk.focus === 'trigger' ? { type: 'trigger-key', key } : { type: 'item-key', key };
  return apply(walk, event, key === 'Tab');
}

function apply(walk: MenuWalk, event: MenuEvent, browserMovesFocus = false): MenuWalk {
  const next = menuTransition(walk.state, event, ITEMS);
  let focus: Where = walk.focus;
  if (next.focus !== null) focus = next.focus.target === 'trigger' ? 'trigger' : `item:${next.focus.index}`;
  else if (browserMovesFocus) focus = 'moved-on-by-the-browser';
  return { state: next.state, focus, prevented: [...walk.prevented, next.preventDefault] };
}

function walkMenu(keys: readonly string[], from: MenuWalk = startMenu()): MenuWalk {
  return keys.reduce(press, from);
}

describe('Menu: Enter and Space open, the arrows move, Home/End jump, Escape and Tab close', () => {
  it('Enter on the trigger opens the menu with focus on the first item', () => {
    const walk = walkMenu(['Enter']);
    expect(walk.state).toEqual({ open: true, active: 0 });
    expect(walk.focus).toBe('item:0');
    // Suppressed, or the same Enter would arrive again as a click and close it.
    expect(walk.prevented).toEqual([true]);
  });

  it('Space on the trigger opens the menu with focus on the first item', () => {
    const walk = walkMenu([' ']);
    expect(walk.state).toEqual({ open: true, active: 0 });
    expect(walk.focus).toBe('item:0');
    expect(walk.prevented).toEqual([true]);
  });

  it('ArrowDown on the trigger opens on the first item, ArrowUp on the last', () => {
    expect(walkMenu(['ArrowDown']).focus).toBe('item:0');
    expect(walkMenu(['ArrowUp']).focus).toBe('item:2');
    expect(walkMenu(['ArrowUp']).state).toEqual({ open: true, active: 2 });
  });

  it('ArrowDown and ArrowUp walk the items and wrap at both ends', () => {
    const focusAfterEach: Where[] = [];
    let walk = walkMenu(['Enter']);
    for (const key of ['ArrowDown', 'ArrowDown', 'ArrowDown', 'ArrowUp', 'ArrowUp', 'ArrowUp']) {
      walk = press(walk, key);
      focusAfterEach.push(walk.focus);
    }
    expect(focusAfterEach).toEqual(['item:1', 'item:2', 'item:0', 'item:2', 'item:1', 'item:0']);
    expect(walk.state.open).toBe(true);
    // Every arrow press is suppressed: an arrow that also scrolled the page would move it.
    expect(walk.prevented.every((value) => value)).toBe(true);
  });

  it('Home jumps to the first item and End to the last, from anywhere', () => {
    const walk = walkMenu(['Enter', 'ArrowDown', 'End']);
    expect(walk.focus).toBe('item:2');
    expect(press(walk, 'Home').focus).toBe('item:0');
    expect(press(press(walk, 'Home'), 'End').focus).toBe('item:2');
  });

  it('Escape on an item closes the menu and returns focus to the trigger', () => {
    for (const before of [['Enter'], ['Enter', 'ArrowDown'], ['ArrowUp'], ['Enter', 'End']]) {
      const walk = walkMenu([...before, 'Escape']);
      expect(walk.state, `after ${before.join(', ')}, Escape`).toEqual(MENU_CLOSED);
      expect(walk.focus, `after ${before.join(', ')}, Escape`).toBe('trigger');
    }
  });

  it('Escape on the trigger of an open menu closes it, and on a closed one does nothing', () => {
    const open = apply(startMenu(), { type: 'trigger-click' });
    expect(open.state.open).toBe(true);
    const closed = apply({ ...open, focus: 'trigger' }, { type: 'trigger-key', key: 'Escape' });
    expect(closed.state).toEqual(MENU_CLOSED);
    expect(closed.focus).toBe('trigger');
    const nothing = menuTransition(MENU_CLOSED, { type: 'trigger-key', key: 'Escape' }, ITEMS);
    expect(nothing).toEqual({ state: MENU_CLOSED, focus: null, preventDefault: false });
  });

  it('Tab leaves: the menu closes, focus is not pulled back, and the browser moves it on', () => {
    for (const before of [['Enter'], ['Enter', 'ArrowDown'], ['ArrowUp']]) {
      const walk = walkMenu([...before, 'Tab']);
      expect(walk.state, `after ${before.join(', ')}, Tab`).toEqual(MENU_CLOSED);
      expect(walk.focus, `after ${before.join(', ')}, Tab`).toBe('moved-on-by-the-browser');
      // Not suppressed: suppressing Tab would trap focus inside a closed menu.
      expect(walk.prevented.at(-1)).toBe(false);
    }
  });

  it('choosing an item closes the menu and returns focus to the trigger', () => {
    for (const before of [['Enter'], ['Enter', 'ArrowDown'], ['Enter', 'End']]) {
      const walk = apply(walkMenu(before), { type: 'chosen' });
      expect(walk.state, `after ${before.join(', ')}, chosen`).toEqual(MENU_CLOSED);
      expect(walk.focus, `after ${before.join(', ')}, chosen`).toBe('trigger');
      // The item's own activation (a link followed, a form posted) must not be cancelled.
      expect(walk.prevented.at(-1)).toBe(false);
    }
  });

  it('a pointer or focus outside closes the menu and leaves focus alone', () => {
    const walk = apply(walkMenu(['Enter', 'ArrowDown']), { type: 'outside' });
    expect(walk.state).toEqual(MENU_CLOSED);
    expect(walk.focus).toBe('item:1'); // unchanged by the transition: the browser owns it
    expect(menuTransition(MENU_CLOSED, { type: 'outside' }, ITEMS).state).toEqual(MENU_CLOSED);
  });

  it('a click on the trigger opens on the first item and a second click closes to the trigger', () => {
    const open = apply(startMenu(), { type: 'trigger-click' });
    expect(open.state).toEqual({ open: true, active: 0 });
    expect(open.focus).toBe('item:0');
    const closed = apply({ ...open, focus: 'trigger' }, { type: 'trigger-click' });
    expect(closed.state).toEqual(MENU_CLOSED);
    expect(closed.focus).toBe('trigger');
  });

  it('keys on items of a closed menu change nothing', () => {
    for (const key of ['ArrowDown', 'ArrowUp', 'Home', 'End', 'Escape', 'Tab']) {
      expect(menuTransition(MENU_CLOSED, { type: 'item-key', key }, ITEMS), key).toEqual({
        state: MENU_CLOSED,
        focus: null,
        preventDefault: false,
      });
    }
  });
});

describe('Menu, server-rendered: the attributes the pattern needs before any script runs', () => {
  const markup = renderToStaticMarkup(
    createElement(Menu, {
      label: 'Учётная запись: Проверка К. А.',
      trigger: 'ПК',
      items: [
        { kind: 'link', label: 'Профиль', href: '/account' },
        { kind: 'link', label: 'Сменить пароль', href: '/account/password' },
        { kind: 'submit', label: 'Выйти', action: '/bff/v1/session/end' },
      ],
    }),
  );

  it('the trigger is a button that says it opens a menu, closed, and names the menu it controls', () => {
    const trigger = /<button[^>]*class="am-menu__trigger"[^>]*>/.exec(markup)?.[0] ?? '';
    expect(trigger).toContain('type="button"');
    expect(trigger).toContain('aria-haspopup="menu"');
    expect(trigger).toContain('aria-expanded="false"');
    const controls = /aria-controls="([^"]+)"/.exec(trigger)?.[1];
    expect(controls).toBeDefined();
    expect(markup).toContain(`role="menu" id="${controls ?? ''}"`);
  });

  it('every item is a menuitem out of the tab order, so Tab leaves the menu instead of walking it', () => {
    const items = [...markup.matchAll(/<(a|button)[^>]*role="menuitem"[^>]*>/g)].map((m) => m[0]);
    expect(items).toHaveLength(3);
    for (const item of items) expect(item).toContain('tabindex="-1"');
  });

  it('the popup is hidden while closed', () => {
    expect(markup).toMatch(/<div class="am-menu__popup" hidden="">/);
  });
});

// ======================================================================= Disclosure

describe('Disclosure: Enter/Space toggle (a native button click), Escape closes and returns focus', () => {
  it('the button toggles it open and closed; the toggle moves no focus', () => {
    const opened = disclosureTransition(false, { type: 'toggle' });
    expect(opened).toEqual({ open: true, focus: null, handled: false });
    expect(disclosureTransition(true, { type: 'toggle' })).toEqual({ open: false, focus: null, handled: false });
  });

  it('Escape inside an open disclosure closes it, returns focus to its button and is consumed', () => {
    expect(disclosureTransition(true, { type: 'key', key: 'Escape' })).toEqual({
      open: false,
      focus: 'button',
      handled: true,
    });
  });

  it('Escape in a closed disclosure is not consumed, so it reaches the one around it', () => {
    expect(disclosureTransition(false, { type: 'key', key: 'Escape' })).toEqual({
      open: false,
      focus: null,
      handled: false,
    });
  });

  it('nested («Меню» around a group): one Escape closes one level, the next closes the outer', () => {
    // Inner group open inside the open «Меню»; focus inside the inner group's panel.
    let outer = true;
    let inner = true;
    let focus: 'inner-panel' | 'inner-button' | 'outer-button' = 'inner-panel';
    const escape = (): void => {
      // The key reaches the inner disclosure first; it bubbles to the outer one only when
      // the inner did not consume it.
      const atInner = disclosureTransition(inner, { type: 'key', key: 'Escape' });
      inner = atInner.open;
      if (atInner.focus === 'button') focus = 'inner-button';
      if (atInner.handled) return;
      const atOuter = disclosureTransition(outer, { type: 'key', key: 'Escape' });
      outer = atOuter.open;
      if (atOuter.focus === 'button') focus = 'outer-button';
    };
    escape();
    expect({ outer, inner, focus }).toEqual({ outer: true, inner: false, focus: 'inner-button' });
    escape();
    expect({ outer, inner, focus }).toEqual({ outer: false, inner: false, focus: 'outer-button' });
  });

  it('Tab leaving it (focus arriving outside) and a click outside both close it', () => {
    expect(disclosureTransition(true, { type: 'outside' })).toEqual({ open: false, focus: null, handled: false });
  });

  it('choosing a link inside it closes it', () => {
    expect(disclosureTransition(true, { type: 'navigate' })).toEqual({ open: false, focus: null, handled: false });
  });

  it('the arrows, Home, End and Tab are left to the browser: a group of links is walked with Tab', () => {
    // §3.5 / `disclosure-state.ts`: the APG disclosure pattern, not a menu; the arrows are
    // deliberately not taken over. Asserted, so a change to that decision is visible here.
    for (const key of ['ArrowDown', 'ArrowUp', 'Home', 'End', 'Tab', 'Enter', ' ']) {
      expect(disclosureTransition(true, { type: 'key', key }), key).toEqual({ open: true, focus: null, handled: false });
    }
  });
});

describe('Disclosure, server-rendered: a real button, closed, controlling a hidden panel', () => {
  const markup = renderToStaticMarkup(
    createElement(Disclosure, {
      label: 'Работа',
      links: [
        { href: '/projects', label: 'Проекты' },
        { href: '/dashboard', label: 'Дашборд' },
      ],
    }),
  );

  it('the trigger is a <button> with aria-expanded=false and aria-controls naming the panel', () => {
    const button = /<button[^>]*>/.exec(markup)?.[0] ?? '';
    expect(button).toContain('type="button"');
    expect(button).toContain('aria-expanded="false"');
    const controls = /aria-controls="([^"]+)"/.exec(button)?.[1];
    expect(controls).toBeDefined();
    expect(markup).toMatch(new RegExp(`id="${controls ?? '-'}"[^>]*hidden=""`));
  });

  it('the panel holds links, not menu items', () => {
    expect(markup).not.toContain('role="menu');
    expect([...markup.matchAll(/<a [^>]*href="([^"]+)"/g)].map((m) => m[1])).toEqual(['/projects', '/dashboard']);
  });
});
