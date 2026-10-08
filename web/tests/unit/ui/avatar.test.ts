/**
 * `Avatar` and the hash that colours it (`R-57`, `W50-SHELL-UI`).
 *
 * The property that matters most is the one a reviewer would only notice weeks later: the
 * colour follows the E-MAIL, so an account whose name is corrected keeps the colour its
 * colleagues know it by. A hash keyed on the name or the initials passes every other case
 * here, which is why the cases that pin the key come first.
 *
 * Every address is invented and under `example.test`.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import {
  AVATAR_PALETTE_SIZE,
  Avatar,
  AvatarInitialsError,
  avatarColourIndex,
  normaliseColourKey,
} from '@/shared/ui';
import type { AvatarProps } from '@/shared/ui';

import { parseMarkup } from '../styles/contrast';
import type { Element } from '../styles/contrast';

function circle(props: AvatarProps): Element {
  const root = parseMarkup(renderToStaticMarkup(createElement(Avatar, props)));
  expect(root.children.length).toBe(1);
  return root.children[0] as Element;
}

/** The pair an avatar renders, read off its class — what the stylesheet will paint. */
function pairOf(props: AvatarProps): string {
  const pairs = [...circle(props).classes].filter((name) => /^am-avatar--\d{2}$/.test(name));
  expect(pairs.length, 'exactly one colour modifier').toBe(1);
  return (pairs[0] as string).slice('am-avatar--'.length);
}

/** Two invented addresses whose colours differ, found rather than assumed. */
function twoAddressesOfDifferentColour(): readonly [string, string] {
  const first = 'petrova@example.test';
  for (let n = 1; n < 100; n += 1) {
    const other = `ivanov-${n}@example.test`;
    if (avatarColourIndex(other) !== avatarColourIndex(first)) return [first, other];
  }
  throw new Error('no second colour among a hundred addresses: the hash is not spreading');
}

// ========================================================== the key is the e-mail

describe('the colour is keyed on the e-mail, never on the name', () => {
  const [mine, theirs] = twoAddressesOfDifferentColour();

  it('a corrected name keeps its colour: same e-mail, different initials and label', () => {
    const before = pairOf({ initials: 'ПА', colourKey: mine, label: 'Петрова А. С.' });
    const after = pairOf({ initials: 'СА', colourKey: mine, label: 'Смирнова А. С.' });
    expect(after).toBe(before);
    // And the case is not vacuous: the two sets of initials hash apart, so an avatar keyed on
    // them would have changed colour here.
    expect(avatarColourIndex('СА')).not.toBe(avatarColourIndex('ПА'));
  });

  it('two accounts with the same initials are told apart by their addresses', () => {
    expect(pairOf({ initials: 'ПА', colourKey: mine })).not.toBe(
      pairOf({ initials: 'ПА', colourKey: theirs }),
    );
  });

  it('the rendered pair is the hash of the colour key, numbered from 01', () => {
    for (const key of [mine, theirs, 'admin', '']) {
      const expected = String(avatarColourIndex(key) + 1).padStart(2, '0');
      expect({ key, pair: pairOf({ initials: 'ПА', colourKey: key }) }).toEqual({ key, pair: expected });
    }
  });
});

// ================================================================= the hash itself

describe('avatarColourIndex', () => {
  it('is 32-bit FNV-1a modulo the palette, by the published test vectors', () => {
    // FNV-1a 32 of "", "a" and "foobar" are 0x811c9dc5, 0xe40c292c and 0xbf9cf968. Pinning
    // them pins the algorithm: a different hash would silently recolour every account.
    expect(avatarColourIndex('')).toBe(0x811c9dc5 % AVATAR_PALETTE_SIZE);
    expect(avatarColourIndex('a')).toBe(0xe40c292c % AVATAR_PALETTE_SIZE);
    expect(avatarColourIndex('foobar')).toBe(0xbf9cf968 % AVATAR_PALETTE_SIZE);
  });

  it('is deterministic: the same key gives the same index, every time', () => {
    const key = 'sidorova.e@example.test';
    const first = avatarColourIndex(key);
    for (let i = 0; i < 20; i += 1) expect(avatarColourIndex(key)).toBe(first);
  });

  it('folds case and surrounding space as the access boundary folds a login', () => {
    expect(normaliseColourKey('  Petrova@Example.TEST ')).toBe('petrova@example.test');
    expect(avatarColourIndex('  Petrova@Example.TEST ')).toBe(avatarColourIndex('petrova@example.test'));
    // Nothing else is folded: a different address is a different account.
    expect(normaliseColourKey('petrova+1@example.test')).toBe('petrova+1@example.test');
  });

  it('reaches every one of the fourteen colours', () => {
    const seen = new Set<number>();
    let tried = 0;
    while (seen.size < AVATAR_PALETTE_SIZE && tried < 1000) {
      tried += 1;
      seen.add(avatarColourIndex(`expert-${tried}@example.test`));
    }
    expect([...seen].sort((a, b) => a - b)).toEqual(
      Array.from({ length: AVATAR_PALETTE_SIZE }, (_, i) => i),
    );
    expect(tried, 'the hash needed far too many addresses to cover the palette').toBeLessThan(200);
  });

  it('gives a valid index for an empty key and for a legacy login that is not an address', () => {
    for (const key of ['', ' ', 'admin', 'проверяющий', 'a'.repeat(254)]) {
      const index = avatarColourIndex(key);
      expect({ key: key.slice(0, 12), valid: Number.isInteger(index) && index >= 0 && index < AVATAR_PALETTE_SIZE })
        .toEqual({ key: key.slice(0, 12), valid: true });
    }
  });
});

// ======================================================================= the circle

describe('the avatar renders its initials on its colour', () => {
  it('is decorative beside a visible name: aria-hidden, and no role', () => {
    const el = circle({ initials: 'ПА', colourKey: 'petrova@example.test' });
    expect(el.tag).toBe('span');
    expect(el.attrs.get('aria-hidden')).toBe('true');
    expect(el.attrs.has('role')).toBe(false);
    expect(el.attrs.has('aria-label')).toBe(false);
  });

  it('standing alone it is an image with the name it is given', () => {
    const el = circle({ initials: 'ПА', colourKey: 'petrova@example.test', label: 'Петрова А. С.' });
    expect(el.attrs.get('role')).toBe('img');
    expect(el.attrs.get('aria-label')).toBe('Петрова А. С.');
    expect(el.attrs.has('aria-hidden')).toBe(false);
  });

  it('shows the initials it is given, and the base class with one modifier', () => {
    const markup = renderToStaticMarkup(
      createElement(Avatar, { initials: 'ПА', colourKey: 'petrova@example.test' }),
    );
    expect(markup).toMatch(/^<span class="am-avatar am-avatar--\d{2}"[^>]*>ПА<\/span>$/);
  });

  it('never renders blank: empty initials are a broken promise upstream and are refused', () => {
    for (const initials of ['', '   ']) {
      expect(() =>
        renderToStaticMarkup(createElement(Avatar, { initials, colourKey: 'petrova@example.test' })),
      ).toThrow(AvatarInitialsError);
    }
  });
});
