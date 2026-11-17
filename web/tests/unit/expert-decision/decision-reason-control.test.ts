/**
 * The decision field and the verdict mark of the `expert-decision` entity (`UIP-S06-01`).
 *
 * Static markup cannot press anything, so this suite calls the field as a function with `useState` replaced by indexed cells
 * (the way `decision-panel-handlers.test.ts` calls the panel), reads the element tree it returns and calls the handlers it
 * finds there. That is the component's own code on the browser's own call path, with nothing but the state hook stood in for.
 *
 * What it pins:
 *   - the text of the field goes to the handler of ✓ and of ✕, trimmed, and an empty field hands over an empty string;
 *   - ✓ and ✕ are held while a press is on its way, and the button of the verdict already in force is held and marked pressed;
 *   - every button has a name, and so has the field;
 *   - the line under the field is a status when it says «Записано» and an alert when it is a refusal;
 *   - the extra slot stands after ✕, and the mark is ✓, ✕ or a dash with the word as its name and no contract value as prose.
 */

import type { ReactElement, ReactNode } from 'react';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const cells = vi.hoisted(() => ({ values: [] as unknown[], index: 0 }));

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useState: (initial: unknown) => {
      const at = cells.index;
      cells.index += 1;
      if (!(at in cells.values)) cells.values[at] = initial;
      return [
        cells.values[at],
        (next: unknown) => {
          cells.values[at] = typeof next === 'function' ? (next as (v: unknown) => unknown)(cells.values[at]) : next;
        },
      ];
    },
  };
});

import { DecisionReasonControl, VerdictMark } from '@/entities/expert-decision';
import type { DecisionReasonControlProps } from '@/entities/expert-decision';
import { VERDICT_VALUES } from '@/shared/api';
import type { Verdict } from '@/shared/api';

type Props = Record<string, unknown> & {
  children?: ReactNode;
  onChange?: (event: unknown) => void;
  onClick?: () => void;
  disabled?: boolean;
};

/** Every host element of the tree whose props satisfy `match`. */
function findAll(node: ReactNode, match: (type: unknown, props: Props) => boolean): ReactElement<Props>[] {
  if (node === null || node === undefined || typeof node === 'boolean') return [];
  if (Array.isArray(node)) return node.flatMap((child) => findAll(child as ReactNode, match));
  if (typeof node !== 'object' || !('props' in node)) return [];
  const element = node as ReactElement<Props>;
  const own = match(element.type, element.props) ? [element] : [];
  return [...own, ...findAll(element.props.children, match)];
}

function props(over: Partial<DecisionReasonControlProps> = {}): DecisionReasonControlProps {
  return { verdict: 'pending', sending: null, note: null, onAccept: vi.fn(), onReject: vi.fn(), ...over };
}

/** Run the field once, as React would on a render, with the cells as they now stand. */
function tree(p: DecisionReasonControlProps): ReactElement<Props> {
  cells.index = 0;
  return DecisionReasonControl(p) as ReactElement<Props>;
}

function button(p: DecisionReasonControlProps, intent: 'accept' | 'reject'): ReactElement<Props> {
  const [found] = findAll(tree(p), (type, pr) => type === 'button' && pr['data-intent'] === intent);
  if (found === undefined) throw new Error(`no ${intent} button`);
  return found;
}

function field(p: DecisionReasonControlProps): ReactElement<Props> {
  const [found] = findAll(tree(p), (type) => type === 'input');
  if (found === undefined) throw new Error('no field');
  return found;
}

function type(p: DecisionReasonControlProps, value: string): void {
  field(p).props.onChange?.({ target: { value } });
}

beforeEach(() => {
  cells.values = [];
  cells.index = 0;
});

describe('the text of the field goes to the handler', () => {
  it('hands the typed reason to ✓, trimmed', () => {
    const p = props();
    type(p, '  Пункт подтверждён по листу 3  ');
    button(p, 'accept').props.onClick?.();
    expect(p.onAccept).toHaveBeenCalledExactlyOnceWith('Пункт подтверждён по листу 3');
    expect(p.onReject).not.toHaveBeenCalled();
  });

  it('hands the typed reason to ✕, trimmed', () => {
    const p = props();
    type(p, 'Не относится к разделу ');
    button(p, 'reject').props.onClick?.();
    expect(p.onReject).toHaveBeenCalledExactlyOnceWith('Не относится к разделу');
    expect(p.onAccept).not.toHaveBeenCalled();
  });

  it('hands over an empty string, not nothing and not a placeholder, when the field is empty or blank', () => {
    const p = props();
    button(p, 'accept').props.onClick?.();
    type(p, '   ');
    button(p, 'reject').props.onClick?.();
    expect(p.onAccept).toHaveBeenCalledExactlyOnceWith('');
    expect(p.onReject).toHaveBeenCalledExactlyOnceWith('');
  });

  it('shows what was typed in the field, and keeps it after the press (a press is not a clear)', () => {
    const p = props();
    type(p, 'причина');
    button(p, 'accept').props.onClick?.();
    expect(field(p).props.value).toBe('причина');
  });
});

