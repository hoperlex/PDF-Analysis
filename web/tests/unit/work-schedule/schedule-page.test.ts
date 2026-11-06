/**
 * «График работ» with the engineer filter and «Просрочки» (`D-319`), rendered from seeded caches: the rows an
 * administrator's filter leaves in the month and in the reserve, the select an expert is not given, what the tile counts
 * and says while the reserve is read and when it fails, and the note for an engineer the read does not carry.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { WorkSchedulePage } from '@/_pages/work-schedule';
import type { ScheduleAddress } from '@/_pages/work-schedule';
import type { Role } from '@/shared/api';
import { queryKeys } from '@/shared/api';

import { newClient, renderScreen, seedError } from '../screens/harness';
import { EXPERT_A, EXPERT_B, monthFixture, reserveFixture } from './fixtures';

const NOBODY = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z';
// The reserve fixture's dated work is on 3 November: two assignments of Иванова Анна are late on the 4th.
const TODAY = '2026-11-04';

type Reads = 'seeded' | 'pending' | 'failed';

function page(
  roles: readonly Role[],
  address: Partial<ScheduleAddress> = {},
  reads: Reads = 'seeded',
): string {
  const client = newClient();
  client.setQueryData(queryKeys.workSchedule.month('2026-11'), monthFixture());
  client.setQueryData(queryKeys.workSchedule.reserve('2026-11-02', 28), reserveFixture());
  if (reads === 'seeded') client.setQueryData(queryKeys.workSchedule.reserve(TODAY, 1), reserveFixture());
  if (reads === 'failed') seedError(client, queryKeys.workSchedule.reserve(TODAY, 1), new Error('unavailable'));
  return renderScreen(client, createElement(WorkSchedulePage, {
    roles,
    today: TODAY,
    initial: { tab: 'completed', month: '2026-11', start: '2026-11-02', engineer: null, ...address },
  }));
}

/** The markup without the filter's own options, which name every engineer whatever the rows are. */
function withoutSelect(html: string): string {
  return html.replace(/<select[\s\S]*?<\/select>/g, '');
}

const overdueTile = (html: string): string => /<div[^>]*data-schedule-overdue[\s\S]*?<\/div>/.exec(html)?.[0] ?? '';

describe('the engineer filter on «Выполнено»', () => {
  it('draws «Инженер: Все» and one option a engineer for an administrator, with everyone\'s rows', () => {
    const html = page(['admin', 'expert']);
    expect(html).toContain('data-schedule-filter=""');
    const select = /<select[\s\S]*?<\/select>/.exec(html)?.[0] ?? '';
    expect(select).toContain('>Все</option>');
    expect(select).toContain(`value="${EXPERT_A}"`);
    expect(select).toContain(`value="${EXPERT_B}"`);
    expect(withoutSelect(html)).toContain('Иванова Анна');
    expect(withoutSelect(html)).toContain('Петров Борис');
    expect(html).not.toContain('data-schedule-filter-unknown');
  });

  it('narrows the grid, the table and the tiles to the engineer the address names', () => {
    const html = page(['admin'], { engineer: EXPERT_B });
    expect(html).toContain(`data-schedule-filter="${EXPERT_B}"`);
    expect(html).toContain(`<option value="${EXPERT_B}" selected="">`);
    const rows = withoutSelect(html);
    expect(rows).toContain('Петров Борис');
    expect(rows).not.toContain('Иванова Анна');
    // One engineer in work, none of Иванова Анна's five reports, and the total row counts one.
    expect(rows).toMatch(/Инженеров в работе<\/span><span[^>]*>1<\/span>/);
    expect(rows).toMatch(/Отчётов за месяц<\/span><span[^>]*>0<\/span>/);
    expect(rows).toContain('Всего по инженерам (1)');
  });

  it('shows everyone and says why when the address names an engineer the read does not carry', () => {
    const html = page(['admin'], { engineer: NOBODY });
    expect(html).toContain('data-schedule-filter-unknown=""');
    expect(html).toContain('Инженер из ссылки не найден среди действующих — показаны все.');
    expect(withoutSelect(html)).toContain('Иванова Анна');
    expect(withoutSelect(html)).toContain('Петров Борис');
  });

  it('is not drawn for an expert, and the address\'s engineer is not applied to them', () => {
    const html = page(['expert'], { engineer: EXPERT_B });
    expect(html).not.toContain('data-schedule-filter');
    expect(html).not.toContain('<select');
    expect(html).toContain('Иванова Анна');
    expect(html).toContain('Петров Борис');
  });
});

