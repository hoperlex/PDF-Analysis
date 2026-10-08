/**
 * `Menu` — the account menu (`W50-SHELL-UI`), the WAI-ARIA menu button pattern.
 *
 * As for the disclosure: the MARKUP is read off server renders (the island closed, the view
 * open), and the LOGIC is `menuTransition`, the pure function the island calls for every
 * event, driven key by key. That focus really lands where the transition says — and that the
 * document listener really hears an outside press — is a browser's to show, first in
 * `W50-SHELL-FRAME` and `W50-QA-01`.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { MENU_CLOSED, Menu, menuTransition } from '@/shared/ui';
import type { MenuEvent, MenuItem, MenuProps, MenuState } from '@/shared/ui';
import { MenuView } from '@/shared/ui/menu';

import { descendants, parseMarkup } from '../styles/contrast';
import type { Element } from '../styles/contrast';

const ITEMS: readonly [MenuItem, ...MenuItem[]] = [
  { kind: 'link', label: 'Профиль', href: '/account' },
  { kind: 'link', label: 'Сменить пароль', href: '/account/password' },
  { kind: 'action', label: 'История версий' },
  { kind: 'submit', label: 'Выйти', action: '/bff/v1/session/end' },
];

const PROPS: MenuProps = {
  label: 'Учётная запись: Петрова А. С.',
  trigger: 'ПА',
  header: 'Петрова А. С.',
  items: ITEMS,
};

const COUNT = ITEMS.length;
const LAST = COUNT - 1;

function tree(markup: string): Element[] {
  return descendants(parseMarkup(markup));
}

/** The control that carries `aria-haspopup`: the menu's trigger, whatever its tag. */
function trigger(elements: readonly Element[]): Element {
  const found = elements.filter((el) => el.attrs.has('aria-haspopup'));
  expect(found.length, 'exactly one element carries aria-haspopup').toBe(1);
  return found[0] as Element;
}

const island = (): string => renderToStaticMarkup(createElement(Menu, PROPS));

const view = (state: MenuState): string =>
  renderToStaticMarkup(
    createElement(MenuView, { ...PROPS, state, triggerId: 'acct-trigger', menuId: 'acct-menu' }),
  );

const OPEN: MenuState = { open: true, active: 0 };

// ===================================================================== the markup

