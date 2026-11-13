/**
 * The queue's pause state in the top strip (`R-151f`, `UI-PARITY-P0E`).
 *
 * The view is pure markup, rendered with `renderToStaticMarkup` (the suite has no DOM); the handlers are
 * read off the element tree. `offersPauseStatus` is the frame's gate: the strip carries the state exactly
 * where the «Очередь» screen is open, so a viewer (`R-150w`) and a guest never read it.
 */

import { createElement, isValidElement, type ReactElement, type ReactNode } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { offersPauseStatus } from '@/_app/navigation';
import { PAUSED_LABEL, PauseStatusView, UNREAD_LABEL } from '@/widgets/pause-status';
import type { PauseStatusViewProps } from '@/widgets/pause-status';

const noop = (): void => {};
const RUNNING = { paused: false, changed_at: '2026-11-05T10:00:00Z' };
const PAUSED = { paused: true, changed_at: '2026-11-05T10:00:00Z' };

function props(over: Partial<PauseStatusViewProps> = {}): PauseStatusViewProps {
  return {
    status: RUNNING, failed: false, mayToggle: false, asking: false, busy: false, error: null,
    onAsk: noop, onConfirm: noop, onCancel: noop, ...over,
  };
}

const html = (over: Partial<PauseStatusViewProps>): string => renderToStaticMarkup(createElement(PauseStatusView, props(over)));

function buttons(node: ReactNode, found: ReactElement<{ onClick?: () => void; children?: ReactNode }>[] = []) {
  if (Array.isArray(node)) node.forEach((child) => buttons(child, found));
  else if (isValidElement<{ children?: ReactNode; onClick?: () => void }>(node)) {
    if (node.type === 'button') found.push(node);
    buttons(node.props.children, found);
  }
  return found;
}

describe('the pause state in the top strip', () => {
  it('names a paused queue to every reader and links to «Очередь»', () => {
    const out = html({ status: PAUSED });
    expect(out).toContain(PAUSED_LABEL);
    expect(out).toContain('href="/queue"');
    expect(out).not.toContain('<button');
  });

  it('says nothing about a running queue to a reader who may not pause it', () => {
    expect(html({ status: RUNNING })).toBe('');
  });

  it('offers ONE «Пауза» button to an administrator on a running and on a paused queue; the way back is a menu item, not a second button', () => {
    for (const status of [RUNNING, PAUSED]) {
      const out = html({ status, mayToggle: true });
      expect(out.match(/aria-haspopup="menu"/g)).toHaveLength(1);
      expect(out).toContain('aria-label="Пауза"');
      expect(out).not.toContain('>Возобновить</button>');
    }
    expect(html({ status: PAUSED, mayToggle: true })).toContain('Выдача анализа — возобновить');
  });

  it('asks in place before it sends, and the confirmation calls the command', () => {
    let confirmed = 0;
    let cancelled = 0;
    const element = PauseStatusView(props({
      status: RUNNING, mayToggle: true, asking: true,
      onConfirm: () => { confirmed += 1; }, onCancel: () => { cancelled += 1; },
    }));
    const out = renderToStaticMarkup(element as ReactElement);
    expect(out).toContain('Приостановить выдачу задач?');
    const [confirm, cancel] = buttons(element);
    expect(confirm?.props.children).toBe('Приостановить');
    confirm?.props.onClick?.();
    cancel?.props.onClick?.();
    expect([confirmed, cancelled]).toEqual([1, 1]);
  });

  it('shows the refusal of a command and an unread state, never an invented one', () => {
    expect(html({ status: RUNNING, mayToggle: true, error: 'Недостаточно прав.' })).toContain('Недостаточно прав.');
    expect(html({ status: undefined, failed: true })).toContain(UNREAD_LABEL);
    expect(html({ status: undefined, failed: false })).toBe('');
  });
});

describe('who reads the pause state', () => {
  const subject = (roles: string[]) => ({ roles, isDefaultCredential: false, profileComplete: true });

  it('the queue is open to an expert and an administrator, so the strip reads it', () => {
    expect(offersPauseStatus(subject(['expert']))).toBe(true);
    expect(offersPauseStatus(subject(['admin']))).toBe(true);
  });

  it('a viewer and a guest never read it', () => {
    expect(offersPauseStatus(subject(['viewer']))).toBe(false);
    expect(offersPauseStatus(null)).toBe(false);
  });
});
