/**
 * The document page's address when the reader changes tab or pass (`UI-B-02`, `D-440`).
 *
 * The proposals' decision filter (`?decision=`) and layout (`?layout=`) live in the address since lanes W3 and P10, but
 * the page writes `?tab=` and `?pass=` itself. A new pass must start from «Все» (the filter belongs to the pass, as it did
 * while it was the widget's state), and leaving «Оптимизация» drops all three, because they belong to that tab.
 */

import { describe, expect, it } from 'vitest';

import { passAddress, tabAddress } from '@/_pages/document-detail';

const HERE = new URLSearchParams('tab=optimisation&pass=opp_A&layout=table&decision=accept&keep=1');

describe('choosing a pass', () => {
  it('drops the decision filter and keeps the layout and the rest', () => {
    const next = passAddress(HERE, 'opp_B');
    expect(next.get('pass')).toBe('opp_B');
    expect(next.get('tab')).toBe('optimisation');
    expect(next.has('decision')).toBe(false);
    expect(next.get('layout')).toBe('table');
    expect(next.get('keep')).toBe('1');
  });

  it('drops the pass and the filter for the newest pass', () => {
    const next = passAddress(HERE, null);
    expect(next.has('pass')).toBe(false);
    expect(next.has('decision')).toBe(false);
  });

  it('does not change the address it was given', () => {
    passAddress(HERE, 'opp_B');
    expect(HERE.get('decision')).toBe('accept');
  });
});

describe('choosing a tab', () => {
  it('drops the pass, the layout and the decision filter when leaving «Оптимизация»', () => {
    const next = tabAddress(HERE, 'versions');
    expect(next.get('tab')).toBe('versions');
    for (const name of ['pass', 'layout', 'decision']) expect(next.has(name)).toBe(false);
    expect(next.get('keep')).toBe('1');
  });

  it('keeps them when staying on «Оптимизация»', () => {
    const next = tabAddress(HERE, 'optimisation');
    expect(next.get('pass')).toBe('opp_A');
    expect(next.get('layout')).toBe('table');
    expect(next.get('decision')).toBe('accept');
  });
});