describe('✓ and ✕ are held when a press cannot or should not be made', () => {
  it('offers both on a decision that is still open', () => {
    const p = props();
    expect([button(p, 'accept').props.disabled, button(p, 'reject').props.disabled]).toEqual([false, false]);
  });

  it('holds both while a press is on its way, and shows which one is on its way', () => {
    for (const sending of ['accept', 'reject'] as const) {
      const p = props({ sending });
      expect([button(p, 'accept').props.disabled, button(p, 'reject').props.disabled]).toEqual([true, true]);
      expect(button(p, sending).props.children).toBe('…');
    }
  });

  it('holds the button of the verdict already in force, marks it pressed, and leaves the other one open', () => {
    const accepted = props({ verdict: 'accepted' });
    expect([button(accepted, 'accept').props.disabled, button(accepted, 'reject').props.disabled]).toEqual([true, false]);
    expect([button(accepted, 'accept').props['aria-pressed'], button(accepted, 'reject').props['aria-pressed']]).toEqual([true, false]);
    const rejected = props({ verdict: 'rejected' });
    expect([button(rejected, 'accept').props.disabled, button(rejected, 'reject').props.disabled]).toEqual([false, true]);
    expect([button(rejected, 'accept').props['aria-pressed'], button(rejected, 'reject').props['aria-pressed']]).toEqual([false, true]);
  });

  it('holds neither on the two verdicts that are not a decision', () => {
    for (const verdict of ['pending', 'needs_manual_review'] as const) {
      const p = props({ verdict });
      expect([button(p, 'accept').props.disabled, button(p, 'reject').props.disabled]).toEqual([false, false]);
      expect([button(p, 'accept').props['aria-pressed'], button(p, 'reject').props['aria-pressed']]).toEqual([false, false]);
    }
  });
});

describe('every control has a name', () => {
  it('names ✓ «Принять», ✕ «Отклонить» and the field «Причина»', () => {
    const p = props();
    expect(button(p, 'accept').props['aria-label']).toBe('Принять');
    expect(button(p, 'reject').props['aria-label']).toBe('Отклонить');
    expect(field(p).props['aria-label']).toBe('Причина');
  });

  it('gives every button and every field of the markup a name', () => {
    const markup = renderToStaticMarkup(createElement(DecisionReasonControl, props({ extra: createElement('button', { type: 'button', 'aria-label': 'На доработку' }, '↺') })));
    const controls = markup.match(/<(?:button|input)\b[^>]*>/g) ?? [];
    expect(controls).toHaveLength(4); // ✓, ✕, the slot's own button, the field
    for (const tag of controls) expect(tag).toMatch(/aria-label="[^"]+"/);
    // The glyphs are the sight; none of them is the only name a button has.
    expect(markup).toContain('>✓<');
    expect(markup).toContain('>✕<');
  });

  it('is a single-line text field, not a text area', () => {
    const markup = renderToStaticMarkup(createElement(DecisionReasonControl, props()));
    expect(markup).toContain('<input');
    expect(markup).toContain('type="text"');
    expect(markup).not.toContain('<textarea');
  });
});

describe('the line under the field', () => {
  it('says nothing when nothing was pressed', () => {
    const markup = renderToStaticMarkup(createElement(DecisionReasonControl, props()));
    expect(markup).not.toContain('role="status"');
    expect(markup).not.toContain('role="alert"');
  });

  it('is a status when the press was recorded, and an alert when it was refused or failed', () => {
    const ok = renderToStaticMarkup(createElement(DecisionReasonControl, props({ note: { tone: 'ok', text: 'Записано' } })));
    expect(ok).toContain('role="status"');
    expect(ok).toContain('Записано');
    const fail = renderToStaticMarkup(createElement(DecisionReasonControl, props({ note: { tone: 'fail', text: 'Перед принятием выберите критичность. Ничего не отправлено.' } })));
    expect(fail).toContain('role="alert"');
    expect(fail).toContain('Перед принятием выберите критичность. Ничего не отправлено.');
  });
});

describe('the slot for a screen’s further actions', () => {
  it('draws what it is given after ✕, in the same row of buttons, and nothing when it is given nothing', () => {
    const withExtra = renderToStaticMarkup(createElement(DecisionReasonControl, props({ extra: createElement('span', { 'data-extra': '' }, 'ещё') })));
    expect(withExtra.indexOf('data-intent="reject"')).toBeLessThan(withExtra.indexOf('data-extra'));
    expect(withExtra.indexOf('data-extra')).toBeLessThan(withExtra.indexOf('<input'));
    expect(renderToStaticMarkup(createElement(DecisionReasonControl, props()))).not.toContain('data-extra');
  });
});

describe('the verdict mark', () => {
  const mark = (verdict: Verdict): string => renderToStaticMarkup(createElement(VerdictMark, { verdict }));

  it('is ✓ for an accepted verdict and ✕ for a rejected one, named by the word', () => {
    expect(mark('accepted')).toContain('>✓<');
    expect(mark('accepted')).toContain('aria-label="Принято"');
    expect(mark('rejected')).toContain('>✕<');
    expect(mark('rejected')).toContain('aria-label="Отклонено"');
  });

  it('is a dash where nothing is decided, and says which of the two it is', () => {
    expect(mark('pending')).toContain('>—<');
    expect(mark('pending')).toContain('aria-label="Не решено"');
    expect(mark('needs_manual_review')).toContain('>—<');
    expect(mark('needs_manual_review')).toContain('aria-label="Нужен ручной разбор"');
  });

  it('is an image with a name, carries the contract value on a data attribute only, and is never a severity', () => {
    for (const verdict of VERDICT_VALUES) {
      const markup = mark(verdict);
      expect(markup).toContain('role="img"');
      expect(markup).toContain(`data-verdict="${verdict}"`);
      expect(markup).not.toContain('data-severity');
      // The contract value is not prose: outside the class names (hashed from the module's own words) it appears once, as the attribute.
      expect(markup.replace(/ class="[^"]*"/g, '').split(verdict).length - 1).toBe(1);
    }
  });

  it('shows a value outside the closed set as a fault, not as a dash', () => {
    const markup = mark('approved' as Verdict);
    expect(markup).toContain('data-closed-vocabulary-fault="verdict"');
    expect(markup).toContain('role="alert"');
    expect(markup).not.toContain('>—<');
    expect(markup).not.toContain('approved');
  });
});