describe('the menu button and its menu', () => {
  it('its trigger is a real <button type="button"> with aria-haspopup="menu"', () => {
    for (const markup of [island(), view(MENU_CLOSED), view(OPEN)]) {
      const button = trigger(tree(markup));
      expect(button.tag).toBe('button');
      expect(button.attrs.get('type')).toBe('button');
      expect(button.attrs.get('aria-haspopup')).toBe('menu');
      expect(button.attrs.get('aria-label')).toBe(PROPS.label);
    }
  });

  it('aria-controls names the role="menu" element, which the trigger labels', () => {
    for (const markup of [island(), view(MENU_CLOSED), view(OPEN)]) {
      const elements = tree(markup);
      const button = trigger(elements);
      const controls = button.attrs.get('aria-controls');
      expect(controls, 'the trigger has no aria-controls').toBeTruthy();
      const menu = elements.find((el) => el.attrs.get('id') === controls);
      expect(menu, `aria-controls="${controls}" names no element`).toBeDefined();
      expect((menu as Element).attrs.get('role')).toBe('menu');
      expect((menu as Element).attrs.get('aria-labelledby')).toBe(button.attrs.get('id'));
    }
  });

  it('is closed by default, and the island renders exactly the closed view', () => {
    const markup = island();
    const elements = tree(markup);
    const button = trigger(elements);
    expect(button.attrs.get('aria-expanded')).toBe('false');
    const popup = elements.find((el) => el.classes.has('am-menu__popup')) as Element;
    expect(popup.attrs.has('hidden')).toBe(true);
    const closed = renderToStaticMarkup(
      createElement(MenuView, {
        ...PROPS,
        state: MENU_CLOSED,
        triggerId: button.attrs.get('id') as string,
        menuId: button.attrs.get('aria-controls') as string,
      }),
    );
    expect(markup).toBe(closed);
  });

  it('open, the popup is shown and aria-expanded says so', () => {
    const elements = tree(view(OPEN));
    expect(trigger(elements).attrs.get('aria-expanded')).toBe('true');
    const popup = elements.find((el) => el.classes.has('am-menu__popup')) as Element;
    expect(popup.attrs.has('hidden')).toBe(false);
  });

  it('every item is a menuitem out of the tab order, inside a presentational list item', () => {
    const elements = tree(view(OPEN));
    const menu = elements.find((el) => el.attrs.get('role') === 'menu') as Element;
    const entries = menu.children;
    expect(entries.map((li) => [li.tag, li.attrs.get('role')])).toEqual(
      ITEMS.map(() => ['li', 'none']),
    );
    const items = elements.filter((el) => el.attrs.get('role') === 'menuitem');
    expect(items.length).toBe(COUNT);
    for (const item of items) expect(item.attrs.get('tabindex')).toBe('-1');
    // The menu holds items and nothing else: the header sits outside it.
    expect(descendants(menu).some((el) => el.classes.has('am-menu__header'))).toBe(false);
    expect(elements.some((el) => el.classes.has('am-menu__header'))).toBe(true);
  });

  it('a link navigates, an action is a button, and sign-out is a POST', () => {
    const items = tree(view(OPEN)).filter((el) => el.attrs.get('role') === 'menuitem');
    expect(items.map((el) => el.tag)).toEqual(['a', 'a', 'button', 'button']);
    expect(items.slice(0, 2).map((el) => el.attrs.get('href'))).toEqual(['/account', '/account/password']);
    expect(items[2]?.attrs.get('type')).toBe('button');
    const signOut = items[3] as Element;
    expect(signOut.attrs.get('type')).toBe('submit');
    const form = signOut.parent as Element;
    expect([form.tag, form.attrs.get('method'), form.attrs.get('action')]).toEqual([
      'form',
      'post',
      '/bff/v1/session/end',
    ]);
  });

  it('renders no header when none is given', () => {
    const markup = renderToStaticMarkup(
      createElement(MenuView, {
        label: 'Меню',
        trigger: 'М',
        items: ITEMS,
        state: OPEN,
        triggerId: 't',
        menuId: 'm',
      }),
    );
    expect(markup).not.toContain('am-menu__header');
  });
});

// ====================================================================== the logic

/** Run a sequence of events from a state, returning every transition. */
function run(from: MenuState, events: readonly MenuEvent[]) {
  const out = [];
  let state = from;
  for (const event of events) {
    const next = menuTransition(state, event, COUNT);
    out.push(next);
    state = next.state;
  }
  return out;
}

const key = (k: string): MenuEvent => ({ type: 'item-key', key: k });
const onTrigger = (k: string): MenuEvent => ({ type: 'trigger-key', key: k });

describe('menuTransition: opening from the trigger', () => {
  it('Enter, Space and ArrowDown open on the first item and suppress the key', () => {
    for (const k of ['Enter', ' ', 'ArrowDown']) {
      expect({ k, t: menuTransition(MENU_CLOSED, onTrigger(k), COUNT) }).toEqual({
        k,
        t: { state: { open: true, active: 0 }, focus: { target: 'item', index: 0 }, preventDefault: true },
      });
    }
  });

  it('ArrowUp opens on the last item', () => {
    expect(menuTransition(MENU_CLOSED, onTrigger('ArrowUp'), COUNT)).toEqual({
      state: { open: true, active: LAST },
      focus: { target: 'item', index: LAST },
      preventDefault: true,
    });
  });

  it('a click opens on the first item, and a second click closes back onto the trigger', () => {
    const [opened, closed] = run(MENU_CLOSED, [{ type: 'trigger-click' }, { type: 'trigger-click' }]);
    expect(opened).toEqual({
      state: { open: true, active: 0 },
      focus: { target: 'item', index: 0 },
      preventDefault: false,
    });
    expect(closed).toEqual({ state: MENU_CLOSED, focus: { target: 'trigger' }, preventDefault: false });
  });

  it('any other key on the trigger does nothing and is left alone', () => {
    for (const k of ['Tab', 'Home', 'a', 'Escape']) {
      expect({ k, t: menuTransition(MENU_CLOSED, onTrigger(k), COUNT) }).toEqual({
        k,
        t: { state: MENU_CLOSED, focus: null, preventDefault: false },
      });
    }
  });

  it('a menu with no items cannot be opened', () => {
    for (const event of [onTrigger('Enter'), onTrigger('ArrowUp'), { type: 'trigger-click' } as const]) {
      expect(menuTransition(MENU_CLOSED, event, 0)).toEqual({
        state: MENU_CLOSED,
        focus: null,
        preventDefault: false,
      });
    }
  });
});

