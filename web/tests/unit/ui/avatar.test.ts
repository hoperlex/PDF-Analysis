/**
 * `Avatar` and the hash that colours it (`R-57`, `W50-SHELL-UI`, `AVATAR-PALETTE-01`).
 *
 * The property that matters most is the one a reviewer would only notice weeks later: the
 * colour follows the account's `user_uid`, so an account whose name is corrected, or whose
 * e-mail is changed, keeps the colour its colleagues know it by. A hash keyed on the name,
 * the initials or the e-mail passes every other case here, which is why the cases that pin
 * the key come first. (The frame test holds the same property one level up, with a session
 * whose e-mail changes; an `Avatar` takes only the key, so here the key is what varies.)
 *
 * Every uid is invented: `usr_` and 26 characters of the contract's alphabet.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import {
  AVATAR_PALETTE_SIZE,
  Avatar,
  AvatarColourKeyError,
  AvatarInitialsError,
  avatarColourIndex,
} from '@/shared/ui';
import type { AvatarProps } from '@/shared/ui';

import { parseMarkup } from '../styles/contrast';
import type { Element } from '../styles/contrast';

const UID = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

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

/** Two invented uids whose colours differ, found rather than assumed. */
function twoUidsOfDifferentColour(): readonly [string, string] {
  for (let n = 1; n < 100; n += 1) {
    const other = `usr_01J9ZQ8K7NHVXW3T2R5M6P4Q${String(n).padStart(2, '0')}`;
    if (avatarColourIndex(other) !== avatarColourIndex(UID)) return [UID, other];
  }
  throw new Error('no second colour among a hundred uids: the hash is not spreading');
}

// ===================================================== the key is the user_uid

describe('the colour is keyed on the user_uid, never on the name', () => {
  const [mine, theirs] = twoUidsOfDifferentColour();

  it('a corrected name keeps its colour: same uid, different initials and label', () => {
    const before = pairOf({ initials: 'ПА', colourKey: mine, label: 'Петрова А. С.' });
    const after = pairOf({ initials: 'СА', colourKey: mine, label: 'Смирнова А. С.' });
    expect(after).toBe(before);
    // And the case is not vacuous: the two sets of initials hash apart, so an avatar keyed on
    // them would have changed colour here.
    expect(avatarColourIndex('СА')).not.toBe(avatarColourIndex('ПА'));
  });

  it('two accounts with the same initials are told apart by their uids', () => {
    expect(pairOf({ initials: 'ПА', colourKey: mine })).not.toBe(
      pairOf({ initials: 'ПА', colourKey: theirs }),
    );
  });

  it('the rendered pair is the hash of the colour key, numbered from 01', () => {
    for (const key of [mine, theirs, 'a', 'проверяющий']) {
      const expected = String(avatarColourIndex(key) + 1).padStart(2, '0');
      expect({ key, pair: pairOf({ initials: 'ПА', colourKey: key }) }).toEqual({ key, pair: expected });
    }
  });

  it('wears a pinned pair for a pinned uid, so a swapped key or hash shows up as a recolouring', () => {
    // Computed outside this code base, with an independent FNV-1a over UTF-8, modulo twelve.
    // The six uids are the ones the owner saw in the preview sheet, in pair order.
    const pinned: readonly (readonly [string, string])[] = [
      ['usr_KBYQMBMEMS8PWSEBZD9ADG44KY', '01'],
      ['usr_1M1WCFXRAXCW0H0JMTBP320X38', '04'],
      ['usr_4TZPFAGEX73V0QQ99GDQ5FSVKY', '06'],
      ['usr_4Y24ZNW985ZD9WZRZPCJQAMCW9', '08'],
      ['usr_7WSCSVCK33HHANZ8GQ9CDA4QY2', '10'],
      ['usr_5CWZK6GVCY7A0Q7YRV6WV2VJT8', '12'],
    ];
    for (const [uid, pair] of pinned) {
      expect({ uid, pair: pairOf({ initials: 'ПА', colourKey: uid }) }).toEqual({ uid, pair });
    }
  });
});

// ================================================================= the hash itself

