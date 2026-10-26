/**
 * `AR-V3-BETA-PACK-STATUS-WEB-FIX-02`: the instrument itself. `live-render.ts` stands in for a
 * browser's click, and a browser dispatches no click to a disabled button. A `press` that called
 * `onClick` whatever the button's state let a test press a button the page had disabled and pass.
 */

import { createElement, useState } from 'react';
import { afterEach, describe, expect, it } from 'vitest';

import { mountLive } from './live-render';
import type { LiveRender } from './live-render';

let live: LiveRender | null = null;

afterEach(async () => {
  await live?.unmount();
  live = null;
});

describe('press', () => {
  it('delivers the click to an enabled button and says so', async () => {
    const pressed: string[] = [];
    live = await mountLive(createElement('button', { onClick: () => pressed.push('x') }, 'Отправить'));
    expect(await live.press('Отправить')).toBe(true);
    expect(pressed).toEqual(['x']);
  });

  it('delivers nothing to a disabled button, and says so', async () => {
    const pressed: string[] = [];
    live = await mountLive(createElement('button', { disabled: true, onClick: () => pressed.push('x') }, 'Отправить'));
    expect(live.markup()).toContain('disabled=""');
    expect(await live.press('Отправить')).toBe(false);
    expect(pressed, 'a disabled button took a press').toEqual([]);
  });

  it('follows the button as its state changes: refused while disabled, delivered once enabled', async () => {
    const pressed: string[] = [];
    function Once() {
      const [sent, setSent] = useState(false);
      return createElement(
        'button',
        {
          disabled: sent,
          onClick: () => {
            pressed.push('x');
            setSent(true);
          },
        },
        'Отправить',
      );
    }
    live = await mountLive(createElement(Once));
    expect(await live.press('Отправить')).toBe(true);
    expect(live.markup()).toContain('disabled=""');
    expect(await live.press('Отправить')).toBe(false);
    expect(pressed).toEqual(['x']);
  });

  it('still throws when there is not exactly one such button', async () => {
    live = await mountLive(createElement('div', null, createElement('button', null, 'А'), createElement('button', null, 'А')));
    await expect(live.press('А')).rejects.toThrow('expected one button «А», found 2');
    await expect(live.press('Б')).rejects.toThrow('expected one button «Б», found 0');
  });
});
