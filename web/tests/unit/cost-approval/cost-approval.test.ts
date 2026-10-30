import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { CostApproval, ceilingMicros, microsAsUsd, usableCostEstimate } from '@/shared/ui';
import { costEstimate } from '../analysis-settings/cost-estimate-fixtures';

describe('explicit finite cost approval', () => {
  it('converts decimal USD to exact micros without rounding the approved cap', () => {
    expect(ceilingMicros(' 1,200001 ', 1_200_000)).toBe(1_200_001);
    expect(ceilingMicros('0.000001', 0)).toBe(1);
    expect(ceilingMicros('0', 0)).toBe(0);
    for (const value of ['', '-1', 'NaN', 'Infinity', '1e6', '1.2000001', '9007199254.740992']) {
      expect(ceilingMicros(value, 0), value).toBeNull();
    }
    expect(ceilingMicros('1.199999', 1_200_000)).toBeNull();
    expect(microsAsUsd(1)).toBe('0.000001');
    expect(microsAsUsd(1_500_000)).toBe('1.5');
  });

  it('refuses malformed readings before they can become a confirmable amount', () => {
    const estimate = costEstimate({ version_uid: 'ver_fixture' });
    expect(usableCostEstimate(estimate)).toBe(true);
    expect(usableCostEstimate({ ...estimate, recommended_ceiling_micros: 1 })).toBe(false);
    expect(usableCostEstimate({ ...estimate, input_tokens: Infinity })).toBe(false);
    expect(usableCostEstimate({ ...estimate, estimate_digest: 'missing' })).toBe(false);
  });

  it('shows actual estimate metrics and the recorded caption, with no automatic agreement', () => {
    const markup = renderToStaticMarkup(createElement(CostApproval, {
      estimate: costEstimate({ version_uid: 'ver_fixture' }), ceiling: '1.5', approved: false,
      disabled: false, onCeilingChange() {}, onApprovedChange() {},
    }));
    expect(markup).toContain('Предварительная оценка: 1.2 USD.');
    expect(markup).toContain('Тестовый режим (recorded)');
    expect(markup).toContain('Оценка не является фактическим расходом.');
    expect(markup).toContain('вызовов: 1');
    expect(markup).not.toContain('checked');
  });

  it('permits zero approval only for an unmetered reading', () => {
    const render = (billing: 'metered' | 'unmetered') => renderToStaticMarkup(createElement(CostApproval, {
      estimate: { ...costEstimate({ version_uid: 'ver_fixture' }), billing,
        estimated_cost_micros: 0, recommended_ceiling_micros: 0 },
      ceiling: '0', approved: true, disabled: false, onCeilingChange() {}, onApprovedChange() {},
    }));
    expect(render('metered')).toContain('лимит должен быть положительным');
    expect(render('metered')).not.toContain('checked');
    expect(render('unmetered')).toContain('checked');
  });
});