describe('menuTransition: moving inside the open menu', () => {
  it('ArrowDown walks forward and wraps from the last item to the first', () => {
    const steps = run(OPEN, [key('ArrowDown'), key('ArrowDown'), key('ArrowDown'), key('ArrowDown')]);
    expect(steps.map((s) => s.focus)).toEqual([
      { target: 'item', index: 1 },
      { target: 'item', index: 2 },
      { target: 'item', index: 3 },
      { target: 'item', index: 0 },
    ]);
    for (const s of steps) expect(s.preventDefault).toBe(true);
  });

  it('ArrowUp walks back and wraps from the first item to the last', () => {
    const steps = run(OPEN, [key('ArrowUp'), key('ArrowUp')]);
    expect(steps.map((s) => s.focus)).toEqual([
      { target: 'item', index: LAST },
      { target: 'item', index: LAST - 1 },
    ]);
  });

  it('Home and End jump to the first and the last item', () => {
    const [end, home] = run({ open: true, active: 1 }, [key('End'), key('Home')]);
    expect(end?.focus).toEqual({ target: 'item', index: LAST });
    expect(home?.focus).toEqual({ target: 'item', index: 0 });
  });

  it('an item focused by a pointer becomes the one the arrows move from', () => {
    const [focused, next] = run(OPEN, [{ type: 'item-focus', index: 2 }, key('ArrowUp')]);
    expect(focused).toEqual({ state: { open: true, active: 2 }, focus: null, preventDefault: false });
    expect(next?.focus).toEqual({ target: 'item', index: 1 });
  });

  it('Enter is the item\'s own: the link follows or the form posts, and nothing is suppressed', () => {
    expect(menuTransition(OPEN, key('Enter'), COUNT)).toEqual({
      state: OPEN,
      focus: null,
      preventDefault: false,
    });
  });
});

describe('menuTransition: closing, and where focus goes', () => {
  it('Escape on an item closes and returns focus to the trigger', () => {
    expect(menuTransition({ open: true, active: 2 }, key('Escape'), COUNT)).toEqual({
      state: MENU_CLOSED,
      focus: { target: 'trigger' },
      preventDefault: true,
    });
  });

  it('Escape on the trigger of an open menu closes it too', () => {
    expect(menuTransition(OPEN, onTrigger('Escape'), COUNT)).toEqual({
      state: MENU_CLOSED,
      focus: { target: 'trigger' },
      preventDefault: true,
    });
  });

  it('choosing an item closes the menu and returns focus to the trigger', () => {
    expect(menuTransition({ open: true, active: 1 }, { type: 'chosen' }, COUNT)).toEqual({
      state: MENU_CLOSED,
      focus: { target: 'trigger' },
      preventDefault: false,
    });
  });

  it('Tab leaves: the menu closes and the browser moves focus on, unsuppressed', () => {
    expect(menuTransition({ open: true, active: 1 }, key('Tab'), COUNT)).toEqual({
      state: MENU_CLOSED,
      focus: null,
      preventDefault: false,
    });
  });

  it('a press or focus outside closes it without moving focus', () => {
    expect(menuTransition(OPEN, { type: 'outside' }, COUNT)).toEqual({
      state: MENU_CLOSED,
      focus: null,
      preventDefault: false,
    });
    expect(menuTransition(MENU_CLOSED, { type: 'outside' }, COUNT)).toEqual({
      state: MENU_CLOSED,
      focus: null,
      preventDefault: false,
    });
  });

  it('a whole keyboard journey: open, walk, Escape, and back on the trigger', () => {
    const steps = run(MENU_CLOSED, [onTrigger('ArrowDown'), key('End'), key('ArrowDown'), key('Escape')]);
    expect(steps.map((s) => [s.state.open, s.focus])).toEqual([
      [true, { target: 'item', index: 0 }],
      [true, { target: 'item', index: LAST }],
      [true, { target: 'item', index: 0 }],
      [false, { target: 'trigger' }],
    ]);
  });
});
