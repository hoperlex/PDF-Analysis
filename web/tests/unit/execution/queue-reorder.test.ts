/**
 * `UI-B-52`: a waiting job is moved by drag or by Alt+↑ / Alt+↓, and a move is one priority command.
 *
 * The arithmetic is pure and is tested as such: the dispatcher takes queued jobs by `priority DESC, created_at, job_id`, so the
 * priority that puts one job into a slot is a function of its neighbours — the nearest one to its own, changing no other job —
 * and a slot no single priority can reach is refused in words, never approximated. The rendered list shows the handle only to the
 * roles that may set a priority and only where there is something to reorder, with the hint and the polite live region.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ExecutionQueueItem, Role } from '@/shared/api';
import type { RunWorker } from '@/entities/execution';
import {
  ExecutionQueue, PRIORITY_MAX, PRIORITY_MIN, keyboardTarget, planReorder, reorderRefusalText, takenBefore,
} from '@/widgets/execution-queue';

import { QUEUE_WORK } from './queue-work';

const noop = () => {};

function job(id: string, priority: number, minute: number, state = 'queued'): ExecutionQueueItem {
  return {
    job_id: `job_${id}`, run_id: `run_${id}`, state, priority,
    created_at: `2026-10-09T10:${String(minute).padStart(2, '0')}:00Z`, available_at: '2026-10-09T10:00:00Z',
    queue_position: minute, ...QUEUE_WORK,
  } as ExecutionQueueItem;
}

const BOTH = { top: true, bottom: true } as const;

describe('the dispatcher’s order, as the screen reads it', () => {
  it('takes the higher priority first, then the older, then the smaller identity', () => {
    expect(takenBefore(job('a', 5, 9), job('b', 4, 1))).toBe(true);
    expect(takenBefore(job('a', 4, 1), job('b', 4, 2))).toBe(true);
    expect(takenBefore(job('a', 4, 2), job('b', 4, 1))).toBe(false);
    expect(takenBefore(job('a', 4, 1), job('b', 4, 1))).toBe(true);
    expect(takenBefore(job('b', 4, 1), job('a', 4, 1))).toBe(false);
  });
});

describe('the priority that puts a job into a slot', () => {
  const queue = [job('a', 3, 1), job('b', 2, 2), job('c', 1, 3), job('d', 0, 4)];

  it('keeps a job where it already is', () => {
    expect(planReorder(queue, 'job_b', 1, BOTH)).toEqual({ kind: 'keep' });
    expect(planReorder(queue, 'job_b', 99, BOTH)).toEqual({ kind: 'set', priority: -1 });
  });

  it('moves a job up to the top with the lowest priority that takes it there', () => {
    // d (0) to the first slot: above a (3) — the priority must beat 3 or tie it as the older; d is newer, so it needs 4.
    expect(planReorder(queue, 'job_d', 0, BOTH)).toEqual({ kind: 'set', priority: 4 });
    // c (1) to the first slot, the same.
    expect(planReorder(queue, 'job_c', 0, BOTH)).toEqual({ kind: 'set', priority: 4 });
  });

  it('moves a job between two others with a priority strictly between, the nearest to its own', () => {
    const wide = [job('a', 10, 1), job('b', 6, 2), job('c', 0, 3), job('d', 9, 4)].sort((x, y) => (takenBefore(x, y) ? -1 : 1));
    // order: a(10) d(9) b(6) c(0). Move c between a and d: needs < 10 (or 10 with a older: c is newer, so < 10 or = 10 only if a older -> a older, so 10 is ok) and > 9 or = 9 with c older (c is older? minute 3 < d minute 4: yes).
    const plan = planReorder(wide, 'job_c', 1, BOTH);
    expect(plan.kind).toBe('set');
    // The nearest priority to c's own (0) that sorts after a and before d: 9 (ties d, and c is the older).
    expect(plan).toEqual({ kind: 'set', priority: 9 });
  });

  it('moves a job down to the end with the nearest priority at or under the last one', () => {
    // a (3) to the last slot: after d (0): priority must be < 0, or 0 if d is older — a (minute 1) is older than d, so 0 sorts a BEFORE d: needs -1.
    expect(planReorder(queue, 'job_a', 3, BOTH)).toEqual({ kind: 'set', priority: -1 });
  });

  it('never leaves the range of priorities', () => {
    const top = [job('a', PRIORITY_MAX, 1), job('b', 0, 2)];
    // b above a would need a priority over 100 (b is newer): refused, nothing invented.
    expect(planReorder(top, 'job_b', 0, BOTH)).toEqual({ kind: 'refused', reason: 'no_room' });
    const bottom = [job('a', 0, 1), job('b', PRIORITY_MIN, 2)];
    // a below b would need a priority under -100 (a is older, so it ties b first): -100 ties b with a older → a stays first → refused.
    expect(planReorder(bottom, 'job_a', 1, BOTH)).toEqual({ kind: 'refused', reason: 'no_room' });
  });

  it('refuses a slot two neighbours at one priority leave no room in, and changes no other job', () => {
    // a, c at priority 5 (a older than c); b (3) wants to go between them: needs 5 and between by age — b is newest, so no priority works.
    const rows = [job('a', 5, 1), job('c', 5, 3), job('b', 3, 5)];
    expect(planReorder(rows, 'job_b', 1, BOTH)).toEqual({ kind: 'refused', reason: 'no_room' });
    expect(reorderRefusalText('no_room')).toContain('Другие задачи не менялись');
  });

  it('refuses an edge whose neighbour is on another page, and allows it where the page is the end', () => {
    expect(planReorder(queue, 'job_c', 0, { top: false, bottom: true })).toEqual({ kind: 'refused', reason: 'edge_above' });
    expect(planReorder(queue, 'job_a', 3, { top: true, bottom: false })).toEqual({ kind: 'refused', reason: 'edge_below' });
    expect(planReorder(queue, 'job_c', 1, { top: false, bottom: false }).kind).toBe('set');
    expect(reorderRefusalText('edge_above')).toContain('предыдущей страницы');
    expect(reorderRefusalText('edge_below')).toContain('следующей страницы');
  });

  it('knows no job that is not waiting', () => {
    expect(planReorder(queue, 'job_zzz', 0, BOTH)).toEqual({ kind: 'refused', reason: 'not_queued' });
  });

  it('puts the job where the plan says, when the dispatcher’s own order is applied to the result', () => {
    const rows = [job('a', 3, 1), job('b', 2, 2), job('c', 1, 3), job('d', 0, 4)];
    for (let from = 0; from < rows.length; from += 1) {
      for (let to = 0; to < rows.length; to += 1) {
        const moving = rows[from]!;
        const plan = planReorder(rows, moving.job_id, to, BOTH);
        if (plan.kind === 'refused') continue;
        const priority = plan.kind === 'set' ? plan.priority : moving.priority;
        const after = rows.map((row) => (row.job_id === moving.job_id ? { ...row, priority } : row))
          .sort((x, y) => (takenBefore(x, y) ? -1 : 1));
        expect(after.findIndex((row) => row.job_id === moving.job_id), `${from} -> ${to}`).toBe(to);
      }
    }
  });
});

describe('the keyboard alternative', () => {
  const queue = [job('a', 3, 1), job('b', 2, 2), job('c', 1, 3)];

  it('moves one place with Alt+↑ and Alt+↓ and ignores every other key', () => {
    expect(keyboardTarget(queue, 'job_b', 'ArrowUp', true)).toBe(0);
    expect(keyboardTarget(queue, 'job_b', 'ArrowDown', true)).toBe(2);
    expect(keyboardTarget(queue, 'job_b', 'ArrowUp', false)).toBeNull();
    expect(keyboardTarget(queue, 'job_b', 'Enter', true)).toBeNull();
    expect(keyboardTarget(queue, 'job_zzz', 'ArrowUp', true)).toBeNull();
  });

  it('at the end of the list asks for the place it already has, which is said, not sent', () => {
    expect(planReorder(queue, 'job_a', keyboardTarget(queue, 'job_a', 'ArrowUp', true)!, BOTH)).toEqual({ kind: 'keep' });
    expect(planReorder(queue, 'job_c', keyboardTarget(queue, 'job_c', 'ArrowDown', true)!, BOTH)).toEqual({ kind: 'keep' });
  });
});

describe('the rendered list', () => {
  function list(roles: Role[], items: ExecutionQueueItem[], extra: { reorderNote?: string | null; busy?: boolean } = {}): string {
    return renderToStaticMarkup(createElement(ExecutionQueue, {
      items, roles, asOf: Date.parse('2026-10-09T10:05:00Z'), busy: extra.busy ?? false,
      workerOf: (): RunWorker => ({ kind: 'pending' }), onCancel: noop, onReaudit: noop, onPriority: noop, onReorder: noop,
      reorderNote: extra.reorderNote ?? null, onNext: null, onPrevious: null,
    }));
  }
  const two = [job('a', 3, 1), job('b', 2, 2)];

  it('gives a handle to each waiting row, for a role that may set a priority', () => {
    const markup = list(['admin'], two);
    expect((markup.match(/data-queue-handle=""/g) ?? []).length).toBe(2);
    expect(markup).toContain('draggable="true"');
    expect(markup).toContain('role="button"');
    expect(markup).toContain('Переместить задачу: АР, лист 3, версия 2');
    expect(markup).toContain('data-queue-reorder-hint=""');
    expect(markup).toContain('Alt+↑');
    expect(markup).toContain('Alt+↓');
    expect(markup).toContain('role="status"');
    expect(markup).toContain('aria-live="polite"');
  });

  it('gives no handle to a role that may not set a priority, or where one waiting job is all there is', () => {
    expect(list(['expert'], two)).not.toContain('data-queue-handle');
    expect(list([], two)).not.toContain('data-queue-handle');
    expect(list(['admin'], [job('a', 3, 1)])).not.toContain('data-queue-handle');
    expect(list(['admin'], [job('a', 3, 1), job('b', 2, 2, 'running')])).not.toContain('data-queue-handle');
  });

  it('gives a handle to waiting rows only, not to the jobs being run or finished', () => {
    const markup = list(['admin'], [job('a', 3, 1), job('b', 2, 2), job('c', 0, 3, 'running'), job('d', 0, 4, 'succeeded')]);
    expect((markup.match(/data-queue-handle=""/g) ?? []).length).toBe(2);
  });

  it('does not start a drag while a command is on its way', () => {
    expect(list(['admin'], two, { busy: true })).toContain('draggable="false"');
  });

  it('says what the last move came to in the live region', () => {
    const markup = list(['admin'], two, { reorderNote: 'Сервер не принял перемещение. Задача осталась на прежнем месте.' });
    expect(markup).toMatch(/data-queue-reorder-note=""[^>]*>Сервер не принял перемещение\. Задача осталась на прежнем месте\.</);
  });

  it('keeps the typed priority beside the handle, unchanged', () => {
    expect(list(['admin'], two)).toContain('Изменить</button>');
  });

  it('does not offer a move without a handler for it', () => {
    const markup = renderToStaticMarkup(createElement(ExecutionQueue, {
      items: two, roles: ['admin'], asOf: null, busy: false, workerOf: (): RunWorker => ({ kind: 'pending' }),
      onCancel: noop, onReaudit: noop, onPriority: noop, onNext: null, onPrevious: null,
    }));
    expect(markup).not.toContain('data-queue-handle');
    expect(markup).not.toContain('data-queue-reorder-note');
  });
});
