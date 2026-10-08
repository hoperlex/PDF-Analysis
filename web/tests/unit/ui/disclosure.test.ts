/**
 * `Disclosure` — the navigation group (`W50-SHELL-UI`).
 *
 * Two halves, because the frontend runs in `environment: 'node'` with no DOM library:
 *
 *   the MARKUP   is read off a server render of the island (closed, which is its only server
 *                state) and of `DisclosureView` (open), parsed into an element tree;
 *   the LOGIC    is `disclosureTransition`, the pure function the island calls for every
 *                event, driven directly.
 *
 * What a real browser adds — that focus actually lands, that the document listener actually
 * hears an outside press — is exercised first by `W50-SHELL-FRAME` and `W50-QA-01`.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { Disclosure, disclosureTransition } from '@/shared/ui';
import type { DisclosureLink, DisclosureProps } from '@/shared/ui';
import { DisclosureView } from '@/shared/ui/disclosure';

import { descendants, parseMarkup } from '../styles/contrast';
import type { Element } from '../styles/contrast';

const LINKS: readonly DisclosureLink[] = [
  { href: '/projects', label: 'Проекты', current: true },
  { href: '/dashboard', label: 'Дашборд' },
  { href: '/section-optimisation', label: 'Оптимизация разделов' },
];

const PROPS: DisclosureProps = { label: 'Работа', links: LINKS };

function tree(markup: string): Element[] {
  return descendants(parseMarkup(markup));
}

/** The control that carries `aria-expanded`: the disclosure's trigger, whatever its tag. */
function trigger(elements: readonly Element[]): Element {
  const found = elements.filter((el) => el.attrs.has('aria-expanded'));
  expect(found.length, 'exactly one element carries aria-expanded').toBe(1);
  return found[0] as Element;
}

function byId(elements: readonly Element[], id: string): Element | undefined {
  return elements.find((el) => el.attrs.get('id') === id);
}

const island = (props: DisclosureProps = PROPS): string =>
  renderToStaticMarkup(createElement(Disclosure, props));

const view = (open: boolean, props: DisclosureProps = PROPS): string =>
  renderToStaticMarkup(createElement(DisclosureView, { ...props, open, panelId: 'nav-work' }));

// ===================================================================== the markup

describe('the disclosure is a button that controls a panel of links', () => {
  it('its trigger is a real <button type="button">, in the island and in the view', () => {
    for (const markup of [island(), view(false), view(true)]) {
      const button = trigger(tree(markup));
      expect(button.tag).toBe('button');
      expect(button.attrs.get('type')).toBe('button');
      expect(button.classes.has('am-disclosure__button')).toBe(true);
    }
  });

  it('aria-controls names the panel, which is always in the markup', () => {
    for (const markup of [island(), view(false), view(true)]) {
      const elements = tree(markup);
      const controls = trigger(elements).attrs.get('aria-controls');
      expect(controls, 'the trigger has no aria-controls').toBeTruthy();
      const panel = byId(elements, controls as string);
      expect(panel, `aria-controls="${controls}" names no element`).toBeDefined();
      expect((panel as Element).classes.has('am-disclosure__panel')).toBe(true);
    }
  });

  it('is closed by default: the island renders aria-expanded="false" and a hidden panel', () => {
    const elements = tree(island());
    const button = trigger(elements);
    expect(button.attrs.get('aria-expanded')).toBe('false');
    const panel = byId(elements, button.attrs.get('aria-controls') as string) as Element;
    expect(panel.attrs.has('hidden')).toBe(true);
  });

  it('the island renders exactly the closed view, so the census measures what ships', () => {
    const markup = island();
    const panelId = trigger(tree(markup)).attrs.get('aria-controls') as string;
    const closed = renderToStaticMarkup(
      createElement(DisclosureView, { ...PROPS, open: false, panelId }),
    );
    expect(markup).toBe(closed);
  });

  it('open, the panel is shown and aria-expanded says so', () => {
    const elements = tree(view(true));
    const button = trigger(elements);
    expect(button.attrs.get('aria-expanded')).toBe('true');
    expect((byId(elements, 'nav-work') as Element).attrs.has('hidden')).toBe(false);
  });

  it('holds links, and no menu role anywhere: the items are links, not commands', () => {
    for (const markup of [island(), view(true)]) {
      const elements = tree(markup);
      const roles = elements.filter((el) => el.attrs.has('role')).map((el) => el.attrs.get('role'));
      expect(roles, 'a disclosure carries no role="menu" / "menuitem"').toEqual([]);
      const anchors = elements.filter((el) => el.tag === 'a');
      expect(anchors.map((a) => a.attrs.get('href'))).toEqual(LINKS.map((link) => link.href));
      // In a list, so a screen reader announces how many there are.
      for (const a of anchors) {
        expect(a.parent?.tag).toBe('li');
        expect(a.parent?.parent?.tag).toBe('ul');
      }
    }
  });

  it('marks the current page on its link and the current group on its button', () => {
    const elements = tree(view(true, { ...PROPS, current: true }));
    const current = elements.filter((el) => el.attrs.has('aria-current'));
    expect(current.map((el) => [el.tag, el.attrs.get('aria-current')])).toEqual([
      ['button', 'true'],
      ['a', 'page'],
    ]);
    // And nothing is current when nothing is.
    const none = tree(view(true, { label: 'Знания', links: [{ href: '/blocks', label: 'Блоки' }] }));
    expect(none.filter((el) => el.attrs.has('aria-current'))).toEqual([]);
  });

  it('holds arbitrary content instead of links, which is how the stacked menu nests groups', () => {
    const nested = createElement(DisclosureView, {
      label: 'Знания',
      links: [{ href: '/knowledge-base', label: 'База знаний' }],
      layout: 'inline',
      open: true,
      panelId: 'nav-knowledge',
    });
    const markup = renderToStaticMarkup(
      createElement(DisclosureView, { label: 'Меню', children: nested, open: true, panelId: 'nav-all' }),
    );
    const elements = tree(markup);
    const buttons = elements.filter((el) => el.tag === 'button');
    expect(buttons.map((b) => b.attrs.get('aria-controls'))).toEqual(['nav-all', 'nav-knowledge']);
    const inner = elements.find((el) => el.classes.has('am-disclosure--inline'));
    expect(inner, 'the inline layout carries its modifier').toBeDefined();
    expect(byId(elements, 'nav-all')?.children[0]).toBe(inner);
  });

  it('carries its layout and alignment as modifiers, and none by default', () => {
    const root = (markup: string): Element => tree(markup)[0] as Element;
    expect([...root(view(false)).classes]).toEqual(['am-disclosure']);
    expect([...root(view(false, { ...PROPS, align: 'end' })).classes]).toEqual([
      'am-disclosure',
      'am-disclosure--end',
    ]);
  });
});