describe('«Просрочки» on «Выполнено»', () => {
  it('counts the open assignments planned before today, and says what it counts in its title', () => {
    const tile = overdueTile(page(['admin']));
    expect(tile).toContain('data-schedule-overdue="ready"');
    expect(tile).toContain('Открытые назначения «Диспетчера», у которых плановая дата раньше сегодняшнего дня. Работа без даты не считается.');
    expect(tile).toMatch(/Просрочки<\/span><span[^>]*>2<\/span>/);
    expect(tile).toContain('Назначения с прошедшей датой');
  });

  it('counts the chosen engineer\'s with the filter', () => {
    expect(overdueTile(page(['admin'], { engineer: EXPERT_A }))).toMatch(/Просрочки<\/span><span[^>]*>2<\/span>/);
    expect(overdueTile(page(['admin'], { engineer: EXPERT_B }))).toMatch(/Просрочки<\/span><span[^>]*>0<\/span>/);
  });

  it('is drawn for an expert as well, from the work the read carries for them', () => {
    expect(overdueTile(page(['expert']))).toMatch(/Просрочки<\/span><span[^>]*>2<\/span>/);
  });

  it('shows no number while the reserve is read, and says so when it could not be', () => {
    const pending = overdueTile(page(['admin'], {}, 'pending'));
    expect(pending).toContain('data-schedule-overdue="pending"');
    expect(pending).toMatch(/Просрочки<\/span><span[^>]*>…<\/span>/);
    const failed = overdueTile(page(['admin'], {}, 'failed'));
    expect(failed).toContain('data-schedule-overdue="failed"');
    expect(failed).toMatch(/Просрочки<\/span><span[^>]*>—<\/span>/);
    expect(failed).toContain('Назначения не загружены');
  });

  it('leaves the month standing when the reserve fails', () => {
    const html = page(['admin'], {}, 'failed');
    expect(html).toContain('data-schedule-month="2026-11"');
    expect(withoutSelect(html)).toContain('Иванова Анна');
  });
});

describe('the engineer filter on «Календарь запаса»', () => {
  const reserve = (roles: readonly Role[], engineer: string | null) => page(roles, { tab: 'reserve', engineer });

  it('narrows the queue to the engineer the address names', () => {
    const html = reserve(['admin'], EXPERT_B);
    expect(html).toContain('data-schedule-reserve="2026-11-02"');
    expect(html).toContain(`data-schedule-filter="${EXPERT_B}"`);
    expect(withoutSelect(html)).toContain('Петров Борис');
    expect(withoutSelect(html)).not.toContain('Иванова Анна');
    expect(withoutSelect(html)).not.toContain('Школа на 550 мест');
  });

  it('shows every engineer without a choice, and none of them a filter for an expert', () => {
    expect(withoutSelect(reserve(['admin'], null))).toContain('Школа на 550 мест');
    const expert = reserve(['expert'], EXPERT_B);
    expect(expert).not.toContain('data-schedule-filter');
    expect(expert).toContain('Иванова Анна');
  });

  it('says why everyone is shown when the engineer is not in the read', () => {
    expect(reserve(['admin'], NOBODY)).toContain('data-schedule-filter-unknown=""');
  });
});