describe('avatarColourIndex', () => {
  it('is 32-bit FNV-1a modulo the palette, by the published test vectors', () => {
    // FNV-1a 32 of "a" and "foobar" are 0xe40c292c and 0xbf9cf968 (the empty string, 0x811c9dc5,
    // is refused as a key, below). Pinning them pins the algorithm: a different hash would
    // silently recolour every account.
    expect(avatarColourIndex('a')).toBe(0xe40c292c % AVATAR_PALETTE_SIZE);
    expect(avatarColourIndex('foobar')).toBe(0xbf9cf968 % AVATAR_PALETTE_SIZE);
    // A uid, hashed by an independent implementation: 0x24d2ee28.
    expect(avatarColourIndex(UID)).toBe(0x24d2ee28 % AVATAR_PALETTE_SIZE);
  });

  it('is deterministic: the same key gives the same index, every time', () => {
    const first = avatarColourIndex(UID);
    for (let i = 0; i < 20; i += 1) expect(avatarColourIndex(UID)).toBe(first);
  });

  it('hashes the key verbatim: case and surrounding space make a different key', () => {
    // The uid is what the API wrote, so nothing is folded. By independent FNV-1a these three
    // strings hash to 0x24d2ee28, 0xd8e44fc8 and 0xbeeaa102: three different pairs of twelve.
    expect(avatarColourIndex(UID)).toBe(0x24d2ee28 % AVATAR_PALETTE_SIZE);
    expect(avatarColourIndex(UID.toLowerCase())).toBe(0xd8e44fc8 % AVATAR_PALETTE_SIZE);
    expect(avatarColourIndex(` ${UID} `)).toBe(0xbeeaa102 % AVATAR_PALETTE_SIZE);
    expect(new Set([UID, UID.toLowerCase(), ` ${UID} `].map(avatarColourIndex)).size).toBe(3);
  });

  it('reaches every one of the twelve colours', () => {
    expect(AVATAR_PALETTE_SIZE).toBe(12);
    const seen = new Set<number>();
    let tried = 0;
    while (seen.size < AVATAR_PALETTE_SIZE && tried < 1000) {
      tried += 1;
      seen.add(avatarColourIndex(`usr_01J9ZQ8K7NHVXW3T2R5M6${String(tried).padStart(5, '0')}`));
    }
    expect([...seen].sort((a, b) => a - b)).toEqual(
      Array.from({ length: AVATAR_PALETTE_SIZE }, (_, i) => i),
    );
    expect(tried, 'the hash needed far too many uids to cover the palette').toBeLessThan(200);
  });

  it('gives a valid index for any non-blank key, including a long one and a non-ASCII one', () => {
    for (const key of ['a', 'проверяющий', 'a'.repeat(254), UID]) {
      const index = avatarColourIndex(key);
      expect({ key: key.slice(0, 12), valid: Number.isInteger(index) && index >= 0 && index < AVATAR_PALETTE_SIZE })
        .toEqual({ key: key.slice(0, 12), valid: true });
    }
  });

  it('refuses an empty or blank key loudly: no uid is a broken promise upstream, not a colour', () => {
    for (const key of ['', ' ', '\t\n']) {
      expect(() => avatarColourIndex(key), JSON.stringify(key)).toThrow(AvatarColourKeyError);
      expect(() => renderToStaticMarkup(createElement(Avatar, { initials: 'ПА', colourKey: key })), JSON.stringify(key)).toThrow(
        AvatarColourKeyError,
      );
    }
  });
});

// ======================================================================= the circle

describe('the avatar renders its initials on its colour', () => {
  it('is decorative beside a visible name: aria-hidden, and no role', () => {
    const el = circle({ initials: 'ПА', colourKey: UID });
    expect(el.tag).toBe('span');
    expect(el.attrs.get('aria-hidden')).toBe('true');
    expect(el.attrs.has('role')).toBe(false);
    expect(el.attrs.has('aria-label')).toBe(false);
  });

  it('standing alone it is an image with the name it is given', () => {
    const el = circle({ initials: 'ПА', colourKey: UID, label: 'Петрова А. С.' });
    expect(el.attrs.get('role')).toBe('img');
    expect(el.attrs.get('aria-label')).toBe('Петрова А. С.');
    expect(el.attrs.has('aria-hidden')).toBe(false);
  });

  it('shows the initials it is given, and the base class with one modifier', () => {
    const markup = renderToStaticMarkup(
      createElement(Avatar, { initials: 'ПА', colourKey: UID }),
    );
    expect(markup).toMatch(/^<span class="am-avatar am-avatar--\d{2}"[^>]*>ПА<\/span>$/);
  });

  it('never renders blank: empty initials are a broken promise upstream and are refused', () => {
    for (const initials of ['', '   ']) {
      expect(() =>
        renderToStaticMarkup(createElement(Avatar, { initials, colourKey: UID })),
      ).toThrow(AvatarInitialsError);
    }
  });
});