// ====================================================================== the logic

describe('disclosureTransition: what each event does', () => {
  it('the button toggles, and moves no focus', () => {
    expect(disclosureTransition(false, { type: 'toggle' })).toEqual({ open: true, focus: null, handled: false });
    expect(disclosureTransition(true, { type: 'toggle' })).toEqual({ open: false, focus: null, handled: false });
  });

  it('Escape closes an open disclosure and returns focus to its button', () => {
    expect(disclosureTransition(true, { type: 'key', key: 'Escape' })).toEqual({
      open: false,
      focus: 'button',
      handled: true,
    });
  });

  it('Escape on a closed disclosure is not consumed, so it reaches the one around it', () => {
    expect(disclosureTransition(false, { type: 'key', key: 'Escape' })).toEqual({
      open: false,
      focus: null,
      handled: false,
    });
  });

  it('takes over no other key: the arrows, Tab, Enter and Space keep their own meaning', () => {
    for (const key of ['ArrowDown', 'ArrowUp', 'Home', 'End', 'Tab', 'Enter', ' ', 'a']) {
      for (const open of [true, false]) {
        expect({ key, open, t: disclosureTransition(open, { type: 'key', key }) }).toEqual({
          key,
          open,
          t: { open, focus: null, handled: false },
        });
      }
    }
  });

  it('a press or focus outside closes it, and so does following a link inside it', () => {
    for (const type of ['outside', 'navigate'] as const) {
      expect(disclosureTransition(true, { type })).toEqual({ open: false, focus: null, handled: false });
      expect(disclosureTransition(false, { type })).toEqual({ open: false, focus: null, handled: false });
    }
  });

  it('nested: one Escape closes one level, from the inside out', () => {
    // The stacked «Меню» (outer) holding an open group (inner). The island stops a handled
    // event at the inner disclosure; an unhandled one bubbles to the outer.
    let inner = true;
    let outer = true;
    const press = (): ('inner' | 'outer' | null) => {
      const a = disclosureTransition(inner, { type: 'key', key: 'Escape' });
      inner = a.open;
      if (a.handled) return 'inner';
      const b = disclosureTransition(outer, { type: 'key', key: 'Escape' });
      outer = b.open;
      return b.handled ? 'outer' : null;
    };
    expect([press(), inner, outer]).toEqual(['inner', false, true]);
    expect([press(), inner, outer]).toEqual(['outer', false, false]);
    expect([press(), inner, outer]).toEqual([null, false, false]);
  });
});
