/**
 * `RUN-SCREEN-FIX-01`: the counts of the cost dialog (pages, characters, windows, calls, input tokens) are grouped by threes with a narrow
 * no-break space, as the application groups every large integer (`groupDigits`), so «412380» reads «412 380».
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { StartRunCostDialogView } from '@/features/start-run';

import { VERSION_UID } from '../review/fixtures';
import { costEstimate } from '../analysis-settings/cost-estimate-fixtures';

const NNBSP = ' ';

const dialog = (estimate: Partial<ReturnType<typeof costEstimate>>, relaxed = false) => renderToStaticMarkup(createElement(StartRunCostDialogView, {
  estimate: { ...costEstimate({ version_uid: VERSION_UID }), ...estimate }, relaxed, ceiling: '1.5', changed: false, busy: false, staticOpen: true,
  onCeilingChange: () => undefined, onConfirm: () => undefined, onCancel: () => undefined,
}));

describe('the counts of the cost dialog', () => {
  it('group a large integer by threes, with the narrow no-break space', () => {
    const markup = dialog({ text_characters: 412_380, input_tokens: 238_400, page_count: 1_204, windows: 1_000, calls: 12_345 });
    expect(markup).toContain(`символов: 412${NNBSP}380;`);
    expect(markup).toContain(`Оценка входных токенов: 238${NNBSP}400.`);
    expect(markup).toContain(`Страниц: 1${NNBSP}204;`);
    expect(markup).toContain(`окон: 1${NNBSP}000;`);
    expect(markup).toContain(`вызовов: 12${NNBSP}345.`);
    expect(markup).not.toContain('412380');
    expect(markup).not.toContain('238400');
  });

  it('say the starting count of calls of a start with no ceiling in the same way', () => {
    expect(dialog({ calls: 12_345 }, true)).toContain(`начальная оценка вызовов: 12${NNBSP}345.`);
  });

  it('leave a number under a thousand as it is, and write no separator where there is no group', () => {
    const markup = dialog({ text_characters: 999, input_tokens: 0, page_count: 2, windows: 1, calls: 1 });
    expect(markup).toContain('символов: 999;');
    expect(markup).toContain('Оценка входных токенов: 0.');
    expect(markup).toContain('Страниц: 2;');
    expect(markup).not.toContain(NNBSP);
  });
});
